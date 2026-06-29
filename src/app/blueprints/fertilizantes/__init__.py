"""Blueprint do módulo Fertilizantes do MVP."""
from flask import Blueprint

fertilizantes_bp = Blueprint(
    "fertilizantes", __name__,
    url_prefix="/fertilizantes",
)

from . import routes  # noqa: E402,F401
