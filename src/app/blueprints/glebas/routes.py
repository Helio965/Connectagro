"""CRUD de Glebas (áreas/talhões) — escopo: propriedade do usuário logado."""
from flask import abort, flash, redirect, render_template, request, url_for

from ...extensions import db
from ...models import Gleba
from ...models._helpers import iso_now
from ...utils.auth import login_required
from ...services.auditoria_service import registrar_sucesso
from ...utils.contexto import parse_float, propriedade_atual, vazio_para_none
from ...utils.permissions import require_permission
from . import glebas_bp


def _gleba_da_propriedade_ou_404(gleba_id, propriedade):
    gleba = Gleba.query.filter_by(id=gleba_id, propriedade_id=propriedade.id).first()
    if gleba is None:
        abort(404)
    return gleba


@glebas_bp.route("/")
@login_required
@require_permission("glebas.view")
def index():
    propriedade = propriedade_atual()
    glebas = (Gleba.query
              .filter_by(propriedade_id=propriedade.id)
              .order_by(Gleba.nome)
              .all())
    return render_template("glebas/list.html", glebas=glebas)


@glebas_bp.route("/nova", methods=["GET", "POST"])
@login_required
@require_permission("glebas.create")
def nova():
    propriedade = propriedade_atual()
    if request.method == "POST":
        nome = vazio_para_none(request.form.get("nome"))
        if not nome:
            flash("O nome da gleba é obrigatório.", "error")
            return render_template("glebas/form.html", gleba=None,
                                   form=request.form), 400
        gleba = Gleba(
            propriedade_id=propriedade.id,
            nome=nome,
            area_ha=parse_float(request.form.get("area_ha")),
            latitude=parse_float(request.form.get("latitude")),
            longitude=parse_float(request.form.get("longitude")),
            tipo_solo=vazio_para_none(request.form.get("tipo_solo")),
            observacoes=vazio_para_none(request.form.get("observacoes")),
        )
        db.session.add(gleba)
        db.session.commit()
        registrar_sucesso("glebas.create", entidade="gleba", entidade_id=gleba.id,
                          descricao="Gleba criada", propriedade_id=propriedade.id,
                          request=request)
        flash("Gleba criada com sucesso.", "success")
        return redirect(url_for("glebas.index"))
    return render_template("glebas/form.html", gleba=None, form={})


@glebas_bp.route("/<int:gleba_id>/editar", methods=["GET", "POST"])
@login_required
@require_permission("glebas.edit")
def editar(gleba_id):
    propriedade = propriedade_atual()
    gleba = _gleba_da_propriedade_ou_404(gleba_id, propriedade)
    if request.method == "POST":
        nome = vazio_para_none(request.form.get("nome"))
        if not nome:
            flash("O nome da gleba é obrigatório.", "error")
            return render_template("glebas/form.html", gleba=gleba,
                                   form=request.form), 400
        gleba.nome = nome
        gleba.area_ha = parse_float(request.form.get("area_ha"))
        gleba.latitude = parse_float(request.form.get("latitude"))
        gleba.longitude = parse_float(request.form.get("longitude"))
        gleba.tipo_solo = vazio_para_none(request.form.get("tipo_solo"))
        gleba.observacoes = vazio_para_none(request.form.get("observacoes"))
        gleba.atualizado_em = iso_now()
        db.session.commit()
        registrar_sucesso("glebas.edit", entidade="gleba", entidade_id=gleba.id,
                          descricao="Gleba editada", propriedade_id=propriedade.id,
                          request=request)
        flash("Gleba atualizada.", "success")
        return redirect(url_for("glebas.index"))
    return render_template("glebas/form.html", gleba=gleba, form=gleba)


@glebas_bp.route("/<int:gleba_id>/remover", methods=["POST"])
@login_required
@require_permission("glebas.delete")
def remover(gleba_id):
    propriedade = propriedade_atual()
    gleba = _gleba_da_propriedade_ou_404(gleba_id, propriedade)
    # Remove vínculos cultura-gleba dependentes antes de excluir a gleba.
    for cg in list(gleba.cultura_glebas):
        db.session.delete(cg)
    db.session.delete(gleba)
    db.session.commit()
    registrar_sucesso("glebas.delete", entidade="gleba", entidade_id=gleba_id,
                      descricao="Gleba removida", propriedade_id=propriedade.id,
                      request=request)
    flash("Gleba removida.", "success")
    return redirect(url_for("glebas.index"))
