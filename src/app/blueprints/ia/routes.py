"""Rotas do módulo IA simulada (placeholder do MVP)."""
from flask import render_template

from . import ia_bp


@ia_bp.route("/")
def index():
    return render_template(
        "placeholders/modulo.html",
        modulo="IA simulada",
        descricao="Apoio informativo por IA (simulada no MVP).",
    )
