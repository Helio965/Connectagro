"""Rotas do módulo Relatórios (placeholder do MVP)."""
from flask import render_template

from . import relatorios_bp


@relatorios_bp.route("/")
def index():
    return render_template(
        "placeholders/modulo.html",
        modulo="Relatórios",
        descricao="Geração de relatórios operacionais e financeiros.",
    )
