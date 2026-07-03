"""Serviço de IA simulada operacional do MVP.

A IA desta etapa é baseada em regras simples e dados locais. Não usa LLM,
API externa, internet ou recomendação agronômica.
"""
from collections import defaultdict
import unicodedata

from sqlalchemy import or_

from ..extensions import db
from ..models import (
    AplicacaoInsumo,
    ColheitaRegistro,
    Cultura,
    CulturaGleba,
    FinanceiroLancamento,
    Gleba,
    IaInteracao,
    ProdutoBase,
    UploadArquivo,
)
from ..utils.formatters import formatar_area, formatar_moeda, formatar_numero, formatar_tamanho

STATUS_CULTURA = ("planejada", "em_andamento", "colhida", "cancelada")
STATUS_LABELS = {
    "planejada": "Planejadas",
    "em_andamento": "Em andamento",
    "colhida": "Colhidas",
    "cancelada": "Canceladas",
}
STATUS_BLOQUEADO = "bloqueado_historico"

INTENCOES = (
    ("financeiro", ("financeiro", "saldo", "receita", "despesa", "gasto", "dinheiro")),
    ("glebas", ("gleba", "glebas", "talhao", "talhoes", "area", "mapa")),
    ("culturas", ("cultura", "culturas", "plantio", "safra", "lavoura")),
    ("colheita", ("colheita", "producao", "produtividade", "safra colhida")),
    ("aplicacoes", ("aplicacao", "aplicacoes", "insumo", "insumos", "dose")),
    ("documentos", ("upload", "arquivo", "arquivos", "documento", "documentos", "anexo", "anexos")),
    ("catalogo", ("catalogo", "defensivo", "defensivos", "fertilizante", "fertilizantes", "produto", "produtos")),
    ("resumo", ("resumo", "visao geral", "geral", "situacao", "propriedade")),
)


def _normalizar_texto(texto):
    texto = unicodedata.normalize("NFKD", texto or "")
    texto = "".join(char for char in texto if not unicodedata.combining(char))
    return texto.lower().strip()


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


def classificar_intencao_simples(pergunta):
    """Classifica a pergunta por palavras-chave simples."""
    texto = _normalizar_texto(pergunta)
    for intencao, palavras in INTENCOES:
        if any(palavra in texto for palavra in palavras):
            return intencao
    return "ajuda"


