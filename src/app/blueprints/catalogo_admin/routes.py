"""Revisão global de propostas; não abre acesso operacional a outras origens."""
from flask import abort, flash, redirect, render_template, request, url_for
from sqlalchemy.exc import IntegrityError, OperationalError
from werkzeug.exceptions import Conflict

from ...extensions import db
from ...models import SolicitacaoCatalogo
from ...services.catalogo_governanca_service import decidir_solicitacao
from ...services.catalogo_local_service import ErroCatalogo, buscar_duplicacoes, ler_json_seguro
from ...services.operacionais_lock import _ocupado
from ...services.operacionais_service import parse_id
from ...utils.auth import login_required
from ...utils.permissions import require_permission
from . import catalogo_admin_bp


def _pedido(id):
    try:
        id = parse_id(id)
    except ValueError:
        abort(404)
    pedido = db.session.get(SolicitacaoCatalogo, id)
    if pedido is None:
        abort(404)
    return pedido


def _render(pedido, form=None, erro=None, status=200):
    try:
        conteudo = ler_json_seguro(pedido.conteudo_json)
    except ErroCatalogo as invalido:
        conteudo, erro, status = {}, invalido, 400
    duplicacoes = buscar_duplicacoes(conteudo.get("nome"), conteudo.get("classe")) if pedido.tipo == "inclusao" else []
    return render_template("catalogo_admin/detail.html", solicitacao=pedido, conteudo=conteudo,
        form=dict(form or {}), errors=erro.errors if erro else {}, duplicacoes=duplicacoes), status


@catalogo_admin_bp.route("/")
@login_required
@require_permission("catalogo.global.review")
def index():
    itens = SolicitacaoCatalogo.query.order_by(SolicitacaoCatalogo.solicitado_em.desc(), SolicitacaoCatalogo.id.desc()).all()
    return render_template("catalogo_admin/index.html", solicitacoes=itens)


@catalogo_admin_bp.route("/<int:id>")
@login_required
@require_permission("catalogo.global.review")
def detalhe(id):
    return _render(_pedido(id))


def _decidir(id, acao):
    pedido = _pedido(id)
    try:
        decidir_solicitacao(pedido.id, acao, request.form)
        db.session.commit()
    except ErroCatalogo as erro:
        db.session.rollback()
        return _render(pedido, request.form, erro, 400)
    except (IntegrityError, Conflict):
        db.session.rollback()
        return _render(pedido, request.form, ErroCatalogo({"formulario": "A origem ou a referência global mudou, ou o identificador já existe. Revise a proposta antes de decidir."}), 409)
    except OperationalError as erro:
        dialect = db.session.get_bind().dialect.name
        db.session.rollback()
        if not _ocupado(erro, dialect):
            raise
        return _render(pedido, request.form, ErroCatalogo({"formulario": "Outra decisão está em andamento. Recarregue e tente novamente."}), 409)
    finally:
        db.session.rollback()
    flash("Decisão administrativa registrada; ela não representa validação regulatória oficial.", "success")
    return redirect(url_for("catalogo_admin.detalhe", id=pedido.id))


@catalogo_admin_bp.route("/<int:id>/aprovar", methods=["POST"])
@login_required
@require_permission("catalogo.global.decide")
def aprovar(id):
    return _decidir(id, "aprovar")


@catalogo_admin_bp.route("/<int:id>/rejeitar", methods=["POST"])
@login_required
@require_permission("catalogo.global.decide")
def rejeitar(id):
    return _decidir(id, "rejeitar")
