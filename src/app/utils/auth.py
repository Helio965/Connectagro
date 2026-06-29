"""Utilitário de autenticação do ConnectAgro (MVP).

Autenticação simples baseada em **sessão Flask** + **werkzeug.security**.
As permissões finas por perfil ficam em ``utils.permissions``. A sessão guarda
apenas dados mínimos do usuário — **nunca** a senha.
"""
from functools import wraps

from flask import flash, redirect, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

_SESSION_KEYS = ("user_id", "user_email", "user_nome", "user_perfil")


def gerar_hash_senha(senha):
    """Gera o hash seguro de uma senha."""
    return generate_password_hash(senha)


def verificar_senha(senha_hash, senha):
    """Verifica uma senha contra o hash armazenado."""
    if not senha_hash:
        return False
    return check_password_hash(senha_hash, senha)


def login_usuario(usuario):
    """Registra o usuário na sessão (apenas dados mínimos, sem senha)."""
    session["user_id"] = usuario.id
    session["user_email"] = usuario.email
    session["user_nome"] = usuario.nome
    session["user_perfil"] = usuario.perfil


def logout_usuario():
    """Limpa os dados de autenticação da sessão."""
    for chave in _SESSION_KEYS:
        session.pop(chave, None)


def is_authenticated():
    """Indica se há um usuário autenticado na sessão."""
    return "user_id" in session


def usuario_atual():
    """Retorna um dict leve com os dados do usuário logado, ou ``None``."""
    if not is_authenticated():
        return None
    return {
        "id": session.get("user_id"),
        "email": session.get("user_email"),
        "nome": session.get("user_nome"),
        "perfil": session.get("user_perfil"),
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
