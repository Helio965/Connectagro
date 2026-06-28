"""Testes da consulta (somente leitura) do catálogo — Etapa 5.5."""
import pytest

from app.extensions import db
from app.utils.auth import gerar_hash_senha


@pytest.fixture
def app_cat(app):
    """App com schema + catálogo importado + usuário de teste."""
    from app.models import Usuario
    from app.services.catalogo_seed import carregar_seed, importar_seed_catalogo

    with app.app_context():
        db.create_all()
        importar_seed_catalogo(db.session, carregar_seed())
        db.session.add(Usuario(nome="T", email="t@connectagro.com", perfil="tecnico",
                               ativo=True, senha_hash=gerar_hash_senha("senha123")))
        db.session.commit()
    return app


def _login(app_cat):
    client = app_cat.test_client()
    client.post("/auth/login", data={"email": "t@connectagro.com", "senha": "senha123"})
    return client


def test_defensivos_exige_login(app_cat):
    resp = app_cat.test_client().get("/defensivos/")
    assert resp.status_code == 302
    assert "/auth/login" in resp.headers["Location"]


def test_fertilizantes_exige_login(app_cat):
    resp = app_cat.test_client().get("/fertilizantes/")
    assert resp.status_code == 302
    assert "/auth/login" in resp.headers["Location"]


def test_lista_defensivos_so_classe_defensivo(app_cat):
    corpo = _login(app_cat).get("/defensivos/").data.decode("utf-8")
    # defensivo conhecido aparece; fertilizante conhecido não
    assert "Glifosato" in corpo
    assert "Ureia" not in corpo


def test_lista_fertilizantes_so_classe_fertilizante(app_cat):
    corpo = _login(app_cat).get("/fertilizantes/").data.decode("utf-8")
    assert "Ureia" in corpo
    assert "Glifosato" not in corpo


def test_busca_textual(app_cat):
    corpo = _login(app_cat).get("/defensivos/?q=glifosato").data.decode("utf-8")
    assert "Glifosato" in corpo
    assert "Imidacloprido" not in corpo


def test_filtro_categoria(app_cat):
    client = _login(app_cat)
    corpo = client.get("/defensivos/?categoria=herbicida").data.decode("utf-8")
    assert "Glifosato" in corpo  # herbicida
    assert "Imidacloprido" not in corpo  # inseticida


def test_filtro_status_regulatorio(app_cat):
    client = _login(app_cat)
    # defensivo com atencao_regulatoria: Clorpirifós
    corpo = client.get("/defensivos/?status_regulatorio=atencao_regulatoria").data.decode("utf-8")
    assert "Clorpirifós" in corpo
    assert "Glifosato" not in corpo  # nao_validado_agrofit


def test_detalhe_defensivo(app_cat):
    corpo = _login(app_cat).get("/defensivos/glifosato").data.decode("utf-8")
    assert "Glifosato" in corpo
    assert "Dados técnicos" in corpo


def test_detalhe_fertilizante(app_cat):
    corpo = _login(app_cat).get("/fertilizantes/ureia").data.decode("utf-8")
    assert "Ureia" in corpo
    assert "Dados técnicos" in corpo


def test_detalhe_slug_inexistente_404(app_cat):
    client = _login(app_cat)
    assert client.get("/defensivos/nao-existe").status_code == 404
    assert client.get("/fertilizantes/nao-existe").status_code == 404


def test_classe_errada_no_slug_404(app_cat):
    """Fertilizante acessado pela rota de defensivos não é encontrado."""
    assert _login(app_cat).get("/defensivos/ureia").status_code == 404


def test_sem_termos_de_venda(app_cat):
    """Não deve haver ação de compra (os termos 'carrinho/cotação' aparecem
    apenas no aviso de que o sistema NÃO os possui — por isso checamos termos de
    ação de compra, que não constam dos avisos)."""
    client = _login(app_cat)
    for url in ("/defensivos/", "/defensivos/glifosato", "/fertilizantes/ureia"):
        corpo = client.get(url).data.decode("utf-8").lower()
        for proibido in ("comprar", "checkout", "finalizar compra",
                         "adicionar ao carrinho", "fazer pedido", "preço:"):
            assert proibido not in corpo, f"'{proibido}' não deveria aparecer em {url}"


def test_aviso_preco_imagem_pendente(app_cat):
    corpo = _login(app_cat).get("/defensivos/glifosato").data.decode("utf-8").lower()
    assert "preço e imagem" in corpo
    assert "pendente" in corpo


def test_campos_json_renderizados_como_lista(app_cat):
    """culturas_comuns (JSON) aparece como lista legível separada por vírgula."""
    corpo = _login(app_cat).get("/defensivos/glifosato").data.decode("utf-8")
    assert "Culturas comuns" in corpo
    # valores do seed renderizados (não o JSON cru com colchetes)
    assert "soja" in corpo
    assert '["soja"' not in corpo


def test_json_invalido_nao_quebra_pagina(app_cat):
    """Um campo técnico com JSON inválido não derruba o detalhe (fallback)."""
    from app.models import ProdutoBase, ProdutoTecnico

    with app_cat.app_context():
        prod = ProdutoBase.query.filter_by(slug="glifosato").first()
        tec = ProdutoTecnico.query.filter_by(produto_id=prod.id).first()
        tec.alvos_controle = "{json invalido"  # texto não-JSON
        db.session.commit()
    resp = _login(app_cat).get("/defensivos/glifosato")
    assert resp.status_code == 200
    assert "{json invalido" in resp.data.decode("utf-8")


def test_preco_e_imagem_seguem_vazios(app_cat):
    from app.models import ProdutoPreco, ProdutoImagem

    client = _login(app_cat)
    client.get("/defensivos/")
    client.get("/defensivos/glifosato")
    client.get("/fertilizantes/ureia")
    with app_cat.app_context():
        assert ProdutoPreco.query.count() == 0
        assert ProdutoImagem.query.count() == 0
