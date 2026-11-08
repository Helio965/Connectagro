"""Upgrade real preserva usuários e defaults, em SQLite descartável."""
from pathlib import Path

from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from flask_migrate import upgrade
from sqlalchemy import text

from app.extensions import db
from app.models import Usuario


def test_migration_auth_version_preserva_usuarios_legados(app):
    migrations = str(Path(__file__).resolve().parents[1] / "migrations")
    with app.app_context():
        upgrade(directory=migrations, revision="b4f2c9d8a1e7")
        with db.engine.begin() as connection:
            connection.execute(text(
                "INSERT INTO usuario (nome,email,senha_hash,perfil,ativo,criado_em) "
                "VALUES ('Legado','legacy@example.invalid','opaque-test-hash','tecnico',1,'2026-01-01')"
            ))
        upgrade(directory=migrations)
        legacy = Usuario.query.filter_by(email="legacy@example.invalid").one()
        assert legacy.nome == "Legado"
        assert legacy.senha_hash == "opaque-test-hash"
        assert legacy.perfil == "tecnico" and legacy.ativo
        assert legacy.criado_em == "2026-01-01" and legacy.auth_version == 1
        with db.engine.begin() as connection:
            connection.execute(text(
                "INSERT INTO usuario (nome,email,senha_hash,perfil,ativo,criado_em) "
                "VALUES ('Novo','new@example.invalid','another-test-hash','trabalhador',1,'2026-01-02')"
            ))
        assert Usuario.query.filter_by(email="new@example.invalid").one().auth_version == 1
        with db.engine.connect() as connection:
            assert compare_metadata(MigrationContext.configure(connection), db.metadata) == []
            table_sql = connection.execute(text(
                "SELECT sql FROM sqlite_master WHERE type='table' AND name='usuario'"
            )).scalar()
            assert "AUTOINCREMENT" in table_sql
