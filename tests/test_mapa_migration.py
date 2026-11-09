"""Upgrade real d3→e4 e reversão sem perda de contornos em SQLite descartável."""
import json
from pathlib import Path

import pytest
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
from flask_migrate import downgrade, upgrade
from sqlalchemy import MetaData, Table, inspect, text

from app.extensions import db
from app.models import (AplicacaoInsumo, ColheitaRegistro, Cultura, CulturaGleba,
    EquipeMembro, FinanceiroLancamento, Gleba, IaInteracao, LogAuditoria,
    ProdutoBase, UploadArquivo, UsuarioPropriedade)

MIGRATIONS = str(Path(__file__).resolve().parents[1]/'migrations')
ANTERIOR = 'd3b94f5a0c21'
NOVA = 'e4ca60b1d732'
POLIGONO = json.dumps({'type':'Polygon','coordinates':[[[0,0],[4,0],[4,4],[0,4],[0,0]]]})
TABELAS_HISTORICAS = ('usuario','usuario_propriedade','gleba','cultura','cultura_gleba',
    'produto_base','aplicacao_insumo','colheita_registro','financeiro_lancamento',
    'upload_arquivo','equipe_membro','ia_interacao','log_auditoria')
COLUNAS_PROPRIEDADE = 'id,usuario_id,nome,municipio,uf,area_total_ha,criado_em,atualizado_em'
# Comparar as colunas históricas, mesmo quando o head acrescenta dados opcionais.
# Os novos campos e o schema completo são verificados na suíte e4→f6.
COLUNAS_HISTORICAS = {
    'usuario': 'id,nome,email,senha_hash,perfil,ativo,auth_version,criado_em,atualizado_em',
    'aplicacao_insumo': 'id,cultura_gleba_id,produto_base_id,data_aplicacao,dose,unidade,responsavel,observacao,criado_em',
    'colheita_registro': 'id,cultura_gleba_id,data_colheita,quantidade,unidade,qualidade,observacao,criado_em',
}


def preparar_legado():
    upgrade(directory=MIGRATIONS,revision=ANTERIOR)
    with db.engine.begin() as c:
        # A fixture usa o schema histórico refletido: defaults novos do modelo
        # atual não podem inserir colunas que ainda não existiam em d3.
        usuario_historico = Table('usuario', MetaData(), autoload_with=c)
        c.execute(usuario_historico.insert(),[
            dict(id=1,nome='Responsável',email='responsavel@legacy.invalid',senha_hash='hash-preservado',perfil='admin',ativo=True,auth_version=1,criado_em='old'),
            dict(id=2,nome='Inativo',email='inativo@legacy.invalid',senha_hash='hash-inativo',perfil='tecnico',ativo=False,auth_version=1,criado_em='old'),
            dict(id=3,nome='Terceiro',email='terceiro@legacy.invalid',senha_hash='hash-terceiro',perfil='trabalhador',ativo=True,auth_version=1,criado_em='old')])
        c.execute(text("INSERT INTO propriedade (id,usuario_id,nome,municipio,uf,area_total_ha,criado_em) VALUES "
            "(10,1,'Minha propriedade','Campinas','SP',100.25,'old'),"
            "(20,2,'Outra legítima',NULL,NULL,200.5,'old')"))
        c.execute(UsuarioPropriedade.__table__.insert(),[
            dict(id=40,usuario_id=1,propriedade_id=10,ativo=True),
            dict(id=41,usuario_id=3,propriedade_id=10,ativo=True),
            dict(id=42,usuario_id=2,propriedade_id=20,ativo=False)])
        c.execute(Gleba.__table__.insert(),[
            dict(id=50,propriedade_id=10,nome='Área com geometria válida',area_ha=5.25,poligono_geojson=POLIGONO),
            dict(id=51,propriedade_id=10,nome='Área com geometria antiga inválida',area_ha=7.5,poligono_geojson='{invalido'),
            dict(id=52,propriedade_id=20,nome='Área sem geometria',area_ha=None,poligono_geojson=None)])
        c.execute(Cultura.__table__.insert(),dict(id=60,propriedade_id=10,nome='Cultura histórica'))
        c.execute(CulturaGleba.__table__.insert(),dict(id=70,cultura_id=60,gleba_id=50))
        c.execute(ProdutoBase.__table__.insert(),dict(id=80,nome='Produto histórico',slug='historia-map',classe='fertilizante'))
        c.execute(AplicacaoInsumo.__table__.insert(),dict(id=90,cultura_gleba_id=70,
            produto_base_id=80,data_aplicacao='2026-11-08',dose=2.5,unidade='kg'))
        c.execute(ColheitaRegistro.__table__.insert(),dict(id=100,cultura_gleba_id=70,
            data_colheita='2026-11-08',quantidade=10,unidade='kg'))
        c.execute(FinanceiroLancamento.__table__.insert(),dict(id=110,propriedade_id=10,
            tipo='receita',valor=15,data='2026-11-08',descricao='Histórico financeiro'))
        c.execute(UploadArquivo.__table__.insert(),dict(id=120,propriedade_id=10,
            nome_original='legado.txt',caminho='propriedade_10/legado.txt'))
        c.execute(EquipeMembro.__table__.insert(),dict(id=130,propriedade_id=10,nome='Membro histórico'))
        c.execute(IaInteracao.__table__.insert(),dict(id=140,usuario_id=1,propriedade_id=10,
            pergunta='Pergunta histórica',resposta='Resposta original'))
        c.execute(LogAuditoria.__table__.insert(),dict(id=150,usuario_id=1,propriedade_id=10,
            acao='historico.original',entidade='gleba',entidade_id=50,descricao='Histórico original'))


