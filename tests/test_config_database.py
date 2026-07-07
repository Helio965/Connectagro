"""Testes da resolução/normalização de URL de banco (estilo NEXO).

Cobrem apenas configuração — nenhum teste conecta em PostgreSQL real.
"""
from app.config import (
    TestingConfig,
    _normalizar_database_url,
    resolve_database_uri,
    resolve_direct_uri,
)

SQLITE_FALLBACK = "sqlite:///connectagro.db"


def _limpar_env(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("DIRECT_URL", raising=False)


def test_sem_database_url_usa_sqlite_local(monkeypatch):
    _limpar_env(monkeypatch)
    assert resolve_database_uri() == SQLITE_FALLBACK


def test_database_url_vazia_usa_sqlite_local(monkeypatch):
    _limpar_env(monkeypatch)
    monkeypatch.setenv("DATABASE_URL", "   ")
    assert resolve_database_uri() == SQLITE_FALLBACK


def test_postgres_scheme_normaliza_para_psycopg2(monkeypatch):
    _limpar_env(monkeypatch)
    monkeypatch.setenv("DATABASE_URL", "postgres://user:pass@host:6543/postgres")
    assert resolve_database_uri() == (
        "postgresql+psycopg2://user:pass@host:6543/postgres"
    )


def test_postgresql_scheme_normaliza_para_psycopg2(monkeypatch):
    _limpar_env(monkeypatch)
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@host:5432/db")
    assert resolve_database_uri() == "postgresql+psycopg2://user:pass@host:5432/db"


def test_url_ja_com_driver_permanece_igual(monkeypatch):
    _limpar_env(monkeypatch)
    url = "postgresql+psycopg2://user:pass@host:5432/db"
    monkeypatch.setenv("DATABASE_URL", url)
    assert resolve_database_uri() == url


def test_sqlite_url_permanece_igual(monkeypatch):
    _limpar_env(monkeypatch)
    monkeypatch.setenv("DATABASE_URL", "sqlite:///outro.db")
    assert resolve_database_uri() == "sqlite:///outro.db"


def test_remove_parametros_incompativeis_do_pooler():
    url = ("postgres://u:p@host:6543/postgres"
           "?pgbouncer=true&connection_limit=1&pool_timeout=10&schema=public")
    assert _normalizar_database_url(url) == (
        "postgresql+psycopg2://u:p@host:6543/postgres"
    )


def test_preserva_parametros_compativeis_como_sslmode():
    url = "postgresql://u:p@host:5432/db?sslmode=require&pgbouncer=true"
    assert _normalizar_database_url(url) == (
        "postgresql+psycopg2://u:p@host:5432/db?sslmode=require"
    )


def test_query_de_sqlite_nao_e_alterada():
    # A limpeza de parâmetros vale apenas para URLs PostgreSQL.
    url = "sqlite:///arquivo.db?mode=ro"
    assert _normalizar_database_url(url) == url


def test_direct_url_e_respeitada_quando_existe(monkeypatch):
    _limpar_env(monkeypatch)
    monkeypatch.setenv("DATABASE_URL", "postgres://u:p@host:6543/postgres")
    monkeypatch.setenv("DIRECT_URL", "postgres://u:p@host:5432/postgres")
    assert resolve_direct_uri() == "postgresql+psycopg2://u:p@host:5432/postgres"
    # A aplicação continua na URL do pooler.
    assert resolve_database_uri() == "postgresql+psycopg2://u:p@host:6543/postgres"


def test_direct_url_ausente_cai_para_database_url(monkeypatch):
    _limpar_env(monkeypatch)
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@host:5432/db")
    assert resolve_direct_uri() == "postgresql+psycopg2://u:p@host:5432/db"


def test_direct_url_sem_nada_cai_para_sqlite(monkeypatch):
    _limpar_env(monkeypatch)
    assert resolve_direct_uri() == SQLITE_FALLBACK


def test_testing_config_usa_sqlite_em_memoria():
    assert TestingConfig.SQLALCHEMY_DATABASE_URI == "sqlite:///:memory:"
    assert TestingConfig.SQLALCHEMY_DIRECT_URI == "sqlite:///:memory:"


# --- Regressões da revisão adversarial (casos extremos reais) ------------

def test_url_postgres_sem_host_socket_local_continua_valida():
    # postgresql:///db (socket local) não pode virar 'postgresql+psycopg2:/db'.
    from sqlalchemy.engine import make_url

    resultado = _normalizar_database_url("postgresql:///connectagro")
    parsed = make_url(resultado)
    assert parsed.drivername == "postgresql+psycopg2"
    assert parsed.database == "connectagro"
    assert parsed.host is None


def test_senha_com_colchete_nao_quebra_import():
    # '[' desbalanceado derrubava o import do módulo (ValueError do urlsplit).
    # O make_url entende a senha e a re-codifica; nunca deve levantar exceção.
    from sqlalchemy.engine import make_url

    resultado = _normalizar_database_url("postgres://user:pa[ss@host:5432/db")
    parsed = make_url(resultado)
    assert parsed.password == "pa[ss"
    assert parsed.host == "host"


def test_url_iliegivel_para_o_make_url_passa_intacta():
    # URLs que nem o SQLAlchemy parseia passam adiante sem exceção; o erro
    # (se houver) aparece na criação do engine, nunca no import do módulo.
    url = "isso nao e uma url"
    assert _normalizar_database_url(url) == url


def test_senha_com_interrogacao_preservada():
    from sqlalchemy.engine import make_url

    resultado = _normalizar_database_url("postgres://user:pa?ss@host:6543/db")
    parsed = make_url(resultado)
    assert parsed.password == "pa?ss"
    assert parsed.host == "host"
    assert parsed.port == 6543
    assert parsed.database == "db"


def test_senha_com_cerquilha_nao_pula_limpeza_do_pooler():
    from sqlalchemy.engine import make_url

    resultado = _normalizar_database_url(
        "postgres://user:p#ss@host:6543/db?pgbouncer=true")
    parsed = make_url(resultado)
    assert parsed.password == "p#ss"
    assert "pgbouncer" not in parsed.query


def test_driver_psycopg3_e_normalizado_para_psycopg2():
    # O projeto instala apenas psycopg2; postgresql+psycopg (psycopg 3)
    # falharia com ModuleNotFoundError na criação do engine.
    resultado = _normalizar_database_url(
        "postgresql+psycopg://u:p@host:6543/db?pgbouncer=true")
    assert resultado.startswith("postgresql+psycopg2://")
    assert "pgbouncer" not in resultado
