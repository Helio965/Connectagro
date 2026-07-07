"""Configuração por ambiente do ConnectAgro.

Segredos e caminhos vêm de variáveis de ambiente (ver ``.env.example``).
Nenhum segredo real deve ser fixado no código.

Banco de dados (estratégia no estilo NEXO):

- ``DATABASE_URL`` é a URL usada pela aplicação. Sem ela, o fallback é o
  SQLite local (``sqlite:///connectagro.db``, resolvido para ``instance/``).
- ``DIRECT_URL`` é opcional e destinada a migrations/conexão direta em
  provedores com pooler (ex.: Supabase usa a porta 6543 via PgBouncer para a
  aplicação e a 5432 para conexão direta).
- URLs ``postgres://``/``postgresql://`` são normalizadas para o driver
  ``postgresql+psycopg2://`` e parâmetros de query exclusivos do pooler
  (``pgbouncer``, ``connection_limit``, ...) são removidos, pois o SQLAlchemy
  não os reconhece.
"""
import os

from dotenv import load_dotenv
from sqlalchemy.engine import make_url

# Carrega o .env da raiz do projeto quando presente. O CLI ``flask`` já faz
# isso automaticamente, mas o entrypoint ``python src/run.py`` não — sem esta
# chamada, um DATABASE_URL definido no .env seria silenciosamente ignorado e
# a aplicação cairia no SQLite local. Não sobrescreve variáveis já definidas.
load_dotenv()

_SQLITE_FALLBACK = "sqlite:///connectagro.db"

# Parâmetros de query usados por Supabase/Prisma/PgBouncer que o
# SQLAlchemy/psycopg2 não aceitam na URL.
_PG_QUERY_PARAMS_INCOMPATIVEIS = {
    "pgbouncer",
    "connection_limit",
    "pool_timeout",
    "schema",
}

# Drivers PostgreSQL reescritos para o psycopg2 (único instalado no projeto).
_PG_DRIVERS_REESCRITOS = {"postgres", "postgresql", "postgresql+psycopg"}


def _normalizar_database_url(url):
    """Normaliza URL de banco vinda do ambiente; retorna ``None`` se vazia.

    Usa o parser do próprio SQLAlchemy (``make_url``), que entende senhas com
    caracteres especiais (``?``, ``#``, ``[``) e URLs sem host (socket local).
    URLs que o SQLAlchemy não parseia passam adiante intactas — o erro, se
    houver, aparece na criação do engine (mesmo comportamento de antes da
    normalização existir), nunca no ``import`` do módulo.
    """
    if not url:
        return None

    url = url.strip()
    if not url:
        return None

    try:
        parsed = make_url(url)
    except Exception:
        return url

    alterada = False

    # Heroku/Supabase às vezes emitem postgres://; guias do SQLAlchemy 2.x
    # sugerem postgresql+psycopg (psycopg 3). O projeto usa psycopg2.
    if parsed.drivername in _PG_DRIVERS_REESCRITOS:
        parsed = parsed.set(drivername="postgresql+psycopg2")
        alterada = True

    if parsed.drivername.startswith("postgresql"):
        query = {
            chave: valor for chave, valor in parsed.query.items()
            if chave.lower() not in _PG_QUERY_PARAMS_INCOMPATIVEIS
        }
        if len(query) != len(parsed.query):
            parsed = parsed.set(query=query)
            alterada = True

    if not alterada:
        return url
    return parsed.render_as_string(hide_password=False)


def resolve_database_uri():
    """URL de banco da aplicação: ``DATABASE_URL`` ou SQLite local."""
    return _normalizar_database_url(os.environ.get("DATABASE_URL")) or _SQLITE_FALLBACK


def resolve_direct_uri():
    """URL de conexão direta (migrations): ``DIRECT_URL`` > ``DATABASE_URL`` > SQLite."""
    return (
        _normalizar_database_url(os.environ.get("DIRECT_URL"))
        or _normalizar_database_url(os.environ.get("DATABASE_URL"))
        or _SQLITE_FALLBACK
    )


def _env_bool(name, default="true"):
    """Lê booleano simples de variável de ambiente."""
    return os.environ.get(name, default).lower() in ("1", "true", "yes", "on")


