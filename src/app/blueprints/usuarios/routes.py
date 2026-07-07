"""Painel de Usuários — somente admin, escopo: propriedade atual (Fase 7.1).

Permite listar, criar, editar dados principais, redefinir senha e ativar/
inativar usuários vinculados à propriedade atual. Não há cadastro público,
remoção física nem painel de roles.
"""
import re

from flask import abort, flash, redirect, render_template, request, session, url_for

from ...extensions import db
from ...models import Usuario, UsuarioPropriedade
from ...models._helpers import iso_now
from ...services.auditoria_service import registrar_negado, registrar_sucesso
from ...utils.auth import gerar_hash_senha, login_required, usuario_atual
from ...utils.contexto import propriedade_atual, vazio_para_none
from ...utils.permissions import PERFIS_OFICIAIS, require_permission, role_label
from . import usuarios_bp

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
MIN_SENHA = 6


def _usuario_da_propriedade_ou_404(usuario_id, propriedade):
    """Busca um usuário vinculado à propriedade atual ou retorna 404."""
    vinculo = UsuarioPropriedade.query.filter_by(
        usuario_id=usuario_id,
        propriedade_id=propriedade.id,
    ).first()
    if vinculo is None:
        abort(404)
    usuario = db.session.get(Usuario, usuario_id)
    if usuario is None:
        abort(404)
    return usuario, vinculo


def _email_valido(email):
    return bool(EMAIL_RE.match(email or ""))


def _email_em_uso(email, usuario_id=None):
    query = Usuario.query.filter_by(email=email)
    if usuario_id is not None:
        query = query.filter(Usuario.id != usuario_id)
    return query.first() is not None


def _usuario_logado_model():
    atual = usuario_atual()
    if not atual:
        return None
    return db.session.get(Usuario, atual["id"])


def _is_admin(usuario):
    return bool(usuario and usuario.perfil == "admin")


def _is_manager(usuario):
    return bool(usuario and usuario.perfil == "tecnico")


def _allowed_roles_to_create(usuario):
    if _is_admin(usuario):
        return ("tecnico", "trabalhador")
    if _is_manager(usuario):
        return ("trabalhador",)
    return ()


def _allowed_roles_to_edit(usuario_logado, alvo):
    if _is_admin(usuario_logado):
        if alvo.perfil == "admin":
            return ("admin",)
        return ("tecnico", "trabalhador")
    if _is_manager(usuario_logado) and alvo.perfil == "trabalhador":
        return ("trabalhador",)
    return ()


def _can_edit_target_user(usuario_logado, alvo):
    return bool(_allowed_roles_to_edit(usuario_logado, alvo))


def _bloquear_acao_usuario(acao, descricao, propriedade=None, usuario_id=None):
    registrar_negado(
        acao,
        entidade="usuario",
        entidade_id=usuario_id,
        descricao=descricao,
        propriedade_id=(propriedade.id if propriedade else None),
        request=request,
    )
    abort(403)


def _ativo_form(default=False):
    return bool(request.form.get("ativo")) if request.method == "POST" else default


def _contar_admins_ativos():
    return Usuario.query.filter_by(perfil="admin", ativo=True).count()


def _validar_admin_preservado(usuario, novo_perfil, novo_ativo):
    atual = usuario_atual()
    erros = []
    if atual and atual.get("id") == usuario.id:
        if not novo_ativo:
            erros.append("Você não pode inativar seu próprio usuário administrador.")
        if novo_perfil != "admin":
            erros.append("Você não pode alterar seu próprio perfil de administrador.")

    unico_admin_ativo = (
        usuario.perfil == "admin"
        and usuario.ativo
        and _contar_admins_ativos() <= 1
    )
    if unico_admin_ativo and novo_perfil != "admin":
        erros.append("Não é possível alterar o perfil do único admin ativo.")
    if unico_admin_ativo and not novo_ativo:
        erros.append("Não é possível inativar o único admin ativo.")
    if usuario.perfil == "admin" and not usuario.ativo and novo_ativo and _contar_admins_ativos() >= 1:
        erros.append("Não é possível ativar outro administrador.")
    return erros


