from flask import Blueprint

catalogo_admin_bp = Blueprint("catalogo_admin", __name__, url_prefix="/catalogo/revisao")

from . import routes  # noqa: E402,F401
