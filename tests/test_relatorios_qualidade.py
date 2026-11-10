"""Regressões de filtros e consultas dos relatórios, com banco real isolado."""
from decimal import Decimal

import pytest
from sqlalchemy import event

from app.extensions import db
from app.models import (
    AplicacaoInsumo, AtividadeItem, AtividadeOperacional, Cultura, CulturaGleba,
    Gleba, LogAuditoria, ProdutoBase, Propriedade, Usuario,
)
from app.services.relatorios_service import (
    FiltroInvalidoError, montar_relatorio_operacional, validar_periodo,
)
from app.utils.auth import gerar_hash_senha
from tests.factories import criar_propriedade_com_vinculo


@pytest.mark.parametrize("valor", [
    "2026-02-30", "2026-2-03", "20260203", "2026-W01-1", "não é data", 0,
])
def test_periodo_recusa_datas_impossiveis_ou_fora_do_formato(valor):
    for inicio, fim in ((valor, None), (None, valor)):
        with pytest.raises(FiltroInvalidoError):
            validar_periodo(inicio, fim)


def test_periodo_aceita_dia_bissexto_e_limites_opcionais():
    for inicio, fim in ((None, None), ("", ""), ("2024-02-29", None),
                        (None, "2024-02-29"), ("2024-02-29", "2024-03-01")):
        validar_periodo(inicio, fim)
    with pytest.raises(FiltroInvalidoError):
        validar_periodo("2024-03-01", "2024-02-29")


@pytest.fixture
def cliente_relatorios(app):
    with app.app_context():
        db.create_all()
        usuario = Usuario(nome="Administrador de testes", email="relatorio8@invalid.test",
                          senha_hash=gerar_hash_senha("Senha-relatorio8!"),
                          perfil="admin", ativo=True)
        db.session.add(usuario)
        db.session.flush()
        criar_propriedade_com_vinculo(usuario.id, nome="Relatórios isolados")
        db.session.commit()
    cliente = app.test_client()
    assert cliente.post("/auth/login", data={"email": "relatorio8@invalid.test",
                                             "senha": "Senha-relatorio8!"}).status_code == 302
    return cliente


@pytest.mark.parametrize("relatorio", ["financeiro", "aplicacoes"])
@pytest.mark.parametrize("sufixo", ["", "/exportar.csv", "/exportar.pdf"])
@pytest.mark.parametrize("campo", ["data_inicio", "data_fim"])
def test_data_invalida_nao_gera_relatorio_nem_exportacao_de_sucesso(
        app, cliente_relatorios, relatorio, sufixo, campo):
    resposta = cliente_relatorios.get("/relatorios/" + relatorio + sufixo,
                                      query_string={campo: "2026-02-30"})
    assert resposta.status_code == 400
    assert "Content-Disposition" not in resposta.headers
    assert not resposta.data.startswith(b"%PDF-")
    with app.app_context():
        assert LogAuditoria.query.filter_by(acao="exportacao.gerada").count() == 0
        if sufixo:
            assert LogAuditoria.query.filter_by(acao="exportacao.falha").count() == 1


@pytest.mark.parametrize("fonte", ["atividade", "aplicacao"])
def test_consultas_do_relatorio_nao_crescem_por_area_cultura_e_produto(app, fonte):
    with app.app_context():
        db.create_all()
        usuario = Usuario(nome="Responsável", email="consultas8@invalid.test",
                          senha_hash="sem-login-neste-teste", perfil="admin", ativo=True)
        db.session.add(usuario)
        db.session.flush()
        propriedade = Propriedade(usuario_id=usuario.id, nome="Consultas isoladas")
        db.session.add(propriedade)
        db.session.flush()
        propriedade_id = propriedade.id

        def adicionar(inicio, quantidade):
            for indice in range(inicio, inicio + quantidade):
                area = Gleba(propriedade_id=propriedade_id, nome=f"Área {indice}")
                cultura = Cultura(propriedade_id=propriedade_id, nome=f"Cultura {indice}")
                produto = ProdutoBase(nome=f"Produto {indice}", slug=f"consultas8-{indice}",
                                      classe="fertilizante")
                db.session.add_all([area, cultura, produto])
                db.session.flush()
                associacao = CulturaGleba(gleba_id=area.id, cultura_id=cultura.id)
                db.session.add(associacao)
                db.session.flush()
                dados_item = dict(produto_base_id=produto.id,
                                  quantidade_utilizada=Decimal("0.100001"),
                                  unidade_quantidade="L", custo_total=Decimal("1.23"),
                                  moeda="BRL", origem_custo="informado_usuario")
                if fonte == "atividade":
                    atividade = AtividadeOperacional(gleba_id=area.id,
                        cultura_gleba_id=associacao.id, tipo_atividade="Inspeção",
                        data_execucao="2026-11-10")
                    atividade.itens.append(AtividadeItem(**dados_item))
                    db.session.add(atividade)
                else:
                    db.session.add(AplicacaoInsumo(cultura_gleba_id=associacao.id,
                        data_aplicacao="2026-11-10", **dados_item))
            db.session.commit()

        def medir(incluir_custos=False):
            # Limpar o identity map impede que os objetos do preparo ocultem N+1.
            db.session.remove()
            prop = db.session.get(Propriedade, propriedade_id)
            consultas = []

            def registrar(_conexao, _cursor, sql, _parametros, _contexto, _muitos):
                if sql.lstrip().upper().startswith("SELECT"):
                    consultas.append(sql)

            engine = db.engine
            event.listen(engine, "after_cursor_execute", registrar)
            try:
                resultado = montar_relatorio_operacional(prop, incluir_custos=incluir_custos)
            finally:
                event.remove(engine, "after_cursor_execute", registrar)
            return resultado, len(consultas)

        adicionar(0, 1)
        primeiro, consultas_uma = medir()
        assert primeiro["total"] == 1
        adicionar(1, 9)
        varios, consultas_dez = medir()
        assert varios["total"] == 10
        assert consultas_dez <= consultas_uma + 1
        assert sum(item["quantidade"] for item in varios["consumo"]) == Decimal("1.000010")
        for registro in varios["registros"]:
            assert registro["fonte"] == fonte
            assert registro["gleba"].startswith("Área ")
            assert registro["cultura"].startswith("Cultura ")
            assert registro["itens"][0]["produto"].startswith("Produto ")
            assert "custo_total" not in registro["itens"][0]
        com_custos, consultas_custos = medir(incluir_custos=True)
        assert consultas_custos <= consultas_uma + 1
        assert com_custos["custos_por_moeda"] == [("BRL", Decimal("12.30"))]
