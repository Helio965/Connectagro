"""Testes da Fase 7.5 — Mapa avançado (edição de polígonos das glebas).

Sem migration/model/tabela nova: usa `Gleba.poligono_geojson` já existente.
"""
import json
import re

import pytest

from app.extensions import db
from app.utils.auth import gerar_hash_senha

SENHA = "senha123"
TOKEN_RE = re.compile(r'data-csrf-token="([^"]+)"')
FORM_TOKEN_RE = re.compile(r'name="csrf_token" value="([^"]+)"')

POLY = {"type": "Polygon", "coordinates": [[
    [-47.21, -15.11], [-47.20, -15.11], [-47.20, -15.10], [-47.21, -15.10],
    [-47.21, -15.11],
]]}
MULTI = {"type": "MultiPolygon", "coordinates": [[[
    [-47.21, -15.11], [-47.20, -15.11], [-47.20, -15.10], [-47.21, -15.11],
]]]}
FEATURE = {"type": "Feature", "properties": {}, "geometry": POLY}
FEATURE_COLLECTION = {"type": "FeatureCollection", "features": [
    {"type": "Feature", "properties": {}, "geometry": POLY}]}
FORA_DE_FAIXA = {"type": "Polygon", "coordinates": [[
    [-200.0, -15.1], [-47.0, -15.1], [-47.0, -14.0], [-200.0, -15.1]]]}
ANEL_INVALIDO = {"type": "Polygon", "coordinates": [[[-47.2, -15.1], [-47.1, -15.1]]]}


def _criar_usuario(nome, email, perfil):
    from app.models import Usuario

    u = Usuario(nome=nome, email=email, perfil=perfil, ativo=True,
                senha_hash=gerar_hash_senha(SENHA))
    db.session.add(u)
    db.session.commit()
    return u


def _vincular(usuario, propriedade):
    from app.models import UsuarioPropriedade

    db.session.add(UsuarioPropriedade(usuario_id=usuario.id,
                                      propriedade_id=propriedade.id, ativo=True))
    db.session.commit()


def _popular(app):
    from app.models import Gleba, Propriedade

    with app.app_context():
        admin = _criar_usuario("Admin", "admin@connectagro.com", "admin")
        tecnico = _criar_usuario("Téc", "tecnico@connectagro.com", "tecnico")
        trab = _criar_usuario("Trab", "trabalhador@connectagro.com", "trabalhador")
        prop = Propriedade(usuario_id=admin.id, nome="Fazenda Mapa")
        db.session.add(prop)
        db.session.commit()
        for u in (admin, tecnico, trab):
            _vincular(u, prop)
        gleba = Gleba(propriedade_id=prop.id, nome="Gleba Mapa", area_ha=10,
                      latitude=-15.1, longitude=-47.2)
        db.session.add(gleba)
        db.session.commit()

        outro = _criar_usuario("Outro", "outro@connectagro.com", "admin")
        outra_prop = Propriedade(usuario_id=outro.id, nome="Fazenda Externa")
        db.session.add(outra_prop)
        db.session.commit()
        _vincular(outro, outra_prop)
        gleba_externa = Gleba(propriedade_id=outra_prop.id, nome="Externa",
                              latitude=-10.0, longitude=-45.0)
        db.session.add(gleba_externa)
        db.session.commit()
        return {"prop_id": prop.id, "gleba_id": gleba.id,
                "gleba_externa_id": gleba_externa.id}


@pytest.fixture
def app_mapa(app):
    with app.app_context():
        db.create_all()
    app.mapa_ids = _popular(app)
    return app


def _login(client, email="admin@connectagro.com"):
    assert client.post("/auth/login", data={"email": email, "senha": SENHA}).status_code == 302


def _login_csrf(client, email="admin@connectagro.com"):
    """Login quando CSRF está ativo: extrai o token do formulário de login."""
    html = client.get("/auth/login").data.decode("utf-8")
    token = FORM_TOKEN_RE.search(html).group(1)
    resp = client.post("/auth/login",
                       data={"email": email, "senha": SENHA, "csrf_token": token})
    assert resp.status_code == 302


def _salvar_url(app):
    return f"/mapa/glebas/{app.mapa_ids['gleba_id']}/poligono"


def _gleba(app, gleba_id=None):
    from app.models import Gleba

    with app.app_context():
        return db.session.get(Gleba, gleba_id or app.mapa_ids["gleba_id"])


def _acoes(app):
    from app.models import LogAuditoria

    with app.app_context():
        return [l.acao for l in LogAuditoria.query.all()]


# --- Permissões ------------------------------------------------------------

def test_mapa_edit_na_matriz():
    from app.utils.permissions import PERMISSOES_POR_PERFIL

    assert "mapa.edit" in PERMISSOES_POR_PERFIL["admin"]
    assert "mapa.edit" in PERMISSOES_POR_PERFIL["tecnico"]
    assert "mapa.edit" not in PERMISSOES_POR_PERFIL["trabalhador"]


