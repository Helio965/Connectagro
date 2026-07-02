"""Exportações CSV/PDF dos relatórios operacionais (Fase 7.4).

Gera CSV (biblioteca padrão) e PDF (ReportLab) **em memória**, sem gravar
arquivo no disco. Reutiliza os mesmos dados do ``relatorios_service``.

Cada exportação traz o aviso de que é um relatório operacional — não cotação,
venda, checkout ou documento comercial.
"""
import csv
import io
from datetime import datetime, timezone

from flask import make_response
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_AVISO_OPERACIONAL = (
    "Relatório operacional do ConnectAgro. Não constitui cotação, venda, "
    "checkout ou documento comercial."
)


def nome_arquivo(slug, extensao):
    """Gera o nome do arquivo de exportação com data."""
    data = datetime.now(timezone.utc).strftime("%Y%m%d")
    return f"connectagro_{slug}_{data}.{extensao}"


def resposta_csv(conteudo, filename):
    """Cria uma resposta HTTP com conteúdo CSV."""
    resp = make_response(conteudo)
    resp.headers["Content-Type"] = "text/csv; charset=utf-8"
    resp.headers["Content-Disposition"] = f'attachment; filename="{filename}"'
    return resp


def resposta_pdf(pdf_bytes, filename):
    """Cria uma resposta HTTP com conteúdo PDF."""
    resp = make_response(pdf_bytes)
    resp.headers["Content-Type"] = "application/pdf"
    resp.headers["Content-Disposition"] = f'attachment; filename="{filename}"'
    return resp


def _csv_writer(buf):
    return csv.writer(buf, delimiter=";", quoting=csv.QUOTE_MINIMAL)


def _pdf_doc(buf, titulo):
    """Cria um SimpleDocTemplate padrão para os PDFs."""
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=2 * cm, rightMargin=2 * cm,
        topMargin=2 * cm, bottomMargin=2 * cm,
        title=titulo,
    )
    return doc


def _pdf_header(titulo, propriedade, styles):
    """Retorna os elementos de cabeçalho padrão para os PDFs."""
    elements = [
        Paragraph(titulo, styles["Title"]),
        Paragraph(f"Propriedade: {propriedade.nome}", styles["Normal"]),
        Paragraph(_AVISO_OPERACIONAL, styles["Italic"]),
        Spacer(1, 0.5 * cm),
    ]
    return elements


def _tabela_pdf(dados, col_widths=None):
    """Cria uma tabela padrão estilizada para PDF."""
    t = Table(dados, colWidths=col_widths, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.Color(0.2, 0.4, 0.2)),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 9),
        ("FONTSIZE", (0, 1), (-1, -1), 8),
        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.Color(0.95, 0.95, 0.95)]),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    return t


def _fmt_valor(v, casas=2):
    """Formata número para exibição."""
    if v is None:
        return "0"
    return f"{float(v):,.{casas}f}".replace(",", "_").replace(".", ",").replace("_", ".")


# ---------------------------------------------------------------------------
# CSV generators
# ---------------------------------------------------------------------------

def gerar_csv_relatorio_geral(propriedade, dados):
    buf = io.StringIO()
    w = _csv_writer(buf)
    w.writerow([_AVISO_OPERACIONAL])
    w.writerow(["Relatório Geral", propriedade.nome])
    w.writerow([])
    w.writerow(["Indicador", "Valor"])
    g = dados["glebas"]
    w.writerow(["Total de propriedades", g["total"]])
    w.writerow(["Área total (ha)", _fmt_valor(g["area_total"])])
    w.writerow(["Propriedades sem área", g["sem_area"]])
    c = dados["culturas"]
    w.writerow(["Total de culturas", c["total"]])
    w.writerow(["Associações cultura↔propriedade", c["total_associacoes"]])
    f = dados["financeiro"]
    w.writerow(["Receitas", _fmt_valor(f["receitas"])])
    w.writerow(["Despesas", _fmt_valor(f["despesas"])])
    w.writerow(["Saldo", _fmt_valor(f["saldo"])])
    e = dados["equipe"]
    w.writerow(["Membros de equipe", e["total"]])
    w.writerow(["Ativos", e["ativos"]])
    w.writerow(["Colheitas", dados["colheita"]["total"]])
    w.writerow(["Aplicações", dados["aplicacoes"]["total"]])
    w.writerow(["Uploads", dados["uploads"]["total"]])
    return buf.getvalue()


