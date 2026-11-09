"""Histórico operacional: fontes, precisão, acesso e exportações reais."""
import base64
import csv
import io
import re
import zlib
from decimal import Decimal

import pytest

from app.extensions import db
from app.models import (
    AplicacaoInsumo, AtividadeItem, AtividadeOperacional, Cultura, CulturaGleba,
    FinanceiroLancamento, Gleba, IaInteracao, ProdutoBase, ProdutoPreco,
    Propriedade, Usuario,
)
from app.services.relatorios_service import (
    formatar_decimal_operacional, montar_relatorio_financeiro,
    montar_relatorio_operacional,
)
from app.utils.auth import gerar_hash_senha
from tests.factories import criar_propriedade_com_vinculo, vincular_usuario_propriedade


@pytest.fixture
def operational_reports(app):
    with app.app_context():
        db.create_all()
        users = {}
        for alias, perfil in (("admin", "admin"), ("manager", "tecnico"),
                              ("worker", "trabalhador"), ("foreign", "admin")):
            users[alias] = Usuario(nome="FOREIGN_ACCOUNT_SECRET" if alias == "foreign" else alias,
                                   email=f"{alias}@report6.invalid", perfil=perfil, ativo=True,
                                   senha_hash=gerar_hash_senha("Report6!pass"))
        db.session.add_all(users.values())
        db.session.flush()
        prop = criar_propriedade_com_vinculo(users["admin"].id, nome="Fazenda <A> & teste")
        other = criar_propriedade_com_vinculo(users["foreign"].id, nome="FOREIGN_PROPERTY_SECRET")
        for alias in ("manager", "worker"):
            vincular_usuario_propriedade(users[alias].id, prop.id)
        areas = [Gleba(propriedade_id=prop.id, nome="Área A"),
                 Gleba(propriedade_id=prop.id, nome="Área A sem cultura"),
                 Gleba(propriedade_id=other.id, nome="FOREIGN_AREA_SECRET")]
        culturas = [Cultura(propriedade_id=prop.id, nome="Cultura A"),
                    Cultura(propriedade_id=other.id, nome="FOREIGN_CROP_SECRET")]
        produtos = [ProdutoBase(nome="Produto um", slug="report6-p1", classe="fertilizante"),
                    ProdutoBase(nome="Produto dois", slug="report6-p2", classe="defensivo")]
        db.session.add_all(areas + culturas + produtos)
        db.session.flush()
        cg = CulturaGleba(gleba_id=areas[0].id, cultura_id=culturas[0].id)
        cg_other = CulturaGleba(gleba_id=areas[2].id, cultura_id=culturas[1].id)
        cg_crossed = CulturaGleba(gleba_id=areas[0].id, cultura_id=culturas[1].id)
        db.session.add_all([cg, cg_other, cg_crossed])
        db.session.flush()
        activities = [AtividadeOperacional(gleba_id=areas[0].id, cultura_gleba_id=cg.id,
                                          tipo_atividade="Irrigação", data_execucao="2026-04-01",
                                          responsavel="Responsável histórico", responsavel_usuario_id=users["worker"].id,
                                          criado_por_id=users["admin"].id),
                      AtividadeOperacional(gleba_id=areas[0].id, tipo_atividade="Inspeção",
                                          data_execucao="2026-04-02", criado_por_id=users["foreign"].id,
                                          responsavel_usuario_id=users["foreign"].id,
                                          responsavel="Snapshot autorizado"),
                      AtividadeOperacional(gleba_id=areas[0].id, tipo_atividade="Cancelada",
                                          data_execucao="2026-04-03", cancelado_em="2026-04-04"),
                      AtividadeOperacional(gleba_id=areas[1].id, tipo_atividade="Sem itens",
                                          data_execucao="2026-04-05"),
                      AtividadeOperacional(gleba_id=areas[2].id, cultura_gleba_id=cg_other.id,
                                          tipo_atividade="FOREIGN_ACTIVITY_SECRET", data_execucao="2026-04-01"),
                      AtividadeOperacional(gleba_id=areas[0].id, cultura_gleba_id=cg_crossed.id,
                                          tipo_atividade="CROSSED_ACTIVITY_SECRET", data_execucao="2026-04-01")]
        db.session.add_all(activities)
        db.session.flush()

        def item(activity, product=0, quantity="0.1", unit="L", **extra):
            return AtividadeItem(atividade_id=activities[activity].id, produto_base_id=produtos[product].id,
                                 quantidade_utilizada=Decimal(quantity), unidade_quantidade=unit, **extra)

        db.session.add_all([
            item(0, quantity="0.100001", dose=Decimal("2"), unidade_dose="L/ha",
                 custo_unitario=Decimal("12.345678"), custo_total=Decimal("7432.19"), moeda="BRL",
                 origem_custo="segredo_custo_operacional"),
            item(0, product=1, quantity="2", unit="kg"),
            item(0, quantity="70", cancelado_em="2026-04-04", custo_total=Decimal("300"), moeda="BRL"),
            item(1, quantity="0.2", custo_total=Decimal("0"), moeda="BRL", origem_custo="informado"),
            item(1, quantity="4", unit="kg"),
            item(1, product=1, quantity="7"),
            item(2, quantity="100", custo_total=Decimal("500"), moeda="BRL"),
            item(4, quantity="999", custo_total=Decimal("99999.99"), moeda="BRL"),
            item(5, quantity="888"),
        ])
        app_new = AplicacaoInsumo(cultura_gleba_id=cg.id, produto_base_id=produtos[0].id,
                                  data_aplicacao="2026-04-06", dose=2, unidade="L/ha",
                                  quantidade_utilizada=Decimal("0.3"), unidade_quantidade="L",
                                  custo_total=Decimal("1.25"), moeda="BRL", origem_custo="informado",
                                  criado_por_id=users["manager"].id, responsavel="Aplicador histórico")
        app_old = AplicacaoInsumo(cultura_gleba_id=cg.id, produto_base_id=produtos[1].id,
                                  data_aplicacao="2026-03-01", dose=3, unidade="kg/ha",
                                  responsavel="Legado textual")
        db.session.add_all([app_new, app_old,
                           AplicacaoInsumo(cultura_gleba_id=cg_crossed.id, produto_base_id=produtos[0].id,
                                           data_aplicacao="2026-04-01", responsavel="CROSSED_APPLICATION_SECRET"),
                           FinanceiroLancamento(propriedade_id=prop.id, tipo="receita", valor=100, data="2026-04-01"),
                           FinanceiroLancamento(propriedade_id=prop.id, tipo="despesa", valor=40, data="2026-04-01"),
                           ProdutoPreco(produto_id=produtos[1].id, valor=999, unidade="kg", moeda="BRL", status_validacao="pendente")])
        db.session.commit()
        app.report6_ids = {"prop": prop.id, "other": other.id, "areas": [area.id for area in areas],
                           "activities": [activity.id for activity in activities],
                           "products": [produto.id for produto in produtos], "old": app_old.id,
                           "users": {alias: user.id for alias, user in users.items()}}
    return app


