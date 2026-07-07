"""Serviço de recuperação de senha do ConnectAgro (Fase 7.2).

Gera tokens seguros (``secrets.token_urlsafe``), expirável e de uso único.
O banco armazena apenas o **hash SHA-256** do token — o token puro nunca é
persistido. Solicitar um novo reset invalida tokens anteriores abertos.
"""
import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from flask import current_app

from ..extensions import db
from ..models import SenhaResetToken, Usuario
from ..models._helpers import iso_now
from ..utils.auth import gerar_hash_senha


def _hash_token(token):
    """Retorna o SHA-256 hex do token."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _agora_utc():
    """Retorna datetime UTC atual sem microssegundos."""
    return datetime.now(timezone.utc).replace(microsecond=0)


def solicitar_reset_por_email(email, *, request=None):
    """Cria um token de recuperação para o e-mail, se válido e ativo.

    Retorna sempre um dict; inclui ``token`` (puro) apenas se gerado.
    A resposta ao usuário deve ser **sempre genérica** (não revelar existência).
    """
    email_norm = (email or "").strip().lower()
    if not email_norm:
        return {}

    usuario = Usuario.query.filter_by(email=email_norm).first()
    if usuario is None or not usuario.ativo:
        return {}

    # Invalida tokens anteriores abertos do mesmo usuário.
    tokens_abertos = SenhaResetToken.query.filter_by(
        usuario_id=usuario.id, usado=False
    ).all()
    for t in tokens_abertos:
        t.usado = True
        t.usado_em = iso_now()
    if tokens_abertos:
        db.session.commit()

    # Gera novo token.
    token_puro = secrets.token_urlsafe(32)
    minutos = current_app.config.get("PASSWORD_RESET_TOKEN_MINUTES", 30)
    expira = _agora_utc() + timedelta(minutes=minutos)

    registro = SenhaResetToken(
        usuario_id=usuario.id,
        token_hash=_hash_token(token_puro),
        expira_em=expira.isoformat(),
    )
    db.session.add(registro)
    db.session.commit()

    return {"token": token_puro}


def gerar_token_definicao_senha(usuario):
    """Gera token de **definição de senha** (convite de novo usuário).

    Mesma mecânica do reset: invalida tokens abertos do usuário, persiste
    apenas o hash SHA-256, expira e é de uso único. A validade vem de
    ``PASSWORD_INVITE_TOKEN_MINUTES`` (maior que a do reset, pois depende
    do destinatário abrir o e-mail). Retorna o token puro apenas para a
    montagem do link — nunca é persistido.
    """
    if usuario is None or not usuario.ativo:
        return None

    tokens_abertos = SenhaResetToken.query.filter_by(
        usuario_id=usuario.id, usado=False
    ).all()
    for t in tokens_abertos:
        t.usado = True
        t.usado_em = iso_now()
    if tokens_abertos:
        db.session.commit()

    token_puro = secrets.token_urlsafe(32)
    minutos = current_app.config.get("PASSWORD_INVITE_TOKEN_MINUTES", 24 * 60)
    expira = _agora_utc() + timedelta(minutes=minutos)

    registro = SenhaResetToken(
        usuario_id=usuario.id,
        token_hash=_hash_token(token_puro),
        expira_em=expira.isoformat(),
    )
    db.session.add(registro)
    db.session.commit()

    return token_puro


def validar_token_reset(token):
    """Valida um token de recuperação de senha.

    Retorna o registro ``SenhaResetToken`` se válido (não usado, não expirado);
    caso contrário ``None``.
    """
    if not token:
        return None

    token_hash = _hash_token(token)
    registro = SenhaResetToken.query.filter_by(
        token_hash=token_hash, usado=False
    ).first()
    if registro is None:
        return None

    # Verifica expiração.
    try:
        expira = datetime.fromisoformat(registro.expira_em)
        if expira.tzinfo is None:
            expira = expira.replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        return None

    if _agora_utc() > expira:
        return None

    return registro


def redefinir_senha_com_token(token, nova_senha, confirmar_senha):
    """Redefine a senha usando o token.

    Retorna ``(True, [])`` em caso de sucesso ou ``(False, [erros])``
    se houver problemas.
    """
    erros = []
    if not nova_senha or len(nova_senha) < 6:
        erros.append("A nova senha deve ter ao menos 6 caracteres.")
    if nova_senha != confirmar_senha:
        erros.append("A nova senha e a confirmação não coincidem.")
    if erros:
        return False, erros

    registro = validar_token_reset(token)
    if registro is None:
        return False, ["Link de redefinição inválido, expirado ou já utilizado."]

    usuario = Usuario.query.get(registro.usuario_id)
    if usuario is None or not usuario.ativo:
        return False, ["Usuário não encontrado ou inativo."]

    # Atualiza a senha.
    usuario.senha_hash = gerar_hash_senha(nova_senha)
    usuario.atualizado_em = iso_now()

    # Marca o token como usado.
    registro.usado = True
    registro.usado_em = iso_now()

    db.session.commit()
    return True, []
