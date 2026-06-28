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


# Usuários de teste do MVP (idempotente). Perfis oficiais: admin, tecnico, trabalhador.
USUARIOS_TESTE = [
    ("Administrador ConnectAgro", "admin@connectagro.com", "admin123", "admin"),
    ("Técnico ConnectAgro", "tecnico@connectagro.com", "tecnico123", "tecnico"),
    ("Trabalhador ConnectAgro", "trabalhador@connectagro.com", "trabalhador123", "trabalhador"),
]


@click.command("seed-users")
@with_appcontext
def seed_users():
    """Cria os usuários de teste do MVP (idempotente; não sobrescreve senha)."""
    from .models import Usuario
    from .utils.auth import gerar_hash_senha

    criados, existentes = 0, 0
    for nome, email, senha, perfil in USUARIOS_TESTE:
        if Usuario.query.filter_by(email=email).first() is not None:
            existentes += 1
            click.echo(f"  já existe: {email} ({perfil})")
            continue
        db.session.add(Usuario(
            nome=nome, email=email, perfil=perfil, ativo=True,
            senha_hash=gerar_hash_senha(senha),
        ))
        criados += 1
        click.echo(f"  criado:    {email} ({perfil})")
    db.session.commit()
    click.echo(
        f"Usuários de teste — criados: {criados}, já existentes: {existentes}. "
        "Senhas armazenadas como hash."
    )


def register_commands(app):
    """Registra os comandos CLI na aplicação."""
    app.cli.add_command(init_db)
    app.cli.add_command(validate_catalog_seed)
    app.cli.add_command(import_catalog_seed)
    app.cli.add_command(seed_users)
