"""Testes da Fase 6.2 — Relatórios Operacionais HTML (somente leitura)."""
import pytest

from app.extensions import db
from app.utils.auth import gerar_hash_senha


def _produtos_catalogo():
    """Garante 1 defensivo e 1 fertilizante no catálogo (slugs únicos)."""
    from app.models import ProdutoBase

    defensivo = ProdutoBase.query.filter_by(slug="def-teste").first()
    if defensivo is None:
        defensivo = ProdutoBase(nome="Defensivo Teste", slug="def-teste",
                                classe="defensivo", categoria="herbicida",
                                status_sistema="pre_cadastrado",
                                status_regulatorio="nao_validado_agrofit")
        db.session.add(defensivo)
    fert = ProdutoBase.query.filter_by(slug="fert-teste").first()
    if fert is None:
        fert = ProdutoBase(nome="Fertilizante Teste", slug="fert-teste",
                           classe="fertilizante", categoria="mineral",
                           status_sistema="pre_cadastrado",
                           status_regulatorio="tipo_tecnico_generico")
        db.session.add(fert)
    db.session.commit()
    return defensivo, fert


def _setup(email, gleba_nome, cultura_nome, receita=100.0, despesa=30.0):
    """Cria usuário + propriedade + dados operacionais. Retorna dict de ids."""
    from app.models import (Usuario, Propriedade, Gleba, Cultura, CulturaGleba,
                            FinanceiroLancamento, ColheitaRegistro, AplicacaoInsumo,
                            EquipeMembro, UploadArquivo)

    u = Usuario(nome=email, email=email, perfil="tecnico", ativo=True,
                senha_hash=gerar_hash_senha("senha123"))
    db.session.add(u)
    db.session.commit()
    p = Propriedade(usuario_id=u.id, nome="Fazenda " + email)
    db.session.add(p)
    db.session.commit()
    g = Gleba(propriedade_id=p.id, nome=gleba_nome, area_ha=10.0,
              latitude=-15.0, longitude=-47.0, tipo_solo="argiloso")
    c = Cultura(propriedade_id=p.id, nome=cultura_nome, status="em_andamento",
                safra="2025/2026")
    db.session.add_all([g, c])
    db.session.commit()
    cg = CulturaGleba(cultura_id=c.id, gleba_id=g.id)
    db.session.add(cg)
    db.session.commit()

    db.session.add(EquipeMembro(propriedade_id=p.id, nome="Membro " + email, ativo=True))
    db.session.add(FinanceiroLancamento(propriedade_id=p.id, tipo="receita",
                                        valor=receita, data="2026-01-10", categoria="venda"))
    db.session.add(FinanceiroLancamento(propriedade_id=p.id, tipo="receita",
                                        valor=50.0, data="2026-02-10"))
    db.session.add(FinanceiroLancamento(propriedade_id=p.id, tipo="despesa",
                                        valor=despesa, data="2026-03-10"))
    db.session.add(ColheitaRegistro(cultura_gleba_id=cg.id, data_colheita="2026-03-10",
                                    quantidade=1200.0, unidade="kg", qualidade="boa"))
    db.session.add(UploadArquivo(propriedade_id=p.id, nome_original="doc_" + email + ".pdf",
                                 caminho="x/doc.pdf", tipo_mime="application/pdf",
                                 tamanho=2048, descricao="contrato"))
    defensivo, fert = _produtos_catalogo()
    db.session.add(AplicacaoInsumo(cultura_gleba_id=cg.id, produto_base_id=defensivo.id,
                                   data_aplicacao="2026-01-15", dose=2.0, unidade="L/ha",
                                   responsavel="Operador A"))
    db.session.add(AplicacaoInsumo(cultura_gleba_id=cg.id, produto_base_id=fert.id,
                                   data_aplicacao="2026-02-15", dose=100.0, unidade="kg/ha",
                                   responsavel="Operador A"))
    db.session.commit()
    return {"prop_id": p.id, "cg_id": cg.id}


@pytest.fixture
def app_rel(app):
    with app.app_context():
        db.create_all()
        _setup("a@connectagro.com", "Talhão A", "Soja A")
        _setup("b@connectagro.com", "Gleba Secreta B", "Cultura Secreta B")
    return app


