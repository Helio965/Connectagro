"""Rotas do módulo Equipe (placeholder do MVP)."""
from flask import render_template

from . import equipe_bp


@equipe_bp.route("/")
def index():
    return render_template(
        "placeholders/modulo.html",
        modulo="Equipe",
        descricao="Gestão de membros e funções.",
    )
