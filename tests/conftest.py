"""Configuração compartilhada dos testes do ConnectAgro.

Adiciona ``src/`` ao ``sys.path`` para permitir ``from app import create_app``
e expõe fixtures de aplicação/cliente de teste.
"""
import os
import sys

import pytest

SRC = os.path.join(os.path.dirname(os.path.dirname(__file__)), "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)

from app import create_app  # noqa: E402


@pytest.fixture
def app():
    application = create_app("testing")
    yield application


@pytest.fixture
def client(app):
    return app.test_client()
