"""Painel de Usuários — somente admin, escopo: propriedade atual (Fase 7.1).

Permite listar, criar (com senha temporária), editar nome/perfil/status e
inativar usuários vinculados à propriedade atual. Não há cadastro público,
remoção física nem painel de roles.
"""
from flask import abort, flash, redirect, render_template, request, url_for

from ...extensions import db
from ...models import Usuario, UsuarioPropriedade
from ...models._helpers import iso_now
from ...services.auditoria_service import registrar_sucesso
from ...utils.auth import gerar_hash_senha, login_required
from ...utils.contexto import propriedade_atual, vazio_para_none
from ...utils.permissions import PERFIS_OFICIAIS, require_permission
from . import usuarios_bp


def _usuario_da_propriedade_ou_404(usuario_id, propriedade):
    """Busca um usuário vinculado à propriedade atual ou retorna 404."""
    vinculo = UsuarioPropriedade.query.filter_by(
        usuario_id=usuario_id,
        propriedade_id=propriedade.id,
    ).first()
    if vinculo is None:
        abort(404)
    usuario = db.session.get(Usuario, usuario_id)
    if usuario is None:
        abort(404)
    return usuario, vinculo


@usuarios_bp.route("/")
@login_required
@require_permission("usuarios.view")
def index():
    propriedade = propriedade_atual()
    vinculos = (UsuarioPropriedade.query
                .filter_by(propriedade_id=propriedade.id)
                .order_by(UsuarioPropriedade.id)
                .all())
    usuarios = []
    for v in vinculos:
        u = db.session.get(Usuario, v.usuario_id)
        if u:
            usuarios.append({"usuario": u, "vinculo": v})
    return render_template("usuarios/list.html", usuarios=usuarios)


@usuarios_bp.route("/novo", methods=["GET", "POST"])
@login_required
@require_permission("usuarios.create")
def novo():
    propriedade = propriedade_atual()
    if request.method == "POST":
        nome = vazio_para_none(request.form.get("nome"))
        email = (request.form.get("email") or "").strip().lower()
        perfil = request.form.get("perfil", "trabalhador")
        senha = request.form.get("senha") or ""

        erros = []
        if not nome:
            erros.append("O nome é obrigatório.")
        if not email:
            erros.append("O e-mail é obrigatório.")
        if perfil not in PERFIS_OFICIAIS:
            erros.append("Perfil inválido.")
        if len(senha) < 6:
            erros.append("A senha deve ter ao menos 6 caracteres.")
        if email and Usuario.query.filter_by(email=email).first():
            erros.append("Já existe um usuário com esse e-mail.")

        if erros:
            for e in erros:
                flash(e, "error")
            return render_template("usuarios/form.html", usuario=None,
                                   form=request.form, perfis=PERFIS_OFICIAIS), 400

        usuario = Usuario(
            nome=nome,
            email=email,
            perfil=perfil,
            ativo=True,
            senha_hash=gerar_hash_senha(senha),
        )
        db.session.add(usuario)
        db.session.commit()

        from ...utils.auth import usuario_atual as _usr_atual
        admin = _usr_atual()
        db.session.add(UsuarioPropriedade(
            usuario_id=usuario.id,
            propriedade_id=propriedade.id,
            ativo=True,
            criado_por_id=admin["id"] if admin else None,
        ))
        db.session.commit()

        registrar_sucesso("usuarios.create", entidade="usuario",
                          entidade_id=usuario.id,
                          descricao="Usuário criado pelo painel",
                          propriedade_id=propriedade.id, request=request)
        flash("Usuário criado com sucesso.", "success")
        return redirect(url_for("usuarios.index"))

    return render_template("usuarios/form.html", usuario=None,
                           form={}, perfis=PERFIS_OFICIAIS)


@usuarios_bp.route("/<int:usuario_id>/editar", methods=["GET", "POST"])
@login_required
@require_permission("usuarios.edit")
def editar(usuario_id):
    propriedade = propriedade_atual()
    usuario, vinculo = _usuario_da_propriedade_ou_404(usuario_id, propriedade)

    if request.method == "POST":
        nome = vazio_para_none(request.form.get("nome"))
        perfil = request.form.get("perfil", usuario.perfil)
        ativo = bool(request.form.get("ativo"))

        erros = []
        if not nome:
            erros.append("O nome é obrigatório.")
        if perfil not in PERFIS_OFICIAIS:
            erros.append("Perfil inválido.")
        if erros:
            for e in erros:
                flash(e, "error")
            return render_template("usuarios/form.html", usuario=usuario,
                                   form=request.form, perfis=PERFIS_OFICIAIS), 400

        usuario.nome = nome
        usuario.perfil = perfil
        usuario.ativo = ativo
        usuario.atualizado_em = iso_now()
        vinculo.ativo = ativo
        vinculo.atualizado_em = iso_now()
        db.session.commit()

        registrar_sucesso("usuarios.edit", entidade="usuario",
                          entidade_id=usuario.id,
                          descricao="Usuário editado pelo painel",
                          propriedade_id=propriedade.id, request=request)
        flash("Usuário atualizado.", "success")
        return redirect(url_for("usuarios.index"))

    return render_template("usuarios/form.html", usuario=usuario,
                           form=usuario, perfis=PERFIS_OFICIAIS)


@usuarios_bp.route("/<int:usuario_id>/inativar", methods=["POST"])
@login_required
@require_permission("usuarios.deactivate")
def inativar(usuario_id):
    propriedade = propriedade_atual()
    usuario, vinculo = _usuario_da_propriedade_ou_404(usuario_id, propriedade)

    usuario.ativo = False
    usuario.atualizado_em = iso_now()
    vinculo.ativo = False
    vinculo.atualizado_em = iso_now()
    db.session.commit()

    registrar_sucesso("usuarios.deactivate", entidade="usuario",
                      entidade_id=usuario.id,
                      descricao="Usuário inativado pelo painel",
                      propriedade_id=propriedade.id, request=request)
    flash("Usuário inativado.", "success")
    return redirect(url_for("usuarios.index"))
