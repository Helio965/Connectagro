"""Colheitas vinculadas ao contexto autorizado, com autoria e executor distintos."""
from collections import defaultdict
from decimal import Decimal
import math
from uuid import UUID, uuid4

from flask import abort, flash, redirect, render_template, request, url_for
from sqlalchemy.exc import IntegrityError

from ...extensions import db
from ...models import ColheitaRegistro, Cultura, CulturaGleba, Gleba
from ...models._helpers import iso_now
from ...services.auditoria_service import preparar_evento
from ...services.operacionais_lock import serializar_operacao
from ...services.operacionais_service import (
    opcoes_responsaveis, parse_id, validar_data_iso, validar_responsavel,
)
from ...utils.auth import login_required, usuario_atual
from ...utils.contexto import parse_float, propriedade_atual, vazio_para_none
from ...utils.permissions import require_permission
from . import colheita_bp


def _cultura_glebas_da_propriedade(propriedade):
    return (CulturaGleba.query
            .join(Cultura, CulturaGleba.cultura_id == Cultura.id)
            .join(Gleba, CulturaGleba.gleba_id == Gleba.id)
            .filter(Cultura.propriedade_id == propriedade.id,
                    Gleba.propriedade_id == propriedade.id)
            .order_by(Cultura.nome, CulturaGleba.id).all())


def _ids_cultura_gleba_validos(propriedade):
    return {cg.id for cg in _cultura_glebas_da_propriedade(propriedade)}


def _colheita_da_propriedade_ou_404(colheita_id, propriedade):
    try:
        colheita_id = parse_id(str(colheita_id))
    except ValueError:
        abort(404)
    colheita = (ColheitaRegistro.query
                .join(CulturaGleba, ColheitaRegistro.cultura_gleba_id == CulturaGleba.id)
                .join(Cultura, CulturaGleba.cultura_id == Cultura.id)
                .join(Gleba, CulturaGleba.gleba_id == Gleba.id)
                .filter(ColheitaRegistro.id == colheita_id,
                        Cultura.propriedade_id == propriedade.id,
                        Gleba.propriedade_id == propriedade.id).first())
    if colheita is None:
        abort(404)
    return colheita


def _opcoes_cultura_gleba(propriedade):
    return [(cg.id, f"{cg.cultura.nome} — {cg.gleba.nome}")
            for cg in _cultura_glebas_da_propriedade(propriedade)]


def _formulario(propriedade, colheita=None, *, form=None, errors=None, status=200):
    if form is None:
        form = ({c.name: getattr(colheita, c.name)
                 for c in ColheitaRegistro.__table__.columns} if colheita else
                {"chave_envio": str(uuid4())})
    else:
        form = dict(form)
    return render_template(
        "colheita/form.html", colheita=colheita, form=form,
        errors=errors or {}, erros=errors or {}, opcoes=_opcoes_cultura_gleba(propriedade),
        opcoes_responsaveis=opcoes_responsaveis(propriedade.id, registro=colheita),
        selecionado=form.get("cultura_gleba_id"),
        token_envio=form.get("chave_envio", "") if not colheita else "",
    ), status


def _chave_envio(raw, errors):
    raw = vazio_para_none(raw)
    if raw is None:
        return None
    try:
        if len(raw) > 36:
            raise ValueError
        return str(UUID(raw))
    except ValueError:
        errors["chave_envio"] = "Recarregue o formulário para obter uma identificação de envio válida."
        return None


def _ler_e_validar_form(propriedade, colheita=None):
    errors = {}
    dados = {}
    try:
        cg_id = parse_id(request.form.get("cultura_gleba_id"))
        if cg_id not in _ids_cultura_gleba_validos(propriedade):
            raise ValueError
        dados["cultura_gleba_id"] = cg_id
    except ValueError:
        errors["cultura_gleba_id"] = "Selecione uma associação cultura↔área de plantio válida."
    try:
        dados["data_colheita"] = validar_data_iso(request.form.get("data_colheita"))
    except ValueError:
        errors["data_colheita"] = "Informe uma data da colheita válida."
    raw = vazio_para_none(request.form.get("quantidade"))
    quantidade = parse_float(raw) if raw is not None and len(raw) <= 100 else None
    if raw is not None and (quantidade is None or not math.isfinite(quantidade) or quantidade <= 0):
        errors["quantidade"] = "A quantidade, se informada, deve ser um número finito maior que zero."
    dados["quantidade"] = quantidade
    for campo, limite in (("unidade", 20), ("qualidade", 80), ("observacao", 10000)):
        valor = vazio_para_none(request.form.get(campo))
        if valor is not None and len(valor) > limite:
            errors[campo] = f"Use no máximo {limite} caracteres."
        dados[campo] = valor
    responsavel_id, responsavel, erros_resp = validar_responsavel(
        propriedade.id,
        request.form.get("responsavel_usuario_id", getattr(colheita, "responsavel_usuario_id", None)),
        request.form.get("responsavel", getattr(colheita, "responsavel", None)),
        registro=colheita)
    dados.update(responsavel_usuario_id=responsavel_id, responsavel=responsavel)
    errors.update(erros_resp)
    if colheita is None:
        dados["chave_envio"] = _chave_envio(request.form.get("chave_envio"), errors)
    return dados, errors


