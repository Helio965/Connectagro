"""Testes do CRUD de Aplicações de Insumo (Etapa 5.6).

O módulo registra histórico operacional vinculado a Cultura↔Gleba e ProdutoBase,
sem recomendação agronômica, sem validação técnica de dose e sem preço/imagem.
"""
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


def _setup_usuario_com_associacao(email, cultura_nome="Soja", gleba_nome="Talhão 1"):
    """Cria usuário + propriedade + gleba + cultura + associação. Retorna ids."""
    from app.models import Cultura, CulturaGleba, Gleba, Propriedade

    u = _criar_usuario(email)
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
    return {"usuario_id": u.id, "propriedade_id": p.id, "cg_id": cg.id}


def _criar_produto(nome="Glifosato", slug="glifosato", classe="defensivo",
                   categoria="herbicida", status_sistema="pre_cadastrado",
                   status_regulatorio="nao_validado_agrofit"):
    from app.models import ProdutoBase

    p = ProdutoBase(nome=nome, slug=slug, classe=classe, categoria=categoria,
                    status_sistema=status_sistema,
                    status_regulatorio=status_regulatorio)
    db.session.add(p)
    db.session.commit()
    return p


@pytest.fixture
def app_db(app):
    with app.app_context():
        db.create_all()
    return app


def _login(app_db, email):
    client = app_db.test_client()
    client.post("/auth/login", data={"email": email, "senha": "senha123"})
    return client


def _setup_basico(email="a@connectagro.com"):
    ids = _setup_usuario_com_associacao(email)
    produto = _criar_produto()
    ids["produto_id"] = produto.id
    return ids


def _criar_registro(client, cg_id, produto_id):
    return client.post("/aplicacoes/nova",
                       data={"cultura_gleba_id": str(cg_id),
                             "produto_base_id": str(produto_id),
                             "data_aplicacao": "2026-02-10",
                             "dose": "2,5", "unidade": "L/ha",
                             "responsavel": "Ana"})


# --- Login obrigatório -----------------------------------------------------

def test_index_exige_login(app_db):
    resp = app_db.test_client().get("/aplicacoes/")
    assert resp.status_code == 302
    assert "/auth/login" in resp.headers["Location"]


def test_nova_exige_login(app_db):
    resp = app_db.test_client().get("/aplicacoes/nova")
    assert resp.status_code == 302
    assert "/auth/login" in resp.headers["Location"]


# --- Criação e validações --------------------------------------------------

def test_criar_aplicacao_valida(app_db):
    from app.models import AplicacaoInsumo

    with app_db.app_context():
        ids = _setup_basico()
    client = _login(app_db, "a@connectagro.com")
    resp = _criar_registro(client, ids["cg_id"], ids["produto_id"])
    assert resp.status_code == 302
    with app_db.app_context():
        aplicacao = AplicacaoInsumo.query.first()
        assert aplicacao is not None
        assert aplicacao.cultura_gleba_id == ids["cg_id"]
        assert aplicacao.produto_base_id == ids["produto_id"]
        assert aplicacao.dose == 2.5
        assert aplicacao.unidade == "L/ha"
        assert aplicacao.responsavel == "Ana"


def test_data_aplicacao_obrigatoria_400(app_db):
    with app_db.app_context():
        ids = _setup_basico()
    client = _login(app_db, "a@connectagro.com")
    resp = client.post("/aplicacoes/nova",
                       data={"cultura_gleba_id": str(ids["cg_id"]),
                             "produto_base_id": str(ids["produto_id"]),
                             "data_aplicacao": ""})
    assert resp.status_code == 400


def test_cultura_gleba_obrigatoria_400(app_db):
    with app_db.app_context():
        ids = _setup_basico()
    client = _login(app_db, "a@connectagro.com")
    resp = client.post("/aplicacoes/nova",
                       data={"cultura_gleba_id": "",
                             "produto_base_id": str(ids["produto_id"]),
                             "data_aplicacao": "2026-02-10"})
    assert resp.status_code == 400


def test_cultura_gleba_inexistente_400(app_db):
    with app_db.app_context():
        ids = _setup_basico()
    client = _login(app_db, "a@connectagro.com")
    resp = client.post("/aplicacoes/nova",
                       data={"cultura_gleba_id": "999999",
                             "produto_base_id": str(ids["produto_id"]),
                             "data_aplicacao": "2026-02-10"})
    assert resp.status_code == 400


def test_nao_usa_cultura_gleba_de_outra_propriedade(app_db):
    with app_db.app_context():
        ids_a = _setup_basico("a@connectagro.com")
        ids_b = _setup_usuario_com_associacao("b@connectagro.com")
    client_a = _login(app_db, "a@connectagro.com")
    resp = client_a.post("/aplicacoes/nova",
                         data={"cultura_gleba_id": str(ids_b["cg_id"]),
                               "produto_base_id": str(ids_a["produto_id"]),
                               "data_aplicacao": "2026-02-10"})
    assert resp.status_code == 400


