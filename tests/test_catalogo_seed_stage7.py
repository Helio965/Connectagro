"""Seed global sem corrupção de identidade ou perda de imagens administradas."""
import copy
from decimal import Decimal

import pytest
from sqlalchemy import event, update
from sqlalchemy.orm import Session

from app.extensions import db
from app.models import ProdutoBase, ProdutoImagem, ProdutoPreco, ProdutoTecnico
from app.services.catalogo_seed import (
    SeedInvalidoError, carregar_seed, importar_seed_catalogo,
    sincronizar_seq_produto_base, validar_seed,
)


@pytest.fixture
def seed7():
    return {
        "produto_base": [{"id": 1, "slug": "produto-global", "nome": "Produto global",
                          "classe": "fertilizante", "categoria": "mineral",
                          "descricao_curta": "Referência inicial",
                          "status_sistema": "pre_cadastrado",
                          "status_regulatorio": "tipo_tecnico_generico"}],
        "produto_tecnico": [{"produto_id": 1, "fonte_tecnica": "Fonte inicial",
                             "nutrientes_principais": ["N"]}],
        "produto_imagem": [{"produto_id": 1, "url": "img/referencia.jpg",
                            "fonte": "Fonte pública", "status_validacao": "nao_consolidado",
                            "observacoes": "Licença de referência"}],
        "produto_preco": [],
    }


@pytest.fixture
def seed_db(app):
    with app.app_context():
        assert db.engine.dialect.name == "sqlite"
        assert db.engine.url.database in (None, "", ":memory:")
        db.create_all()
        yield app
        db.session.remove()


@pytest.mark.parametrize("valor", [None, [], "texto", True, 42])
def test_validador_raiz_malformada_controlada(valor):
    with pytest.raises(SeedInvalidoError):
        validar_seed(valor)


@pytest.mark.parametrize("campo", ["produto_base", "produto_tecnico", "produto_imagem", "produto_preco"])
@pytest.mark.parametrize("valor", [None, {}, "texto", True])
def test_validador_componentes_precisam_ser_listas(seed7, campo, valor):
    seed7[campo] = valor
    with pytest.raises(SeedInvalidoError):
        validar_seed(seed7)


@pytest.mark.parametrize("campo", ["produto_base", "produto_tecnico", "produto_imagem", "produto_preco"])
@pytest.mark.parametrize("valor", [None, [], "texto"])
def test_validador_itens_precisam_ser_objetos(seed7, campo, valor):
    seed7[campo] = [valor]
    with pytest.raises(SeedInvalidoError):
        validar_seed(seed7)


@pytest.mark.parametrize("campo,valor", [
    ("id", True), ("id", 0), ("id", -1), ("id", 2**31), ("id", "1"),
    ("slug", []), ("slug", ""), ("slug", "Sem-slug"), ("slug", "slug/com/caminho"),
    ("nome", {}), ("nome", ""), ("nome", "n"*151),
    ("classe", []), ("classe", "outra"), ("categoria", []),
    ("status_sistema", []), ("status_sistema", "oficial"),
    ("status_regulatorio", {}), ("status_regulatorio", "validado_oficialmente"),
])
def test_validador_campos_base_invalidos_controlados(seed7, campo, valor):
    seed7["produto_base"][0][campo] = valor
    with pytest.raises(SeedInvalidoError):
        validar_seed(seed7)


@pytest.mark.parametrize("campo", ["status_sistema", "status_regulatorio"])
def test_validador_bloqueado_independe_da_lista_de_exclusoes(seed7, campo):
    seed7["produto_base"][0][campo] = "bloqueado_historico"
    seed7["itens_bloqueados_ou_excluidos"] = []
    with pytest.raises(SeedInvalidoError, match="bloqueado"):
        validar_seed(seed7)


@pytest.mark.parametrize("campo", ["produto_tecnico", "produto_imagem"])
@pytest.mark.parametrize("valor", [True, "1", [], 999])
def test_validador_fk_malformada_ou_inexistente(seed7, campo, valor):
    seed7[campo][0]["produto_id"] = valor
    with pytest.raises(SeedInvalidoError):
        validar_seed(seed7)


