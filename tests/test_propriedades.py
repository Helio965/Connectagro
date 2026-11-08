"""Seleção, gestão e isolamento: banco e arquivos exclusivamente descartáveis."""
import re
from io import BytesIO
from pathlib import Path

import pytest
from sqlalchemy import event
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models import (Usuario, Propriedade, UsuarioPropriedade, Gleba, Cultura,
    CulturaGleba, FinanceiroLancamento, ProdutoBase, AplicacaoInsumo,
    ColheitaRegistro, UploadArquivo, IaInteracao, LogAuditoria)
from app.utils.auth import gerar_hash_senha


@pytest.fixture
def tenants(app, tmp_path):
    app.config['UPLOAD_FOLDER'] = str(tmp_path)
    ids = {}
    with app.app_context():
        db.create_all()
        for role in ['admin', 'tecnico', 'trabalhador', 'outro']:
            u = Usuario(nome=role, email=role+'@tenants.invalid', ativo=True,
                        perfil='admin' if role == 'outro' else role,
                        senha_hash=gerar_hash_senha('tenant-password'))
            db.session.add(u); db.session.flush(); ids[role] = u.id
        product = ProdutoBase(nome='Catálogo global', slug='global', classe='defensivo',
                              categoria='herbicida', status_sistema='pre_cadastrado')
        db.session.add(product); db.session.flush(); ids['product'] = product.id
        for name in ['A', 'B', 'C']:
            owner = ids['outro'] if name == 'C' else ids['admin']
            p = Propriedade(usuario_id=owner, nome='Fazenda '+name)
            db.session.add(p); db.session.flush(); ids[name] = p.id
            members = [owner] if name == 'C' else [owner, ids['trabalhador']]
            for uid in members:
                db.session.add(UsuarioPropriedade(usuario_id=uid, propriedade_id=p.id, ativo=True))
            g = Gleba(propriedade_id=p.id, nome=name+'-secret-gleba', area_ha=10)
            c = Cultura(propriedade_id=p.id, nome=name+'-secret-cultura')
            db.session.add_all([g,c]); db.session.flush()
            cg = CulturaGleba(cultura_id=c.id, gleba_id=g.id)
            db.session.add(cg); db.session.flush()
            a = AplicacaoInsumo(cultura_gleba_id=cg.id, produto_base_id=product.id,
                data_aplicacao='2026-11-07', responsavel=name+'-secret-responsavel')
            h = ColheitaRegistro(cultura_gleba_id=cg.id, data_colheita='2026-11-07',
                                quantidade=10, unidade=name+'-secret-unidade')
            folder = tmp_path / f'propriedade_{p.id}'
            folder.mkdir(); (folder/'fixture.txt').write_bytes(name.encode())
            up = UploadArquivo(propriedade_id=p.id, nome_original=name+'-secret-file.txt',
                               caminho=f'propriedade_{p.id}/fixture.txt', tamanho=1)
            db.session.add_all([a,h,up,FinanceiroLancamento(propriedade_id=p.id,
                tipo='receita', valor=11 if name=='A' else 22, data='2026-11-07',
                descricao=name+'-secret-financeiro'),
                IaInteracao(usuario_id=ids['admin'], propriedade_id=p.id,
                    pergunta=name+'-secret-pergunta', resposta=name+'-secret-resposta',tipo='simulada'),
                LogAuditoria(usuario_id=ids['admin'], propriedade_id=p.id,
                    acao='fixture',resultado='sucesso',descricao=name+'-secret-log')])
            db.session.flush()
            ids[name+'_gleba'], ids[name+'_cultura'], ids[name+'_cg'] = g.id,c.id,cg.id
            ids[name+'_app'], ids[name+'_harvest'], ids[name+'_upload'] = a.id,h.id,up.id
        db.session.commit()
    app.tenant_ids = ids
    return app


def enter(app, role='admin', selected='A'):
    client = app.test_client()
    assert client.post('/auth/login', data={'email':role+'@tenants.invalid',
        'senha':'tenant-password'}).status_code == 302
    if selected:
        assert client.post('/propriedades/selecionar',data={
            'propriedade_id':str(app.tenant_ids[selected])}).status_code == 302
    return client


def test_uma_propriedade_e_selecao_automatica(tenants):
    client = enter(tenants, 'outro', None)
    assert client.get('/').status_code == 200
    with client.session_transaction() as sess:
        assert sess['propriedade_ativa_id'] == tenants.tenant_ids['C']


