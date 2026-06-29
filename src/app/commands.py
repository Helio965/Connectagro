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
    """Cria usuários de teste e vínculos com a propriedade demo."""
    from .models import Propriedade, Usuario, UsuarioPropriedade
    from .utils.auth import gerar_hash_senha

    criados, existentes = 0, 0
    usuarios = {}
    for nome, email, senha, perfil in USUARIOS_TESTE:
        usuario = Usuario.query.filter_by(email=email).first()
        if usuario is not None:
            existentes += 1
            usuarios[email] = usuario
            click.echo(f"  já existe: {email} ({perfil})")
            continue
        usuario = Usuario(
            nome=nome, email=email, perfil=perfil, ativo=True,
            senha_hash=gerar_hash_senha(senha),
        )
        db.session.add(usuario)
        usuarios[email] = usuario
        criados += 1
        click.echo(f"  criado:    {email} ({perfil})")
    db.session.commit()

    admin = usuarios["admin@connectagro.com"]
    propriedade = (Propriedade.query
                   .filter_by(usuario_id=admin.id)
                   .filter_by(nome="Propriedade Demo ConnectAgro")
                   .order_by(Propriedade.id)
                   .first())
    propriedade_criada = False
    if propriedade is None:
        propriedade = Propriedade(
            usuario_id=admin.id,
            nome="Propriedade Demo ConnectAgro",
        )
        db.session.add(propriedade)
        db.session.commit()
        propriedade_criada = True

    vinculos_criados, vinculos_existentes = 0, 0
    for usuario in usuarios.values():
        vinculo = UsuarioPropriedade.query.filter_by(
            usuario_id=usuario.id,
            propriedade_id=propriedade.id,
        ).first()
        if vinculo is None:
            db.session.add(UsuarioPropriedade(
                usuario_id=usuario.id,
                propriedade_id=propriedade.id,
                ativo=True,
                criado_por_id=admin.id,
            ))
            vinculos_criados += 1
        else:
            vinculos_existentes += 1
    db.session.commit()
    click.echo(
        f"Usuários de teste — criados: {criados}, já existentes: {existentes}. "
        "Senhas armazenadas como hash."
    )
    click.echo(
        "Propriedade demo — "
        f"{'criada' if propriedade_criada else 'já existente'}; "
        f"vínculos criados: {vinculos_criados}, "
        f"já existentes: {vinculos_existentes}."
    )


def register_commands(app):
    """Registra os comandos CLI na aplicação."""
    app.cli.add_command(init_db)
    app.cli.add_command(validate_catalog_seed)
    app.cli.add_command(import_catalog_seed)
    app.cli.add_command(seed_users)
