"""Testes da IA Simulada Operacional (Fase 6.1)."""
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


def _popular_cenario_ia():
    from app.models import (
        AplicacaoInsumo,
        ColheitaRegistro,
        Cultura,
        CulturaGleba,
        FinanceiroLancamento,
        Gleba,
        IaInteracao,
        ProdutoBase,
        Propriedade,
        UploadArquivo,
    )

    usuario_a, prop_a = _criar_usuario_propriedade("a@connectagro.com", "Fazenda A")
    usuario_b, prop_b = _criar_usuario_propriedade("b@connectagro.com", "Fazenda B")
    prop_a2 = Propriedade(usuario_id=usuario_a.id, nome="Fazenda A2")
    db.session.add(prop_a2)
    db.session.commit()

    gleba_a1 = Gleba(propriedade_id=prop_a.id, nome="Talhão A1", area_ha=10.5)
    gleba_a2 = Gleba(propriedade_id=prop_a.id, nome="Talhão A2")
    gleba_b = Gleba(propriedade_id=prop_b.id, nome="Talhão B secreto", area_ha=999)
    db.session.add_all([gleba_a1, gleba_a2, gleba_b])
    db.session.commit()

    cultura_a1 = Cultura(propriedade_id=prop_a.id, nome="Soja", status="planejada")
    cultura_a2 = Cultura(propriedade_id=prop_a.id, nome="Milho", status="em_andamento")
    cultura_b = Cultura(propriedade_id=prop_b.id, nome="Cultura secreta", status="colhida")
    db.session.add_all([cultura_a1, cultura_a2, cultura_b])
    db.session.commit()

    cg_a1 = CulturaGleba(cultura_id=cultura_a1.id, gleba_id=gleba_a1.id)
    cg_a2 = CulturaGleba(cultura_id=cultura_a2.id, gleba_id=gleba_a2.id)
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
    db.session.commit()

    db.session.add_all([
        ColheitaRegistro(cultura_gleba_id=cg_a1.id, data_colheita="2026-03-10",
                         quantidade=30, unidade="sacas", qualidade="boa"),
        ColheitaRegistro(cultura_gleba_id=cg_a2.id, data_colheita="2026-03-11",
                         quantidade=2, unidade="ton", qualidade="boa"),
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
    db.session.add_all([
        IaInteracao(usuario_id=usuario_a.id, propriedade_id=prop_a.id,
                    pergunta="Histórico atual", resposta="Resposta atual", tipo="simulada"),
        IaInteracao(usuario_id=usuario_b.id, propriedade_id=prop_b.id,
                    pergunta="Pergunta secreta outro usuário", resposta="Resposta secreta", tipo="simulada"),
        IaInteracao(usuario_id=usuario_a.id, propriedade_id=prop_a2.id,
                    pergunta="Pergunta de outra propriedade", resposta="Resposta outra propriedade", tipo="simulada"),
    ])
    db.session.commit()


@pytest.fixture
def app_db(app):
    with app.app_context():
        db.create_all()
        _popular_cenario_ia()
    return app


def _corpo_ia(app_db, email="a@connectagro.com"):
    client = _login(app_db, email)
    resp = client.get("/ia/")
    return resp, resp.data.decode("utf-8")


def _post_ia(app_db, pergunta="Faça um resumo da propriedade.", email="a@connectagro.com"):
    client = _login(app_db, email)
    resp = client.post("/ia/", data={"pergunta": pergunta})
    return resp, resp.data.decode("utf-8")


def test_ia_exige_login(app_db):
    resp = app_db.test_client().get("/ia/")
    assert resp.status_code == 302
    assert "/auth/login" in resp.headers["Location"]


def test_ia_com_login_responde_200(app_db):
    resp, corpo = _corpo_ia(app_db)
    assert resp.status_code == 200
    assert "IA Simulada" in corpo
    assert "Apoio operacional do MVP" in corpo


def test_ia_mostra_avisos_obrigatorios(app_db):
    _, corpo = _corpo_ia(app_db)
    for texto in (
        "A IA do MVP é simulada, baseada em regras simples",
        "Não recomenda produtos.",
        "Não valida dose.",
        "Não faz diagnóstico agronômico.",
        "Não consulta internet ou fontes oficiais em tempo real.",
        "Não lê o conteúdo de arquivos enviados.",
    ):
        assert texto in corpo


def test_post_ia_pergunta_valida_salva_interacao(app_db):
    from app.models import IaInteracao

    resp, corpo = _post_ia(app_db, "Faça um resumo da propriedade.")
    assert resp.status_code == 200
    assert "Resumo operacional da propriedade" in corpo
    with app_db.app_context():
        interacao = IaInteracao.query.filter_by(pergunta="Faça um resumo da propriedade.").one()
        assert interacao.tipo == "simulada"
        assert "Resumo operacional da propriedade" in interacao.resposta


def test_post_ia_vincula_usuario_atual(app_db):
    from app.models import IaInteracao, Usuario

    _post_ia(app_db, "Como está o financeiro?")
    with app_db.app_context():
        usuario = Usuario.query.filter_by(email="a@connectagro.com").one()
        interacao = IaInteracao.query.filter_by(pergunta="Como está o financeiro?").one()
        assert interacao.usuario_id == usuario.id


def test_post_ia_vincula_propriedade_atual(app_db):
    from app.models import IaInteracao, Propriedade, Usuario

    _post_ia(app_db, "Tenho propriedades sem área?")
    with app_db.app_context():
        usuario = Usuario.query.filter_by(email="a@connectagro.com").one()
        propriedade = Propriedade.query.filter_by(usuario_id=usuario.id, nome="Fazenda A").one()
        interacao = IaInteracao.query.filter_by(pergunta="Tenho propriedades sem área?").one()
        assert interacao.propriedade_id == propriedade.id


def test_post_ia_pergunta_vazia_retorna_400(app_db):
    from app.models import IaInteracao

    resp, corpo = _post_ia(app_db, "")
    assert resp.status_code == 400
    assert "Informe uma pergunta com pelo menos 2 caracteres." in corpo
    with app_db.app_context():
        assert IaInteracao.query.filter_by(pergunta="").count() == 0


def test_post_ia_pergunta_longa_retorna_400(app_db):
    from app.models import IaInteracao

    pergunta = "a" * 1001
    resp, corpo = _post_ia(app_db, pergunta)
    assert resp.status_code == 400
    assert "A pergunta deve ter no máximo 1000 caracteres." in corpo
    with app_db.app_context():
        assert IaInteracao.query.filter_by(pergunta=pergunta).count() == 0


def test_historico_mostra_apenas_usuario_e_propriedade_atual(app_db):
    _, corpo = _corpo_ia(app_db)
    assert "Histórico atual" in corpo
    assert "Pergunta secreta outro usuário" not in corpo
    assert "Resposta secreta" not in corpo
    assert "Pergunta de outra propriedade" not in corpo
    assert "Resposta outra propriedade" not in corpo


def test_resposta_financeiro_retorna_receitas_despesas_saldo(app_db):
    resp, corpo = _post_ia(app_db, "Como está o financeiro?")
    assert resp.status_code == 200
    assert "Resumo financeiro" in corpo
    assert "Receitas: R$ 1.000,00" in corpo
    assert "Despesas: R$ 250,00" in corpo
    assert "Saldo: R$ 750,00" in corpo
    assert "R$ 99.999,00" not in corpo


def test_resposta_propriedades_retorna_total_area_sem_area(app_db):
    resp, corpo = _post_ia(app_db, "Tenho propriedades sem área?")
    assert resp.status_code == 200
    assert "Resumo de propriedades" in corpo
    assert "Propriedades cadastradas: 2" in corpo
    assert "Área total informada: 10,50 ha" in corpo
    assert "Propriedades sem área informada: 1" in corpo
    assert "999,00 ha" not in corpo


def test_resposta_culturas_retorna_status_e_associacoes(app_db):
    resp, corpo = _post_ia(app_db, "Resumo das culturas e plantios.")
    assert resp.status_code == 200
    assert "Resumo de culturas" in corpo
    assert "Culturas cadastradas: 2" in corpo
    assert "Planejadas: 1" in corpo
    assert "Em andamento: 1" in corpo
    assert "Associações cultura↔propriedade: 2" in corpo
    assert "Cultura secreta" not in corpo


def test_resposta_colheita_retorna_registros_e_soma_por_unidade(app_db):
    resp, corpo = _post_ia(app_db, "Resumo das colheitas.")
    assert resp.status_code == 200
    assert "Resumo de colheita" in corpo
    assert "Registros de colheita: 2" in corpo
    assert "30,00 sacas" in corpo
    assert "2,00 ton" in corpo
    assert "999,00 sacas" not in corpo


def test_resposta_aplicacoes_inclui_aviso_obrigatorio(app_db):
    resp, corpo = _post_ia(app_db, "Resumo das aplicações de insumo.")
    assert resp.status_code == 200
    assert "Resumo de aplicações de insumo" in corpo
    assert "Aplicações registradas: 1" in corpo
    assert "Glifosato" in corpo
    assert "Aplicações são registros históricos operacionais." in corpo
    assert "O ConnectAgro não recomenda produtos e não valida dose." in corpo
    assert "999,00 kg/ha" not in corpo


def test_resposta_documentos_informa_que_nao_le_conteudo(app_db):
    resp, corpo = _post_ia(app_db, "Resumo dos documentos.")
    assert resp.status_code == 200
    assert "Resumo de documentos" in corpo
    assert "Arquivos cadastrados: 2" in corpo
    assert "A IA não lê o conteúdo dos arquivos enviados no MVP." in corpo
    assert "arquivo-secreto.pdf" not in corpo


def test_resposta_catalogo_informa_limites(app_db):
    resp, corpo = _post_ia(app_db, "O que existe no catálogo?")
    assert resp.status_code == 200
    assert "Resumo do catálogo" in corpo
    assert "Defensivos cadastrados: 2" in corpo
    assert "Fertilizantes cadastrados: 1" in corpo
    assert "Produtos bloqueados/históricos: 1" in corpo
    assert "O ConnectAgro não vende produtos" in corpo
    assert "status regulatório não representa validação oficial automática" in corpo


def test_resposta_desconhecida_retorna_ajuda(app_db):
    resp, corpo = _post_ia(app_db, "Explique algo aleatório")
    assert resp.status_code == 200
    assert "Não entendi totalmente a pergunta." in corpo
    for tema in ("resumo", "financeiro", "propriedades", "culturas", "colheita", "aplicações", "documentos", "catálogo"):
        assert tema in corpo


def test_resposta_nao_contem_termos_proibidos(app_db):
    from app.models import IaInteracao

    _post_ia(app_db, "Resumo das aplicações de insumo.")
    with app_db.app_context():
        resposta = IaInteracao.query.filter_by(pergunta="Resumo das aplicações de insumo.").one().resposta.lower()
    for proibido in (
        "produto recomendado",
        "dose correta",
        "dose segura",
        "compre",
        "checkout",
        "carrinho",
        "cotação oficial",
        "validado oficialmente pelo mapa",
    ):
        assert proibido not in resposta
