"""Atividades por área autorizada; itens e auditoria persistem atomicamente."""
from uuid import UUID, uuid4

from flask import abort, flash, redirect, render_template, request, url_for
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError

from ...extensions import db
from ...models import (AtividadeItem, AtividadeOperacional, Cultura, CulturaGleba,
                       Gleba, ProdutoBase)
from ...models._helpers import iso_now
from ...services.auditoria_service import preparar_evento
from ...services.operacionais_lock import serializar_operacao
from ...services.operacionais_service import (
    CAMPOS_CUSTO, opcoes_responsaveis, parse_id, validar_consumo_custo,
    validar_data_iso, validar_decimal, validar_responsavel,
)
from ...utils.auth import login_required, usuario_atual
from ...utils.contexto import propriedade_atual
from ...utils.permissions import has_permission, require_permission
from . import atividades_bp

MAX_ITENS = 20
_CAMPOS_ATIVIDADE = ("gleba_id", "cultura_gleba_id", "tipo_atividade", "data_execucao",
                     "responsavel", "responsavel_usuario_id", "observacao")
_CAMPOS_ITEM = ("item_id", "produto_base_id", "dose", "unidade_dose",
                "quantidade_utilizada", "unidade_quantidade", "custo_unitario",
                "custo_total", "moeda")
_STATUS_BLOQUEADO = "bloqueado_historico"


def _query(propriedade):
    # Mesmo dados inconsistentes legados não podem atravessar os dois contextos.
    return (AtividadeOperacional.query.join(Gleba, AtividadeOperacional.gleba_id == Gleba.id)
            .outerjoin(CulturaGleba, AtividadeOperacional.cultura_gleba_id == CulturaGleba.id)
            .outerjoin(Cultura, CulturaGleba.cultura_id == Cultura.id)
            .filter(Gleba.propriedade_id == propriedade.id,
                    or_(AtividadeOperacional.cultura_gleba_id.is_(None),
                        (Cultura.propriedade_id == propriedade.id) &
                        (CulturaGleba.gleba_id == AtividadeOperacional.gleba_id))))


def _atividade_ou_404(atividade_id, propriedade):
    if not 1 <= atividade_id <= 2**31-1:
        abort(404)
    atividade = _query(propriedade).filter(AtividadeOperacional.id == atividade_id).first()
    if atividade is None:
        abort(404)
    return atividade


def _opcoes(propriedade, registro=None):
    glebas = Gleba.query.filter_by(propriedade_id=propriedade.id).order_by(Gleba.nome, Gleba.id).all()
    associacoes = (CulturaGleba.query.join(Cultura).join(Gleba)
                   .filter(Cultura.propriedade_id == propriedade.id,
                           Gleba.propriedade_id == propriedade.id)
                   .order_by(Cultura.nome, Gleba.nome, CulturaGleba.id).all())
    produtos = (ProdutoBase.query.filter(ProdutoBase.status_sistema != _STATUS_BLOQUEADO,
                                         ProdutoBase.status_regulatorio != _STATUS_BLOQUEADO)
                .order_by(ProdutoBase.nome, ProdutoBase.id).all())
    opcoes_produtos = [(p.id, p.nome) for p in produtos]
    if registro is not None:
        presentes = {p.id for p in produtos}
        for item in registro.itens:
            if not item.cancelado_em and item.produto_base_id not in presentes:
                opcoes_produtos.append((item.produto_base_id,
                    (item.produto.nome if item.produto else "Produto") + " (registro histórico; bloqueado para novo uso)"))
                presentes.add(item.produto_base_id)
    return dict(opcoes_glebas=[(g.id, g.nome) for g in glebas],
                opcoes_cultura_gleba=[(c.id, f"{c.cultura.nome} — {c.gleba.nome}") for c in associacoes],
                opcoes_produtos=opcoes_produtos,
                opcoes_responsaveis=opcoes_responsaveis(propriedade.id, registro))