def _login(app, alias="admin"):
    client = app.test_client()
    response = client.post("/auth/login", data={"email": f"{alias}@report6.invalid", "senha": "Report6!pass"})
    assert response.status_code == 302
    return client


def _pdf_text(data):
    chunks = []
    for match in re.finditer(rb"stream\r?\n(.*?)endstream", data, re.S):
        payload = match.group(1).strip()
        try:
            payload = zlib.decompress(base64.a85decode(payload, adobe=True))
        except (ValueError, zlib.error):
            continue
        chunks.append(payload.decode("latin-1"))
    return "\n".join(chunks)


@pytest.mark.parametrize("suffix", ["", "/exportar.csv", "/exportar.pdf"])
def test_operational_report_requires_login(operational_reports, suffix):
    response = operational_reports.test_client().get("/relatorios/operacionais" + suffix)
    assert response.status_code == 302
    assert "/auth/login" in response.location


@pytest.mark.parametrize("alias", ["admin", "manager", "worker"])
@pytest.mark.parametrize("suffix", ["", "/exportar.csv", "/exportar.pdf"])
def test_reports_enforce_cost_visibility_and_territory(operational_reports, alias, suffix):
    response = _login(operational_reports, alias).get("/relatorios/operacionais" + suffix + "?incluir_custos=true&propriedade_id=" + str(operational_reports.report6_ids["other"]))
    assert response.status_code == 200
    content = _pdf_text(response.data) if suffix.endswith("pdf") else response.get_data(as_text=True)
    for marker in ("FOREIGN_PROPERTY_SECRET", "FOREIGN_AREA_SECRET", "FOREIGN_ACTIVITY_SECRET", "FOREIGN_ACCOUNT_SECRET", "CROSSED_ACTIVITY_SECRET", "CROSSED_APPLICATION_SECRET"):
        assert marker not in content
    assert "Produto um" in content
    if alias == "worker":
        for marker in ("7.432,19", "7.433,44", "12,345678", "segredo_custo_operacional", "Custo unit", "Custo total"):
            assert marker not in content
    else:
        assert "7.432,19" in content and "7.433,44" in content
        assert "12,345678" in content and "segredo_custo_operacional" in content


