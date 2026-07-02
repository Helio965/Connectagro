"""Serviço de mapa do ConnectAgro (Fase 7.5).

Valida, atualiza e limpa polígonos GeoJSON das glebas. O GeoJSON é validado
no backend (Polygon/MultiPolygon/Feature, coordenadas em faixa, tamanho
limitado); inválido retorna erro e não é salvo.
"""
import json

from ..models._helpers import iso_now

# Tipos GeoJSON aceitos.
_TIPOS_ACEITOS = {"Polygon", "MultiPolygon", "Feature"}

# Tamanho máximo do GeoJSON serializado (bytes).
_MAX_GEOJSON_BYTES = 500_000


def validar_poligono_geojson(payload):
    """Valida um payload GeoJSON para salvamento.

    Retorna ``(geojson_string, None)`` em caso de sucesso ou
    ``(None, mensagem_de_erro)`` se inválido.
    """
    if payload is None:
        return None, "Payload vazio."

    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except (TypeError, ValueError):
            return None, "JSON inválido."

    if not isinstance(payload, dict):
        return None, "O payload deve ser um objeto JSON."

    tipo = payload.get("type")
    if tipo not in _TIPOS_ACEITOS:
        return None, f"Tipo GeoJSON não suportado: {tipo}. Use Polygon, MultiPolygon ou Feature."

    if tipo in {"Polygon", "MultiPolygon"}:
        coords = payload.get("coordinates")
        if not isinstance(coords, list):
            return None, "Coordenadas ausentes ou inválidas."
        if not _validar_coordenadas_recursive(coords):
            return None, "Coordenadas fora da faixa válida (-90/90 lat, -180/180 lng)."

    if tipo == "Feature":
        geometry = payload.get("geometry")
        if not isinstance(geometry, dict):
            return None, "Feature sem geometria válida."
        geo_tipo = geometry.get("type")
        if geo_tipo not in {"Polygon", "MultiPolygon"}:
            return None, f"Geometria não suportada dentro de Feature: {geo_tipo}."
        coords = geometry.get("coordinates")
        if not isinstance(coords, list):
            return None, "Coordenadas ausentes na geometria."
        if not _validar_coordenadas_recursive(coords):
            return None, "Coordenadas fora da faixa válida."

    geojson_str = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    if len(geojson_str.encode("utf-8")) > _MAX_GEOJSON_BYTES:
        return None, f"GeoJSON excede o tamanho máximo ({_MAX_GEOJSON_BYTES} bytes)."

    return geojson_str, None


def _validar_coordenadas_recursive(coords, depth=0):
    """Valida coordenadas recursivamente (listas de listas de [lng, lat])."""
    if depth > 4:
        return False
    if not isinstance(coords, list):
        return False
    if len(coords) == 0:
        return True
    # Se é uma coordenada [lng, lat] ou [lng, lat, alt]
    if isinstance(coords[0], (int, float)):
        if len(coords) < 2:
            return False
        lng, lat = coords[0], coords[1]
        return -180 <= lng <= 180 and -90 <= lat <= 90
    # Caso contrário é uma lista de coordenadas
    return all(_validar_coordenadas_recursive(c, depth + 1) for c in coords)


def atualizar_poligono_gleba(gleba, geojson_str):
    """Atualiza o polígono GeoJSON de uma gleba."""
    gleba.poligono_geojson = geojson_str
    gleba.atualizado_em = iso_now()


def limpar_poligono_gleba(gleba):
    """Remove o polígono GeoJSON de uma gleba."""
    gleba.poligono_geojson = None
    gleba.atualizado_em = iso_now()
