"""Agregações somente leitura para o Dashboard Operacional."""
from collections import defaultdict

from sqlalchemy import or_

from ..models import (
    AplicacaoInsumo,
    ColheitaRegistro,
    Cultura,
    CulturaGleba,
    EquipeMembro,
    FinanceiroLancamento,
    Gleba,
    ProdutoBase,
    UploadArquivo,
)

STATUS_CULTURA = ("planejada", "em_andamento", "colhida", "cancelada")
STATUS_BLOQUEADO = "bloqueado_historico"


def _associacoes_da_propriedade_query(propriedade):
    return (CulturaGleba.query
            .join(Cultura, CulturaGleba.cultura_id == Cultura.id)
            .join(Gleba, CulturaGleba.gleba_id == Gleba.id)
            .filter(Cultura.propriedade_id == propriedade.id,
                    Gleba.propriedade_id == propriedade.id))


def _colheitas_da_propriedade_query(propriedade):
    return (ColheitaRegistro.query
            .join(CulturaGleba, ColheitaRegistro.cultura_gleba_id == CulturaGleba.id)
            .join(Cultura, CulturaGleba.cultura_id == Cultura.id)
            .join(Gleba, CulturaGleba.gleba_id == Gleba.id)
            .filter(Cultura.propriedade_id == propriedade.id,
                    Gleba.propriedade_id == propriedade.id))


def _aplicacoes_da_propriedade_query(propriedade):
    return (AplicacaoInsumo.query
            .join(CulturaGleba, AplicacaoInsumo.cultura_gleba_id == CulturaGleba.id)
            .join(Cultura, CulturaGleba.cultura_id == Cultura.id)
            .join(Gleba, CulturaGleba.gleba_id == Gleba.id)
            .filter(Cultura.propriedade_id == propriedade.id,
                    Gleba.propriedade_id == propriedade.id))


def _resumo_glebas(propriedade):
    glebas = Gleba.query.filter_by(propriedade_id=propriedade.id).all()
    return {
        "total": len(glebas),
        "area_total": sum(g.area_ha or 0 for g in glebas),
        "sem_area": sum(1 for g in glebas if not g.area_ha),
    }


def _resumo_culturas(propriedade):
    culturas = Cultura.query.filter_by(propriedade_id=propriedade.id).all()
    por_status = {status: 0 for status in STATUS_CULTURA}
    for cultura in culturas:
        if cultura.status in por_status:
            por_status[cultura.status] += 1
    return {
        "total": len(culturas),
        "por_status": por_status,
        "total_associacoes": _associacoes_da_propriedade_query(propriedade).count(),
    }


def _resumo_financeiro(propriedade):
    lancamentos = (FinanceiroLancamento.query
                   .filter_by(propriedade_id=propriedade.id)
                   .all())
    receitas = sum(l.valor for l in lancamentos if l.tipo == "receita")
    despesas = sum(l.valor for l in lancamentos if l.tipo == "despesa")
    ultimos = (FinanceiroLancamento.query
               .filter_by(propriedade_id=propriedade.id)
               .order_by(FinanceiroLancamento.data.desc(), FinanceiroLancamento.id.desc())
               .limit(5)
               .all())
    return {
        "receitas": receitas,
        "despesas": despesas,
        "saldo": receitas - despesas,
        "total_lancamentos": len(lancamentos),
        "ultimos": ultimos,
    }


def _resumo_equipe(propriedade):
    membros = EquipeMembro.query.filter_by(propriedade_id=propriedade.id).all()
    ativos = sum(1 for membro in membros if membro.ativo)
    return {"total": len(membros), "ativos": ativos, "inativos": len(membros) - ativos}


def _resumo_colheita(propriedade):
    colheitas = _colheitas_da_propriedade_query(propriedade).all()
    por_unidade = defaultdict(float)
    for colheita in colheitas:
        if colheita.quantidade is not None:
            por_unidade[colheita.unidade or "sem unidade"] += colheita.quantidade
    ultimas = (_colheitas_da_propriedade_query(propriedade)
               .order_by(ColheitaRegistro.data_colheita.desc(), ColheitaRegistro.id.desc())
               .limit(5)
               .all())
    return {
        "total": len(colheitas),
        "por_unidade": sorted(por_unidade.items()),
        "ultimas": ultimas,
    }


def _resumo_aplicacoes(propriedade):
    query = _aplicacoes_da_propriedade_query(propriedade)
    return {
        "total": query.count(),
        "ultimas": (query
                     .order_by(AplicacaoInsumo.data_aplicacao.desc(), AplicacaoInsumo.id.desc())
                     .limit(5)
                     .all()),
    }


def _resumo_uploads(propriedade):
    arquivos = UploadArquivo.query.filter_by(propriedade_id=propriedade.id).all()
    ultimos = (UploadArquivo.query
               .filter_by(propriedade_id=propriedade.id)
               .order_by(UploadArquivo.enviado_em.desc(), UploadArquivo.id.desc())
               .limit(5)
               .all())
    return {
        "total": len(arquivos),
        "tamanho_total": sum(arquivo.tamanho or 0 for arquivo in arquivos),
        "ultimos": ultimos,
    }


def _resumo_catalogo():
    return {
        "defensivos": ProdutoBase.query.filter_by(classe="defensivo").count(),
        "fertilizantes": ProdutoBase.query.filter_by(classe="fertilizante").count(),
        "bloqueados": (ProdutoBase.query
                        .filter(or_(ProdutoBase.status_sistema == STATUS_BLOQUEADO,
                                    ProdutoBase.status_regulatorio == STATUS_BLOQUEADO))
                        .count()),
    }


def montar_dashboard_operacional(propriedade):
    """Monta o resumo operacional da propriedade atual sem alterar dados."""
    return {
        "glebas": _resumo_glebas(propriedade),
        "culturas": _resumo_culturas(propriedade),
        "financeiro": _resumo_financeiro(propriedade),
        "equipe": _resumo_equipe(propriedade),
        "colheita": _resumo_colheita(propriedade),
        "aplicacoes": _resumo_aplicacoes(propriedade),
        "uploads": _resumo_uploads(propriedade),
        "catalogo": _resumo_catalogo(),
    }
