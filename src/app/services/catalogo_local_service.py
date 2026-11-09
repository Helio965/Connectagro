"""Cadastros e complementos locais; nenhuma FK operacional ou preço é alterado."""
import hashlib
import json
import re
import unicodedata
from uuid import UUID

from flask import abort, request
from sqlalchemy import or_

from ..extensions import db
from ..models import (CatalogoRevisao, ProdutoBase, ProdutoLocal,
                      ProdutoPersonalizacao, SolicitacaoCatalogo)
from ..models._helpers import iso_now
from ..utils.auth import usuario_atual
from .auditoria_service import preparar_evento
from .operacionais_service import parse_id

CLASSES = {"defensivo", "fertilizante"}
CAMPOS_LOCAL = {"nome": 150, "classe": 30, "categoria": 40,
    "descricao_curta": 255, "descricao_completa": 5000,
    "unidade_referencia": 20, "observacoes": 5000, "fonte": 255}
CAMPOS_PERSONALIZACAO = {"nome_local": 150, "descricao_local": 5000,
    "unidade_referencia": 20, "observacoes": 5000, "fonte": 255}
CAMPOS_PROPOSTA = {"nome": 150, "classe": 30, "categoria": 40,
    "descricao_curta": 255, "descricao_completa": 5000, "fonte": 255}
PROTEGIDOS = {"propriedade_id", "usuario_id", "criado_por_id", "atualizado_por_id",
    "status_sistema", "status_regulatorio", "catalogo_global_aprovador", "estado",
    "produto_base_id", "produto_global_id", "produto_publicado_id", "decidido_por_id",
    "solicitado_por_id", "solicitado_em", "decidido_em", "criado_em", "atualizado_em", "ativo", "versao"}


class ErroCatalogo(ValueError):
    def __init__(self, errors, duplicacoes=None):
        self.errors = errors
        self.duplicacoes = duplicacoes or []
        super().__init__(next(iter(errors.values()), "Revise os campos informados."))


