"""Extensões centralizadas do ConnectAgro.

Este módulo apenas centraliza a instância ``db`` (Flask-SQLAlchemy), criada sem
aplicação e inicializada na Application Factory (``create_app``) via ``init_app``.
Os modelos de domínio ficam em ``src/app/models/`` e usam esta mesma instância.
"""
from flask_sqlalchemy import SQLAlchemy

# ORM oficial do MVP (Flask-SQLAlchemy). Modelos definidos em app/models/.
db = SQLAlchemy()
