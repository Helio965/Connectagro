"""Contratos HTTP territoriais, isolamento e preservação dos registros reais."""
import json
import math
import re

import pytest
from sqlalchemy import event
from sqlalchemy.exc import IntegrityError

from app import create_app
from app.config import TestingConfig
from app.extensions import db
from app.models import (AplicacaoInsumo, ColheitaRegistro, Cultura, CulturaGleba,
    Gleba, LogAuditoria, ProdutoBase, Propriedade, Usuario, UsuarioPropriedade)
from app.utils.auth import gerar_hash_senha
from tests.factories import vincular_usuario_propriedade


def poligono(x=0, y=0, lado=4):
    return {'type':'Polygon','coordinates':[[
        [x,y],[x+lado,y],[x+lado,y+lado],[x,y+lado],[x,y]]],}


@pytest.fixture
def territorio_db(app):
    ids = {}
    with app.app_context():
        db.create_all()
        for perfil in ('admin','tecnico','trabalhador','outro'):
            u = Usuario(nome=perfil, email=perfil+'@territorio.invalid',ativo=True,
                perfil='admin' if perfil == 'outro' else perfil,
                senha_hash=gerar_hash_senha('territorio-password'))
            db.session.add(u); db.session.flush(); ids[perfil] = u.id
        for nome in ('A','B','C'):
            dono = ids['outro'] if nome == 'C' else ids['admin']
            p = Propriedade(usuario_id=dono,nome='Propriedade '+nome,
                municipio='Campinas',uf='SP',area_total_ha=100.25)
            db.session.add(p); db.session.flush(); ids[nome] = p.id
            usuarios = (dono,) if nome == 'C' else tuple(ids[v] for v in ('admin','tecnico','trabalhador'))
            for uid in usuarios: vincular_usuario_propriedade(uid,p.id)
            g = Gleba(propriedade_id=p.id,nome='Área '+nome+'1',area_ha=5.25,
                poligono_geojson=json.dumps(poligono(1,1,1)))
            db.session.add(g); db.session.flush(); ids[nome+'1'] = g.id
        p = db.session.get(Propriedade,ids['A'])
        a2 = Gleba(propriedade_id=p.id,nome='Área A2',area_ha=7.5,
            poligono_geojson=json.dumps(poligono(2,2,0.5)))
        a3 = Gleba(propriedade_id=p.id,nome='Área A3 sem delimitação')
        cultura = Cultura(propriedade_id=p.id,nome='Cultura histórica')
        produto = ProdutoBase(nome='Produto histórico',slug='historico-territorio',classe='fertilizante')
        db.session.add_all([a2,a3,cultura,produto]); db.session.flush()
        ids['A2'],ids['A3'] = a2.id,a3.id
        cg = CulturaGleba(cultura_id=cultura.id,gleba_id=ids['A1'])
        db.session.add(cg);db.session.flush();ids['cg'] = cg.id
        db.session.add_all([
            AplicacaoInsumo(cultura_gleba_id=cg.id,produto_base_id=produto.id,
                data_aplicacao='2026-11-08',dose=2.5,unidade='kg'),
            ColheitaRegistro(cultura_gleba_id=cg.id,data_colheita='2026-11-08',quantidade=10,unidade='kg'),
            LogAuditoria(usuario_id=ids['admin'],propriedade_id=p.id,acao='historico.original',
                descricao='Histórico preservado')])
        db.session.commit()
    app.territorio_ids = ids
    return app


def entrar(app, perfil='admin', propriedade='A'):
    c = app.test_client()
    assert c.post('/auth/login',data={'email':perfil+'@territorio.invalid',
        'senha':'territorio-password'}).status_code == 302
    assert c.post('/propriedades/selecionar',data={
        'propriedade_id':str(app.territorio_ids[propriedade])}).status_code == 302
    return c


def url(app, entidade, *, identificador=None, limpar=False):
    nome = 'A' if entidade == 'propriedades' else 'A1'
    ident = app.territorio_ids[nome] if identificador is None else identificador
    return f'/mapa/{entidade}/{ident}/poligono'+('/limpar' if limpar else '')


def geometria(app, entidade, nome=None):
    modelo = Propriedade if entidade == 'propriedades' else Gleba
    with app.app_context():
        return db.session.get(modelo,app.territorio_ids[nome or ('A' if entidade == 'propriedades' else 'A1')]).poligono_geojson