def test_service_dto_omits_restricted_fields_and_preserves_history(operational_reports):
    with operational_reports.app_context():
        prop = db.session.get(Propriedade, operational_reports.report6_ids["prop"])
        dados = montar_relatorio_operacional(prop)
        assert not dados["incluir_custos"]
        assert "custos_por_moeda" not in dados
        assert dados["total"] == 6 and dados["total_ativos"] == 5
        for registro in dados["registros"]:
            assert not any("custo" in campo for campo in registro)
            for item in registro["itens"]:
                assert not any("custo" in campo or campo == "moeda" for campo in item)
        antigo = next(registro for registro in dados["registros"] if registro["fonte"] == "aplicacao" and registro["id"] == operational_reports.report6_ids["old"])
        assert antigo["itens"][0]["dose"] == Decimal("3")
        assert antigo["itens"][0]["quantidade_utilizada"] is None
        assert antigo["autor"] is None
        assert antigo["responsavel"] == "Legado textual"
        snapshot = next(registro for registro in dados["registros"] if registro["tipo_atividade"] == "Inspeção")
        assert snapshot["autor"] is None
        assert snapshot["responsavel"] == "Snapshot autorizado"


def test_consumption_is_exact_and_grouped_by_product_and_unit(operational_reports):
    with operational_reports.app_context():
        prop = db.session.get(Propriedade, operational_reports.report6_ids["prop"])
        dados = montar_relatorio_operacional(prop, incluir_custos=True)
        p1, p2 = operational_reports.report6_ids["products"]
        consumo = {(item["produto_id"], item["unidade"]): item["quantidade"] for item in dados["consumo"]}
        assert consumo == {(p1, "L"): Decimal("0.600001"), (p1, "kg"): Decimal("4"),
                           (p2, "L"): Decimal("7"), (p2, "kg"): Decimal("2")}
        assert dados["custos_por_moeda"] == [("BRL", Decimal("7433.44"))]
        assert all(isinstance(item["quantidade"], Decimal) for item in dados["consumo"])
        antigo = next(registro for registro in dados["registros"] if registro["fonte"] == "aplicacao" and registro["id"] == operational_reports.report6_ids["old"])
        assert antigo["itens"][0]["custo_total"] is None
        assert antigo["itens"][0]["custo_unitario"] is None
        assert dados["custos_ausentes"] == 4


@pytest.mark.parametrize("suffix", ["", "/exportar.csv", "/exportar.pdf"])
@pytest.mark.parametrize("area", ["foreign", "999999", "-1", "999999999999999999999999", "abc"])
def test_invalid_or_foreign_area_never_falls_back_to_all(operational_reports, suffix, area):
    if area == "foreign":
        area = str(operational_reports.report6_ids["areas"][2])
    response = _login(operational_reports).get("/relatorios/operacionais" + suffix, query_string={"gleba_id": area})
    assert response.status_code == 404
    assert b"FOREIGN_AREA_SECRET" not in response.data


@pytest.mark.parametrize("params", [{"data_inicio": "2026-02-30"}, {"data_fim": "nope"},
                                     {"data_inicio": "2026-05-01", "data_fim": "2026-04-01"},
                                     {"tipo_atividade": "x" * 121}])
@pytest.mark.parametrize("suffix", ["", "/exportar.csv", "/exportar.pdf"])
def test_operational_filters_are_validated(operational_reports, params, suffix):
    assert _login(operational_reports).get("/relatorios/operacionais" + suffix, query_string=params).status_code == 400


def test_period_type_area_filters_share_sources_without_duplicates(operational_reports):
    with operational_reports.app_context():
        prop = db.session.get(Propriedade, operational_reports.report6_ids["prop"])
        dados = montar_relatorio_operacional(prop, data_inicio="2026-04-01", data_fim="2026-04-02",
                                             gleba_id=operational_reports.report6_ids["areas"][0])
        assert [registro["tipo_atividade"] for registro in dados["registros"]] == ["Inspeção", "Irrigação"]
        assert len({(r["fonte"], r["id"]) for r in dados["registros"]}) == dados["total"]
        apps = montar_relatorio_operacional(prop, tipo_atividade="Aplicação de insumo")
        assert apps["total"] == 2
        assert all(registro["fonte"] == "aplicacao" for registro in apps["registros"])
        vazio = montar_relatorio_operacional(prop, gleba_id=operational_reports.report6_ids["areas"][1])
        assert vazio["total"] == 1 and vazio["registros"][0]["itens"] == []