def montar_contexto_operacional(propriedade):
    """Monta um contexto operacional somente leitura da propriedade atual."""
    glebas = Gleba.query.filter_by(propriedade_id=propriedade.id).all()
    culturas = Cultura.query.filter_by(propriedade_id=propriedade.id).all()
    lancamentos = FinanceiroLancamento.query.filter_by(propriedade_id=propriedade.id).all()
    colheitas = _colheitas_da_propriedade_query(propriedade).all()
    aplicacoes_query = _aplicacoes_da_propriedade_query(propriedade)
    aplicacoes = aplicacoes_query.all()
    uploads = UploadArquivo.query.filter_by(propriedade_id=propriedade.id).all()

    culturas_por_status = {status: 0 for status in STATUS_CULTURA}
    for cultura in culturas:
        if cultura.status in culturas_por_status:
            culturas_por_status[cultura.status] += 1

    receitas = sum(lancamento.valor for lancamento in lancamentos if lancamento.tipo == "receita")
    despesas = sum(lancamento.valor for lancamento in lancamentos if lancamento.tipo == "despesa")

    colheita_por_unidade = defaultdict(float)
    for colheita in colheitas:
        if colheita.quantidade is not None:
            colheita_por_unidade[colheita.unidade or "sem unidade"] += colheita.quantidade

    return {
        "glebas": {
            "total": len(glebas),
            "area_total": sum(gleba.area_ha or 0 for gleba in glebas),
            "sem_area": sum(1 for gleba in glebas if not gleba.area_ha),
        },
        "culturas": {
            "total": len(culturas),
            "por_status": culturas_por_status,
            "total_associacoes": _associacoes_da_propriedade_query(propriedade).count(),
        },
        "financeiro": {
            "receitas": receitas,
            "despesas": despesas,
            "saldo": receitas - despesas,
            "total_lancamentos": len(lancamentos),
            "ultimos": (FinanceiroLancamento.query
                         .filter_by(propriedade_id=propriedade.id)
                         .order_by(FinanceiroLancamento.data.desc(), FinanceiroLancamento.id.desc())
                         .limit(5)
                         .all()),
        },
        "colheita": {
            "total": len(colheitas),
            "por_unidade": sorted(colheita_por_unidade.items()),
            "ultimas": (_colheitas_da_propriedade_query(propriedade)
                         .order_by(ColheitaRegistro.data_colheita.desc(), ColheitaRegistro.id.desc())
                         .limit(5)
                         .all()),
        },
        "aplicacoes": {
            "total": len(aplicacoes),
            "ultimas": (aplicacoes_query
                         .order_by(AplicacaoInsumo.data_aplicacao.desc(), AplicacaoInsumo.id.desc())
                         .limit(5)
                         .all()),
        },
        "uploads": {
            "total": len(uploads),
            "tamanho_total": sum(arquivo.tamanho or 0 for arquivo in uploads),
            "ultimos": (UploadArquivo.query
                         .filter_by(propriedade_id=propriedade.id)
                         .order_by(UploadArquivo.enviado_em.desc(), UploadArquivo.id.desc())
                         .limit(5)
                         .all()),
        },
        "catalogo": {
            "defensivos": ProdutoBase.query.filter_by(classe="defensivo").count(),
            "fertilizantes": ProdutoBase.query.filter_by(classe="fertilizante").count(),
            "bloqueados": (ProdutoBase.query
                            .filter(or_(ProdutoBase.status_sistema == STATUS_BLOQUEADO,
                                        ProdutoBase.status_regulatorio == STATUS_BLOQUEADO))
                            .count()),
        },
    }


def gerar_alertas_operacionais(propriedade):
    """Gera alertas simples de dados incompletos para a propriedade atual."""
    contexto = montar_contexto_operacional(propriedade)
    alertas = []

    if contexto["glebas"]["total"] == 0:
        alertas.append("Nenhuma propriedade cadastrada ainda.")
    else:
        if contexto["glebas"]["sem_area"]:
            alertas.append(f"Existem {contexto['glebas']['sem_area']} propriedades sem área informada.")

    if contexto["culturas"]["total"] == 0:
        alertas.append("Nenhuma cultura cadastrada ainda.")
    elif contexto["culturas"]["total_associacoes"] == 0:
        alertas.append("Nenhuma associação cultura↔propriedade cadastrada ainda.")

    if contexto["financeiro"]["total_lancamentos"] == 0:
        alertas.append("Nenhum lançamento financeiro cadastrado.")
    if contexto["colheita"]["total"] == 0:
        alertas.append("Nenhum registro de colheita cadastrado.")
    if contexto["aplicacoes"]["total"] == 0:
        alertas.append("Nenhuma aplicação de insumo registrada.")
    if contexto["uploads"]["total"] == 0:
        alertas.append("Nenhum upload cadastrado. A IA não lê conteúdo de arquivos no MVP.")

    return alertas or ["Nenhum alerta operacional simples identificado nos dados atuais."]


def _linhas_alertas(propriedade):
    return [f"* {alerta}" for alerta in gerar_alertas_operacionais(propriedade)]


def _rodape_simulado():
    return "Importante: esta IA é simulada e fornece apenas apoio operacional."


def gerar_resumo_operacional(propriedade):
    contexto = montar_contexto_operacional(propriedade)
    linhas = [
        "Resumo operacional da propriedade",
        "",
        f"* Propriedades cadastradas: {contexto['glebas']['total']}",
        f"* Culturas cadastradas: {contexto['culturas']['total']}",
        f"* Saldo financeiro: {formatar_moeda(contexto['financeiro']['saldo'])}",
        f"* Registros de colheita: {contexto['colheita']['total']}",
        f"* Aplicações registradas: {contexto['aplicacoes']['total']}",
        f"* Uploads cadastrados: {contexto['uploads']['total']}",
        "",
        "Alertas:",
        *_linhas_alertas(propriedade),
        "",
        _rodape_simulado(),
    ]
    return "\n".join(linhas)


