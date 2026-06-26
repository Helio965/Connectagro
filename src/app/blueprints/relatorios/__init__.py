"""Blueprint do módulo Relatórios (placeholder do MVP)."""
from flask import Blueprint

relatorios_bp = Blueprint(
    "relatorios", __name__,
    url_prefix="/relatorios",
)

from . import routes  # noqa: E402,F401
