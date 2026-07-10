"""Testes de integridade na exclusão/desassociação de culturas e glebas.

Associações cultura↔gleba referenciadas por aplicações ou colheitas não
podem ser removidas: as rotas bloqueiam com mensagem amigável (sem 500 e
sem cascata), preservando aplicações, colheitas e os próprios registros.
"""
import pytest

from app.extensions import db
from app.utils.auth import gerar_hash_senha

SENHA = "senha123"
MSG_BLOQUEIO = "dados históricos vinculados"


def _criar_usuario(email):
    from app.models import Usuario

    usuario = Usuario(nome=email, email=email, perfil="admin", ativo=True,
                      senha_hash=gerar_hash_senha(SENHA))
    db.session.add(usuario)
    db.session.commit()
    return usuario.id


def _setup_com_associacao(email="a@integridade.com"):
    from app.models import Cultura, CulturaGleba, Gleba, Propriedade

    usuario_id = _criar_usuario(email)
    propriedade = Propriedade(usuario_id=usuario_id, nome="Fazenda " + email)
    db.session.add(propriedade)
    db.session.commit()
    gleba = Gleba(propriedade_id=propriedade.id, nome="Talhão 1")
    cultura = Cultura(propriedade_id=propriedade.id, nome="Soja",
                      status="em_andamento")
    db.session.add_all([gleba, cultura])
    db.session.commit()
    cultura_gleba = CulturaGleba(cultura_id=cultura.id, gleba_id=gleba.id)
    db.session.add(cultura_gleba)
    db.session.commit()
    return {"propriedade_id": propriedade.id, "gleba_id": gleba.id,
            "cultura_id": cultura.id, "cg_id": cultura_gleba.id}


def _criar_aplicacao(cg_id):
    from app.models import AplicacaoInsumo, ProdutoBase

    produto = ProdutoBase(nome="Glifosato", slug="glifosato",
                          classe="defensivo", categoria="herbicida",
                          status_sistema="pre_cadastrado",
                          status_regulatorio="nao_validado_agrofit")
    db.session.add(produto)
    db.session.commit()
    aplicacao = AplicacaoInsumo(cultura_gleba_id=cg_id,
                                produto_base_id=produto.id,
                                data_aplicacao="2026-02-10")
    db.session.add(aplicacao)
    db.session.commit()
    return aplicacao.id


def _criar_colheita(cg_id):
    from app.models import ColheitaRegistro

    colheita = ColheitaRegistro(cultura_gleba_id=cg_id,
                                data_colheita="2026-06-01")
    db.session.add(colheita)
    db.session.commit()
    return colheita.id


@pytest.fixture
def app_db(app):
    with app.app_context():
        db.create_all()
    return app


def _login(app_db, email="a@integridade.com"):
    client = app_db.test_client()
    client.post("/auth/login", data={"email": email, "senha": SENHA})
    return client


# --- Exclusão sem histórico continua funcionando ----------------------------

def test_cultura_sem_historico_pode_ser_excluida(app_db):
    from app.models import Cultura, CulturaGleba

    with app_db.app_context():
        ids = _setup_com_associacao()
    client = _login(app_db)
    resp = client.post(f"/culturas/{ids['cultura_id']}/remover")
    assert resp.status_code == 302
    with app_db.app_context():
        assert db.session.get(Cultura, ids["cultura_id"]) is None
        assert db.session.get(CulturaGleba, ids["cg_id"]) is None


def test_gleba_sem_historico_pode_ser_excluida(app_db):
    from app.models import CulturaGleba, Gleba

    with app_db.app_context():
        ids = _setup_com_associacao()
    client = _login(app_db)
    resp = client.post(f"/glebas/{ids['gleba_id']}/remover")
    assert resp.status_code == 302
    with app_db.app_context():
        assert db.session.get(Gleba, ids["gleba_id"]) is None
        assert db.session.get(CulturaGleba, ids["cg_id"]) is None


# --- Exclusão bloqueada quando há histórico ---------------------------------

def _assert_tudo_intacto(app_db, ids, aplicacao_id=None, colheita_id=None):
    from app.models import (AplicacaoInsumo, ColheitaRegistro, Cultura,
                            CulturaGleba, Gleba)

    with app_db.app_context():
        assert db.session.get(Cultura, ids["cultura_id"]) is not None
        assert db.session.get(Gleba, ids["gleba_id"]) is not None
        assert db.session.get(CulturaGleba, ids["cg_id"]) is not None
        if aplicacao_id is not None:
            aplicacao = db.session.get(AplicacaoInsumo, aplicacao_id)
            assert aplicacao is not None
            assert aplicacao.cultura_gleba_id == ids["cg_id"]
        if colheita_id is not None:
            colheita = db.session.get(ColheitaRegistro, colheita_id)
            assert colheita is not None
            assert colheita.cultura_gleba_id == ids["cg_id"]