def _validar_dados_usuario(*, usuario=None, perfis_permitidos=()):
    nome = vazio_para_none(request.form.get("nome"))
    email = (request.form.get("email") or "").strip().lower()
    perfil = request.form.get("perfil") or ""
    ativo = _ativo_form(default=True if usuario is None else bool(usuario.ativo))
    senha = request.form.get("senha") or ""
    confirmar_senha = request.form.get("confirmar_senha") or ""

    erros = []
    if not nome:
        erros.append("O nome é obrigatório.")
    if not email:
        erros.append("O e-mail é obrigatório.")
    elif not _email_valido(email):
        erros.append("Informe um e-mail válido.")
    elif _email_em_uso(email, usuario.id if usuario else None):
        erros.append("Já existe um usuário com esse e-mail.")
    if perfil not in PERFIS_OFICIAIS:
        erros.append("Perfil inválido.")
    elif perfil not in perfis_permitidos:
        erros.append(f"Perfil não permitido: {role_label(perfil)}.")

    if usuario is None:
        if not senha:
            erros.append("A senha é obrigatória.")
        if not confirmar_senha:
            erros.append("A confirmação de senha é obrigatória.")
    elif confirmar_senha and not senha:
        erros.append("Preencha a nova senha antes da confirmação.")

    if senha and len(senha) < MIN_SENHA:
        erros.append(f"A senha deve ter ao menos {MIN_SENHA} caracteres.")
    if senha or confirmar_senha:
        if senha != confirmar_senha:
            erros.append("A senha e a confirmação não coincidem.")

    if usuario is not None:
        erros.extend(_validar_admin_preservado(usuario, perfil, ativo))

    return {
        "nome": nome,
        "email": email,
        "perfil": perfil,
        "ativo": ativo,
        "senha": senha,
        "confirmar_senha": confirmar_senha,
    }, erros


def _render_form(usuario, form, perfis, status=200, titulo=None, form_action=None):
    return render_template(
        "usuarios/form.html",
        usuario=usuario,
        form=form,
        perfis=perfis,
        min_senha=MIN_SENHA,
        titulo=titulo,
        form_action=form_action,
    ), status


def _sincronizar_sessao_se_usuario_atual(usuario):
    atual = usuario_atual()
    if not atual or atual.get("id") != usuario.id:
        return
    session["user_email"] = usuario.email
    session["user_nome"] = usuario.nome
    session["user_perfil"] = usuario.perfil


@usuarios_bp.route("/")
@login_required
@require_permission("usuarios.view")
def index():
    """Usuários e Acessos — listagem agrupada por perfil.

    Admin vê os três blocos (Administrador, Gerentes de Plantio,
    Trabalhadores); gerente vê apenas o bloco de Trabalhadores.
    """
    propriedade = propriedade_atual()
    usuario_logado = _usuario_logado_model()
    atual = usuario_atual()
    admins_ativos = _contar_admins_ativos()
    vinculos = (UsuarioPropriedade.query
                .filter_by(propriedade_id=propriedade.id)
                .order_by(UsuarioPropriedade.id)
                .all())

    grupos = {"admin": [], "tecnico": [], "trabalhador": []}
    for v in vinculos:
        u = db.session.get(Usuario, v.usuario_id)
        if not u or u.perfil not in grupos:
            continue
        if not (_is_admin(usuario_logado)
                or (_is_manager(usuario_logado) and u.perfil == "trabalhador")):
            continue
        can_manage = _can_edit_target_user(usuario_logado, u)
        eh_proprio = bool(atual and atual.get("id") == u.id)
        eh_unico_admin = (u.perfil == "admin" and u.ativo and admins_ativos <= 1)
        grupos[u.perfil].append({
            "usuario": u,
            "vinculo": v,
            "can_manage": can_manage,
            "admin_principal": (u.perfil == "admin"
                                and propriedade.usuario_id == u.id),
            # Botão de inativar some para o único admin ativo e para o
            # próprio usuário (o backend também bloqueia as duas ações).
            "mostrar_inativar": (can_manage and u.ativo
                                 and not eh_unico_admin and not eh_proprio),
        })

    perfis_criaveis = _allowed_roles_to_create(usuario_logado)
    return render_template(
        "usuarios/list.html",
        admins=grupos["admin"],
        gerentes=grupos["tecnico"],
        trabalhadores=grupos["trabalhador"],
        pode_criar_gerente="tecnico" in perfis_criaveis,
        pode_criar_trabalhador="trabalhador" in perfis_criaveis,
        eh_admin=_is_admin(usuario_logado),
    )


