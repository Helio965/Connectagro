import logging
from logging.config import fileConfig

from flask import current_app

from alembic import context

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
fileConfig(config.config_file_name)
logger = logging.getLogger('alembic.env')


def get_engine():
    try:
        # this works with Flask-SQLAlchemy<3 and Alchemical
        return current_app.extensions['migrate'].db.get_engine()
    except (TypeError, AttributeError):
        # this works with Flask-SQLAlchemy>=3
        return current_app.extensions['migrate'].db.engine


def get_engine_url():
    try:
        return get_engine().url.render_as_string(hide_password=False).replace(
            '%', '%%')
    except AttributeError:
        return str(get_engine().url).replace('%', '%%')


def get_direct_url():
    """URL de conexão direta para migrations (``DIRECT_URL``), quando difere
    da URL da aplicação; caso contrário ``None`` (mantém o engine da app).

    Em provedores com pooler (ex.: Supabase/PgBouncer na porta 6543), DDL de
    migrations deve usar a conexão direta (porta 5432). SQLite nunca usa
    conexão direta: o Flask-SQLAlchemy resolve caminhos relativos para
    ``instance/`` no engine da app, e um engine paralelo apontaria para outro
    arquivo. A comparação usa as URIs de configuração (cruas), pela mesma
    razão.
    """
    direta = current_app.config.get('SQLALCHEMY_DIRECT_URI')
    app_uri = current_app.config.get('SQLALCHEMY_DATABASE_URI') or ''
    if not direta or direta.startswith('sqlite'):
        return None
    if app_uri.startswith('sqlite'):
        # Aplicação no fallback SQLite (ex.: só DIRECT_URL definida, sem
        # DATABASE_URL): migrar um Postgres que a app não usa criaria
        # divergência silenciosa entre schema migrado e banco em uso.
        return None
    if direta == app_uri:
        return None
    return direta


# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
_direct_url = get_direct_url()
config.set_main_option(
    'sqlalchemy.url',
    _direct_url.replace('%', '%%') if _direct_url else get_engine_url())
target_db = current_app.extensions['migrate'].db

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def get_metadata():
    if hasattr(target_db, 'metadatas'):
        return target_db.metadatas[None]
    return target_db.metadata


def run_migrations_offline():
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url, target_metadata=get_metadata(), literal_binds=True
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """

    # this callback is used to prevent an auto-migration from being generated
    # when there are no changes to the schema
    # reference: http://alembic.zzzcomputing.com/en/latest/cookbook.html
    def process_revision_directives(context, revision, directives):
        if getattr(config.cmd_opts, 'autogenerate', False):
            script = directives[0]
            if script.upgrade_ops.is_empty():
                directives[:] = []
                logger.info('No changes in schema detected.')

    conf_args = current_app.extensions['migrate'].configure_args
    if conf_args.get("process_revision_directives") is None:
        conf_args["process_revision_directives"] = process_revision_directives

    if _direct_url:
        # Conexão direta (DIRECT_URL) para DDL, evitando o pooler. NullPool
        # (padrão do template do Alembic) garante que a conexão direta —
        # recurso escasso em provedores como Supabase — não fique presa em
        # pool após as migrations.
        from sqlalchemy import create_engine, pool
        connectable = create_engine(_direct_url, poolclass=pool.NullPool)
    else:
        connectable = get_engine()

    try:
        with connectable.connect() as connection:
            context.configure(
                connection=connection,
                target_metadata=get_metadata(),
                **conf_args
            )

            with context.begin_transaction():
                context.run_migrations()
    finally:
        if _direct_url:
            connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
