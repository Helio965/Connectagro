"""Rotas do módulo Mapa real (placeholder do MVP)."""
from flask import render_template

from . import mapa_bp


@mapa_bp.route("/")
def index():
    return render_template(
        "placeholders/modulo.html",
        modulo="Mapa real",
        descricao="Visualização das glebas em mapa.",
    )
