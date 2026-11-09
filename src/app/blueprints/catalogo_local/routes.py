"""Catálogo privado da Propriedade ativa; solicitações não publicam produtos."""
from uuid import uuid4

from flask import abort, flash, redirect, render_template, request, url_for
from sqlalchemy.exc import IntegrityError
from werkzeug.exceptions import Conflict

from ...extensions import db
from ...models import CatalogoRevisao, ProdutoBase, ProdutoLocal, ProdutoPersonalizacao, SolicitacaoCatalogo
from ...models._helpers import iso_now
from ...services.catalogo_local_service import (CAMPOS_LOCAL, CAMPOS_PERSONALIZACAO,
    ErroCatalogo, alterar_estado, auditar, conferir_formulario, ler_json_seguro,
    proposta_padrao, salvar_local, salvar_personalizacao, solicitar)
from ...services.operacionais_lock import serializar_operacao
from ...services.operacionais_service import parse_id
from ...utils.auth import login_required, usuario_atual
from ...utils.contexto import propriedade_atual
from ...utils.permissions import has_permission, require_permission
from . import catalogo_local_bp


def _id(valor):
    try:
        return parse_id(valor)
    except ValueError:
        abort(404)


def _local(produto_id):
    item = ProdutoLocal.query.filter_by(id=_id(produto_id), propriedade_id=propriedade_atual().id).first()
    if item is None:
        abort(404)
    return item


def _personalizacao(id):
    item = ProdutoPersonalizacao.query.filter_by(id=_id(id), propriedade_id=propriedade_atual().id).first()
    if item is None:
        abort(404)
    return item


def _pedido(id):
    item = SolicitacaoCatalogo.query.filter_by(id=_id(id), propriedade_id=propriedade_atual().id).first()
    if item is None:
        abort(404)
    return item


def _render_form(modo, registro=None, produto_global=None, form=None, erro=None, status=200):
    if form is None:
        campos = CAMPOS_LOCAL if modo == "local" else CAMPOS_PERSONALIZACAO
        form = {c: getattr(registro, c) for c in campos} if registro else {}
        if registro:
            form["versao"] = registro.versao
        elif modo == "local":
            form["chave_envio"] = uuid4().hex
    return render_template("catalogo_local/form.html", modo=modo, registro=registro,
        produto_global=produto_global, form=dict(form), errors=erro.errors if erro else {},
        duplicacoes=erro.duplicacoes if erro else []), status


def _conflito():
    return ErroCatalogo({"formulario": "Os dados mudaram ou este envio já foi utilizado. Recarregue o registro antes de continuar."})


def _validar_acao_form(permitidos):
    try:
        conferir_formulario(request.form, permitidos)
    except ErroCatalogo as erro:
        flash(str(erro), "error")
        abort(400)


@catalogo_local_bp.route("/")
@login_required
@require_permission("catalogo.view")
def index():
    pid = propriedade_atual().id
    return render_template("catalogo_local/index.html",
        produtos_locais=ProdutoLocal.query.filter_by(propriedade_id=pid).order_by(ProdutoLocal.nome, ProdutoLocal.id).all(),
        personalizacoes=ProdutoPersonalizacao.query.filter_by(propriedade_id=pid).order_by(ProdutoPersonalizacao.id).all())


@catalogo_local_bp.route("/novo", methods=["GET", "POST"])
@login_required
@require_permission("catalogo.local.create")
@serializar_operacao("catalogo.local.create")
def nova():
    if request.method == "GET":
        return _render_form("local")
    try:
        registro = salvar_local(propriedade_atual(), request.form)
        db.session.commit()
    except ErroCatalogo as erro:
        return _render_form("local", form=request.form, erro=erro, status=400)
    except (IntegrityError, Conflict):
        db.session.rollback()
        return _render_form("local", form=request.form, erro=_conflito(), status=409)
    flash("Produto local registrado nesta propriedade.", "success")
    return redirect(url_for("catalogo_local.detalhe", produto_id=registro.id))


