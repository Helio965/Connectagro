"""Testes do Mapa real simplificado (Etapa 5.9)."""
import json

import pytest

from app.extensions import db
from app.utils.auth import gerar_hash_senha


def _login(app_db, email):
    client = app_db.test_client()
    client.post("/auth/login", data={"email": email, "senha": "senha123"})
    return client


def _criar_usuario_propriedade(email, nome_propriedade):
    from app.models import Propriedade, Usuario

    usuario = Usuario(nome=email, email=email, perfil="tecnico", ativo=True,
                      senha_hash=gerar_hash_senha("senha123"))
    db.session.add(usuario)
    db.session.commit()
    propriedade = Propriedade(usuario_id=usuario.id, nome=nome_propriedade)
    db.session.add(propriedade)
    db.session.commit()
    return usuario, propriedade


def _poligono_valido():
    return json.dumps({
        "type": "Polygon",
        "coordinates": [[
            [-47.21, -15.11],
            [-47.20, -15.11],
            [-47.20, -15.10],
            [-47.21, -15.10],
            [-47.21, -15.11],
        ]],
    })


def _popular_cenario_mapa():
    from app.models import Gleba

    _, prop_a = _criar_usuario_propriedade("a@connectagro.com", "Fazenda A")
    _, prop_b = _criar_usuario_propriedade("b@connectagro.com", "Fazenda B")
    _criar_usuario_propriedade("vazio@connectagro.com", "Fazenda Vazia")
    _, prop_sem_poligono = _criar_usuario_propriedade(
        "sempoligono@connectagro.com", "Fazenda Sem Poligono"
    )

    db.session.add_all([
        Gleba(propriedade_id=prop_a.id, nome="Talhao Norte", area_ha=10.5,
              tipo_solo="argiloso", status="em_cultivo",
              observacoes="perto da sede", poligono_geojson=_poligono_valido()),
        Gleba(propriedade_id=prop_a.id, nome="Talhao Sem Poligono", area_ha=4.0),
        Gleba(propriedade_id=prop_a.id, nome="Talhao GeoJSON Invalido",
              area_ha=3.0, poligono_geojson="{invalido"),
        Gleba(propriedade_id=prop_b.id, nome="Talhao B secreto", area_ha=999,
              poligono_geojson=_poligono_valido()),
        Gleba(propriedade_id=prop_sem_poligono.id, nome="Talhao Sem Poligono", area_ha=8.0),
    ])
    db.session.commit()


@pytest.fixture
def app_db(app):
    with app.app_context():
        db.create_all()
        _popular_cenario_mapa()
    return app


def _corpo_mapa(app_db, email="a@connectagro.com"):
    client = _login(app_db, email)
    resp = client.get("/mapa/")
    return resp, resp.data.decode("utf-8")


def _json_mapa(app_db, email="a@connectagro.com"):
    client = _login(app_db, email)
    resp = client.get("/mapa/dados")
    return resp, resp.get_json()


def test_mapa_exige_login(app_db):
    resp = app_db.test_client().get("/mapa/")
    assert resp.status_code == 302
    assert "/auth/login" in resp.headers["Location"]


def test_mapa_dados_exige_login(app_db):
    resp = app_db.test_client().get("/mapa/dados")
    assert resp.status_code == 302
    assert "/auth/login" in resp.headers["Location"]


def test_mapa_com_login_responde_200(app_db):
    resp, corpo = _corpo_mapa(app_db)
    assert resp.status_code == 200
    assert "Mapa da propriedade" in corpo
    assert "mapa-glebas" in corpo


def test_mapa_mostra_propriedade_atual_sem_vazar_outra(app_db):
    _, corpo = _corpo_mapa(app_db)
    assert "Fazenda A" in corpo
    assert "Talhao Norte" in corpo
    assert "Fazenda B" not in corpo
    assert "Talhao B secreto" not in corpo


