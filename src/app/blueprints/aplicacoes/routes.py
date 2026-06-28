"""CRUD de Aplicações de Insumo — escopo: propriedade do usuário logado.

Cada registro vincula uma associação Cultura↔Gleba da propriedade atual a um
ProdutoBase do catálogo. É histórico operacional: não recomenda produto e não
valida dose tecnicamente.
"""
from flask import abort, flash, redirect, render_template, request, url_for

from ...extensions import db
from ...models import AplicacaoInsumo, Cultura, CulturaGleba, Gleba, ProdutoBase
from ...utils.auth import login_required
from ...utils.contexto import parse_float, propriedade_atual, vazio_para_none
from ...utils.permissions import require_permission
from . import aplicacoes_bp

STATUS_BLOQUEADO = "bloqueado_historico"


def _cultura_glebas_da_propriedade(propriedade):
    """Associações cultura↔gleba pertencentes à propriedade atual."""
    return (CulturaGleba.query
            .join(Cultura, CulturaGleba.cultura_id == Cultura.id)
            .join(Gleba, CulturaGleba.gleba_id == Gleba.id)
            .filter(Cultura.propriedade_id == propriedade.id,
                    Gleba.propriedade_id == propriedade.id)
            .order_by(Cultura.nome, Gleba.nome, CulturaGleba.id)
            .all())


def _ids_cultura_gleba_validos(propriedade):
    return {cg.id for cg in _cultura_glebas_da_propriedade(propriedade)}


def _produto_bloqueado(produto):
    return (produto.status_sistema == STATUS_BLOQUEADO or
            produto.status_regulatorio == STATUS_BLOQUEADO)


def _produtos_aplicaveis():
    """Produtos do catálogo permitidos para registro operacional."""
    return (ProdutoBase.query
            .filter(ProdutoBase.status_sistema != STATUS_BLOQUEADO,
                    ProdutoBase.status_regulatorio != STATUS_BLOQUEADO)
            .order_by(ProdutoBase.classe, ProdutoBase.nome)
            .all())


def _ids_produtos_aplicaveis():
    return {p.id for p in _produtos_aplicaveis()}


def _aplicacao_da_propriedade_ou_404(aplicacao_id, propriedade):
    aplicacao = (AplicacaoInsumo.query
                 .join(CulturaGleba,
                       AplicacaoInsumo.cultura_gleba_id == CulturaGleba.id)
                 .join(Cultura, CulturaGleba.cultura_id == Cultura.id)
                 .join(Gleba, CulturaGleba.gleba_id == Gleba.id)
                 .filter(AplicacaoInsumo.id == aplicacao_id,
                         Cultura.propriedade_id == propriedade.id,
                         Gleba.propriedade_id == propriedade.id)
                 .first())
    if aplicacao is None:
        abort(404)
    return aplicacao


def _opcoes_cultura_gleba(propriedade):
    opcoes = []
    for cg in _cultura_glebas_da_propriedade(propriedade):
        opcoes.append((cg.id, f"{cg.cultura.nome} — {cg.gleba.nome}"))
    return opcoes


def _opcoes_produtos():
    opcoes = []
    for produto in _produtos_aplicaveis():
        categoria = produto.categoria or "—"
        opcoes.append((produto.id, f"{produto.nome} — {produto.classe} — {categoria}"))
    return opcoes


def _ler_e_validar_form(propriedade):
    """Lê/valida o formulário de aplicação. Retorna (dados, erro)."""
    cg_raw = (request.form.get("cultura_gleba_id") or "").strip()
    produto_raw = (request.form.get("produto_base_id") or "").strip()
    data_aplicacao = vazio_para_none(request.form.get("data_aplicacao"))
    dose_raw = request.form.get("dose")

    if not cg_raw:
        return None, "Selecione uma associação cultura↔gleba válida."
    if not cg_raw.isdigit() or int(cg_raw) not in _ids_cultura_gleba_validos(propriedade):
        return None, "Selecione uma associação cultura↔gleba válida da propriedade atual."

    if not produto_raw:
        return None, "Selecione um produto do catálogo."
    if not produto_raw.isdigit():
        return None, "Selecione um produto válido do catálogo."
    produto = db.session.get(ProdutoBase, int(produto_raw))
    if produto is None:
        return None, "Selecione um produto válido do catálogo."
    if _produto_bloqueado(produto) or produto.id not in _ids_produtos_aplicaveis():
        return None, "Produtos bloqueados/históricos não podem ser registrados como aplicação válida."

    if not data_aplicacao:
        return None, "A data da aplicação é obrigatória."

    dose = None
    if vazio_para_none(dose_raw) is not None:
        dose = parse_float(dose_raw)
        if dose is None or dose <= 0:
            return None, "A dose, se informada, deve ser um número maior que zero."

    return {
        "cultura_gleba_id": int(cg_raw),
        "produto_base_id": int(produto_raw),
        "data_aplicacao": data_aplicacao,
        "dose": dose,
        "unidade": vazio_para_none(request.form.get("unidade")),
        "responsavel": vazio_para_none(request.form.get("responsavel")),
        "observacao": vazio_para_none(request.form.get("observacao")),
    }, None