def test_produto_obrigatorio_400(app_db):
    with app_db.app_context():
        ids = _setup_basico()
    client = _login(app_db, "a@connectagro.com")
    resp = client.post("/aplicacoes/nova",
                       data={"cultura_gleba_id": str(ids["cg_id"]),
                             "produto_base_id": "",
                             "data_aplicacao": "2026-02-10"})
    assert resp.status_code == 400


def test_produto_inexistente_400(app_db):
    with app_db.app_context():
        ids = _setup_basico()
    client = _login(app_db, "a@connectagro.com")
    resp = client.post("/aplicacoes/nova",
                       data={"cultura_gleba_id": str(ids["cg_id"]),
                             "produto_base_id": "999999",
                             "data_aplicacao": "2026-02-10"})
    assert resp.status_code == 400


def test_produto_bloqueado_por_status_sistema_400(app_db):
    with app_db.app_context():
        ids = _setup_usuario_com_associacao("a@connectagro.com")
        bloqueado = _criar_produto(nome="Paraquate", slug="paraquate",
                                   status_sistema="bloqueado_historico")
    client = _login(app_db, "a@connectagro.com")
    resp = client.post("/aplicacoes/nova",
                       data={"cultura_gleba_id": str(ids["cg_id"]),
                             "produto_base_id": str(bloqueado.id),
                             "data_aplicacao": "2026-02-10"})
    assert resp.status_code == 400


def test_produto_bloqueado_por_status_regulatorio_400(app_db):
    with app_db.app_context():
        ids = _setup_usuario_com_associacao("a@connectagro.com")
        bloqueado = _criar_produto(nome="Produto histórico", slug="produto-historico",
                                   status_regulatorio="bloqueado_historico")
    client = _login(app_db, "a@connectagro.com")
    resp = client.post("/aplicacoes/nova",
                       data={"cultura_gleba_id": str(ids["cg_id"]),
                             "produto_base_id": str(bloqueado.id),
                             "data_aplicacao": "2026-02-10"})
    assert resp.status_code == 400


def test_produto_bloqueado_nao_aparece_no_select(app_db):
    with app_db.app_context():
        _setup_usuario_com_associacao("a@connectagro.com")
        _criar_produto(nome="Ureia", slug="ureia", classe="fertilizante",
                       categoria="fertilizante nitrogenado",
                       status_regulatorio="tipo_tecnico_generico")
        _criar_produto(nome="Paraquate", slug="paraquate",
                       status_sistema="bloqueado_historico")
    corpo = _login(app_db, "a@connectagro.com").get("/aplicacoes/nova").data.decode("utf-8")
    assert "Ureia" in corpo
    assert "Paraquate" not in corpo


def test_dose_aceita_virgula_e_ponto(app_db):
    from app.models import AplicacaoInsumo

    with app_db.app_context():
        ids = _setup_basico()
    client = _login(app_db, "a@connectagro.com")
    client.post("/aplicacoes/nova",
                data={"cultura_gleba_id": str(ids["cg_id"]),
                      "produto_base_id": str(ids["produto_id"]),
                      "data_aplicacao": "2026-02-10", "dose": "1,25"})
    client.post("/aplicacoes/nova",
                data={"cultura_gleba_id": str(ids["cg_id"]),
                      "produto_base_id": str(ids["produto_id"]),
                      "data_aplicacao": "2026-02-11", "dose": "2.5"})
    with app_db.app_context():
        doses = sorted(a.dose for a in AplicacaoInsumo.query.all())
        assert doses == [1.25, 2.5]


def test_dose_invalida_400(app_db):
    with app_db.app_context():
        ids = _setup_basico()
    client = _login(app_db, "a@connectagro.com")
    resp = client.post("/aplicacoes/nova",
                       data={"cultura_gleba_id": str(ids["cg_id"]),
                             "produto_base_id": str(ids["produto_id"]),
                             "data_aplicacao": "2026-02-10", "dose": "abc"})
    assert resp.status_code == 400


def test_dose_nao_positiva_400(app_db):
    with app_db.app_context():
        ids = _setup_basico()
    client = _login(app_db, "a@connectagro.com")
    assert client.post("/aplicacoes/nova",
                       data={"cultura_gleba_id": str(ids["cg_id"]),
                             "produto_base_id": str(ids["produto_id"]),
                             "data_aplicacao": "2026-02-10", "dose": "0"}).status_code == 400
    assert client.post("/aplicacoes/nova",
                       data={"cultura_gleba_id": str(ids["cg_id"]),
                             "produto_base_id": str(ids["produto_id"]),
                             "data_aplicacao": "2026-02-10", "dose": "-1"}).status_code == 400


# --- Edição/remoção/escopo -------------------------------------------------

def test_editar_aplicacao(app_db):
    from app.models import AplicacaoInsumo

    with app_db.app_context():
        ids = _setup_basico()
    client = _login(app_db, "a@connectagro.com")
    _criar_registro(client, ids["cg_id"], ids["produto_id"])
    with app_db.app_context():
        aplicacao_id = AplicacaoInsumo.query.first().id
    resp = client.post(f"/aplicacoes/{aplicacao_id}/editar",
                       data={"cultura_gleba_id": str(ids["cg_id"]),
                             "produto_base_id": str(ids["produto_id"]),
                             "data_aplicacao": "2026-03-01",
                             "dose": "3", "unidade": "kg/ha",
                             "responsavel": "Bruno"})
    assert resp.status_code == 302
    with app_db.app_context():
        aplicacao = db.session.get(AplicacaoInsumo, aplicacao_id)
        assert aplicacao.data_aplicacao == "2026-03-01"
        assert aplicacao.dose == 3.0
        assert aplicacao.unidade == "kg/ha"
        assert aplicacao.responsavel == "Bruno"