# --- GET continua funcionando ----------------------------------------------

def test_mapa_get_exige_login(app_mapa):
    resp = app_mapa.test_client().get("/mapa/")
    assert resp.status_code == 302


@pytest.mark.parametrize("email", ["admin@connectagro.com", "tecnico@connectagro.com",
                                   "trabalhador@connectagro.com"])
def test_mapa_get_funciona_para_todos_os_perfis(app_mapa, email):
    client = app_mapa.test_client()
    _login(client, email)
    assert client.get("/mapa/").status_code == 200
    assert client.get("/mapa/dados").status_code == 200


# --- Salvar polígono -------------------------------------------------------

def test_admin_salva_poligono(app_mapa):
    client = app_mapa.test_client()
    _login(client)
    resp = client.post(_salvar_url(app_mapa), json=POLY)
    assert resp.status_code == 200
    assert resp.get_json()["ok"] is True
    assert _gleba(app_mapa).poligono_geojson


def test_tecnico_salva_poligono(app_mapa):
    client = app_mapa.test_client()
    _login(client, "tecnico@connectagro.com")
    assert client.post(_salvar_url(app_mapa), json=POLY).status_code == 200


def test_trabalhador_nao_salva_poligono(app_mapa):
    client = app_mapa.test_client()
    _login(client, "trabalhador@connectagro.com")
    assert client.post(_salvar_url(app_mapa), json=POLY).status_code == 403


def test_salvar_sem_login_redireciona(app_mapa):
    resp = app_mapa.test_client().post(_salvar_url(app_mapa), json=POLY)
    assert resp.status_code == 302
    assert "/auth/login" in resp.headers["Location"]


def test_gleba_de_outra_propriedade_404(app_mapa):
    client = app_mapa.test_client()
    _login(client)
    url = f"/mapa/glebas/{app_mapa.mapa_ids['gleba_externa_id']}/poligono"
    assert client.post(url, json=POLY).status_code == 404


def test_geojson_invalido_400(app_mapa):
    client = app_mapa.test_client()
    _login(client)
    assert client.post(_salvar_url(app_mapa), json={"type": "Point"}).status_code == 400


def test_coordenadas_fora_de_faixa_400(app_mapa):
    client = app_mapa.test_client()
    _login(client)
    assert client.post(_salvar_url(app_mapa), json=FORA_DE_FAIXA).status_code == 400


def test_anel_invalido_400(app_mapa):
    client = app_mapa.test_client()
    _login(client)
    assert client.post(_salvar_url(app_mapa), json=ANEL_INVALIDO).status_code == 400


def test_payload_grande_demais_400(app_mapa):
    client = app_mapa.test_client()
    _login(client)
    anel = [[-47.0, -15.0] for _ in range(8000)]
    grande = {"type": "Polygon", "coordinates": [anel]}
    assert client.post(_salvar_url(app_mapa), json=grande).status_code == 400


def test_multipolygon_aceito(app_mapa):
    client = app_mapa.test_client()
    _login(client)
    assert client.post(_salvar_url(app_mapa), json=MULTI).status_code == 200


def test_feature_aceito(app_mapa):
    client = app_mapa.test_client()
    _login(client)
    assert client.post(_salvar_url(app_mapa), json=FEATURE).status_code == 200


def test_feature_collection_recusado(app_mapa):
    client = app_mapa.test_client()
    _login(client)
    assert client.post(_salvar_url(app_mapa), json=FEATURE_COLLECTION).status_code == 400


def test_poligono_persistido_e_substituido(app_mapa):
    client = app_mapa.test_client()
    _login(client)
    client.post(_salvar_url(app_mapa), json=POLY)
    primeiro = _gleba(app_mapa).poligono_geojson
    assert primeiro
    client.post(_salvar_url(app_mapa), json=MULTI)
    segundo = _gleba(app_mapa).poligono_geojson
    assert segundo
    assert json.loads(segundo)["type"] == "MultiPolygon"


def test_atualizado_em_preenchido(app_mapa):
    client = app_mapa.test_client()
    _login(client)
    client.post(_salvar_url(app_mapa), json=POLY)
    assert _gleba(app_mapa).atualizado_em is not None


# --- Limpar polígono -------------------------------------------------------

def _limpar_url(app):
    return f"/mapa/glebas/{app.mapa_ids['gleba_id']}/poligono/limpar"


def test_admin_limpa_poligono(app_mapa):
    client = app_mapa.test_client()
    _login(client)
    client.post(_salvar_url(app_mapa), json=POLY)
    resp = client.post(_limpar_url(app_mapa))
    assert resp.status_code == 200
    assert _gleba(app_mapa).poligono_geojson is None


def test_tecnico_limpa_poligono(app_mapa):
    client = app_mapa.test_client()
    _login(client, "tecnico@connectagro.com")
    assert client.post(_limpar_url(app_mapa)).status_code == 200


