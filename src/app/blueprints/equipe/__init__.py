"""Blueprint do módulo Equipe do MVP."""
from flask import Blueprint

equipe_bp = Blueprint(
    "equipe", __name__,
    url_prefix="/equipe",
)

from . import routes  # noqa: E402,F401
