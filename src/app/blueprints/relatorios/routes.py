"""Rotas do módulo Relatórios (placeholder do MVP)."""
from flask import render_template

from . import relatorios_bp
from ...utils.auth import login_required


@relatorios_bp.route("/")
@login_required
def index():
    return render_template(
        "placeholders/modulo.html",
        modulo="Relatórios",
        descricao="Geração de relatórios operacionais e financeiros.",
    )
