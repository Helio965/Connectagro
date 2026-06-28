"""Comandos CLI do ConnectAgro.

- ``flask init-db``: cria o schema via ``db.create_all()`` (uso pontual/local).
  O fluxo preferido para evoluir o schema passa a ser **migrations**
  (Flask-Migrate): ``flask db upgrade``.
- ``flask validate-catalog-seed``: valida o seed técnico do catálogo.
- ``flask import-catalog-seed``: valida e importa o catálogo técnico
  (``produto_base`` + ``produto_tecnico``), de forma idempotente. **Não** importa
  preço, imagem nem itens bloqueados.

Nenhum comando é executado automaticamente; o banco gerado não é versionado.
"""
import click
from flask.cli import with_appcontext

from .extensions import db


@click.command("init-db")
@with_appcontext
def init_db():
    """Cria o schema SQLite (sem popular dados nem importar seed).

    Útil para uso local pontual; em fluxo com migrations, prefira
    ``flask db upgrade``.
    """
    from . import models  # noqa: F401

    db.create_all()
    click.echo("Schema SQLite criado com sucesso.")


@click.command("validate-catalog-seed")
@with_appcontext
def validate_catalog_seed():
    """Valida o seed técnico do catálogo (sem importar nada)."""
    from .services.catalogo_seed import carregar_seed, validar_seed

    dados = carregar_seed()
    validar_seed(dados)
    click.echo(
        "Seed válido: "
        f"{len(dados['produto_base'])} produto_base, "
        f"{len(dados['produto_tecnico'])} produto_tecnico, "
        f"produto_preco={len(dados['produto_preco'])}, "
        f"produto_imagem={len(dados['produto_imagem'])}."
    )


@click.command("import-catalog-seed")
@with_appcontext
def import_catalog_seed():
    """Valida e importa o catálogo técnico (produto_base + produto_tecnico)."""
    from .services.catalogo_seed import carregar_seed, importar_seed_catalogo

    dados = carregar_seed()
    resumo = importar_seed_catalogo(db.session, dados)
    click.echo(
        "Importação concluída — "
        f"produto_base: +{resumo['base_inseridos']} "
        f"(ignorados {resumo['base_ignorados']}); "
        f"produto_tecnico: +{resumo['tecnico_inseridos']} "
        f"(ignorados {resumo['tecnico_ignorados']}). "
        "Preço e imagem permanecem vazios no MVP."
    )


def register_commands(app):
    """Registra os comandos CLI na aplicação."""
    app.cli.add_command(init_db)
    app.cli.add_command(validate_catalog_seed)
    app.cli.add_command(import_catalog_seed)
