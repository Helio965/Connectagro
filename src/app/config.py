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


class DevelopmentConfig(BaseConfig):
    """Ambiente de desenvolvimento."""

    DEBUG = True


class TestingConfig(BaseConfig):
    """Ambiente de testes — banco SQLite em memória, isolado."""

    TESTING = True
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False


class ProductionConfig(BaseConfig):
    """Ambiente de produção."""

    DEBUG = False


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