@aplicacoes_bp.route("/")
@login_required
@require_permission("aplicacoes.view")
def index():
    propriedade = propriedade_atual()
    ids_validos = _ids_cultura_gleba_validos(propriedade)
    aplicacoes = []
    if ids_validos:
        aplicacoes = (AplicacaoInsumo.query
                      .filter(AplicacaoInsumo.cultura_gleba_id.in_(ids_validos))
                      .order_by(AplicacaoInsumo.data_aplicacao.desc(),
                                AplicacaoInsumo.id.desc())
                      .all())
    return render_template("aplicacoes/list.html", aplicacoes=aplicacoes)


@aplicacoes_bp.route("/nova", methods=["GET", "POST"])
@login_required
@require_permission("aplicacoes.create")
def nova():
    propriedade = propriedade_atual()
    opcoes_cultura_gleba = _opcoes_cultura_gleba(propriedade)
    opcoes_produtos = _opcoes_produtos()
    if request.method == "POST":
        dados, erro = _ler_e_validar_form(propriedade)
        if erro:
            flash(erro, "error")
            return render_template("aplicacoes/form.html", aplicacao=None,
                                   form=request.form,
                                   opcoes_cultura_gleba=opcoes_cultura_gleba,
                                   opcoes_produtos=opcoes_produtos,
                                   selecionado_cg=None,
                                   selecionado_produto=None), 400
        db.session.add(AplicacaoInsumo(**dados))
        db.session.commit()
        flash("Aplicação de insumo registrada.", "success")
        return redirect(url_for("aplicacoes.index"))
    return render_template("aplicacoes/form.html", aplicacao=None, form={},
                           opcoes_cultura_gleba=opcoes_cultura_gleba,
                           opcoes_produtos=opcoes_produtos,
                           selecionado_cg=None,
                           selecionado_produto=None)


@aplicacoes_bp.route("/<int:aplicacao_id>/editar", methods=["GET", "POST"])
@login_required
@require_permission("aplicacoes.edit")
def editar(aplicacao_id):
    propriedade = propriedade_atual()
    aplicacao = _aplicacao_da_propriedade_ou_404(aplicacao_id, propriedade)
    opcoes_cultura_gleba = _opcoes_cultura_gleba(propriedade)
    opcoes_produtos = _opcoes_produtos()
    if request.method == "POST":
        dados, erro = _ler_e_validar_form(propriedade)
        if erro:
            flash(erro, "error")
            return render_template("aplicacoes/form.html", aplicacao=aplicacao,
                                   form=request.form,
                                   opcoes_cultura_gleba=opcoes_cultura_gleba,
                                   opcoes_produtos=opcoes_produtos,
                                   selecionado_cg=aplicacao.cultura_gleba_id,
                                   selecionado_produto=aplicacao.produto_base_id), 400
        aplicacao.cultura_gleba_id = dados["cultura_gleba_id"]
        aplicacao.produto_base_id = dados["produto_base_id"]
        aplicacao.data_aplicacao = dados["data_aplicacao"]
        aplicacao.dose = dados["dose"]
        aplicacao.unidade = dados["unidade"]
        aplicacao.responsavel = dados["responsavel"]
        aplicacao.observacao = dados["observacao"]
        db.session.commit()
        flash("Aplicação de insumo atualizada.", "success")
        return redirect(url_for("aplicacoes.index"))
    return render_template("aplicacoes/form.html", aplicacao=aplicacao,
                           form=aplicacao,
                           opcoes_cultura_gleba=opcoes_cultura_gleba,
                           opcoes_produtos=opcoes_produtos,
                           selecionado_cg=aplicacao.cultura_gleba_id,
                           selecionado_produto=aplicacao.produto_base_id)


@aplicacoes_bp.route("/<int:aplicacao_id>/remover", methods=["POST"])
@login_required
@require_permission("aplicacoes.delete")
def remover(aplicacao_id):
    propriedade = propriedade_atual()
    aplicacao = _aplicacao_da_propriedade_ou_404(aplicacao_id, propriedade)
    db.session.delete(aplicacao)
    db.session.commit()
    flash("Aplicação de insumo removida.", "success")
    return redirect(url_for("aplicacoes.index"))
