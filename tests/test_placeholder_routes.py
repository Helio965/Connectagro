"""Testes de fumaça das rotas da fundação Flask.

Verifica apenas que as rotas principais respondem HTTP 200. Não testa CRUD,
banco, login real ou seed.
"""
import pytest

ROTAS = [
    "/",
    "/health",
    "/auth/",
    "/culturas/",
    "/glebas/",
    "/defensivos/",
    "/fertilizantes/",
    "/financeiro/",
    "/upload/",
    "/equipe/",
    "/colheita/",
    "/mapa/",
    "/ia/",
    "/relatorios/",
]


@pytest.mark.parametrize("rota", ROTAS)
def test_rota_responde_200(client, rota):
    resp = client.get(rota)
    assert resp.status_code == 200
