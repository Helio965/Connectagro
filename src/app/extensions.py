"""Extensões centralizadas do ConnectAgro.

Este módulo apenas centraliza a instância ``db`` (Flask-SQLAlchemy), criada sem
aplicação e inicializada na Application Factory (``create_app``) via ``init_app``.
Os modelos de domínio ficam em ``src/app/models/`` e usam esta mesma instância.
"""
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect

# ORM oficial do MVP (Flask-SQLAlchemy). Modelos definidos em app/models/.
db = SQLAlchemy()

# Migrations (Flask-Migrate/Alembic), inicializado na Application Factory.
migrate = Migrate()

# Proteção CSRF global dos formulários POST.
csrf = CSRFProtect()
