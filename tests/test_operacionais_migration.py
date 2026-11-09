"""Evolução e4→f6 em SQLite populado, com foreign_keys ativo e sem backfill."""
from decimal import Decimal
from pathlib import Path

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
from flask_migrate import downgrade, upgrade
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models import AtividadeItem, AtividadeOperacional

MIGRATIONS = str(Path(__file__).resolve().parents[1] / "migrations")
ANTERIOR = "e4ca60b1d732"
NOVA = "f6a28d9c104e"
NOVAS_COLUNAS = {
    "aplicacao_insumo": ["responsavel_usuario_id", "criado_por_id", "atualizado_por_id",
        "atualizado_em", "chave_envio", "quantidade_utilizada", "unidade_quantidade",
        "custo_unitario", "custo_total", "moeda", "origem_custo"],
    "colheita_registro": ["responsavel", "responsavel_usuario_id", "criado_por_id",
        "atualizado_por_id", "atualizado_em", "chave_envio"],
}


def _preparar_legado():
    upgrade(directory=MIGRATIONS, revision=ANTERIOR)
    with db.engine.begin() as c:
        c.execute(sa.text("PRAGMA foreign_keys=ON"))
        assert c.execute(sa.text("PRAGMA foreign_keys")).scalar() == 1
        statements = [
            "INSERT INTO usuario (id,nome,email,senha_hash,perfil,ativo,criado_em) VALUES (1,'Gerente','operacional@legacy.invalid','hash-antigo','tecnico',1,'2001-01-01')",
            "INSERT INTO usuario (id,nome,email,senha_hash,perfil,ativo,criado_em) VALUES (2,'Executor','executor@legacy.invalid','hash-original','trabalhador',1,'2002-02-02')",
            "INSERT INTO propriedade (id,usuario_id,nome,area_total_ha,poligono_geojson,criado_em) VALUES (10,1,'Propriedade original',12.25,'{contorno-legado}','2001-01-01')",
            "INSERT INTO usuario_propriedade (id,usuario_id,propriedade_id,ativo,criado_em) VALUES (11,1,10,1,'2001-01-01')",
            "INSERT INTO usuario_propriedade (id,usuario_id,propriedade_id,ativo,criado_em) VALUES (12,2,10,1,'2002-02-02')",
            "INSERT INTO gleba (id,propriedade_id,nome,area_ha,poligono_geojson,status,criado_em) VALUES (20,10,'Área original',7.5,'{poligono-legado}','ativa','2001-01-01')",
            "INSERT INTO cultura (id,propriedade_id,nome,status,criado_em) VALUES (30,10,'Cultura original','em_andamento','2001-01-01')",
            "INSERT INTO cultura_gleba (id,cultura_id,gleba_id,observacoes) VALUES (40,30,20,'Associação original')",
            "INSERT INTO produto_base (id,nome,slug,classe,status_sistema,status_regulatorio,criado_em) VALUES (50,'Produto histórico','produto-legado-operacional','fertilizante','bloqueado_historico','bloqueado_historico','2001-01-01')",
            "INSERT INTO aplicacao_insumo (id,cultura_gleba_id,produto_base_id,data_aplicacao,dose,unidade,responsavel,observacao,criado_em) VALUES (60,40,50,'2003-03-03',2.5,'L/ha','Nome histórico livre','Observação original','2004-04-04')",
            "INSERT INTO colheita_registro (id,cultura_gleba_id,data_colheita,quantidade,unidade,observacao,criado_em) VALUES (70,40,'2003-03-03',100.25,'kg','Colheita original','2004-04-04')",
            "INSERT INTO financeiro_lancamento (id,propriedade_id,tipo,descricao,valor,data,criado_em) VALUES (80,10,'despesa','Despesa original',123.45,'2003-03-03','2004-04-04')",
            "INSERT INTO equipe_membro (id,propriedade_id,nome,ativo,criado_em) VALUES (90,10,'Membro sem conta',1,'2001-01-01')",
            "INSERT INTO upload_arquivo (id,propriedade_id,nome_original,caminho,enviado_em) VALUES (100,10,'Documento original.txt','preservar/original.txt','2001-01-01')",
            "INSERT INTO ia_interacao (id,usuario_id,propriedade_id,pergunta,resposta,tipo,criado_em) VALUES (110,1,10,'Pergunta original','Resposta original','simulada','2001-01-01')",
            "INSERT INTO log_auditoria (id,usuario_id,propriedade_id,acao,descricao,resultado,criado_em) VALUES (120,1,10,'original','Auditoria original','sucesso','2001-01-01')",
        ]
        for statement in statements:
            c.execute(sa.text(statement))
    inspector = sa.inspect(db.engine)
    colunas = {table: [column["name"] for column in inspector.get_columns(table)]
               for table in inspector.get_table_names() if table != "alembic_version"}
    return colunas, _snapshot(colunas)


