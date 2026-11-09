"""Evolução real f6→g7, preservação e reversão protegida em SQLite descartável."""
from decimal import Decimal
from pathlib import Path

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from flask_migrate import downgrade, upgrade
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models import (AplicacaoInsumo, AtividadeItem, CatalogoControle,
                        CatalogoRevisao, ProdutoBase, ProdutoImagem, ProdutoLocal,
                        ProdutoPersonalizacao, SolicitacaoCatalogo, Usuario)

MIGRATIONS = str(Path(__file__).resolve().parents[1] / "migrations")
ANTERIOR = "f6a28d9c104e"
NOVA = "g7c53b8e19a2"
NOVAS_TABELAS = {"catalogo_controle", "produto_local", "produto_personalizacao",
                 "catalogo_revisao", "solicitacao_catalogo"}


def _snapshot(colunas):
    with db.engine.connect() as conexao:
        return {tabela: conexao.execute(sa.text(
            f'SELECT {",".join(nomes)} FROM {tabela} ORDER BY id')).all()
            for tabela, nomes in colunas.items()}


def _colunas():
    insp = sa.inspect(db.engine)
    return {tabela: [c["name"] for c in insp.get_columns(tabela)]
            for tabela in insp.get_table_names() if tabela != "alembic_version"}


def _preparar_f6():
    upgrade(directory=MIGRATIONS, revision=ANTERIOR)
    with db.engine.begin() as c:
        c.execute(sa.text("PRAGMA foreign_keys=ON"))
        assert c.execute(sa.text("PRAGMA foreign_keys")).scalar() == 1
        # SQL histórico explícito: defaults de modelos futuros não são colunas
        # da revisão f6 e não podem contaminar o preparo da instalação antiga.
        statements = [
            "INSERT INTO usuario (id,nome,email,senha_hash,perfil,ativo,auth_version,criado_em) VALUES (1,'Admin original','admin@catalogo.legacy.invalid','hash-original','admin',1,3,'2001-01-01')",
            "INSERT INTO usuario (id,nome,email,senha_hash,perfil,ativo,auth_version,criado_em) VALUES (2,'Trabalhador original','worker@catalogo.legacy.invalid','outro-hash','trabalhador',1,2,'2002-02-02')",
            "INSERT INTO propriedade (id,usuario_id,nome,area_total_ha,poligono_geojson,criado_em) VALUES (10,1,'Propriedade antiga',125.5,'{geometria-legada}','2001-01-01')",
            "INSERT INTO propriedade (id,usuario_id,nome,area_total_ha,criado_em) VALUES (20,2,'Outro contexto',70.25,'2002-02-02')",
            "INSERT INTO usuario_propriedade (id,usuario_id,propriedade_id,ativo,criado_em) VALUES (30,1,10,1,'2001-01-01'),(31,2,10,1,'2002-02-02'),(32,2,20,0,'2002-02-02')",
            "INSERT INTO gleba (id,propriedade_id,nome,area_ha,poligono_geojson,status,criado_em) VALUES (100,10,'Área antiga',1.25,'{poligono-antigo}','ativa','2001-01-01')",
            "INSERT INTO cultura (id,propriedade_id,nome,status,criado_em) VALUES (101,10,'Cultura antiga','em_andamento','2001-01-01')",
            "INSERT INTO cultura_gleba (id,cultura_id,gleba_id,observacoes) VALUES (102,101,100,'Associação preservada')",
            "INSERT INTO produto_base (id,nome,slug,classe,categoria,status_sistema,status_regulatorio,criado_em) VALUES (200,'Produto global antigo','produto-global-antigo','fertilizante','mineral','pre_cadastrado','sujeito_a_sipeagro_nao_validado','2001-01-01')",
            "INSERT INTO produto_base (id,nome,slug,classe,status_sistema,status_regulatorio,criado_em) VALUES (201,'Histórico bloqueado','historico-bloqueado','defensivo','bloqueado_historico','bloqueado_historico','2001-01-01')",
            "INSERT INTO produto_tecnico (id,produto_id,grupo_quimico,fonte_tecnica,observacoes) VALUES (210,200,'Grupo original','Fonte original','Ficha original')",
            "INSERT INTO produto_preco (id,produto_id,valor,moeda,status_validacao,criado_em) VALUES (220,200,NULL,'BRL','pendente','2001-01-01')",
            "INSERT INTO produto_imagem (id,produto_id,url,fonte,status_validacao,observacoes,criado_em) VALUES (230,200,'/static/img/original.svg','Fonte e licença originais','nao_consolidado','Imagem original','2001-01-01')",
            "INSERT INTO aplicacao_insumo (id,cultura_gleba_id,produto_base_id,data_aplicacao,dose,unidade,responsavel,criado_em,criado_por_id,responsavel_usuario_id,quantidade_utilizada,unidade_quantidade,custo_unitario,custo_total,moeda,origem_custo) VALUES (240,102,200,'2005-05-05',2.5,'L/ha','Executor histórico','2006-06-06',1,2,'15.000001','L','2.125000','31.88','BRL','informado_usuario')",
            "INSERT INTO colheita_registro (id,cultura_gleba_id,data_colheita,quantidade,unidade,observacao,criado_em,responsavel,criado_por_id) VALUES (250,102,'2005-05-05',100.25,'sc','Colheita original','2006-06-06','Executor antigo',1)",
            "INSERT INTO atividade_operacional (id,gleba_id,cultura_gleba_id,tipo_atividade,data_execucao,responsavel,responsavel_usuario_id,criado_por_id,criado_em,observacao,chave_envio) VALUES (260,100,102,'Atividade original','2005-05-05','Executor histórico',2,1,'2006-06-06','Observação privada antiga','chave-original')",
            "INSERT INTO atividade_item (id,atividade_id,produto_base_id,dose,unidade_dose,quantidade_utilizada,unidade_quantidade,custo_unitario,custo_total,moeda,origem_custo) VALUES (270,260,200,'2.500000','L/ha','15.000001','L','2.125000','31.88','BRL','informado_usuario')",
            "INSERT INTO financeiro_lancamento (id,propriedade_id,tipo,descricao,valor,data,criado_em) VALUES (280,10,'receita','Receita original',555.5,'2005-05-05','2006-06-06')",
            "INSERT INTO equipe_membro (id,propriedade_id,nome,ativo,criado_em) VALUES (290,10,'Membro original',1,'2001-01-01')",
            "INSERT INTO upload_arquivo (id,propriedade_id,nome_original,caminho,enviado_em) VALUES (300,10,'Documento antigo.txt','propriedade_10/original.txt','2001-01-01')",
            "INSERT INTO ia_interacao (id,usuario_id,propriedade_id,pergunta,resposta,tipo,criado_em) VALUES (310,1,10,'Pergunta original','Resposta original','simulada','2001-01-01')",
            "INSERT INTO log_auditoria (id,usuario_id,propriedade_id,acao,descricao,resultado,criado_em) VALUES (320,1,10,'historico.original','Auditoria original','sucesso','2001-01-01')",
        ]
        for statement in statements:
            c.execute(sa.text(statement))
    colunas = _colunas()
    return colunas, _snapshot(colunas)


