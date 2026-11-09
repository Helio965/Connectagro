"""Autoridade global explícita, limitada à revisão do catálogo."""
import re

from flask import abort, g, request
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from ..extensions import db
from ..models import (CatalogoControle, ProdutoBase, ProdutoTecnico, Propriedade,
                      SolicitacaoCatalogo, Usuario)
from ..models._helpers import iso_now
from ..utils.auth import usuario_atual
from ..utils.contexto import invalidar_contexto
from ..utils.permissions import has_permission
from .auditoria_service import preparar_evento
from .catalogo_local_service import (CAMPOS_PROPOSTA, ErroCatalogo, _campos, auditar,
    buscar_duplicacoes, conferir_formulario, fingerprint_global, gerar_slug,
    json_canonico, ler_json_seguro, nome_restrito)
from .operacionais_service import parse_id


def adquirir_lock_catalogo(db_session):
    """Trava comum de seed/publicação, sem commit nem mudança de contexto."""
    conexao = db_session.connection()
    tabela = CatalogoControle.__table__
    if conexao.dialect.name == "sqlite":
        if conexao.connection.driver_connection.in_transaction:
            conexao.execute(db.update(tabela).where(tabela.c.id == 1).values(id=tabela.c.id))
        else:
            conexao.exec_driver_sql("BEGIN IMMEDIATE")
        conexao.execute(sqlite_insert(tabela).values(id=1).on_conflict_do_nothing())
    elif conexao.dialect.name == "postgresql":
        conexao.execute(pg_insert(tabela).values(id=1).on_conflict_do_nothing())
    else:
        raise ValueError("Banco não suportado para governança de catálogo.")
    conexao.execute(db.select(tabela.c.id).where(tabela.c.id == 1).with_for_update()).one()


def _travar_decisao(solicitacao_id):
    ator = usuario_atual()
    if ator is None:
        abort(403)
    ator_id = ator["id"]
    adquirir_lock_catalogo(db.session)
    pedido = db.session.get(SolicitacaoCatalogo, solicitacao_id, populate_existing=True)
    if pedido is None:
        abort(404)
    # Ordem comum: catálogo → propriedade de origem → conta do revisor. Isso
    # não seleciona a Propriedade na sessão nem libera suas rotas operacionais.
    conexao = db.session.connection()
    if conexao.execute(db.select(Propriedade.id).where(
            Propriedade.id == pedido.propriedade_id).with_for_update()).first() is None:
        abort(409)
    conexao.execute(db.select(Usuario.id).where(Usuario.id == ator_id).with_for_update()).first()
    db.session.expire_all()
    g.pop("_auth_request", None)
    g.pop("_auth_usuario", None)
    invalidar_contexto()
    if not has_permission("catalogo.global.decide"):
        abort(403)
    return db.session.get(SolicitacaoCatalogo, solicitacao_id, populate_existing=True)


def _validar_origem(pedido):
    origem = pedido.produto_local if pedido.tipo == "inclusao" else pedido.personalizacao
    if (origem is None or origem.propriedade_id != pedido.propriedade_id
            or not origem.ativo or origem.versao != pedido.origem_versao):
        abort(409)
    return origem


