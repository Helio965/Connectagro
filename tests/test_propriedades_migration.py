"""Migration real de vínculos: conserva registros e aborta conflitos."""
from pathlib import Path

import pytest
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from flask_migrate import upgrade
from sqlalchemy import inspect, text

from app.extensions import db
from app.models import (Propriedade, UsuarioPropriedade, Gleba, Cultura,
    CulturaGleba, FinanceiroLancamento, UploadArquivo, LogAuditoria)

MIGRATIONS = str(Path(__file__).resolve().parents[1] / 'migrations')


def old_schema(app):
    upgrade(directory=MIGRATIONS, revision='c2a83e4f9b10')
    with db.engine.begin() as conn:
        conn.execute(text("INSERT INTO usuario (id,nome,email,senha_hash,perfil,ativo,criado_em) VALUES (1,'Owner','owner@legacy.invalid','opaque','admin',1,'old'),(2,'Inactive','inactive@legacy.invalid','opaque2','tecnico',0,'old'),(3,'Other','other@legacy.invalid','opaque3','trabalhador',1,'old')"))
        conn.execute(text("INSERT INTO propriedade (id,usuario_id,nome,criado_em) VALUES (10,1,'Minha propriedade','old'),(11,1,'Outra legítima','old'),(12,2,'Responsável inativo','old')"))


def test_reconciliacao_preserva_inativos_responsaveis_e_terceiros(app):
    with app.app_context():
        old_schema(app)
        with db.engine.begin() as c:
            c.execute(text("INSERT INTO usuario_propriedade (id,usuario_id,propriedade_id,ativo,criado_em) VALUES (40,1,10,0,'old'),(41,3,10,1,'old')"))
            c.execute(Gleba.__table__.insert(), dict(id=50,propriedade_id=10,
                nome='Área legada',area_ha=5,poligono_geojson='{"type":"Polygon","coordinates":[]}'))
            c.execute(Cultura.__table__.insert(), dict(id=50,propriedade_id=10,nome='Cultura legada'))
            c.execute(CulturaGleba.__table__.insert(), dict(id=50,cultura_id=50,gleba_id=50))
            c.execute(FinanceiroLancamento.__table__.insert(),dict(id=50,propriedade_id=10,
                tipo='receita',valor=15,data='2026-11-07',descricao='Histórico financeiro'))
            c.execute(UploadArquivo.__table__.insert(),dict(id=50,propriedade_id=10,
                nome_original='legado.txt',caminho='propriedade_10/legado.txt'))
            c.execute(LogAuditoria.__table__.insert(),dict(id=50,usuario_id=1,
                propriedade_id=10,acao='legacy',descricao='Histórico original'))
            tabelas = ('gleba','cultura','cultura_gleba','financeiro_lancamento','upload_arquivo','log_auditoria')
            historico = {t:c.execute(text(f'SELECT * FROM {t} ORDER BY id')).all() for t in tabelas}
            before=c.execute(text('SELECT id,usuario_id,nome,criado_em FROM propriedade ORDER BY id')).all()
        upgrade(directory=MIGRATIONS)
        with db.engine.connect() as c:
            assert c.execute(text('SELECT id,usuario_id,nome,criado_em FROM propriedade ORDER BY id')).all()==before
            for tabela, linhas in historico.items():
                assert c.execute(text(f'SELECT * FROM {tabela} ORDER BY id')).all() == linhas
            assert c.execute(text('PRAGMA foreign_key_check')).all() == []
            assert c.execute(text('SELECT id,usuario_id,propriedade_id,ativo,criado_em FROM usuario_propriedade WHERE id IN (40,41) ORDER BY id')).all()==[(40,1,10,0,'old'),(41,3,10,1,'old')]
            assert compare_metadata(MigrationContext.configure(c),db.metadata)==[]
            assert 'AUTOINCREMENT' in c.execute(text("SELECT sql FROM sqlite_master WHERE name='propriedade'")).scalar()
        assert UsuarioPropriedade.query.filter_by(usuario_id=1,propriedade_id=11,ativo=True).count()==1
        assert UsuarioPropriedade.query.filter_by(usuario_id=2,propriedade_id=12,ativo=False).count()==1
        assert UsuarioPropriedade.query.count()==4
        # Repetir upgrade não duplica backfill nem reativa o vínculo antigo.
        upgrade(directory=MIGRATIONS)
        assert UsuarioPropriedade.query.count()==4
        assert not db.session.get(UsuarioPropriedade,40).ativo


@pytest.mark.parametrize('statuses',[(1,1),(1,0),(0,0)])
def test_preflight_duplicatas_aborta_sem_apagar_ou_alterar_schema(app,statuses):
    with app.app_context():
        old_schema(app)
        with db.engine.begin() as c:
            for vid,status in zip((40,41),statuses):
                c.execute(text("INSERT INTO usuario_propriedade (id,usuario_id,propriedade_id,ativo,criado_em) VALUES (:id,1,10,:status,'old')"),{'id':vid,'status':status})
        # API Alembic preserva a causa; o wrapper CLI Flask-Migrate a converte em exit(1).
        config = app.extensions['migrate'].migrate.get_config(MIGRATIONS)
        with pytest.raises(RuntimeError,match='Vínculos duplicados'):
            command.upgrade(config, 'head')
        with db.engine.connect() as c:
            assert c.execute(text('SELECT id,ativo FROM usuario_propriedade ORDER BY id')).all()==list(zip((40,41),statuses))
            assert c.execute(text('SELECT version_num FROM alembic_version')).scalar()=='c2a83e4f9b10'
            assert c.execute(text('SELECT COUNT(*) FROM propriedade')).scalar()==3
        assert not inspect(db.engine).get_unique_constraints('usuario_propriedade')


def test_preflight_orfao_aborta_sem_inventar_usuario(app):
    with app.app_context():
        old_schema(app)
        with db.engine.begin() as c:
            c.execute(text("INSERT INTO propriedade (id,usuario_id,nome,criado_em) VALUES (13,999,'Órfã','old')"))
        config = app.extensions['migrate'].migrate.get_config(MIGRATIONS)
        with pytest.raises(RuntimeError,match='referências órfãs'):
            command.upgrade(config, 'head')
        with db.engine.connect() as c:
            assert c.execute(text('SELECT COUNT(*) FROM usuario')).scalar()==3
            assert c.execute(text('SELECT COUNT(*) FROM propriedade')).scalar()==4
            assert c.execute(text('SELECT COUNT(*) FROM usuario_propriedade')).scalar()==0
