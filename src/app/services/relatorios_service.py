"""Agregações somente leitura para os Relatórios Operacionais (Fase 6.2).

Todas as funções são de leitura e **escopadas pela propriedade atual**. Reutiliza
os helpers de consulta do ``dashboard_service`` para evitar duplicação. Nenhuma
função cria, altera ou remove dados.
"""
from collections import defaultdict
from datetime import date
from decimal import Decimal, InvalidOperation

from sqlalchemy import and_, or_
from sqlalchemy.orm import joinedload

from ..models import (
    AplicacaoInsumo,
    ColheitaRegistro,
    Cultura,
    EquipeMembro,
    FinanceiroLancamento,
    Gleba,
    ProdutoBase,
    UploadArquivo,
    Usuario,
    UsuarioPropriedade,
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
    """Exige datas civis ISO válidas antes de compará-las como texto."""
    for valor in (data_inicio, data_fim):
        if valor in (None, ""):
            continue
        try:
            if (not isinstance(valor, str) or len(valor) != 10
                    or date.fromisoformat(valor).isoformat() != valor):
                raise ValueError
        except (TypeError, ValueError):
            raise FiltroInvalidoError("Informe datas válidas no formato AAAA-MM-DD.") from None
    if data_inicio and data_fim and data_inicio > data_fim:
        raise FiltroInvalidoError("A data inicial não pode ser maior que a data final.")


def filtrar_por_periodo_query(query, campo_data, data_inicio=None, data_fim=None):
    """Aplica filtro de período a uma query (datas ISO comparáveis como texto)."""
    if data_inicio:
        query = query.filter(campo_data >= data_inicio)
    if data_fim:
        query = query.filter(campo_data <= data_fim)
    return query


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
        "glebas": [{"obj": g} for g in glebas],
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


class AreaRelatorioInacessivelError(LookupError):
    """Área inexistente ou fora do contexto, sem distinguir os dois casos."""


def decimal_operacional(valor):
    """Converte apenas números finitos, sem usar float para valores decimais."""
    if valor is None:
        return None
    try:
        numero = valor if isinstance(valor, Decimal) else Decimal(str(valor))
    except (InvalidOperation, ValueError, TypeError):
        return None
    return numero if numero.is_finite() else None


def formatar_decimal_operacional(valor, casas=None):
    """Exibe ausentes como ausentes e mantém a precisão do consumo informado."""
    numero = decimal_operacional(valor)
    if numero is None:
        return "—"
    texto = format(numero, f",.{casas}f" if casas is not None else ",f")
    if casas is None and "." in texto:
        texto = texto.rstrip("0").rstrip(".")
    return texto.replace(",", "_").replace(".", ",").replace("_", ".")


def _filtros_operacionais(propriedade, data_inicio, data_fim, gleba_id, tipo_atividade):
    validar_periodo(data_inicio, data_fim)
    area = None
    if gleba_id not in (None, ""):
        texto = str(gleba_id)
        if not texto.isascii() or not texto.isdigit() or len(texto) > 10:
            raise AreaRelatorioInacessivelError
        identificador = int(texto)
        if not 0 < identificador <= 2147483647:
            raise AreaRelatorioInacessivelError
        area = Gleba.query.filter_by(id=identificador, propriedade_id=propriedade.id).first()
        if area is None:
            raise AreaRelatorioInacessivelError
    tipo = (tipo_atividade or "").strip()
    if len(tipo) > 120:
        raise FiltroInvalidoError("A atividade deve ter no máximo 120 caracteres.")
    return area, tipo


def montar_relatorio_operacional(propriedade, data_inicio=None, data_fim=None,
                                gleba_id=None, tipo_atividade=None, *, incluir_custos=False):
    """Histórico consolidado sem sincronizar ou duplicar as duas fontes.

    O chamador determina ``incluir_custos`` pela permissão financeira atual.
    Sem ela, nem os DTOs contêm campos monetários. Consumos são agrupados por
    produto/unidade; custos informados não alteram lançamentos financeiros.
    """
    # Import local mantém explícita a dependência do modelo operacional.
    from ..models import AtividadeItem, AtividadeOperacional, CulturaGleba

    area, tipo = _filtros_operacionais(
        propriedade, data_inicio, data_fim, gleba_id, tipo_atividade)
    atividades_query = (AtividadeOperacional.query
                        .options(joinedload(AtividadeOperacional.gleba),
                                 joinedload(AtividadeOperacional.cultura_gleba)
                                 .joinedload(CulturaGleba.cultura))
                        .join(Gleba, AtividadeOperacional.gleba_id == Gleba.id)
                        .outerjoin(CulturaGleba, AtividadeOperacional.cultura_gleba_id == CulturaGleba.id)
                        .outerjoin(Cultura, CulturaGleba.cultura_id == Cultura.id)
                        .filter(Gleba.propriedade_id == propriedade.id,
                                or_(AtividadeOperacional.cultura_gleba_id.is_(None),
                                    and_(CulturaGleba.gleba_id == AtividadeOperacional.gleba_id,
                                         Cultura.propriedade_id == propriedade.id))))
    atividades_query = filtrar_por_periodo_query(
        atividades_query, AtividadeOperacional.data_execucao, data_inicio, data_fim)
    aplicacoes_query = filtrar_por_periodo_query(
        _aplicacoes_da_propriedade_query(propriedade).options(
            joinedload(AplicacaoInsumo.produto),
            joinedload(AplicacaoInsumo.cultura_gleba).joinedload(CulturaGleba.gleba),
            joinedload(AplicacaoInsumo.cultura_gleba).joinedload(CulturaGleba.cultura)),
        AplicacaoInsumo.data_aplicacao,
        data_inicio, data_fim)
    if area is not None:
        atividades_query = atividades_query.filter(AtividadeOperacional.gleba_id == area.id)
        aplicacoes_query = aplicacoes_query.filter(Gleba.id == area.id)
    if tipo:
        atividades_query = atividades_query.filter(AtividadeOperacional.tipo_atividade == tipo)
        if tipo != "Aplicação de insumo":
            aplicacoes_query = aplicacoes_query.filter(AplicacaoInsumo.id.is_(None))
    atividades = atividades_query.all()
    aplicacoes = aplicacoes_query.all()
    ids_atividades = [atividade.id for atividade in atividades]
    itens_por_atividade = defaultdict(list)
    if ids_atividades:
        for item in (AtividadeItem.query.options(joinedload(AtividadeItem.produto))
                     .filter(AtividadeItem.atividade_id.in_(ids_atividades))
                     .order_by(AtividadeItem.id).all()):
            itens_por_atividade[item.atividade_id].append(item)

    # Nomes de contas são operacionais, sem e-mail/perfil/equipe. Uma FK antiga
    # não concede acesso à identidade de uma conta fora do contexto atual.
    ids_usuarios = {getattr(obj, campo, None)
                   for obj in atividades + aplicacoes
                   for campo in ("criado_por_id", "responsavel_usuario_id")}
    ids_usuarios.discard(None)
    nomes = {}
    if ids_usuarios:
        nomes = {usuario.id: usuario.nome for usuario in
                 Usuario.query.join(UsuarioPropriedade, UsuarioPropriedade.usuario_id == Usuario.id)
                 .filter(Usuario.id.in_(ids_usuarios), Usuario.ativo.is_(True),
                         UsuarioPropriedade.propriedade_id == propriedade.id,
                         UsuarioPropriedade.ativo.is_(True)).all()}

    def item_dto(item, aplicacao=False):
        produto = item.produto
        dto = {"produto_id": item.produto_base_id,
               "produto": produto.nome if produto else "Produto indisponível",
               "dose": decimal_operacional(item.dose),
               "unidade_dose": item.unidade if aplicacao else item.unidade_dose,
               "quantidade_utilizada": decimal_operacional(item.quantidade_utilizada),
               "unidade_quantidade": item.unidade_quantidade,
               "cancelado": False if aplicacao else bool(item.cancelado_em)}
        if incluir_custos:
            dto.update(custo_unitario=decimal_operacional(item.custo_unitario),
                       custo_total=decimal_operacional(item.custo_total),
                       moeda=item.moeda, origem_custo=item.origem_custo)
        return dto

    registros = []
    for atividade in atividades:
        associacao = atividade.cultura_gleba
        registros.append({
            "fonte": "atividade", "fonte_label": "Atividade", "id": atividade.id,
            "tipo_atividade": atividade.tipo_atividade,
            "data_execucao": atividade.data_execucao,
            "gleba_id": atividade.gleba_id, "gleba": atividade.gleba.nome,
            "cultura": associacao.cultura.nome if associacao else None,
            "responsavel": atividade.responsavel or nomes.get(atividade.responsavel_usuario_id),
            "autor": nomes.get(atividade.criado_por_id), "criado_em": atividade.criado_em,
            "observacao": atividade.observacao, "cancelado": bool(atividade.cancelado_em),
            "itens": [item_dto(item) for item in itens_por_atividade[atividade.id]],
        })
    for aplicacao in aplicacoes:
        associacao = aplicacao.cultura_gleba
        registros.append({
            "fonte": "aplicacao", "fonte_label": "Aplicação", "id": aplicacao.id,
            "tipo_atividade": "Aplicação de insumo", "data_execucao": aplicacao.data_aplicacao,
            "gleba_id": associacao.gleba_id, "gleba": associacao.gleba.nome,
            "cultura": associacao.cultura.nome,
            "responsavel": aplicacao.responsavel or nomes.get(aplicacao.responsavel_usuario_id),
            "autor": nomes.get(aplicacao.criado_por_id), "criado_em": aplicacao.criado_em,
            "observacao": aplicacao.observacao, "cancelado": False,
            "itens": [item_dto(aplicacao, aplicacao=True)],
        })
    registros.sort(key=lambda registro: (registro["data_execucao"], registro["fonte"], registro["id"]), reverse=True)
    consumo = {}
    custos = defaultdict(Decimal)
    custos_ausentes = 0
    for registro in registros:
        if registro["cancelado"]:
            continue
        for item in registro["itens"]:
            if item["cancelado"]:
                continue
            quantidade = item["quantidade_utilizada"]
            unidade = item["unidade_quantidade"]
            if quantidade is not None and unidade:
                chave = (item["produto_id"], unidade)
                if chave not in consumo:
                    consumo[chave] = {"produto_id": item["produto_id"], "produto": item["produto"],
                                      "unidade": unidade, "quantidade": Decimal(0)}
                consumo[chave]["quantidade"] += quantidade
            if incluir_custos:
                if item["custo_total"] is not None and item["moeda"]:
                    custos[item["moeda"]] += item["custo_total"]
                else:
                    custos_ausentes += 1
    dados = {"registros": registros, "total": len(registros),
             "total_ativos": sum(not registro["cancelado"] for registro in registros),
             "consumo": sorted(consumo.values(), key=lambda item: (item["produto"], item["unidade"], item["produto_id"])),
             "incluir_custos": bool(incluir_custos),
             "filtros": {"data_inicio": data_inicio or "", "data_fim": data_fim or "",
                         "gleba_id": str(area.id) if area else "", "tipo_atividade": tipo}}
    if incluir_custos:
        dados.update(custos_por_moeda=sorted(custos.items()), custos_ausentes=custos_ausentes)
    return dados
