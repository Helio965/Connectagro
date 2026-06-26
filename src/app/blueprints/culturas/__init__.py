"""Blueprint do módulo Culturas (placeholder do MVP)."""
from flask import Blueprint

culturas_bp = Blueprint(
    "culturas", __name__,
    url_prefix="/culturas",
)

from . import routes  # noqa: E402,F401
