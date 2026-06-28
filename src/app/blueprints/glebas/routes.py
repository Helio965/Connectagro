"""Rotas do módulo Glebas (placeholder do MVP)."""
from flask import render_template

from . import glebas_bp
from ...utils.auth import login_required


@glebas_bp.route("/")
@login_required
def index():
    return render_template(
        "placeholders/modulo.html",
        modulo="Glebas",
        descricao="Cadastro e gestão das áreas/talhões.",
    )
