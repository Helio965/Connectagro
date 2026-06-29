"""Blueprint do módulo Financeiro do MVP."""
from flask import Blueprint

financeiro_bp = Blueprint(
    "financeiro", __name__,
    url_prefix="/financeiro",
)

from . import routes  # noqa: E402,F401
