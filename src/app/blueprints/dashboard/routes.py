"""Rotas do módulo Dashboard."""
from flask import render_template

from . import dashboard_bp
from ...utils.auth import login_required


@dashboard_bp.route("/")
@login_required
def index():
    return render_template("dashboard/index.html")