def test_mapa_sem_contorno_preserva_contrato_e_lista_areas(territorio_db):
    c = entrar(territorio_db)
    r = c.get('/mapa/dados'); assert r.status_code == 200
    dados = r.get_json()
    assert set(dados) == {'propriedade','glebas'}
    assert dados['propriedade']['poligono_geojson'] is None
    assert dados['propriedade']['poligono_estado'] == 'ausente'
    assert dados['propriedade']['area_total_ha'] == 100.25
    assert {g['nome'] for g in dados['glebas']} == {'Área A1','Área A2','Área A3 sem delimitação'}
    assert all(g['contencao']['status'] == 'sem_delimitacao' for g in dados['glebas'])
    assert 'Propriedade C' not in r.get_data(as_text=True)
    assert '@territorio.invalid' not in r.get_data(as_text=True)
    assert c.get('/mapa/').status_code == 200


@pytest.mark.parametrize('perfil',['admin','tecnico'])
@pytest.mark.parametrize('entidade',['propriedades','glebas'])
def test_admin_e_gerente_salvam_entidade_autorizada_sem_alterar_outras(territorio_db,perfil,entidade):
    c = entrar(territorio_db,perfil)
    outra = geometria(territorio_db,'glebas','A2')
    area1_antes = geometria(territorio_db,'glebas')
    r = c.post(url(territorio_db,entidade),json=poligono())
    assert r.status_code == 200 and r.get_json()['ok']
    assert json.loads(geometria(territorio_db,entidade)) == poligono()
    assert geometria(territorio_db,'glebas','A2') == outra
    if entidade == 'propriedades':
        assert geometria(territorio_db,'glebas') == area1_antes
        assert {'ok','message','propriedade','glebas'} == set(r.get_json())
        assert r.get_json()['propriedade']['poligono_estado'] == 'valido'
    else:
        assert geometria(territorio_db,'propriedades') is None
        assert {'ok','message','gleba'} == set(r.get_json())
    with territorio_db.app_context():
        p = db.session.get(Propriedade,territorio_db.territorio_ids['A'])
        g = db.session.get(Gleba,territorio_db.territorio_ids['A1'])
        assert (p.usuario_id,p.area_total_ha,g.area_ha) == (territorio_db.territorio_ids['admin'],100.25,5.25)
        cg = db.session.get(CulturaGleba,territorio_db.territorio_ids['cg'])
        assert cg.gleba_id == g.id and AplicacaoInsumo.query.one().dose == 2.5
        assert ColheitaRegistro.query.one().quantidade == 10


@pytest.mark.parametrize('entidade',['propriedades','glebas'])
def test_limpar_poligono_nao_remove_entidade_ou_historico(territorio_db,entidade):
    c = entrar(territorio_db)
    assert c.post(url(territorio_db,entidade),json=poligono()).status_code == 200
    outra = geometria(territorio_db,'glebas','A2')
    assert c.post(url(territorio_db,entidade,limpar=True)).status_code == 200
    assert geometria(territorio_db,entidade) is None
    assert geometria(territorio_db,'glebas','A2') == outra
    with territorio_db.app_context():
        assert Propriedade.query.count() == 3 and Gleba.query.count() == 5
        assert CulturaGleba.query.count() == 1
        assert AplicacaoInsumo.query.count() == 1 and ColheitaRegistro.query.count() == 1


def test_comparacao_informa_area_fora_sem_bloquear_ou_recortar(territorio_db):
    c = entrar(territorio_db)
    r = c.post(url(territorio_db,'propriedades'),json=poligono())
    assert r.status_code == 200
    assert all(g['contencao']['status'] == 'contida' for g in r.json['glebas'] if g['poligono_geojson'])
    fora = poligono(8,8,1)
    r = c.post(url(territorio_db,'glebas'),json=fora)
    assert r.status_code == 200 and r.json['gleba']['contencao']['status'] == 'fora_do_limite'
    assert json.loads(geometria(territorio_db,'glebas')) == fora
    r = c.post(url(territorio_db,'propriedades',limpar=True))
    assert all(g['contencao']['status'] == 'sem_delimitacao' for g in r.json['glebas'])
    assert json.loads(geometria(territorio_db,'glebas')) == fora


