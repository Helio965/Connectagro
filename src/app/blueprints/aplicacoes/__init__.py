"""Blueprint do módulo Aplicações de Insumo (registro operacional do MVP)."""
from flask import Blueprint

aplicacoes_bp = Blueprint(
    "aplicacoes", __name__,
    url_prefix="/aplicacoes",
)

from . import routes  # noqa: E402,F401
