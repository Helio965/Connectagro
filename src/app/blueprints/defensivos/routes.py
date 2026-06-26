"""Rotas do módulo Defensivos (placeholder do MVP)."""
from flask import render_template

from . import defensivos_bp


@defensivos_bp.route("/")
def index():
    return render_template(
        "placeholders/modulo.html",
        modulo="Defensivos",
        descricao="Consulta de defensivos do catálogo técnico.",
    )
