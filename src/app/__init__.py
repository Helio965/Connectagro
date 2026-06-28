"""Application Factory do ConnectAgro (MVP).

Cria e configura a aplicação Flask: carrega configuração por ambiente,
inicializa extensões, registra blueprints, handlers de erro e a rota de
health check. Nenhum CRUD, banco populado, migration ou seed é executado aqui.
"""
from flask import Flask, jsonify, render_template

from .config import get_config
from .extensions import db, migrate
from .blueprints import register_blueprints
from .commands import register_commands


def create_app(config_name=None):
    """Cria a aplicação Flask configurada.

    :param config_name: ``development`` | ``testing`` | ``production``.
        Quando ``None``, usa ``FLASK_ENV`` (padrão: ``development``).
    """
    app = Flask(__name__)
    app.config.from_object(get_config(config_name))

    # Extensões
    db.init_app(app)

    # Registra os modelos no metadata do SQLAlchemy (não cria tabelas aqui).
    from . import models  # noqa: F401

    # Migrations (Flask-Migrate) — precisa dos modelos já registrados.
    migrate.init_app(app, db)

    # Blueprints dos módulos do MVP
    register_blueprints(app)

    # Comandos CLI (ex.: flask init-db, seed-users)
    register_commands(app)

    # Dados do usuário logado disponíveis nos templates Jinja.
    from .utils.auth import is_authenticated, usuario_atual

    @app.context_processor
    def inject_usuario():
        return {"current_user": usuario_atual(), "is_authenticated": is_authenticated()}

    # Health check
    @app.route("/health")
    def health():
        return jsonify({"status": "ok", "app": app.config.get("APP_NAME", "ConnectAgro")})

    # Handlers de erro
    @app.errorhandler(404)
    def not_found(error):
        return render_template("errors/404.html"), 404

    @app.errorhandler(500)
    def server_error(error):
        return render_template("errors/500.html"), 500

    return app