def _responder_financeiro(propriedade):
    financeiro = montar_contexto_operacional(propriedade)["financeiro"]
    linhas = [
        "Resumo financeiro",
        "",
        f"* Receitas: {formatar_moeda(financeiro['receitas'])}",
        f"* Despesas: {formatar_moeda(financeiro['despesas'])}",
        f"* Saldo: {formatar_moeda(financeiro['saldo'])}",
        f"* Lançamentos cadastrados: {financeiro['total_lancamentos']}",
    ]
    if financeiro["total_lancamentos"] == 0:
        linhas.append("* Ainda não há lançamentos financeiros cadastrados.")
    linhas.extend(["", _rodape_simulado()])
    return "\n".join(linhas)


def _responder_glebas(propriedade):
    glebas = montar_contexto_operacional(propriedade)["glebas"]
    linhas = [
        "Resumo de propriedades",
        "",
        f"* Propriedades cadastradas: {glebas['total']}",
        f"* Área total informada: {formatar_area(glebas['area_total'])}",
        f"* Propriedades sem área informada: {glebas['sem_area']}",
        "",
        _rodape_simulado(),
    ]
    return "\n".join(linhas)


def _responder_culturas(propriedade):
    culturas = montar_contexto_operacional(propriedade)["culturas"]
    linhas = ["Resumo de culturas", "", f"* Culturas cadastradas: {culturas['total']}"]
    for status, total in culturas["por_status"].items():
        linhas.append(f"* {STATUS_LABELS[status]}: {total}")
    linhas.append(f"* Associações cultura↔propriedade: {culturas['total_associacoes']}")
    if culturas["total"] and culturas["total_associacoes"] == 0:
        linhas.append("* Há culturas cadastradas sem associação cultura↔propriedade.")
    elif culturas["total"] == 0:
        linhas.append("* Ainda não há culturas cadastradas.")
    linhas.extend(["", _rodape_simulado()])
    return "\n".join(linhas)


def _responder_colheita(propriedade):
    colheita = montar_contexto_operacional(propriedade)["colheita"]
    linhas = ["Resumo de colheita", "", f"* Registros de colheita: {colheita['total']}"]
    if colheita["por_unidade"]:
        linhas.append("* Soma por unidade:")
        for unidade, total in colheita["por_unidade"]:
            linhas.append(f"  - {formatar_numero(total)} {unidade}")
    else:
        linhas.append("* Ainda não há quantidades de colheita informadas.")
    if colheita["ultimas"]:
        linhas.append("* Últimas colheitas:")
        for item in colheita["ultimas"]:
            cultura = item.cultura_gleba.cultura.nome
            gleba = item.cultura_gleba.gleba.nome
            quantidade = formatar_numero(item.quantidade) if item.quantidade is not None else "sem quantidade"
            unidade = item.unidade or ""
            linhas.append(f"  - {item.data_colheita}: {cultura} / {gleba} — {quantidade} {unidade}".strip())
    linhas.extend(["", _rodape_simulado()])
    return "\n".join(linhas)


def _responder_aplicacoes(propriedade):
    aplicacoes = montar_contexto_operacional(propriedade)["aplicacoes"]
    linhas = [
        "Resumo de aplicações de insumo",
        "",
        f"* Aplicações registradas: {aplicacoes['total']}",
    ]
    if aplicacoes["ultimas"]:
        linhas.append("* Últimas aplicações:")
        for item in aplicacoes["ultimas"]:
            produto = item.produto.nome
            cultura = item.cultura_gleba.cultura.nome
            gleba = item.cultura_gleba.gleba.nome
            dose = ""
            if item.dose is not None:
                dose = f" — {formatar_numero(item.dose)} {item.unidade or ''}".rstrip()
            linhas.append(f"  - {item.data_aplicacao}: {produto} em {cultura} / {gleba}{dose}")
    else:
        linhas.append("* Ainda não há aplicações registradas.")
    linhas.extend([
        "",
        "Aplicações são registros históricos operacionais. O ConnectAgro não recomenda produtos e não valida dose.",
        _rodape_simulado(),
    ])
    return "\n".join(linhas)