def _snapshot(colunas):
    with db.engine.connect() as c:
        return {table: c.execute(sa.text(
            f'SELECT {",".join(columns)} FROM {table} ORDER BY id')).all()
            for table, columns in colunas.items()}


def test_upgrade_preserva_historico_poligonos_e_colunas_novas_ausentes(app):
    with app.app_context():
        colunas, antes = _preparar_legado()
        # O contrato de dados e4→f6 também deve sobreviver ao head atual; os
        # testes de downgrade abaixo continuam isolando a própria revisão f6.
        upgrade(directory=MIGRATIONS)
        assert _snapshot(colunas) == antes
        with db.engine.connect() as c:
            assert c.execute(sa.text("PRAGMA foreign_key_check")).all() == []
            assert c.execute(sa.text("PRAGMA foreign_keys")).scalar() == 1
            config = app.extensions['migrate'].migrate.get_config(MIGRATIONS)
            assert c.execute(sa.text("SELECT version_num FROM alembic_version")).scalar() == ScriptDirectory.from_config(config).get_current_head()
            for tabela, novas in NOVAS_COLUNAS.items():
                values = c.execute(sa.text(f'SELECT {",".join(novas)} FROM {tabela}')).one()
                assert all(value is None for value in values)
                infos = {col["name"]: col for col in sa.inspect(c).get_columns(tabela)}
                assert all(infos[nome]["nullable"] and infos[nome]["default"] is None for nome in novas)
            assert c.execute(sa.text("SELECT COUNT(*) FROM atividade_operacional")).scalar() == 0
            assert c.execute(sa.text("SELECT COUNT(*) FROM atividade_item")).scalar() == 0
            assert compare_metadata(MigrationContext.configure(c), db.metadata) == []
        upgrade(directory=MIGRATIONS)
        assert _snapshot(colunas) == antes


def test_downgrade_vazio_e_reupgrade_preservam_historico(app):
    with app.app_context():
        colunas, antes = _preparar_legado()
        upgrade(directory=MIGRATIONS, revision=NOVA)
        downgrade(directory=MIGRATIONS, revision=ANTERIOR)
        assert _snapshot(colunas) == antes
        inspector = sa.inspect(db.engine)
        assert "atividade_operacional" not in inspector.get_table_names()
        for tabela, novas in NOVAS_COLUNAS.items():
            assert not set(novas) & {c["name"] for c in inspector.get_columns(tabela)}
        upgrade(directory=MIGRATIONS, revision=NOVA)
        assert _snapshot(colunas) == antes


@pytest.mark.parametrize("tabela,campo", [
    (tabela, campo) for tabela, campos in NOVAS_COLUNAS.items() for campo in campos
])
def test_downgrade_bloqueia_qualquer_campo_novo_antes_de_ddl(app, tabela, campo):
    with app.app_context():
        colunas, antes = _preparar_legado()
        upgrade(directory=MIGRATIONS, revision=NOVA)
        valor = 1 if campo.endswith("_id") else "0" if campo in {
            "quantidade_utilizada", "custo_unitario", "custo_total"} else ""
        with db.engine.begin() as c:
            c.execute(sa.text(f"UPDATE {tabela} SET {campo}=:valor"), {"valor": valor})
        config = app.extensions["migrate"].migrate.get_config(MIGRATIONS)
        with pytest.raises(RuntimeError, match="Downgrade bloqueado"):
            command.downgrade(config, ANTERIOR)
        assert _snapshot(colunas) == antes
        with db.engine.connect() as c:
            assert c.execute(sa.text("SELECT version_num FROM alembic_version")).scalar() == NOVA
            assert c.execute(sa.text(f"SELECT {campo} FROM {tabela}")).scalar() is not None
            assert "atividade_operacional" in sa.inspect(c).get_table_names()