def test_mapa_renderiza_avisos_e_assets_sem_depender_do_backend(app_db):
    _, corpo = _corpo_mapa(app_db)
    assert "mapa-aviso" in corpo
    assert "dados técnicos no cadastro" in corpo
    assert "leaflet" in corpo.lower()
    assert "js/mapa.js" in corpo


def test_mapa_dados_retorna_json_da_propriedade_atual(app_db):
    resp, dados = _json_mapa(app_db)
    assert resp.status_code == 200
    assert resp.content_type.startswith("application/json")
    assert dados["propriedade"]["nome"] == "Fazenda A"
    assert set(dados) == {"propriedade", "glebas"}


def test_mapa_dados_nao_expoe_usuario_ou_email(app_db):
    _, dados = _json_mapa(app_db)
    serializado = json.dumps(dados, ensure_ascii=False).lower()
    assert "a@connectagro.com" not in serializado
    assert "b@connectagro.com" not in serializado
    assert "usuario" not in dados["propriedade"]


def test_mapa_dados_filtra_por_propriedade(app_db):
    _, dados = _json_mapa(app_db)
    nomes = {gleba["nome"] for gleba in dados["glebas"]}
    assert "Talhao Norte" in nomes
    assert "Talhao GeoJSON Invalido" in nomes
    assert "Talhao B secreto" not in nomes


def test_mapa_dados_inclui_gleba_e_poligono_sem_coordenadas(app_db):
    _, dados = _json_mapa(app_db)
    norte = next(gleba for gleba in dados["glebas"] if gleba["nome"] == "Talhao Norte")
    assert "latitude" not in norte
    assert "longitude" not in norte
    assert norte["area_ha"] == 10.5
    assert norte["tipo_solo"] == "argiloso"
    assert norte["status"] == "em_cultivo"
    assert norte["poligono_geojson"]["type"] == "Polygon"


def test_mapa_dados_inclui_glebas_mesmo_sem_poligono(app_db):
    _, dados = _json_mapa(app_db)
    sem_poligono = next(gleba for gleba in dados["glebas"] if gleba["nome"] == "Talhao Sem Poligono")
    assert sem_poligono["poligono_geojson"] is None
    assert "sem_coordenadas" not in dados


def test_mapa_dados_ignora_geojson_invalido_sem_quebrar(app_db):
    _, dados = _json_mapa(app_db)
    gleba = next(item for item in dados["glebas"] if item["nome"] == "Talhao GeoJSON Invalido")
    assert "latitude" not in gleba
    assert "longitude" not in gleba
    assert gleba["poligono_geojson"] is None


def test_mapa_sem_glebas_mostra_estado_vazio(app_db):
    resp, corpo = _corpo_mapa(app_db, "vazio@connectagro.com")
    assert resp.status_code == 200
    assert "Fazenda Vazia" in corpo
    assert "Nenhuma propriedade cadastrada ainda." in corpo
    assert "Talhao Norte" not in corpo


def test_mapa_sem_poligono_mantem_lista_e_mapa_funcionando(app_db):
    resp, corpo = _corpo_mapa(app_db, "sempoligono@connectagro.com")
    assert resp.status_code == 200
    assert "Fazenda Sem Poligono" in corpo
    assert "Talhao Sem Poligono" in corpo
    assert "Sem polígono cadastrado" in corpo


def test_mapa_nao_tem_post_nas_rotas_de_consulta(app_db):
    client = _login(app_db, "a@connectagro.com")
    assert client.post("/mapa/").status_code == 405
    assert client.post("/mapa/dados").status_code == 405


def test_mapa_nao_apresenta_recursos_fora_de_escopo(app_db):
    _, corpo = _corpo_mapa(app_db)
    assert "data-can-edit" in corpo
    corpo = corpo.lower()
    for proibido in (
        "postgis",
        "importar geojson",
        "exportar geojson",
        "shapefile",
        "camada de satélite",
    ):
        assert proibido not in corpo
