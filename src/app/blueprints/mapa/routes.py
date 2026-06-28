"""Rotas do módulo Mapa real (placeholder do MVP)."""
from flask import render_template

from . import mapa_bp
from ...utils.auth import login_required


@mapa_bp.route("/")
@login_required
def index():
    return render_template(
        "placeholders/modulo.html",
        modulo="Mapa real",
        descricao="Visualização das glebas em mapa.",
    )
