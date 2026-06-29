"""Exportações operacionais dos relatórios (Fase 7.4 — MVP ampliado).

Gera **CSV** (biblioteca padrão) e **PDF** (ReportLab) **em memória**, a partir
dos dados já montados por ``relatorios_service`` (somente leitura, escopados pela
propriedade atual). As exportações são **relatórios operacionais** — nunca
cotação, venda, checkout ou documento comercial.

Decisões documentadas:
- CSV em **UTF-8 sem BOM**, separador **vírgula**, com linhas iniciais de
  metadados (relatório, propriedade, geração, filtros e aviso).
- PDF simples (sem logo/imagem, sem HTML-to-PDF), em página A4 paisagem.
"""
import csv
import io
from datetime import datetime, timezone
from xml.sax.saxutils import escape

from flask import Response
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

AVISO = ("Relatório operacional interno. Não é cotação, venda, recomendação "
         "agronômica ou documento comercial.")

_PAGINA = landscape(A4)
_MARGEM = 15 * mm
_LARGURA_UTIL = _PAGINA[0] - 2 * _MARGEM

_ESTILO_TITULO = ParagraphStyle("titulo", fontSize=14, leading=17,
                                spaceAfter=4, fontName="Helvetica-Bold")
_ESTILO_SUBTITULO = ParagraphStyle("subtitulo", fontSize=10, leading=13,
                                   spaceBefore=6, spaceAfter=3,
                                   fontName="Helvetica-Bold")
_ESTILO_NORMAL = ParagraphStyle("normal", fontSize=8, leading=10)
_ESTILO_AVISO = ParagraphStyle("aviso", fontSize=7, leading=9,
                               textColor=colors.HexColor("#9a3412"),
                               spaceBefore=3)
_ESTILO_CELULA = ParagraphStyle("celula", fontSize=7, leading=8)
_ESTILO_CELULA_HEADER = ParagraphStyle("celula_h", fontSize=7, leading=8,
                                       textColor=colors.white,
                                       fontName="Helvetica-Bold")


# ---------------------------------------------------------------------------
# Helpers comuns
# ---------------------------------------------------------------------------

def _agora_legivel():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def _txt(valor):
    """Converte valor em texto seguro para célula/CSV ('' para None)."""
    if valor is None:
        return ""
    return str(valor)


def _num(valor, casas=2):
    """Número com ponto decimal (formato neutro/máquina)."""
    if valor is None:
        return ""
    return f"{float(valor):.{casas}f}"


def _filtros_legivel(filtros):
    if not filtros:
        return ""
    return "; ".join(f"{k}={v}" for k, v in filtros.items() if v not in (None, ""))


def nome_arquivo(slug, ext):
    """Nome do arquivo de exportação, com carimbo de data."""
    data = datetime.now(timezone.utc).strftime("%Y%m%d")
    return f"relatorio_{slug}_{data}.{ext}"


# ---------------------------------------------------------------------------
# Respostas HTTP
# ---------------------------------------------------------------------------

def resposta_csv(conteudo, nome):
    return Response(
        conteudo,
        content_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{nome}"'},
    )


def resposta_pdf(bytes_pdf, nome):
    return Response(
        bytes_pdf,
        content_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{nome}"'},
    )


# ---------------------------------------------------------------------------
# CSV — helpers
# ---------------------------------------------------------------------------

def _novo_csv():
    buffer = io.StringIO()
    return buffer, csv.writer(buffer)


def _csv_cabecalho(writer, titulo, propriedade, filtros=None):
    writer.writerow(["Relatório", titulo])
    writer.writerow(["Propriedade", propriedade.nome])
    writer.writerow(["Gerado em", _agora_legivel()])
    if filtros:
        writer.writerow(["Filtros", _filtros_legivel(filtros)])
    writer.writerow(["Aviso", AVISO])
    writer.writerow([])


# ---------------------------------------------------------------------------
# PDF — helpers
# ---------------------------------------------------------------------------

