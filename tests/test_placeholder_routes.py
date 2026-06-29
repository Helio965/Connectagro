"""Testes de fumaça das rotas, considerando a autenticação (Etapa 5.1).

- Rotas públicas (`/health`, `/auth/login`) respondem 200 sem login.
- Rotas dos módulos são protegidas: sem login redirecionam para `/auth/login`;
  com login respondem 200.
"""
import pytest

from app.extensions import db
from app.utils.auth import gerar_hash_senha

ROTAS_PROTEGIDAS = [
    "/",
    "/culturas/",
    "/glebas/",
    "/defensivos/",
    "/fertilizantes/",
    "/aplicacoes/",
    "/financeiro/",
    "/upload/",
    "/usuarios/",
    "/equipe/",
    "/colheita/",
    "/mapa/",
    "/ia/",
    "/relatorios/",
]


@pytest.fixture
def logged_client(app):
    """Cliente autenticado, com schema criado e um usuário ativo."""
    from app.models import Usuario

    with app.app_context():
        db.create_all()
        db.session.add(Usuario(nome="Admin", email="admin@connectagro.com",
                               perfil="admin", ativo=True,
                               senha_hash=gerar_hash_senha("admin123")))
        db.session.commit()
    client = app.test_client()
    client.post("/auth/login",
                data={"email": "admin@connectagro.com", "senha": "admin123"})
    return client


@pytest.mark.parametrize("rota", ["/health", "/auth/login"])
def test_rotas_publicas_200(client, rota):
    assert client.get(rota).status_code == 200


@pytest.mark.parametrize("rota", ROTAS_PROTEGIDAS)
def test_rotas_protegidas_redirecionam_sem_login(client, rota):
    resp = client.get(rota)
    assert resp.status_code == 302
    assert "/auth/login" in resp.headers["Location"]


@pytest.mark.parametrize("rota", ROTAS_PROTEGIDAS)
def test_rotas_protegidas_200_com_login(logged_client, rota):
    assert logged_client.get(rota).status_code == 200