def _reenvio(propriedade, dados):
    chave = dados.get("chave_envio")
    if not chave:
        return None
    anterior = ColheitaRegistro.query.filter_by(chave_envio=chave).first()
    if anterior is None:
        return None
    if (anterior.criado_por_id != usuario_atual()["id"]
            or anterior.cultura_gleba_id not in _ids_cultura_gleba_validos(propriedade)
            or any(getattr(anterior, campo) != valor for campo, valor in dados.items())):
        abort(409, description="Identificação de envio já utilizada. Recarregue o formulário.")
    return redirect(url_for("colheita.index"))


@colheita_bp.route("/")
@login_required
@require_permission("colheita.view")
def index():
    propriedade = propriedade_atual()
    ids_validos = _ids_cultura_gleba_validos(propriedade)
    registros = (ColheitaRegistro.query
                 .filter(ColheitaRegistro.cultura_gleba_id.in_(ids_validos))
                 .order_by(ColheitaRegistro.data_colheita.desc(), ColheitaRegistro.id.desc())
                 .all()) if ids_validos else []
    # Somente quantidades finitas, agrupadas pela unidade informada, sem conversão.
    soma_por_unidade = defaultdict(Decimal)
    for r in registros:
        if r.quantidade and r.unidade and math.isfinite(r.quantidade):
            soma_por_unidade[r.unidade] += Decimal(str(r.quantidade))
    return render_template("colheita/list.html", registros=registros,
                           total=len(registros), soma_por_unidade=dict(soma_por_unidade))


@colheita_bp.route("/nova", methods=["GET", "POST"])
@login_required
@require_permission("colheita.create")
@serializar_operacao("colheita.create")
def nova():
    propriedade = propriedade_atual()
    if request.method == "GET":
        return _formulario(propriedade)
    dados, errors = _ler_e_validar_form(propriedade)
    if errors:
        flash("Revise os campos indicados antes de salvar.", "error")
        return _formulario(propriedade, form=request.form, errors=errors, status=400)
    repetido = _reenvio(propriedade, dados)
    if repetido is not None:
        return repetido
    registro = ColheitaRegistro(criado_por_id=usuario_atual()["id"], **dados)
    db.session.add(registro)
    try:
        db.session.flush()
        db.session.add(preparar_evento(
            "colheita.create", entidade="colheita_registro", entidade_id=registro.id,
            descricao="Colheita registrada", propriedade_id=propriedade.id, request=request))
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        repetido = _reenvio(propriedade, dados)
        if repetido is not None:
            return repetido
        abort(409, description="O registro mudou durante o envio. Recarregue e tente novamente.")
    flash("Colheita registrada.", "success")
    return redirect(url_for("colheita.index"))


@colheita_bp.route("/<int:colheita_id>/editar", methods=["GET", "POST"])
@login_required
@require_permission("colheita.edit")
@serializar_operacao("colheita.edit")
def editar(colheita_id):
    propriedade = propriedade_atual()
    colheita = _colheita_da_propriedade_ou_404(colheita_id, propriedade)
    if request.method == "GET":
        return _formulario(propriedade, colheita)
    dados, errors = _ler_e_validar_form(propriedade, colheita)
    if errors:
        flash("Revise os campos indicados antes de salvar.", "error")
        return _formulario(propriedade, colheita, form=request.form, errors=errors, status=400)
    alterados = [campo for campo, valor in dados.items() if getattr(colheita, campo) != valor]
    for campo, valor in dados.items():
        setattr(colheita, campo, valor)
    colheita.atualizado_por_id = usuario_atual()["id"]
    colheita.atualizado_em = iso_now()
    db.session.add(preparar_evento(
        "colheita.edit", entidade="colheita_registro", entidade_id=colheita.id,
        descricao="Colheita editada; campos: " + ", ".join(alterados),
        propriedade_id=propriedade.id, request=request))
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        abort(409, description="O registro mudou durante a edição. Recarregue e tente novamente.")
    flash("Colheita atualizada.", "success")
    return redirect(url_for("colheita.index"))


@colheita_bp.route("/<int:colheita_id>/remover", methods=["POST"])
@login_required
@require_permission("colheita.delete")
@serializar_operacao("colheita.delete")
def remover(colheita_id):
    propriedade = propriedade_atual()
    colheita = _colheita_da_propriedade_ou_404(colheita_id, propriedade)
    db.session.delete(colheita)
    db.session.add(preparar_evento(
        "colheita.delete", entidade="colheita_registro", entidade_id=colheita_id,
        descricao="Colheita removida", propriedade_id=propriedade.id, request=request))
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        abort(409, description="Colheita possui dependências e não pode ser removida.")
    flash("Colheita removida.", "success")
    return redirect(url_for("colheita.index"))
