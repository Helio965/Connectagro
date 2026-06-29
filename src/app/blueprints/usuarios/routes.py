"""Painel de usuários internos da propriedade."""
from flask import abort, flash, redirect, render_template, request, url_for

from ...services.usuarios_service import (
    criar_usuario_da_propriedade,
    editar_usuario_da_propriedade,
    inativar_usuario_da_propriedade,
    listar_usuarios_da_propriedade,
    obter_vinculo_usuario,
)
from ...utils.auth import login_required, usuario_atual
from ...utils.contexto import propriedade_atual
from ...utils.permissions import PERFIS_OFICIAIS, require_permission
from . import usuarios_bp


def _vinculo_ou_404(usuario_id, propriedade):
    vinculo = obter_vinculo_usuario(propriedade, usuario_id)
    if vinculo is None:
        abort(404)
    return vinculo


@usuarios_bp.route("/")
@login_required
@require_permission("usuarios.view")
def index():
    propriedade = propriedade_atual()
    vinculos = listar_usuarios_da_propriedade(propriedade)
    return render_template("usuarios/list.html", vinculos=vinculos,
                           propriedade=propriedade)


@usuarios_bp.route("/novo", methods=["GET", "POST"])
@login_required
@require_permission("usuarios.create")
def novo():
    propriedade = propriedade_atual()
    if request.method == "POST":
        usuario, erros = criar_usuario_da_propriedade(
            propriedade,
            request.form,
            usuario_atual()["id"],
        )
        if erros:
            for erro in erros:
                flash(erro, "error")
            return render_template(
                "usuarios/form.html",
                usuario=None,
                form=request.form,
                perfis=PERFIS_OFICIAIS,
            ), 400
        flash(f"Usuário {usuario.email} criado e vinculado à propriedade.", "success")
        return redirect(url_for("usuarios.index"))
    return render_template(
        "usuarios/form.html",
        usuario=None,
        form={"ativo": True},
        perfis=PERFIS_OFICIAIS,
    )


@usuarios_bp.route("/<int:usuario_id>/editar", methods=["GET", "POST"])
@login_required
@require_permission("usuarios.edit")
def editar(usuario_id):
    propriedade = propriedade_atual()
    vinculo = _vinculo_ou_404(usuario_id, propriedade)
    usuario = vinculo.usuario
    if request.method == "POST":
        erros = editar_usuario_da_propriedade(propriedade, vinculo, request.form)
        if erros:
            for erro in erros:
                flash(erro, "error")
            form = dict(request.form)
            form["email"] = usuario.email
            return render_template(
                "usuarios/form.html",
                usuario=usuario,
                form=form,
                perfis=PERFIS_OFICIAIS,
            ), 400
        flash("Usuário atualizado.", "success")
        return redirect(url_for("usuarios.index"))
    return render_template(
        "usuarios/form.html",
        usuario=usuario,
        form=usuario,
        perfis=PERFIS_OFICIAIS,
    )


@usuarios_bp.route("/<int:usuario_id>/inativar", methods=["POST"])
@login_required
@require_permission("usuarios.deactivate")
def inativar(usuario_id):
    propriedade = propriedade_atual()
    vinculo = _vinculo_ou_404(usuario_id, propriedade)
    erros = inativar_usuario_da_propriedade(propriedade, vinculo)
    if erros:
        for erro in erros:
            flash(erro, "error")
        vinculos = listar_usuarios_da_propriedade(propriedade)
        return render_template(
            "usuarios/list.html",
            vinculos=vinculos,
            propriedade=propriedade,
        ), 400
    flash("Usuário inativado.", "success")
    return redirect(url_for("usuarios.index"))
