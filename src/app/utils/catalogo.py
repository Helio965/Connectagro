"""Helpers de consulta (somente leitura) do catálogo de produtos.

O catálogo é base técnica de consulta — o ConnectAgro **não vende** produtos.
Estes helpers são compartilhados pelos módulos Defensivos e Fertilizantes.
"""
import json

from ..models import ProdutoBase, ProdutoTecnico


def parse_json_lista(valor):
    """Converte um campo TEXT/JSON em lista para exibição amigável.

    Retorna lista de strings. Em JSON inválido/vazio, faz fallback seguro:
    string não-JSON vira ``[valor]``; vazio/None vira ``[]``.
    """
    if not valor:
        return []
    if isinstance(valor, (list, tuple)):
        return [str(v) for v in valor]
    try:
        dados = json.loads(valor)
    except (ValueError, TypeError):
        return [str(valor)]
    if isinstance(dados, list):
        return [str(v) for v in dados]
    return [str(dados)]


def aplicar_filtros_catalogo(classe, q=None, categoria=None, status_regulatorio=None):
    """Monta a query de `ProdutoBase` da classe, com busca/filtros opcionais."""
    query = ProdutoBase.query.filter(ProdutoBase.classe == classe)
    if q:
        termo = f"%{q.strip()}%"
        query = query.filter(db_or(
            ProdutoBase.nome.ilike(termo),
            ProdutoBase.categoria.ilike(termo),
            ProdutoBase.descricao_curta.ilike(termo),
            ProdutoBase.descricao_completa.ilike(termo),
        ))
    if categoria:
        query = query.filter(ProdutoBase.categoria == categoria)
    if status_regulatorio:
        query = query.filter(ProdutoBase.status_regulatorio == status_regulatorio)
    return query.order_by(ProdutoBase.nome)


def db_or(*clauses):
    """Pequeno wrapper para `sqlalchemy.or_` (evita import direto nas rotas)."""
    from sqlalchemy import or_
    return or_(*clauses)


def _valores_distintos(classe, coluna):
    valores = (ProdutoBase.query
               .with_entities(coluna)
               .filter(ProdutoBase.classe == classe, coluna.isnot(None))
               .distinct()
               .order_by(coluna)
               .all())
    return [v[0] for v in valores if v[0]]


def categorias_disponiveis(classe):
    """Categorias distintas existentes para a classe (para o filtro)."""
    return _valores_distintos(classe, ProdutoBase.categoria)


def status_disponiveis(classe):
    """Valores de status_regulatorio distintos para a classe (para o filtro)."""
    return _valores_distintos(classe, ProdutoBase.status_regulatorio)


def primeiro_tecnico(produto):
    """Retorna o primeiro `ProdutoTecnico` do produto, ou ``None``."""
    return (ProdutoTecnico.query
            .filter_by(produto_id=produto.id)
            .first())
