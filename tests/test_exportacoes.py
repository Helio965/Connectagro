"""Testes da Fase 7.4 — PDF/exportações dos relatórios operacionais.

CSV (biblioteca padrão) e PDF (ReportLab), em memória, reaproveitando os
serviços de relatórios. Exigem `relatorios.view`, escopo por propriedade e
geram auditoria `exportacao.gerada`. Não há tabela/migration nova.
"""
import pytest

from app.extensions import db
from app.utils.auth import gerar_hash_senha

SENHA = "senha123"
RELATORIOS = ["geral", "financeiro", "agricola", "aplicacoes", "uploads"]
AVISO_TRECHO = "Não constitui cotação, venda"


def _criar_usuario(nome, email, perfil):
    from app.models import Usuario

    u = Usuario(nome=nome, email=email, perfil=perfil, ativo=True,
                senha_hash=gerar_hash_senha(SENHA))
    db.session.add(u)
    db.session.commit()
    return u


def _vincular(usuario, propriedade):
    from app.models import UsuarioPropriedade

    db.session.add(UsuarioPropriedade(usuario_id=usuario.id,
                                      propriedade_id=propriedade.id, ativo=True))
    db.session.commit()


def _popular(app):
    from app.models import (AplicacaoInsumo, ColheitaRegistro, Cultura,
                            CulturaGleba, EquipeMembro, FinanceiroLancamento,
                            Gleba, ProdutoBase, Propriedade, UploadArquivo)

    with app.app_context():
        admin = _criar_usuario("Admin", "admin@connectagro.com", "admin")
        tecnico = _criar_usuario("Téc", "tecnico@connectagro.com", "tecnico")
        prop = Propriedade(usuario_id=admin.id, nome="Fazenda Export")
        db.session.add(prop)
        db.session.commit()
        _vincular(admin, prop)
        _vincular(tecnico, prop)

        gleba = Gleba(propriedade_id=prop.id, nome="Gleba Export", area_ha=20,
                      tipo_solo="argiloso")
        cultura = Cultura(propriedade_id=prop.id, nome="Soja Export",
                          status="em_andamento", safra="2026")
        produto = ProdutoBase(nome="Produto Export", slug="produto-export",
                              classe="defensivo", categoria="herbicida",
                              status_sistema="pre_cadastrado",
                              status_regulatorio="nao_validado_agrofit")
        membro = EquipeMembro(propriedade_id=prop.id, nome="Membro Export", ativo=True)
        lanc = FinanceiroLancamento(propriedade_id=prop.id, tipo="receita",
                                    valor=1234.50, data="2026-03-01",
                                    categoria="venda safra", descricao="entrada")
        upload = UploadArquivo(propriedade_id=prop.id, nome_original="doc-export.pdf",
                               caminho="propriedade_x/doc.pdf", tipo_mime="application/pdf",
                               tamanho=2048, descricao="documento")
        db.session.add_all([gleba, cultura, produto, membro, lanc, upload])
        db.session.commit()
        cg = CulturaGleba(cultura_id=cultura.id, gleba_id=gleba.id)
        db.session.add(cg)
        db.session.commit()
        db.session.add(ColheitaRegistro(cultura_gleba_id=cg.id, data_colheita="2026-04-01",
                                        quantidade=99, unidade="sc", qualidade="boa"))
        db.session.add(AplicacaoInsumo(cultura_gleba_id=cg.id, produto_base_id=produto.id,
                                       data_aplicacao="2026-03-15", dose=2.5, unidade="L/ha",
                                       responsavel="João"))
        db.session.commit()

        # segunda propriedade (escopo)
        outro = _criar_usuario("Outro", "outro@connectagro.com", "admin")
        outra_prop = Propriedade(usuario_id=outro.id, nome="Fazenda Externa")
        db.session.add(outra_prop)
        db.session.commit()
        _vincular(outro, outra_prop)
        db.session.add(Gleba(propriedade_id=outra_prop.id, nome="GLEBA_SECRETA_OUTRA",
                             area_ha=5))
        db.session.add(FinanceiroLancamento(propriedade_id=outra_prop.id, tipo="receita",
                                            valor=777, data="2026-03-01",
                                            descricao="SEGREDO_OUTRA_PROP"))
        db.session.commit()
        return {"prop_id": prop.id}


@pytest.fixture
def app_exp(app):
    with app.app_context():
        db.create_all()
    app.exp_ids = _popular(app)
    return app


def _login(client, email="admin@connectagro.com"):
    resp = client.post("/auth/login", data={"email": email, "senha": SENHA})
    assert resp.status_code == 302


