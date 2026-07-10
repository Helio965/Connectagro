"""Serviço de mapa do ConnectAgro (Fase 7.5).

Valida, atualiza e limpa polígonos GeoJSON das glebas. O GeoJSON é validado
no backend (Polygon/MultiPolygon/Feature, coordenadas em faixa, tamanho
limitado); inválido retorna erro e não é salvo.
"""
import json
import math

from ..models._helpers import iso_now

# Tipos GeoJSON aceitos.
_TIPOS_ACEITOS = {"Polygon", "MultiPolygon", "Feature"}

# Tamanho máximo do GeoJSON serializado (bytes) — contrato da Fase 7.5.
_MAX_GEOJSON_BYTES = 100 * 1024


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
        erro = _validar_geometria(tipo, payload.get("coordinates"))
        if erro:
            return None, erro

    if tipo == "Feature":
        geometry = payload.get("geometry")
        if not isinstance(geometry, dict):
            return None, "Feature sem geometria válida."
        geo_tipo = geometry.get("type")
        if geo_tipo not in {"Polygon", "MultiPolygon"}:
            return None, f"Geometria não suportada dentro de Feature: {geo_tipo}."
        erro = _validar_geometria(geo_tipo, geometry.get("coordinates"))
        if erro:
            return None, erro

    geojson_str = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    if len(geojson_str.encode("utf-8")) > _MAX_GEOJSON_BYTES:
        return None, f"GeoJSON excede o tamanho máximo ({_MAX_GEOJSON_BYTES} bytes)."

    return geojson_str, None


def _validar_geometria(tipo, coords):
    """Valida as ``coordinates`` de um Polygon/MultiPolygon.

    Retorna ``None`` quando válidas ou a mensagem de erro apropriada.
    """
    if not isinstance(coords, list) or not coords:
        return "Coordenadas ausentes ou inválidas."
    if tipo == "Polygon":
        return _validar_poligono(coords)
    # MultiPolygon: lista não vazia de polígonos.
    for poligono in coords:
        erro = _validar_poligono(poligono)
        if erro:
            return erro
    return None


def _validar_poligono(aneis):
    """Valida um polígono: lista não vazia de anéis lineares válidos."""
    if not isinstance(aneis, list) or not aneis:
        return "O polígono deve conter ao menos um anel de coordenadas."
    for anel in aneis:
        erro = _validar_anel(anel)
        if erro:
            return erro
    return None


def _validar_anel(anel):
    """Valida um anel linear: >= 4 posições válidas e fechado."""
    if not isinstance(anel, list) or len(anel) < 4:
        return "Cada anel do polígono precisa de ao menos 4 pontos."
    for posicao in anel:
        if not _posicao_valida(posicao):
            return ("Coordenadas inválidas: cada posição deve ser [lng, lat] "
                    "numérica, com longitude entre -180 e 180 e latitude "
                    "entre -90 e 90.")
    if anel[0] != anel[-1]:
        return "Cada anel do polígono deve ser fechado (último ponto igual ao primeiro)."
    return None


def _posicao_valida(posicao):
    """Posição GeoJSON: [lng, lat] (altitude opcional) numérica e em faixa."""
    if not isinstance(posicao, list) or len(posicao) < 2:
        return False
    lng, lat = posicao[0], posicao[1]
    for valor in (lng, lat):
        if isinstance(valor, bool) or not isinstance(valor, (int, float)):
            return False
        if not math.isfinite(valor):
            return False
    return -180 <= lng <= 180 and -90 <= lat <= 90


def atualizar_poligono_gleba(gleba, geojson_str):
    """Atualiza o polígono GeoJSON de uma gleba."""
    gleba.poligono_geojson = geojson_str
    gleba.atualizado_em = iso_now()


def limpar_poligono_gleba(gleba):
    """Remove o polígono GeoJSON de uma gleba."""
    gleba.poligono_geojson = None
    gleba.atualizado_em = iso_now()
