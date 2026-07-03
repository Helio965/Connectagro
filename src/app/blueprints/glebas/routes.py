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

STATUS_GLEBA_VALIDOS = ("ativa", "em_preparo", "em_cultivo", "pousio", "inativa")


def _gleba_da_propriedade_ou_404(gleba_id, propriedade):
    gleba = Gleba.query.filter_by(id=gleba_id, propriedade_id=propriedade.id).first()
    if gleba is None:
        abort(404)
    return gleba


def _ler_e_validar_form():
    nome = vazio_para_none(request.form.get("nome"))
    area_ha = parse_float(request.form.get("area_ha"))
    status = request.form.get("status") or "ativa"

    if not nome:
        return None, "O nome da propriedade é obrigatório."
    if area_ha is None or area_ha <= 0:
        return None, "A área da propriedade deve ser informada e maior que zero."
    if status not in STATUS_GLEBA_VALIDOS:
        status = "ativa"

    return {
        "nome": nome,
        "area_ha": area_ha,
        "tipo_solo": vazio_para_none(request.form.get("tipo_solo")),
        "status": status,
        "observacoes": vazio_para_none(request.form.get("observacoes")),
    }, None


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
        dados, erro = _ler_e_validar_form()
        if erro:
            flash(erro, "error")
            return render_template("glebas/form.html", gleba=None,
                                   form=request.form,
                                   status_validos=STATUS_GLEBA_VALIDOS), 400
        gleba = Gleba(
            propriedade_id=propriedade.id,
            **dados,
        )
        db.session.add(gleba)
        db.session.commit()
        registrar_sucesso("glebas.create", entidade="propriedade", entidade_id=gleba.id,
                          descricao="Propriedade criada", propriedade_id=propriedade.id,
                          request=request)
        flash("Propriedade cadastrada com sucesso.", "success")
        return redirect(url_for("glebas.index"))
    return render_template("glebas/form.html", gleba=None, form={"status": "ativa"},
                           status_validos=STATUS_GLEBA_VALIDOS)


@glebas_bp.route("/<int:gleba_id>/editar", methods=["GET", "POST"])
@login_required
@require_permission("glebas.edit")
def editar(gleba_id):
    propriedade = propriedade_atual()
    gleba = _gleba_da_propriedade_ou_404(gleba_id, propriedade)
    if request.method == "POST":
        dados, erro = _ler_e_validar_form()
        if erro:
            flash(erro, "error")
            return render_template("glebas/form.html", gleba=gleba,
                                   form=request.form,
                                   status_validos=STATUS_GLEBA_VALIDOS), 400
        gleba.nome = dados["nome"]
        gleba.area_ha = dados["area_ha"]
        gleba.tipo_solo = dados["tipo_solo"]
        gleba.status = dados["status"]
        gleba.observacoes = dados["observacoes"]
        gleba.atualizado_em = iso_now()
        db.session.commit()
        registrar_sucesso("glebas.edit", entidade="propriedade", entidade_id=gleba.id,
                          descricao="Propriedade editada", propriedade_id=propriedade.id,
                          request=request)
        flash("Propriedade atualizada com sucesso.", "success")
        return redirect(url_for("glebas.index"))
    return render_template("glebas/form.html", gleba=gleba, form=gleba,
                           status_validos=STATUS_GLEBA_VALIDOS)


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
    registrar_sucesso("glebas.delete", entidade="propriedade", entidade_id=gleba_id,
                      descricao="Propriedade removida", propriedade_id=propriedade.id,
                      request=request)
    flash("Propriedade excluída com sucesso.", "success")
    return redirect(url_for("glebas.index"))