@usuarios_bp.route("/novo", methods=["GET", "POST"])
@login_required
@require_permission("usuarios.create")
def novo():
    """Criação genérica (perfil escolhido no formulário)."""
    return _fluxo_novo()


@usuarios_bp.route("/novo/gerente", methods=["GET", "POST"])
@login_required
@require_permission("usuarios.create")
def novo_gerente():
    """Criação com perfil travado em Gerente de Plantio (interno: tecnico)."""
    return _fluxo_novo(perfil_fixo="tecnico")


@usuarios_bp.route("/novo/trabalhador", methods=["GET", "POST"])
@login_required
@require_permission("usuarios.create")
def novo_trabalhador():
    """Criação com perfil travado em Trabalhador."""
    return _fluxo_novo(perfil_fixo="trabalhador")


def _fluxo_novo(perfil_fixo=None):
    propriedade = propriedade_atual()
    usuario_logado = _usuario_logado_model()
    perfis_permitidos = _allowed_roles_to_create(usuario_logado)
    if not perfis_permitidos:
        _bloquear_acao_usuario(
            "usuarios.create.blocked",
            "Tentativa bloqueada de acessar criação de usuário",
            propriedade,
        )
    titulo = None
    form_action = None
    if perfil_fixo is not None:
        if perfil_fixo not in perfis_permitidos:
            _bloquear_acao_usuario(
                "usuarios.create.blocked",
                f"Tentativa bloqueada de criar perfil {perfil_fixo}",
                propriedade,
            )
        # Trava o perfil: o POST manipulado com outro perfil cai no bloqueio
        # padrão logo abaixo (perfil fora de perfis_permitidos -> 403).
        perfis_permitidos = (perfil_fixo,)
        titulo = f"Novo {role_label(perfil_fixo)}"
        endpoint = ("usuarios.novo_gerente" if perfil_fixo == "tecnico"
                    else "usuarios.novo_trabalhador")
        form_action = url_for(endpoint)
    if request.method == "POST":
        perfil_solicitado = request.form.get("perfil") or ""
        if perfil_solicitado not in perfis_permitidos:
            _bloquear_acao_usuario(
                "usuarios.create.blocked",
                f"Tentativa bloqueada de criar perfil {perfil_solicitado or 'vazio'}",
                propriedade,
            )

        dados, erros = _validar_dados_usuario(perfis_permitidos=perfis_permitidos)
        if erros:
            for e in erros:
                flash(e, "error")
            return _render_form(None, request.form, perfis_permitidos, 400,
                                titulo=titulo, form_action=form_action)

        usuario = Usuario(
            nome=dados["nome"],
            email=dados["email"],
            perfil=dados["perfil"],
            ativo=dados["ativo"],
            senha_hash=gerar_hash_senha(dados["senha"]),
        )
        db.session.add(usuario)
        db.session.flush()

        atual = usuario_atual()
        db.session.add(UsuarioPropriedade(
            usuario_id=usuario.id,
            propriedade_id=propriedade.id,
            ativo=dados["ativo"],
            criado_por_id=atual["id"] if atual else None,
        ))
        db.session.commit()

        descricao = f"Usuário criado: {usuario.email}"
        if _is_manager(usuario_logado):
            descricao = f"Gerente criou trabalhador: {usuario.email}"
        registrar_sucesso("usuarios.create", entidade="usuario",
                          entidade_id=usuario.id,
                          descricao=descricao,
                          propriedade_id=propriedade.id, request=request)
        flash("Usuário criado com sucesso.", "success")
        return redirect(url_for("usuarios.index"))

    return _render_form(None, {"perfil": perfis_permitidos[0], "ativo": True},
                        perfis_permitidos, titulo=titulo,
                        form_action=form_action)[0]


