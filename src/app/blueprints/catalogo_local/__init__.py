from flask import Blueprint

catalogo_local_bp = Blueprint("catalogo_local", __name__, url_prefix="/catalogo/local")

from . import routes  # noqa: E402,F401