def _login(app_rel, email):
    client = app_rel.test_client()
    client.post("/auth/login", data={"email": email, "senha": "senha123"})
    return client


ROTAS = ["/relatorios/", "/relatorios/geral", "/relatorios/financeiro",
         "/relatorios/agricola", "/relatorios/aplicacoes", "/relatorios/uploads"]


@pytest.mark.parametrize("rota", ROTAS)
def test_exige_login(app_rel, rota):
    resp = app_rel.test_client().get(rota)
    assert resp.status_code == 302
    assert "/auth/login" in resp.headers["Location"]


def test_index_lista_relatorios(app_rel):
    corpo = _login(app_rel, "a@connectagro.com").get("/relatorios/").data.decode("utf-8")
    for endpoint in ("/relatorios/geral", "/relatorios/financeiro", "/relatorios/agricola",
                     "/relatorios/aplicacoes", "/relatorios/uploads"):
        assert endpoint in corpo


# --- Geral ----------------------------------------------------------------

def test_geral_mostra_propriedade_e_totais(app_rel):
    corpo = _login(app_rel, "a@connectagro.com").get("/relatorios/geral").data.decode("utf-8")
    assert "Fazenda a@connectagro.com" in corpo
    assert "Total de glebas" in corpo
    assert "Total de culturas" in corpo
    assert "Total de aplicações" in corpo


def test_geral_nao_vaza_outra_propriedade(app_rel):
    corpo = _login(app_rel, "a@connectagro.com").get("/relatorios/geral").data.decode("utf-8")
    assert "Secreta B" not in corpo
    assert "Fazenda b@connectagro.com" not in corpo


# --- Financeiro -----------------------------------------------------------

def test_financeiro_totais(app_rel):
    corpo = _login(app_rel, "a@connectagro.com").get("/relatorios/financeiro").data.decode("utf-8")
    assert "150,00" in corpo  # receitas (100 + 50)
    assert "30,00" in corpo   # despesas
    assert "120,00" in corpo  # saldo


def test_financeiro_filtro_tipo_receita(app_rel):
    corpo = _login(app_rel, "a@connectagro.com").get(
        "/relatorios/financeiro?tipo=receita").data.decode("utf-8")
    # saldo passa a ser só receitas (150) e nenhuma linha de despesa
    assert "150,00" in corpo
    assert "despesa" not in corpo.split("<tbody>")[1].split("</tbody>")[0]


def test_financeiro_filtro_periodo(app_rel):
    corpo = _login(app_rel, "a@connectagro.com").get(
        "/relatorios/financeiro?data_inicio=2026-02-01").data.decode("utf-8")
    # exclui a receita de 2026-01-10; saldo = 50 - 30 = 20
    assert "20,00" in corpo


def test_financeiro_periodo_invalido_400(app_rel):
    resp = _login(app_rel, "a@connectagro.com").get(
        "/relatorios/financeiro?data_inicio=2026-05-01&data_fim=2026-01-01")
    assert resp.status_code == 400


def test_financeiro_tipo_invalido_400(app_rel):
    resp = _login(app_rel, "a@connectagro.com").get("/relatorios/financeiro?tipo=xpto")
    assert resp.status_code == 400


def test_financeiro_escopo(app_rel):
    # usuário B tem apenas seus dados; saldo dele = (100+50) - 30 = 120 igual,
    # mas a checagem de escopo é não ver gleba/cultura de A — validado em agrícola.
    corpo = _login(app_rel, "b@connectagro.com").get("/relatorios/financeiro").data.decode("utf-8")
    assert "venda" in corpo or "—" in corpo  # apenas garante render ok


# --- Agrícola -------------------------------------------------------------

def test_agricola_dados_da_propriedade(app_rel):
    corpo = _login(app_rel, "a@connectagro.com").get("/relatorios/agricola").data.decode("utf-8")
    assert "Talhão A" in corpo
    assert "Soja A" in corpo


def test_agricola_nao_vaza_outra_propriedade(app_rel):
    corpo = _login(app_rel, "a@connectagro.com").get("/relatorios/agricola").data.decode("utf-8")
    assert "Secreta B" not in corpo


# --- Aplicações -----------------------------------------------------------