def _responder_documentos(propriedade):
    uploads = montar_contexto_operacional(propriedade)["uploads"]
    linhas = [
        "Resumo de documentos",
        "",
        f"* Arquivos cadastrados: {uploads['total']}",
        f"* Tamanho total armazenado: {formatar_tamanho(uploads['tamanho_total'])}",
    ]
    if uploads["ultimos"]:
        linhas.append("* Últimos arquivos:")
        for arquivo in uploads["ultimos"]:
            linhas.append(f"  - {arquivo.nome_original} ({formatar_tamanho(arquivo.tamanho)})")
    else:
        linhas.append("* Ainda não há uploads cadastrados.")
    linhas.extend(["", "A IA não lê o conteúdo dos arquivos enviados no MVP.", _rodape_simulado()])
    return "\n".join(linhas)


def _responder_catalogo(propriedade):
    catalogo = montar_contexto_operacional(propriedade)["catalogo"]
    linhas = [
        "Resumo do catálogo",
        "",
        f"* Defensivos cadastrados: {catalogo['defensivos']}",
        f"* Fertilizantes cadastrados: {catalogo['fertilizantes']}",
        f"* Produtos bloqueados/históricos: {catalogo['bloqueados']}",
        "",
        "O catálogo é base técnica inicial de consulta. O ConnectAgro não vende produtos e o status regulatório não representa validação oficial automática.",
        _rodape_simulado(),
    ]
    return "\n".join(linhas)


def _responder_ajuda(propriedade):
    return "\n".join([
        "Não entendi totalmente a pergunta.",
        "",
        "Posso ajudar com estes temas:",
        "* resumo",
        "* financeiro",
        "* propriedades",
        "* culturas",
        "* colheita",
        "* aplicações",
        "* documentos",
        "* catálogo",
        "",
        _rodape_simulado(),
    ])


def responder_pergunta_simulada(propriedade, pergunta):
    """Gera resposta simulada por regras e dados locais da propriedade."""
    intencao = classificar_intencao_simples(pergunta)
    respostas = {
        "resumo": gerar_resumo_operacional,
        "financeiro": _responder_financeiro,
        "glebas": _responder_glebas,
        "culturas": _responder_culturas,
        "colheita": _responder_colheita,
        "aplicacoes": _responder_aplicacoes,
        "documentos": _responder_documentos,
        "catalogo": _responder_catalogo,
        "ajuda": _responder_ajuda,
    }
    return respostas[intencao](propriedade)


def registrar_interacao_ia(usuario, propriedade, pergunta, resposta, tipo="simulada"):
    """Persiste a interação da IA simulada para o usuário/propriedade atuais."""
    usuario_id = usuario["id"] if isinstance(usuario, dict) else usuario.id
    interacao = IaInteracao(
        usuario_id=usuario_id,
        propriedade_id=propriedade.id,
        pergunta=pergunta,
        resposta=resposta,
        tipo=tipo,
    )
    db.session.add(interacao)
    db.session.commit()
    return interacao


def listar_interacoes_ia(usuario, propriedade, limite=10):
    """Lista o histórico da IA apenas do usuário e propriedade atuais."""
    usuario_id = usuario["id"] if isinstance(usuario, dict) else usuario.id
    return (IaInteracao.query
            .filter_by(usuario_id=usuario_id, propriedade_id=propriedade.id)
            .order_by(IaInteracao.criado_em.desc(), IaInteracao.id.desc())
            .limit(limite)
            .all())
