"""Rotas de autenticação (login/logout/recuperação de senha) do ConnectAgro."""
from flask import (
    current_app,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)

from ...models import Usuario
from ...services.auditoria_service import (
    mascarar_email,
    registrar_evento,
    registrar_falha,
    registrar_sucesso,
)
from ...services.email_service import (
    email_ativo,
    email_recuperacao_senha,
    montar_link_absoluto,
)
from ...services.password_reset_service import (
    redefinir_senha_com_token,
    solicitar_reset_por_email,
    validar_token_reset,
)
from ...utils.auth import (
    is_authenticated,
    login_usuario,
    logout_usuario,
    usuario_atual,
    verificar_senha,
)
from . import auth_bp

# Mensagem genérica para evitar enumeração de e-mails.
MENSAGEM_RESET_GENERICA = (
    "Se o e-mail estiver cadastrado e ativo, um link de redefinição será "
    "disponibilizado conforme o ambiente."
)
MENSAGEM_TOKEN_INVALIDO = "Link de redefinição inválido, expirado ou já utilizado."


@auth_bp.route("/")
def index():
    """Raiz do módulo: redireciona para a tela de login."""
    return redirect(url_for("auth.login"))


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    # Já autenticado: vai direto ao dashboard.
    if is_authenticated():
        return redirect(url_for("dashboard.index"))

    if request.method == "POST":
        email = (request.form.get("email") or "").strip().lower()
        senha = request.form.get("senha") or ""

        usuario = Usuario.query.filter_by(email=email).first()

        # Mensagem genérica para credenciais inválidas (não vaza detalhes).
        if usuario is None or not verificar_senha(usuario.senha_hash, senha):
            registrar_falha(
                "auth.login.falha",
                entidade="usuario",
                entidade_id=(usuario.id if usuario else None),
                descricao=f"Falha de login para {mascarar_email(email)}",
                usuario_id=(usuario.id if usuario else None),
                request=request,
            )
            flash("E-mail ou senha inválidos.", "error")
            return render_template("auth/login.html"), 401

        if not usuario.ativo:
            registrar_falha(
                "auth.login.falha",
                entidade="usuario",
                entidade_id=usuario.id,
                descricao="Login bloqueado: usuário inativo",
                usuario_id=usuario.id,
                request=request,
            )
            flash("Usuário inativo. Procure o administrador.", "error")
            return render_template("auth/login.html"), 403

        login_usuario(usuario)
        registrar_sucesso(
            "auth.login.sucesso",
            entidade="usuario",
            entidade_id=usuario.id,
            descricao=f"Login de {mascarar_email(usuario.email)}",
            usuario_id=usuario.id,
            request=request,
        )
        flash(f"Bem-vindo(a), {usuario.nome}.", "success")
        return redirect(url_for("dashboard.index"))

    return render_template("auth/login.html")


@auth_bp.route("/logout")
def logout():
    atual = usuario_atual()
    usuario_id = atual["id"] if atual else None
    if usuario_id is not None:
        registrar_sucesso(
            "auth.logout",
            entidade="usuario",
            entidade_id=usuario_id,
            descricao="Logout de sessão",
            usuario_id=usuario_id,
            request=request,
        )
    logout_usuario()
    flash("Sessão encerrada.", "success")
    return redirect(url_for("auth.login"))


