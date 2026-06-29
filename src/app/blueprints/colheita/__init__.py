"""Blueprint do módulo Colheita do MVP."""
from flask import Blueprint

colheita_bp = Blueprint(
    "colheita", __name__,
    url_prefix="/colheita",
)

from . import routes  # noqa: E402,F401
