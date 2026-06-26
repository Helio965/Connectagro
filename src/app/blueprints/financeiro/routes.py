"""Rotas do módulo Financeiro (placeholder do MVP)."""
from flask import render_template

from . import financeiro_bp


@financeiro_bp.route("/")
def index():
    return render_template(
        "placeholders/modulo.html",
        modulo="Financeiro",
        descricao="Registro de receitas e despesas.",
    )