def _preparar_g7():
    colunas, anterior = _preparar_f6()
    upgrade(directory=MIGRATIONS, revision=NOVA)
    assert _snapshot(colunas) == anterior
    return colunas, anterior


def _local(**campos):
    valores = dict(propriedade_id=10, nome="Nome local", classe="fertilizante",
                   criado_por_id=1)
    valores.update(campos)
    registro = ProdutoLocal(**valores)
    db.session.add(registro)
    db.session.flush()
    return registro


def _personalizacao(**campos):
    valores = dict(propriedade_id=10, produto_base_id=200, nome_local="Nome do contexto",
                   criado_por_id=1)
    valores.update(campos)
    registro = ProdutoPersonalizacao(**valores)
    db.session.add(registro)
    db.session.flush()
    return registro


def test_upgrade_preserva_ids_slugs_imagens_fks_custos_e_historico(app):
    with app.app_context():
        antigas, anterior = _preparar_g7()
        assert len(antigas) == 20
        assert _snapshot(antigas) == anterior
        with db.engine.connect() as c:
            assert c.execute(sa.text("PRAGMA foreign_keys")).scalar() == 1
            assert c.execute(sa.text("PRAGMA foreign_key_check")).all() == []
            assert c.execute(sa.text("SELECT version_num FROM alembic_version")).scalar() == NOVA
            assert c.execute(sa.text("SELECT id FROM catalogo_controle")).all() == [(1,)]
            for tabela in NOVAS_TABELAS - {"catalogo_controle"}:
                assert c.execute(sa.text(f"SELECT COUNT(*) FROM {tabela}")).scalar() == 0
            assert c.execute(sa.text("SELECT catalogo_global_aprovador FROM usuario ORDER BY id")).all() == [(0,), (0,)]
            assert c.execute(sa.text("SELECT origem_seed,seed_fingerprint FROM produto_imagem")).all() == [(None, None)]
            assert compare_metadata(MigrationContext.configure(c), db.metadata) == []
        assert db.session.get(ProdutoBase, 200).slug == "produto-global-antigo"
        assert db.session.get(AplicacaoInsumo, 240).produto_base_id == 200
        assert db.session.get(AtividadeItem, 270).produto_base_id == 200
        assert db.session.get(AtividadeItem, 270).quantidade_utilizada == Decimal("15.000001")
        assert db.session.get(AtividadeItem, 270).custo_total == Decimal("31.88")
        upgrade(directory=MIGRATIONS, revision=NOVA)
        assert _snapshot(antigas) == anterior
        assert CatalogoControle.query.count() == 1


