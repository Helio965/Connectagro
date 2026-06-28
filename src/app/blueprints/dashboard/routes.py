"""Rotas do módulo Dashboard."""
from flask import render_template

from . import dashboard_bp
from ...services.dashboard_service import montar_dashboard_operacional
from ...utils.auth import login_required
from ...utils.contexto import propriedade_atual
from ...utils.formatters import formatar_area, formatar_moeda, formatar_numero, formatar_tamanho
from ...utils.permissions import require_permission


@dashboard_bp.route("/")
@login_required
@require_permission("dashboard.view")
def index():
    propriedade = propriedade_atual()
    dashboard = montar_dashboard_operacional(propriedade)
    return render_template(
        "dashboard/index.html",
        propriedade=propriedade,
        dashboard=dashboard,
        formatar_area=formatar_area,
        formatar_moeda=formatar_moeda,
        formatar_numero=formatar_numero,
        formatar_tamanho=formatar_tamanho,
    )
