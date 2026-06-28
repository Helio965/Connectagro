"""Rotas do módulo Mapa real simplificado do MVP."""
import json

from flask import jsonify, render_template

from . import mapa_bp
from ...models import Gleba
from ...utils.auth import login_required
from ...utils.contexto import propriedade_atual
from ...utils.formatters import formatar_area
from ...utils.permissions import require_permission

_GEOJSON_TYPES = {"Feature", "FeatureCollection", "Polygon", "MultiPolygon"}


def _numero(valor):
    """Converte valores numéricos simples sem alterar o dado armazenado."""
    if valor is None:
        return None
    try:
        return float(valor)
    except (TypeError, ValueError):
        return None


def _coordenadas_validas(gleba):
    """Retorna latitude/longitude válidas ou ``None``."""
    latitude = _numero(gleba.latitude)
    longitude = _numero(gleba.longitude)
    if latitude is None or longitude is None:
        return None
    if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
        return None
    return latitude, longitude


def _poligono_geojson_valido(valor):
    """Lê GeoJSON salvo na gleba; conteúdo inválido é ignorado com segurança."""
    if not valor:
        return None
    try:
        dados = json.loads(valor)
    except (TypeError, ValueError):
        return None

    if not isinstance(dados, dict) or dados.get("type") not in _GEOJSON_TYPES:
        return None
    if dados["type"] in {"Polygon", "MultiPolygon"} and "coordinates" not in dados:
        return None
    if dados["type"] == "Feature" and not isinstance(dados.get("geometry"), dict):
        return None
    if dados["type"] == "FeatureCollection" and not isinstance(dados.get("features"), list):
        return None
    return dados


def _gleba_payload(gleba):
    latitude, longitude = _coordenadas_validas(gleba)
    return {
        "id": gleba.id,
        "nome": gleba.nome,
        "area_ha": gleba.area_ha,
        "latitude": latitude,
        "longitude": longitude,
        "tipo_solo": gleba.tipo_solo,
        "observacoes": gleba.observacoes,
        "poligono_geojson": _poligono_geojson_valido(gleba.poligono_geojson),
    }


def _gleba_sem_coordenada_payload(gleba):
    return {"id": gleba.id, "nome": gleba.nome}


def _dados_mapa(propriedade):
    glebas = (Gleba.query
              .filter_by(propriedade_id=propriedade.id)
              .order_by(Gleba.nome.asc())
              .all())
    com_coordenadas = []
    sem_coordenadas = []

    for gleba in glebas:
        if _coordenadas_validas(gleba) is None:
            sem_coordenadas.append(_gleba_sem_coordenada_payload(gleba))
        else:
            com_coordenadas.append(_gleba_payload(gleba))

    return glebas, com_coordenadas, sem_coordenadas


@mapa_bp.route("/")
@login_required
@require_permission("mapa.view")
def index():
    propriedade = propriedade_atual()
    glebas, glebas_com_coordenadas, glebas_sem_coordenadas = _dados_mapa(propriedade)
    return render_template(
        "mapa/index.html",
        propriedade=propriedade,
        glebas=glebas,
        glebas_com_coordenadas=glebas_com_coordenadas,
        glebas_sem_coordenadas=glebas_sem_coordenadas,
        formatar_area=formatar_area,
    )


@mapa_bp.route("/dados")
@login_required
@require_permission("mapa.view")
def dados():
    propriedade = propriedade_atual()
    _, glebas_com_coordenadas, glebas_sem_coordenadas = _dados_mapa(propriedade)
    return jsonify({
        "propriedade": {"id": propriedade.id, "nome": propriedade.nome},
        "glebas": glebas_com_coordenadas,
        "sem_coordenadas": glebas_sem_coordenadas,
    })
