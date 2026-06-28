"""Agregações somente leitura para os Relatórios Operacionais (Fase 6.2).

Todas as funções são de leitura e **escopadas pela propriedade atual**. Reutiliza
os helpers de consulta do ``dashboard_service`` para evitar duplicação. Nenhuma
função cria, altera ou remove dados.
"""
from collections import defaultdict

from ..models import (
    AplicacaoInsumo,
    ColheitaRegistro,
    Cultura,
    EquipeMembro,
    FinanceiroLancamento,
    Gleba,
    ProdutoBase,
    UploadArquivo,
)
from .dashboard_service import (
    _aplicacoes_da_propriedade_query,
    _associacoes_da_propriedade_query,
    _colheitas_da_propriedade_query,
)

STATUS_CULTURA = ("planejada", "em_andamento", "colhida", "cancelada")
TIPOS_FINANCEIRO = ("receita", "despesa")
CLASSES_PRODUTO = ("defensivo", "fertilizante")


class FiltroInvalidoError(ValueError):
    """Erro de filtro inválido em relatório (período, tipo ou classe)."""


# ---------------------------------------------------------------------------
# Helpers de filtro
# ---------------------------------------------------------------------------

def validar_periodo(data_inicio, data_fim):
    """Valida um período (datas ISO ``yyyy-mm-dd`` como texto).

    Lança ``FiltroInvalidoError`` se ``data_inicio > data_fim``.
    """
    if data_inicio and data_fim and data_inicio > data_fim:
        raise FiltroInvalidoError("A data inicial não pode ser maior que a data final.")


def filtrar_por_periodo_query(query, campo_data, data_inicio=None, data_fim=None):
    """Aplica filtro de período a uma query (datas ISO comparáveis como texto)."""
    if data_inicio:
        query = query.filter(campo_data >= data_inicio)
    if data_fim:
        query = query.filter(campo_data <= data_fim)
    return query


def _coordenada_valida(gleba):
    return (gleba.latitude is not None and gleba.longitude is not None
            and -90 <= gleba.latitude <= 90 and -180 <= gleba.longitude <= 180)


# ---------------------------------------------------------------------------
# Relatório Geral
# ---------------------------------------------------------------------------

def montar_relatorio_geral(propriedade):
    glebas = Gleba.query.filter_by(propriedade_id=propriedade.id).all()
    culturas = Cultura.query.filter_by(propriedade_id=propriedade.id).all()
    por_status = {s: 0 for s in STATUS_CULTURA}
    for c in culturas:
        if c.status in por_status:
            por_status[c.status] += 1

    membros = EquipeMembro.query.filter_by(propriedade_id=propriedade.id).all()
    ativos = sum(1 for m in membros if m.ativo)

    lancamentos = FinanceiroLancamento.query.filter_by(propriedade_id=propriedade.id).all()
    receitas = sum(l.valor for l in lancamentos if l.tipo == "receita")
    despesas = sum(l.valor for l in lancamentos if l.tipo == "despesa")

    colheitas = _colheitas_da_propriedade_query(propriedade).all()
    por_unidade = defaultdict(float)
    for col in colheitas:
        if col.quantidade is not None:
            por_unidade[col.unidade or "sem unidade"] += col.quantidade

    arquivos = UploadArquivo.query.filter_by(propriedade_id=propriedade.id).all()

    return {
        "propriedade": propriedade,
        "glebas": {
            "total": len(glebas),
            "area_total": sum(g.area_ha or 0 for g in glebas),
            "sem_area": sum(1 for g in glebas if not g.area_ha),
            "sem_coordenadas": sum(1 for g in glebas if not _coordenada_valida(g)),
        },
        "culturas": {
            "total": len(culturas),
            "por_status": por_status,
            "total_associacoes": _associacoes_da_propriedade_query(propriedade).count(),
        },
        "equipe": {"total": len(membros), "ativos": ativos,
                   "inativos": len(membros) - ativos},
        "financeiro": {"receitas": receitas, "despesas": despesas,
                       "saldo": receitas - despesas,
                       "total_lancamentos": len(lancamentos)},
        "colheita": {"total": len(colheitas),
                     "por_unidade": sorted(por_unidade.items())},
        "aplicacoes": {"total": _aplicacoes_da_propriedade_query(propriedade).count()},
        "uploads": {"total": len(arquivos),
                    "tamanho_total": sum(a.tamanho or 0 for a in arquivos)},
        "catalogo": {
            "defensivos": ProdutoBase.query.filter_by(classe="defensivo").count(),
            "fertilizantes": ProdutoBase.query.filter_by(classe="fertilizante").count(),
        },
    }