def _tabela(headers, rows):
    largura_col = _LARGURA_UTIL / max(len(headers), 1)
    dados = [[Paragraph(escape(str(h)), _ESTILO_CELULA_HEADER) for h in headers]]
    for row in rows:
        dados.append([Paragraph(escape(_txt(c)), _ESTILO_CELULA) for c in row])
    tabela = Table(dados, colWidths=[largura_col] * len(headers), repeatRows=1)
    tabela.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2d6a4f")),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1),
         [colors.white, colors.HexColor("#f2f2f2")]),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))
    return tabela


def _cabecalho_pdf(titulo, propriedade, filtros=None):
    flow = [
        Paragraph(escape(titulo), _ESTILO_TITULO),
        Paragraph(f"Propriedade: {escape(propriedade.nome)}", _ESTILO_NORMAL),
        Paragraph(f"Gerado em: {_agora_legivel()}", _ESTILO_NORMAL),
    ]
    if filtros and _filtros_legivel(filtros):
        flow.append(Paragraph("Filtros: " + escape(_filtros_legivel(filtros)),
                              _ESTILO_NORMAL))
    flow.append(Paragraph(AVISO, _ESTILO_AVISO))
    flow.append(Spacer(1, 5 * mm))
    return flow


def _render_pdf(story):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=_PAGINA, leftMargin=_MARGEM, rightMargin=_MARGEM,
        topMargin=_MARGEM, bottomMargin=_MARGEM, title="ConnectAgro",
    )
    doc.build(story)
    return buffer.getvalue()


def _subtitulo(texto):
    return Paragraph(escape(texto), _ESTILO_SUBTITULO)


# ===========================================================================
# Relatório Geral
# ===========================================================================

def _linhas_geral(dados):
    g, c = dados["glebas"], dados["culturas"]
    eq, fin = dados["equipe"], dados["financeiro"]
    linhas = [
        ("Glebas", "Total de glebas", g["total"]),
        ("Glebas", "Área total (ha)", _num(g["area_total"])),
        ("Glebas", "Glebas sem área", g["sem_area"]),
        ("Glebas", "Glebas sem coordenadas válidas", g["sem_coordenadas"]),
        ("Culturas", "Total de culturas", c["total"]),
        ("Culturas", "Associações cultura↔gleba", c["total_associacoes"]),
    ]
    for status, qtd in c["por_status"].items():
        linhas.append(("Culturas", f"Culturas: {status}", qtd))
    linhas += [
        ("Equipe", "Total de membros", eq["total"]),
        ("Equipe", "Ativos", eq["ativos"]),
        ("Equipe", "Inativos", eq["inativos"]),
        ("Financeiro", "Receitas", _num(fin["receitas"])),
        ("Financeiro", "Despesas", _num(fin["despesas"])),
        ("Financeiro", "Saldo", _num(fin["saldo"])),
        ("Financeiro", "Lançamentos", fin["total_lancamentos"]),
        ("Colheita", "Total de colheitas", dados["colheita"]["total"]),
        ("Aplicações", "Total de aplicações", dados["aplicacoes"]["total"]),
        ("Uploads", "Total de uploads", dados["uploads"]["total"]),
        ("Uploads", "Tamanho total (bytes)", dados["uploads"]["tamanho_total"]),
        ("Catálogo", "Defensivos", dados["catalogo"]["defensivos"]),
        ("Catálogo", "Fertilizantes", dados["catalogo"]["fertilizantes"]),
    ]
    return linhas


def gerar_csv_relatorio_geral(propriedade, dados):
    buffer, writer = _novo_csv()
    _csv_cabecalho(writer, "Geral", propriedade)
    writer.writerow(["Seção", "Indicador", "Valor"])
    for secao, indicador, valor in _linhas_geral(dados):
        writer.writerow([secao, indicador, _txt(valor)])
    return buffer.getvalue()


def gerar_pdf_relatorio_geral(propriedade, dados):
    story = _cabecalho_pdf("Relatório Geral", propriedade)
    rows = [[s, i, _txt(v)] for s, i, v in _linhas_geral(dados)]
    story.append(_tabela(["Seção", "Indicador", "Valor"], rows))
    return _render_pdf(story)


# ===========================================================================
# Relatório Financeiro
# ===========================================================================

_HEADERS_FIN = ["Data", "Tipo", "Categoria", "Descrição", "Valor"]


