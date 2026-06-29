"""Autorização por perfil do MVP.

As permissões ficam em código nesta fase: não há tabela de roles/permissões e
não há dependência externa de RBAC.
"""
from functools import wraps

from flask import abort, flash, redirect, url_for

from .auth import is_authenticated, usuario_atual

PERFIS_OFICIAIS = ("admin", "tecnico", "trabalhador")

_ADMIN_PERMISSIONS = {
    "dashboard.view",
    "mapa.view",
    "catalogo.view",
    "relatorios.view",
    "ia.view",
    "glebas.view",
    "glebas.create",
    "glebas.edit",
    "glebas.delete",
    "culturas.view",
    "culturas.create",
    "culturas.edit",
    "culturas.delete",
    "equipe.view",
    "equipe.create",
    "equipe.edit",
    "equipe.delete",
    "financeiro.view",
    "financeiro.create",
    "financeiro.edit",
    "financeiro.delete",
    "colheita.view",
    "colheita.create",
    "colheita.edit",
    "colheita.delete",
    "aplicacoes.view",
    "aplicacoes.create",
    "aplicacoes.edit",
    "aplicacoes.delete",
    "upload.view",
    "upload.create",
    "upload.download",
    "upload.delete",
    "usuarios.view",
    "usuarios.create",
    "usuarios.edit",
    "usuarios.deactivate",
    "auditoria.view",
}

_TECNICO_PERMISSIONS = {
    "dashboard.view",
    "mapa.view",
    "catalogo.view",
    "relatorios.view",
    "ia.view",
    "glebas.view",
    "glebas.create",
    "glebas.edit",
    "culturas.view",
    "culturas.create",
    "culturas.edit",
    "equipe.view",
    "financeiro.view",
    "colheita.view",
    "colheita.create",
    "colheita.edit",
    "aplicacoes.view",
    "aplicacoes.create",
    "aplicacoes.edit",
    "upload.view",
    "upload.create",
    "upload.download",
}

_TRABALHADOR_PERMISSIONS = {
    "dashboard.view",
    "mapa.view",
    "catalogo.view",
    "relatorios.view",
    "ia.view",
    "glebas.view",
    "culturas.view",
    "colheita.view",
    "colheita.create",
    "aplicacoes.view",
    "aplicacoes.create",
    "upload.view",
    "upload.create",
    "upload.download",
}

PERMISSOES_POR_PERFIL = {
    "admin": _ADMIN_PERMISSIONS,
    "tecnico": _TECNICO_PERMISSIONS,
    "trabalhador": _TRABALHADOR_PERMISSIONS,
}


def perfil_atual():
    """Retorna o perfil do usuário autenticado ou ``None``."""
    usuario = usuario_atual()
    if usuario is None:
        return None
    return usuario.get("perfil")


def has_permission(permission):
    """Indica se o perfil atual possui a permissão informada."""
    permissoes = PERMISSOES_POR_PERFIL.get(perfil_atual(), set())
    return permission in permissoes


def can(permission):
    """Alias usado nos templates Jinja."""
    return has_permission(permission)


def require_permission(permission):
    """Protege uma rota autenticada com permissão por perfil."""
    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if not is_authenticated():
                flash("É necessário fazer login para acessar esta página.", "warning")
                return redirect(url_for("auth.login"))
            if not has_permission(permission):
                # Auditoria de permissão negada (import local evita ciclo).
                try:
                    from flask import request
                    from ..services.auditoria_service import registrar_negado
                    registrar_negado(
                        "permissao.negada",
                        entidade="permission",
                        entidade_id=permission,
                        descricao=f"Permissão negada: {permission}",
                        request=request,
                    )
                except Exception:
                    pass
                flash("Você não tem permissão para acessar esta ação.", "error")
                abort(403)
            return view(*args, **kwargs)

        return wrapped

    return decorator
