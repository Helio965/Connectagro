"""Blueprint de auditoria/logs administrativos do MVP ampliado."""
from flask import Blueprint

auditoria_bp = Blueprint("auditoria", __name__, url_prefix="/auditoria")

from . import routes  # noqa: E402,F401
