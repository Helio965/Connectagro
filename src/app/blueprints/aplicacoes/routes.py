"""Aplicações históricas, com consumo e custo separados da dose informada."""
import math
from uuid import UUID, uuid4

from flask import abort, flash, redirect, render_template, request, url_for
from sqlalchemy.exc import IntegrityError

from ...extensions import db
from ...models import AplicacaoInsumo, Cultura, CulturaGleba, Gleba, ProdutoBase
from ...models._helpers import iso_now
from ...services.auditoria_service import preparar_evento
from ...services.operacionais_lock import serializar_operacao
from ...services.operacionais_service import (
    opcoes_responsaveis, parse_id, validar_consumo_custo, validar_data_iso,
    validar_responsavel,
)
from ...utils.auth import login_required, usuario_atual
from ...utils.contexto import parse_float, propriedade_atual, vazio_para_none
from ...utils.permissions import has_permission, require_permission
from . import aplicacoes_bp

STATUS_BLOQUEADO = "bloqueado_historico"
_CAMPOS_CUSTO = {"custo_unitario", "custo_total", "moeda", "origem_custo"}


def _cultura_glebas_da_propriedade(propriedade):
    return (CulturaGleba.query
            .join(Cultura, CulturaGleba.cultura_id == Cultura.id)
            .join(Gleba, CulturaGleba.gleba_id == Gleba.id)
            .filter(Cultura.propriedade_id == propriedade.id,
                    Gleba.propriedade_id == propriedade.id)
            .order_by(Cultura.nome, Gleba.nome, CulturaGleba.id).all())


def _ids_cultura_gleba_validos(propriedade):
    return {cg.id for cg in _cultura_glebas_da_propriedade(propriedade)}


def _produto_bloqueado(produto):
    return (produto.status_sistema == STATUS_BLOQUEADO or
            produto.status_regulatorio == STATUS_BLOQUEADO)


def _produtos_aplicaveis():
    return (ProdutoBase.query
            .filter(ProdutoBase.status_sistema != STATUS_BLOQUEADO,
                    ProdutoBase.status_regulatorio != STATUS_BLOQUEADO)
            .order_by(ProdutoBase.classe, ProdutoBase.nome).all())


def _ids_produtos_aplicaveis():
    return {p.id for p in _produtos_aplicaveis()}


def _aplicacao_da_propriedade_ou_404(aplicacao_id, propriedade):
    try:
        aplicacao_id = parse_id(str(aplicacao_id))
    except ValueError:
        abort(404)
    aplicacao = (AplicacaoInsumo.query
                 .join(CulturaGleba,
                       AplicacaoInsumo.cultura_gleba_id == CulturaGleba.id)
                 .join(Cultura, CulturaGleba.cultura_id == Cultura.id)
                 .join(Gleba, CulturaGleba.gleba_id == Gleba.id)
                 .filter(AplicacaoInsumo.id == aplicacao_id,
                         Cultura.propriedade_id == propriedade.id,
                         Gleba.propriedade_id == propriedade.id).first())
    if aplicacao is None:
        abort(404)
    return aplicacao


def _opcoes_cultura_gleba(propriedade):
    return [(cg.id, f"{cg.cultura.nome} — {cg.gleba.nome}")
            for cg in _cultura_glebas_da_propriedade(propriedade)]


def _opcoes_produtos():
    return [(p.id, f"{p.nome} — {p.classe} — {p.categoria or '—'}")
            for p in _produtos_aplicaveis()]


def _formulario(propriedade, aplicacao=None, *, form=None, errors=None, status=200):
    if form is None:
        form = ({c.name: getattr(aplicacao, c.name)
                 for c in AplicacaoInsumo.__table__.columns} if aplicacao else
                {"chave_envio": str(uuid4())})
    else:
        form = dict(form)
    if not has_permission("financeiro.view"):
        form = {k: v for k, v in form.items() if k not in _CAMPOS_CUSTO}
    pode_custo = has_permission("financeiro.edit" if aplicacao else "financeiro.create")
    return render_template(
        "aplicacoes/form.html", aplicacao=aplicacao, form=form,
        errors=errors or {}, erros=errors or {},
        opcoes_cultura_gleba=_opcoes_cultura_gleba(propriedade),
        opcoes_produtos=_opcoes_produtos(),
        opcoes_responsaveis=opcoes_responsaveis(propriedade.id, registro=aplicacao),
        selecionado_cg=form.get("cultura_gleba_id"),
        selecionado_produto=form.get("produto_base_id"),
        token_envio=form.get("chave_envio", "") if not aplicacao else "",
        can_editar_custos=pode_custo, pode_informar_custo=pode_custo,
        can_ver_custos=has_permission("financeiro.view"),
        pode_ver_custo=has_permission("financeiro.view"),
    ), status


