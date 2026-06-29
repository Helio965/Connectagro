"""Relatórios Operacionais HTML (somente leitura) — escopo: propriedade atual.

Não criam, alteram ou removem dados. Sem PDF/exportação nesta fase; a impressão
é feita pelo navegador (``window.print()``).
"""
from flask import abort, flash, render_template, request

from ...utils.auth import login_required
from ...utils.contexto import propriedade_atual, vazio_para_none
from ...utils.formatters import (
    formatar_area,
    formatar_moeda,
    formatar_numero,
    formatar_tamanho,
)
from ...utils.permissions import require_permission
from ...services.auditoria_service import registrar_falha, registrar_sucesso
from ...services.exportacoes_service import (
    gerar_csv_relatorio_agricola,
    gerar_csv_relatorio_aplicacoes,
    gerar_csv_relatorio_financeiro,
    gerar_csv_relatorio_geral,
    gerar_csv_relatorio_uploads,
    gerar_pdf_relatorio_agricola,
    gerar_pdf_relatorio_aplicacoes,
    gerar_pdf_relatorio_financeiro,
    gerar_pdf_relatorio_geral,
    gerar_pdf_relatorio_uploads,
    nome_arquivo,
    resposta_csv,
    resposta_pdf,
)
from ...services.relatorios_service import (
    FiltroInvalidoError,
    montar_relatorio_agricola,
    montar_relatorio_aplicacoes,
    montar_relatorio_financeiro,
    montar_relatorio_geral,
    montar_relatorio_uploads,
)
from . import relatorios_bp

_NOMES_RELATORIO = {
    "geral": "geral", "financeiro": "financeiro", "agricola": "agrícola",
    "aplicacoes": "aplicações", "uploads": "uploads",
}


def _auditar_exportacao(slug, formato, propriedade):
    registrar_sucesso(
        "exportacao.gerada", entidade="relatorio", entidade_id=slug,
        descricao=f"Exportação {formato.upper()} do relatório {_NOMES_RELATORIO[slug]}",
        propriedade_id=propriedade.id, request=request)


def _falha_exportacao(slug, formato, propriedade, erro):
    registrar_falha(
        "exportacao.falha", entidade="relatorio", entidade_id=slug,
        descricao=f"Filtro inválido na exportação {formato.upper()} de {slug}",
        propriedade_id=propriedade.id, request=request)
    flash(str(erro), "error")
    abort(400)

# Formatadores disponibilizados aos templates de relatórios.
FMT = {
    "formatar_area": formatar_area,
    "formatar_moeda": formatar_moeda,
    "formatar_numero": formatar_numero,
    "formatar_tamanho": formatar_tamanho,
}


@relatorios_bp.route("/")
@login_required
@require_permission("relatorios.view")
def index():
    propriedade = propriedade_atual()
    # Auditamos apenas o acesso à central de relatórios (decisão: evitar ruído
    # de auditoria a cada sub-relatório/GET).
    registrar_sucesso("relatorios.view", entidade="relatorios",
                      descricao="Acesso à central de relatórios",
                      propriedade_id=propriedade.id, request=request)
    return render_template("relatorios/index.html", propriedade=propriedade, **FMT)


@relatorios_bp.route("/geral")
@login_required
@require_permission("relatorios.view")
def geral():
    propriedade = propriedade_atual()
    dados = montar_relatorio_geral(propriedade)
    return render_template("relatorios/geral.html", propriedade=propriedade, dados=dados, **FMT)


@relatorios_bp.route("/financeiro")
@login_required
@require_permission("relatorios.view")
def financeiro():
    propriedade = propriedade_atual()
    data_inicio = vazio_para_none(request.args.get("data_inicio"))
    data_fim = vazio_para_none(request.args.get("data_fim"))
    tipo = vazio_para_none(request.args.get("tipo"))
    try:
        dados = montar_relatorio_financeiro(propriedade, data_inicio, data_fim, tipo)
    except FiltroInvalidoError as erro:
        flash(str(erro), "error")
        return render_template(
            "relatorios/financeiro.html", propriedade=propriedade, dados=None,
            filtros={"data_inicio": data_inicio or "", "data_fim": data_fim or "",
                     "tipo": tipo or "todos"}, **FMT), 400
    return render_template("relatorios/financeiro.html", propriedade=propriedade,
                           dados=dados, filtros=dados["filtros"], **FMT)