@pytest.mark.parametrize("campo", ["produto_tecnico", "produto_imagem"])
def test_validador_referencia_seed_duplicada_e_recusada(seed7, campo):
    seed7[campo].append(copy.deepcopy(seed7[campo][0]))
    with pytest.raises(SeedInvalidoError, match="duplicad"):
        validar_seed(seed7)


@pytest.mark.parametrize("campo,valor", [("url", []), ("fonte", {}), ("status_validacao", []),
                                         ("status_validacao", "oficial"), ("observacoes", 2)])
def test_validador_campos_imagem_malformados(seed7, campo, valor):
    seed7["produto_imagem"][0][campo] = valor
    with pytest.raises(SeedInvalidoError):
        validar_seed(seed7)


def test_validador_json_tecnico_nao_finito_ou_circular(seed7):
    seed7["produto_tecnico"][0]["nutrientes_principais"] = [float("nan")]
    with pytest.raises(SeedInvalidoError):
        validar_seed(seed7)
    circular = []
    circular.append(circular)
    seed7["produto_tecnico"][0]["nutrientes_principais"] = circular
    with pytest.raises(SeedInvalidoError):
        validar_seed(seed7)


@pytest.mark.parametrize("valor", [None, {}, [None], [{"slug": []}]])
def test_validador_lista_de_bloqueios_malformada(seed7, valor):
    seed7["itens_bloqueados_ou_excluidos"] = valor
    with pytest.raises(SeedInvalidoError):
        validar_seed(seed7)


@pytest.mark.parametrize("ocupacao", ["id", "slug", "ambos"])
def test_preflight_identidade_abortado_antes_de_inserts_de_dominio(seed_db, seed7, ocupacao):
    if ocupacao in {"id", "ambos"}:
        db.session.add(ProdutoBase(id=1, slug="outro-global", nome="Outro global", classe="fertilizante"))
    if ocupacao in {"slug", "ambos"}:
        db.session.add(ProdutoBase(id=10, slug="produto-global", nome="Produto legado", classe="fertilizante"))
    db.session.commit()
    antes = [(p.id, p.slug, p.nome) for p in ProdutoBase.query.order_by(ProdutoBase.id)]
    sql = []

    def capturar(conn, cursor, statement, parameters, context, executemany):
        sql.append(statement.lower().strip())

    event.listen(db.engine, "before_cursor_execute", capturar)
    try:
        with pytest.raises(SeedInvalidoError, match="identidade"):
            importar_seed_catalogo(db.session, seed7)
    finally:
        event.remove(db.engine, "before_cursor_execute", capturar)
    assert [(p.id, p.slug, p.nome) for p in ProdutoBase.query.order_by(ProdutoBase.id)] == antes
    assert ProdutoTecnico.query.count() == ProdutoImagem.query.count() == 0
    assert not any(statement.startswith("insert into produto_base") for statement in sql)


def test_preflight_conflito_no_ultimo_produto_nao_importa_os_anteriores(seed_db, seed7):
    segundo = dict(seed7["produto_base"][0], id=2, slug="outro-seed")
    seed7["produto_base"].append(segundo)
    db.session.add(ProdutoBase(id=2, slug="ocupado", nome="Existente", classe="fertilizante"))
    db.session.commit()
    with pytest.raises(SeedInvalidoError):
        importar_seed_catalogo(db.session, seed7)
    assert [(p.id, p.slug) for p in ProdutoBase.query.all()] == [(2, "ocupado")]
    assert ProdutoTecnico.query.count() == ProdutoImagem.query.count() == 0


def test_importacao_nova_tem_proveniencia_e_reimportacao_preserva_identificadores(seed_db, seed7):
    primeiro = importar_seed_catalogo(db.session, seed7)
    imagem = ProdutoImagem.query.one()
    ids = (ProdutoBase.query.one().id, ProdutoTecnico.query.one().id, imagem.id)
    assert imagem.origem_seed == "produto-global"
    assert len(imagem.seed_fingerprint) == 64
    fingerprint = imagem.seed_fingerprint
    segundo = importar_seed_catalogo(db.session, copy.deepcopy(seed7))
    imagem = ProdutoImagem.query.one()
    assert (ProdutoBase.query.one().id, ProdutoTecnico.query.one().id, imagem.id) == ids
    assert imagem.seed_fingerprint == fingerprint
    assert primeiro["imagem_inseridos"] == 1
    assert segundo["base_inseridos"] == segundo["tecnico_inseridos"] == segundo["imagem_inseridos"] == segundo["imagem_atualizados"] == 0