@auth_bp.route("/esqueci-senha", methods=["GET", "POST"])
def esqueci_senha():
    """Solicitação de redefinição de senha.

    Resposta sempre genérica (não revela se o e-mail existe). Em ambientes
    locais/dev/teste (``PASSWORD_RESET_SHOW_DEV_LINK``), exibe o link gerado
    para uso manual — não há envio real de e-mail nesta fase.
    """
    if request.method == "POST":
        email = request.form.get("email") or ""
        resultado = solicitar_reset_por_email(email, request=request)

        email_norm = (email or "").strip().lower()
        usuario = Usuario.query.filter_by(email=email_norm).first() if email_norm else None
        registrar_evento(
            "auth.password_reset.solicitado",
            entidade="usuario",
            entidade_id=(usuario.id if usuario else None),
            resultado="sucesso",
            descricao=f"Solicitação de redefinição para {mascarar_email(email_norm)}",
            usuario_id=(usuario.id if usuario else None),
            request=request,
        )

        # Com SMTP configurado, envia o e-mail real de recuperação
        # (fail-safe: falha de envio não altera a resposta genérica).
        if resultado.get("token") and usuario is not None and email_ativo():
            link = montar_link_absoluto(
                url_for("auth.redefinir_senha", token=resultado["token"])
            )
            email_recuperacao_senha(usuario, link)

        dev_link = None
        if (not email_ativo()
                and current_app.config.get("PASSWORD_RESET_SHOW_DEV_LINK")
                and resultado.get("token")):
            dev_link = url_for("auth.redefinir_senha", token=resultado["token"])

        flash(MENSAGEM_RESET_GENERICA, "info")
        return render_template("auth/esqueci_senha.html", dev_link=dev_link)

    return render_template("auth/esqueci_senha.html", dev_link=None)


def _fluxo_senha_com_token(token, *, definicao=False):
    """Fluxo compartilhado de redefinição (reset) e definição (convite).

    ``definicao=True`` só muda o texto exibido — a validação do token, o
    uso único, a expiração e o hash da senha são idênticos.
    """
    endpoint = "auth.definir_senha" if definicao else "auth.redefinir_senha"
    registro = validar_token_reset(token)
    if registro is None:
        registrar_falha(
            "auth.password_reset.token_invalido",
            entidade="senha_reset_token",
            descricao="Tentativa com token inválido, expirado ou usado",
            request=request,
        )
        flash(MENSAGEM_TOKEN_INVALIDO, "error")
        return render_template(
            "auth/redefinir_senha.html", token=token, token_valido=False,
            definicao=definicao, form_endpoint=endpoint,
        ), 400

    usuario_id_token = registro.usuario_id

    if request.method == "POST":
        nova_senha = request.form.get("nova_senha") or ""
        confirmar_senha = request.form.get("confirmar_senha") or ""
        ok, erros = redefinir_senha_com_token(token, nova_senha, confirmar_senha)
        if not ok:
            for erro in erros:
                flash(erro, "error")
            # Se o token deixou de ser válido (ex.: usado/expirado entre passos),
            # não exibimos o formulário novamente.
            ainda_valido = validar_token_reset(token) is not None
            return render_template(
                "auth/redefinir_senha.html", token=token, token_valido=ainda_valido,
                definicao=definicao, form_endpoint=endpoint,
            ), 400
        acao = ("auth.password_definida" if definicao
                else "auth.password_reset.redefinido")
        descricao = ("Senha definida via convite"
                     if definicao else "Senha redefinida via token")
        registrar_sucesso(
            acao,
            entidade="usuario",
            entidade_id=usuario_id_token,
            descricao=descricao,
            usuario_id=usuario_id_token,
            request=request,
        )
        mensagem = ("Senha definida com sucesso. Faça login para começar."
                    if definicao
                    else "Senha redefinida com sucesso. Faça login novamente.")
        flash(mensagem, "success")
        return redirect(url_for("auth.login"))

    return render_template(
        "auth/redefinir_senha.html", token=token, token_valido=True,
        definicao=definicao, form_endpoint=endpoint,
    )


@auth_bp.route("/redefinir-senha/<token>", methods=["GET", "POST"])
def redefinir_senha(token):
    """Redefinição de senha mediante token válido, expirável e de uso único."""
    return _fluxo_senha_com_token(token, definicao=False)


@auth_bp.route("/definir-senha/<token>", methods=["GET", "POST"])
def definir_senha(token):
    """Definição de senha de novo usuário (convite) — mesmo token seguro."""
    return _fluxo_senha_com_token(token, definicao=True)
