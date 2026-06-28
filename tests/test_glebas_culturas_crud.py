"""Testes do CRUD de Glebas e Culturas (Etapa 5.2) + associação cultura↔gleba."""
import pytest

from app.extensions import db
from app.utils.auth import gerar_hash_senha


def _criar_usuario(email):
    from app.models import Usuario

    u = Usuario(nome=email, email=email, perfil="tecnico", ativo=True,
                senha_hash=gerar_hash_senha("senha123"))
    db.session.add(u)
    db.session.commit()
    return u


@pytest.fixture
def app_db(app):
    with app.app_context():
        db.create_all()
        _criar_usuario("a@connectagro.com")
        _criar_usuario("b@connectagro.com")
    return app


def _login(app_db, email):
    client = app_db.test_client()
    client.post("/auth/login", data={"email": email, "senha": "senha123"})
    return client


# --- Glebas ---------------------------------------------------------------

def test_criar_gleba(app_db):
    from app.models import Gleba

    client = _login(app_db, "a@connectagro.com")
    resp = client.post("/glebas/nova",
                       data={"nome": "Talhão 1", "area_ha": "12,5",
                             "tipo_solo": "argiloso"})
    assert resp.status_code == 302
    with app_db.app_context():
        g = Gleba.query.filter_by(nome="Talhão 1").first()
        assert g is not None
        assert g.area_ha == 12.5
        assert g.tipo_solo == "argiloso"


def test_gleba_exige_nome(app_db):
    client = _login(app_db, "a@connectagro.com")
    resp = client.post("/glebas/nova", data={"nome": ""})
    assert resp.status_code == 400


def test_editar_gleba(app_db):
    from app.models import Gleba

    client = _login(app_db, "a@connectagro.com")
    client.post("/glebas/nova", data={"nome": "G1"})
    with app_db.app_context():
        gid = Gleba.query.filter_by(nome="G1").first().id
    resp = client.post(f"/glebas/{gid}/editar", data={"nome": "G1 editada", "area_ha": "3"})
    assert resp.status_code == 302
    with app_db.app_context():
        g = db.session.get(Gleba, gid)
        assert g.nome == "G1 editada"
        assert g.area_ha == 3.0
        assert g.atualizado_em is not None


def test_remover_gleba(app_db):
    from app.models import Gleba

    client = _login(app_db, "a@connectagro.com")
    client.post("/glebas/nova", data={"nome": "G-del"})
    with app_db.app_context():
        gid = Gleba.query.filter_by(nome="G-del").first().id
    resp = client.post(f"/glebas/{gid}/remover")
    assert resp.status_code == 302
    with app_db.app_context():
        assert db.session.get(Gleba, gid) is None


def test_escopo_gleba_por_propriedade(app_db):
    """Usuário B não pode editar gleba do usuário A (404)."""
    from app.models import Gleba

    client_a = _login(app_db, "a@connectagro.com")
    client_a.post("/glebas/nova", data={"nome": "Gleba A"})
    with app_db.app_context():
        gid = Gleba.query.filter_by(nome="Gleba A").first().id

    client_b = _login(app_db, "b@connectagro.com")
    assert client_b.get(f"/glebas/{gid}/editar").status_code == 404
    assert client_b.post(f"/glebas/{gid}/remover").status_code == 404


# --- Culturas + associação -------------------------------------------------

def test_criar_cultura_com_glebas(app_db):
    from app.models import Cultura, Gleba

    client = _login(app_db, "a@connectagro.com")
    client.post("/glebas/nova", data={"nome": "Gleba X"})
    with app_db.app_context():
        gid = Gleba.query.filter_by(nome="Gleba X").first().id

    resp = client.post("/culturas/nova",
                       data={"nome": "Soja", "status": "planejada",
                             "safra": "2025/2026", "glebas": [str(gid)]})
    assert resp.status_code == 302
    with app_db.app_context():
        c = Cultura.query.filter_by(nome="Soja").first()
        assert c is not None
        assert c.status == "planejada"
        assert {cg.gleba_id for cg in c.cultura_glebas} == {gid}


def test_editar_cultura_sincroniza_glebas(app_db):
    from app.models import Cultura, Gleba

    client = _login(app_db, "a@connectagro.com")
    client.post("/glebas/nova", data={"nome": "G-A"})
    client.post("/glebas/nova", data={"nome": "G-B"})
    with app_db.app_context():
        ga = Gleba.query.filter_by(nome="G-A").first().id
        gb = Gleba.query.filter_by(nome="G-B").first().id
    client.post("/culturas/nova", data={"nome": "Milho", "glebas": [str(ga)]})
    with app_db.app_context():
        cid = Cultura.query.filter_by(nome="Milho").first().id

    # troca a associação de G-A para G-B
    resp = client.post(f"/culturas/{cid}/editar",
                       data={"nome": "Milho", "status": "em_andamento",
                             "glebas": [str(gb)]})
    assert resp.status_code == 302
    with app_db.app_context():
        c = db.session.get(Cultura, cid)
        assert c.status == "em_andamento"
        assert {cg.gleba_id for cg in c.cultura_glebas} == {gb}


def test_cultura_exige_nome(app_db):
    client = _login(app_db, "a@connectagro.com")
    assert client.post("/culturas/nova", data={"nome": ""}).status_code == 400


def test_remover_cultura_remove_associacoes(app_db):
    from app.models import Cultura, CulturaGleba, Gleba

    client = _login(app_db, "a@connectagro.com")
    client.post("/glebas/nova", data={"nome": "G-rm"})
    with app_db.app_context():
        gid = Gleba.query.filter_by(nome="G-rm").first().id
    client.post("/culturas/nova", data={"nome": "Feijão", "glebas": [str(gid)]})
    with app_db.app_context():
        cid = Cultura.query.filter_by(nome="Feijão").first().id

    resp = client.post(f"/culturas/{cid}/remover")
    assert resp.status_code == 302
    with app_db.app_context():
        assert db.session.get(Cultura, cid) is None
        assert CulturaGleba.query.filter_by(cultura_id=cid).count() == 0


def test_crud_exige_login(app_db):
    """Sem login, as rotas de CRUD redirecionam para o login."""
    client = app_db.test_client()
    for url in ("/glebas/nova", "/culturas/nova"):
        resp = client.get(url)
        assert resp.status_code == 302
        assert "/auth/login" in resp.headers["Location"]