def snapshot():
    with db.engine.connect() as c:
        dados = {t:c.execute(text(f'SELECT {COLUNAS_HISTORICAS.get(t,"*")} FROM {t} ORDER BY id')).all() for t in TABELAS_HISTORICAS}
        dados['propriedade'] = c.execute(text(f'SELECT {COLUNAS_PROPRIEDADE} FROM propriedade ORDER BY id')).all()
        return dados


def test_upgrade_adiciona_contorno_opcional_sem_copiar_gleba_ou_modificar_historico(app):
    with app.app_context():
        preparar_legado()
        antes = snapshot()
        upgrade(directory=MIGRATIONS)
        assert snapshot() == antes
        coluna = next(c for c in inspect(db.engine).get_columns('propriedade') if c['name'] == 'poligono_geojson')
        assert coluna['nullable'] and coluna['default'] is None
        with db.engine.connect() as c:
            assert c.execute(text('SELECT id,poligono_geojson FROM propriedade ORDER BY id')).all() == [(10,None),(20,None)]
            assert c.execute(text('PRAGMA foreign_key_check')).all() == []
            config = app.extensions['migrate'].migrate.get_config(MIGRATIONS)
            assert c.execute(text('SELECT version_num FROM alembic_version')).scalar() == ScriptDirectory.from_config(config).get_current_head()
            assert 'AUTOINCREMENT' in c.execute(text("SELECT sql FROM sqlite_master WHERE name='propriedade'")).scalar()
            assert compare_metadata(MigrationContext.configure(c),db.metadata) == []
        upgrade(directory=MIGRATIONS)
        assert snapshot() == antes


def test_downgrade_sem_contornos_preserva_relacoes_e_pode_reaplicar(app):
    with app.app_context():
        preparar_legado(); antes = snapshot()
        upgrade(directory=MIGRATIONS)
        downgrade(directory=MIGRATIONS,revision=ANTERIOR)
        assert snapshot() == antes
        assert 'poligono_geojson' not in {c['name'] for c in inspect(db.engine).get_columns('propriedade')}
        upgrade(directory=MIGRATIONS)
        assert snapshot() == antes
        with db.engine.connect() as c:
            assert c.execute(text('SELECT COUNT(*) FROM propriedade WHERE poligono_geojson IS NOT NULL')).scalar() == 0


@pytest.mark.parametrize('conteudo',[POLIGONO,'','{invalido'])
def test_downgrade_com_conteudo_nao_null_aborta_antes_de_ddl_ou_exclusao(app,conteudo):
    with app.app_context():
        preparar_legado(); antes = snapshot()
        # Este teste exerce o guard da própria e4, antes de migrations posteriores.
        upgrade(directory=MIGRATIONS, revision=NOVA)
        with db.engine.begin() as c:
            c.execute(text('UPDATE propriedade SET poligono_geojson=:valor WHERE id=10'),{'valor':conteudo})
        config = app.extensions['migrate'].migrate.get_config(MIGRATIONS)
        with pytest.raises(RuntimeError,match='Downgrade bloqueado'):
            command.downgrade(config,ANTERIOR)
        assert snapshot() == antes
        with db.engine.connect() as c:
            assert c.execute(text('SELECT poligono_geojson FROM propriedade WHERE id=10')).scalar() == conteudo
            assert c.execute(text('SELECT version_num FROM alembic_version')).scalar() == NOVA