def _linhas_financeiro(dados):
    return [[_txt(l.data), _txt(l.tipo), _txt(l.categoria), _txt(l.descricao),
             _num(l.valor)] for l in dados["lancamentos"]]


def gerar_csv_relatorio_financeiro(propriedade, dados):
    buffer, writer = _novo_csv()
    _csv_cabecalho(writer, "Financeiro", propriedade, dados.get("filtros"))
    writer.writerow(["Receitas", _num(dados["receitas"])])
    writer.writerow(["Despesas", _num(dados["despesas"])])
    writer.writerow(["Saldo", _num(dados["saldo"])])
    writer.writerow(["Quantidade", dados["quantidade"]])
    writer.writerow([])
    writer.writerow(_HEADERS_FIN)
    for linha in _linhas_financeiro(dados):
        writer.writerow(linha)
    return buffer.getvalue()


def gerar_pdf_relatorio_financeiro(propriedade, dados):
    story = _cabecalho_pdf("Relatório Financeiro", propriedade, dados.get("filtros"))
    resumo = [["Receitas", _num(dados["receitas"])],
              ["Despesas", _num(dados["despesas"])],
              ["Saldo", _num(dados["saldo"])],
              ["Quantidade", _txt(dados["quantidade"])]]
    story.append(_subtitulo("Resumo"))
    story.append(_tabela(["Indicador", "Valor"], resumo))
    story.append(Spacer(1, 4 * mm))
    story.append(_subtitulo("Lançamentos"))
    story.append(_tabela(_HEADERS_FIN, _linhas_financeiro(dados)))
    return _render_pdf(story)


# ===========================================================================
# Relatório Agrícola
# ===========================================================================

def gerar_csv_relatorio_agricola(propriedade, dados):
    buffer, writer = _novo_csv()
    _csv_cabecalho(writer, "Agrícola", propriedade)

    writer.writerow(["Glebas"])
    writer.writerow(["Nome", "Área (ha)", "Tipo de solo", "Latitude",
                     "Longitude", "Coordenadas válidas"])
    for item in dados["glebas"]:
        g = item["obj"]
        writer.writerow([_txt(g.nome), _num(g.area_ha), _txt(g.tipo_solo),
                         _txt(g.latitude), _txt(g.longitude),
                         "Sim" if item["coordenada_valida"] else "Não"])
    writer.writerow([])

    writer.writerow(["Culturas"])
    writer.writerow(["Nome", "Variedade", "Safra", "Status", "Início", "Fim"])
    for c in dados["culturas"]:
        writer.writerow([_txt(c.nome), _txt(c.variedade), _txt(c.safra),
                         _txt(c.status), _txt(c.data_inicio), _txt(c.data_fim)])
    writer.writerow([])

    writer.writerow(["Associações cultura-gleba"])
    writer.writerow(["Cultura", "Gleba", "Status da cultura"])
    for cg in dados["associacoes"]:
        writer.writerow([_txt(cg.cultura.nome), _txt(cg.gleba.nome),
                         _txt(cg.cultura.status)])
    writer.writerow([])

    writer.writerow(["Colheitas"])
    writer.writerow(["Data", "Cultura", "Gleba", "Quantidade", "Unidade",
                     "Qualidade"])
    for col in dados["colheitas"]:
        writer.writerow([_txt(col.data_colheita), _txt(col.cultura_gleba.cultura.nome),
                         _txt(col.cultura_gleba.gleba.nome), _num(col.quantidade),
                         _txt(col.unidade), _txt(col.qualidade)])
    return buffer.getvalue()