# ---------------------------------------------------------------------------
# Relatório Financeiro
# ---------------------------------------------------------------------------

def montar_relatorio_financeiro(propriedade, data_inicio=None, data_fim=None, tipo=None):
    if tipo in (None, "", "todos"):
        tipo = None
    elif tipo not in TIPOS_FINANCEIRO:
        raise FiltroInvalidoError("Tipo inválido: use receita, despesa ou todos.")
    validar_periodo(data_inicio, data_fim)

    query = FinanceiroLancamento.query.filter_by(propriedade_id=propriedade.id)
    query = filtrar_por_periodo_query(query, FinanceiroLancamento.data, data_inicio, data_fim)
    if tipo:
        query = query.filter(FinanceiroLancamento.tipo == tipo)
    lancamentos = query.order_by(FinanceiroLancamento.data.desc(),
                                 FinanceiroLancamento.id.desc()).all()

    receitas = sum(l.valor for l in lancamentos if l.tipo == "receita")
    despesas = sum(l.valor for l in lancamentos if l.tipo == "despesa")
    return {
        "lancamentos": lancamentos,
        "receitas": receitas,
        "despesas": despesas,
        "saldo": receitas - despesas,
        "quantidade": len(lancamentos),
        "filtros": {"data_inicio": data_inicio or "", "data_fim": data_fim or "",
                    "tipo": tipo or "todos"},
    }


# ---------------------------------------------------------------------------
# Relatório Agrícola
# ---------------------------------------------------------------------------

def montar_relatorio_agricola(propriedade):
    glebas = (Gleba.query.filter_by(propriedade_id=propriedade.id)
              .order_by(Gleba.nome).all())
    culturas = (Cultura.query.filter_by(propriedade_id=propriedade.id)
                .order_by(Cultura.nome).all())
    associacoes = (_associacoes_da_propriedade_query(propriedade)
                   .order_by(Cultura.nome).all())
    colheitas = (_colheitas_da_propriedade_query(propriedade)
                 .order_by(ColheitaRegistro.data_colheita.desc()).all())

    por_unidade = defaultdict(float)
    for col in colheitas:
        if col.quantidade is not None:
            por_unidade[col.unidade or "sem unidade"] += col.quantidade

    return {
        "glebas": [{"obj": g, "coordenada_valida": _coordenada_valida(g)} for g in glebas],
        "culturas": culturas,
        "associacoes": associacoes,
        "colheitas": colheitas,
        "total_colheitas": len(colheitas),
        "colheita_por_unidade": sorted(por_unidade.items()),
    }


# ---------------------------------------------------------------------------
# Relatório de Aplicações de Insumo
# ---------------------------------------------------------------------------

def montar_relatorio_aplicacoes(propriedade, data_inicio=None, data_fim=None, classe=None):
    if classe in (None, "", "todos"):
        classe = None
    elif classe not in CLASSES_PRODUTO:
        raise FiltroInvalidoError("Classe inválida: use defensivo, fertilizante ou todos.")
    validar_periodo(data_inicio, data_fim)

    query = _aplicacoes_da_propriedade_query(propriedade)
    query = filtrar_por_periodo_query(query, AplicacaoInsumo.data_aplicacao,
                                      data_inicio, data_fim)
    if classe:
        query = (query.join(ProdutoBase, AplicacaoInsumo.produto_base_id == ProdutoBase.id)
                 .filter(ProdutoBase.classe == classe))
    aplicacoes = query.order_by(AplicacaoInsumo.data_aplicacao.desc(),
                                AplicacaoInsumo.id.desc()).all()
    return {
        "aplicacoes": aplicacoes,
        "total": len(aplicacoes),
        "filtros": {"data_inicio": data_inicio or "", "data_fim": data_fim or "",
                    "classe": classe or "todos"},
    }


# ---------------------------------------------------------------------------
# Relatório de Uploads
# ---------------------------------------------------------------------------

def montar_relatorio_uploads(propriedade):
    arquivos = (UploadArquivo.query.filter_by(propriedade_id=propriedade.id)
                .order_by(UploadArquivo.enviado_em.desc(), UploadArquivo.id.desc())
                .all())
    return {
        "arquivos": arquivos,
        "total": len(arquivos),
        "tamanho_total": sum(a.tamanho or 0 for a in arquivos),
    }