def decidir_solicitacao(solicitacao_id, acao, form):
    conferir_formulario(form, {"justificativa", "slug_global", "produto_global_existente_id", "confirmar_distinto"})
    pedido = _travar_decisao(solicitacao_id)
    destino = "aprovada" if acao == "aprovar" else "rejeitada"
    if pedido.estado == destino:
        return pedido
    if pedido.estado != "pendente":
        abort(409)
    justificativa = _campos(form, {"justificativa": 2000})["justificativa"]
    if acao == "rejeitar":
        pedido.estado = "rejeitada"
    else:
        origem = _validar_origem(pedido)
        dados = ler_json_seguro(pedido.conteudo_json)
        if pedido.tipo == "inclusao":
            conferir_formulario(dados, CAMPOS_PROPOSTA)
            dados = _campos(dados, CAMPOS_PROPOSTA, ("nome", "classe"))
            slug = str(form.get("slug_global") or gerar_slug(dados["nome"])).strip()
            if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", slug) or len(slug) > 150:
                raise ErroCatalogo({"slug_global": "Informe uma identificação com letras minúsculas, números e hífens, até 150 caracteres."})
            if nome_restrito(dados["nome"], slug):
                raise ErroCatalogo({"formulario": "A proposta coincide com referência bloqueada/excluída; este fluxo não libera seu uso."})
            try:
                existente_id = parse_id(form.get("produto_global_existente_id"), opcional=True)
            except ValueError as exc:
                raise ErroCatalogo({"produto_global_existente_id": str(exc)}) from None
            if existente_id is not None:
                produto = (ProdutoBase.query.filter_by(id=existente_id).with_for_update().first())
                if (produto is None or produto.classe != dados["classe"]
                        or produto.status_sistema == "bloqueado_historico"
                        or produto.status_regulatorio == "bloqueado_historico"):
                    raise ErroCatalogo({"produto_global_existente_id": "Escolha uma referência global da mesma classe, sem bloqueio."})
                # Associação humana explícita do resultado, sem alterar o
                # existente, fundir locais ou remapear histórico operacional.
                pedido.produto_publicado_id = produto.id
            else:
                duplicacoes = buscar_duplicacoes(dados["nome"], dados["classe"])
                if ProdutoBase.query.filter_by(slug=slug).first() is not None:
                    abort(409)
                if duplicacoes and form.get("confirmar_distinto") not in {"1", "on", "true"}:
                    raise ErroCatalogo({"confirmar_distinto": "Revise as referências semelhantes e confirme que se trata de produto distinto."}, duplicacoes)
                from .catalogo_seed import sincronizar_seq_produto_base
                sincronizar_seq_produto_base(db.session)
                produto = ProdutoBase(nome=dados["nome"], slug=slug, classe=dados["classe"],
                    categoria=dados["categoria"], descricao_curta=dados["descricao_curta"],
                    descricao_completa=dados["descricao_completa"], status_sistema="cadastrado_usuario",
                    status_regulatorio="nao_validado_agrofit" if dados["classe"] == "defensivo"
                    else "sujeito_a_sipeagro_nao_validado")
                db.session.add(produto)
                db.session.flush()
                if dados["fonte"]:
                    db.session.add(ProdutoTecnico(produto_id=produto.id, fonte_tecnica=dados["fonte"]))
                pedido.produto_publicado_id = produto.id
        elif pedido.tipo == "alteracao":
            campos = {c: CAMPOS_PROPOSTA[c] for c in ("descricao_curta", "descricao_completa", "fonte")}
            conferir_formulario(dados, campos)
            dados = _campos(dados, campos)
            produto = ProdutoBase.query.filter_by(id=origem.produto_base_id).with_for_update().first()
            if produto is None or pedido.global_fingerprint != fingerprint_global(produto):
                abort(409)
            pedido.global_anterior_json = json_canonico({
                "descricao_curta": produto.descricao_curta, "descricao_completa": produto.descricao_completa})
            produto.descricao_curta, produto.descricao_completa = dados["descricao_curta"], dados["descricao_completa"]
            produto.atualizado_em = iso_now()
            pedido.produto_publicado_id = produto.id
        else:
            raise ErroCatalogo({"formulario": "O tipo de solicitação precisa ser revisado."})
        pedido.estado = "aprovada"
    pedido.decidido_por_id = usuario_atual()["id"]
    pedido.decidido_em, pedido.justificativa = iso_now(), justificativa
    auditar("catalogo.solicitacao."+acao, pedido,
            "Decisão administrativa: " + pedido.estado + "; sem validação regulatória oficial")
    return pedido


def definir_aprovador_global(usuario_id, habilitar, motivo=None):
    """Provisionamento explícito pelo operador CLI; não há rota de autoconcessão."""
    adquirir_lock_catalogo(db.session)
    usuario = Usuario.query.filter_by(id=usuario_id).with_for_update().first()
    if usuario is None or (habilitar and (usuario.perfil != "admin" or not usuario.ativo)):
        raise ValueError("A habilitação exige uma conta Administrador existente e ativa.")
    if usuario.catalogo_global_aprovador == habilitar:
        return False
    usuario.catalogo_global_aprovador = habilitar
    db.session.add(preparar_evento("catalogo.global.habilitar" if habilitar else "catalogo.global.revogar",
        entidade="usuario", entidade_id=usuario.id,
        descricao="Capacidade de revisão global " + ("habilitada" if habilitar else "revogada") +
                  " explicitamente pelo operador CLI" + ("; motivo informado" if motivo else "")))
    return True
