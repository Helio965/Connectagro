"""Blueprint do módulo Financeiro (placeholder do MVP)."""
from flask import Blueprint

financeiro_bp = Blueprint(
    "financeiro", __name__,
    url_prefix="/financeiro",
)

from . import routes  # noqa: E402,F401