def _chave_envio(raw, errors):
    raw = vazio_para_none(raw)
    if raw is None:
        # Clientes anteriores não possuem chave. Os formulários novos a enviam.
        return None
    try:
        if len(raw) > 36:
            raise ValueError
        return str(UUID(raw))
    except ValueError:
        errors["chave_envio"] = "Recarregue o formulário para obter uma identificação de envio válida."
        return None


def _ler_e_validar_form(propriedade, aplicacao=None):
    errors = {}
    dados = {}
    try:
        cg_id = parse_id(request.form.get("cultura_gleba_id"))
        if cg_id not in _ids_cultura_gleba_validos(propriedade):
            raise ValueError
        dados["cultura_gleba_id"] = cg_id
    except ValueError:
        errors["cultura_gleba_id"] = "Selecione uma associação cultura↔área de plantio válida."
    try:
        produto_id = parse_id(request.form.get("produto_base_id"))
        produto = db.session.get(ProdutoBase, produto_id)
        if produto is None:
            raise ValueError
        if _produto_bloqueado(produto):
            errors["produto_base_id"] = "Produtos bloqueados/históricos não podem ser registrados como aplicação válida."
        else:
            dados["produto_base_id"] = produto_id
    except ValueError:
        errors["produto_base_id"] = "Selecione um produto válido do catálogo."
    try:
        dados["data_aplicacao"] = validar_data_iso(request.form.get("data_aplicacao"))
    except ValueError:
        errors["data_aplicacao"] = "Informe uma data da aplicação válida."
    dose_raw = vazio_para_none(request.form.get("dose"))
    dose = parse_float(dose_raw) if dose_raw is not None and len(dose_raw) <= 100 else None
    if dose_raw is not None and (dose is None or not math.isfinite(dose) or dose <= 0):
        errors["dose"] = "A dose, se informada, deve ser um número finito maior que zero."
    dados["dose"] = dose
    for campo, limite in (("unidade", 20), ("observacao", 10000)):
        valor = vazio_para_none(request.form.get(campo))
        if valor is not None and len(valor) > limite:
            errors[campo] = f"Use no máximo {limite} caracteres."
        dados[campo] = valor
    responsavel_id, responsavel, erros_resp = validar_responsavel(
        propriedade.id,
        request.form.get("responsavel_usuario_id", getattr(aplicacao, "responsavel_usuario_id", None)),
        request.form.get("responsavel", getattr(aplicacao, "responsavel", None)),
        registro=aplicacao)
    dados.update(responsavel_usuario_id=responsavel_id, responsavel=responsavel)
    errors.update(erros_resp)
    consumo, erros_consumo = validar_consumo_custo(
        request.form, existente=aplicacao,
        pode_criar_custo=has_permission("financeiro.create"),
        pode_editar_custo=has_permission("financeiro.edit"))
    dados.update(consumo)
    errors.update(erros_consumo)
    if aplicacao is None:
        dados["chave_envio"] = _chave_envio(request.form.get("chave_envio"), errors)
    return dados, errors


def _reenvio(propriedade, dados):
    chave = dados.get("chave_envio")
    if not chave:
        return None
    anterior = AplicacaoInsumo.query.filter_by(chave_envio=chave).first()
    if anterior is None:
        return None
    if (anterior.criado_por_id != usuario_atual()["id"]
            or anterior.cultura_gleba_id not in _ids_cultura_gleba_validos(propriedade)
            or any(getattr(anterior, campo) != valor for campo, valor in dados.items())):
        abort(409, description="Identificação de envio já utilizada. Recarregue o formulário.")
    return redirect(url_for("aplicacoes.index"))