@usuarios_bp.route("/<int:usuario_id>/editar", methods=["GET", "POST"])
@login_required
@require_permission("usuarios.edit")
def editar(usuario_id):
    propriedade = propriedade_atual()
    usuario_logado = _usuario_logado_model()
    usuario, vinculo = _usuario_da_propriedade_ou_404(usuario_id, propriedade)
    perfis_permitidos = _allowed_roles_to_edit(usuario_logado, usuario)
    if not perfis_permitidos:
        _bloquear_acao_usuario(
            "usuarios.edit.blocked",
            f"Tentativa bloqueada de editar usuário #{usuario.id}",
            propriedade,
            usuario.id,
        )

    if request.method == "POST":
        perfil_solicitado = request.form.get("perfil") or ""
        if perfil_solicitado not in perfis_permitidos:
            _bloquear_acao_usuario(
                "usuarios.profile_change.blocked",
                f"Tentativa bloqueada de alterar perfil para {perfil_solicitado or 'vazio'}",
                propriedade,
                usuario.id,
            )

        dados, erros = _validar_dados_usuario(
            usuario=usuario,
            perfis_permitidos=perfis_permitidos,
        )
        if erros:
            for e in erros:
                flash(e, "error")
            return _render_form(usuario, request.form, perfis_permitidos, 400)

        perfil_anterior = usuario.perfil
        ativo_anterior = bool(usuario.ativo)
        email_anterior = usuario.email
        senha_alterada = bool(dados["senha"])

        usuario.nome = dados["nome"]
        usuario.email = dados["email"]
        usuario.perfil = dados["perfil"]
        usuario.ativo = dados["ativo"]
        if senha_alterada:
            usuario.senha_hash = gerar_hash_senha(dados["senha"])
        usuario.atualizado_em = iso_now()
        vinculo.ativo = dados["ativo"]
        vinculo.atualizado_em = iso_now()
        db.session.commit()
        _sincronizar_sessao_se_usuario_atual(usuario)

        registrar_sucesso("usuarios.edit", entidade="usuario",
                          entidade_id=usuario.id,
                          descricao=f"Usuário editado: #{usuario.id}",
                          propriedade_id=propriedade.id, request=request)
        if email_anterior != usuario.email:
            registrar_sucesso("usuarios.email_change", entidade="usuario",
                              entidade_id=usuario.id,
                              descricao=f"E-mail alterado: {email_anterior} -> {usuario.email}",
                              propriedade_id=propriedade.id, request=request)
        if perfil_anterior != usuario.perfil:
            registrar_sucesso("usuarios.profile_change", entidade="usuario",
                              entidade_id=usuario.id,
                              descricao=f"Perfil alterado: {perfil_anterior} -> {usuario.perfil}",
                              propriedade_id=propriedade.id, request=request)
        if ativo_anterior != usuario.ativo:
            acao = "usuarios.activate" if usuario.ativo else "usuarios.deactivate"
            descricao = "Usuário ativado" if usuario.ativo else "Usuário desativado"
            registrar_sucesso(acao, entidade="usuario", entidade_id=usuario.id,
                              descricao=f"{descricao}: #{usuario.id}",
                              propriedade_id=propriedade.id, request=request)
        if senha_alterada:
            registrar_sucesso("usuarios.password_reset", entidade="usuario",
                              entidade_id=usuario.id,
                              descricao=f"Senha redefinida para usuário #{usuario.id}",
                              propriedade_id=propriedade.id, request=request)
        flash("Usuário atualizado.", "success")
        return redirect(url_for("usuarios.index"))

    return _render_form(usuario, usuario, perfis_permitidos)[0]


@usuarios_bp.route("/<int:usuario_id>/inativar", methods=["POST"])
@login_required
@require_permission("usuarios.deactivate")
def inativar(usuario_id):
    propriedade = propriedade_atual()
    usuario_logado = _usuario_logado_model()
    usuario, vinculo = _usuario_da_propriedade_ou_404(usuario_id, propriedade)
    if not _can_edit_target_user(usuario_logado, usuario):
        _bloquear_acao_usuario(
            "usuarios.deactivate.blocked",
            f"Tentativa bloqueada de inativar usuário #{usuario.id}",
            propriedade,
            usuario.id,
        )
    atual = usuario_atual()
    if atual and atual.get("id") == usuario.id:
        flash("Você não pode inativar seu próprio usuário administrador.", "error")
        return redirect(url_for("usuarios.index")), 400
    if usuario.perfil == "admin" and usuario.ativo and _contar_admins_ativos() <= 1:
        flash("Não é possível inativar o único admin ativo.", "error")
        return redirect(url_for("usuarios.index")), 400

    usuario.ativo = False
    usuario.atualizado_em = iso_now()
    vinculo.ativo = False
    vinculo.atualizado_em = iso_now()
    db.session.commit()

    registrar_sucesso("usuarios.deactivate", entidade="usuario",
                      entidade_id=usuario.id,
                      descricao=f"Usuário desativado: #{usuario.id}",
                      propriedade_id=propriedade.id, request=request)
    flash("Usuário inativado.", "success")
    return redirect(url_for("usuarios.index"))