@pytest.mark.parametrize("campo,valor", [("url", "img/nova.jpg"), ("fonte", "Outra fonte pública"),
                                         ("status_validacao", "pendente"), ("observacoes", "Nova licença")])
def test_apenas_imagem_seed_com_fingerprint_intacto_pode_ser_atualizada(seed_db, seed7, campo, valor):
    importar_seed_catalogo(db.session, seed7)
    imagem = ProdutoImagem.query.one()
    id_anterior, fingerprint = imagem.id, imagem.seed_fingerprint
    seed7["produto_imagem"][0][campo] = valor
    resumo = importar_seed_catalogo(db.session, seed7)
    imagem = ProdutoImagem.query.one()
    assert imagem.id == id_anterior and getattr(imagem, campo) == valor
    assert imagem.seed_fingerprint != fingerprint
    assert resumo["imagem_atualizados"] == 1 and resumo["imagem_inseridos"] == 0


@pytest.mark.parametrize("campo,valor", [("url", "privado/administrado.jpg"), ("fonte", "Fonte administrativa"),
                                         ("status_validacao", "pendente"), ("observacoes", "Licença administrativa")])
def test_divergencia_administrada_nao_e_sobrescrita_pelo_seed(seed_db, seed7, campo, valor):
    importar_seed_catalogo(db.session, seed7)
    imagem = ProdutoImagem.query.one()
    fingerprint = imagem.seed_fingerprint
    setattr(imagem, campo, valor)
    db.session.commit()
    seed7["produto_imagem"][0]["url"] = "img/nova-referencia.jpg"
    resumo = importar_seed_catalogo(db.session, seed7)
    imagem = ProdutoImagem.query.one()
    assert getattr(imagem, campo) == valor and imagem.seed_fingerprint == fingerprint
    assert resumo["imagem_atualizados"] == resumo["imagem_inseridos"] == 0
    assert resumo["imagem_preservadas"] == 1


def test_imagem_legada_igual_ao_seed_nao_recebe_backfill_de_proveniencia(seed_db, seed7):
    db.session.add(ProdutoBase(id=1, slug="produto-global", nome="Produto global", classe="fertilizante"))
    db.session.flush()
    db.session.add(ProdutoImagem(**seed7["produto_imagem"][0]))
    db.session.commit()
    seed7["produto_imagem"][0]["url"] = "img/atualizada.jpg"
    resumo = importar_seed_catalogo(db.session, seed7)
    imagem = ProdutoImagem.query.one()
    assert imagem.url == "img/referencia.jpg"
    assert imagem.origem_seed is None and imagem.seed_fingerprint is None
    assert resumo["imagem_preservadas"] == 1


def test_varias_imagens_nao_selecionam_a_administrada_por_acaso(seed_db, seed7):
    importar_seed_catalogo(db.session, seed7)
    original = ProdutoImagem.query.one().id
    administrada = ProdutoImagem(produto_id=1, url="privado/imagem.jpg", fonte="Admin", observacoes="Licença Admin")
    db.session.add(administrada)
    db.session.commit()
    aid = administrada.id
    seed7["produto_imagem"][0]["url"] = "img/nova.jpg"
    resumo = importar_seed_catalogo(db.session, seed7)
    assert db.session.get(ProdutoImagem, original).url == "img/nova.jpg"
    assert (db.session.get(ProdutoImagem, aid).url, db.session.get(ProdutoImagem, aid).fonte) == ("privado/imagem.jpg", "Admin")
    assert ProdutoImagem.query.count() == 2 and resumo["imagem_atualizados"] == 1


