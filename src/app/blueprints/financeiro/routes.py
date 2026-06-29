"""CRUD de Financeiro (lançamentos) — escopo: propriedade do usuário logado."""
from flask import abort, flash, redirect, render_template, request, url_for

from ...extensions import db
from ...models import FinanceiroLancamento
from ...models._helpers import iso_now
from ...utils.auth import login_required
from ...services.auditoria_service import registrar_sucesso
from ...utils.contexto import parse_float, propriedade_atual, vazio_para_none
from ...utils.permissions import require_permission
from . import financeiro_bp

TIPOS_VALIDOS = ("receita", "despesa")


def _lancamento_da_propriedade_ou_404(lancamento_id, propriedade):
    lanc = FinanceiroLancamento.query.filter_by(
        id=lancamento_id, propriedade_id=propriedade.id).first()
    if lanc is None:
        abort(404)
    return lanc


def _ler_e_validar_form():
    """Lê e valida os campos do formulário. Retorna (dados, erro)."""
    tipo = (request.form.get("tipo") or "").strip()
    categoria = vazio_para_none(request.form.get("categoria"))
    descricao = vazio_para_none(request.form.get("descricao"))
    valor = parse_float(request.form.get("valor"))
    data = vazio_para_none(request.form.get("data"))

    if tipo not in TIPOS_VALIDOS:
        return None, "Tipo inválido: use receita ou despesa."
    if valor is None or valor <= 0:
        return None, "O valor deve ser um número maior que zero."
    if not data:
        return None, "A data é obrigatória."

    return {"tipo": tipo, "categoria": categoria, "descricao": descricao,
            "valor": valor, "data": data}, None


@financeiro_bp.route("/")
@login_required
@require_permission("financeiro.view")
def index():
    propriedade = propriedade_atual()
    lancamentos = (FinanceiroLancamento.query
                   .filter_by(propriedade_id=propriedade.id)
                   .order_by(FinanceiroLancamento.data.desc(),
                             FinanceiroLancamento.id.desc())
                   .all())
    receitas = sum(l.valor for l in lancamentos if l.tipo == "receita")
    despesas = sum(l.valor for l in lancamentos if l.tipo == "despesa")
    saldo = receitas - despesas
    return render_template("financeiro/list.html", lancamentos=lancamentos,
                           receitas=receitas, despesas=despesas, saldo=saldo)


@financeiro_bp.route("/novo", methods=["GET", "POST"])
@login_required
@require_permission("financeiro.create")
def novo():
    propriedade = propriedade_atual()
    if request.method == "POST":
        dados, erro = _ler_e_validar_form()
        if erro:
            flash(erro, "error")
            return render_template("financeiro/form.html", lancamento=None,
                                   form=request.form, tipos=TIPOS_VALIDOS), 400
        lanc = FinanceiroLancamento(propriedade_id=propriedade.id, **dados)
        db.session.add(lanc)
        db.session.commit()
        registrar_sucesso("financeiro.create", entidade="financeiro_lancamento",
                          entidade_id=lanc.id, descricao=f"Lançamento {dados['tipo']} criado",
                          propriedade_id=propriedade.id, request=request)
        flash("Lançamento registrado.", "success")
        return redirect(url_for("financeiro.index"))
    return render_template("financeiro/form.html", lancamento=None, form={},
                           tipos=TIPOS_VALIDOS)


@financeiro_bp.route("/<int:lancamento_id>/editar", methods=["GET", "POST"])
@login_required
@require_permission("financeiro.edit")
def editar(lancamento_id):
    propriedade = propriedade_atual()
    lanc = _lancamento_da_propriedade_ou_404(lancamento_id, propriedade)
    if request.method == "POST":
        dados, erro = _ler_e_validar_form()
        if erro:
            flash(erro, "error")
            return render_template("financeiro/form.html", lancamento=lanc,
                                   form=request.form, tipos=TIPOS_VALIDOS), 400
        lanc.tipo = dados["tipo"]
        lanc.categoria = dados["categoria"]
        lanc.descricao = dados["descricao"]
        lanc.valor = dados["valor"]
        lanc.data = dados["data"]
        lanc.atualizado_em = iso_now()
        db.session.commit()
        registrar_sucesso("financeiro.edit", entidade="financeiro_lancamento",
                          entidade_id=lanc.id, descricao="Lançamento editado",
                          propriedade_id=propriedade.id, request=request)
        flash("Lançamento atualizado.", "success")
        return redirect(url_for("financeiro.index"))
    return render_template("financeiro/form.html", lancamento=lanc, form=lanc,
                           tipos=TIPOS_VALIDOS)


@financeiro_bp.route("/<int:lancamento_id>/remover", methods=["POST"])
@login_required
@require_permission("financeiro.delete")
def remover(lancamento_id):
    propriedade = propriedade_atual()
    lanc = _lancamento_da_propriedade_ou_404(lancamento_id, propriedade)
    db.session.delete(lanc)
    db.session.commit()
    registrar_sucesso("financeiro.delete", entidade="financeiro_lancamento",
                      entidade_id=lancamento_id, descricao="Lançamento removido",
                      propriedade_id=propriedade.id, request=request)
    flash("Lançamento removido.", "success")
    return redirect(url_for("financeiro.index"))
