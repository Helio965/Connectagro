"""Topologia, limites de recurso e leitura legada sem reparos silenciosos."""
import copy
import json
import math

import pytest

from app.services.mapa_service import (
    MAX_GEOJSON_BYTES,
    comparar_limites,
    ler_poligono_geojson,
    validar_poligono_geojson,
)


def quadrado(x=0, y=0, lado=4):
    return {"type": "Polygon", "coordinates": [[
        [x, y], [x+lado, y], [x+lado, y+lado], [x, y+lado], [x, y],
    ]]}


def multipoligono(*poligonos):
    return {"type": "MultiPolygon", "coordinates": [p["coordinates"] for p in poligonos]}


def feature(geometria, properties=None):
    return {"type": "Feature", "properties": properties or {}, "geometry": geometria}


@pytest.mark.parametrize('payload', [
    quadrado(),
    multipoligono(quadrado(), quadrado(8, 8)),
    # Toque em um único vértice é válido entre partes.
    multipoligono(quadrado(), quadrado(4, 4)),
    feature(quadrado(), {"nome": "Delimitação antiga"}),
    {"type":"Polygon", "coordinates":[quadrado()["coordinates"][0],
        quadrado(1, 1, 1)["coordinates"][0]]},
    {"type":"Polygon", "coordinates":[[
        [0, 0, 100], [4, 0, 100], [4, 4, 100], [0, 4, 100], [0, 0, 100]]]},
])
def test_geometrias_validas_preservam_formato_e_vertices(payload):
    anterior = copy.deepcopy(payload)
    texto, erro = validar_poligono_geojson(payload)
    assert erro is None
    assert json.loads(texto) == anterior
    assert payload == anterior


@pytest.mark.parametrize('transformar', [lambda p: p, json.dumps,
    lambda p: json.dumps(p).encode('utf-8')])
def test_validador_aceita_objeto_texto_e_bytes_utf8(transformar):
    texto, erro = validar_poligono_geojson(transformar(quadrado()))
    assert erro is None
    assert json.loads(texto) == quadrado()


@pytest.mark.parametrize('payload', [
    None, [], 1, True, False, 'invalido', b'\xff',
    {"type": []}, {"type": {}}, {"type": True},
    {"type": "GeometryCollection", "geometries": []},
    {"type":"Feature", "geometry":{"type":[]}},
    {"type":"Feature", "geometry":{"type":{}}},
    {"type":"Feature", "geometry":None},
    {"type":"Feature", "geometry":quadrado(), "properties":[]},
])
def test_payloads_malformados_retornam_erro_controlado(payload):
    texto, erro = validar_poligono_geojson(payload)
    assert texto is None
    assert isinstance(erro, str) and erro


@pytest.mark.parametrize('valor', [
    10**1000, -(10**1000), float('inf'), float('-inf'), float('nan'),
    True, False, '1', None, [], {},
])
def test_coordenada_malformada_ou_enorme_nao_gera_excecao(valor):
    payload = quadrado()
    payload['coordinates'][0][1][0] = valor
    texto, erro = validar_poligono_geojson(payload)
    assert texto is None and erro


@pytest.mark.parametrize('altitude', [True, 'alta', float('nan'), float('inf'), 10**1000])
def test_altitude_opcional_tambem_exige_numero_finito(altitude):
    payload = quadrado()
    payload['coordinates'] = [[[p[0], p[1], altitude] for p in payload['coordinates'][0]]]
    assert validar_poligono_geojson(payload)[0] is None


@pytest.mark.parametrize('valor', [float('nan'), float('inf'), float('-inf')])
def test_numeros_nao_json_em_metadados_sao_recusados(valor):
    payload = feature(quadrado(), {'arbitrario': valor})
    assert validar_poligono_geojson(payload)[0] is None
    assert validar_poligono_geojson(json.dumps(payload).encode())[0] is None


@pytest.mark.parametrize('payload', [
    # Apenas um ou dois pontos distintos.
    {"type":"Polygon", "coordinates":[[[0,0],[0,0],[0,0],[0,0]]]},
    {"type":"Polygon", "coordinates":[[[0,0],[1,1],[0,0],[0,0]]]},
    # Colinear, sem região de área positiva.
    {"type":"Polygon", "coordinates":[[[0,0],[1,1],[2,2],[0,0]]]},
    # Bow-tie: autointerseção.
    {"type":"Polygon", "coordinates":[[[0,0],[4,4],[0,4],[4,0],[0,0]]]},
    # Anel aberto.
    {"type":"Polygon", "coordinates":[[[0,0],[4,0],[4,4],[0,4]]]},
    # Furo externo à casca.
    {"type":"Polygon", "coordinates":[quadrado()['coordinates'][0],
        quadrado(8,8,1)['coordinates'][0]]},
    # Dois furos sobrepostos.
    {"type":"Polygon", "coordinates":[quadrado()['coordinates'][0],
        quadrado(1,1,2)['coordinates'][0], quadrado(2,2,1)['coordinates'][0]]},
    # Partes com sobreposição ou aresta inteira compartilhada.
    multipoligono(quadrado(), quadrado(2,2)),
    multipoligono(quadrado(), quadrado(4,0)),
])
def test_topologia_invalida_e_recusada_sem_reparo(payload):
    anterior = copy.deepcopy(payload)
    texto, erro = validar_poligono_geojson(payload)
    assert texto is None and erro
    assert payload == anterior


