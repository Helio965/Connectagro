"""Blueprint do módulo Glebas (placeholder do MVP)."""
from flask import Blueprint

glebas_bp = Blueprint(
    "glebas", __name__,
    url_prefix="/glebas",
)

from . import routes  # noqa: E402,F401
