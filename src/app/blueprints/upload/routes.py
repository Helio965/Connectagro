"""Rotas do módulo Upload (placeholder do MVP)."""
from flask import render_template

from . import upload_bp
from ...utils.auth import login_required


@upload_bp.route("/")
@login_required
def index():
    return render_template(
        "placeholders/modulo.html",
        modulo="Upload",
        descricao="Envio e armazenamento de documentos/arquivos.",
    )
