"""Testes da Etapa 5.1 — Autenticação real (sessão Flask + Werkzeug).

Usam SQLite em memória (fixture ``app``) e o ``client`` de teste.
"""
import pytest

from app.extensions import db
from app.utils.auth import gerar_hash_senha


@pytest.fixture
def db_app(app):
    """App com schema criado para os testes de autenticação."""
    with app.app_context():
        db.create_all()
        yield app


@pytest.fixture
def usuarios(db_app):
    """Cria usuários de teste (ativo e inativo) com senha em hash."""
    from app.models import Usuario

    with db_app.app_context():
        ativo = Usuario(nome="Admin", email="admin@connectagro.com",
                        perfil="admin", ativo=True,
                        senha_hash=gerar_hash_senha("admin123"))
        inativo = Usuario(nome="Inativo", email="inativo@connectagro.com",
                          perfil="trabalhador", ativo=False,
                          senha_hash=gerar_hash_senha("inativo123"))
        db.session.add_all([ativo, inativo])
        db.session.commit()
    return db_app


def test_login_get_200(usuarios):
    resp = usuarios.test_client().get("/auth/login")
    assert resp.status_code == 200
    assert b"Entrar" in resp.data


def test_login_valido_redireciona_dashboard(usuarios):
    client = usuarios.test_client()
    resp = client.post("/auth/login",
                       data={"email": "admin@connectagro.com", "senha": "admin123"})
    assert resp.status_code == 302
    assert resp.headers["Location"].endswith("/")


def test_login_senha_errada_nao_autentica(usuarios):
    client = usuarios.test_client()
    resp = client.post("/auth/login",
                       data={"email": "admin@connectagro.com", "senha": "errada"})
    assert resp.status_code == 401
    with client.session_transaction() as sess:
        assert "user_id" not in sess


def test_usuario_inativo_nao_loga(usuarios):
    client = usuarios.test_client()
    resp = client.post("/auth/login",
                       data={"email": "inativo@connectagro.com", "senha": "inativo123"})
    assert resp.status_code == 403
    with client.session_transaction() as sess:
        assert "user_id" not in sess


def test_logout_limpa_sessao(usuarios):
    client = usuarios.test_client()
    client.post("/auth/login",
                data={"email": "admin@connectagro.com", "senha": "admin123"})
    with client.session_transaction() as sess:
        assert "user_id" in sess
    client.get("/auth/logout")
    with client.session_transaction() as sess:
        assert "user_id" not in sess


def test_dashboard_sem_login_redireciona(usuarios):
    resp = usuarios.test_client().get("/")
    assert resp.status_code == 302
    assert "/auth/login" in resp.headers["Location"]


def test_modulo_protegido_redireciona(usuarios):
    resp = usuarios.test_client().get("/culturas/")
    assert resp.status_code == 302
    assert "/auth/login" in resp.headers["Location"]


def test_dashboard_com_login_ok(usuarios):
    client = usuarios.test_client()
    client.post("/auth/login",
                data={"email": "admin@connectagro.com", "senha": "admin123"})
    resp = client.get("/")
    assert resp.status_code == 200


def test_health_continua_publico(usuarios):
    resp = usuarios.test_client().get("/health")
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "ok"


def test_sessao_nao_contem_senha(usuarios):
    client = usuarios.test_client()
    client.post("/auth/login",
                data={"email": "admin@connectagro.com", "senha": "admin123"})
    with client.session_transaction() as sess:
        assert "senha" not in sess
        assert "senha_hash" not in sess
        assert sess.get("user_perfil") == "admin"


def test_senha_armazenada_como_hash(usuarios):
    from app.models import Usuario

    with usuarios.app_context():
        u = Usuario.query.filter_by(email="admin@connectagro.com").first()
        assert u.senha_hash != "admin123"
        assert u.senha_hash.startswith(("pbkdf2:", "scrypt:"))


def test_seed_users_idempotente(db_app):
    """O comando seed-users cria os 3 usuários e não duplica em nova execução."""
    from app.models import Usuario

    runner = db_app.test_cli_runner()

    r1 = runner.invoke(args=["seed-users"])
    assert r1.exit_code == 0
    with db_app.app_context():
        assert Usuario.query.count() == 3
        for u in Usuario.query.all():
            assert u.senha_hash and u.senha_hash != ""

    # segunda execução não duplica
    r2 = runner.invoke(args=["seed-users"])
    assert r2.exit_code == 0
    with db_app.app_context():
        assert Usuario.query.count() == 3
