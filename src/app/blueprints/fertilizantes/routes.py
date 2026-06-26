"""Rotas do módulo Fertilizantes (placeholder do MVP)."""
from flask import render_template

from . import fertilizantes_bp


@fertilizantes_bp.route("/")
def index():
    return render_template(
        "placeholders/modulo.html",
        modulo="Fertilizantes",
        descricao="Consulta de fertilizantes do catálogo técnico.",
    )