def test_remover_aplicacao(app_db):
    from app.models import AplicacaoInsumo

    with app_db.app_context():
        ids = _setup_basico()
    client = _login(app_db, "a@connectagro.com")
    _criar_registro(client, ids["cg_id"], ids["produto_id"])
    with app_db.app_context():
        aplicacao_id = AplicacaoInsumo.query.first().id
    assert client.post(f"/aplicacoes/{aplicacao_id}/remover").status_code == 302
    with app_db.app_context():
        assert db.session.get(AplicacaoInsumo, aplicacao_id) is None


def test_usuario_nao_acessa_aplicacao_de_outra_propriedade_404(app_db):
    from app.models import AplicacaoInsumo

    with app_db.app_context():
        ids_a = _setup_basico("a@connectagro.com")
        _setup_usuario_com_associacao("b@connectagro.com")
    client_a = _login(app_db, "a@connectagro.com")
    _criar_registro(client_a, ids_a["cg_id"], ids_a["produto_id"])
    with app_db.app_context():
        aplicacao_id = AplicacaoInsumo.query.first().id
    client_b = _login(app_db, "b@connectagro.com")
    assert client_b.get(f"/aplicacoes/{aplicacao_id}/editar").status_code == 404
    assert client_b.post(f"/aplicacoes/{aplicacao_id}/remover").status_code == 404


# --- Listagem, orientações e limites de escopo ----------------------------

def test_listagem_exibe_dados(app_db):
    with app_db.app_context():
        ids = _setup_usuario_com_associacao("a@connectagro.com",
                                            cultura_nome="Milho", gleba_nome="Área Norte")
        produto = _criar_produto(nome="Ureia", slug="ureia", classe="fertilizante",
                                 categoria="fertilizante nitrogenado",
                                 status_regulatorio="tipo_tecnico_generico")
        ids["produto_id"] = produto.id
    client = _login(app_db, "a@connectagro.com")
    _criar_registro(client, ids["cg_id"], ids["produto_id"])
    corpo = client.get("/aplicacoes/").data.decode("utf-8")
    assert "Milho" in corpo
    assert "Área Norte" in corpo
    assert "Ureia" in corpo
    assert "2.50" in corpo
    assert "L/ha" in corpo
    assert "Ana" in corpo


def test_nova_sem_cultura_gleba_orienta_usuario(app_db):
    from app.models import Propriedade

    with app_db.app_context():
        usuario = _criar_usuario("x@connectagro.com")
        db.session.add(Propriedade(usuario_id=usuario.id, nome="Fazenda X"))
        db.session.commit()
        _criar_produto()
    resp = _login(app_db, "x@connectagro.com").get("/aplicacoes/nova")
    corpo = resp.data.decode("utf-8").lower()
    assert resp.status_code == 200
    assert "gleba" in corpo
    assert "cultura" in corpo


def test_nova_sem_produto_disponivel_orienta_importar_seed(app_db):
    with app_db.app_context():
        _setup_usuario_com_associacao("a@connectagro.com")
    resp = _login(app_db, "a@connectagro.com").get("/aplicacoes/nova")
    corpo = resp.data.decode("utf-8")
    assert resp.status_code == 200
    assert "import-catalog-seed" in corpo


def test_paginas_nao_tem_acoes_de_venda(app_db):
    with app_db.app_context():
        ids = _setup_basico()
    client = _login(app_db, "a@connectagro.com")
    for url in ("/aplicacoes/", "/aplicacoes/nova"):
        corpo = client.get(url).data.decode("utf-8").lower()
        for proibido in ("comprar", "checkout", "finalizar compra", "adicionar ao carrinho"):
            assert proibido not in corpo, f"'{proibido}' não deveria aparecer em {url}"


def test_crud_aplicacao_nao_cria_preco_nem_imagem(app_db):
    from app.models import AplicacaoInsumo, ProdutoImagem, ProdutoPreco

    with app_db.app_context():
        ids = _setup_basico()
    client = _login(app_db, "a@connectagro.com")
    _criar_registro(client, ids["cg_id"], ids["produto_id"])
    with app_db.app_context():
        aplicacao_id = AplicacaoInsumo.query.first().id
    client.post(f"/aplicacoes/{aplicacao_id}/editar",
                data={"cultura_gleba_id": str(ids["cg_id"]),
                      "produto_base_id": str(ids["produto_id"]),
                      "data_aplicacao": "2026-03-01", "dose": "1"})
    client.post(f"/aplicacoes/{aplicacao_id}/remover")
    with app_db.app_context():
        assert ProdutoPreco.query.count() == 0
        assert ProdutoImagem.query.count() == 0