def test_varias_exigem_selecao_e_troca_nao_muda_dados(tenants):
    client = enter(tenants, selected=None)
    assert client.get('/').headers['Location'].endswith('/propriedades/selecionar')
    for name, other in [('A','B'), ('B','A')]:
        assert client.post('/propriedades/selecionar', data={'propriedade_id':str(tenants.tenant_ids[name])}).status_code==302
        body = client.get('/financeiro/').get_data(as_text=True)
        assert name+'-secret-financeiro' in body and other+'-secret-financeiro' not in body
    with tenants.app_context():
        assert FinanceiroLancamento.query.filter_by(propriedade_id=tenants.tenant_ids['A']).one().valor==11


@pytest.mark.parametrize('route', ['/', '/propriedades/', '/propriedades/selecionar', '/glebas/', '/usuarios/'])
def test_sem_propriedade_nao_cria_registros_ao_ler(tenants, route):
    with tenants.app_context(): before=(Propriedade.query.count(),UsuarioPropriedade.query.count())
    client=enter(tenants,'tecnico',None)
    assert client.get(route).status_code in (200,302)
    with tenants.app_context(): assert before==(Propriedade.query.count(),UsuarioPropriedade.query.count())


@pytest.mark.parametrize('value', [0,-1,True,None,'bad',10**1000])
def test_selecao_malformada_nao_altera_contexto(tenants,value):
    client=enter(tenants)
    assert client.post('/propriedades/selecionar',json={'propriedade_id':value}).status_code==404
    with client.session_transaction() as sess: assert sess['propriedade_ativa_id']==tenants.tenant_ids['A']


@pytest.mark.parametrize('payload', [[1],True,1,'x',None])
def test_json_nao_objeto_retorna_400(tenants,payload):
    import json
    client=enter(tenants)
    assert client.post('/propriedades/selecionar',data=json.dumps(payload),content_type='application/json').status_code==400


def test_admin_nao_tem_acesso_global_nem_id_inexistente(tenants):
    client=enter(tenants)
    for pid in [tenants.tenant_ids['C'],999999]:
        assert client.post('/propriedades/selecionar',data={'propriedade_id':str(pid)}).status_code==404
        r=client.get(f'/propriedades/{pid}')
        assert r.status_code==404 and b'Fazenda C' not in r.data


def test_revogacao_nao_reativa_owner_nem_executa_post_no_outro_contexto(tenants):
    client=enter(tenants)
    with tenants.app_context():
        v=UsuarioPropriedade.query.filter_by(usuario_id=tenants.tenant_ids['admin'],propriedade_id=tenants.tenant_ids['A']).one()
        v.ativo=False;db.session.commit()
        before=FinanceiroLancamento.query.count()
    assert client.post('/financeiro/novo',data={'tipo':'receita','valor':'5','data':'2026-11-07'}).status_code==409
    with tenants.app_context():
        assert FinanceiroLancamento.query.count()==before
        assert not UsuarioPropriedade.query.filter_by(usuario_id=tenants.tenant_ids['admin'],propriedade_id=tenants.tenant_ids['A']).one().ativo
    with client.session_transaction() as sess: assert 'propriedade_ativa_id' not in sess


def test_usuario_inativo_e_propriedade_removida_invalidam_contexto(tenants):
    client=enter(tenants)
    with tenants.app_context():
        db.session.execute(db.delete(Propriedade).where(Propriedade.id==tenants.tenant_ids['A']))
        db.session.commit()
    assert client.get('/').status_code==302
    with client.session_transaction() as sess: assert 'propriedade_ativa_id' not in sess
    with tenants.app_context():
        u=db.session.get(Usuario,tenants.tenant_ids['admin']);u.ativo=False;db.session.commit()
    assert '/auth/login' in client.get('/propriedades/').headers['Location']


@pytest.mark.parametrize('route,token', [('/culturas/','cultura'),('/glebas/','gleba'),
    ('/financeiro/','financeiro'),('/colheita/','unidade'),('/aplicacoes/','responsavel'),
    ('/upload/','file'),('/relatorios/financeiro','financeiro'),('/mapa/dados','gleba'),
    ('/auditoria/','log'),('/ia/','resposta')])
def test_dados_operacionais_isolados_apos_troca(tenants,route,token):
    client=enter(tenants)
    for name,other in [('A','B'),('B','A')]:
        client.post('/propriedades/selecionar',data={'propriedade_id':str(tenants.tenant_ids[name])})
        r=client.get(route);assert r.status_code==200
        body=r.get_data(as_text=True)
        assert name+'-secret-'+token in body
        assert other+'-secret-'+token not in body