@pytest.mark.parametrize("cancelada", [False, True])
def test_downgrade_bloqueia_atividade_mesmo_sem_itens_ou_cancelada(app, cancelada):
    with app.app_context():
        _preparar_legado()
        upgrade(directory=MIGRATIONS, revision=NOVA)
        atividade = AtividadeOperacional(gleba_id=20, tipo_atividade="Inspeção livre",
            data_execucao="2026-11-08", criado_por_id=1,
            cancelado_em="2026-11-08" if cancelada else None,
            cancelado_por_id=1 if cancelada else None)
        db.session.add(atividade)
        db.session.commit()
        db.session.remove()
        config = app.extensions["migrate"].migrate.get_config(MIGRATIONS)
        with pytest.raises(RuntimeError, match="Downgrade bloqueado"):
            command.downgrade(config, ANTERIOR)
        with db.engine.connect() as c:
            assert c.execute(sa.text("SELECT COUNT(*) FROM atividade_operacional")).scalar() == 1
            assert c.execute(sa.text("SELECT version_num FROM alembic_version")).scalar() == NOVA


def test_itens_multiplos_decimais_e_fk_impedem_exclusao_cascata(app):
    with app.app_context():
        _preparar_legado()
        # Relacionamentos ORM usam o modelo atual e, portanto, schema no head.
        upgrade(directory=MIGRATIONS)
        atividade = AtividadeOperacional(gleba_id=20, cultura_gleba_id=40,
            tipo_atividade="Atividade informada", data_execucao="2026-11-08",
            responsavel="Nome informado", responsavel_usuario_id=2, criado_por_id=1)
        atividade.itens = [AtividadeItem(produto_base_id=50,
            dose=Decimal("2.500000"), unidade_dose="L/ha",
            quantidade_utilizada=Decimal("999999999999.999999"), unidade_quantidade="L",
            custo_total=Decimal("9999999999999999.99"), moeda="BRL", origem_custo="informado"),
            AtividadeItem(produto_base_id=50, quantidade_utilizada=Decimal("1.000001"),
                          unidade_quantidade="kg")]
        db.session.add(atividade)
        db.session.commit()
        chave = atividade.id
        db.session.remove()
        persistida = db.session.get(AtividadeOperacional, chave)
        assert persistida.gleba.id == 20 and persistida.cultura_gleba.id == 40
        assert persistida.criado_por.id == 1 and persistida.responsavel_usuario.id == 2
        assert len(persistida.itens) == 2
        assert persistida.itens[0].quantidade_utilizada == Decimal("999999999999.999999")
        assert persistida.itens[0].custo_total == Decimal("9999999999999999.99")
        assert persistida.itens[1].custo_total is None
        db.session.delete(persistida)
        with pytest.raises(IntegrityError):
            db.session.commit()
        db.session.rollback()
        assert db.session.get(AtividadeOperacional, chave) is not None
        assert AtividadeItem.query.count() == 2
        db.session.remove()
        with db.engine.connect() as c:
            assert c.execute(sa.text("PRAGMA foreign_key_check")).all() == []
            assert c.execute(sa.text("SELECT COUNT(*) FROM financeiro_lancamento")).scalar() == 1


@pytest.mark.parametrize("tabela,colunas,valores", [
    ("aplicacao_insumo", "cultura_gleba_id,produto_base_id,data_aplicacao,criado_em", "40,50,'2026-11-08','cadastro'"),
    ("colheita_registro", "cultura_gleba_id,data_colheita,criado_em", "40,'2026-11-08','cadastro'"),
    ("atividade_operacional", "gleba_id,tipo_atividade,data_execucao,criado_em", "20,'Inspeção','2026-11-08','cadastro'"),
])
def test_chave_envio_unica_com_null_permitido_para_historicos(app, tabela, colunas, valores):
    with app.app_context():
        _preparar_legado()
        upgrade(directory=MIGRATIONS, revision=NOVA)
        with db.engine.begin() as c:
            for _ in range(2):
                c.execute(sa.text(f"INSERT INTO {tabela} ({colunas}) VALUES ({valores})"))
            c.execute(sa.text(f"INSERT INTO {tabela} ({colunas},chave_envio) VALUES ({valores},'chave-repetida')"))
        with pytest.raises(IntegrityError):
            with db.engine.begin() as c:
                c.execute(sa.text(f"INSERT INTO {tabela} ({colunas},chave_envio) VALUES ({valores},'chave-repetida')"))
        with db.engine.connect() as c:
            assert c.execute(sa.text(f"SELECT COUNT(*) FROM {tabela} WHERE chave_envio='chave-repetida'")).scalar() == 1
            assert c.execute(sa.text(f"SELECT COUNT(*) FROM {tabela} WHERE chave_envio IS NULL")).scalar() >= 2
            assert c.execute(sa.text("PRAGMA foreign_key_check")).all() == []