def gerar_pdf_relatorio_agricola(propriedade, dados):
    story = _cabecalho_pdf("Relatório Agrícola", propriedade)

    story.append(_subtitulo("Glebas"))
    rows = [[_txt(i["obj"].nome), _num(i["obj"].area_ha), _txt(i["obj"].tipo_solo),
             _txt(i["obj"].latitude), _txt(i["obj"].longitude),
             "Sim" if i["coordenada_valida"] else "Não"] for i in dados["glebas"]]
    story.append(_tabela(["Nome", "Área (ha)", "Tipo de solo", "Latitude",
                          "Longitude", "Coord. válidas"], rows))
    story.append(Spacer(1, 4 * mm))

    story.append(_subtitulo("Culturas"))
    rows = [[_txt(c.nome), _txt(c.variedade), _txt(c.safra), _txt(c.status),
             _txt(c.data_inicio), _txt(c.data_fim)] for c in dados["culturas"]]
    story.append(_tabela(["Nome", "Variedade", "Safra", "Status", "Início", "Fim"], rows))
    story.append(Spacer(1, 4 * mm))

    story.append(_subtitulo("Associações cultura↔gleba"))
    rows = [[_txt(cg.cultura.nome), _txt(cg.gleba.nome), _txt(cg.cultura.status)]
            for cg in dados["associacoes"]]
    story.append(_tabela(["Cultura", "Gleba", "Status da cultura"], rows))
    story.append(Spacer(1, 4 * mm))

    story.append(_subtitulo(f"Colheitas (total: {dados['total_colheitas']})"))
    rows = [[_txt(col.data_colheita), _txt(col.cultura_gleba.cultura.nome),
             _txt(col.cultura_gleba.gleba.nome), _num(col.quantidade),
             _txt(col.unidade), _txt(col.qualidade)] for col in dados["colheitas"]]
    story.append(_tabela(["Data", "Cultura", "Gleba", "Quantidade", "Unidade",
                          "Qualidade"], rows))
    return _render_pdf(story)


# ===========================================================================
# Relatório de Aplicações
# ===========================================================================

_HEADERS_APL = ["Data", "Cultura", "Gleba", "Produto", "Classe", "Dose",
                "Unidade", "Responsável", "Observação"]


def _linhas_aplicacoes(dados):
    linhas = []
    for a in dados["aplicacoes"]:
        linhas.append([
            _txt(a.data_aplicacao), _txt(a.cultura_gleba.cultura.nome),
            _txt(a.cultura_gleba.gleba.nome), _txt(a.produto.nome),
            _txt(a.produto.classe), _num(a.dose), _txt(a.unidade),
            _txt(a.responsavel), _txt(a.observacao),
        ])
    return linhas


def gerar_csv_relatorio_aplicacoes(propriedade, dados):
    buffer, writer = _novo_csv()
    _csv_cabecalho(writer, "Aplicações", propriedade, dados.get("filtros"))
    writer.writerow(["Total", dados["total"]])
    writer.writerow([])
    writer.writerow(_HEADERS_APL)
    for linha in _linhas_aplicacoes(dados):
        writer.writerow(linha)
    return buffer.getvalue()


def gerar_pdf_relatorio_aplicacoes(propriedade, dados):
    story = _cabecalho_pdf("Relatório de Aplicações", propriedade, dados.get("filtros"))
    story.append(_subtitulo(f"Total de aplicações: {dados['total']}"))
    story.append(_tabela(_HEADERS_APL, _linhas_aplicacoes(dados)))
    return _render_pdf(story)


# ===========================================================================
# Relatório de Uploads
# ===========================================================================

_HEADERS_UP = ["Data", "Nome original", "Tipo MIME", "Tamanho (bytes)", "Descrição"]


def _linhas_uploads(dados):
    return [[_txt(a.enviado_em), _txt(a.nome_original), _txt(a.tipo_mime),
             _txt(a.tamanho), _txt(a.descricao)] for a in dados["arquivos"]]


def gerar_csv_relatorio_uploads(propriedade, dados):
    buffer, writer = _novo_csv()
    _csv_cabecalho(writer, "Uploads", propriedade)
    writer.writerow(["Total", dados["total"]])
    writer.writerow(["Tamanho total (bytes)", dados["tamanho_total"]])
    writer.writerow([])
    writer.writerow(_HEADERS_UP)
    for linha in _linhas_uploads(dados):
        writer.writerow(linha)
    return buffer.getvalue()


def gerar_pdf_relatorio_uploads(propriedade, dados):
    story = _cabecalho_pdf("Relatório de Uploads", propriedade)
    story.append(_subtitulo(
        f"Total: {dados['total']} · Tamanho total (bytes): {dados['tamanho_total']}"))
    story.append(_tabela(_HEADERS_UP, _linhas_uploads(dados)))
    return _render_pdf(story)
