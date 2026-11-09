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


def aplicar_filtros_catalogo(classe, q=None, categoria=None, status_regulatorio=None,
                            propriedade_id=None):
    """Monta a query de `ProdutoBase` da classe, com busca/filtros opcionais."""
    query = ProdutoBase.query.filter(ProdutoBase.classe == classe)
    if q:
        termo = f"%{q.strip()}%"
        condicoes = [
            ProdutoBase.nome.ilike(termo),
            ProdutoBase.categoria.ilike(termo),
            ProdutoBase.descricao_curta.ilike(termo),
            ProdutoBase.descricao_completa.ilike(termo),
        ]
        if propriedade_id is not None:
            # O ID é derivado do contexto autorizado pelas rotas, nunca de args.
            from sqlalchemy import select
            from ..models import ProdutoPersonalizacao
            alias_local = select(ProdutoPersonalizacao.produto_base_id).where(
                ProdutoPersonalizacao.propriedade_id == propriedade_id,
                ProdutoPersonalizacao.ativo.is_(True),
                db_or(ProdutoPersonalizacao.nome_local.ilike(termo),
                      ProdutoPersonalizacao.descricao_local.ilike(termo)))
            condicoes.append(ProdutoBase.id.in_(alias_local))
        query = query.filter(db_or(*condicoes))
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


def contexto_local_catalogo(classe, q=None, categoria=None):
    """Complementos da Propriedade autorizada, sem modificar dados globais.

    A consulta global permanece disponível quando não há contexto. Retornar
    registros locais exige o vínculo validado pelo resolvedor existente.
    """
    from ..models import ProdutoLocal, ProdutoPersonalizacao
    from .contexto import propriedade_atual

    propriedade = propriedade_atual()
    dados = {"propriedade_catalogo": propriedade, "personalizacoes": {},
             "personalizacoes_existentes": {}, "produtos_locais": [],
             "categorias_locais": []}
    if propriedade is None:
        return dados
    personalizados = (ProdutoPersonalizacao.query
        .join(ProdutoBase, ProdutoPersonalizacao.produto_base_id == ProdutoBase.id)
        .filter(ProdutoPersonalizacao.propriedade_id == propriedade.id,
                ProdutoBase.classe == classe).all())
    dados["personalizacoes_existentes"] = {p.produto_base_id: p for p in personalizados}
    dados["personalizacoes"] = {p.produto_base_id: p for p in personalizados if p.ativo}
    locais = ProdutoLocal.query.filter_by(propriedade_id=propriedade.id,
                                         classe=classe, ativo=True)
    dados["categorias_locais"] = [c[0] for c in locais.with_entities(ProdutoLocal.categoria)
                                   .filter(ProdutoLocal.categoria.isnot(None))
                                   .distinct().all() if c[0]]
    if q:
        termo = f"%{q.strip()}%"
        locais = locais.filter(db_or(ProdutoLocal.nome.ilike(termo),
            ProdutoLocal.categoria.ilike(termo), ProdutoLocal.descricao_curta.ilike(termo),
            ProdutoLocal.descricao_completa.ilike(termo)))
    if categoria:
        locais = locais.filter(ProdutoLocal.categoria == categoria)
    dados["produtos_locais"] = locais.order_by(ProdutoLocal.nome, ProdutoLocal.id).all()
    return dados