def _formulario(propriedade, *, atividade=None, form=None, itens=None, erros=None, status=200):
    form = dict(form or {})
    if atividade is None and "chave_envio" not in form:
        form["chave_envio"] = uuid4().hex
    editar_custos = has_permission("financeiro.edit" if atividade else "financeiro.create")
    return render_template("atividades/form.html", atividade=atividade, form=form,
        itens=itens or [], erros=erros or {}, errors=erros or {},
        can_editar_custos=editar_custos, can_ver_custos=has_permission("financeiro.view"),
        token_envio=form.get("chave_envio"), **_opcoes(propriedade, atividade)), status


def _linhas_form():
    """Listas paralelas limitadas, sem truncar itens ou aceitar campos extras."""
    colunas = {campo: request.form.getlist(campo) for campo in _CAMPOS_ITEM if campo in request.form}
    # origem_custo é calculada pelo servidor, nunca aceita do navegador.
    if "origem_custo" in request.form:
        abort(400)
    if not colunas:
        return [], {}
    tamanho = max(map(len, colunas.values()))
    if tamanho > MAX_ITENS:
        return [], {"itens": f"Registre no máximo {MAX_ITENS} itens por atividade."}
    if len(colunas.get("produto_base_id", [])) != tamanho or any(len(v) != tamanho for v in colunas.values()):
        return [], {"itens": "Os campos dos itens estão incompletos. Revise as linhas e envie novamente."}
    return [{campo: valores[i] for campo, valores in colunas.items()} for i in range(tamanho)], {}


def _validar(propriedade, form, linhas, *, atividade=None):
    erros, dados = {}, {}
    for campo, limite, obrigatorio in (("tipo_atividade", 120, True), ("observacao", 10000, False)):
        valor = str(form.get(campo) or "").strip() or None
        dados[campo] = valor
        if (obrigatorio and valor is None) or (valor and len(valor) > limite):
            erros[campo] = f"Informe até {limite} caracteres." if valor else "Informe a atividade executada."
    try:
        dados["data_execucao"] = validar_data_iso(form.get("data_execucao"))
    except ValueError as exc:
        erros["data_execucao"] = str(exc)
    try:
        gid = parse_id(form.get("gleba_id"))
        gleba = Gleba.query.filter_by(id=gid, propriedade_id=propriedade.id).first()
        if gleba is None:
            raise ValueError("Selecione uma Área de Plantio desta propriedade.")
        dados["gleba_id"] = gid
    except ValueError as exc:
        erros["gleba_id"] = str(exc)
    try:
        cg_id = parse_id(form.get("cultura_gleba_id"), opcional=True)
        if cg_id is not None:
            associacao = (CulturaGleba.query.join(Cultura).join(Gleba)
                          .filter(CulturaGleba.id == cg_id,
                                  CulturaGleba.gleba_id == dados.get("gleba_id"),
                                  Cultura.propriedade_id == propriedade.id,
                                  Gleba.propriedade_id == propriedade.id).first())
            if associacao is None:
                raise ValueError("A cultura/ciclo deve pertencer à área selecionada e à propriedade ativa.")
        dados["cultura_gleba_id"] = cg_id
    except ValueError as exc:
        erros["cultura_gleba_id"] = str(exc)
    uid, nome, falhas = validar_responsavel(propriedade.id, form.get("responsavel_usuario_id"),
                                          form.get("responsavel"), registro=atividade)
    erros.update(falhas)
    dados.update(responsavel_usuario_id=uid, responsavel=nome)
    if not uid and not nome:
        erros["responsavel"] = "Informe o responsável ou selecione uma conta autorizada."
    anteriores = {item.id: item for item in atividade.itens if not item.cancelado_em} if atividade else {}
    vistos, itens = set(), []
    for indice, linha in enumerate(linhas):
        prefixo = f"itens.{indice}."
        # A linha inteiramente vazia é apenas o convite para adicionar um item.
        if not any(str(v or "").strip() for k, v in linha.items() if k != "moeda"):
            continue
        item_dados = {}
        try:
            item_id = parse_id(linha.get("item_id"), opcional=True)
            if item_id and (item_id not in anteriores or item_id in vistos):
                raise ValueError("Item inválido para esta atividade.")
            if item_id:
                vistos.add(item_id)
        except ValueError as exc:
            erros[prefixo+"item_id"] = str(exc)
            continue
        anterior = anteriores.get(item_id)
        bloqueado = False
        try:
            pid = parse_id(linha.get("produto_base_id"))
            produto = db.session.get(ProdutoBase, pid)
            if produto is None:
                raise ValueError("Selecione um produto do catálogo.")
            bloqueado = (produto.status_sistema == _STATUS_BLOQUEADO or
                         produto.status_regulatorio == _STATUS_BLOQUEADO)
            item_dados["produto_base_id"] = pid
        except ValueError as exc:
            erros[prefixo+"produto_base_id"] = str(exc)
        try:
            item_dados["dose"] = validar_decimal(linha.get("dose"))
        except ValueError as exc:
            erros[prefixo+"dose"] = str(exc)
        unidade = str(linha.get("unidade_dose") or "").strip() or None
        item_dados["unidade_dose"] = unidade
        if unidade and len(unidade) > 20:
            erros[prefixo+"unidade_dose"] = "Use até 20 caracteres."
        if item_dados.get("dose") is not None and not unidade:
            erros[prefixo+"unidade_dose"] = "Informe a unidade da dose histórica."
        consumo, falhas = validar_consumo_custo(linha, existente=anterior,
            pode_criar_custo=has_permission("financeiro.create"),
            pode_editar_custo=has_permission("financeiro.edit"))
        item_dados.update(consumo)
        erros.update({prefixo+campo: msg for campo, msg in falhas.items()})
        if bloqueado and (anterior is None or any(
                getattr(anterior, campo) != valor for campo, valor in item_dados.items())):
            erros[prefixo+"produto_base_id"] = "Produtos bloqueados/históricos não podem ser utilizados em novos registros ou alterações."
        itens.append((anterior, item_dados))
    removidos = [item for iid, item in anteriores.items() if iid not in vistos]
    if not has_permission("financeiro.edit") and any(
            item.custo_total is not None or item.custo_unitario is not None for item in removidos):
        abort(403)
    return dados, itens, removidos, erros


