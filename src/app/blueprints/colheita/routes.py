"""CRUD de Colheita — escopo: propriedade do usuário logado.

Cada registro de colheita vincula-se a uma associação Cultura↔Gleba
(`cultura_gleba`) cuja cultura pertence à propriedade atual.
"""
from collections import defaultdict

from flask import abort, flash, redirect, render_template, request, url_for

from ...extensions import db
from ...models import ColheitaRegistro, Cultura, CulturaGleba, Gleba
from ...models._helpers import iso_now
from ...utils.auth import login_required
from ...services.auditoria_service import registrar_sucesso
from ...utils.contexto import parse_float, propriedade_atual, vazio_para_none
from ...utils.permissions import require_permission
from . import colheita_bp


def _cultura_glebas_da_propriedade(propriedade):
    """Associações cultura↔gleba cuja cultura pertence à propriedade."""
    return (CulturaGleba.query
            .join(Cultura, CulturaGleba.cultura_id == Cultura.id)
            .filter(Cultura.propriedade_id == propriedade.id)
            .order_by(Cultura.nome, CulturaGleba.id)
            .all())


def _ids_cultura_gleba_validos(propriedade):
    return {cg.id for cg in _cultura_glebas_da_propriedade(propriedade)}


def _colheita_da_propriedade_ou_404(colheita_id, propriedade):
    colheita = (ColheitaRegistro.query
                .join(CulturaGleba, ColheitaRegistro.cultura_gleba_id == CulturaGleba.id)
                .join(Cultura, CulturaGleba.cultura_id == Cultura.id)
                .filter(ColheitaRegistro.id == colheita_id,
                        Cultura.propriedade_id == propriedade.id)
                .first())
    if colheita is None:
        abort(404)
    return colheita


def _opcoes_cultura_gleba(propriedade):
    """Lista de (id, rótulo 'Cultura — Gleba') para o select."""
    opcoes = []
    for cg in _cultura_glebas_da_propriedade(propriedade):
        opcoes.append((cg.id, f"{cg.cultura.nome} — {cg.gleba.nome}"))
    return opcoes


def _ler_e_validar_form(propriedade):
    """Lê/valida o formulário de colheita. Retorna (dados, erro)."""
    cg_raw = request.form.get("cultura_gleba_id") or ""
    data_colheita = vazio_para_none(request.form.get("data_colheita"))
    quantidade_raw = request.form.get("quantidade")

    if not cg_raw.isdigit() or int(cg_raw) not in _ids_cultura_gleba_validos(propriedade):
        return None, "Selecione uma associação cultura↔gleba válida."
    if not data_colheita:
        return None, "A data da colheita é obrigatória."

    quantidade = None
    if vazio_para_none(quantidade_raw) is not None:
        quantidade = parse_float(quantidade_raw)
        if quantidade is None or quantidade <= 0:
            return None, "A quantidade, se informada, deve ser um número maior que zero."

    return {
        "cultura_gleba_id": int(cg_raw),
        "data_colheita": data_colheita,
        "quantidade": quantidade,
        "unidade": vazio_para_none(request.form.get("unidade")),
        "qualidade": vazio_para_none(request.form.get("qualidade")),
        "observacao": vazio_para_none(request.form.get("observacao")),
    }, None


@colheita_bp.route("/")
@login_required
@require_permission("colheita.view")
def index():
    propriedade = propriedade_atual()
    ids_validos = _ids_cultura_gleba_validos(propriedade)
    registros = []
    if ids_validos:
        registros = (ColheitaRegistro.query
                     .filter(ColheitaRegistro.cultura_gleba_id.in_(ids_validos))
                     .order_by(ColheitaRegistro.data_colheita.desc(),
                               ColheitaRegistro.id.desc())
                     .all())
    # resumo simples: soma de quantidade por unidade (ignora sem qtd/unidade)
    soma_por_unidade = defaultdict(float)
    for r in registros:
        if r.quantidade and r.unidade:
            soma_por_unidade[r.unidade] += r.quantidade
    return render_template("colheita/list.html", registros=registros,
                           total=len(registros), soma_por_unidade=dict(soma_por_unidade))


@colheita_bp.route("/nova", methods=["GET", "POST"])
@login_required
@require_permission("colheita.create")
def nova():
    propriedade = propriedade_atual()
    opcoes = _opcoes_cultura_gleba(propriedade)
    if request.method == "POST":
        dados, erro = _ler_e_validar_form(propriedade)
        if erro:
            flash(erro, "error")
            return render_template("colheita/form.html", colheita=None,
                                   form=request.form, opcoes=opcoes,
                                   selecionado=None), 400
        registro = ColheitaRegistro(**dados)
        db.session.add(registro)
        db.session.commit()
        registrar_sucesso("colheita.create", entidade="colheita_registro",
                          entidade_id=registro.id, descricao="Colheita registrada",
                          propriedade_id=propriedade.id, request=request)
        flash("Colheita registrada.", "success")
        return redirect(url_for("colheita.index"))
    return render_template("colheita/form.html", colheita=None, form={},
                           opcoes=opcoes, selecionado=None)


@colheita_bp.route("/<int:colheita_id>/editar", methods=["GET", "POST"])
@login_required
@require_permission("colheita.edit")
def editar(colheita_id):
    propriedade = propriedade_atual()
    colheita = _colheita_da_propriedade_ou_404(colheita_id, propriedade)
    opcoes = _opcoes_cultura_gleba(propriedade)
    if request.method == "POST":
        dados, erro = _ler_e_validar_form(propriedade)
        if erro:
            flash(erro, "error")
            return render_template("colheita/form.html", colheita=colheita,
                                   form=request.form, opcoes=opcoes,
                                   selecionado=colheita.cultura_gleba_id), 400
        colheita.cultura_gleba_id = dados["cultura_gleba_id"]
        colheita.data_colheita = dados["data_colheita"]
        colheita.quantidade = dados["quantidade"]
        colheita.unidade = dados["unidade"]
        colheita.qualidade = dados["qualidade"]
        colheita.observacao = dados["observacao"]
        db.session.commit()
        registrar_sucesso("colheita.edit", entidade="colheita_registro",
                          entidade_id=colheita.id, descricao="Colheita editada",
                          propriedade_id=propriedade.id, request=request)
        flash("Colheita atualizada.", "success")
        return redirect(url_for("colheita.index"))
    return render_template("colheita/form.html", colheita=colheita, form=colheita,
                           opcoes=opcoes, selecionado=colheita.cultura_gleba_id)


@colheita_bp.route("/<int:colheita_id>/remover", methods=["POST"])
@login_required
@require_permission("colheita.delete")
def remover(colheita_id):
    propriedade = propriedade_atual()
    colheita = _colheita_da_propriedade_ou_404(colheita_id, propriedade)
    db.session.delete(colheita)
    db.session.commit()
    registrar_sucesso("colheita.delete", entidade="colheita_registro",
                      entidade_id=colheita_id, descricao="Colheita removida",
                      propriedade_id=propriedade.id, request=request)
    flash("Colheita removida.", "success")
    return redirect(url_for("colheita.index"))