@relatorios_bp.route("/agricola")
@login_required
@require_permission("relatorios.view")
def agricola():
    propriedade = propriedade_atual()
    dados = montar_relatorio_agricola(propriedade)
    return render_template("relatorios/agricola.html", propriedade=propriedade, dados=dados, **FMT)


@relatorios_bp.route("/aplicacoes")
@login_required
@require_permission("relatorios.view")
def aplicacoes():
    propriedade = propriedade_atual()
    data_inicio = vazio_para_none(request.args.get("data_inicio"))
    data_fim = vazio_para_none(request.args.get("data_fim"))
    classe = vazio_para_none(request.args.get("classe"))
    try:
        dados = montar_relatorio_aplicacoes(propriedade, data_inicio, data_fim, classe)
    except FiltroInvalidoError as erro:
        flash(str(erro), "error")
        return render_template(
            "relatorios/aplicacoes.html", propriedade=propriedade, dados=None,
            filtros={"data_inicio": data_inicio or "", "data_fim": data_fim or "",
                     "classe": classe or "todos"}, **FMT), 400
    return render_template("relatorios/aplicacoes.html", propriedade=propriedade,
                           dados=dados, filtros=dados["filtros"], **FMT)


@relatorios_bp.route("/uploads")
@login_required
@require_permission("relatorios.view")
def uploads():
    propriedade = propriedade_atual()
    dados = montar_relatorio_uploads(propriedade)
    return render_template("relatorios/uploads.html", propriedade=propriedade, dados=dados, **FMT)


# ---------------------------------------------------------------------------
# Exportações (Fase 7.4) — CSV (biblioteca padrão) e PDF (ReportLab), em memória.
# Reaproveitam os mesmos serviços e filtros dos relatórios HTML, exigem
# `relatorios.view`, são escopadas pela propriedade atual e geram auditoria.
# ---------------------------------------------------------------------------

def _filtros_financeiro():
    return (vazio_para_none(request.args.get("data_inicio")),
            vazio_para_none(request.args.get("data_fim")),
            vazio_para_none(request.args.get("tipo")))


def _filtros_aplicacoes():
    return (vazio_para_none(request.args.get("data_inicio")),
            vazio_para_none(request.args.get("data_fim")),
            vazio_para_none(request.args.get("classe")))


@relatorios_bp.route("/geral/exportar.csv")
@login_required
@require_permission("relatorios.view")
def geral_exportar_csv():
    propriedade = propriedade_atual()
    conteudo = gerar_csv_relatorio_geral(propriedade, montar_relatorio_geral(propriedade))
    _auditar_exportacao("geral", "csv", propriedade)
    return resposta_csv(conteudo, nome_arquivo("geral", "csv"))


@relatorios_bp.route("/geral/exportar.pdf")
@login_required
@require_permission("relatorios.view")
def geral_exportar_pdf():
    propriedade = propriedade_atual()
    pdf = gerar_pdf_relatorio_geral(propriedade, montar_relatorio_geral(propriedade))
    _auditar_exportacao("geral", "pdf", propriedade)
    return resposta_pdf(pdf, nome_arquivo("geral", "pdf"))


@relatorios_bp.route("/financeiro/exportar.csv")
@login_required
@require_permission("relatorios.view")
def financeiro_exportar_csv():
    propriedade = propriedade_atual()
    di, df, tipo = _filtros_financeiro()
    try:
        dados = montar_relatorio_financeiro(propriedade, di, df, tipo)
    except FiltroInvalidoError as erro:
        _falha_exportacao("financeiro", "csv", propriedade, erro)
    conteudo = gerar_csv_relatorio_financeiro(propriedade, dados)
    _auditar_exportacao("financeiro", "csv", propriedade)
    return resposta_csv(conteudo, nome_arquivo("financeiro", "csv"))