def test_flag_global_nunca_e_concedida_por_default_ou_perfil_admin(app):
    with app.app_context():
        _preparar_g7()
        assert db.session.get(Usuario, 1).perfil == "admin"
        assert db.session.get(Usuario, 1).catalogo_global_aprovador is False
        novo = Usuario(nome="Outro admin", email="new@catalogo.legacy.invalid",
                       senha_hash="hash", perfil="admin")
        db.session.add(novo)
        db.session.commit()
        assert novo.catalogo_global_aprovador is False
        with db.engine.begin() as c:
            c.execute(sa.text("INSERT INTO usuario (id,nome,email,senha_hash,perfil,ativo,criado_em) VALUES (99,'SQL admin','sql@catalogo.legacy.invalid','hash','admin',1,'old')"))
            assert c.execute(sa.text("SELECT catalogo_global_aprovador FROM usuario WHERE id=99")).scalar() == 0


def test_downgrade_vazio_e_reupgrade_preservam_todas_as_colunas_antigas(app):
    with app.app_context():
        antigas, anterior = _preparar_g7()
        downgrade(directory=MIGRATIONS, revision=ANTERIOR)
        assert _snapshot(antigas) == anterior
        assert not NOVAS_TABELAS.intersection(sa.inspect(db.engine).get_table_names())
        assert "catalogo_global_aprovador" not in {c["name"] for c in sa.inspect(db.engine).get_columns("usuario")}
        assert not {"origem_seed", "seed_fingerprint"}.intersection(
            c["name"] for c in sa.inspect(db.engine).get_columns("produto_imagem"))
        upgrade(directory=MIGRATIONS, revision=NOVA)
        assert _snapshot(antigas) == anterior
        with db.engine.connect() as c:
            assert c.execute(sa.text("PRAGMA foreign_key_check")).all() == []
            assert compare_metadata(MigrationContext.configure(c), db.metadata) == []


@pytest.mark.parametrize("campo,valor", [
    ("catalogo_global_aprovador", 1), ("origem_seed", ""),
    ("origem_seed", "seed-oficial"), ("seed_fingerprint", ""),
    ("seed_fingerprint", "a" * 64),
])
def test_downgrade_preflight_preserva_flag_ou_proveniencia_sem_ddl(app, campo, valor):
    with app.app_context():
        _preparar_g7()
        tabela, identificador = ("usuario", 1) if campo == "catalogo_global_aprovador" else ("produto_imagem", 230)
        with db.engine.begin() as c:
            c.execute(sa.text(f"UPDATE {tabela} SET {campo}=:valor WHERE id=:id"), {"valor": valor, "id": identificador})
        colunas, antes = _colunas(), _snapshot(_colunas())
        config = app.extensions["migrate"].migrate.get_config(MIGRATIONS)
        with pytest.raises(RuntimeError, match="Downgrade bloqueado"):
            command.downgrade(config, ANTERIOR)
        assert _colunas() == colunas and _snapshot(colunas) == antes
        with db.engine.connect() as c:
            assert c.execute(sa.text("SELECT version_num FROM alembic_version")).scalar() == NOVA


