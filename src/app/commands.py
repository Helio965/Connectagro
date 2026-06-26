"""Comandos CLI do ConnectAgro.

Comando ``flask init-db``: cria o schema do banco SQLite via ``db.create_all()``.
**Não** popula dados, **não** importa seed e **não** cria migrations. O banco
gerado não deve ser versionado.
"""
import click
from flask.cli import with_appcontext

from .extensions import db


@click.command("init-db")
@with_appcontext
def init_db():
    """Cria o schema SQLite (sem popular dados nem importar seed)."""
    # Importa os modelos para registrar as tabelas no metadata antes de criar.
    from . import models  # noqa: F401

    db.create_all()
    click.echo("Schema SQLite criado com sucesso.")


def register_commands(app):
    """Registra os comandos CLI na aplicação."""
    app.cli.add_command(init_db)
