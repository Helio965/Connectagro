"""Mapa operacional: contorno de Propriedade e Áreas de Plantio autorizadas."""
import math

from flask import abort, jsonify, render_template, request
from werkzeug.exceptions import BadRequest

from . import mapa_bp
from ...extensions import db
from ...models import Gleba
from ...services.auditoria_service import registrar_falha, registrar_negado, registrar_sucesso
from ...services.mapa_service import (
    MAX_GEOJSON_BYTES,
    atualizar_poligono_gleba,
    atualizar_poligono_propriedade,
    comparar_limites,
    ler_poligono_geojson,
    limpar_poligono_gleba,
    limpar_poligono_propriedade,
    validar_poligono_geojson,
)
from ...utils.auth import login_required
from ...utils.contexto import propriedade_atual
from ...utils.formatters import formatar_area
from ...utils.permissions import require_permission


def _poligono_geojson_valido(valor):
    """Compatibilidade do leitor anterior, agora com validação completa e limites."""
    return ler_poligono_geojson(valor)


def _estado_poligono(valor, geometria):
    if valor is None or valor == "" or valor == b"":
        return "ausente"
    return "valido" if geometria is not None else "invalido"


def _numero_finito(valor):
    if isinstance(valor, bool) or not isinstance(valor, (int, float)):
        return None
    try:
        return valor if math.isfinite(valor) else None
    except OverflowError:
        return None


def _propriedade_payload(propriedade):
    geometria = _poligono_geojson_valido(propriedade.poligono_geojson)
    return {
        "id": propriedade.id,
        "nome": propriedade.nome,
        "municipio": propriedade.municipio,
        "uf": propriedade.uf,
        "area_total_ha": _numero_finito(propriedade.area_total_ha),
        "poligono_geojson": geometria,
        "poligono_estado": _estado_poligono(propriedade.poligono_geojson, geometria),
    }


def _gleba_payload(gleba, propriedade=None):
    geometria = _poligono_geojson_valido(gleba.poligono_geojson)
    return {
        "id": gleba.id,
        "nome": gleba.nome,
        "area_ha": _numero_finito(gleba.area_ha),
        "tipo_solo": gleba.tipo_solo,
        "status": gleba.status,
        "observacoes": gleba.observacoes,
        "poligono_geojson": geometria,
        "poligono_estado": _estado_poligono(gleba.poligono_geojson, geometria),
        "contencao": comparar_limites(
            propriedade.poligono_geojson if propriedade is not None else None,
            gleba.poligono_geojson),
    }


def _dados_mapa(propriedade):
    glebas = (Gleba.query.filter_by(propriedade_id=propriedade.id)
              .order_by(Gleba.nome.asc()).all())
    return glebas, [_gleba_payload(gleba, propriedade) for gleba in glebas]


@mapa_bp.route("/")
@login_required
@require_permission("mapa.view")
def index():
    propriedade = propriedade_atual()
    glebas, glebas_payload = _dados_mapa(propriedade)
    return render_template("mapa/index.html", propriedade=propriedade,
        propriedade_mapa=_propriedade_payload(propriedade), glebas=glebas,
        glebas_mapa=glebas_payload, formatar_area=formatar_area)


@mapa_bp.route("/dados")
@login_required
@require_permission("mapa.view")
def dados():
    propriedade = propriedade_atual()
    _, glebas_mapa = _dados_mapa(propriedade)
    return jsonify(propriedade=_propriedade_payload(propriedade), glebas=glebas_mapa)


def _id_em_faixa(valor):
    return type(valor) is int and 1 <= valor <= 2**63 - 1


def _recurso_negado(entidade, identificador, propriedade):
    # PostgreSQL usa INTEGER para entidade_id. Não tentar gravar o identificador
    # arbitrário de uma URL fora dessa faixa, nem consultar geometrias de terceiros.
    id_auditoria = identificador if type(identificador) is int and 1 <= identificador <= 2**31 - 1 else None
    prefixo = "mapa.propriedade.poligono" if entidade == "propriedade" else "mapa.poligono"
    registrar_negado(prefixo + ".negado", entidade=entidade, entidade_id=id_auditoria,
        descricao="Tentativa de alterar delimitação fora do contexto autorizado",
        propriedade_id=propriedade.id, request=request)
    abort(404)


def _gleba_da_propriedade_ou_404(gleba_id, propriedade):
    if not _id_em_faixa(gleba_id):
        _recurso_negado("gleba", gleba_id, propriedade)
    gleba = Gleba.query.filter_by(id=gleba_id, propriedade_id=propriedade.id).first()
    if gleba is None:
        _recurso_negado("gleba", gleba_id, propriedade)
    return gleba


