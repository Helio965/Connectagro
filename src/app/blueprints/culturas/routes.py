"""CRUD de Culturas (+ associação cultura↔gleba) — escopo: propriedade logada."""
from flask import abort, flash, redirect, render_template, request, url_for

from ...extensions import db
from ...models import Cultura, CulturaGleba, Gleba
from ...models._helpers import iso_now
from ...utils.auth import login_required
from ...utils.contexto import propriedade_atual, vazio_para_none
from ...utils.permissions import require_permission
from . import culturas_bp

STATUS_VALIDOS = ("planejada", "em_andamento", "colhida", "cancelada")


def _cultura_da_propriedade_ou_404(cultura_id, propriedade):
    cultura = Cultura.query.filter_by(id=cultura_id, propriedade_id=propriedade.id).first()
    if cultura is None:
        abort(404)
    return cultura


def _glebas_da_propriedade(propriedade):
    return Gleba.query.filter_by(propriedade_id=propriedade.id).order_by(Gleba.nome).all()


def _sincronizar_glebas(cultura, gleba_ids, propriedade):
    """Sincroniza as associações cultura↔gleba conforme os ids selecionados.

    Considera apenas glebas da mesma propriedade (evita vincular glebas alheias).
    """
    validos = {g.id for g in _glebas_da_propriedade(propriedade)}
    desejados = {int(x) for x in gleba_ids if str(x).isdigit()} & validos
    atuais = {cg.gleba_id: cg for cg in cultura.cultura_glebas}

    # remover associações que saíram
    for gid, cg in atuais.items():
        if gid not in desejados:
            db.session.delete(cg)
    # adicionar novas
    for gid in desejados - set(atuais):
        db.session.add(CulturaGleba(cultura_id=cultura.id, gleba_id=gid))


@culturas_bp.route("/")
@login_required
@require_permission("culturas.view")
def index():
    propriedade = propriedade_atual()
    culturas = (Cultura.query
                .filter_by(propriedade_id=propriedade.id)
                .order_by(Cultura.nome)
                .all())
    return render_template("culturas/list.html", culturas=culturas)


@culturas_bp.route("/nova", methods=["GET", "POST"])
@login_required
@require_permission("culturas.create")
def nova():
    propriedade = propriedade_atual()
    glebas = _glebas_da_propriedade(propriedade)
    if request.method == "POST":
        nome = vazio_para_none(request.form.get("nome"))
        status = request.form.get("status") or "planejada"
        if not nome:
            flash("O nome da cultura é obrigatório.", "error")
            return render_template("culturas/form.html", cultura=None,
                                   form=request.form, glebas=glebas,
                                   glebas_sel=set(), status_validos=STATUS_VALIDOS), 400
        if status not in STATUS_VALIDOS:
            status = "planejada"
        cultura = Cultura(
            propriedade_id=propriedade.id,
            nome=nome,
            variedade=vazio_para_none(request.form.get("variedade")),
            safra=vazio_para_none(request.form.get("safra")),
            data_inicio=vazio_para_none(request.form.get("data_inicio")),
            data_fim=vazio_para_none(request.form.get("data_fim")),
            status=status,
        )
        db.session.add(cultura)
        db.session.flush()  # garante cultura.id
        _sincronizar_glebas(cultura, request.form.getlist("glebas"), propriedade)
        db.session.commit()
        flash("Cultura criada com sucesso.", "success")
        return redirect(url_for("culturas.index"))
    return render_template("culturas/form.html", cultura=None, form={},
                           glebas=glebas, glebas_sel=set(),
                           status_validos=STATUS_VALIDOS)


@culturas_bp.route("/<int:cultura_id>/editar", methods=["GET", "POST"])
@login_required
@require_permission("culturas.edit")
def editar(cultura_id):
    propriedade = propriedade_atual()
    cultura = _cultura_da_propriedade_ou_404(cultura_id, propriedade)
    glebas = _glebas_da_propriedade(propriedade)
    if request.method == "POST":
        nome = vazio_para_none(request.form.get("nome"))
        status = request.form.get("status") or cultura.status
        if not nome:
            flash("O nome da cultura é obrigatório.", "error")
            sel = {int(x) for x in request.form.getlist("glebas") if x.isdigit()}
            return render_template("culturas/form.html", cultura=cultura,
                                   form=request.form, glebas=glebas,
                                   glebas_sel=sel, status_validos=STATUS_VALIDOS), 400
        cultura.nome = nome
        cultura.variedade = vazio_para_none(request.form.get("variedade"))
        cultura.safra = vazio_para_none(request.form.get("safra"))
        cultura.data_inicio = vazio_para_none(request.form.get("data_inicio"))
        cultura.data_fim = vazio_para_none(request.form.get("data_fim"))
        cultura.status = status if status in STATUS_VALIDOS else cultura.status
        cultura.atualizado_em = iso_now()
        _sincronizar_glebas(cultura, request.form.getlist("glebas"), propriedade)
        db.session.commit()
        flash("Cultura atualizada.", "success")
        return redirect(url_for("culturas.index"))
    sel = {cg.gleba_id for cg in cultura.cultura_glebas}
    return render_template("culturas/form.html", cultura=cultura, form=cultura,
                           glebas=glebas, glebas_sel=sel,
                           status_validos=STATUS_VALIDOS)


@culturas_bp.route("/<int:cultura_id>/remover", methods=["POST"])
@login_required
@require_permission("culturas.delete")
def remover(cultura_id):
    propriedade = propriedade_atual()
    cultura = _cultura_da_propriedade_ou_404(cultura_id, propriedade)
    for cg in list(cultura.cultura_glebas):
        db.session.delete(cg)
    db.session.delete(cultura)
    db.session.commit()
    flash("Cultura removida.", "success")
    return redirect(url_for("culturas.index"))
