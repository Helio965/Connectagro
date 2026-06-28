"""Relatórios Operacionais HTML (somente leitura) — escopo: propriedade atual.

Não criam, alteram ou removem dados. Sem PDF/exportação nesta fase; a impressão
é feita pelo navegador (``window.print()``).
"""
from flask import flash, render_template, request

from ...utils.auth import login_required
from ...utils.contexto import propriedade_atual, vazio_para_none
from ...utils.formatters import (
    formatar_area,
    formatar_moeda,
    formatar_numero,
    formatar_tamanho,
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

# Formatadores disponibilizados aos templates de relatórios.
FMT = {
    "formatar_area": formatar_area,
    "formatar_moeda": formatar_moeda,
    "formatar_numero": formatar_numero,
    "formatar_tamanho": formatar_tamanho,
}


@relatorios_bp.route("/")
@login_required
def index():
    return render_template("relatorios/index.html", propriedade=propriedade_atual(), **FMT)


@relatorios_bp.route("/geral")
@login_required
def geral():
    propriedade = propriedade_atual()
    dados = montar_relatorio_geral(propriedade)
    return render_template("relatorios/geral.html", propriedade=propriedade, dados=dados, **FMT)


@relatorios_bp.route("/financeiro")
@login_required
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
def agricola():
    propriedade = propriedade_atual()
    dados = montar_relatorio_agricola(propriedade)
    return render_template("relatorios/agricola.html", propriedade=propriedade, dados=dados, **FMT)


@relatorios_bp.route("/aplicacoes")
@login_required
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
def uploads():
    propriedade = propriedade_atual()
    dados = montar_relatorio_uploads(propriedade)
    return render_template("relatorios/uploads.html", propriedade=propriedade, dados=dados, **FMT)
