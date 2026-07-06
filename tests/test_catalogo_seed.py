"""Testes da Etapa 4.2 — Flask-Migrate + validação/importação do seed técnico.

Usam SQLite em memória (via fixture ``app``) e não dependem de banco .db real.
"""
import copy
import json

import pytest

from app.extensions import db, migrate
from app.services.catalogo_seed import (
    SeedInvalidoError,
    carregar_seed,
    validar_seed,
    importar_seed_catalogo,
)


def test_migrate_configurado_sem_quebrar_app(app):
    """Flask-Migrate está inicializado e create_app continua funcionando."""
    assert app is not None
    assert migrate is not None
    # extensão 'migrate' registrada na app
    assert "migrate" in app.extensions


def test_seed_real_e_valido():
    dados = carregar_seed()
    assert validar_seed(dados) is True


# --- Validador: casos negativos -------------------------------------------

@pytest.fixture
def seed():
    return carregar_seed()


def test_validador_detecta_ids_duplicados(seed):
    seed["produto_base"][1]["id"] = seed["produto_base"][0]["id"]
    with pytest.raises(SeedInvalidoError, match="ids duplicados"):
        validar_seed(seed)


def test_validador_detecta_slugs_duplicados(seed):
    seed["produto_base"][1]["slug"] = seed["produto_base"][0]["slug"]
    with pytest.raises(SeedInvalidoError, match="slugs duplicados"):
        validar_seed(seed)


def test_validador_detecta_fk_invalida(seed):
    seed["produto_tecnico"][0]["produto_id"] = 999999
    with pytest.raises(SeedInvalidoError, match="produto_base correspondente"):
        validar_seed(seed)


def test_validador_detecta_preco_nao_vazio(seed):
    seed["produto_preco"] = [{"id": 1, "produto_id": 1, "valor": 10.0}]
    with pytest.raises(SeedInvalidoError, match="produto_preco deve estar vazio"):
        validar_seed(seed)


def test_validador_detecta_imagem_fk_invalida(seed):
    seed["produto_imagem"].append(
        {"id": 99999, "produto_id": 999999, "url": "img/x.jpg"})
    with pytest.raises(SeedInvalidoError, match="produto_base correspondente"):
        validar_seed(seed)


def test_validador_detecta_imagem_sem_url(seed):
    pid = seed["produto_base"][0]["id"]
    seed["produto_imagem"].append({"id": 99998, "produto_id": pid, "url": ""})
    with pytest.raises(SeedInvalidoError, match="produto_imagem sem url"):
        validar_seed(seed)


# --- Importação ------------------------------------------------------------

def test_importacao_popula_base_e_tecnico(app, seed):
    from app.models import ProdutoBase, ProdutoTecnico

    with app.app_context():
        db.create_all()
        resumo = importar_seed_catalogo(db.session, seed)
        assert resumo["base_inseridos"] == len(seed["produto_base"])
        assert resumo["tecnico_inseridos"] == len(seed["produto_tecnico"])
        assert ProdutoBase.query.count() == len(seed["produto_base"])
        assert ProdutoTecnico.query.count() == len(seed["produto_tecnico"])


def test_importacao_nao_popula_preco(app, seed):
    """Preço continua vazio no MVP (fica para o sistema final)."""
    from app.models import ProdutoPreco

    with app.app_context():
        db.create_all()
        importar_seed_catalogo(db.session, seed)
        assert ProdutoPreco.query.count() == 0


def test_importacao_popula_imagem_para_todos(app, seed):
    """Toda a base recebe uma imagem de referência ao importar o seed."""
    from app.models import ProdutoBase, ProdutoImagem

    with app.app_context():
        db.create_all()
        resumo = importar_seed_catalogo(db.session, seed)
        total = len(seed["produto_base"])
        assert resumo["imagem_inseridos"] == total
        assert ProdutoImagem.query.count() == total
        # nenhum produto fica sem imagem_url
        sem_imagem = [p.slug for p in ProdutoBase.query.all() if not p.imagem_url]
        assert sem_imagem == []


def test_seed_tem_imagem_para_todos_os_produtos(seed):
    """O seed cobre 100% dos produtos e cada imagem aponta para um produto."""
    ids_base = {p["id"] for p in seed["produto_base"]}
    ids_imagem = {i["produto_id"] for i in seed["produto_imagem"]}
    assert ids_imagem == ids_base
    assert len(seed["produto_imagem"]) == len(seed["produto_base"])


def test_arquivos_locais_das_imagens_existem(app, seed):
    """Todo caminho local declarado no seed existe em src/app/static/."""
    import os

    faltando = []
    for img in seed["produto_imagem"]:
        url = img["url"]
        # só validamos caminhos locais (relativos ao static)
        if url.startswith(("http://", "https://", "data:", "/")):
            continue
        caminho = os.path.join(app.static_folder, url.replace("/", os.sep))
        if not os.path.isfile(caminho):
            faltando.append(url)
    assert faltando == []


def test_itens_bloqueados_nao_importados(app, seed):
    from app.models import ProdutoBase

    with app.app_context():
        db.create_all()
        importar_seed_catalogo(db.session, seed)
        bloqueados = [b["slug"] for b in seed["itens_bloqueados_ou_excluidos"]]
        assert bloqueados  # garante que há itens bloqueados no seed
        encontrados = ProdutoBase.query.filter(
            ProdutoBase.slug.in_(bloqueados)).count()
        assert encontrados == 0


def test_importacao_idempotente(app, seed):
    from app.models import ProdutoBase, ProdutoTecnico

    with app.app_context():
        db.create_all()
        importar_seed_catalogo(db.session, seed)
        base1 = ProdutoBase.query.count()
        tec1 = ProdutoTecnico.query.count()
        # segunda importação não deve duplicar
        resumo2 = importar_seed_catalogo(db.session, copy.deepcopy(seed))
        assert resumo2["base_inseridos"] == 0
        assert resumo2["tecnico_inseridos"] == 0
        assert ProdutoBase.query.count() == base1
        assert ProdutoTecnico.query.count() == tec1


def test_listas_salvas_como_json_texto(app, seed):
    from app.models import ProdutoTecnico

    with app.app_context():
        db.create_all()
        importar_seed_catalogo(db.session, seed)
        # um técnico de defensivo tem alvos_controle/culturas_comuns como JSON
        tec = ProdutoTecnico.query.filter(
            ProdutoTecnico.alvos_controle.isnot(None)).first()
        assert tec is not None
        valor = json.loads(tec.alvos_controle)
        assert isinstance(valor, list)
        culturas = json.loads(tec.culturas_comuns)
        assert isinstance(culturas, list)


def test_novos_campos_uso_principal_e_tipo_liberacao(app, seed):
    from app.models import ProdutoBase, ProdutoTecnico

    with app.app_context():
        db.create_all()
        importar_seed_catalogo(db.session, seed)
        # fertilizante (ex.: ureia) tem uso_principal e tipo_liberacao no seed
        base = ProdutoBase.query.filter_by(slug="ureia").first()
        assert base is not None
        tec = ProdutoTecnico.query.filter_by(produto_id=base.id).first()
        assert tec.uso_principal is not None
        assert tec.tipo_liberacao is not None
        # forma_aplicacao do seed foi mapeada para modo_aplicacao
        assert tec.modo_aplicacao is not None