def _auditar(acao, atividade, descricao):
    db.session.add(preparar_evento(acao, entidade="atividade_operacional",
        entidade_id=atividade.id, propriedade_id=atividade.gleba.propriedade_id,
        descricao=descricao, request=request))


def _mesmo_envio(atividade, dados, itens):
    if atividade.cancelado_em or atividade.criado_por_id != usuario_atual()["id"]:
        return False
    if any(getattr(atividade, campo) != valor for campo, valor in dados.items()):
        return False
    antigos = [i for i in atividade.itens if not i.cancelado_em]
    return len(antigos) == len(itens) and all(
        all(getattr(antigo, campo) == valor for campo, valor in valores.items())
        for antigo, (_, valores) in zip(antigos, itens))


@atividades_bp.route("/")
@login_required
@require_permission("atividades.view")
def index():
    propriedade = propriedade_atual()
    atividades = _query(propriedade).order_by(AtividadeOperacional.data_execucao.desc(),
                                            AtividadeOperacional.id.desc()).all()
    return render_template("atividades/list.html", atividades=atividades,
                           can_ver_custos=has_permission("financeiro.view"))


@atividades_bp.route("/nova", methods=["GET", "POST"])
@login_required
@require_permission("atividades.create")
@serializar_operacao("atividades.create")
def nova():
    propriedade = propriedade_atual()
    if request.method == "GET":
        return _formulario(propriedade)
    form = request.form.to_dict()
    linhas, erros = _linhas_form()
    try:
        chave = UUID(str(form.get("chave_envio", ""))).hex
    except (ValueError, AttributeError):
        chave = None
        erros["chave_envio"] = "Recarregue o formulário para iniciar um novo registro."
    dados, itens, _, falhas = _validar(propriedade, form, linhas)
    erros.update(falhas)
    if erros:
        return _formulario(propriedade, form=form, itens=linhas, erros=erros, status=400)
    anterior = AtividadeOperacional.query.filter_by(chave_envio=chave).first()
    if anterior is not None:
        autorizada = _query(propriedade).filter(AtividadeOperacional.id == anterior.id).first()
        if autorizada is None or not _mesmo_envio(anterior, dados, itens):
            abort(409)
        flash("Esta atividade já foi registrada; nenhum registro duplicado foi criado.", "info")
        return redirect(url_for("atividades.index"))
    atividade = AtividadeOperacional(**dados, chave_envio=chave,
                                     criado_por_id=usuario_atual()["id"])
    db.session.add(atividade)
    for _, valores in itens:
        atividade.itens.append(AtividadeItem(**valores))
    try:
        db.session.flush()
        _auditar("atividades.create", atividade, "Atividade registrada com seus itens")
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        anterior = _query(propriedade).filter(AtividadeOperacional.chave_envio == chave).first()
        if anterior is None or not _mesmo_envio(anterior, dados, itens):
            abort(409)
    flash("Atividade operacional registrada.", "success")
    return redirect(url_for("atividades.index"))