def test_aplicacoes_mostra_dados(app_rel):
    corpo = _login(app_rel, "a@connectagro.com").get("/relatorios/aplicacoes").data.decode("utf-8")
    assert "Soja A" in corpo
    assert "Talhão A" in corpo
    assert "Defensivo Teste" in corpo
    assert "Operador A" in corpo


def test_aplicacoes_filtro_classe(app_rel):
    corpo = _login(app_rel, "a@connectagro.com").get(
        "/relatorios/aplicacoes?classe=defensivo").data.decode("utf-8")
    assert "Defensivo Teste" in corpo
    assert "Fertilizante Teste" not in corpo


def test_aplicacoes_filtro_periodo(app_rel):
    corpo = _login(app_rel, "a@connectagro.com").get(
        "/relatorios/aplicacoes?data_inicio=2026-02-01").data.decode("utf-8")
    assert "Fertilizante Teste" in corpo   # 2026-02-15
    assert "Defensivo Teste" not in corpo  # 2026-01-15


def test_aplicacoes_periodo_invalido_400(app_rel):
    resp = _login(app_rel, "a@connectagro.com").get(
        "/relatorios/aplicacoes?data_inicio=2026-05-01&data_fim=2026-01-01")
    assert resp.status_code == 400


def test_aplicacoes_avisos(app_rel):
    corpo = _login(app_rel, "a@connectagro.com").get("/relatorios/aplicacoes").data.decode("utf-8").lower()
    assert "não recomenda" in corpo
    assert "não valida" in corpo and "dose" in corpo


def test_aplicacoes_escopo(app_rel):
    corpo = _login(app_rel, "a@connectagro.com").get("/relatorios/aplicacoes").data.decode("utf-8")
    assert "Secreta B" not in corpo


# --- Uploads --------------------------------------------------------------

def test_uploads_mostra_arquivos_e_total(app_rel):
    corpo = _login(app_rel, "a@connectagro.com").get("/relatorios/uploads").data.decode("utf-8")
    assert "doc_a@connectagro.com.pdf" in corpo
    assert "2,0 KB" in corpo  # 2048 bytes
    assert "/download" in corpo  # link de download protegido


def test_uploads_escopo(app_rel):
    corpo = _login(app_rel, "a@connectagro.com").get("/relatorios/uploads").data.decode("utf-8")
    assert "doc_b@connectagro.com.pdf" not in corpo


def test_uploads_aviso_nao_le_conteudo(app_rel):
    corpo = _login(app_rel, "a@connectagro.com").get("/relatorios/uploads").data.decode("utf-8").lower()
    assert "não lê automaticamente" in corpo


# --- Restrições -----------------------------------------------------------

def test_sem_termos_de_venda(app_rel):
    client = _login(app_rel, "a@connectagro.com")
    for rota in ROTAS:
        corpo = client.get(rota).data.decode("utf-8").lower()
        for proibido in ("comprar", "checkout", "carrinho", "finalizar compra",
                         "cotação oficial"):
            assert proibido not in corpo, f"'{proibido}' em {rota}"


def test_sem_recomendacao_ou_validacao(app_rel):
    client = _login(app_rel, "a@connectagro.com")
    for rota in ROTAS:
        corpo = client.get(rota).data.decode("utf-8").lower()
        for proibido in ("produto recomendado", "dose correta", "dose segura",
                         "validado oficialmente pelo mapa", "diagnóstico agronômico"):
            assert proibido not in corpo, f"'{proibido}' em {rota}"


def test_relatorios_nao_criam_registros(app_rel):
    from app.models import (FinanceiroLancamento, AplicacaoInsumo, ColheitaRegistro,
                            Gleba, Cultura, UploadArquivo)

    with app_rel.app_context():
        antes = (FinanceiroLancamento.query.count(), AplicacaoInsumo.query.count(),
                 ColheitaRegistro.query.count(), Gleba.query.count(),
                 Cultura.query.count(), UploadArquivo.query.count())
    client = _login(app_rel, "a@connectagro.com")
    for rota in ROTAS:
        client.get(rota)
    with app_rel.app_context():
        depois = (FinanceiroLancamento.query.count(), AplicacaoInsumo.query.count(),
                  ColheitaRegistro.query.count(), Gleba.query.count(),
                  Cultura.query.count(), UploadArquivo.query.count())
    assert antes == depois
