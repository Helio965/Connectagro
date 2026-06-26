"""Rotas do módulo Upload (placeholder do MVP)."""
from flask import render_template

from . import upload_bp


@upload_bp.route("/")
def index():
    return render_template(
        "placeholders/modulo.html",
        modulo="Upload",
        descricao="Envio e armazenamento de documentos/arquivos.",
    )