def _acoes(app):
    from app.models import LogAuditoria

    with app.app_context():
        return [l.acao for l in LogAuditoria.query.all()]


# --- Acesso ----------------------------------------------------------------

@pytest.mark.parametrize("slug", RELATORIOS)
@pytest.mark.parametrize("ext", ["csv", "pdf"])
def test_exportacao_exige_login(app_exp, slug, ext):
    resp = app_exp.test_client().get(f"/relatorios/{slug}/exportar.{ext}")
    assert resp.status_code == 302
    assert "/auth/login" in resp.headers["Location"]


@pytest.mark.parametrize("slug", RELATORIOS)
@pytest.mark.parametrize("ext", ["csv", "pdf"])
def test_admin_acessa_exportacao(app_exp, slug, ext):
    client = app_exp.test_client()
    _login(client)
    assert client.get(f"/relatorios/{slug}/exportar.{ext}").status_code == 200


@pytest.mark.parametrize("slug", RELATORIOS)
def test_tecnico_pode_exportar(app_exp, slug):
    client = app_exp.test_client()
    _login(client, "tecnico@connectagro.com")
    assert client.get(f"/relatorios/{slug}/exportar.csv").status_code == 200


# --- CSV -------------------------------------------------------------------

def test_geral_csv_headers_e_conteudo(app_exp):
    client = app_exp.test_client()
    _login(client)
    resp = client.get("/relatorios/geral/exportar.csv")
    assert resp.status_code == 200
    assert resp.content_type.startswith("text/csv")
    assert "attachment" in resp.headers["Content-Disposition"]
    assert ".csv" in resp.headers["Content-Disposition"]
    corpo = resp.data.decode("utf-8")
    assert "Fazenda Export" in corpo
    assert AVISO_TRECHO in corpo


def test_csv_nao_contem_dados_de_outra_propriedade(app_exp):
    client = app_exp.test_client()
    _login(client)
    for slug in RELATORIOS:
        corpo = client.get(f"/relatorios/{slug}/exportar.csv").data.decode("utf-8")
        assert "SEGREDO_OUTRA_PROP" not in corpo
        assert "GLEBA_SECRETA_OUTRA" not in corpo


def test_financeiro_csv_tem_lancamento(app_exp):
    client = app_exp.test_client()
    _login(client)
    corpo = client.get("/relatorios/financeiro/exportar.csv").data.decode("utf-8")
    assert "1.234,50" in corpo
    assert "entrada" in corpo


def test_aplicacoes_csv_tem_dados(app_exp):
    client = app_exp.test_client()
    _login(client)
    corpo = client.get("/relatorios/aplicacoes/exportar.csv").data.decode("utf-8")
    # O CSV atual traz a propriedade no cabeçalho e o produto nas linhas
    # (a coluna Cultura saiu do layout na revisão das exportações).
    assert "Fazenda Export" in corpo
    assert "Produto Export" in corpo


def test_uploads_csv_tem_dados(app_exp):
    client = app_exp.test_client()
    _login(client)
    corpo = client.get("/relatorios/uploads/exportar.csv").data.decode("utf-8")
    assert "doc-export.pdf" in corpo


def test_agricola_csv_tem_dados(app_exp):
    client = app_exp.test_client()
    _login(client)
    corpo = client.get("/relatorios/agricola/exportar.csv").data.decode("utf-8")
    assert "Gleba Export" in corpo
    assert "Soja Export" in corpo


# --- PDF -------------------------------------------------------------------

@pytest.mark.parametrize("slug", RELATORIOS)
def test_pdf_headers_e_assinatura(app_exp, slug):
    client = app_exp.test_client()
    _login(client)
    resp = client.get(f"/relatorios/{slug}/exportar.pdf")
    assert resp.status_code == 200
    assert resp.content_type.startswith("application/pdf")
    assert "attachment" in resp.headers["Content-Disposition"]
    assert ".pdf" in resp.headers["Content-Disposition"]
    assert resp.data[:5] == b"%PDF-"
    assert len(resp.data) > 800


# --- Filtros ---------------------------------------------------------------

def test_financeiro_exporta_com_filtros_validos(app_exp):
    client = app_exp.test_client()
    _login(client)
    resp = client.get("/relatorios/financeiro/exportar.csv"
                      "?data_inicio=2026-01-01&data_fim=2026-12-31&tipo=receita")
    assert resp.status_code == 200
    assert "1.234,50" in resp.data.decode("utf-8")


def test_financeiro_filtro_invalido_400(app_exp):
    client = app_exp.test_client()
    _login(client)
    resp = client.get("/relatorios/financeiro/exportar.csv"
                      "?data_inicio=2026-12-31&data_fim=2026-01-01")
    assert resp.status_code == 400


