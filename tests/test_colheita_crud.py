"""Testes do CRUD de Colheita (Etapa 5.4) — escopo por propriedade via cultura↔gleba."""
import pytest

from app.extensions import db
from app.utils.auth import gerar_hash_senha


def _setup_usuario_com_associacao(email, cultura_nome="Soja", gleba_nome="Talhão 1"):
    """Cria usuário + propriedade + gleba + cultura + associação. Retorna ids."""
    from app.models import Usuario, Propriedade, Gleba, Cultura, CulturaGleba

    u = Usuario(nome=email, email=email, perfil="tecnico", ativo=True,
                senha_hash=gerar_hash_senha("senha123"))
    db.session.add(u)
    db.session.commit()
    p = Propriedade(usuario_id=u.id, nome="Fazenda " + email)
    db.session.add(p)
    db.session.commit()
    g = Gleba(propriedade_id=p.id, nome=gleba_nome)
    c = Cultura(propriedade_id=p.id, nome=cultura_nome, status="em_andamento")
    db.session.add_all([g, c])
    db.session.commit()
    cg = CulturaGleba(cultura_id=c.id, gleba_id=g.id)
    db.session.add(cg)
    db.session.commit()
    return {"cg_id": cg.id}


@pytest.fixture
def app_db(app):
    with app.app_context():
        db.create_all()
    return app


def _login(app_db, email):
    client = app_db.test_client()
    client.post("/auth/login", data={"email": email, "senha": "senha123"})
    return client


# --- Login obrigatório -----------------------------------------------------

def test_index_exige_login(app_db):
    resp = app_db.test_client().get("/colheita/")
    assert resp.status_code == 302
    assert "/auth/login" in resp.headers["Location"]


def test_nova_exige_login(app_db):
    resp = app_db.test_client().get("/colheita/nova")
    assert resp.status_code == 302
    assert "/auth/login" in resp.headers["Location"]


# --- Criação ---------------------------------------------------------------

def test_criar_colheita(app_db):
    from app.models import ColheitaRegistro

    with app_db.app_context():
        ids = _setup_usuario_com_associacao("a@connectagro.com")
    client = _login(app_db, "a@connectagro.com")
    resp = client.post("/colheita/nova",
                       data={"cultura_gleba_id": str(ids["cg_id"]),
                             "data_colheita": "2026-03-10", "quantidade": "1200,5",
                             "unidade": "kg", "qualidade": "boa"})
    assert resp.status_code == 302
    with app_db.app_context():
        r = ColheitaRegistro.query.first()
        assert r is not None
        assert r.quantidade == 1200.5
        assert r.unidade == "kg"


def test_data_obrigatoria_400(app_db):
    with app_db.app_context():
        ids = _setup_usuario_com_associacao("a@connectagro.com")
    client = _login(app_db, "a@connectagro.com")
    resp = client.post("/colheita/nova",
                       data={"cultura_gleba_id": str(ids["cg_id"]), "data_colheita": ""})
    assert resp.status_code == 400


def test_cultura_gleba_obrigatoria_400(app_db):
    with app_db.app_context():
        _setup_usuario_com_associacao("a@connectagro.com")
    client = _login(app_db, "a@connectagro.com")
    resp = client.post("/colheita/nova",
                       data={"cultura_gleba_id": "", "data_colheita": "2026-03-10"})
    assert resp.status_code == 400


def test_cultura_gleba_inexistente_400(app_db):
    with app_db.app_context():
        _setup_usuario_com_associacao("a@connectagro.com")
    client = _login(app_db, "a@connectagro.com")
    # id inexistente -> validação retorna 400 (documentado)
    resp = client.post("/colheita/nova",
                       data={"cultura_gleba_id": "999999", "data_colheita": "2026-03-10"})
    assert resp.status_code == 400


def test_nao_usa_cultura_gleba_de_outra_propriedade(app_db):
    with app_db.app_context():
        _setup_usuario_com_associacao("a@connectagro.com")
        ids_b = _setup_usuario_com_associacao("b@connectagro.com")
    client_a = _login(app_db, "a@connectagro.com")
    # usuário A tenta usar a associação da propriedade de B -> 400
    resp = client_a.post("/colheita/nova",
                         data={"cultura_gleba_id": str(ids_b["cg_id"]),
                               "data_colheita": "2026-03-10"})
    assert resp.status_code == 400


def test_quantidade_aceita_virgula_e_ponto(app_db):
    from app.models import ColheitaRegistro

    with app_db.app_context():
        ids = _setup_usuario_com_associacao("a@connectagro.com")
    client = _login(app_db, "a@connectagro.com")
    client.post("/colheita/nova",
                data={"cultura_gleba_id": str(ids["cg_id"]),
                      "data_colheita": "2026-03-10", "quantidade": "35.5", "unidade": "sacas"})
    with app_db.app_context():
        assert ColheitaRegistro.query.first().quantidade == 35.5


