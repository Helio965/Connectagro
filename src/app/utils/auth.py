"""Utilitário de autenticação do ConnectAgro (MVP).

Autenticação simples baseada em **sessão Flask** + **werkzeug.security**.
As permissões finas por perfil ficam em ``utils.permissions``. A sessão guarda
apenas dados mínimos do usuário — **nunca** a senha.
"""
from functools import wraps

from flask import flash, g, has_request_context, redirect, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from ..extensions import db
from ..models import Usuario


def _cache_usuario(usuario):
    # g pertence ao app context: associar ao request também evita reaproveitar
    # o cache quando testes/CLI mantêm um app context aberto entre requisições.
    g._auth_request = request._get_current_object()
    g._auth_usuario = usuario


def _limpar_sessao_local():
    session.clear()
    _cache_usuario(None)


def _usuario_validado():
    if not has_request_context():
        return None
    if g.get("_auth_request") is request._get_current_object():
        return g._auth_usuario
    if "user_id" not in session:
        _cache_usuario(None)
        return None

    from .permissions import PERFIS_OFICIAIS

    uid, versao = session.get("user_id"), session.get("auth_version")
    # bool é subclasse de int, mas não é um identificador/epoch válido.
    if (type(uid) is not int or not 1 <= uid <= 2**63 - 1
            or type(versao) is not int or not 1 <= versao <= 2**63 - 1):
        _limpar_sessao_local()
        return None
    usuario = db.session.get(Usuario, uid, populate_existing=True)
    if (usuario is None or not usuario.ativo
            or usuario.perfil not in PERFIS_OFICIAIS
            or usuario.auth_version != versao):
        _limpar_sessao_local()
        return None
    _cache_usuario(usuario)
    return usuario


def gerar_hash_senha(senha):
    """Gera o hash seguro de uma senha."""
    return generate_password_hash(senha)


def verificar_senha(senha_hash, senha):
    """Verifica uma senha contra o hash armazenado."""
    if not senha_hash:
        return False
    return check_password_hash(senha_hash, senha)


def login_usuario(usuario):
    """Emite identificação e epoch; nome/e-mail/perfil vêm sempre do banco."""
    from .permissions import PERFIS_OFICIAIS

    if (not usuario.ativo or usuario.perfil not in PERFIS_OFICIAIS
            or type(usuario.id) is not int or usuario.id < 1
            or type(usuario.auth_version) is not int or usuario.auth_version < 1):
        raise ValueError("Usuário inválido para autenticação.")
    session.clear()
    session["user_id"] = usuario.id
    session["auth_version"] = usuario.auth_version
    session.permanent = True
    _cache_usuario(usuario)


def logout_usuario():
    """Revoga todas as sessões desse usuário e limpa o navegador atual.

    Uma cópia anterior do cookie também deixa de autenticar. Cookie inválido
    nunca pode revogar sessões novas: só um usuário já validado é revogado.
    """
    usuario = _usuario_validado()
    if usuario is not None:
        usuario.revogar_sessoes()
        db.session.commit()
    _limpar_sessao_local()


def is_authenticated():
    """Indica se o usuário real e a versão da sessão continuam válidos."""
    return _usuario_validado() is not None


def usuario_atual():
    """Interface compatível com os módulos, derivada do usuário validado."""
    usuario = _usuario_validado()
    if usuario is None:
        return None
    return {
        "id": usuario.id,
        "email": usuario.email,
        "nome": usuario.nome,
        "perfil": usuario.perfil,
    }


def login_required(view):
    """Protege uma view: exige usuário autenticado, senão redireciona ao login."""

    @wraps(view)
    def wrapped(*args, **kwargs):
        if not is_authenticated():
            flash("É necessário fazer login para acessar esta página.", "warning")
            return redirect(url_for("auth.login"))
        return view(*args, **kwargs)

    return wrapped
