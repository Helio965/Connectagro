"""Testes do Dashboard Operacional (Etapa 5.8)."""
import pytest

from app.extensions import db
from app.utils.auth import gerar_hash_senha


def _login(app_db, email):
    client = app_db.test_client()
    client.post("/auth/login", data={"email": email, "senha": "senha123"})
    return client


def _criar_usuario_propriedade(email, nome_propriedade):
    from app.models import Propriedade, Usuario

    usuario = Usuario(nome=email, email=email, perfil="tecnico", ativo=True,
                      senha_hash=gerar_hash_senha("senha123"))
    db.session.add(usuario)
    db.session.commit()
    propriedade = Propriedade(usuario_id=usuario.id, nome=nome_propriedade)
    db.session.add(propriedade)
    db.session.commit()
    return usuario, propriedade


def _popular_cenario_dashboard():
    from app.models import (
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

    _, prop_a = _criar_usuario_propriedade("a@connectagro.com", "Fazenda A")
    _, prop_b = _criar_usuario_propriedade("b@connectagro.com", "Fazenda B")
    _criar_usuario_propriedade("vazio@connectagro.com", "Fazenda Vazia")

    gleba_a1 = Gleba(propriedade_id=prop_a.id, nome="Talhão A1", area_ha=10.5)
    gleba_a2 = Gleba(propriedade_id=prop_a.id, nome="Talhão A2")
    gleba_b = Gleba(propriedade_id=prop_b.id, nome="Talhão B secreto", area_ha=999)
    db.session.add_all([gleba_a1, gleba_a2, gleba_b])
    db.session.commit()

    culturas_a = [
        Cultura(propriedade_id=prop_a.id, nome="Soja", status="planejada"),
        Cultura(propriedade_id=prop_a.id, nome="Milho", status="em_andamento"),
        Cultura(propriedade_id=prop_a.id, nome="Trigo", status="colhida"),
        Cultura(propriedade_id=prop_a.id, nome="Algodão", status="cancelada"),
    ]
    cultura_b = Cultura(propriedade_id=prop_b.id, nome="Cultura secreta", status="em_andamento")
    db.session.add_all(culturas_a + [cultura_b])
    db.session.commit()

    cg_a1 = CulturaGleba(cultura_id=culturas_a[0].id, gleba_id=gleba_a1.id)
    cg_a2 = CulturaGleba(cultura_id=culturas_a[1].id, gleba_id=gleba_a2.id)
    cg_b = CulturaGleba(cultura_id=cultura_b.id, gleba_id=gleba_b.id)
    db.session.add_all([cg_a1, cg_a2, cg_b])
    db.session.commit()

    db.session.add_all([
        FinanceiroLancamento(propriedade_id=prop_a.id, tipo="receita", valor=1000,
                              data="2026-01-10", descricao="Venda soja"),
        FinanceiroLancamento(propriedade_id=prop_a.id, tipo="despesa", valor=250,
                              data="2026-01-11", descricao="Insumos"),
        FinanceiroLancamento(propriedade_id=prop_b.id, tipo="receita", valor=99999,
                              data="2026-01-12", descricao="Receita secreta"),
    ])
    db.session.add_all([
        EquipeMembro(propriedade_id=prop_a.id, nome="Ana", ativo=True),
        EquipeMembro(propriedade_id=prop_a.id, nome="Bruno", ativo=True),
        EquipeMembro(propriedade_id=prop_a.id, nome="Carla", ativo=False),
        EquipeMembro(propriedade_id=prop_b.id, nome="Equipe secreta", ativo=True),
    ])
    db.session.commit()

    db.session.add_all([
        ColheitaRegistro(cultura_gleba_id=cg_a1.id, data_colheita="2026-03-10",
                         quantidade=30, unidade="sacas", qualidade="boa"),
        ColheitaRegistro(cultura_gleba_id=cg_a2.id, data_colheita="2026-03-11",
                         quantidade=10, unidade="sacas", qualidade="boa"),
        ColheitaRegistro(cultura_gleba_id=cg_b.id, data_colheita="2026-03-12",
                         quantidade=999, unidade="sacas", qualidade="secreta"),
    ])

    glifosato = ProdutoBase(nome="Glifosato", slug="glifosato", classe="defensivo",
                            categoria="herbicida")
    ureia = ProdutoBase(nome="Ureia", slug="ureia", classe="fertilizante",
                        categoria="fertilizante nitrogenado",
                        status_regulatorio="tipo_tecnico_generico")
    paraquate = ProdutoBase(nome="Paraquate", slug="paraquate", classe="defensivo",
                            categoria="herbicida", status_sistema="bloqueado_historico",
                            status_regulatorio="bloqueado_historico")
    db.session.add_all([glifosato, ureia, paraquate])
    db.session.commit()

    db.session.add_all([
        AplicacaoInsumo(cultura_gleba_id=cg_a1.id, produto_base_id=glifosato.id,
                        data_aplicacao="2026-02-10", dose=2.5, unidade="L/ha"),
        AplicacaoInsumo(cultura_gleba_id=cg_b.id, produto_base_id=ureia.id,
                        data_aplicacao="2026-02-11", dose=999, unidade="kg/ha"),
    ])
    db.session.add_all([
        UploadArquivo(propriedade_id=prop_a.id, nome_original="relatorio-a.pdf",
                      caminho="propriedade_1/a.pdf", tamanho=500),
        UploadArquivo(propriedade_id=prop_a.id, nome_original="mapa-a.txt",
                      caminho="propriedade_1/a.txt", tamanho=1024),
        UploadArquivo(propriedade_id=prop_b.id, nome_original="arquivo-secreto.pdf",
                      caminho="propriedade_2/b.pdf", tamanho=99999),
    ])
    db.session.commit()


@pytest.fixture
def app_db(app):
    with app.app_context():
        db.create_all()
        _popular_cenario_dashboard()
    return app


def _corpo_dashboard(app_db, email="a@connectagro.com"):
    client = _login(app_db, email)
    resp = client.get("/")
    return resp, resp.data.decode("utf-8")


def test_dashboard_exige_login(app_db):
    resp = app_db.test_client().get("/")
    assert resp.status_code == 302
    assert "/auth/login" in resp.headers["Location"]


def test_dashboard_com_login_responde_200(app_db):
    resp, _ = _corpo_dashboard(app_db)
    assert resp.status_code == 200


def test_dashboard_mostra_nome_da_propriedade_atual(app_db):
    _, corpo = _corpo_dashboard(app_db)
    assert "Fazenda A" in corpo
    assert "Fazenda B" not in corpo


def test_dashboard_mostra_glebas_e_nao_vaza_outra_propriedade(app_db):
    _, corpo = _corpo_dashboard(app_db)
    assert "Glebas" in corpo
    assert "10,50 ha no total" in corpo
    assert "1 sem área" in corpo
    assert "Talhão B secreto" not in corpo


def test_dashboard_mostra_culturas_por_status(app_db):
    _, corpo = _corpo_dashboard(app_db)
    for texto in ("Planejada", "Em andamento", "Colhida", "Cancelada"):
        assert texto in corpo
    assert "2 associações cultura↔gleba" in corpo
    assert "Cultura secreta" not in corpo


def test_dashboard_calcula_financeiro_da_propriedade(app_db):
    _, corpo = _corpo_dashboard(app_db)
    assert "R$ 1.000,00" in corpo
    assert "R$ 250,00" in corpo
    assert "R$ 750,00" in corpo
    assert "Venda soja" in corpo
    assert "Receita secreta" not in corpo
    assert "R$ 99.999,00" not in corpo


def test_dashboard_mostra_equipe_e_ativos(app_db):
    _, corpo = _corpo_dashboard(app_db)
    assert "Equipe" in corpo
    assert "2 ativos · 1 inativos" in corpo
    assert "Equipe secreta" not in corpo


def test_dashboard_mostra_colheitas_e_soma_por_unidade(app_db):
    _, corpo = _corpo_dashboard(app_db)
    assert "Últimas colheitas" in corpo
    assert "Soja" in corpo
    assert "Milho" in corpo
    assert "sacas" in corpo
    assert "40,00" in corpo
    assert "999,00" not in corpo


def test_dashboard_mostra_aplicacoes_sem_vazar_outra_propriedade(app_db):
    _, corpo = _corpo_dashboard(app_db)
    assert "Últimas aplicações" in corpo
    assert "Glifosato" in corpo
    assert "2,50 L/ha" in corpo
    assert "999,00 kg/ha" not in corpo


def test_dashboard_mostra_uploads_sem_vazar_outra_propriedade(app_db):
    _, corpo = _corpo_dashboard(app_db)
    assert "relatorio-a.pdf" in corpo
    assert "mapa-a.txt" in corpo
    assert "1,5 KB armazenados" in corpo
    assert "arquivo-secreto.pdf" not in corpo


def test_dashboard_mostra_totais_globais_do_catalogo(app_db):
    _, corpo = _corpo_dashboard(app_db)
    assert "2 defensivos · 1 fertilizantes" in corpo
    assert "1 produtos bloqueados/históricos" in corpo


def test_dashboard_mostra_estados_vazios(app_db):
    resp, corpo = _corpo_dashboard(app_db, "vazio@connectagro.com")
    assert resp.status_code == 200
    assert "Fazenda Vazia" in corpo
    assert "Nenhuma gleba cadastrada ainda." in corpo
    assert "Nenhuma cultura cadastrada ainda." in corpo
    assert "Nenhum lançamento financeiro cadastrado." in corpo
    assert "Nenhum upload enviado." in corpo


def test_dashboard_contem_atalhos_principais(app_db):
    _, corpo = _corpo_dashboard(app_db)
    for texto in (
        "Nova Gleba",
        "Nova Cultura",
        "Novo Lançamento Financeiro",
        "Nova Colheita",
        "Nova Aplicação",
        "Novo Upload",
        "Catálogo de Defensivos",
        "Catálogo de Fertilizantes",
    ):
        assert texto in corpo


def test_dashboard_nao_contem_termos_de_venda(app_db):
    _, corpo = _corpo_dashboard(app_db)
    corpo = corpo.lower()
    for proibido in ("comprar", "checkout", "carrinho", "cotação", "finalizar compra"):
        assert proibido not in corpo
