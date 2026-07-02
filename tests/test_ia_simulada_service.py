"""Testes diretos do serviço de IA simulada."""
import pytest

from app.extensions import db
from app.utils.auth import gerar_hash_senha


def _criar_base(app):
    from app.models import Cultura, CulturaGleba, FinanceiroLancamento, Gleba, Propriedade, Usuario

    with app.app_context():
        db.create_all()
        usuario = Usuario(nome="Técnico", email="tecnico@connectagro.com", perfil="tecnico",
                          ativo=True, senha_hash=gerar_hash_senha("senha123"))
        db.session.add(usuario)
        db.session.commit()
        propriedade = Propriedade(usuario_id=usuario.id, nome="Fazenda Serviço")
        db.session.add(propriedade)
        db.session.commit()
        gleba = Gleba(propriedade_id=propriedade.id, nome="Talhão Serviço", area_ha=12)
        gleba_sem_area = Gleba(propriedade_id=propriedade.id, nome="Talhão Sem Área")
        cultura = Cultura(propriedade_id=propriedade.id, nome="Soja", status="planejada")
        db.session.add_all([gleba, gleba_sem_area, cultura])
        db.session.commit()
        db.session.add(CulturaGleba(cultura_id=cultura.id, gleba_id=gleba.id))
        db.session.add(FinanceiroLancamento(propriedade_id=propriedade.id, tipo="receita",
                                            valor=500, data="2026-01-10"))
        db.session.commit()
        return usuario.id, propriedade.id


@pytest.fixture
def app_db(app):
    usuario_id, propriedade_id = _criar_base(app)
    return app, usuario_id, propriedade_id


def test_classificar_intencao_simples(app_db):
    from app.services.ia_simulada_service import classificar_intencao_simples

    assert classificar_intencao_simples("Como está o financeiro?") == "financeiro"
    assert classificar_intencao_simples("Tenho propriedades sem área?") == "glebas"
    assert classificar_intencao_simples("Resumo das aplicações") == "aplicacoes"
    assert classificar_intencao_simples("O que existe no catálogo?") == "catalogo"
    assert classificar_intencao_simples("pergunta sem tema") == "ajuda"


def test_montar_contexto_operacional(app_db):
    from app.models import Propriedade
    from app.services.ia_simulada_service import montar_contexto_operacional

    app, _, propriedade_id = app_db
    with app.app_context():
        propriedade = db.session.get(Propriedade, propriedade_id)
        contexto = montar_contexto_operacional(propriedade)
        assert contexto["glebas"]["total"] == 2
        assert contexto["glebas"]["area_total"] == pytest.approx(12)
        assert contexto["culturas"]["total"] == 1
        assert contexto["culturas"]["total_associacoes"] == 1
        assert contexto["financeiro"]["receitas"] == pytest.approx(500)
        assert contexto["financeiro"]["saldo"] == pytest.approx(500)


def test_gerar_alertas_operacionais(app_db):
    from app.models import Propriedade
    from app.services.ia_simulada_service import gerar_alertas_operacionais

    app, _, propriedade_id = app_db
    with app.app_context():
        propriedade = db.session.get(Propriedade, propriedade_id)
        alertas = gerar_alertas_operacionais(propriedade)
        assert "Existem 1 propriedades sem área informada." in alertas
        assert "Nenhum registro de colheita cadastrado." in alertas
        assert "Nenhum upload cadastrado. A IA não lê conteúdo de arquivos no MVP." in alertas


def test_responder_pergunta_simulada(app_db):
    from app.models import Propriedade
    from app.services.ia_simulada_service import responder_pergunta_simulada

    app, _, propriedade_id = app_db
    with app.app_context():
        propriedade = db.session.get(Propriedade, propriedade_id)
        resposta = responder_pergunta_simulada(propriedade, "Faça um resumo da propriedade")
        assert "Resumo operacional da propriedade" in resposta
        assert "Propriedades cadastradas: 2" in resposta
        assert "Saldo financeiro: R$ 500,00" in resposta
        assert "Importante: esta IA é simulada" in resposta


def test_registrar_e_listar_interacao_ia(app_db):
    from app.models import Propriedade, Usuario
    from app.services.ia_simulada_service import listar_interacoes_ia, registrar_interacao_ia

    app, usuario_id, propriedade_id = app_db
    with app.app_context():
        usuario = db.session.get(Usuario, usuario_id)
        propriedade = db.session.get(Propriedade, propriedade_id)
        registrar_interacao_ia(usuario, propriedade, "Pergunta teste", "Resposta teste")
        interacoes = listar_interacoes_ia(usuario, propriedade)
        assert len(interacoes) == 1
        assert interacoes[0].pergunta == "Pergunta teste"
        assert interacoes[0].resposta == "Resposta teste"
        assert interacoes[0].tipo == "simulada"