def test_objetos_de_outro_contexto_negados_mesmo_com_dois_vinculos(tenants):
    client=enter(tenants); ids=tenants.tenant_ids
    for route in [f'/glebas/{ids["B_gleba"]}/editar', f'/culturas/{ids["B_cultura"]}/editar',
        f'/aplicacoes/{ids["B_app"]}/editar',f'/colheita/{ids["B_harvest"]}/editar',
        f'/upload/{ids["B_upload"]}/download']:
        assert client.get(route).status_code==404,route
    assert client.post('/colheita/nova',data={'cultura_gleba_id':str(ids['B_cg']),'data_colheita':'2026-11-07'}).status_code==400
    assert client.post(f'/mapa/glebas/{ids["B_gleba"]}/poligono/limpar').status_code==404
    r=client.get('/relatorios/financeiro/exportar.csv?propriedade_id='+str(ids['B']))
    assert r.status_code==200 and b'B-secret-financeiro' not in r.data


@pytest.mark.parametrize('role', ['admin','tecnico'])
def test_cadastro_explicito_responsavel_e_vinculo_sem_alterar_anterior(tenants,role):
    client=enter(tenants,role,None)
    r=client.post('/propriedades/nova',data={'nome':'Nova unidade','usuario_id':str(tenants.tenant_ids['outro']),'area_total_ha':'10,5'})
    assert r.status_code==302
    with tenants.app_context():
        p=Propriedade.query.filter_by(nome='Nova unidade').one()
        assert p.usuario_id==tenants.tenant_ids[role] and p.area_total_ha==10.5
        assert UsuarioPropriedade.query.filter_by(usuario_id=p.usuario_id,propriedade_id=p.id,ativo=True).count()==1
        assert FinanceiroLancamento.query.filter_by(propriedade_id=tenants.tenant_ids['A']).one().valor==11
        assert LogAuditoria.query.filter_by(acao='propriedades.create',propriedade_id=p.id).count()==1


def test_trabalhador_nao_cria_edita_nem_perde_perfil_ao_trocar(tenants):
    c=enter(tenants,'trabalhador')
    assert c.get('/propriedades/nova').status_code==403
    assert c.post(f'/propriedades/{tenants.tenant_ids["A"]}/editar',data={'nome':'bad'}).status_code==403
    c.post('/propriedades/selecionar',data={'propriedade_id':str(tenants.tenant_ids['B'])})
    assert c.get('/financeiro/').status_code==403


def test_remocao_bloqueada_e_vinculo_unico(tenants):
    c=enter(tenants);pid=tenants.tenant_ids['A']
    assert c.post(f'/propriedades/{pid}/remover').status_code==409
    with tenants.app_context():
        assert db.session.get(Propriedade,pid) is not None
        db.session.add(UsuarioPropriedade(usuario_id=tenants.tenant_ids['admin'],propriedade_id=pid,ativo=False))
        with pytest.raises(IntegrityError):db.session.commit()
        db.session.rollback()


def test_selector_csrf_e_interface_uma_varias_nenhuma(tenants):
    c=enter(tenants)
    tenants.config['WTF_CSRF_ENABLED']=True
    assert c.post('/propriedades/selecionar',data={'propriedade_id':str(tenants.tenant_ids['B'])}).status_code==400
    html=c.get('/propriedades/selecionar').get_data(as_text=True)
    assert 'Fazenda A' in html and 'Fazenda B' in html and 'Fazenda C' not in html
    token=re.search(r'name="csrf_token" value="([^"]+)"',html).group(1)
    assert c.post('/propriedades/selecionar',data={'csrf_token':token,'propriedade_id':str(tenants.tenant_ids['B'])}).status_code==302
    tenants.config['WTF_CSRF_ENABLED']=False
    for role,marker in [('outro','Fazenda C'),('tecnico','Nenhuma propriedade autorizada')]:
        html=enter(tenants,role,None).get('/propriedades/').get_data(as_text=True)
        assert marker in html


def test_conta_compartilhada_inativacao_local_preserva_outro_ambiente(tenants):
    admin=enter(tenants);a=enter(tenants,'trabalhador');b=enter(tenants,'trabalhador','B')
    uid=tenants.tenant_ids['trabalhador']
    assert admin.post(f'/usuarios/{uid}/inativar').status_code==302
    with tenants.app_context():
        assert db.session.get(Usuario,uid).ativo
        assert not UsuarioPropriedade.query.filter_by(usuario_id=uid,propriedade_id=tenants.tenant_ids['A']).one().ativo
        assert UsuarioPropriedade.query.filter_by(usuario_id=uid,propriedade_id=tenants.tenant_ids['B']).one().ativo
    assert a.get('/glebas/').status_code==302
    assert b.get('/glebas/').status_code==200