def test_quantidade_invalida_400(app_db):
    with app_db.app_context():
        ids = _setup_usuario_com_associacao("a@connectagro.com")
    client = _login(app_db, "a@connectagro.com")
    resp = client.post("/colheita/nova",
                       data={"cultura_gleba_id": str(ids["cg_id"]),
                             "data_colheita": "2026-03-10", "quantidade": "abc"})
    assert resp.status_code == 400


def test_quantidade_nao_positiva_400(app_db):
    with app_db.app_context():
        ids = _setup_usuario_com_associacao("a@connectagro.com")
    client = _login(app_db, "a@connectagro.com")
    assert client.post("/colheita/nova",
                       data={"cultura_gleba_id": str(ids["cg_id"]),
                             "data_colheita": "2026-03-10", "quantidade": "0"}).status_code == 400
    assert client.post("/colheita/nova",
                       data={"cultura_gleba_id": str(ids["cg_id"]),
                             "data_colheita": "2026-03-10", "quantidade": "-3"}).status_code == 400


# --- Edição/remoção --------------------------------------------------------

def _criar_registro(client, cg_id):
    client.post("/colheita/nova",
                data={"cultura_gleba_id": str(cg_id), "data_colheita": "2026-03-10",
                      "quantidade": "10", "unidade": "kg"})


def test_editar_colheita(app_db):
    from app.models import ColheitaRegistro

    with app_db.app_context():
        ids = _setup_usuario_com_associacao("a@connectagro.com")
    client = _login(app_db, "a@connectagro.com")
    _criar_registro(client, ids["cg_id"])
    with app_db.app_context():
        rid = ColheitaRegistro.query.first().id
    resp = client.post(f"/colheita/{rid}/editar",
                       data={"cultura_gleba_id": str(ids["cg_id"]),
                             "data_colheita": "2026-04-01", "quantidade": "99", "unidade": "ton"})
    assert resp.status_code == 302
    with app_db.app_context():
        r = db.session.get(ColheitaRegistro, rid)
        assert r.data_colheita == "2026-04-01"
        assert r.quantidade == 99.0
        assert r.unidade == "ton"


def test_remover_colheita(app_db):
    from app.models import ColheitaRegistro

    with app_db.app_context():
        ids = _setup_usuario_com_associacao("a@connectagro.com")
    client = _login(app_db, "a@connectagro.com")
    _criar_registro(client, ids["cg_id"])
    with app_db.app_context():
        rid = ColheitaRegistro.query.first().id
    assert client.post(f"/colheita/{rid}/remover").status_code == 302
    with app_db.app_context():
        assert db.session.get(ColheitaRegistro, rid) is None


def test_escopo_colheita_por_propriedade(app_db):
    from app.models import ColheitaRegistro

    with app_db.app_context():
        ids_a = _setup_usuario_com_associacao("a@connectagro.com")
        _setup_usuario_com_associacao("b@connectagro.com")
    ca = _login(app_db, "a@connectagro.com")
    _criar_registro(ca, ids_a["cg_id"])
    with app_db.app_context():
        rid = ColheitaRegistro.query.first().id
    cb = _login(app_db, "b@connectagro.com")
    assert cb.get(f"/colheita/{rid}/editar").status_code == 404
    assert cb.post(f"/colheita/{rid}/remover").status_code == 404


# --- Listagem e orientação -------------------------------------------------

def test_listagem_exibe_dados(app_db):
    with app_db.app_context():
        ids = _setup_usuario_com_associacao("a@connectagro.com",
                                            cultura_nome="Milho", gleba_nome="Área Norte")
    client = _login(app_db, "a@connectagro.com")
    client.post("/colheita/nova",
                data={"cultura_gleba_id": str(ids["cg_id"]), "data_colheita": "2026-03-10",
                      "quantidade": "1200", "unidade": "kg", "qualidade": "ótima"})
    corpo = client.get("/colheita/").data.decode("utf-8")
    assert "Milho" in corpo
    assert "Área Norte" in corpo
    assert "kg" in corpo
    assert "ótima" in corpo


def test_nova_sem_associacao_orienta_usuario(app_db):
    """Sem cultura↔gleba, GET /colheita/nova responde 200 e orienta o usuário."""
    from app.models import Usuario, Propriedade

    with app_db.app_context():
        u = Usuario(nome="x", email="x@connectagro.com", perfil="tecnico", ativo=True,
                    senha_hash=gerar_hash_senha("senha123"))
        db.session.add(u)
        db.session.commit()
        db.session.add(Propriedade(usuario_id=u.id, nome="Fazenda X"))
        db.session.commit()
    client = _login(app_db, "x@connectagro.com")
    resp = client.get("/colheita/nova")
    assert resp.status_code == 200
    assert "cultura" in resp.data.decode("utf-8").lower()
