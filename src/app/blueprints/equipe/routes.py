"""CRUD de Equipe (membros) — escopo: propriedade do usuário logado."""
from flask import abort, flash, redirect, render_template, request, url_for

from ...extensions import db
from ...models import EquipeMembro
from ...models._helpers import iso_now
from ...utils.auth import login_required
from ...services.auditoria_service import registrar_sucesso
from ...utils.contexto import propriedade_atual, vazio_para_none
from ...utils.permissions import require_permission
from . import equipe_bp


def _membro_da_propriedade_ou_404(membro_id, propriedade):
    membro = EquipeMembro.query.filter_by(
        id=membro_id, propriedade_id=propriedade.id).first()
    if membro is None:
        abort(404)
    return membro


def _email_normalizado(valor):
    valor = vazio_para_none(valor)
    return valor.lower() if valor else None


@equipe_bp.route("/")
@login_required
@require_permission("equipe.view")
def index():
    propriedade = propriedade_atual()
    membros = (EquipeMembro.query
               .filter_by(propriedade_id=propriedade.id)
               .order_by(EquipeMembro.ativo.desc(), EquipeMembro.nome)
               .all())
    return render_template("equipe/list.html", membros=membros)


@equipe_bp.route("/novo", methods=["GET", "POST"])
@login_required
@require_permission("equipe.create")
def novo():
    propriedade = propriedade_atual()
    if request.method == "POST":
        nome = vazio_para_none(request.form.get("nome"))
        if not nome:
            flash("O nome do membro é obrigatório.", "error")
            return render_template("equipe/form.html", membro=None,
                                   form=request.form), 400
        membro = EquipeMembro(
            propriedade_id=propriedade.id,
            nome=nome,
            funcao=vazio_para_none(request.form.get("funcao")),
            email=_email_normalizado(request.form.get("email")),
            telefone=vazio_para_none(request.form.get("telefone")),
            ativo=bool(request.form.get("ativo")),
        )
        db.session.add(membro)
        db.session.commit()
        registrar_sucesso("equipe.create", entidade="equipe_membro",
                          entidade_id=membro.id, descricao="Membro de equipe criado",
                          propriedade_id=propriedade.id, request=request)
        flash("Membro adicionado.", "success")
        return redirect(url_for("equipe.index"))
    # GET: novo membro começa ativo por padrão
    return render_template("equipe/form.html", membro=None, form={"ativo": True})


@equipe_bp.route("/<int:membro_id>/editar", methods=["GET", "POST"])
@login_required
@require_permission("equipe.edit")
def editar(membro_id):
    propriedade = propriedade_atual()
    membro = _membro_da_propriedade_ou_404(membro_id, propriedade)
    if request.method == "POST":
        nome = vazio_para_none(request.form.get("nome"))
        if not nome:
            flash("O nome do membro é obrigatório.", "error")
            return render_template("equipe/form.html", membro=membro,
                                   form=request.form), 400
        membro.nome = nome
        membro.funcao = vazio_para_none(request.form.get("funcao"))
        membro.email = _email_normalizado(request.form.get("email"))
        membro.telefone = vazio_para_none(request.form.get("telefone"))
        membro.ativo = bool(request.form.get("ativo"))
        membro.atualizado_em = iso_now()
        db.session.commit()
        registrar_sucesso("equipe.edit", entidade="equipe_membro",
                          entidade_id=membro.id, descricao="Membro de equipe editado",
                          propriedade_id=propriedade.id, request=request)
        flash("Membro atualizado.", "success")
        return redirect(url_for("equipe.index"))
    return render_template("equipe/form.html", membro=membro, form=membro)


@equipe_bp.route("/<int:membro_id>/remover", methods=["POST"])
@login_required
@require_permission("equipe.delete")
def remover(membro_id):
    propriedade = propriedade_atual()
    membro = _membro_da_propriedade_ou_404(membro_id, propriedade)
    db.session.delete(membro)
    db.session.commit()
    registrar_sucesso("equipe.delete", entidade="equipe_membro",
                      entidade_id=membro_id, descricao="Membro de equipe removido",
                      propriedade_id=propriedade.id, request=request)
    flash("Membro removido.", "success")
    return redirect(url_for("equipe.index"))
