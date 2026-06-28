"""Rotas do módulo IA simulada (placeholder do MVP)."""
from flask import render_template

from . import ia_bp
from ...utils.auth import login_required


@ia_bp.route("/")
@login_required
def index():
    return render_template(
        "placeholders/modulo.html",
        modulo="IA simulada",
        descricao="Apoio informativo por IA (simulada no MVP).",
    )