def test_cache_anterior_nao_encobre_imagem_administrada_em_outra_sessao(seed_db, seed7):
    importar_seed_catalogo(db.session, seed7)
    imagem = ProdutoImagem.query.one()
    assert imagem.url == "img/referencia.jpg"
    with Session(db.engine) as outra:
        outra.execute(update(ProdutoImagem).where(ProdutoImagem.id == imagem.id)
                      .values(url="privado/administrada-depois.jpg"))
        outra.commit()
    # A identidade ORM local ainda contém o snapshot anterior ao commit externo.
    assert imagem.url == "img/referencia.jpg"
    resumo = importar_seed_catalogo(db.session, seed7)
    assert ProdutoImagem.query.one().url == "privado/administrada-depois.jpg"
    assert resumo["imagem_preservadas"] == 1 and resumo["imagem_atualizados"] == 0


@pytest.mark.parametrize("alteracao", ["fingerprint_ausente", "fingerprint_invalido", "origem_diferente", "origem_ambigua"])
def test_proveniencia_incerta_e_preservada_sem_escolha_arbitraria(seed_db, seed7, alteracao):
    importar_seed_catalogo(db.session, seed7)
    imagem = ProdutoImagem.query.one()
    if alteracao == "fingerprint_ausente":
        imagem.seed_fingerprint = None
    elif alteracao == "fingerprint_invalido":
        imagem.seed_fingerprint = "0"*64
    elif alteracao == "origem_diferente":
        imagem.origem_seed = "outra-origem"
    else:
        db.session.add(ProdutoImagem(produto_id=1, url=imagem.url, fonte=imagem.fonte,
            status_validacao=imagem.status_validacao, observacoes=imagem.observacoes,
            origem_seed=imagem.origem_seed, seed_fingerprint=imagem.seed_fingerprint))
    db.session.commit()
    antes = [(i.id, i.url, i.origem_seed, i.seed_fingerprint) for i in ProdutoImagem.query.order_by(ProdutoImagem.id)]
    seed7["produto_imagem"][0]["url"] = "img/nova.jpg"
    resumo = importar_seed_catalogo(db.session, seed7)
    assert [(i.id, i.url, i.origem_seed, i.seed_fingerprint) for i in ProdutoImagem.query.order_by(ProdutoImagem.id)] == antes
    assert resumo["imagem_preservadas"] == 1 and resumo["imagem_atualizados"] == 0


def test_importacao_preserva_base_ficha_preco_e_bloqueio_administrados(seed_db, seed7):
    importar_seed_catalogo(db.session, seed7)
    produto = ProdutoBase.query.one()
    produto.nome, produto.descricao_curta = "Nome administrado", "Descrição administrada"
    produto.status_sistema = "bloqueado_historico"
    ProdutoTecnico.query.one().fonte_tecnica = "Fonte administrada"
    imagem = ProdutoImagem.query.one()
    antes_imagem = (imagem.url, imagem.fonte, imagem.seed_fingerprint)
    db.session.add(ProdutoPreco(produto_id=1, valor=123.45, fonte="Dado anterior"))
    db.session.commit()
    seed7["produto_imagem"][0]["url"] = "img/nova.jpg"
    resumo = importar_seed_catalogo(db.session, seed7)
    produto = ProdutoBase.query.one()
    assert (produto.id, produto.slug, produto.nome, produto.descricao_curta, produto.status_sistema) == (1, "produto-global", "Nome administrado", "Descrição administrada", "bloqueado_historico")
    assert ProdutoTecnico.query.one().fonte_tecnica == "Fonte administrada"
    assert (imagem.url, imagem.fonte, imagem.seed_fingerprint) == antes_imagem
    assert ProdutoPreco.query.count() == 1 and ProdutoPreco.query.one().valor == 123.45
    assert resumo["imagem_atualizados"] == 0


def test_falha_apos_flush_desfaz_importacao_inteira(seed_db, seed7, monkeypatch):
    def falhar():
        raise RuntimeError("Falha de persistência simulada")

    with monkeypatch.context() as patch:
        patch.setattr(db.session, "commit", falhar)
        with pytest.raises(RuntimeError, match="simulada"):
            importar_seed_catalogo(db.session, seed7)
    assert ProdutoBase.query.count() == ProdutoTecnico.query.count() == ProdutoImagem.query.count() == 0
    assert ProdutoPreco.query.count() == 0