@aplicacoes_bp.route("/")
@login_required
@require_permission("aplicacoes.view")
def index():
    propriedade = propriedade_atual()
    ids_validos = _ids_cultura_gleba_validos(propriedade)
    aplicacoes = (AplicacaoInsumo.query
                  .filter(AplicacaoInsumo.cultura_gleba_id.in_(ids_validos))
                  .order_by(AplicacaoInsumo.data_aplicacao.desc(), AplicacaoInsumo.id.desc())
                  .all()) if ids_validos else []
    return render_template("aplicacoes/list.html", aplicacoes=aplicacoes,
                           can_ver_custos=has_permission("financeiro.view"))


@aplicacoes_bp.route("/nova", methods=["GET", "POST"])
@login_required
@require_permission("aplicacoes.create")
@serializar_operacao("aplicacoes.create")
def nova():
    propriedade = propriedade_atual()
    if request.method == "GET":
        return _formulario(propriedade)
    dados, errors = _ler_e_validar_form(propriedade)
    if errors:
        flash("Revise os campos indicados antes de salvar.", "error")
        return _formulario(propriedade, form=request.form, errors=errors, status=400)
    repetido = _reenvio(propriedade, dados)
    if repetido is not None:
        return repetido
    aplicacao = AplicacaoInsumo(criado_por_id=usuario_atual()["id"], **dados)
    db.session.add(aplicacao)
    try:
        db.session.flush()
        db.session.add(preparar_evento(
            "aplicacoes.create", entidade="aplicacao_insumo", entidade_id=aplicacao.id,
            descricao="Aplicação registrada", propriedade_id=propriedade.id, request=request))
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        repetido = _reenvio(propriedade, dados)
        if repetido is not None:
            return repetido
        abort(409, description="O registro mudou durante o envio. Recarregue e tente novamente.")
    flash("Aplicação de insumo registrada.", "success")
    return redirect(url_for("aplicacoes.index"))


@aplicacoes_bp.route("/<int:aplicacao_id>/editar", methods=["GET", "POST"])
@login_required
@require_permission("aplicacoes.edit")
@serializar_operacao("aplicacoes.edit")
def editar(aplicacao_id):
    propriedade = propriedade_atual()
    aplicacao = _aplicacao_da_propriedade_ou_404(aplicacao_id, propriedade)
    if request.method == "GET":
        return _formulario(propriedade, aplicacao)
    dados, errors = _ler_e_validar_form(propriedade, aplicacao)
    if errors:
        flash("Revise os campos indicados antes de salvar.", "error")
        return _formulario(propriedade, aplicacao, form=request.form, errors=errors, status=400)
    alterados = [campo for campo, valor in dados.items() if getattr(aplicacao, campo) != valor]
    for campo, valor in dados.items():
        setattr(aplicacao, campo, valor)
    aplicacao.atualizado_por_id = usuario_atual()["id"]
    aplicacao.atualizado_em = iso_now()
    db.session.add(preparar_evento(
        "aplicacoes.edit", entidade="aplicacao_insumo", entidade_id=aplicacao.id,
        descricao="Aplicação editada; campos: " + ", ".join(alterados),
        propriedade_id=propriedade.id, request=request))
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        abort(409, description="O registro mudou durante a edição. Recarregue e tente novamente.")
    flash("Aplicação de insumo atualizada.", "success")
    return redirect(url_for("aplicacoes.index"))


@aplicacoes_bp.route("/<int:aplicacao_id>/remover", methods=["POST"])
@login_required
@require_permission("aplicacoes.delete")
@serializar_operacao("aplicacoes.delete")
def remover(aplicacao_id):
    propriedade = propriedade_atual()
    aplicacao = _aplicacao_da_propriedade_ou_404(aplicacao_id, propriedade)
    db.session.delete(aplicacao)
    db.session.add(preparar_evento(
        "aplicacoes.delete", entidade="aplicacao_insumo", entidade_id=aplicacao_id,
        descricao="Aplicação removida", propriedade_id=propriedade.id, request=request))
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        abort(409, description="Aplicação possui dependências e não pode ser removida.")
    flash("Aplicação de insumo removida.", "success")
    return redirect(url_for("aplicacoes.index"))
