"""Propriedade é o contexto; Gleba continua sendo a Área de Plantio."""
import math
import re

from flask import abort, flash, redirect, render_template, request, url_for
from sqlalchemy.exc import SQLAlchemyError

from ...extensions import db
from ...models import Propriedade
from ...models._helpers import iso_now
from ...services.auditoria_service import preparar_evento, registrar_negado, registrar_sucesso
from ...utils.auth import login_required, usuario_atual
from ...utils.contexto import (garantir_vinculo_usuario_propriedade, invalidar_contexto,
    propriedades_autorizadas, selecionar_propriedade, vazio_para_none, parse_float)
from ...utils.permissions import require_permission
from . import propriedades_bp


def _autorizada_ou_404(propriedade_id):
    prop = next((p for p in propriedades_autorizadas() if p.id == propriedade_id), None)
    if prop is None:
        abort(404)
    return prop


def _dados_form():
    nome = (request.form.get("nome") or "").strip()
    municipio = vazio_para_none(request.form.get("municipio"))
    uf = (request.form.get("uf") or "").strip().upper() or None
    area_raw = vazio_para_none(request.form.get("area_total_ha"))
    area = parse_float(area_raw)
    if not nome or len(nome) > 150:
        return None, "Informe um nome de até 150 caracteres."
    if municipio and len(municipio) > 120:
        return None, "O município deve ter até 120 caracteres."
    if uf and not re.fullmatch(r"[A-Z]{2}", uf):
        return None, "A UF deve conter duas letras."
    if area_raw is not None and (area is None or not math.isfinite(area) or area <= 0):
        return None, "A área total, se informada, deve ser finita e maior que zero."
    return dict(nome=nome, municipio=municipio, uf=uf, area_total_ha=area), None


@propriedades_bp.route("/")
@login_required
@require_permission("propriedades.view")
def index():
    return render_template("propriedades/list.html")


@propriedades_bp.route("/selecionar", methods=["GET", "POST"])
@login_required
@require_permission("propriedades.select")
def selecionar():
    if request.method == "GET":
        return render_template("propriedades/list.html", escolher=True)
    payload = request.get_json(silent=True) if request.is_json else None
    if request.is_json and not isinstance(payload, dict):
        abort(400)
    raw = request.form.get("propriedade_id") if not request.is_json else payload.get("propriedade_id")
    if isinstance(raw, str) and raw.isascii() and raw.isdigit() and len(raw) <= 19:
        raw = int(raw)
    prop = selecionar_propriedade(raw)
    if prop is None:
        registrar_negado("propriedades.selecao.negada", entidade="propriedade",
                         descricao="Tentativa de seleção não autorizada", request=request)
        abort(404)
    registrar_sucesso("propriedades.selecionada", entidade="propriedade", entidade_id=prop.id,
                      propriedade_id=prop.id, descricao="Contexto operacional selecionado", request=request)
    flash("Propriedade selecionada.", "success")
    return redirect(url_for("dashboard.index"))


@propriedades_bp.route("/nova", methods=["GET", "POST"])
@login_required
@require_permission("propriedades.create")
def nova():
    if request.method == "POST":
        dados, erro = _dados_form()
        if erro:
            flash(erro, "error")
            return render_template("propriedades/form.html", propriedade=None, form=request.form), 400
        ator = usuario_atual()
        prop = Propriedade(usuario_id=ator["id"], **dados)
        try:
            db.session.add(prop)
            db.session.flush()
            garantir_vinculo_usuario_propriedade(ator["id"], prop.id, ator["id"])
            db.session.add(preparar_evento("propriedades.create", entidade="propriedade",
                entidade_id=prop.id, propriedade_id=prop.id, usuario_id=ator["id"],
                descricao="Propriedade cadastrada explicitamente", request=request))
            db.session.commit()
        except SQLAlchemyError:
            db.session.rollback()
            flash("Não foi possível registrar a propriedade. Recarregue e tente novamente.", "error")
            return render_template("propriedades/form.html", propriedade=None, form=request.form), 409
        invalidar_contexto()
        flash("Propriedade cadastrada. Selecione o ambiente em que deseja trabalhar.", "success")
        return redirect(url_for("propriedades.detalhe", propriedade_id=prop.id))
    return render_template("propriedades/form.html", propriedade=None, form={})


@propriedades_bp.route("/<int:propriedade_id>")
@login_required
@require_permission("propriedades.view")
def detalhe(propriedade_id):
    return render_template("propriedades/detail.html", propriedade=_autorizada_ou_404(propriedade_id))


@propriedades_bp.route("/<int:propriedade_id>/editar", methods=["GET", "POST"])
@login_required
@require_permission("propriedades.edit")
def editar(propriedade_id):
    prop = _autorizada_ou_404(propriedade_id)
    if request.method == "POST":
        dados, erro = _dados_form()
        if erro:
            flash(erro, "error")
            return render_template("propriedades/form.html", propriedade=prop, form=request.form), 400
        for campo, valor in dados.items():
            setattr(prop, campo, valor)
        prop.atualizado_em = iso_now()
        try:
            db.session.add(preparar_evento("propriedades.edit", entidade="propriedade",
                entidade_id=prop.id, propriedade_id=prop.id, usuario_id=usuario_atual()["id"],
                descricao="Dados da propriedade atualizados", request=request))
            db.session.commit()
        except SQLAlchemyError:
            db.session.rollback()
            flash("Não foi possível atualizar a propriedade. Recarregue e tente novamente.", "error")
            return render_template("propriedades/form.html", propriedade=prop, form=request.form), 409
        invalidar_contexto()
        flash("Propriedade atualizada.", "success")
        return redirect(url_for("propriedades.detalhe", propriedade_id=prop.id))
    return render_template("propriedades/form.html", propriedade=prop, form=prop)


@propriedades_bp.route("/<int:propriedade_id>/remover", methods=["POST"])
@login_required
@require_permission("propriedades.edit")
def remover(propriedade_id):
    _autorizada_ou_404(propriedade_id)
    # Sem status/contrato de retenção aprovado, bloquear inclusive base vazia.
    flash("Exclusão bloqueada para preservar vínculos e históricos. A política de desativação e retenção ainda precisa ser definida.", "warning")
    return render_template("propriedades/detail.html", propriedade=_autorizada_ou_404(propriedade_id)), 409
