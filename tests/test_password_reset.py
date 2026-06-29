"""Testes da Fase 7.2 — Recuperação de senha (token seguro, expirável, dev-link).

Usam SQLite em memória (fixture ``app``). Token puro nunca é persistido; só o
hash. Não há envio real de e-mail.
"""
import hashlib
import re
from datetime import datetime, timedelta, timezone

import pytest

from app.extensions import db
from app.utils.auth import gerar_hash_senha

TOKEN_RE = re.compile(r'name="csrf_token" value="([^"]+)"')
GENERICA = "Se o e-mail estiver cadastrado e ativo"
DEV_BLOCK = "Link de redefinição para ambiente local"


def extrair_csrf_token(html):
    match = TOKEN_RE.search(html)
    assert match, "csrf_token não encontrado no HTML"
    return match.group(1)


def _criar_usuario(email, senha, ativo=True, perfil="admin"):
    from app.models import Usuario

    usuario = Usuario(nome=email, email=email, perfil=perfil, ativo=ativo,
                      senha_hash=gerar_hash_senha(senha))
    db.session.add(usuario)
    db.session.commit()
    return usuario


@pytest.fixture
def db_app(app):
    with app.app_context():
        db.create_all()
        _criar_usuario("admin@connectagro.com", "senha-antiga", ativo=True)
        _criar_usuario("inativo@connectagro.com", "inativo123", ativo=False)
    return app


def _solicitar_token(app, email):
    """Gera um token via serviço e devolve o token puro (fluxo dev)."""
    from app.services.password_reset_service import solicitar_reset_por_email

    with app.app_context():
        return solicitar_reset_por_email(email).get("token")


def _contar_tokens(app, email=None):
    from app.models import SenhaResetToken, Usuario

    with app.app_context():
        consulta = SenhaResetToken.query
        if email is not None:
            usuario = Usuario.query.filter_by(email=email).first()
            consulta = consulta.filter_by(usuario_id=usuario.id)
        return consulta.count()


# --- Fluxo de solicitação --------------------------------------------------

def test_login_tem_link_esqueci_senha(db_app):
    html = db_app.test_client().get("/auth/login").data.decode("utf-8")
    assert "/auth/esqueci-senha" in html
    assert "Esqueci minha senha" in html


def test_get_esqueci_senha_200(db_app):
    resp = db_app.test_client().get("/auth/esqueci-senha")
    assert resp.status_code == 200


def test_post_esqueci_senha_email_existente_mensagem_generica(db_app):
    resp = db_app.test_client().post("/auth/esqueci-senha",
                                     data={"email": "admin@connectagro.com"})
    assert resp.status_code == 200
    assert GENERICA in resp.data.decode("utf-8")


def test_post_esqueci_senha_email_inexistente_mesma_mensagem(db_app):
    resp = db_app.test_client().post("/auth/esqueci-senha",
                                     data={"email": "naoexiste@connectagro.com"})
    assert resp.status_code == 200
    assert GENERICA in resp.data.decode("utf-8")


def test_email_inexistente_nao_cria_token(db_app):
    db_app.test_client().post("/auth/esqueci-senha",
                              data={"email": "naoexiste@connectagro.com"})
    assert _contar_tokens(db_app) == 0


def test_usuario_inativo_nao_cria_token(db_app):
    db_app.test_client().post("/auth/esqueci-senha",
                              data={"email": "inativo@connectagro.com"})
    assert _contar_tokens(db_app) == 0


def test_usuario_ativo_cria_token_com_hash_sem_texto_puro(db_app):
    from app.models import SenhaResetToken

    token = _solicitar_token(db_app, "admin@connectagro.com")
    assert token
    with db_app.app_context():
        registro = SenhaResetToken.query.one()
        esperado = hashlib.sha256(token.encode("utf-8")).hexdigest()
        assert registro.token_hash == esperado
        assert registro.token_hash != token
        assert len(registro.token_hash) == 64
        # O token puro não deve aparecer em nenhuma coluna textual.
        for valor in (registro.token_hash, registro.ip_solicitacao,
                      registro.user_agent_solicitacao):
            assert valor != token


def test_token_criado_tem_expiracao(db_app):
    from app.models import SenhaResetToken

    _solicitar_token(db_app, "admin@connectagro.com")
    with db_app.app_context():
        registro = SenhaResetToken.query.one()
        assert registro.expira_em
        expira = datetime.fromisoformat(registro.expira_em)
        assert expira > datetime.now(timezone.utc)


def test_dev_link_aparece_quando_configurado(db_app):
    resp = db_app.test_client().post("/auth/esqueci-senha",
                                     data={"email": "admin@connectagro.com"})
    corpo = resp.data.decode("utf-8")
    assert DEV_BLOCK in corpo
    assert "/auth/redefinir-senha/" in corpo