def gerar_csv_relatorio_financeiro(propriedade, dados):
    buf = io.StringIO()
    w = _csv_writer(buf)
    w.writerow([_AVISO_OPERACIONAL])
    w.writerow(["Relatório Financeiro", propriedade.nome])
    w.writerow(["Receitas", _fmt_valor(dados["receitas"])])
    w.writerow(["Despesas", _fmt_valor(dados["despesas"])])
    w.writerow(["Saldo", _fmt_valor(dados["saldo"])])
    w.writerow([])
    w.writerow(["Data", "Tipo", "Categoria", "Descrição", "Valor"])
    for l in dados["lancamentos"]:
        w.writerow([l.data, l.tipo, l.categoria or "", l.descricao or "", _fmt_valor(l.valor)])
    return buf.getvalue()


def gerar_csv_relatorio_agricola(propriedade, dados):
    buf = io.StringIO()
    w = _csv_writer(buf)
    w.writerow([_AVISO_OPERACIONAL])
    w.writerow(["Relatório Agrícola", propriedade.nome])
    w.writerow([])
    w.writerow(["Propriedades"])
    w.writerow(["Nome", "Área (ha)", "Tipo de Solo"])
    for item in dados["glebas"]:
        g = item["obj"]
        w.writerow([g.nome, _fmt_valor(g.area_ha), g.tipo_solo or ""])
    w.writerow([])
    w.writerow(["Culturas"])
    w.writerow(["Nome", "Variedade", "Safra", "Status"])
    for c in dados["culturas"]:
        w.writerow([c.nome, c.variedade or "", c.safra or "", c.status])
    return buf.getvalue()


def gerar_csv_relatorio_aplicacoes(propriedade, dados):
    buf = io.StringIO()
    w = _csv_writer(buf)
    w.writerow([_AVISO_OPERACIONAL])
    w.writerow(["Relatório de Aplicações", propriedade.nome, f"Total: {dados['total']}"])
    w.writerow([])
    w.writerow(["Data", "Produto", "Dose", "Unidade", "Responsável", "Observação"])
    for a in dados["aplicacoes"]:
        produto = a.produto.nome if a.produto else ""
        w.writerow([a.data_aplicacao, produto, _fmt_valor(a.dose), a.unidade or "",
                    a.responsavel or "", a.observacao or ""])
    return buf.getvalue()


def gerar_csv_relatorio_uploads(propriedade, dados):
    buf = io.StringIO()
    w = _csv_writer(buf)
    w.writerow([_AVISO_OPERACIONAL])
    w.writerow(["Relatório de Uploads", propriedade.nome, f"Total: {dados['total']}"])
    w.writerow([])
    w.writerow(["Nome", "Tipo MIME", "Tamanho", "Descrição", "Enviado em"])
    for a in dados["arquivos"]:
        w.writerow([a.nome_original, a.tipo_mime or "", a.tamanho or 0,
                    a.descricao or "", a.enviado_em])
    return buf.getvalue()


# ---------------------------------------------------------------------------
# PDF generators
# ---------------------------------------------------------------------------

def gerar_pdf_relatorio_geral(propriedade, dados):
    buf = io.BytesIO()
    doc = _pdf_doc(buf, "Relatório Geral")
    styles = getSampleStyleSheet()
    elems = _pdf_header("Relatório Geral", propriedade, styles)

    table_data = [["Indicador", "Valor"]]
    g = dados["glebas"]
    table_data.append(["Total de propriedades", str(g["total"])])
    table_data.append(["Área total", f'{_fmt_valor(g["area_total"])} ha'])
    c = dados["culturas"]
    table_data.append(["Total de culturas", str(c["total"])])
    f = dados["financeiro"]
    table_data.append(["Receitas", f'R$ {_fmt_valor(f["receitas"])}'])
    table_data.append(["Despesas", f'R$ {_fmt_valor(f["despesas"])}'])
    table_data.append(["Saldo", f'R$ {_fmt_valor(f["saldo"])}'])
    e = dados["equipe"]
    table_data.append(["Equipe (ativos)", str(e["ativos"])])
    table_data.append(["Colheitas", str(dados["colheita"]["total"])])
    table_data.append(["Aplicações", str(dados["aplicacoes"]["total"])])
    table_data.append(["Uploads", str(dados["uploads"]["total"])])

    elems.append(_tabela_pdf(table_data))
    doc.build(elems)
    return buf.getvalue()


