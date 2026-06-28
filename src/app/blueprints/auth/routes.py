"""Rotas de autenticação (login/logout) do ConnectAgro."""
from flask import flash, redirect, render_template, request, url_for

from ...models import Usuario
from ...utils.auth import (
    is_authenticated,
    login_usuario,
    logout_usuario,
    verificar_senha,
)
from . import auth_bp


@auth_bp.route("/")
def index():
    """Raiz do módulo: redireciona para a tela de login."""
    return redirect(url_for("auth.login"))


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    # Já autenticado: vai direto ao dashboard.
    if is_authenticated():
        return redirect(url_for("dashboard.index"))

    if request.method == "POST":
        email = (request.form.get("email") or "").strip().lower()
        senha = request.form.get("senha") or ""

        usuario = Usuario.query.filter_by(email=email).first()

        # Mensagem genérica para credenciais inválidas (não vaza detalhes).
        if usuario is None or not verificar_senha(usuario.senha_hash, senha):
            flash("E-mail ou senha inválidos.", "error")
            return render_template("auth/login.html"), 401

        if not usuario.ativo:
            flash("Usuário inativo. Procure o administrador.", "error")
            return render_template("auth/login.html"), 403

        login_usuario(usuario)
        flash(f"Bem-vindo(a), {usuario.nome}.", "success")
        return redirect(url_for("dashboard.index"))

    return render_template("auth/login.html")


@auth_bp.route("/logout")
def logout():
    logout_usuario()
    flash("Sessão encerrada.", "success")
    return redirect(url_for("auth.login"))
