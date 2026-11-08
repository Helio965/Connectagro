"""Gerenciamento explícito e seleção de propriedades autorizadas."""
from flask import Blueprint

propriedades_bp = Blueprint("propriedades", __name__, url_prefix="/propriedades")

from . import routes  # noqa: E402,F401
