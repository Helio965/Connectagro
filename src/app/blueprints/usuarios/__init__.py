"""Blueprint do painel de usuários do MVP ampliado."""
from flask import Blueprint

usuarios_bp = Blueprint("usuarios", __name__, url_prefix="/usuarios")

from . import routes  # noqa: E402,F401
