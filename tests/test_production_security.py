"""Configuração de produção sem serviços ou credenciais externos."""
from datetime import timedelta
import secrets

import pytest
from sqlalchemy import event

from app import create_app
from app.extensions import db
from app.models import Usuario
from app.utils.auth import gerar_hash_senha


@pytest.fixture
def production_env(monkeypatch, tmp_path):
    monkeypatch.setenv("SECRET_KEY", secrets.token_urlsafe(48))
    monkeypatch.setenv("DATABASE_URL", "sqlite:///" + str(tmp_path / "production-simulation.sqlite"))
    monkeypatch.delenv("DIRECT_URL", raising=False)
    monkeypatch.setenv("FLASK_DEBUG", "0")
    monkeypatch.setenv("APP_BASE_URL", "https://example.invalid")
    return tmp_path


@pytest.mark.parametrize("key", [None, "", "   ", "short", "a" * 64,
    "change-this-in-production", "troque-esta-chave-em-producao",
    "test-secret-key-that-is-long-enough-for-production",
    "0123456789" * 6, "abcdefghijklmnopqrstuvwxyz012345"])
def test_producao_rejeita_chave_ausente_ou_insegura(production_env, monkeypatch, key):
    if key is None:
        monkeypatch.delenv("SECRET_KEY")
    else:
        monkeypatch.setenv("SECRET_KEY", key)
    with pytest.raises(ValueError, match="SECRET_KEY"):
        create_app("production")


def test_producao_chave_estavel_lida_por_criacao(production_env, monkeypatch):
    first = create_app("production")
    second = create_app("production")
    assert first.secret_key == second.secret_key
    monkeypatch.setenv("SECRET_KEY", secrets.token_urlsafe(48))
    third = create_app("production")
    assert third.secret_key != first.secret_key


@pytest.mark.parametrize("url", [None, "", "  ", "not-a-database-url"])
def test_producao_exige_banco_explicito_valido(production_env, monkeypatch, url):
    if url is None:
        monkeypatch.delenv("DATABASE_URL")
    else:
        monkeypatch.setenv("DATABASE_URL", url)
    with pytest.raises(ValueError, match="DATABASE_URL|URL de banco"):
        create_app("production")


@pytest.mark.parametrize("flag", ["1", "true", "on", "banana", "off", " 0 "])
def test_producao_rejeita_debug_por_ambiente(production_env, monkeypatch, flag):
    monkeypatch.setenv("FLASK_DEBUG", flag)
    with pytest.raises(ValueError, match="FLASK_DEBUG"):
        create_app("production")


@pytest.mark.parametrize("base", ["", "http://example.invalid", "https://", "https://user:pass@example.invalid", "https://example.invalid/?query=yes", "https://bad host.invalid", "https://example.invalid\\path"])
def test_producao_exige_origem_canonica_para_nao_usar_host_do_solicitante(production_env, monkeypatch, base):
    monkeypatch.setenv("APP_BASE_URL", base)
    with pytest.raises(ValueError, match="APP_BASE_URL"):
        create_app("production")


@pytest.mark.parametrize("name", ["prodution", "", "dev", "unknown"])
def test_ambiente_desconhecido_nao_cai_em_development(monkeypatch, name):
    with pytest.raises(ValueError, match="Ambiente inválido"):
        create_app(name)
    monkeypatch.setenv("FLASK_ENV", name)
    with pytest.raises(ValueError, match="Ambiente inválido"):
        create_app()


def test_producao_cookies_csrf_debug_e_links_seguros(production_env, monkeypatch):
    from app.config import BaseConfig

    monkeypatch.setenv("WTF_CSRF_ENABLED", "false")
    monkeypatch.setenv("PASSWORD_RESET_SHOW_DEV_LINK", "true")
    # Simula também um import inicial com diagnóstico SMTP habilitado.
    monkeypatch.setattr(BaseConfig, "MAIL_DEBUG", True)
    app = create_app("production")
    assert not app.debug
    assert not app.config["MAIL_DEBUG"]
    assert app.config["WTF_CSRF_ENABLED"]
    assert not app.config["PASSWORD_RESET_SHOW_DEV_LINK"]
    assert app.config["SESSION_COOKIE_HTTPONLY"]
    assert app.config["SESSION_COOKIE_SECURE"]
    assert app.config["SESSION_COOKIE_SAMESITE"] == "Lax"
    assert app.permanent_session_lifetime == timedelta(hours=8)
    response = app.test_client().get("/auth/login", base_url="https://example.invalid")
    cookie = response.headers["Set-Cookie"]
    assert "Secure" in cookie and "HttpOnly" in cookie and "SameSite=Lax" in cookie


def test_seed_producao_bloqueia_antes_de_qualquer_sql(production_env):
    app = create_app("production")
    statements = []
    with app.app_context():
        def observe(*args):
            statements.append(args[2])
        event.listen(db.engine, "before_cursor_execute", observe)
        try:
            response = app.test_cli_runner().invoke(args=["seed-users"])
            assert response.exit_code != 0
            assert "apenas em development ou testing" in response.output
            assert statements == []
            assert not (production_env / "production-simulation.sqlite").exists()
        finally:
            event.remove(db.engine, "before_cursor_execute", observe)


def test_development_preserva_http_local_e_seed_idempotente(monkeypatch, tmp_path):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///" + str(tmp_path / "dev.sqlite"))
    monkeypatch.delenv("DIRECT_URL", raising=False)
    app = create_app("development")
    assert not app.config["SESSION_COOKIE_SECURE"]
    with app.app_context():
        db.create_all()
    runner = app.test_cli_runner()
    assert runner.invoke(args=["seed-users"]).exit_code == 0
    assert runner.invoke(args=["seed-users"]).exit_code == 0
    with app.app_context():
        assert Usuario.query.count() == 3
    assert app.test_client().get("/health").status_code == 200