def test_seed_real_preserva_ids_e_fontes_sem_preco_nem_duplicacao(seed_db):
    seed = carregar_seed()
    importar_seed_catalogo(db.session, seed)
    antes = [(p.id, p.slug, p.status_sistema, p.status_regulatorio) for p in ProdutoBase.query.order_by(ProdutoBase.id)]
    imagens = [(i.id, i.produto_id, i.url, i.fonte, i.observacoes) for i in ProdutoImagem.query.order_by(ProdutoImagem.id)]
    resumo = importar_seed_catalogo(db.session, copy.deepcopy(seed))
    assert antes == [(p["id"], p["slug"], p["status_sistema"], p["status_regulatorio"]) for p in seed["produto_base"]]
    assert [(p.id, p.slug, p.status_sistema, p.status_regulatorio) for p in ProdutoBase.query.order_by(ProdutoBase.id)] == antes
    assert [(i.id, i.produto_id, i.url, i.fonte, i.observacoes) for i in ProdutoImagem.query.order_by(ProdutoImagem.id)] == imagens
    assert ProdutoBase.query.count() == ProdutoTecnico.query.count() == ProdutoImagem.query.count() == 60
    assert ProdutoPreco.query.count() == 0
    assert resumo["imagem_inseridos"] == resumo["imagem_atualizados"] == 0


def test_importacao_nao_altera_custos_produtos_ou_quantidades_historicos(seed_db, seed7):
    from app.models import (AplicacaoInsumo, AtividadeItem, AtividadeOperacional,
        Cultura, CulturaGleba, Gleba, Propriedade, Usuario)

    importar_seed_catalogo(db.session, seed7)
    usuario = Usuario(nome="Autor", email="autor@seed.invalid", perfil="admin", senha_hash="fixture")
    db.session.add(usuario); db.session.flush()
    propriedade = Propriedade(usuario_id=usuario.id, nome="Propriedade")
    db.session.add(propriedade); db.session.flush()
    gleba = Gleba(propriedade_id=propriedade.id, nome="Área")
    cultura = Cultura(propriedade_id=propriedade.id, nome="Cultura")
    db.session.add_all([gleba, cultura]); db.session.flush()
    cg = CulturaGleba(cultura_id=cultura.id, gleba_id=gleba.id)
    atividade = AtividadeOperacional(gleba_id=gleba.id, tipo_atividade="Inspeção",
        data_execucao="2026-11-01", responsavel="Executor", criado_por_id=usuario.id)
    db.session.add_all([cg, atividade]); db.session.flush()
    aplicacao = AplicacaoInsumo(cultura_gleba_id=cg.id, produto_base_id=1,
        data_aplicacao="2026-11-01", dose=2.5, unidade="L/ha", quantidade_utilizada=Decimal("15.123456"),
        unidade_quantidade="L", custo_total=Decimal("99.99"), moeda="BRL")
    item = AtividadeItem(atividade_id=atividade.id, produto_base_id=1,
        quantidade_utilizada=Decimal("3.123456"), unidade_quantidade="kg", custo_total=Decimal("12.34"), moeda="BRL")
    db.session.add_all([aplicacao, item]); db.session.commit()
    antes = (aplicacao.produto_base_id, aplicacao.dose, aplicacao.quantidade_utilizada,
             aplicacao.custo_total, item.produto_base_id, item.quantidade_utilizada, item.custo_total)
    seed7["produto_imagem"][0]["url"] = "img/nova.jpg"
    importar_seed_catalogo(db.session, seed7)
    assert (aplicacao.produto_base_id, aplicacao.dose, aplicacao.quantidade_utilizada,
            aplicacao.custo_total, item.produto_base_id, item.quantidade_utilizada, item.custo_total) == antes


def test_sincronizar_sequence_sqlite_e_noop_sem_sql_postgres(seed_db):
    sql = []

    def capturar(conn, cursor, statement, parameters, context, executemany):
        sql.append(statement)

    event.listen(db.engine, "before_cursor_execute", capturar)
    try:
        sincronizar_seq_produto_base(db.session)
    finally:
        event.remove(db.engine, "before_cursor_execute", capturar)
    assert sql == []