@pytest.mark.parametrize('entidade',['propriedades','glebas'])
def test_trabalhador_visualiza_mas_nao_edita_ou_limpa(territorio_db,entidade):
    c = entrar(territorio_db,'trabalhador')
    antes = geometria(territorio_db,entidade)
    assert c.get('/mapa/dados').status_code == 200
    assert c.post(url(territorio_db,entidade),json=poligono()).status_code == 403
    assert c.post(url(territorio_db,entidade,limpar=True)).status_code == 403
    assert geometria(territorio_db,entidade) == antes


@pytest.mark.parametrize('entidade',['propriedades','glebas'])
def test_rotas_geograficas_exigem_login(territorio_db,entidade):
    c = territorio_db.test_client()
    assert c.get('/mapa/dados').status_code == 302
    assert c.post(url(territorio_db,entidade),json=poligono()).status_code == 302
    assert c.post(url(territorio_db,entidade,limpar=True)).status_code == 302


@pytest.mark.parametrize('entidade',['propriedades','glebas'])
def test_ids_de_outro_contexto_e_enormes_negados_e_auditados(territorio_db,entidade):
    c = entrar(territorio_db)
    ids = territorio_db.territorio_ids
    alvos = [ids['B' if entidade == 'propriedades' else 'B1'],
        ids['C' if entidade == 'propriedades' else 'C1'],0,999999,2**63,10**1000]
    for identificador in alvos:
        for limpar in (False,True):
            r = c.post(url(territorio_db,entidade,identificador=identificador,limpar=limpar),json=poligono())
            assert r.status_code == 404
            assert b'Propriedade C' not in r.data
    acao = 'mapa.propriedade.poligono.negado' if entidade == 'propriedades' else 'mapa.poligono.negado'
    with territorio_db.app_context():
        logs = LogAuditoria.query.filter_by(acao=acao).all()
        assert len(logs) == len(alvos)*2
        assert all(l.propriedade_id == ids['A'] for l in logs)
        assert all(l.entidade_id is None for l in logs[-4:])


def test_troca_de_propriedade_atualiza_geometrias_sem_acesso_pelo_id_anterior(territorio_db):
    c = entrar(territorio_db)
    assert c.post(url(territorio_db,'propriedades'),json=poligono()).status_code == 200
    c.post('/propriedades/selecionar',data={'propriedade_id':str(territorio_db.territorio_ids['B'])})
    dados = c.get('/mapa/dados').get_json()
    assert dados['propriedade']['nome'] == 'Propriedade B'
    assert {g['nome'] for g in dados['glebas']} == {'Área B1'}
    assert dados['propriedade']['poligono_geojson'] is None
    assert c.post(url(territorio_db,'propriedades'),json=poligono(10,10)).status_code == 404
    assert json.loads(geometria(territorio_db,'propriedades')) == poligono()


def test_vinculo_revogado_invalida_post_sem_escolher_outro_ambiente(territorio_db):
    c = entrar(territorio_db)
    with territorio_db.app_context():
        vinculo = UsuarioPropriedade.query.filter_by(usuario_id=territorio_db.territorio_ids['admin'],
            propriedade_id=territorio_db.territorio_ids['A']).one()
        vinculo.ativo = False; db.session.commit()
    assert c.post(url(territorio_db,'propriedades'),json=poligono()).status_code == 409
    assert geometria(territorio_db,'propriedades') is None


@pytest.mark.parametrize('entidade',['propriedades','glebas'])
def test_json_malformado_profundo_e_grande_nao_sobrescreve_geometria(territorio_db,entidade):
    c = entrar(territorio_db)
    assert c.post(url(territorio_db,entidade),json=poligono()).status_code == 200
    antes = geometria(territorio_db,entidade)
    invalidos = [b'null', b'{"type":[]}', b'{"type":"Feature","geometry":{"type":[]}}',
        b'['*2000+b'0'+b']'*2000, b' '*102401,
        json.dumps({'type':'Polygon','coordinates':[[[0,0],[10**1000,0],[1,1],[0,0]]]}).encode(),
        b'{"type":"Polygon","coordinates":[[[0,0],[NaN,0],[1,1],[0,0]]]}',
        json.dumps({'type':'Polygon','coordinates':[[[0,0],[4,4],[0,4],[4,0],[0,0]]]}).encode()]
    for bruto in invalidos:
        r = c.post(url(territorio_db,entidade),data=bruto,content_type='application/json')
        assert r.status_code == 400 and r.get_json()['ok'] is False
        assert geometria(territorio_db,entidade) == antes
    assert c.post(url(territorio_db,entidade),data=json.dumps(poligono()),content_type='text/plain').status_code == 400


