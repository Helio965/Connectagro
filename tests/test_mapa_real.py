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


def _popular_cenario_mapa():
    from app.models import Gleba

    _, prop_a = _criar_usuario_propriedade("a@connectagro.com", "Fazenda A")
    _, prop_b = _criar_usuario_propriedade("b@connectagro.com", "Fazenda B")
    _criar_usuario_propriedade("vazio@connectagro.com", "Fazenda Vazia")
    _, prop_sem_coords = _criar_usuario_propriedade(
        "semcoords@connectagro.com", "Fazenda Sem Coordenadas"
    )

    poligono_valido = json.dumps({
        "type": "Polygon",
        "coordinates": [[
            [-47.21, -15.11],
            [-47.20, -15.11],
            [-47.20, -15.10],
            [-47.21, -15.10],
            [-47.21, -15.11],
        ]],
    })

    db.session.add_all([
        Gleba(propriedade_id=prop_a.id, nome="Talhão Norte", area_ha=10.5,
              latitude=-15.1, longitude=-47.2, tipo_solo="argiloso",
              observacoes="perto da sede", poligono_geojson=poligono_valido),
        Gleba(propriedade_id=prop_a.id, nome="Talhão Sem Coordenada", area_ha=4.0),
        Gleba(propriedade_id=prop_a.id, nome="Talhão Coordenada Inválida",
              latitude=-120.0, longitude=-47.5),
        Gleba(propriedade_id=prop_a.id, nome="Talhão GeoJSON Inválido",
              latitude=-15.3, longitude=-47.3, poligono_geojson="{invalido"),
        Gleba(propriedade_id=prop_b.id, nome="Talhão B secreto", area_ha=999,
              latitude=-10.0, longitude=-45.0),
        Gleba(propriedade_id=prop_sem_coords.id, nome="Talhão Sem Latitude", area_ha=8.0),
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
    assert "Talhão Norte" in corpo
    assert "Fazenda B" not in corpo
    assert "Talhão B secreto" not in corpo


def test_mapa_renderiza_avisos_e_assets_sem_depender_do_backend(app_db):
    _, corpo = _corpo_mapa(app_db)
    # Fase 7.5: o mapa agora permite edição de polígono (apoio operacional).
    assert "edição do polígono" in corpo
    assert "não substitui medição técnica ou" in corpo
    assert "leaflet" in corpo.lower()
    assert "js/mapa.js" in corpo


def test_mapa_dados_retorna_json_da_propriedade_atual(app_db):
    resp, dados = _json_mapa(app_db)
    assert resp.status_code == 200
    assert resp.content_type.startswith("application/json")
    assert dados["propriedade"]["nome"] == "Fazenda A"
    assert set(dados) == {"propriedade", "glebas", "sem_coordenadas"}


def test_mapa_dados_nao_expoe_usuario_ou_email(app_db):
    _, dados = _json_mapa(app_db)
    serializado = json.dumps(dados, ensure_ascii=False).lower()
    assert "a@connectagro.com" not in serializado
    assert "b@connectagro.com" not in serializado
    assert "usuario" not in dados["propriedade"]


def test_mapa_dados_filtra_por_propriedade(app_db):
    _, dados = _json_mapa(app_db)
    nomes = {gleba["nome"] for gleba in dados["glebas"]}
    assert "Talhão Norte" in nomes
    assert "Talhão GeoJSON Inválido" in nomes
    assert "Talhão B secreto" not in nomes


def test_mapa_dados_inclui_coordenadas_validas_e_poligono(app_db):
    _, dados = _json_mapa(app_db)
    norte = next(gleba for gleba in dados["glebas"] if gleba["nome"] == "Talhão Norte")
    assert norte["latitude"] == pytest.approx(-15.1)
    assert norte["longitude"] == pytest.approx(-47.2)
    assert norte["area_ha"] == pytest.approx(10.5)
    assert norte["tipo_solo"] == "argiloso"
    assert norte["poligono_geojson"]["type"] == "Polygon"


def test_mapa_dados_separa_glebas_sem_coordenadas_validas(app_db):
    _, dados = _json_mapa(app_db)
    sem_coordenadas = {gleba["nome"] for gleba in dados["sem_coordenadas"]}
    assert "Talhão Sem Coordenada" in sem_coordenadas
    assert "Talhão Coordenada Inválida" in sem_coordenadas
    assert "Talhão Norte" not in sem_coordenadas


def test_mapa_dados_ignora_geojson_invalido_sem_quebrar(app_db):
    _, dados = _json_mapa(app_db)
    gleba = next(item for item in dados["glebas"] if item["nome"] == "Talhão GeoJSON Inválido")
    assert gleba["latitude"] == pytest.approx(-15.3)
    assert gleba["longitude"] == pytest.approx(-47.3)
    assert gleba["poligono_geojson"] is None


def test_mapa_sem_glebas_mostra_estado_vazio(app_db):
    resp, corpo = _corpo_mapa(app_db, "vazio@connectagro.com")
    assert resp.status_code == 200
    assert "Fazenda Vazia" in corpo
    assert "Nenhuma gleba cadastrada ainda." in corpo
    assert "Talhão Norte" not in corpo


def test_mapa_sem_coordenadas_validas_mostra_estado_vazio(app_db):
    resp, corpo = _corpo_mapa(app_db, "semcoords@connectagro.com")
    assert resp.status_code == 200
    assert "Fazenda Sem Coordenadas" in corpo
    assert "Nenhuma gleba com coordenadas válidas para exibir no mapa." in corpo
    assert "Talhão Sem Latitude" in corpo


def test_mapa_nao_tem_rotas_post(app_db):
    client = _login(app_db, "a@connectagro.com")
    assert client.post("/mapa/").status_code == 405
    assert client.post("/mapa/dados").status_code == 405


def test_mapa_nao_apresenta_recursos_fora_de_escopo(app_db):
    # Fase 7.5: edição de polígono é funcionalidade ativa, mas recursos fora de
    # escopo (PostGIS, importação/exportação geográfica, satélite) não são oferecidos.
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
