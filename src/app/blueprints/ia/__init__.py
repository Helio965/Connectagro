"""Blueprint do módulo IA simulada (placeholder do MVP)."""
from flask import Blueprint

ia_bp = Blueprint(
    "ia", __name__,
    url_prefix="/ia",
)

from . import routes  # noqa: E402,F401