def test_get_legado_invalido_mantem_entidades_e_textos_sem_escrita(territorio_db):
    c = entrar(territorio_db)
    texto_prop = '{"type":[]}'
    texto_area = '{"type":"Polygon","coordinates":[[[0,0],[1,1],[2,2],[0,0]]]}'
    with territorio_db.app_context():
        db.session.get(Propriedade,territorio_db.territorio_ids['A']).poligono_geojson = texto_prop
        db.session.get(Gleba,territorio_db.territorio_ids['A1']).poligono_geojson = texto_area
        db.session.commit(); quantidade_logs = LogAuditoria.query.count()
    for rota in ('/mapa/dados','/mapa/'):
        assert c.get(rota).status_code == 200
    dados = c.get('/mapa/dados').json
    assert dados['propriedade']['poligono_estado'] == 'invalido'
    assert dados['propriedade']['poligono_geojson'] is None
    area = next(g for g in dados['glebas'] if g['id'] == territorio_db.territorio_ids['A1'])
    assert area['poligono_estado'] == 'invalido' and area['poligono_geojson'] is None
    assert area['contencao']['status'] == 'nao_verificavel'
    assert geometria(territorio_db,'propriedades') == texto_prop
    assert geometria(territorio_db,'glebas') == texto_area
    with territorio_db.app_context(): assert LogAuditoria.query.count() == quantidade_logs


def test_colecao_legada_valida_continua_visivel_sem_normalizar_storage(territorio_db):
    c = entrar(territorio_db)
    objeto = {'type':'FeatureCollection','features':[{'type':'Feature','properties':{},'geometry':poligono()}]}
    texto = json.dumps(objeto,indent=4)
    with territorio_db.app_context():
        db.session.get(Gleba,territorio_db.territorio_ids['A1']).poligono_geojson = texto
        db.session.commit()
    area = next(g for g in c.get('/mapa/dados').json['glebas'] if g['id'] == territorio_db.territorio_ids['A1'])
    assert area['poligono_geojson'] == objeto and area['poligono_estado'] == 'valido'
    assert geometria(territorio_db,'glebas') == texto


def test_areas_numericas_legadas_nao_finitas_nao_quebram_json_nem_sao_alteradas(territorio_db):
    c = entrar(territorio_db)
    with territorio_db.app_context():
        db.session.get(Propriedade,territorio_db.territorio_ids['A']).area_total_ha = float('inf')
        db.session.get(Gleba,territorio_db.territorio_ids['A1']).area_ha = float('inf')
        db.session.commit()
    r = c.get('/mapa/dados'); assert r.status_code == 200
    assert r.json['propriedade']['area_total_ha'] is None
    assert next(g for g in r.json['glebas'] if g['id'] == territorio_db.territorio_ids['A1'])['area_ha'] is None
    assert 'Infinity' not in r.get_data(as_text=True) and 'NaN' not in r.get_data(as_text=True)
    with territorio_db.app_context():
        assert math.isinf(db.session.get(Propriedade,territorio_db.territorio_ids['A']).area_total_ha)
        assert math.isinf(db.session.get(Gleba,territorio_db.territorio_ids['A1']).area_ha)


@pytest.mark.parametrize('valor',['NaN','inf','-inf','1e9999'])
def test_cadastro_e_edicao_de_area_rejeitam_hectares_nao_finitos(territorio_db,valor):
    c = entrar(territorio_db)
    dados = {'nome':'Área inválida','area_ha':valor}
    assert c.post('/glebas/nova',data=dados).status_code == 400
    assert c.post(f'/glebas/{territorio_db.territorio_ids["A1"]}/editar',data=dados).status_code == 400
    with territorio_db.app_context():
        assert not Gleba.query.filter_by(nome='Área inválida').first()
        assert db.session.get(Gleba,territorio_db.territorio_ids['A1']).area_ha == 5.25


@pytest.mark.parametrize('entidade',['propriedades','glebas'])
def test_escritas_geograficas_exigem_csrf(territorio_db,entidade):
    c = entrar(territorio_db)
    territorio_db.config['WTF_CSRF_ENABLED'] = True
    assert c.post(url(territorio_db,entidade),json=poligono()).status_code == 400
    assert c.post(url(territorio_db,entidade,limpar=True)).status_code == 400
    html = c.get('/mapa/').get_data(as_text=True)
    token = re.search(r'name="csrf_token" value="([^"]+)"',html).group(1)
    assert c.post(url(territorio_db,entidade),json=poligono(),headers={'X-CSRFToken':token}).status_code == 200
    assert c.post(url(territorio_db,entidade,limpar=True),headers={'X-CSRFToken':token}).status_code == 200


