"""Contrato do runtime Alembic, sem acessar bancos externos ou dados reais."""
from io import StringIO
from pathlib import Path
import warnings

import pytest
from alembic import command
from alembic.script import ScriptDirectory
from flask_migrate import check, upgrade
from sqlalchemy import inspect, text
from sqlalchemy.engine import make_url

from app import create_app
from app.extensions import db


MIGRATIONS = str(Path(__file__).resolve().parents[1] / "migrations")


@pytest.mark.filterwarnings("error::DeprecationWarning")
def test_upgrade_e_check_efetivos_sem_api_depreciada(app):
    """A correção precisa permitir upgrade/check reais com avisos fatais."""
    with app.app_context():
        config = app.extensions["migrate"].migrate.get_config(MIGRATIONS)
        heads = ScriptDirectory.from_config(config).get_heads()
        assert len(heads) == 1
        upgrade(directory=MIGRATIONS)
        check(directory=MIGRATIONS)
        with db.engine.connect() as connection:
            assert connection.execute(text(
                "SELECT version_num FROM alembic_version")).scalar_one() == heads[0]
            assert connection.execute(text("PRAGMA foreign_key_check")).all() == []
        assert set(inspect(db.engine).get_table_names()) == set(db.metadata.tables) | {
            "alembic_version"}


@pytest.mark.parametrize("direct_url", [
    "sqlite:///nao-deve-ser-criado.sqlite",
    "postgresql+psycopg2://offline:example@unreachable.invalid/direct",
])
@pytest.mark.filterwarnings("error::DeprecationWarning")
def test_sqlite_migra_engine_da_app_e_ignora_direct_url(app, tmp_path, direct_url):
    """DIRECT_URL não pode trocar o banco SQLite nem criar arquivo paralelo."""
    arquivo = tmp_path / "nao-deve-ser-criado.sqlite"
    if direct_url.startswith("sqlite"):
        direct_url = f"sqlite:///{arquivo}"
    app.config["SQLALCHEMY_DIRECT_URI"] = direct_url
    with app.app_context():
        upgrade(directory=MIGRATIONS)
        assert "usuario" in inspect(db.engine).get_table_names()
        assert db.engine.url.database == ":memory:"
        check(directory=MIGRATIONS)
    assert not arquivo.exists()


@pytest.mark.parametrize("usar_direct", [False, True])
def test_postgres_offline_preserva_url_e_escaping_sem_conexao(monkeypatch, usar_direct):
    """Exercita o roteamento SQL offline; não a compatibilidade PG online."""
    app_url = "postgresql+psycopg2://offline:example%25pass@app.invalid/application"
    direct_url = "postgresql+psycopg2://offline:other%25pass@direct.invalid/migrations"
    monkeypatch.setenv("DATABASE_URL", app_url)
    monkeypatch.setenv("DIRECT_URL", direct_url if usar_direct else "")
    monkeypatch.setenv("FLASK_ENV", "development")
    application = create_app("development")
    with application.app_context(), warnings.catch_warnings():
        warnings.simplefilter("error", DeprecationWarning)
        config = application.extensions["migrate"].migrate.get_config(MIGRATIONS)
        config.output_buffer = StringIO()
        # A revisão inicial é SQL puro. Revisões posteriores têm preflights
        # de dados e devem rodar online em base descartável.
        command.upgrade(config, "97642b24c238", sql=True)
        expected = direct_url if usar_direct else app_url
        assert make_url(config.get_main_option("sqlalchemy.url")) == make_url(expected)
        assert "CREATE TABLE usuario" in config.output_buffer.getvalue()
        assert "SERIAL" in config.output_buffer.getvalue()
        assert "alembic_version" in config.output_buffer.getvalue()
