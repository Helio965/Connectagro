"""Validação/normalização de polígonos GeoJSON do mapa avançado (Fase 7.5).

Operacional, **sem PostGIS**, sem dependência geoespacial e sem georreferencia-
mento oficial. Aceita apenas ``Polygon``, ``MultiPolygon`` ou ``Feature`` com
geometria Polygon/MultiPolygon — **rejeita** FeatureCollection e
GeometryCollection (um polígono por gleba nesta fase).
"""
import json

from ..models._helpers import iso_now

# Limite de tamanho do GeoJSON aceito (evita abuso). 100 KB.
MAX_GEOJSON_BYTES = 100 * 1024


def _eh_numero(valor):
    return isinstance(valor, (int, float)) and not isinstance(valor, bool)


def _validar_anel(anel):
    if not isinstance(anel, list) or len(anel) < 4:
        return "Cada anel do polígono precisa de ao menos 4 pontos."
    for ponto in anel:
        if not isinstance(ponto, (list, tuple)) or len(ponto) < 2:
            return "Coordenada inválida: use pares [longitude, latitude]."
        lon, lat = ponto[0], ponto[1]
        if not _eh_numero(lon) or not _eh_numero(lat):
            return "Coordenada não numérica."
        if not (-180 <= lon <= 180) or not (-90 <= lat <= 90):
            return "Coordenada fora da faixa permitida."
    return None


def _validar_poligono_coords(coords):
    if not isinstance(coords, list) or not coords:
        return "Polígono sem anéis."
    for anel in coords:
        erro = _validar_anel(anel)
        if erro:
            return erro
    return None


def _validar_geometry(geom):
    if not isinstance(geom, dict):
        return "Geometria inválida."
    tipo = geom.get("type")
    coords = geom.get("coordinates")
    if tipo == "Polygon":
        return _validar_poligono_coords(coords)
    if tipo == "MultiPolygon":
        if not isinstance(coords, list) or not coords:
            return "MultiPolygon sem polígonos."
        for poligono in coords:
            erro = _validar_poligono_coords(poligono)
            if erro:
                return erro
        return None
    return "Tipo de geometria não suportado (use Polygon ou MultiPolygon)."


def _fechar_anel(anel):
    if anel and anel[0] != anel[-1]:
        return list(anel) + [list(anel[0])]
    return [list(p) for p in anel]


def _normalizar_coords(tipo, coords):
    if tipo == "Polygon":
        return [_fechar_anel(anel) for anel in coords]
    # MultiPolygon
    return [[_fechar_anel(anel) for anel in poligono] for poligono in coords]


def _normalizar_geometry(geom):
    tipo = geom["type"]
    return {"type": tipo, "coordinates": _normalizar_coords(tipo, geom["coordinates"])}


def validar_poligono_geojson(payload):
    """Valida e normaliza o GeoJSON recebido.

    Retorna ``(geojson_normalizado, None)`` em sucesso ou ``(None, mensagem)`` em
    erro. Aceita Polygon/MultiPolygon/Feature; fecha anéis automaticamente.
    """
    if not isinstance(payload, dict):
        return None, "GeoJSON inválido."

    try:
        if len(json.dumps(payload)) > MAX_GEOJSON_BYTES:
            return None, "GeoJSON excede o tamanho máximo permitido."
    except (TypeError, ValueError):
        return None, "GeoJSON inválido."

    tipo = payload.get("type")
    if tipo == "Feature":
        geometry = payload.get("geometry")
        erro = _validar_geometry(geometry)
        if erro:
            return None, erro
        return {
            "type": "Feature",
            "properties": payload.get("properties") if isinstance(payload.get("properties"), dict) else {},
            "geometry": _normalizar_geometry(geometry),
        }, None

    if tipo in ("Polygon", "MultiPolygon"):
        erro = _validar_geometry(payload)
        if erro:
            return None, erro
        return _normalizar_geometry(payload), None

    if tipo in ("FeatureCollection", "GeometryCollection"):
        return None, "Use um único polígono (Polygon/MultiPolygon/Feature) por gleba."

    return None, "Tipo de GeoJSON não suportado (use Polygon, MultiPolygon ou Feature)."


def normalizar_poligono_geojson(payload):
    """Atalho que retorna apenas o GeoJSON normalizado (ou ``None``)."""
    geojson, _ = validar_poligono_geojson(payload)
    return geojson


def atualizar_poligono_gleba(gleba, geojson_normalizado):
    """Grava o polígono na gleba (como TEXT) e marca atualização."""
    gleba.poligono_geojson = json.dumps(geojson_normalizado, ensure_ascii=False)
    gleba.atualizado_em = iso_now()


def limpar_poligono_gleba(gleba):
    """Remove o polígono da gleba e marca atualização."""
    gleba.poligono_geojson = None
    gleba.atualizado_em = iso_now()
