"""Rotas do módulo Defensivos (placeholder do MVP)."""
from flask import render_template

from . import defensivos_bp
from ...utils.auth import login_required


@defensivos_bp.route("/")
@login_required
def index():
    return render_template(
        "placeholders/modulo.html",
        modulo="Defensivos",
        descricao="Consulta de defensivos do catálogo técnico.",
    )
