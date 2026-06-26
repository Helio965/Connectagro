"""Testes mínimos da fundação Flask (Application Factory e rotas básicas)."""


def test_create_app_testing(app):
    """A factory cria a aplicação no modo de testes."""
    assert app is not None
    assert app.config["TESTING"] is True


def test_health(client):
    """/health responde 200 com JSON {status: ok, app: ConnectAgro}."""
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "ok"
    assert data["app"] == "ConnectAgro"


def test_index(client):
    """A rota inicial (dashboard) responde 200."""
    resp = client.get("/")
    assert resp.status_code == 200
