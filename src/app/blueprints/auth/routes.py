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
from ...services.password_reset_service import (
    redefinir_senha_com_token,
    solicitar_reset_por_email,
    validar_token_reset,
)
from ...utils.auth import (
    is_authenticated,
    login_usuario,
    logout_usuario,
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
            flash("E-mail ou senha inválidos.", "error")
            return render_template("auth/login.html"), 401

        if not usuario.ativo:
            flash("Usuário inativo. Procure o administrador.", "error")
            return render_template("auth/login.html"), 403

        login_usuario(usuario)
        flash(f"Bem-vindo(a), {usuario.nome}.", "success")
        return redirect(url_for("dashboard.index"))

    return render_template("auth/login.html")


@auth_bp.route("/logout")
def logout():
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

        dev_link = None
        if current_app.config.get("PASSWORD_RESET_SHOW_DEV_LINK") and resultado.get("token"):
            dev_link = url_for("auth.redefinir_senha", token=resultado["token"])

        flash(MENSAGEM_RESET_GENERICA, "info")
        return render_template("auth/esqueci_senha.html", dev_link=dev_link)

    return render_template("auth/esqueci_senha.html", dev_link=None)


@auth_bp.route("/redefinir-senha/<token>", methods=["GET", "POST"])
def redefinir_senha(token):
    """Redefinição de senha mediante token válido, expirável e de uso único."""
    registro = validar_token_reset(token)
    if registro is None:
        flash(MENSAGEM_TOKEN_INVALIDO, "error")
        return render_template(
            "auth/redefinir_senha.html", token=token, token_valido=False
        ), 400

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
                "auth/redefinir_senha.html", token=token, token_valido=ainda_valido
            ), 400
        flash("Senha redefinida com sucesso. Faça login novamente.", "success")
        return redirect(url_for("auth.login"))

    return render_template(
        "auth/redefinir_senha.html", token=token, token_valido=True
    )