def gerar_pdf_relatorio_financeiro(propriedade, dados):
    buf = io.BytesIO()
    doc = _pdf_doc(buf, "Relatório Financeiro")
    styles = getSampleStyleSheet()
    elems = _pdf_header("Relatório Financeiro", propriedade, styles)

    elems.append(Paragraph(
        f'Receitas: R$ {_fmt_valor(dados["receitas"])} | '
        f'Despesas: R$ {_fmt_valor(dados["despesas"])} | '
        f'Saldo: R$ {_fmt_valor(dados["saldo"])}',
        styles["Normal"]))
    elems.append(Spacer(1, 0.3 * cm))

    table_data = [["Data", "Tipo", "Categoria", "Valor"]]
    for l in dados["lancamentos"]:
        table_data.append([l.data, l.tipo, l.categoria or "—", f"R$ {_fmt_valor(l.valor)}"])
    elems.append(_tabela_pdf(table_data))
    doc.build(elems)
    return buf.getvalue()


def gerar_pdf_relatorio_agricola(propriedade, dados):
    buf = io.BytesIO()
    doc = _pdf_doc(buf, "Relatório Agrícola")
    styles = getSampleStyleSheet()
    elems = _pdf_header("Relatório Agrícola", propriedade, styles)

    elems.append(Paragraph("Propriedades", styles["Heading2"]))
    table_data = [["Nome", "Área (ha)", "Tipo de Solo"]]
    for item in dados["glebas"]:
        g = item["obj"]
        table_data.append([g.nome, _fmt_valor(g.area_ha), g.tipo_solo or "—"])
    elems.append(_tabela_pdf(table_data))
    elems.append(Spacer(1, 0.5 * cm))

    elems.append(Paragraph("Culturas", styles["Heading2"]))
    table_data = [["Nome", "Variedade", "Safra", "Status"]]
    for c in dados["culturas"]:
        table_data.append([c.nome, c.variedade or "—", c.safra or "—", c.status])
    elems.append(_tabela_pdf(table_data))
    doc.build(elems)
    return buf.getvalue()


def gerar_pdf_relatorio_aplicacoes(propriedade, dados):
    buf = io.BytesIO()
    doc = _pdf_doc(buf, "Relatório de Aplicações")
    styles = getSampleStyleSheet()
    elems = _pdf_header("Relatório de Aplicações", propriedade, styles)

    table_data = [["Data", "Produto", "Dose", "Unidade", "Responsável"]]
    for a in dados["aplicacoes"]:
        produto = a.produto.nome if a.produto else "—"
        table_data.append([a.data_aplicacao, produto, _fmt_valor(a.dose),
                          a.unidade or "—", a.responsavel or "—"])
    elems.append(_tabela_pdf(table_data))
    doc.build(elems)
    return buf.getvalue()


def gerar_pdf_relatorio_uploads(propriedade, dados):
    buf = io.BytesIO()
    doc = _pdf_doc(buf, "Relatório de Uploads")
    styles = getSampleStyleSheet()
    elems = _pdf_header("Relatório de Uploads", propriedade, styles)

    table_data = [["Nome", "Tipo MIME", "Tamanho", "Enviado em"]]
    for a in dados["arquivos"]:
        table_data.append([a.nome_original, a.tipo_mime or "—",
                          str(a.tamanho or 0), a.enviado_em or "—"])
    elems.append(_tabela_pdf(table_data))
    doc.build(elems)
    return buf.getvalue()
