"""Configuração por ambiente do ConnectAgro.

Segredos e caminhos vêm de variáveis de ambiente (ver ``.env.example``).
Nenhum segredo real deve ser fixado no código.
"""
import os


def _env_bool(name, default="true"):
    """Lê booleano simples de variável de ambiente."""
    return os.environ.get(name, default).lower() in ("1", "true", "yes", "on")


class BaseConfig:
    """Configuração base comum a todos os ambientes."""

    SECRET_KEY = os.environ.get("SECRET_KEY", "change-this-in-production")
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", "sqlite:///connectagro.db")
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


class DevelopmentConfig(BaseConfig):
    """Ambiente de desenvolvimento."""

    DEBUG = True
    # Em desenvolvimento, exibir o link de redefinição facilita o uso local
    # (não há envio real de e-mail nesta fase).
    PASSWORD_RESET_SHOW_DEV_LINK = _env_bool("PASSWORD_RESET_SHOW_DEV_LINK", "true")


class TestingConfig(BaseConfig):
    """Ambiente de testes — banco SQLite em memória, isolado."""

    TESTING = True
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False
    PASSWORD_RESET_SHOW_DEV_LINK = True


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
