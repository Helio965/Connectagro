"""Registros gerais de atividades agrícolas."""
from flask import Blueprint

atividades_bp = Blueprint("atividades", __name__, url_prefix="/atividades")

from . import routes  # noqa: E402,F401
