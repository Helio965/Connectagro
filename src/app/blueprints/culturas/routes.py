"""Rotas do módulo Culturas (placeholder do MVP)."""
from flask import render_template

from . import culturas_bp


@culturas_bp.route("/")
def index():
    return render_template(
        "placeholders/modulo.html",
        modulo="Culturas",
        descricao="Cadastro e acompanhamento das culturas.",
    )
