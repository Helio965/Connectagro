"""CRUD de Culturas (+ associação cultura↔gleba) — escopo: propriedade logada."""
from flask import abort, flash, redirect, render_template, request, url_for
from sqlalchemy.exc import IntegrityError

from ...extensions import db
from ...models import AplicacaoInsumo, ColheitaRegistro, Cultura, CulturaGleba, Gleba
from ...models._helpers import iso_now
from ...utils.auth import login_required
from ...services.auditoria_service import registrar_falha, registrar_sucesso
from ...utils.contexto import propriedade_atual, vazio_para_none
from ...utils.permissions import require_permission
from . import culturas_bp

STATUS_VALIDOS = ("planejada", "em_andamento", "colhida", "cancelada")

MSG_CULTURA_COM_HISTORICO = (
    "Não é possível excluir esta cultura porque ela possui aplicações, "
    "colheitas ou outros dados históricos vinculados."
)
MSG_VINCULO_COM_HISTORICO = (
    "Não é possível remover o vínculo com gleba que possui aplicações, "
    "colheitas ou outros dados históricos vinculados."
)


def _cg_ids_com_historico(cg_ids):
    """Ids de associações cultura↔gleba referenciadas por aplicações/colheitas."""
    cg_ids = list(cg_ids)
    if not cg_ids:
        return set()
    com_aplicacao = db.session.query(AplicacaoInsumo.cultura_gleba_id).filter(
        AplicacaoInsumo.cultura_gleba_id.in_(cg_ids))
    com_colheita = db.session.query(ColheitaRegistro.cultura_gleba_id).filter(
        ColheitaRegistro.cultura_gleba_id.in_(cg_ids))
    return {r[0] for r in com_aplicacao} | {r[0] for r in com_colheita}


def _cultura_da_propriedade_ou_404(cultura_id, propriedade):
    cultura = Cultura.query.filter_by(id=cultura_id, propriedade_id=propriedade.id).first()
    if cultura is None:
        abort(404)
    return cultura


def _glebas_da_propriedade(propriedade):
    return Gleba.query.filter_by(propriedade_id=propriedade.id).order_by(Gleba.nome).all()


def _glebas_desejadas(gleba_ids, propriedade):
    """Ids de gleba selecionados no form, restritos à propriedade atual."""
    validos = {g.id for g in _glebas_da_propriedade(propriedade)}
    return {int(x) for x in gleba_ids if str(x).isdigit()} & validos


def _sincronizar_glebas(cultura, gleba_ids, propriedade):
    """Sincroniza as associações cultura↔gleba conforme os ids selecionados.

    Considera apenas glebas da mesma propriedade (evita vincular glebas alheias).
    """
    desejados = _glebas_desejadas(gleba_ids, propriedade)
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
        registrar_sucesso("culturas.create", entidade="cultura",
                          entidade_id=cultura.id, descricao="Cultura criada",
                          propriedade_id=propriedade.id, request=request)
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
        desejados = _glebas_desejadas(request.form.getlist("glebas"), propriedade)
        a_remover = [cg.id for cg in cultura.cultura_glebas
                     if cg.gleba_id not in desejados]
        if _cg_ids_com_historico(a_remover):
            flash(MSG_VINCULO_COM_HISTORICO, "error")
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
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            registrar_falha("culturas.edit", entidade="cultura",
                            entidade_id=cultura_id,
                            descricao="Edição bloqueada: associação com histórico",
                            propriedade_id=propriedade.id, request=request)
            flash(MSG_VINCULO_COM_HISTORICO, "error")
            return redirect(url_for("culturas.editar", cultura_id=cultura_id))
        registrar_sucesso("culturas.edit", entidade="cultura",
                          entidade_id=cultura.id, descricao="Cultura editada",
                          propriedade_id=propriedade.id, request=request)
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
    if _cg_ids_com_historico(cg.id for cg in cultura.cultura_glebas):
        flash(MSG_CULTURA_COM_HISTORICO, "error")
        return redirect(url_for("culturas.index"))
    try:
        for cg in list(cultura.cultura_glebas):
            db.session.delete(cg)
        db.session.delete(cultura)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        registrar_falha("culturas.delete", entidade="cultura",
                        entidade_id=cultura_id,
                        descricao="Exclusão bloqueada: cultura com histórico",
                        propriedade_id=propriedade.id, request=request)
        flash(MSG_CULTURA_COM_HISTORICO, "error")
        return redirect(url_for("culturas.index"))
    registrar_sucesso("culturas.delete", entidade="cultura",
                      entidade_id=cultura_id, descricao="Cultura removida",
                      propriedade_id=propriedade.id, request=request)
    flash("Cultura removida.", "success")
    return redirect(url_for("culturas.index"))
