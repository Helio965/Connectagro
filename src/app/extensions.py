"""Extensões centralizadas do ConnectAgro.

As instâncias são criadas aqui, sem aplicação, e inicializadas na Application
Factory (``create_app``) via ``init_app``. Nenhum modelo é definido nesta etapa.
"""
from flask_sqlalchemy import SQLAlchemy

# ORM oficial do MVP (Flask-SQLAlchemy). Modelos serão adicionados em etapa futura.
db = SQLAlchemy()