def test_cultura_com_aplicacao_nao_e_excluida(app_db):
    with app_db.app_context():
        ids = _setup_com_associacao()
        aplicacao_id = _criar_aplicacao(ids["cg_id"])
    client = _login(app_db)
    resp = client.post(f"/culturas/{ids['cultura_id']}/remover",
                       follow_redirects=True)
    assert resp.status_code == 200
    assert MSG_BLOQUEIO in resp.data.decode("utf-8")
    _assert_tudo_intacto(app_db, ids, aplicacao_id=aplicacao_id)


def test_cultura_com_colheita_nao_e_excluida(app_db):
    with app_db.app_context():
        ids = _setup_com_associacao()
        colheita_id = _criar_colheita(ids["cg_id"])
    client = _login(app_db)
    resp = client.post(f"/culturas/{ids['cultura_id']}/remover",
                       follow_redirects=True)
    assert resp.status_code == 200
    assert MSG_BLOQUEIO in resp.data.decode("utf-8")
    _assert_tudo_intacto(app_db, ids, colheita_id=colheita_id)


def test_gleba_com_aplicacao_nao_e_excluida(app_db):
    with app_db.app_context():
        ids = _setup_com_associacao()
        aplicacao_id = _criar_aplicacao(ids["cg_id"])
    client = _login(app_db)
    resp = client.post(f"/glebas/{ids['gleba_id']}/remover",
                       follow_redirects=True)
    assert resp.status_code == 200
    assert MSG_BLOQUEIO in resp.data.decode("utf-8")
    _assert_tudo_intacto(app_db, ids, aplicacao_id=aplicacao_id)


def test_gleba_com_colheita_nao_e_excluida(app_db):
    with app_db.app_context():
        ids = _setup_com_associacao()
        colheita_id = _criar_colheita(ids["cg_id"])
    client = _login(app_db)
    resp = client.post(f"/glebas/{ids['gleba_id']}/remover",
                       follow_redirects=True)
    assert resp.status_code == 200
    assert MSG_BLOQUEIO in resp.data.decode("utf-8")
    _assert_tudo_intacto(app_db, ids, colheita_id=colheita_id)


# --- Edição de cultura que tenta desassociar gleba com histórico ------------

def test_editar_cultura_nao_remove_associacao_com_historico(app_db):
    from app.models import Cultura

    with app_db.app_context():
        ids = _setup_com_associacao()
        aplicacao_id = _criar_aplicacao(ids["cg_id"])
    client = _login(app_db)
    # tenta desmarcar todas as glebas (removeria a associação usada)
    resp = client.post(f"/culturas/{ids['cultura_id']}/editar",
                       data={"nome": "Soja renomeada", "status": "colhida"})
    assert resp.status_code == 400
    assert MSG_BLOQUEIO in resp.data.decode("utf-8")
    _assert_tudo_intacto(app_db, ids, aplicacao_id=aplicacao_id)
    with app_db.app_context():
        cultura = db.session.get(Cultura, ids["cultura_id"])
        assert cultura.nome == "Soja"  # nada foi alterado
        assert cultura.status == "em_andamento"


def test_editar_cultura_mantendo_associacao_com_historico_funciona(app_db):
    from app.models import Cultura, Gleba

    with app_db.app_context():
        ids = _setup_com_associacao()
        _criar_aplicacao(ids["cg_id"])
        nova_gleba = Gleba(propriedade_id=ids["propriedade_id"], nome="Talhão 2")
        db.session.add(nova_gleba)
        db.session.commit()
        nova_gleba_id = nova_gleba.id
    client = _login(app_db)
    # mantém a gleba com histórico e adiciona outra: permitido
    resp = client.post(f"/culturas/{ids['cultura_id']}/editar",
                       data={"nome": "Soja", "status": "em_andamento",
                             "glebas": [str(ids["gleba_id"]),
                                        str(nova_gleba_id)]})
    assert resp.status_code == 302
    with app_db.app_context():
        cultura = db.session.get(Cultura, ids["cultura_id"])
        assert {cg.gleba_id for cg in cultura.cultura_glebas} == {
            ids["gleba_id"], nova_gleba_id}


# --- Sessão continua utilizável após o bloqueio -----------------------------

def test_sessao_continua_utilizavel_apos_bloqueio(app_db):
    from app.models import Gleba

    with app_db.app_context():
        ids = _setup_com_associacao()
        _criar_aplicacao(ids["cg_id"])
    client = _login(app_db)
    assert client.post(f"/culturas/{ids['cultura_id']}/remover").status_code == 302
    assert client.post(f"/glebas/{ids['gleba_id']}/remover").status_code == 302
    # a sessão do banco segue funcional: novo CRUD completo funciona
    resp = client.post("/glebas/nova", data={"nome": "Pós-bloqueio",
                                             "area_ha": "1"})
    assert resp.status_code == 302
    with app_db.app_context():
        assert Gleba.query.filter_by(nome="Pós-bloqueio").first() is not None
    assert client.get("/culturas/").status_code == 200
