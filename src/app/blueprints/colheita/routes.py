"""Rotas do módulo Colheita (placeholder do MVP)."""
from flask import render_template

from . import colheita_bp


@colheita_bp.route("/")
def index():
    return render_template(
        "placeholders/modulo.html",
        modulo="Colheita",
        descricao="Registro e acompanhamento da colheita.",
    )
