"""Consulta (somente leitura) de Defensivos do catálogo técnico."""
from flask import abort, render_template, request

from ...models import ProdutoBase
from ...utils.auth import login_required
from ...utils.catalogo import (
    aplicar_filtros_catalogo,
    categorias_disponiveis,
    parse_json_lista,
    primeiro_tecnico,
)
from ...utils.permissions import require_permission
from . import defensivos_bp

CLASSE = "defensivo"
# Campos técnicos em lista exibidos no detalhe de defensivos.
CAMPOS_LISTA = ("culturas_comuns", "alvos_controle")


@defensivos_bp.route("/")
@login_required
@require_permission("catalogo.view")
def index():
    q = request.args.get("q") or None
    categoria = request.args.get("categoria") or None
    produtos = aplicar_filtros_catalogo(CLASSE, q=q, categoria=categoria).all()
    return render_template(
        "catalogo/list.html",
        titulo="Defensivos", endpoint="defensivos.detalhe",
        tipo="defensivos",
        produtos=produtos, q=q or "", categoria=categoria or "",
        categorias=categorias_disponiveis(CLASSE))


@defensivos_bp.route("/<slug>")
@login_required
@require_permission("catalogo.view")
def detalhe(slug):
    produto = ProdutoBase.query.filter_by(slug=slug, classe=CLASSE).first()
    if produto is None:
        abort(404)
    tecnico = primeiro_tecnico(produto)
    listas = {campo: parse_json_lista(getattr(tecnico, campo, None))
              for campo in CAMPOS_LISTA} if tecnico else {}
    return render_template(
        "catalogo/detail.html",
        titulo="Defensivo", voltar_endpoint="defensivos.index",
        produto=produto, tecnico=tecnico, listas=listas, tipo="defensivo")