@relatorios_bp.route("/financeiro/exportar.pdf")
@login_required
@require_permission("relatorios.view")
def financeiro_exportar_pdf():
    propriedade = propriedade_atual()
    di, df, tipo = _filtros_financeiro()
    try:
        dados = montar_relatorio_financeiro(propriedade, di, df, tipo)
    except FiltroInvalidoError as erro:
        _falha_exportacao("financeiro", "pdf", propriedade, erro)
    pdf = gerar_pdf_relatorio_financeiro(propriedade, dados)
    _auditar_exportacao("financeiro", "pdf", propriedade)
    return resposta_pdf(pdf, nome_arquivo("financeiro", "pdf"))


@relatorios_bp.route("/agricola/exportar.csv")
@login_required
@require_permission("relatorios.view")
def agricola_exportar_csv():
    propriedade = propriedade_atual()
    conteudo = gerar_csv_relatorio_agricola(propriedade, montar_relatorio_agricola(propriedade))
    _auditar_exportacao("agricola", "csv", propriedade)
    return resposta_csv(conteudo, nome_arquivo("agricola", "csv"))


@relatorios_bp.route("/agricola/exportar.pdf")
@login_required
@require_permission("relatorios.view")
def agricola_exportar_pdf():
    propriedade = propriedade_atual()
    pdf = gerar_pdf_relatorio_agricola(propriedade, montar_relatorio_agricola(propriedade))
    _auditar_exportacao("agricola", "pdf", propriedade)
    return resposta_pdf(pdf, nome_arquivo("agricola", "pdf"))


@relatorios_bp.route("/aplicacoes/exportar.csv")
@login_required
@require_permission("relatorios.view")
def aplicacoes_exportar_csv():
    propriedade = propriedade_atual()
    di, df, classe = _filtros_aplicacoes()
    try:
        dados = montar_relatorio_aplicacoes(propriedade, di, df, classe)
    except FiltroInvalidoError as erro:
        _falha_exportacao("aplicacoes", "csv", propriedade, erro)
    conteudo = gerar_csv_relatorio_aplicacoes(propriedade, dados)
    _auditar_exportacao("aplicacoes", "csv", propriedade)
    return resposta_csv(conteudo, nome_arquivo("aplicacoes", "csv"))


@relatorios_bp.route("/aplicacoes/exportar.pdf")
@login_required
@require_permission("relatorios.view")
def aplicacoes_exportar_pdf():
    propriedade = propriedade_atual()
    di, df, classe = _filtros_aplicacoes()
    try:
        dados = montar_relatorio_aplicacoes(propriedade, di, df, classe)
    except FiltroInvalidoError as erro:
        _falha_exportacao("aplicacoes", "pdf", propriedade, erro)
    pdf = gerar_pdf_relatorio_aplicacoes(propriedade, dados)
    _auditar_exportacao("aplicacoes", "pdf", propriedade)
    return resposta_pdf(pdf, nome_arquivo("aplicacoes", "pdf"))


@relatorios_bp.route("/uploads/exportar.csv")
@login_required
@require_permission("relatorios.view")
def uploads_exportar_csv():
    propriedade = propriedade_atual()
    conteudo = gerar_csv_relatorio_uploads(propriedade, montar_relatorio_uploads(propriedade))
    _auditar_exportacao("uploads", "csv", propriedade)
    return resposta_csv(conteudo, nome_arquivo("uploads", "csv"))


@relatorios_bp.route("/uploads/exportar.pdf")
@login_required
@require_permission("relatorios.view")
def uploads_exportar_pdf():
    propriedade = propriedade_atual()
    pdf = gerar_pdf_relatorio_uploads(propriedade, montar_relatorio_uploads(propriedade))
    _auditar_exportacao("uploads", "pdf", propriedade)
    return resposta_pdf(pdf, nome_arquivo("uploads", "pdf"))