@atividades_bp.route("/<int:atividade_id>/editar", methods=["GET", "POST"])
@login_required
@require_permission("atividades.edit")
@serializar_operacao("atividades.edit")
def editar(atividade_id):
    propriedade = propriedade_atual()
    atividade = _atividade_ou_404(atividade_id, propriedade)
    if atividade.cancelado_em:
        abort(409)
    if request.method == "GET":
        form = {campo: getattr(atividade, campo) for campo in _CAMPOS_ATIVIDADE}
        linhas = []
        for item in atividade.itens:
            if item.cancelado_em:
                continue
            linha = {campo: getattr(item, campo) for campo in _CAMPOS_ITEM if campo != "item_id"}
            linha["item_id"] = item.id
            linha["origem_custo"] = item.origem_custo
            if not has_permission("financeiro.view"):
                for campo in CAMPOS_CUSTO:
                    linha.pop(campo, None)
            linhas.append(linha)
        return _formulario(propriedade, atividade=atividade, form=form, itens=linhas)
    form = request.form.to_dict()
    linhas, erros = _linhas_form()
    dados, itens, removidos, falhas = _validar(propriedade, form, linhas, atividade=atividade)
    erros.update(falhas)
    if erros:
        return _formulario(propriedade, atividade=atividade, form=form, itens=linhas,
                           erros=erros, status=400)
    agora, ator = iso_now(), usuario_atual()["id"]
    alterados = sorted(campo for campo, valor in dados.items() if getattr(atividade, campo) != valor)
    for campo, valor in dados.items():
        setattr(atividade, campo, valor)
    for anterior, valores in itens:
        if anterior is None:
            atividade.itens.append(AtividadeItem(**valores))
        else:
            for campo, valor in valores.items():
                setattr(anterior, campo, valor)
    for removido in removidos:
        removido.cancelado_em, removido.cancelado_por_id = agora, ator
    atividade.atualizado_em, atividade.atualizado_por_id = agora, ator
    _auditar("atividades.edit", atividade, "Atividade editada; campos: " +
             ", ".join(alterados + ["itens"]))
    db.session.commit()
    flash("Atividade operacional atualizada.", "success")
    return redirect(url_for("atividades.index"))


@atividades_bp.route("/<int:atividade_id>/cancelar", methods=["POST"])
@login_required
@require_permission("atividades.delete")
@serializar_operacao("atividades.delete")
def cancelar(atividade_id):
    propriedade = propriedade_atual()
    atividade = _atividade_ou_404(atividade_id, propriedade)
    if not atividade.cancelado_em:
        atividade.cancelado_em = iso_now()
        atividade.cancelado_por_id = usuario_atual()["id"]
        _auditar("atividades.cancel", atividade, "Atividade cancelada; histórico e itens preservados")
        db.session.commit()
    flash("Atividade cancelada. O histórico foi preservado.", "success")
    return redirect(url_for("atividades.index"))