@catalogo_local_bp.route("/<int:produto_id>")
@login_required
@require_permission("catalogo.view")
def detalhe(produto_id):
    return render_template("catalogo_local/detail.html", registro=_local(produto_id))


@catalogo_local_bp.route("/<int:produto_id>/editar", methods=["GET", "POST"])
@login_required
@require_permission("catalogo.local.edit")
@serializar_operacao("catalogo.local.edit")
def editar(produto_id):
    registro = _local(produto_id)
    if request.method == "GET":
        return _render_form("local", registro)
    try:
        salvar_local(propriedade_atual(), request.form, registro)
        db.session.commit()
    except ErroCatalogo as erro:
        return _render_form("local", registro, form=request.form, erro=erro, status=400)
    except (IntegrityError, Conflict):
        db.session.rollback()
        return _render_form("local", registro, form=request.form, erro=_conflito(), status=409)
    flash("Produto local atualizado; versão anterior preservada.", "success")
    return redirect(url_for("catalogo_local.detalhe", produto_id=registro.id))


def _estado_local(produto_id, ativo):
    registro = _local(produto_id)
    _validar_acao_form({"versao"})
    alterar_estado(registro, ativo, request.form.get("versao"))
    db.session.commit()
    flash("Situação local atualizada; histórico preservado.", "success")
    return redirect(url_for("catalogo_local.detalhe", produto_id=registro.id))


@catalogo_local_bp.route("/<int:produto_id>/inativar", methods=["POST"])
@login_required
@require_permission("catalogo.local.edit")
@serializar_operacao("catalogo.local.edit")
def inativar(produto_id):
    return _estado_local(produto_id, False)


@catalogo_local_bp.route("/<int:produto_id>/reativar", methods=["POST"])
@login_required
@require_permission("catalogo.local.edit")
@serializar_operacao("catalogo.local.edit")
def reativar(produto_id):
    return _estado_local(produto_id, True)


@catalogo_local_bp.route("/personalizar/<int:produto_id>", methods=["GET", "POST"])
@login_required
@require_permission("catalogo.view")
@serializar_operacao("catalogo.view")
def personalizar(produto_id):
    produto = db.session.get(ProdutoBase, _id(produto_id))
    if produto is None:
        abort(404)
    propriedade = propriedade_atual()
    registro = ProdutoPersonalizacao.query.filter_by(
        propriedade_id=propriedade.id, produto_base_id=produto.id).first()
    permissao = "catalogo.personalizar.edit" if registro else "catalogo.personalizar.create"
    if not has_permission(permissao):
        abort(403)
    if request.method == "GET":
        return _render_form("personalizacao", registro, produto)
    try:
        salvar_personalizacao(propriedade, produto, request.form, registro)
        db.session.commit()
    except ErroCatalogo as erro:
        return _render_form("personalizacao", registro, produto, form=request.form, erro=erro, status=400)
    except (IntegrityError, Conflict):
        db.session.rollback()
        return _render_form("personalizacao", registro, produto, form=request.form, erro=_conflito(), status=409)
    flash("Complemento local salvo; a ficha global permanece separada.", "success")
    return redirect(url_for("catalogo_local.index"))


@catalogo_local_bp.route("/personalizacoes/<int:personalizacao_id>/estado", methods=["POST"])
@login_required
@require_permission("catalogo.personalizar.edit")
@serializar_operacao("catalogo.personalizar.edit")
def personalizacao_estado(personalizacao_id):
    registro = _personalizacao(personalizacao_id)
    _validar_acao_form({"versao", "ativo"})
    if request.form.get("ativo") not in {"0", "1"}:
        abort(400)
    alterar_estado(registro, request.form["ativo"] == "1", request.form.get("versao"))
    db.session.commit()
    return redirect(url_for("catalogo_local.index"))


