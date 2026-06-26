"""Blueprint do módulo Defensivos (placeholder do MVP)."""
from flask import Blueprint

defensivos_bp = Blueprint(
    "defensivos", __name__,
    url_prefix="/defensivos",
)

from . import routes  # noqa: E402,F401
