"""Blueprint do módulo Mapa real do MVP."""
from flask import Blueprint

mapa_bp = Blueprint(
    "mapa", __name__,
    url_prefix="/mapa",
)

from . import routes  # noqa: E402,F401