@pytest.mark.parametrize('entidade',['propriedades','glebas'])
def test_auditoria_distingue_entidades_sem_geojson(territorio_db,entidade):
    c = entrar(territorio_db)
    assert c.post(url(territorio_db,entidade),json=poligono()).status_code == 200
    assert c.post(url(territorio_db,entidade,limpar=True)).status_code == 200
    assert c.post(url(territorio_db,entidade),json={'type':[]}).status_code == 400
    prefixo = 'mapa.propriedade.poligono' if entidade == 'propriedades' else 'mapa.poligono'
    with territorio_db.app_context():
        logs = LogAuditoria.query.filter(LogAuditoria.acao.like(prefixo+'.%')).all()
        assert {l.acao for l in logs} == {prefixo+'.update',prefixo+'.delete',prefixo+'.falha'}
        for log in logs:
            assert log.entidade == ('propriedade' if entidade == 'propriedades' else 'gleba')
            assert log.usuario_id == territorio_db.territorio_ids['admin']
            assert log.propriedade_id == territorio_db.territorio_ids['A']
            assert 'coordinates' not in log.descricao and 'Polygon' not in log.descricao


@pytest.mark.parametrize('entidade',['propriedades','glebas'])
def test_falha_no_log_nao_desfaz_poligono_ja_confirmado(territorio_db,entidade):
    c = entrar(territorio_db)
    def falhar(mapper,connection,log):
        if log.acao.startswith('mapa.'):
            raise IntegrityError('Falha sintética de auditoria',{},Exception('Falha sintética'))
    event.listen(LogAuditoria,'before_insert',falhar)
    try:
        r = c.post(url(territorio_db,entidade),json=poligono())
        assert r.status_code == 200 and r.json['ok']
    finally:
        event.remove(LogAuditoria,'before_insert',falhar)
    assert json.loads(geometria(territorio_db,entidade)) == poligono()


def test_poligono_persiste_apos_recriar_app_e_engine(tmp_path,monkeypatch):
    from flask_migrate import upgrade
    from pathlib import Path
    uri = 'sqlite:///'+str(tmp_path/'persistencia.sqlite')
    monkeypatch.setattr(TestingConfig,'SQLALCHEMY_DATABASE_URI',uri)
    monkeypatch.setattr(TestingConfig,'SQLALCHEMY_DIRECT_URI',uri)
    app1 = create_app('testing')
    with app1.app_context():
        upgrade(directory=str(Path(__file__).resolve().parents[1]/'migrations'))
        usuario = Usuario(nome='Persistência',email='persistencia@territorio.invalid',ativo=True,
            perfil='admin',senha_hash=gerar_hash_senha('persistencia-password'))
        db.session.add(usuario);db.session.flush()
        p = Propriedade(usuario_id=usuario.id,nome='Unidade persistente',area_total_ha=19.5)
        db.session.add(p);db.session.flush();vincular_usuario_propriedade(usuario.id,p.id)
        g = Gleba(propriedade_id=p.id,nome='Área persistente',area_ha=2.25)
        db.session.add(g);db.session.commit();pid,gid = p.id,g.id
    c = app1.test_client()
    assert c.post('/auth/login',data={'email':'persistencia@territorio.invalid','senha':'persistencia-password'}).status_code == 302
    assert c.post(f'/mapa/propriedades/{pid}/poligono',json=poligono()).status_code == 200
    assert c.post(f'/mapa/glebas/{gid}/poligono',json=poligono(1,1,1)).status_code == 200
    with app1.app_context():
        db.session.remove();db.engine.dispose()
    app2 = create_app('testing')
    c = app2.test_client()
    assert c.post('/auth/login',data={'email':'persistencia@territorio.invalid','senha':'persistencia-password'}).status_code == 302
    dados = c.get('/mapa/dados').get_json()
    assert dados['propriedade']['poligono_geojson'] == poligono()
    assert dados['glebas'][0]['poligono_geojson'] == poligono(1,1,1)
    with app2.app_context():
        assert db.session.get(Propriedade,pid).area_total_ha == 19.5
        assert db.session.get(Gleba,gid).area_ha == 2.25
        db.session.remove();db.engine.dispose()