class BaseConfig:
    """Configuração base comum a todos os ambientes."""

    SECRET_KEY = os.environ.get("SECRET_KEY", "change-this-in-production")
    SQLALCHEMY_DATABASE_URI = resolve_database_uri()
    SQLALCHEMY_DIRECT_URI = resolve_direct_uri()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = os.environ.get("UPLOAD_FOLDER", "instance/uploads")
    MAX_CONTENT_LENGTH = int(os.environ.get("MAX_CONTENT_LENGTH", 16 * 1024 * 1024))
    APP_NAME = "ConnectAgro"
    WTF_CSRF_ENABLED = _env_bool("WTF_CSRF_ENABLED", "true")
    # Recuperação de senha (Fase 7.2): validade do token e exibição do link
    # de redefinição em tela (apenas para ambientes locais/dev/teste).
    PASSWORD_RESET_TOKEN_MINUTES = int(
        os.environ.get("PASSWORD_RESET_TOKEN_MINUTES", 30)
    )
    PASSWORD_RESET_SHOW_DEV_LINK = _env_bool("PASSWORD_RESET_SHOW_DEV_LINK", "false")
    # Convite de definição de senha (novos usuários): validade maior que a do
    # reset, pois depende do destinatário abrir o e-mail (padrão: 24h).
    PASSWORD_INVITE_TOKEN_MINUTES = int(
        os.environ.get("PASSWORD_INVITE_TOKEN_MINUTES", 24 * 60)
    )

    # ------------------------------------------------------------------
    # E-mail transacional (Flask-Mail). MAIL_ATIVO só liga quando a flag
    # está true E servidor/credenciais/sender estão configurados — sem
    # SMTP o sistema não tenta envio real (modo dev usa link em tela).
    # ------------------------------------------------------------------
    MAIL_SERVER = os.environ.get("MAIL_SERVER", "")
    MAIL_PORT = int(os.environ.get("MAIL_PORT", 587))
    MAIL_USE_TLS = _env_bool("MAIL_USE_TLS", "true")
    MAIL_USE_SSL = _env_bool("MAIL_USE_SSL", "false")
    MAIL_USERNAME = os.environ.get("MAIL_USERNAME", "")
    MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD", "")
    MAIL_DEFAULT_SENDER = os.environ.get("MAIL_DEFAULT_SENDER", "")
    MAIL_SUPPRESS_SEND = _env_bool("MAIL_SUPPRESS_SEND", "false")
    # Nunca imprimir o diálogo SMTP (contém credenciais codificadas em
    # base64). Sem isto, Flask-Mail herda app.debug e vaza o AUTH no console.
    MAIL_DEBUG = _env_bool("MAIL_DEBUG", "false")
    MAIL_ATIVO = (
        _env_bool("MAIL_ATIVO", "false")
        and bool(os.environ.get("MAIL_SERVER"))
        and bool(os.environ.get("MAIL_USERNAME"))
        and bool(os.environ.get("MAIL_PASSWORD"))
        and bool(os.environ.get("MAIL_DEFAULT_SENDER"))
    )
    # Base pública para montar links absolutos em e-mails (fallback: host
    # da requisição via url_for(_external=True)).
    APP_BASE_URL = os.environ.get("APP_BASE_URL", "")


class DevelopmentConfig(BaseConfig):
    """Ambiente de desenvolvimento."""

    DEBUG = True
    # Em desenvolvimento, exibir o link de redefinição facilita o uso local
    # (não há envio real de e-mail nesta fase).
    PASSWORD_RESET_SHOW_DEV_LINK = _env_bool("PASSWORD_RESET_SHOW_DEV_LINK", "true")


class TestingConfig(BaseConfig):
    """Ambiente de testes — banco SQLite em memória, isolado.

    Nunca depende de PostgreSQL: mesmo com ``DATABASE_URL``/``DIRECT_URL``
    no ambiente, os testes usam SQLite em memória.
    """

    TESTING = True
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SQLALCHEMY_DIRECT_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False
    PASSWORD_RESET_SHOW_DEV_LINK = True
    # Testes nunca enviam e-mail real.
    MAIL_ATIVO = False
    MAIL_SUPPRESS_SEND = True


class ProductionConfig(BaseConfig):
    """Ambiente de produção."""

    DEBUG = False
    # Em produção, nunca exibir o link/token de redefinição na tela.
    PASSWORD_RESET_SHOW_DEV_LINK = False


# Mapa de seleção por nome de ambiente.
CONFIG_BY_NAME = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
}


def get_config(config_name=None):
    """Resolve a classe de configuração a partir do nome ou de ``FLASK_ENV``."""
    name = config_name or os.environ.get("FLASK_ENV", "development")
    return CONFIG_BY_NAME.get(name, DevelopmentConfig)