def test_json_grande_e_recusado_antes_do_parse():
    bruto = b' ' * (MAX_GEOJSON_BYTES + 1)
    texto, erro = validar_poligono_geojson(bruto)
    assert texto is None and 'tamanho' in erro


def test_tamanho_utf8_tambem_e_limitado():
    payload = feature(quadrado(), {'texto': 'á' * (MAX_GEOJSON_BYTES // 2)})
    assert validar_poligono_geojson(payload)[0] is None


def test_json_profundamente_aninhado_bruto_e_controlado():
    bruto = b'[' * 2000 + b'0' + b']' * 2000
    assert validar_poligono_geojson(bruto)[0] is None


def test_profundidade_de_metadados_e_limitada_antes_da_serializacao():
    payload = feature(quadrado())
    destino = payload['properties']
    for _ in range(40):
        destino['nivel'] = {}
        destino = destino['nivel']
    texto, erro = validar_poligono_geojson(payload)
    assert texto is None and 'complexidade' in erro


def test_ciclo_em_objeto_direto_e_controlado():
    payload = feature(quadrado())
    payload['properties']['ciclo'] = payload
    assert validar_poligono_geojson(payload)[0] is None


def test_referencias_repetidas_sem_ciclo_nao_sao_rejeitadas():
    compartilhado = [1,2,3]
    payload = feature(quadrado(), {'a': compartilhado, 'b': compartilhado})
    assert validar_poligono_geojson(payload)[1] is None


@pytest.mark.parametrize('payload', [
    feature(quadrado(), {'itens': [0] * 20001}),
    {"type":"Polygon", "coordinates":[[[0,0]] * 5001]},
    {"type":"Polygon", "coordinates":[quadrado()['coordinates'][0]] * 257},
    multipoligono(*[quadrado() for _ in range(129)]),
])
def test_limites_de_nos_posicoes_aneis_e_partes(payload):
    texto, erro = validar_poligono_geojson(payload)
    assert texto is None and 'complexidade' in erro


def test_texto_unicode_invalido_em_metadados_e_controlado():
    payload = feature(quadrado(), {'texto': '\ud800'})
    assert validar_poligono_geojson(payload)[0] is None
    assert validar_poligono_geojson(json.dumps(payload))[0] is None


def test_leitor_legado_preserva_colecao_poligonal_valida_sem_permitir_nova_escrita():
    colecao = {"type":"FeatureCollection", "features":[feature(quadrado()),
        feature(multipoligono(quadrado(8,8),quadrado(16,16)))]}
    texto = json.dumps(colecao, indent=2, ensure_ascii=False)
    assert ler_poligono_geojson(texto) == colecao
    assert validar_poligono_geojson(colecao)[0] is None
    assert texto == json.dumps(colecao, indent=2, ensure_ascii=False)


@pytest.mark.parametrize('payload', [
    '{invalido', {'type':[]},
    {"type":"Polygon", "coordinates":[[[0,0],[1,1],[2,2],[0,0]]]},
    {"type":"FeatureCollection", "features":[{"type":"Feature", "geometry":None}]},
    {"type":"FeatureCollection", "features":[{"type":"Feature", "geometry":{"type":"Point","coordinates":[0,0]}}]},
    {"type":"FeatureCollection", "features":[quadrado()]},
])
def test_leitura_legada_invalida_e_ignorada_sem_excecao(payload):
    assert ler_poligono_geojson(payload) is None


@pytest.mark.parametrize('contorno,area,status', [
    (quadrado(), quadrado(1,1,1), 'contida'),
    (quadrado(), quadrado(0,0,1), 'contida'),
    (quadrado(), quadrado(), 'contida'),
    (quadrado(), quadrado(3,3,2), 'fora_do_limite'),
    (quadrado(), quadrado(8,8,1), 'fora_do_limite'),
    (None, quadrado(), 'sem_delimitacao'),
    (quadrado(), '', 'sem_delimitacao'),
    ('{invalido', quadrado(), 'nao_verificavel'),
    (quadrado(), {'type':[]}, 'nao_verificavel'),
    ({'type':'FeatureCollection','features':[]}, quadrado(), 'nao_verificavel'),
])
def test_comparacao_de_limites_e_informativa(contorno,area,status):
    resultado = comparar_limites(contorno,area)
    assert resultado['status'] == status
    assert isinstance(resultado['mensagem'],str) and resultado['mensagem']


def test_area_em_furo_da_propriedade_nao_e_contida():
    contorno = quadrado()
    contorno['coordinates'].append(quadrado(1,1,2)['coordinates'][0])
    assert comparar_limites(contorno, quadrado(1.2,1.2,0.5))['status'] == 'fora_do_limite'


def test_contencao_considera_todas_as_partes_e_features_legadas():
    partes = multipoligono(quadrado(),quadrado(8,8))
    area = multipoligono(quadrado(1,1,1),quadrado(9,9,1))
    assert comparar_limites(partes,area)['status'] == 'contida'
    colecao = {'type':'FeatureCollection','features':[feature(quadrado()),feature(quadrado(8,8))]}
    assert comparar_limites(json.dumps(colecao),feature(area))['status'] == 'contida'


def test_antimeridiano_nao_e_apresentado_como_comparacao_geodesica():
    contorno = {'type':'Polygon','coordinates':[[[179,0],[-179,0],[-179,4],[179,4],[179,0]]]}
    assert validar_poligono_geojson(contorno)[1] is None
    resultado = comparar_limites(contorno,quadrado(179,1,0.5))
    assert resultado['status'] == 'nao_verificavel'
    assert 'antimeridiano' in resultado['mensagem']
