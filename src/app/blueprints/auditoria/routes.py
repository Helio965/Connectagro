"""Logs de auditoria — somente admin, escopo: propriedade atual (Fase 7.3).

Exibe logs de ações sensíveis da propriedade atual. Sem dashboard gráfico,
exportação de logs, retenção automática ou integração externa.
"""
from flask import render_template

from ...models.log_auditoria import LogAuditoria
from ...utils.auth import login_required
from ...utils.contexto import propriedade_atual
from ...utils.permissions import require_permission
from . import auditoria_bp


@auditoria_bp.route("/")
@login_required
@require_permission("auditoria.view")
def index():
    propriedade = propriedade_atual()
    logs = (LogAuditoria.query
            .filter_by(propriedade_id=propriedade.id)
            .order_by(LogAuditoria.id.desc())
            .limit(200)
            .all())
    return render_template("auditoria/list.html", logs=logs)
