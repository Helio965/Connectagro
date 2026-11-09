"""Consulta (somente leitura) de Fertilizantes do catálogo técnico."""
from flask import abort, render_template, request

from ...models import ProdutoBase
from ...utils.auth import login_required
from ...utils.catalogo import (
    aplicar_filtros_catalogo,
    categorias_disponiveis,
    contexto_local_catalogo,
    parse_json_lista,
    primeiro_tecnico,
)
from ...utils.permissions import require_permission
from . import fertilizantes_bp

CLASSE = "fertilizante"
# Campos técnicos em lista exibidos no detalhe de fertilizantes.
CAMPOS_LISTA = ("nutrientes_principais", "culturas_comuns")


@fertilizantes_bp.route("/")
@login_required
@require_permission("catalogo.view")
def index():
    q = request.args.get("q") or None
    categoria = request.args.get("categoria") or None
    contexto = contexto_local_catalogo(CLASSE, q=q, categoria=categoria)
    propriedade = contexto["propriedade_catalogo"]
    produtos = aplicar_filtros_catalogo(CLASSE, q=q, categoria=categoria,
        propriedade_id=propriedade.id if propriedade else None).all()
    return render_template(
        "catalogo/list.html",
        titulo="Fertilizantes", endpoint="fertilizantes.detalhe",
        tipo="fertilizantes",
        produtos=produtos, q=q or "", categoria=categoria or "",
        categorias=sorted(set(categorias_disponiveis(CLASSE) + contexto["categorias_locais"])),
        **contexto)


@fertilizantes_bp.route("/<slug>")
@login_required
@require_permission("catalogo.view")
def detalhe(slug):
    produto = ProdutoBase.query.filter_by(slug=slug, classe=CLASSE).first()
    if produto is None:
        abort(404)
    tecnico = primeiro_tecnico(produto)
    listas = {campo: parse_json_lista(getattr(tecnico, campo, None))
              for campo in CAMPOS_LISTA} if tecnico else {}
    contexto = contexto_local_catalogo(CLASSE)
    return render_template(
        "catalogo/detail.html",
        titulo="Fertilizante", voltar_endpoint="fertilizantes.index",
        produto=produto, tecnico=tecnico, listas=listas, tipo="fertilizante", **contexto)
