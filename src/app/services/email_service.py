"""E-mails transacionais do ConnectAgro (Flask-Mail).

Regras:

- Envio **fail-safe**: falha de SMTP nunca derruba o fluxo chamador; a função
  registra ``warning`` no log e retorna ``False``.
- Nada sensível em logs: apenas e-mail mascarado — nunca senha, token puro,
  link completo ou credenciais SMTP.
- Sem ``MAIL_ATIVO`` (flag + credenciais completas) nenhum envio é tentado.
- Senhas nunca são enviadas por e-mail; os e-mails carregam apenas o link de
  definição/redefinição, que é expirável e de uso único.
"""
from flask import current_app, render_template
from flask_mail import Message

from ..extensions import mail
from .auditoria_service import mascarar_email


def email_ativo():
    """Indica se o envio real de e-mail está habilitado e configurado."""
    return bool(current_app.config.get("MAIL_ATIVO"))


def montar_link_absoluto(caminho):
    """Monta link absoluto usando ``APP_BASE_URL`` quando configurada.

    ``caminho`` deve ser um path absoluto da aplicação (ex.: ``/auth/...``).
    """
    base = (current_app.config.get("APP_BASE_URL") or "").strip().rstrip("/")
    if base:
        return f"{base}{caminho}"
    return caminho


def enviar_email(destinatarios, assunto, template, **contexto):
    """Renderiza ``templates/emails/<template>`` e envia via Flask-Mail.

    Retorna ``True`` em caso de sucesso e ``False`` quando o envio está
    inativo ou falhou (fail-safe: nunca propaga exceção).
    """
    if isinstance(destinatarios, str):
        destinatarios = [destinatarios]

    if not email_ativo():
        return False

    try:
        corpo_html = render_template(f"emails/{template}", **contexto)
        mensagem = Message(
            subject=assunto,
            recipients=destinatarios,
            html=corpo_html,
        )
        mail.send(mensagem)
        return True
    except Exception:  # noqa: BLE001 — fail-safe deliberado
        mascarados = ", ".join(mascarar_email(d) for d in destinatarios)
        current_app.logger.warning(
            "Falha ao enviar e-mail '%s' para %s", assunto, mascarados,
        )
        return False


def email_convite_definir_senha(usuario, link_definir):
    """Convite de boas-vindas com link para o usuário definir a própria senha."""
    minutos = current_app.config.get("PASSWORD_INVITE_TOKEN_MINUTES", 24 * 60)
    return enviar_email(
        usuario.email,
        "Bem-vindo(a) ao ConnectAgro — defina sua senha",
        "convite_definir_senha.html",
        nome=usuario.nome,
        link_definir=link_definir,
        validade_horas=max(1, minutos // 60),
    )


def email_recuperacao_senha(usuario, link_reset):
    """E-mail de recuperação de senha (fluxo 'esqueci minha senha')."""
    minutos = current_app.config.get("PASSWORD_RESET_TOKEN_MINUTES", 30)
    return enviar_email(
        usuario.email,
        "ConnectAgro — redefinição de senha",
        "recuperacao_senha.html",
        nome=usuario.nome,
        link_reset=link_reset,
        validade_minutos=minutos,
    )