def test_dev_link_nao_aparece_quando_desativado(db_app):
    db_app.config["PASSWORD_RESET_SHOW_DEV_LINK"] = False
    resp = db_app.test_client().post("/auth/esqueci-senha",
                                     data={"email": "admin@connectagro.com"})
    corpo = resp.data.decode("utf-8")
    assert DEV_BLOCK not in corpo
    assert "/auth/redefinir-senha/" not in corpo
    # mas a mensagem genérica continua aparecendo
    assert GENERICA in corpo
    # e o token foi criado normalmente no backend
    assert _contar_tokens(db_app) == 1


# --- Redefinição -----------------------------------------------------------

def test_get_redefinir_token_valido_mostra_formulario(db_app):
    token = _solicitar_token(db_app, "admin@connectagro.com")
    resp = db_app.test_client().get(f"/auth/redefinir-senha/{token}")
    assert resp.status_code == 200
    assert 'name="nova_senha"' in resp.data.decode("utf-8")


def test_get_redefinir_token_invalido_retorna_erro(db_app):
    resp = db_app.test_client().get("/auth/redefinir-senha/token-falso")
    assert resp.status_code == 400
    assert "inválido, expirado ou já utilizado" in resp.data.decode("utf-8")


def test_get_redefinir_token_expirado_retorna_erro(db_app):
    from app.models import SenhaResetToken

    token = _solicitar_token(db_app, "admin@connectagro.com")
    with db_app.app_context():
        registro = SenhaResetToken.query.one()
        registro.expira_em = (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()
        db.session.commit()
    resp = db_app.test_client().get(f"/auth/redefinir-senha/{token}")
    assert resp.status_code == 400


def test_post_redefinir_senha_curta_falha(db_app):
    token = _solicitar_token(db_app, "admin@connectagro.com")
    resp = db_app.test_client().post(
        f"/auth/redefinir-senha/{token}",
        data={"nova_senha": "123", "confirmar_senha": "123"})
    assert resp.status_code == 400
    assert "pelo menos 6 caracteres" in resp.data.decode("utf-8")


def test_post_redefinir_confirmacao_divergente_falha(db_app):
    token = _solicitar_token(db_app, "admin@connectagro.com")
    resp = db_app.test_client().post(
        f"/auth/redefinir-senha/{token}",
        data={"nova_senha": "senha-nova", "confirmar_senha": "outra-coisa"})
    assert resp.status_code == 400
    assert "confirmação de senha não confere" in resp.data.decode("utf-8")


def test_post_redefinir_token_valido_altera_senha(db_app):
    from app.models import Usuario

    token = _solicitar_token(db_app, "admin@connectagro.com")
    resp = db_app.test_client().post(
        f"/auth/redefinir-senha/{token}",
        data={"nova_senha": "senha-nova", "confirmar_senha": "senha-nova"})
    assert resp.status_code == 302
    assert "/auth/login" in resp.headers["Location"]
    with db_app.app_context():
        from app.utils.auth import verificar_senha
        usuario = Usuario.query.filter_by(email="admin@connectagro.com").first()
        assert verificar_senha(usuario.senha_hash, "senha-nova")


def test_nova_senha_armazenada_como_hash(db_app):
    from app.models import Usuario

    token = _solicitar_token(db_app, "admin@connectagro.com")
    db_app.test_client().post(
        f"/auth/redefinir-senha/{token}",
        data={"nova_senha": "senha-nova", "confirmar_senha": "senha-nova"})
    with db_app.app_context():
        usuario = Usuario.query.filter_by(email="admin@connectagro.com").first()
        assert usuario.senha_hash != "senha-nova"
        assert usuario.senha_hash.startswith(("pbkdf2:", "scrypt:"))


def test_token_usado_marcado_como_usado(db_app):
    from app.models import SenhaResetToken

    token = _solicitar_token(db_app, "admin@connectagro.com")
    db_app.test_client().post(
        f"/auth/redefinir-senha/{token}",
        data={"nova_senha": "senha-nova", "confirmar_senha": "senha-nova"})
    with db_app.app_context():
        registro = SenhaResetToken.query.one()
        assert registro.usado is True
        assert registro.usado_em


def test_token_usado_nao_pode_ser_reutilizado(db_app):
    token = _solicitar_token(db_app, "admin@connectagro.com")
    client = db_app.test_client()
    client.post(f"/auth/redefinir-senha/{token}",
                data={"nova_senha": "senha-nova", "confirmar_senha": "senha-nova"})
    # segunda tentativa com o mesmo token
    resp = client.post(f"/auth/redefinir-senha/{token}",
                       data={"nova_senha": "outra-senha", "confirmar_senha": "outra-senha"})
    assert resp.status_code == 400


def test_login_antigo_falha_apos_redefinir(db_app):
    token = _solicitar_token(db_app, "admin@connectagro.com")
    client = db_app.test_client()
    client.post(f"/auth/redefinir-senha/{token}",
                data={"nova_senha": "senha-nova", "confirmar_senha": "senha-nova"})
    resp = client.post("/auth/login",
                       data={"email": "admin@connectagro.com", "senha": "senha-antiga"})
    assert resp.status_code == 401


def test_login_novo_funciona_apos_redefinir(db_app):
    token = _solicitar_token(db_app, "admin@connectagro.com")
    client = db_app.test_client()
    client.post(f"/auth/redefinir-senha/{token}",
                data={"nova_senha": "senha-nova", "confirmar_senha": "senha-nova"})
    resp = client.post("/auth/login",
                       data={"email": "admin@connectagro.com", "senha": "senha-nova"})
    assert resp.status_code == 302
    assert resp.headers["Location"].endswith("/")


def test_usuario_inativado_depois_nao_redefine(db_app):
    from app.models import Usuario

    token = _solicitar_token(db_app, "admin@connectagro.com")
    with db_app.app_context():
        usuario = Usuario.query.filter_by(email="admin@connectagro.com").first()
        usuario.ativo = False
        db.session.commit()
    resp = db_app.test_client().post(
        f"/auth/redefinir-senha/{token}",
        data={"nova_senha": "senha-nova", "confirmar_senha": "senha-nova"})
    assert resp.status_code == 400
    with db_app.app_context():
        from app.utils.auth import verificar_senha
        usuario = Usuario.query.filter_by(email="admin@connectagro.com").first()
        # senha não foi alterada e usuário continua inativo
        assert verificar_senha(usuario.senha_hash, "senha-antiga")
        assert usuario.ativo is False


def test_solicitar_novo_token_invalida_anteriores(db_app):
    from app.models import SenhaResetToken

    token_antigo = _solicitar_token(db_app, "admin@connectagro.com")
    token_novo = _solicitar_token(db_app, "admin@connectagro.com")
    assert token_antigo != token_novo
    with db_app.app_context():
        assert SenhaResetToken.query.count() == 2
        usados = SenhaResetToken.query.filter_by(usado=True).count()
        assert usados == 1
    # token antigo não funciona mais
    resp = db_app.test_client().get(f"/auth/redefinir-senha/{token_antigo}")
    assert resp.status_code == 400
    # token novo funciona
    resp = db_app.test_client().get(f"/auth/redefinir-senha/{token_novo}")
    assert resp.status_code == 200


# --- CSRF ------------------------------------------------------------------

@pytest.fixture
def app_csrf(app):
    app.config["WTF_CSRF_ENABLED"] = True
    with app.app_context():
        db.create_all()
        _criar_usuario("admin@connectagro.com", "senha-antiga", ativo=True)
    return app


def test_csrf_post_esqueci_senha_sem_token_400(app_csrf):
    resp = app_csrf.test_client().post("/auth/esqueci-senha",
                                       data={"email": "admin@connectagro.com"})
    assert resp.status_code == 400


def test_csrf_post_esqueci_senha_com_token_funciona(app_csrf):
    client = app_csrf.test_client()
    token = extrair_csrf_token(client.get("/auth/esqueci-senha").data.decode("utf-8"))
    resp = client.post("/auth/esqueci-senha",
                       data={"email": "admin@connectagro.com", "csrf_token": token})
    assert resp.status_code == 200
    assert GENERICA in resp.data.decode("utf-8")


def test_csrf_post_redefinir_sem_token_400(app_csrf):
    from app.services.password_reset_service import solicitar_reset_por_email

    with app_csrf.app_context():
        token = solicitar_reset_por_email("admin@connectagro.com").get("token")
    resp = app_csrf.test_client().post(
        f"/auth/redefinir-senha/{token}",
        data={"nova_senha": "senha-nova", "confirmar_senha": "senha-nova"})
    assert resp.status_code == 400


def test_csrf_post_redefinir_com_token_funciona(app_csrf):
    from app.services.password_reset_service import solicitar_reset_por_email
    from app.utils.auth import verificar_senha
    from app.models import Usuario

    with app_csrf.app_context():
        token = solicitar_reset_por_email("admin@connectagro.com").get("token")
    client = app_csrf.test_client()
    csrf = extrair_csrf_token(
        client.get(f"/auth/redefinir-senha/{token}").data.decode("utf-8"))
    resp = client.post(f"/auth/redefinir-senha/{token}", data={
        "nova_senha": "senha-nova",
        "confirmar_senha": "senha-nova",
        "csrf_token": csrf,
    })
    assert resp.status_code == 302
    with app_csrf.app_context():
        usuario = Usuario.query.filter_by(email="admin@connectagro.com").first()
        assert verificar_senha(usuario.senha_hash, "senha-nova")
