"""Blueprint do módulo Auditoria do MVP ampliado (Fase 7.3)."""
from flask import Blueprint

auditoria_bp = Blueprint(
    "auditoria", __name__,
    url_prefix="/auditoria",
)

from . import routes  # noqa: E402,F401