def _propriedade_ativa_ou_404(propriedade_id):
    propriedade = propriedade_atual()
    if not _id_em_faixa(propriedade_id) or propriedade_id != propriedade.id:
        _recurso_negado("propriedade", propriedade_id, propriedade)
    return propriedade


def _ler_novo_poligono():
    """Limita bytes antes do parse; JSON profundo não chega ao parser do Flask."""
    if not request.is_json:
        return None, "Envie o polígono como JSON."
    if request.content_length is not None and request.content_length > MAX_GEOJSON_BYTES:
        return None, f"GeoJSON excede o tamanho máximo ({MAX_GEOJSON_BYTES} bytes)."
    try:
        bruto = request.stream.read(MAX_GEOJSON_BYTES + 1)
    except BadRequest:
        return None, "Não foi possível ler o JSON enviado."
    return validar_poligono_geojson(bruto)


def _erro_poligono(prefixo, entidade, objeto, propriedade, erro):
    registrar_falha(prefixo + ".falha", entidade=entidade,
        entidade_id=objeto.id if objeto.id <= 2**31 - 1 else None,
        descricao="GeoJSON inválido ao salvar delimitação",
        propriedade_id=propriedade.id, request=request)
    return jsonify(ok=False, error=erro), 400


@mapa_bp.route("/glebas/<int:gleba_id>/poligono", methods=["POST"])
@login_required
@require_permission("mapa.edit")
def salvar_poligono(gleba_id):
    propriedade = propriedade_atual()
    gleba = _gleba_da_propriedade_ou_404(gleba_id, propriedade)
    geojson, erro = _ler_novo_poligono()
    if erro:
        return _erro_poligono("mapa.poligono", "gleba", gleba, propriedade, erro)
    atualizar_poligono_gleba(gleba, geojson)
    db.session.commit()
    registrar_sucesso("mapa.poligono.update", entidade="gleba",
        entidade_id=gleba.id if gleba.id <= 2**31 - 1 else None,
        descricao="Polígono da Área de Plantio atualizado",
        propriedade_id=propriedade.id, request=request)
    return jsonify(ok=True, message="Polígono salvo com sucesso.",
                   gleba=_gleba_payload(gleba, propriedade))


@mapa_bp.route("/glebas/<int:gleba_id>/poligono/limpar", methods=["POST"])
@login_required
@require_permission("mapa.edit")
def limpar_poligono(gleba_id):
    propriedade = propriedade_atual()
    gleba = _gleba_da_propriedade_ou_404(gleba_id, propriedade)
    limpar_poligono_gleba(gleba)
    db.session.commit()
    registrar_sucesso("mapa.poligono.delete", entidade="gleba",
        entidade_id=gleba.id if gleba.id <= 2**31 - 1 else None,
        descricao="Polígono da Área de Plantio removido",
        propriedade_id=propriedade.id, request=request)
    return jsonify(ok=True, message="Polígono removido com sucesso.",
                   gleba=_gleba_payload(gleba, propriedade))


@mapa_bp.route("/propriedades/<int:propriedade_id>/poligono", methods=["POST"])
@login_required
@require_permission("mapa.edit")
def salvar_poligono_propriedade(propriedade_id):
    propriedade = _propriedade_ativa_ou_404(propriedade_id)
    geojson, erro = _ler_novo_poligono()
    if erro:
        return _erro_poligono("mapa.propriedade.poligono", "propriedade",
                              propriedade, propriedade, erro)
    atualizar_poligono_propriedade(propriedade, geojson)
    db.session.commit()
    registrar_sucesso("mapa.propriedade.poligono.update", entidade="propriedade",
        entidade_id=propriedade.id if propriedade.id <= 2**31 - 1 else None,
        descricao="Contorno da Propriedade atualizado",
        propriedade_id=propriedade.id, request=request)
    return _resposta_propriedade(propriedade, "Polígono da Propriedade salvo com sucesso.")


@mapa_bp.route("/propriedades/<int:propriedade_id>/poligono/limpar", methods=["POST"])
@login_required
@require_permission("mapa.edit")
def limpar_poligono_da_propriedade(propriedade_id):
    propriedade = _propriedade_ativa_ou_404(propriedade_id)
    limpar_poligono_propriedade(propriedade)
    db.session.commit()
    registrar_sucesso("mapa.propriedade.poligono.delete", entidade="propriedade",
        entidade_id=propriedade.id if propriedade.id <= 2**31 - 1 else None,
        descricao="Contorno da Propriedade removido",
        propriedade_id=propriedade.id, request=request)
    return _resposta_propriedade(propriedade, "Polígono da Propriedade removido com sucesso.")


def _resposta_propriedade(propriedade, mensagem):
    _, glebas = _dados_mapa(propriedade)
    return jsonify(ok=True, message=mensagem,
                   propriedade=_propriedade_payload(propriedade), glebas=glebas)
