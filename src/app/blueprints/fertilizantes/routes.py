"""Rotas do módulo Fertilizantes (placeholder do MVP)."""
from flask import render_template

from . import fertilizantes_bp
from ...utils.auth import login_required


@fertilizantes_bp.route("/")
@login_required
def index():
    return render_template(
        "placeholders/modulo.html",
        modulo="Fertilizantes",
        descricao="Consulta de fertilizantes do catálogo técnico.",
    )