def test_financeiro_pdf_filtro_invalido_400(app_exp):
    client = app_exp.test_client()
    _login(client)
    resp = client.get("/relatorios/financeiro/exportar.pdf?tipo=invalido")
    assert resp.status_code == 400


def test_aplicacoes_exporta_com_filtros_validos(app_exp):
    client = app_exp.test_client()
    _login(client)
    resp = client.get("/relatorios/aplicacoes/exportar.csv?classe=defensivo")
    assert resp.status_code == 200
    assert "Produto Export" in resp.data.decode("utf-8")


def test_aplicacoes_filtro_invalido_400(app_exp):
    client = app_exp.test_client()
    _login(client)
    resp = client.get("/relatorios/aplicacoes/exportar.csv?classe=xpto")
    assert resp.status_code == 400


def test_links_exportacao_preservam_filtros(app_exp):
    client = app_exp.test_client()
    _login(client)
    html = client.get("/relatorios/financeiro?tipo=receita&data_inicio=2026-01-01"
                      "&data_fim=2026-12-31").data.decode("utf-8")
    assert "exportar.csv" in html
    assert "tipo=receita" in html
    assert "data_inicio=2026-01-01" in html


# --- Auditoria -------------------------------------------------------------

def test_exportacao_csv_gera_log(app_exp):
    client = app_exp.test_client()
    _login(client)
    client.get("/relatorios/financeiro/exportar.csv")
    assert "exportacao.gerada" in _acoes(app_exp)


def test_exportacao_pdf_gera_log(app_exp):
    from app.models import LogAuditoria

    client = app_exp.test_client()
    _login(client)
    client.get("/relatorios/geral/exportar.pdf")
    with app_exp.app_context():
        logs = LogAuditoria.query.filter_by(acao="exportacao.gerada").all()
        assert logs
        assert all(l.entidade == "relatorio" for l in logs)
        assert all(l.propriedade_id == app_exp.exp_ids["prop_id"] for l in logs)


def test_exportacao_log_escopado_e_sem_dados_sensiveis(app_exp):
    from app.models import LogAuditoria

    client = app_exp.test_client()
    _login(client)
    client.get("/relatorios/financeiro/exportar.csv")
    with app_exp.app_context():
        for log in LogAuditoria.query.filter_by(acao="exportacao.gerada").all():
            blob = " ".join(filter(None, [log.descricao, log.entidade, log.entidade_id]))
            assert "1234.50" not in blob
            assert "senha" not in blob.lower()


def test_filtro_invalido_nao_gera_sucesso(app_exp):
    client = app_exp.test_client()
    _login(client)
    client.get("/relatorios/financeiro/exportar.csv"
               "?data_inicio=2026-12-31&data_fim=2026-01-01")
    acoes = _acoes(app_exp)
    assert "exportacao.gerada" not in acoes
    assert "exportacao.falha" in acoes


# --- Segurança / escopo ----------------------------------------------------

def test_exportacao_nao_cria_dados(app_exp):
    from app.models import (FinanceiroLancamento, Gleba, ProdutoImagem,
                            ProdutoPreco)

    client = app_exp.test_client()
    _login(client)
    with app_exp.app_context():
        glebas_antes = Gleba.query.count()
        fin_antes = FinanceiroLancamento.query.count()
    for slug in RELATORIOS:
        client.get(f"/relatorios/{slug}/exportar.csv")
        client.get(f"/relatorios/{slug}/exportar.pdf")
    with app_exp.app_context():
        assert Gleba.query.count() == glebas_antes
        assert FinanceiroLancamento.query.count() == fin_antes
        assert ProdutoPreco.query.count() == 0
        assert ProdutoImagem.query.count() == 0


def test_servico_csv_direto_sem_dados_de_venda(app_exp):
    # As exportações são operacionais; nenhum recurso de comércio é introduzido.
    # (O aviso legitimamente diz "não é cotação, venda...", então esses termos não
    # são proibidos aqui; checamos termos de comércio que não aparecem no aviso.)
    client = app_exp.test_client()
    _login(client)
    corpo = client.get("/relatorios/geral/exportar.csv").data.decode("utf-8").lower()
    # O aviso legal cita "checkout" ao negar comércio; ignora a linha do aviso.
    corpo_sem_aviso = "\n".join(
        linha for linha in corpo.splitlines() if "não constitui" not in linha
    )
    for termo in ("carrinho", "checkout", "comprar", "adicionar ao carrinho"):
        assert termo not in corpo_sem_aviso