def test_consultation_does_not_create_financial_entries_or_use_catalog_prices(operational_reports):
    client = _login(operational_reports)
    with operational_reports.app_context():
        counts = (FinanceiroLancamento.query.count(), AplicacaoInsumo.query.count(), AtividadeOperacional.query.count(), AtividadeItem.query.count())
    for suffix in ("", "/exportar.csv", "/exportar.pdf"):
        assert client.get("/relatorios/operacionais" + suffix).status_code == 200
    with operational_reports.app_context():
        assert counts == (FinanceiroLancamento.query.count(), AplicacaoInsumo.query.count(), AtividadeOperacional.query.count(), AtividadeItem.query.count())
        dados = montar_relatorio_financeiro(db.session.get(Propriedade, operational_reports.report6_ids["prop"]))
        assert dados["receitas"] == 100 and dados["despesas"] == 40 and dados["saldo"] == 60


@pytest.mark.parametrize("suffix", ["", "/exportar.csv", "/exportar.pdf"])
def test_empty_operational_history_is_exportable(operational_reports, suffix):
    response = _login(operational_reports, "worker").get(
        "/relatorios/operacionais" + suffix,
        query_string={"data_inicio": "2030-01-01", "data_fim": "2030-12-31"})
    assert response.status_code == 200
    content = _pdf_text(response.data) if suffix.endswith("pdf") else response.get_data(as_text=True)
    assert "Produto um" not in content and "segredo_custo_operacional" not in content
    if not suffix:
        assert "Nenhum registro operacional encontrado" in content


def test_report_formats_legacy_unknown_cost_as_absent_not_zero(operational_reports):
    client = _login(operational_reports)
    response = client.get("/relatorios/operacionais/exportar.csv", query_string={"data_fim": "2026-03-31"})
    rows = list(csv.reader(io.StringIO(response.get_data(as_text=True)), delimiter=";"))
    header = next(row for row in rows if row and row[0] == "Fonte")
    antigo = next(row for row in rows if row and row[0] == "Aplicação")
    assert antigo[header.index("Custo total")] == "—"
    assert antigo[header.index("Custo unitário")] == "—"
    assert antigo[header.index("Quantidade utilizada")] == "—"
    assert antigo[header.index("Dose")] == "3"


@pytest.mark.parametrize("alias", ["admin", "worker"])
def test_assistant_persists_consumption_without_individual_costs(operational_reports, alias):
    client = _login(operational_reports, alias)
    response = client.post("/ia/", data={"pergunta": "Resumo das atividades e consumo"})
    assert response.status_code == 200
    with operational_reports.app_context():
        resposta = IaInteracao.query.filter_by(usuario_id=operational_reports.report6_ids["users"][alias]).one().resposta
        assert "0,600001 L" in resposta and "Produto um" in resposta
        assert "7 kg" not in resposta
        for marker in ("7432", "7.432", "7.433", "segredo_custo_operacional", "12,345678", "FOREIGN", "CROSSED"):
            assert marker not in resposta
    content = client.get("/ia/").get_data(as_text=True)
    assert "60,00" in content  # agregado financeiro aprovado permanece


def test_csv_and_pdf_escape_new_free_text(operational_reports):
    with operational_reports.app_context():
        atividade = db.session.get(AtividadeOperacional, operational_reports.report6_ids["activities"][0])
        atividade.tipo_atividade = '=HYPERLINK("https://invalid.test")'
        atividade.observacao = '<b>Texto literal</b> & <img src="never"/>'
        db.session.commit()
    client = _login(operational_reports)
    response = client.get("/relatorios/operacionais/exportar.csv")
    rows = list(csv.reader(io.StringIO(response.get_data(as_text=True)), delimiter=";"))
    assert any(cell.startswith("'=HYPERLINK") for row in rows for cell in row)
    response_pdf = client.get("/relatorios/operacionais/exportar.pdf")
    assert response_pdf.status_code == 200 and response_pdf.data.startswith(b"%PDF")
    assert "Texto literal" in _pdf_text(response_pdf.data)
    response_html = client.get("/relatorios/operacionais")
    assert b"&lt;b&gt;Texto literal&lt;/b&gt;" in response_html.data


def test_decimal_display_preserves_precision_and_unknowns():
    assert formatar_decimal_operacional(Decimal("900719925474.123456")) == "900.719.925.474,123456"
    assert formatar_decimal_operacional(None) == "—"
    assert formatar_decimal_operacional(Decimal("0"), 2) == "0,00"
    assert formatar_decimal_operacional(Decimal("NaN")) == "—"