@catalogo_local_bp.route("/historico/<tipo>/<int:id>")
@login_required
@require_permission("catalogo.view")
def historico(tipo, id):
    if tipo not in {"local", "personalizacao"}:
        abort(404)
    registro = _local(id) if tipo == "local" else _personalizacao(id)
    campo = "produto_local_id" if tipo == "local" else "personalizacao_id"
    revisoes = CatalogoRevisao.query.filter_by(propriedade_id=propriedade_atual().id,
        **{campo: registro.id}).order_by(CatalogoRevisao.versao.desc()).all()
    detalhes = {}
    for revisao in revisoes:
        try:
            detalhes[revisao.id] = ler_json_seguro(revisao.snapshot_json)
        except ErroCatalogo:
            detalhes[revisao.id] = {}
    return render_template("catalogo_local/historico.html", modo=tipo, registro=registro,
                           revisoes=revisoes, detalhes_revisoes=detalhes)


def _solicitar(registro):
    local = isinstance(registro, ProdutoLocal)
    tipo = "inclusao" if local else "alteracao"
    errors, status = {}, 200
    form = proposta_padrao(registro) if request.method == "GET" else request.form.to_dict()
    if request.method == "GET":
        form["versao_origem"] = registro.versao
    else:
        try:
            pedido = solicitar(registro, request.form)
            db.session.commit()
            flash("Solicitação registrada para análise; nenhum produto foi publicado automaticamente.", "success")
            return redirect(url_for("catalogo_local.solicitacao", id=pedido.id))
        except ErroCatalogo as erro:
            errors, status = erro.errors, 400
        except (IntegrityError, Conflict):
            db.session.rollback()
            errors, status = _conflito().errors, 409
    return render_template("catalogo_local/solicitar.html", modo="local" if local else "personalizacao",
        registro=registro, tipo=tipo, form=form, errors=errors, duplicacoes=[]), status


@catalogo_local_bp.route("/<int:produto_id>/solicitar", methods=["GET", "POST"])
@login_required
@require_permission("catalogo.solicitar")
@serializar_operacao("catalogo.solicitar")
def solicitar_local(produto_id):
    return _solicitar(_local(produto_id))


@catalogo_local_bp.route("/personalizacoes/<int:personalizacao_id>/solicitar", methods=["GET", "POST"])
@login_required
@require_permission("catalogo.solicitar")
@serializar_operacao("catalogo.solicitar")
def solicitar_personalizacao(personalizacao_id):
    return _solicitar(_personalizacao(personalizacao_id))


@catalogo_local_bp.route("/solicitacoes")
@login_required
@require_permission("catalogo.view")
def solicitacoes():
    itens = SolicitacaoCatalogo.query.filter_by(propriedade_id=propriedade_atual().id).order_by(
        SolicitacaoCatalogo.solicitado_em.desc(), SolicitacaoCatalogo.id.desc()).all()
    return render_template("catalogo_local/solicitacoes.html", solicitacoes=itens)


@catalogo_local_bp.route("/solicitacoes/<int:id>")
@login_required
@require_permission("catalogo.view")
def solicitacao(id):
    item = _pedido(id)
    try:
        conteudo = ler_json_seguro(item.conteudo_json)
    except ErroCatalogo:
        conteudo = {}
    return render_template("catalogo_local/solicitacao.html", solicitacao=item, conteudo=conteudo,
                           form={}, errors={}, duplicacoes=[])


@catalogo_local_bp.route("/solicitacoes/<int:id>/cancelar", methods=["POST"])
@login_required
@require_permission("catalogo.local.edit")
@serializar_operacao("catalogo.local.edit")
def cancelar_solicitacao(id):
    _validar_acao_form(set())
    pedido = _pedido(id)
    if pedido.estado != "pendente":
        abort(409)
    pedido.estado, pedido.decidido_por_id, pedido.decidido_em = "cancelada", usuario_atual()["id"], iso_now()
    auditar("catalogo.solicitacao.cancelar", pedido, "Solicitação cancelada localmente; proposta preservada")
    db.session.commit()
    return redirect(url_for("catalogo_local.solicitacao", id=pedido.id))
