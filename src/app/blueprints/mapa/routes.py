"""Rotas do módulo Mapa (real simplificado + edição de polígonos — Fase 7.5)."""
import json

from flask import abort, jsonify, render_template, request

from . import mapa_bp
from ...extensions import db
from ...models import Gleba
from ...services.auditoria_service import registrar_falha, registrar_sucesso
from ...services.mapa_service import (
    atualizar_poligono_gleba,
    limpar_poligono_gleba,
    validar_poligono_geojson,
)
from ...utils.auth import login_required
from ...utils.contexto import propriedade_atual
from ...utils.formatters import formatar_area
from ...utils.permissions import require_permission

_GEOJSON_TYPES = {"Feature", "FeatureCollection", "Polygon", "MultiPolygon"}


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
    return {
        "id": gleba.id,
        "nome": gleba.nome,
        "area_ha": gleba.area_ha,
        "tipo_solo": gleba.tipo_solo,
        "status": gleba.status,
        "observacoes": gleba.observacoes,
        "poligono_geojson": _poligono_geojson_valido(gleba.poligono_geojson),
    }


def _dados_mapa(propriedade):
    glebas = (Gleba.query
              .filter_by(propriedade_id=propriedade.id)
              .order_by(Gleba.nome.asc())
              .all())
    return glebas, [_gleba_payload(gleba) for gleba in glebas]


@mapa_bp.route("/")
@login_required
@require_permission("mapa.view")
def index():
    propriedade = propriedade_atual()
    glebas, glebas_payload = _dados_mapa(propriedade)
    return render_template(
        "mapa/index.html",
        propriedade=propriedade,
        glebas=glebas,
        glebas_mapa=glebas_payload,
        formatar_area=formatar_area,
    )


@mapa_bp.route("/dados")
@login_required
@require_permission("mapa.view")
def dados():
    propriedade = propriedade_atual()
    _, glebas_mapa = _dados_mapa(propriedade)
    return jsonify({
        "propriedade": {"id": propriedade.id, "nome": propriedade.nome},
        "glebas": glebas_mapa,
    })


def _gleba_da_propriedade_ou_404(gleba_id, propriedade):
    gleba = Gleba.query.filter_by(id=gleba_id, propriedade_id=propriedade.id).first()
    if gleba is None:
        abort(404)
    return gleba


@mapa_bp.route("/glebas/<int:gleba_id>/poligono", methods=["POST"])
@login_required
@require_permission("mapa.edit")
def salvar_poligono(gleba_id):
    """Salva o polígono GeoJSON de uma gleba da propriedade atual."""
    propriedade = propriedade_atual()
    gleba = _gleba_da_propriedade_ou_404(gleba_id, propriedade)

    payload = request.get_json(silent=True)
    geojson, erro = validar_poligono_geojson(payload)
    if erro:
        registrar_falha(
            "mapa.poligono.falha", entidade="propriedade", entidade_id=gleba.id,
            descricao="GeoJSON inválido ao salvar polígono",
            propriedade_id=propriedade.id, request=request)
        return jsonify({"ok": False, "error": erro}), 400

    atualizar_poligono_gleba(gleba, geojson)
    db.session.commit()
    registrar_sucesso(
        "mapa.poligono.update", entidade="propriedade", entidade_id=gleba.id,
        descricao="Polígono da propriedade atualizado",
        propriedade_id=propriedade.id, request=request)
    return jsonify({
        "ok": True,
        "message": "Polígono salvo com sucesso.",
        "gleba": _gleba_payload(gleba),
    })


@mapa_bp.route("/glebas/<int:gleba_id>/poligono/limpar", methods=["POST"])
@login_required
@require_permission("mapa.edit")
def limpar_poligono(gleba_id):
    """Remove o polígono GeoJSON de uma gleba da propriedade atual."""
    propriedade = propriedade_atual()
    gleba = _gleba_da_propriedade_ou_404(gleba_id, propriedade)

    limpar_poligono_gleba(gleba)
    db.session.commit()
    registrar_sucesso(
        "mapa.poligono.delete", entidade="propriedade", entidade_id=gleba.id,
        descricao="Polígono da propriedade removido",
        propriedade_id=propriedade.id, request=request)
    return jsonify({
        "ok": True,
        "message": "Polígono removido com sucesso.",
        "gleba": _gleba_payload(gleba),
    })