def test_formulario_antigo_nao_grava_apos_troca_de_propriedade(tenants):
    c = enter(tenants)
    tenants.config['WTF_CSRF_ENABLED'] = True
    def token():
        html = c.get('/financeiro/novo').get_data(as_text=True)
        return re.search(r'name="csrf_token" value="([^"]+)"', html).group(1)
    anterior = token()
    assert c.post('/propriedades/selecionar', data={
        'csrf_token': anterior, 'propriedade_id': str(tenants.tenant_ids['B'])}).status_code == 302
    with tenants.app_context():
        before = FinanceiroLancamento.query.count()
    dados = dict(csrf_token=anterior, tipo='receita', valor='5', data='2026-11-07',
                 descricao='formulario-da-A')
    assert c.post('/financeiro/novo', data=dados).status_code == 400
    with tenants.app_context():
        assert FinanceiroLancamento.query.count() == before
    dados.update(csrf_token=token(), descricao='formulario-da-B')
    assert c.post('/financeiro/novo', data=dados).status_code == 302
    with tenants.app_context():
        assert FinanceiroLancamento.query.filter_by(descricao='formulario-da-B').one().propriedade_id == tenants.tenant_ids['B']


@pytest.mark.parametrize('campo,valor', [('nome','Alterado'),('email','novo@tenants.invalid'),
    ('perfil','tecnico'),('senha','another-password')])
def test_conta_compartilhada_fora_do_escopo_bloqueia_alteracao_global(tenants,campo,valor):
    uid = tenants.tenant_ids['trabalhador']
    with tenants.app_context():
        db.session.add(UsuarioPropriedade(usuario_id=uid, propriedade_id=tenants.tenant_ids['C'], ativo=True))
        db.session.commit()
        u = db.session.get(Usuario, uid)
        before = (u.nome,u.email,u.perfil,u.senha_hash,u.auth_version)
    admin = enter(tenants)
    dados = dict(nome='trabalhador',email='trabalhador@tenants.invalid',perfil='trabalhador',ativo='1')
    dados[campo] = valor
    if campo == 'senha': dados['confirmar_senha'] = valor
    assert admin.post(f'/usuarios/{uid}/editar',data=dados).status_code == 403
    assert admin.post(f'/usuarios/{uid}/reenviar-convite').status_code == 403
    with tenants.app_context():
        u = db.session.get(Usuario, uid)
        assert (u.nome,u.email,u.perfil,u.senha_hash,u.auth_version) == before
        assert not u.tokens_reset


def test_editar_conta_compartilhada_fora_do_escopo_inativa_so_vinculo(tenants):
    uid = tenants.tenant_ids['trabalhador']
    with tenants.app_context():
        db.session.add(UsuarioPropriedade(usuario_id=uid, propriedade_id=tenants.tenant_ids['C'], ativo=True))
        db.session.commit()
    admin = enter(tenants)
    assert b'readonly' in admin.get(f'/usuarios/{uid}/editar').data
    assert admin.post(f'/usuarios/{uid}/editar', data=dict(nome='trabalhador',
        email='trabalhador@tenants.invalid',perfil='trabalhador')).status_code == 302
    with tenants.app_context():
        assert db.session.get(Usuario,uid).ativo
        for name, ativo in [('A',False),('B',True),('C',True)]:
            assert UsuarioPropriedade.query.filter_by(usuario_id=uid,
                propriedade_id=tenants.tenant_ids[name]).one().ativo == ativo


def test_edicao_propriedade_preserva_responsavel_e_contexto(tenants):
    admin = enter(tenants)
    pid = tenants.tenant_ids['B']
    assert admin.post(f'/propriedades/{pid}/editar',data=dict(nome='Nova identificação',
        municipio='Campinas',uf='sp',area_total_ha='20,5',usuario_id=str(tenants.tenant_ids['outro']))).status_code == 302
    with tenants.app_context():
        p = db.session.get(Propriedade,pid)
        assert (p.nome,p.municipio,p.uf,p.area_total_ha,p.usuario_id) == (
            'Nova identificação','Campinas','SP',20.5,tenants.tenant_ids['admin'])
    with admin.session_transaction() as sess:
        assert sess['propriedade_ativa_id'] == tenants.tenant_ids['A']