def test_trabalhador_nao_limpa_poligono(app_mapa):
    client = app_mapa.test_client()
    _login(client, "trabalhador@connectagro.com")
    assert client.post(_limpar_url(app_mapa)).status_code == 403


def test_limpar_gleba_de_outra_propriedade_404(app_mapa):
    client = app_mapa.test_client()
    _login(client)
    url = f"/mapa/glebas/{app_mapa.mapa_ids['gleba_externa_id']}/poligono/limpar"
    assert client.post(url).status_code == 404


# --- Auditoria -------------------------------------------------------------

def test_salvar_gera_log_update(app_mapa):
    client = app_mapa.test_client()
    _login(client)
    client.post(_salvar_url(app_mapa), json=POLY)
    assert "mapa.poligono.update" in _acoes(app_mapa)


def test_limpar_gera_log_delete(app_mapa):
    client = app_mapa.test_client()
    _login(client)
    client.post(_limpar_url(app_mapa))
    assert "mapa.poligono.delete" in _acoes(app_mapa)


def test_geojson_invalido_gera_log_falha(app_mapa):
    client = app_mapa.test_client()
    _login(client)
    client.post(_salvar_url(app_mapa), json={"type": "Point"})
    assert "mapa.poligono.falha" in _acoes(app_mapa)


def test_log_nao_contem_geojson_completo(app_mapa):
    from app.models import LogAuditoria

    client = app_mapa.test_client()
    _login(client)
    client.post(_salvar_url(app_mapa), json=POLY)
    with app_mapa.app_context():
        for log in LogAuditoria.query.all():
            blob = " ".join(filter(None, [log.descricao, log.entidade, log.entidade_id]))
            assert "-47.2" not in blob
            assert "coordinates" not in blob
            assert "Polygon" not in blob


def test_log_escopado_por_propriedade(app_mapa):
    from app.models import LogAuditoria

    client = app_mapa.test_client()
    _login(client)
    client.post(_salvar_url(app_mapa), json=POLY)
    with app_mapa.app_context():
        for log in LogAuditoria.query.filter_by(acao="mapa.poligono.update").all():
            assert log.propriedade_id == app_mapa.mapa_ids["prop_id"]


# --- Template --------------------------------------------------------------

def test_template_inclui_csrf_e_can_edit(app_mapa):
    client = app_mapa.test_client()
    _login(client)
    html = client.get("/mapa/").data.decode("utf-8")
    assert "data-csrf-token=" in html
    assert 'data-can-edit="1"' in html
    assert "Editar polígono" in html


def test_template_trabalhador_sem_controles(app_mapa):
    client = app_mapa.test_client()
    _login(client, "trabalhador@connectagro.com")
    html = client.get("/mapa/").data.decode("utf-8")
    assert 'data-can-edit="0"' in html
    assert "mapa-gleba-select" not in html


def test_texto_antigo_removido(app_mapa):
    client = app_mapa.test_client()
    _login(client)
    html = client.get("/mapa/").data.decode("utf-8")
    assert "ficam para etapas futuras" not in html


# --- Sem efeitos colaterais ------------------------------------------------

def test_exportacao_nao_cria_produto_preco_imagem(app_mapa):
    from app.models import ProdutoImagem, ProdutoPreco

    client = app_mapa.test_client()
    _login(client)
    client.post(_salvar_url(app_mapa), json=POLY)
    with app_mapa.app_context():
        assert ProdutoPreco.query.count() == 0
        assert ProdutoImagem.query.count() == 0


# --- CSRF ------------------------------------------------------------------

@pytest.fixture
def app_mapa_csrf(app):
    app.config["WTF_CSRF_ENABLED"] = True
    with app.app_context():
        db.create_all()
    app.mapa_ids = _popular(app)
    return app


def _csrf_token(client):
    html = client.get("/mapa/").data.decode("utf-8")
    match = TOKEN_RE.search(html)
    assert match
    return match.group(1)


def test_csrf_salvar_sem_token_400(app_mapa_csrf):
    client = app_mapa_csrf.test_client()
    _login_csrf(client)
    resp = client.post(_salvar_url(app_mapa_csrf), json=POLY)
    assert resp.status_code == 400


def test_csrf_salvar_com_token_funciona(app_mapa_csrf):
    client = app_mapa_csrf.test_client()
    _login_csrf(client)
    token = _csrf_token(client)
    resp = client.post(_salvar_url(app_mapa_csrf), json=POLY,
                       headers={"X-CSRFToken": token})
    assert resp.status_code == 200


def test_csrf_limpar_sem_token_400(app_mapa_csrf):
    client = app_mapa_csrf.test_client()
    _login_csrf(client)
    resp = client.post(_limpar_url(app_mapa_csrf))
    assert resp.status_code == 400


def test_csrf_limpar_com_token_funciona(app_mapa_csrf):
    client = app_mapa_csrf.test_client()
    _login_csrf(client)
    token = _csrf_token(client)
    resp = client.post(_limpar_url(app_mapa_csrf), headers={"X-CSRFToken": token})
    assert resp.status_code == 200
