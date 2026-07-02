"""Serviço de auditoria do ConnectAgro (Fase 7.3).

Registra ações sensíveis na tabela ``log_auditoria``. Funções de conveniência:

- ``registrar_evento`` — registro genérico.
- ``registrar_sucesso`` — atalho com resultado ``sucesso``.
- ``registrar_falha`` — atalho com resultado ``falha``.
- ``registrar_negado`` — atalho com resultado ``negado`` (permissão negada).
- ``mascarar_email`` — oculta parcialmente o e-mail para exibição nos logs.

A auditoria **nunca quebra o fluxo principal**: uma falha ao gravar log não
impede a ação do usuário.
"""
from ..extensions import db
from ..models.log_auditoria import LogAuditoria


def _safe_session_get_user_id():
    """Obtém o user_id da sessão de forma segura, sem importar ciclo."""
    try:
        from flask import session
        return session.get("user_id")
    except Exception:
        return None


def _safe_propriedade_id():
    """Obtém o propriedade_id do contexto de forma segura."""
    try:
        from ..utils.contexto import propriedade_atual
        prop = propriedade_atual()
        return prop.id if prop else None
    except Exception:
        return None


def _request_info(request):
    """Extrai IP e user-agent do request de forma segura."""
    if request is None:
        return None, None
    try:
        ip = request.remote_addr
        ua = str(request.user_agent)[:300] if request.user_agent else None
        return ip, ua
    except Exception:
        return None, None


def mascarar_email(email):
    """Oculta parcialmente o e-mail para logs. Ex.: a***@exemplo.com."""
    if not email or "@" not in email:
        return "***"
    local, dominio = email.split("@", 1)
    if len(local) <= 1:
        return f"*@{dominio}"
    return f"{local[0]}***@{dominio}"


def registrar_evento(
    acao,
    *,
    entidade=None,
    entidade_id=None,
    resultado="sucesso",
    descricao=None,
    usuario_id=None,
    propriedade_id=None,
    request=None,
):
    """Registra um evento de auditoria. Nunca levanta exceção."""
    try:
        ip, ua = _request_info(request)
        if usuario_id is None:
            usuario_id = _safe_session_get_user_id()
        if propriedade_id is None:
            propriedade_id = _safe_propriedade_id()

        log = LogAuditoria(
            usuario_id=usuario_id,
            propriedade_id=propriedade_id,
            acao=acao,
            entidade=entidade,
            entidade_id=entidade_id,
            resultado=resultado,
            descricao=descricao[:500] if descricao else None,
            ip=ip,
            user_agent=ua,
        )
        db.session.add(log)
        db.session.commit()
    except Exception:
        # A auditoria nunca quebra o fluxo principal.
        try:
            db.session.rollback()
        except Exception:
            pass


def registrar_sucesso(acao, *, entidade=None, entidade_id=None, descricao=None,
                      usuario_id=None, propriedade_id=None, request=None):
    """Atalho para evento com resultado ``sucesso``."""
    registrar_evento(
        acao,
        entidade=entidade,
        entidade_id=entidade_id,
        resultado="sucesso",
        descricao=descricao,
        usuario_id=usuario_id,
        propriedade_id=propriedade_id,
        request=request,
    )


def registrar_falha(acao, *, entidade=None, entidade_id=None, descricao=None,
                     usuario_id=None, propriedade_id=None, request=None):
    """Atalho para evento com resultado ``falha``."""
    registrar_evento(
        acao,
        entidade=entidade,
        entidade_id=entidade_id,
        resultado="falha",
        descricao=descricao,
        usuario_id=usuario_id,
        propriedade_id=propriedade_id,
        request=request,
    )


def registrar_negado(acao, *, entidade=None, entidade_id=None, descricao=None,
                      usuario_id=None, propriedade_id=None, request=None):
    """Atalho para evento com resultado ``negado`` (permissão negada)."""
    registrar_evento(
        acao,
        entidade=entidade,
        entidade_id=entidade_id,
        resultado="negado",
        descricao=descricao,
        usuario_id=usuario_id,
        propriedade_id=propriedade_id,
        request=request,
    )