@pytest.mark.parametrize('acao', ['create','edit'])
def test_falha_auditoria_reverte_propriedade_e_vinculo(tenants,acao):
    admin = enter(tenants)
    with tenants.app_context():
        before = (Propriedade.query.count(),UsuarioPropriedade.query.count(),LogAuditoria.query.count())
    def falhar(mapper, connection, log):
        if log.acao == 'propriedades.'+acao:
            raise IntegrityError('Falha sintética no log', {}, Exception('Falha sintética'))
    event.listen(LogAuditoria, 'before_insert', falhar)
    try:
        url = '/propriedades/nova' if acao == 'create' else f'/propriedades/{tenants.tenant_ids["A"]}/editar'
        assert admin.post(url,data={'nome':'Nao deve persistir'}).status_code == 409
    finally:
        event.remove(LogAuditoria, 'before_insert', falhar)
    with tenants.app_context():
        assert (Propriedade.query.count(),UsuarioPropriedade.query.count(),LogAuditoria.query.count()) == before
        assert not Propriedade.query.filter_by(nome='Nao deve persistir').first()
        assert db.session.get(Propriedade,tenants.tenant_ids['A']).nome == 'Fazenda A'


def test_dado_legacy_cruzado_nao_vaza_nem_e_apagado(tenants):
    ids=tenants.tenant_ids
    with tenants.app_context():
        cg=CulturaGleba(cultura_id=ids['A_cultura'],gleba_id=ids['B_gleba'])
        db.session.add(cg);db.session.flush()
        h=ColheitaRegistro(cultura_gleba_id=cg.id,data_colheita='2026-11-07',unidade='foreign-secret')
        db.session.add(h);db.session.commit();hid=h.id;cgid=cg.id
    c=enter(tenants)
    assert b'foreign-secret' not in c.get('/colheita/').data
    assert c.get(f'/colheita/{hid}/editar').status_code==404
    assert c.post(f'/culturas/{ids["A_cultura"]}/editar',data={'nome':'Nao mudar'}).status_code==409
    assert c.post(f'/culturas/{ids["A_cultura"]}/remover').status_code==409
    with tenants.app_context(): assert db.session.get(CulturaGleba,cgid) is not None


def test_upload_com_caminho_de_outra_propriedade_nao_baixa_ou_apaga(tenants):
    ids=tenants.tenant_ids
    with tenants.app_context():
        upload=db.session.get(UploadArquivo,ids['A_upload'])
        upload.caminho=f'propriedade_{ids["B"]}/fixture.txt';db.session.commit()
    c=enter(tenants)
    assert c.get(f'/upload/{ids["A_upload"]}/download').status_code==404
    assert c.post(f'/upload/{ids["A_upload"]}/remover').status_code==404
    assert (Path(tenants.config['UPLOAD_FOLDER'])/f'propriedade_{ids["B"]}'/'fixture.txt').read_bytes()==b'B'


@pytest.mark.parametrize('modo', ['traversal', 'symlink_arquivo', 'symlink_pasta'])
def test_upload_escape_fisico_entre_propriedades_bloqueado(tenants,modo):
    ids = tenants.tenant_ids
    base = Path(tenants.config['UPLOAD_FOLDER'])
    pasta_a, pasta_b = base/f'propriedade_{ids["A"]}', base/f'propriedade_{ids["B"]}'
    caminho = f'propriedade_{ids["A"]}/fixture.txt'
    if modo == 'traversal':
        caminho = f'propriedade_{ids["A"]}/../propriedade_{ids["B"]}/fixture.txt'
    elif modo == 'symlink_arquivo':
        (pasta_a/'link.txt').symlink_to(pasta_b/'fixture.txt')
        caminho = f'propriedade_{ids["A"]}/link.txt'
    else:
        pasta_a.rename(base/'original_A')
        pasta_a.symlink_to(pasta_b, target_is_directory=True)
    with tenants.app_context():
        db.session.get(UploadArquivo,ids['A_upload']).caminho = caminho
        db.session.commit()
    c = enter(tenants)
    assert c.get(f'/upload/{ids["A_upload"]}/download').status_code == 404
    assert c.post(f'/upload/{ids["A_upload"]}/remover').status_code == 404
    if modo == 'symlink_pasta':
        assert c.post('/upload/novo', data={'arquivo':(BytesIO(b'nao-gravar'),'novo.txt')},
            content_type='multipart/form-data').status_code == 404
    assert list(pasta_b.iterdir()) == [pasta_b/'fixture.txt']
    assert (pasta_b/'fixture.txt').read_bytes() == b'B'
    with tenants.app_context():
        assert UploadArquivo.query.count() == 3
