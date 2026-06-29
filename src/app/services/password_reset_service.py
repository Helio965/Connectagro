"""Serviço de recuperação/redefinição de senha (Fase 7.2 — MVP ampliado).

Fluxo **local/dev** seguro e testável, **sem envio real de e-mail**:

- gera um token seguro (``secrets.token_urlsafe``);
- persiste apenas o **hash** do token (SHA-256), nunca o token puro;
- o token **expira** e, uma vez **usado**, não pode ser reutilizado;
- ao solicitar um novo reset, tokens abertos anteriores são invalidados;
- usuário inativo / e-mail inexistente **não** geram token válido, mas a rota
  responde sempre com mensagem genérica (evita enumeração de e-mails);
- a redefinição **não** reativa usuário inativo e **não** loga automaticamente.
"""
import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from flask import current_app

from ..extensions import db
from ..models import SenhaResetToken, Usuario
from ..models._helpers import iso_now
from ..utils.auth import gerar_hash_senha

SENHA_MINIMA = 6


def hash_token(token):
    """Hash estável e seguro do token puro (SHA-256 hex)."""
    return hashlib.sha256((token or "").encode("utf-8")).hexdigest()


def _agora():
    return datetime.now(timezone.utc).replace(microsecond=0)


def _expira_em_iso(minutos):
    return (_agora() + timedelta(minutes=minutos)).isoformat()


def token_expirado(token_model):
    """Indica se o token já passou da validade (``expira_em``)."""
    if token_model is None or not token_model.expira_em:
        return True
    try:
        expira = datetime.fromisoformat(token_model.expira_em)
    except (TypeError, ValueError):
        return True
    if expira.tzinfo is None:
        expira = expira.replace(tzinfo=timezone.utc)
    return _agora() >= expira


def _dado_request(request, attr, header=None, limite=255):
    if request is None:
        return None
    valor = None
    if header is not None:
        valor = request.headers.get(header)
    else:
        valor = getattr(request, attr, None)
    if valor is None:
        return None
    return valor[:limite]


def invalidar_tokens_abertos_do_usuario(usuario_id):
    """Marca como usados os tokens abertos (não usados) do usuário."""
    abertos = SenhaResetToken.query.filter_by(
        usuario_id=usuario_id, usado=False
    ).all()
    agora = iso_now()
    for token in abertos:
        token.usado = True
        token.usado_em = agora
    return len(abertos)


def gerar_token_reset(usuario, request=None):
    """Gera um token de reset para o usuário; persiste só o hash.

    Invalida tokens abertos anteriores e retorna o **token puro** (usado apenas
    no fluxo local/dev para montar o link de redefinição).
    """
    invalidar_tokens_abertos_do_usuario(usuario.id)
    token = secrets.token_urlsafe(32)
    minutos = current_app.config.get("PASSWORD_RESET_TOKEN_MINUTES", 30)
    registro = SenhaResetToken(
        usuario_id=usuario.id,
        token_hash=hash_token(token),
        usado=False,
        expira_em=_expira_em_iso(minutos),
        ip_solicitacao=_dado_request(request, "remote_addr", limite=64),
        user_agent_solicitacao=_dado_request(request, None, header="User-Agent"),
    )
    db.session.add(registro)
    db.session.commit()
    return token


def solicitar_reset_por_email(email, request=None):
    """Processa a solicitação de reset por e-mail.

    Retorna sempre um dict ``{"token": <token puro | None>}``. O token só é
    gerado para usuário **existente e ativo**; nos demais casos, retorna
    ``None`` sem criar registro (sem vazar se o e-mail existe).
    """
    email = (email or "").strip().lower()
    resultado = {"token": None}
    if not email:
        return resultado
    usuario = Usuario.query.filter_by(email=email).first()
    if usuario is None or not usuario.ativo:
        return resultado
    resultado["token"] = gerar_token_reset(usuario, request=request)
    return resultado


def validar_token_reset(token):
    """Retorna o registro válido do token, ou ``None``.

    Válido = existe (pelo hash), não usado, não expirado e com usuário
    associado **ativo**.
    """
    if not token:
        return None
    registro = SenhaResetToken.query.filter_by(token_hash=hash_token(token)).first()
    if registro is None or registro.usado or token_expirado(registro):
        return None
    usuario = db.session.get(Usuario, registro.usuario_id)
    if usuario is None or not usuario.ativo:
        return None
    return registro


def validar_nova_senha(nova_senha, confirmar_senha=None):
    """Valida a nova senha e a confirmação. Retorna lista de erros."""
    erros = []
    nova_senha = nova_senha or ""
    if len(nova_senha) < SENHA_MINIMA:
        erros.append(
            f"A nova senha deve ter pelo menos {SENHA_MINIMA} caracteres."
        )
    if confirmar_senha is not None and nova_senha != confirmar_senha:
        erros.append("A confirmação de senha não confere.")
    return erros


def redefinir_senha_com_token(token, nova_senha, confirmar_senha=None):
    """Redefine a senha mediante token válido.

    Retorna ``(ok, erros)``. Marca o token como usado, **não** reativa usuário
    inativo e **não** autentica o usuário.
    """
    registro = validar_token_reset(token)
    if registro is None:
        return False, ["Link de redefinição inválido, expirado ou já utilizado."]

    erros = validar_nova_senha(nova_senha, confirmar_senha)
    if erros:
        return False, erros

    usuario = db.session.get(Usuario, registro.usuario_id)
    usuario.senha_hash = gerar_hash_senha(nova_senha)
    usuario.atualizado_em = iso_now()
    registro.usado = True
    registro.usado_em = iso_now()
    db.session.commit()
    return True, []


def limpar_tokens_expirados_opcional():
    """Remove tokens já expirados (limpeza opcional). Retorna o total removido."""
    removidos = 0
    for registro in SenhaResetToken.query.filter_by(usado=False).all():
        if token_expirado(registro):
            db.session.delete(registro)
            removidos += 1
    if removidos:
        db.session.commit()
    return removidos
