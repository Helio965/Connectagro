"""Consulta de logs de auditoria — somente admin, escopo por propriedade."""
from flask import render_template, request

from ...services.auditoria_service import listar_logs
from ...utils.auth import login_required
from ...utils.contexto import propriedade_atual
from ...utils.permissions import require_permission
from . import auditoria_bp

LIMITE_LOGS = 100


@auditoria_bp.route("/")
@login_required
@require_permission("auditoria.view")
def index():
    propriedade = propriedade_atual()
    filtros = {
        "acao": request.args.get("acao", ""),
        "resultado": request.args.get("resultado", ""),
        "entidade": request.args.get("entidade", ""),
        "usuario_id": request.args.get("usuario_id", ""),
    }
    logs = listar_logs(propriedade, filtros=filtros, limite=LIMITE_LOGS)
    return render_template(
        "auditoria/list.html",
        logs=logs,
        filtros=filtros,
        propriedade=propriedade,
        limite=LIMITE_LOGS,
    )
