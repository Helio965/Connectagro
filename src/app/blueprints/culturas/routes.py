"""Rotas do módulo Culturas (placeholder do MVP)."""
from flask import render_template

from . import culturas_bp
from ...utils.auth import login_required


@culturas_bp.route("/")
@login_required
def index():
    return render_template(
        "placeholders/modulo.html",
        modulo="Culturas",
        descricao="Cadastro e acompanhamento das culturas.",
    )
