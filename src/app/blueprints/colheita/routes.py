"""Rotas do módulo Colheita (placeholder do MVP)."""
from flask import render_template

from . import colheita_bp
from ...utils.auth import login_required


@colheita_bp.route("/")
@login_required
def index():
    return render_template(
        "placeholders/modulo.html",
        modulo="Colheita",
        descricao="Registro e acompanhamento da colheita.",
    )
