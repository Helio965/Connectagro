"""Blueprint do módulo Dashboard do MVP."""
from flask import Blueprint

dashboard_bp = Blueprint(
    "dashboard", __name__,
)

from . import routes  # noqa: E402,F401
