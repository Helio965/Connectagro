"""Rotas do módulo Login (placeholder do MVP)."""
from flask import render_template

from . import auth_bp


@auth_bp.route("/")
def index():
    return render_template(
        "placeholders/modulo.html",
        modulo="Login",
        descricao="Autenticação e controle de acesso.",
    )