@pytest.mark.parametrize("origem", ["local", "personalizacao", "revisao", "solicitacao"])
@pytest.mark.parametrize("inativo", [False, True])
def test_downgrade_bloqueia_dominio_inclusive_inativo_e_decisao_rejeitada(app, origem, inativo):
    with app.app_context():
        _preparar_g7()
        if origem == "personalizacao":
            _personalizacao(ativo=not inativo)
        else:
            local = _local(ativo=not inativo)
            if origem == "revisao":
                db.session.add(CatalogoRevisao(propriedade_id=10, produto_local_id=local.id,
                    versao=1, snapshot_json='{"nome":"Histórico"}', alterado_por_id=1, acao="create"))
            elif origem == "solicitacao":
                db.session.add(SolicitacaoCatalogo(propriedade_id=10, produto_local_id=local.id,
                    origem_versao=1, tipo="inclusao", conteudo_json='{"nome":"Proposta"}',
                    estado="rejeitada" if inativo else "pendente", solicitado_por_id=1))
        db.session.commit()
        colunas = _colunas(); antes = _snapshot(colunas)
        config = app.extensions["migrate"].migrate.get_config(MIGRATIONS)
        with pytest.raises(RuntimeError, match="Downgrade bloqueado"):
            command.downgrade(config, ANTERIOR)
        assert _colunas() == colunas and _snapshot(colunas) == antes


def test_personalizacao_unica_por_propriedade_produto_sem_publicacao_ou_copia(app):
    with app.app_context():
        antigas, antes = _preparar_g7()
        primeiro = _personalizacao()
        db.session.commit()
        assert _snapshot(antigas) == antes
        assert primeiro.produto.id == 200 and primeiro.nome_local != primeiro.produto.nome
        with pytest.raises(IntegrityError):
            _personalizacao(ativo=False)
        db.session.rollback()
        outro = _personalizacao(propriedade_id=20)
        db.session.commit()
        assert outro.id != primeiro.id and outro.produto_base_id == primeiro.produto_base_id
        assert ProdutoBase.query.count() == 2 and ProdutoLocal.query.count() == 0


def test_produto_local_categorias_opcionais_chave_unica_e_contexto_preservados(app):
    with app.app_context():
        antigas, antes = _preparar_g7()
        local = _local(chave_envio="key-original")
        db.session.commit()
        assert local.categoria is None and local.ativo and local.versao == 1
        assert local.criado_por.id == 1 and local.propriedade.id == 10
        assert _snapshot(antigas) == antes and ProdutoBase.query.count() == 2
        with pytest.raises(IntegrityError):
            _local(chave_envio="key-original", propriedade_id=20)
        db.session.rollback()
        assert ProdutoLocal.query.count() == 1


@pytest.mark.parametrize("classe", [CatalogoRevisao, SolicitacaoCatalogo])
@pytest.mark.parametrize("ambas", [False, True])
def test_origem_xor_exige_exatamente_um_produto_local_ou_personalizacao(app, classe, ambas):
    with app.app_context():
        _preparar_g7()
        local, personalizacao = _local(), _personalizacao()
        db.session.commit()
        dados = dict(propriedade_id=10, produto_local_id=local.id if ambas else None,
                     personalizacao_id=personalizacao.id if ambas else None)
        if classe is CatalogoRevisao:
            dados.update(versao=1, snapshot_json="{}", alterado_por_id=1, acao="create")
        else:
            dados.update(origem_versao=1, tipo="inclusao", conteudo_json="{}", solicitado_por_id=1)
        db.session.add(classe(**dados))
        with pytest.raises(IntegrityError):
            db.session.commit()
        db.session.rollback()
        assert classe.query.count() == 0