def json_canonico(dados):
    return json.dumps(dados, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def ler_json_seguro(texto):
    try:
        if not isinstance(texto, str) or len(texto.encode("utf-8")) > 65536:
            raise ValueError
        dados = json.loads(texto)
        if not isinstance(dados, dict):
            raise ValueError
        return dados
    except (ValueError, TypeError, RecursionError):
        raise ErroCatalogo({"formulario": "O conteúdo registrado precisa ser revisado antes de continuar."}) from None


def normalizar_nome(nome):
    texto = unicodedata.normalize("NFKD", str(nome or "")).casefold()
    return " ".join("".join(c for c in texto if not unicodedata.combining(c)).split())


def gerar_slug(nome):
    texto = normalizar_nome(nome).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", "-", texto).strip("-")[:150].rstrip("-")


def conferir_formulario(form, permitidos):
    enviados = set(form.keys()) - {"csrf_token"}
    if (enviados - set(permitidos)) & PROTEGIDOS:
        abort(403)
    if enviados - set(permitidos):
        raise ErroCatalogo({"formulario": "O formulário contém campos não permitidos."})
    if hasattr(form, "getlist") and any(len(form.getlist(campo)) != 1 for campo in enviados):
        raise ErroCatalogo({"formulario": "Envie cada campo uma única vez."})


def _campos(form, limites, obrigatorios=()):
    dados, errors = {}, {}
    for campo, limite in limites.items():
        valor = str(form.get(campo) or "").strip() or None
        dados[campo] = valor
        if campo in obrigatorios and valor is None:
            errors[campo] = "Este campo é obrigatório."
        elif valor and (len(valor) > limite or any(ord(c) < 32 and c not in "\r\n\t" for c in valor)):
            errors[campo] = f"Use até {limite} caracteres de texto válido."
    if "classe" in dados and dados["classe"] not in CLASSES:
        errors["classe"] = "Escolha Defensivo ou Fertilizante."
    if errors:
        raise ErroCatalogo(errors)
    return dados


def nome_restrito(nome, slug=None):
    """Só bloqueios já documentados/registrados; não é validação regulatória."""
    from .catalogo_seed import carregar_seed
    normalizado, slug_nome = normalizar_nome(nome), gerar_slug(nome)
    slugs = {s for s in (slug, slug_nome) if s}
    bloqueados = ProdutoBase.query.filter(or_(
        ProdutoBase.status_sistema == "bloqueado_historico",
        ProdutoBase.status_regulatorio == "bloqueado_historico")).all()
    if any(normalizar_nome(p.nome) == normalizado or p.slug in slugs for p in bloqueados):
        return True
    for item in carregar_seed().get("itens_bloqueados_ou_excluidos", []):
        if item.get("slug") in slugs or (item.get("nome") and normalizar_nome(item["nome"]) == normalizado):
            return True
    return False


def buscar_duplicacoes(nome, classe, propriedade_id=None, excluir_local_id=None):
    nome_chave, slug = normalizar_nome(nome), gerar_slug(nome)
    resultado = []
    if not nome_chave:
        return resultado
    for p in ProdutoBase.query.filter_by(classe=classe).order_by(ProdutoBase.id).all():
        if normalizar_nome(p.nome) == nome_chave or p.slug == slug:
            resultado.append({"origem": "global", "id": p.id, "nome": p.nome, "classe": p.classe})
    if propriedade_id is not None:
        for p in ProdutoLocal.query.filter_by(propriedade_id=propriedade_id, classe=classe).order_by(ProdutoLocal.id).all():
            if p.id != excluir_local_id and normalizar_nome(p.nome) == nome_chave:
                resultado.append({"origem": "local", "id": p.id, "nome": p.nome, "classe": p.classe})
    return resultado[:50]


def conferir_versao(registro, valor):
    try:
        versao = parse_id(valor)
    except ValueError:
        abort(409)
    if versao != registro.versao or versao >= 2**31-1:
        abort(409)


def auditar(acao, registro, descricao):
    db.session.add(preparar_evento(acao, entidade=registro.__tablename__,
        entidade_id=registro.id, propriedade_id=registro.propriedade_id,
        descricao=descricao, request=request))


def registrar_revisao(registro, acao):
    db.session.flush()
    local = isinstance(registro, ProdutoLocal)
    campos = CAMPOS_LOCAL if local else CAMPOS_PERSONALIZACAO
    snapshot = {campo: getattr(registro, campo) for campo in campos}
    snapshot.update(ativo=registro.ativo, versao=registro.versao)
    db.session.add(CatalogoRevisao(propriedade_id=registro.propriedade_id,
        produto_local_id=registro.id if local else None,
        personalizacao_id=None if local else registro.id, versao=registro.versao,
        snapshot_json=json_canonico(snapshot), alterado_por_id=usuario_atual()["id"], acao=acao))
    auditar("catalogo.local."+acao if local else "catalogo.personalizacao."+acao,
            registro, "Registro local: " + acao + "; campos: " + ", ".join(campos))


def salvar_local(propriedade, form, registro=None):
    permitidos = set(CAMPOS_LOCAL) | {"confirmar_semelhante", "versao" if registro else "chave_envio"}
    conferir_formulario(form, permitidos)
    dados = _campos(form, CAMPOS_LOCAL, ("nome", "classe"))
    if nome_restrito(dados["nome"]):
        raise ErroCatalogo({"nome": "Este nome corresponde a uma referência bloqueada/excluída. O cadastro local não pode liberar seu uso."})
    duplicacoes = buscar_duplicacoes(dados["nome"], dados["classe"], propriedade.id,
                                    registro.id if registro else None)
    if registro is not None:
        conferir_versao(registro, form.get("versao"))
        if all(getattr(registro, campo) == valor for campo, valor in dados.items()):
            return registro
    else:
        try:
            chave = UUID(str(form.get("chave_envio") or "")).hex
        except ValueError:
            raise ErroCatalogo({"chave_envio": "Recarregue o formulário para iniciar um novo registro."}) from None
        anterior = ProdutoLocal.query.filter_by(chave_envio=chave).first()
        if anterior:
            if (anterior.propriedade_id != propriedade.id or anterior.criado_por_id != usuario_atual()["id"]
                    or not anterior.ativo or any(getattr(anterior, c) != v for c, v in dados.items())):
                abort(409)
            return anterior
    if duplicacoes and form.get("confirmar_semelhante") not in {"1", "on", "true"}:
        raise ErroCatalogo({"confirmar_semelhante": "Há referências com nome semelhante. Confira se este é um registro local distinto."}, duplicacoes)
    if registro is None:
        registro = ProdutoLocal(**dados, propriedade_id=propriedade.id,
            criado_por_id=usuario_atual()["id"], chave_envio=chave, ativo=True, versao=1)
        db.session.add(registro)
        acao = "create"
    else:
        for campo, valor in dados.items():
            setattr(registro, campo, valor)
        registro.versao += 1
        registro.atualizado_por_id, registro.atualizado_em = usuario_atual()["id"], iso_now()
        acao = "edit"
    registrar_revisao(registro, acao)
    return registro


def salvar_personalizacao(propriedade, produto, form, registro=None):
    conferir_formulario(form, set(CAMPOS_PERSONALIZACAO) | {"versao"})
    dados = _campos(form, CAMPOS_PERSONALIZACAO)
    if not any(dados.values()):
        raise ErroCatalogo({"formulario": "Informe ao menos um complemento local."})
    if registro is None:
        registro = ProdutoPersonalizacao(**dados, propriedade_id=propriedade.id,
            produto_base_id=produto.id, criado_por_id=usuario_atual()["id"], ativo=True, versao=1)
        db.session.add(registro)
        acao = "create"
    else:
        conferir_versao(registro, form.get("versao"))
        if all(getattr(registro, c) == v for c, v in dados.items()):
            return registro
        for campo, valor in dados.items():
            setattr(registro, campo, valor)
        registro.versao += 1
        registro.atualizado_por_id, registro.atualizado_em = usuario_atual()["id"], iso_now()
        acao = "edit"
    registrar_revisao(registro, acao)
    return registro


def alterar_estado(registro, ativo, versao):
    conferir_versao(registro, versao)
    if registro.ativo != ativo:
        registro.ativo = ativo
        registro.versao += 1
        registro.atualizado_por_id, registro.atualizado_em = usuario_atual()["id"], iso_now()
        registrar_revisao(registro, "reativar" if ativo else "inativar")


def fingerprint_global(produto):
    campos = ("nome", "slug", "classe", "categoria", "descricao_curta", "descricao_completa",
              "status_sistema", "status_regulatorio")
    return hashlib.sha256(json_canonico({c: getattr(produto, c) for c in campos}).encode()).hexdigest()


def proposta_padrao(registro):
    if isinstance(registro, ProdutoLocal):
        return {c: getattr(registro, c) for c in CAMPOS_PROPOSTA}
    return {"descricao_curta": registro.produto.descricao_curta,
            "descricao_completa": registro.descricao_local,
            "fonte": registro.fonte}


def solicitar(registro, form):
    local = isinstance(registro, ProdutoLocal)
    campos = CAMPOS_PROPOSTA if local else {c: CAMPOS_PROPOSTA[c] for c in ("descricao_curta", "descricao_completa", "fonte")}
    conferir_formulario(form, set(campos) | {"versao_origem"})
    conferir_versao(registro, form.get("versao_origem"))
    if not registro.ativo:
        abort(409)
    dados = _campos(form, campos, ("nome", "classe") if local else ())
    if local and nome_restrito(dados["nome"]):
        raise ErroCatalogo({"nome": "Uma referência bloqueada/excluída não pode ser publicada por este fluxo."})
    if not local and all(dados[c] == getattr(registro.produto, c) for c in ("descricao_curta", "descricao_completa")):
        raise ErroCatalogo({"formulario": "Informe uma alteração descritiva para propor ao catálogo global."})
    origem_campo = "produto_local_id" if local else "personalizacao_id"
    anterior = SolicitacaoCatalogo.query.filter_by(**{origem_campo: registro.id}, origem_versao=registro.versao).first()
    conteudo = json_canonico(dados)
    if anterior is not None:
        if anterior.conteudo_json != conteudo:
            abort(409)
        return anterior
    pedido = SolicitacaoCatalogo(propriedade_id=registro.propriedade_id,
        **{origem_campo: registro.id}, tipo="inclusao" if local else "alteracao",
        origem_versao=registro.versao, conteudo_json=conteudo,
        global_fingerprint=None if local else fingerprint_global(registro.produto),
        solicitado_por_id=usuario_atual()["id"], estado="pendente")
    db.session.add(pedido)
    db.session.flush()
    auditar("catalogo.solicitacao.create", pedido, "Solicitação enviada; fonte versionada e proposta preservada")
    return pedido