@pytest.mark.parametrize("classe", [CatalogoRevisao, SolicitacaoCatalogo])
@pytest.mark.parametrize("tipo", ["local", "personalizacao"])
def test_revisao_e_solicitacao_nao_repetem_mesma_origem_versao(app, classe, tipo):
    with app.app_context():
        _preparar_g7()
        origem = _local() if tipo == "local" else _personalizacao()
        db.session.commit()
        dados = dict(propriedade_id=10, **{"produto_local_id" if tipo == "local" else "personalizacao_id": origem.id})
        if classe is CatalogoRevisao:
            dados.update(versao=1, snapshot_json="{}", alterado_por_id=1, acao="create")
        else:
            dados.update(origem_versao=1, tipo="inclusao" if tipo == "local" else "alteracao",
                         conteudo_json="{}", solicitado_por_id=1)
        db.session.add(classe(**dados)); db.session.commit()
        db.session.add(classe(**dados))
        with pytest.raises(IntegrityError):
            db.session.commit()
        db.session.rollback()
        assert classe.query.count() == 1


@pytest.mark.parametrize("classe", [ProdutoLocal, ProdutoPersonalizacao, CatalogoRevisao, SolicitacaoCatalogo])
def test_versoes_nao_positivas_sao_recusadas_pelo_banco(app, classe):
    with app.app_context():
        _preparar_g7()
        if classe is ProdutoLocal:
            objeto = ProdutoLocal(propriedade_id=10, nome="Local", classe="fertilizante", criado_por_id=1, versao=0)
        elif classe is ProdutoPersonalizacao:
            objeto = ProdutoPersonalizacao(propriedade_id=10, produto_base_id=200, criado_por_id=1, versao=0)
        else:
            local = _local(); db.session.commit()
            if classe is CatalogoRevisao:
                objeto = CatalogoRevisao(propriedade_id=10, produto_local_id=local.id, versao=0,
                                         snapshot_json="{}", alterado_por_id=1, acao="create")
            else:
                objeto = SolicitacaoCatalogo(propriedade_id=10, produto_local_id=local.id,
                    origem_versao=0, tipo="inclusao", conteudo_json="{}", solicitado_por_id=1)
        db.session.add(objeto)
        with pytest.raises(IntegrityError):
            db.session.commit()
        db.session.rollback()


def test_controle_singleton_e_fks_preservam_historico_sem_cascade(app):
    with app.app_context():
        _preparar_g7()
        db.session.add(CatalogoControle(id=2))
        with pytest.raises(IntegrityError):
            db.session.commit()
        db.session.rollback()
        local = _local()
        db.session.add(CatalogoRevisao(propriedade_id=10, produto_local_id=local.id,
            versao=1, snapshot_json='{"nome":"Original"}', alterado_por_id=1, acao="create"))
        db.session.commit()
        colunas = _colunas(); antes = _snapshot(colunas)
        for tabela, identificador in (("produto_local", local.id), ("produto_base", 200), ("usuario", 1), ("propriedade", 10)):
            with pytest.raises(IntegrityError):
                with db.engine.begin() as c:
                    c.execute(sa.text(f"DELETE FROM {tabela} WHERE id=:id"), {"id": identificador})
            assert _snapshot(colunas) == antes
        with db.engine.connect() as c:
            assert c.execute(sa.text("PRAGMA foreign_key_check")).all() == []


def test_revisoes_e_solicitacoes_carregam_relacoes_explicitas_sem_publicar(app):
    with app.app_context():
        _preparar_g7()
        local, personalizacao = _local(), _personalizacao()
        revisao = CatalogoRevisao(propriedade_id=10, personalizacao_id=personalizacao.id,
            versao=1, snapshot_json='{"nome_local":"Rótulo"}', alterado_por_id=1, acao="create")
        solicitacao = SolicitacaoCatalogo(propriedade_id=10, produto_local_id=local.id,
            origem_versao=1, tipo="inclusao", conteudo_json='{"nome":"Proposta"}', solicitado_por_id=2)
        db.session.add_all([revisao, solicitacao]); db.session.commit()
        assert revisao.personalizacao.produto.id == 200 and revisao.alterado_por.id == 1
        assert solicitacao.produto_local.id == local.id and solicitacao.solicitado_por.id == 2
        assert solicitacao.estado == "pendente" and solicitacao.produto_publicado is None
        assert solicitacao.decidido_por is None and solicitacao.global_anterior_json is None
        assert ProdutoBase.query.count() == 2 and ProdutoImagem.query.count() == 1
