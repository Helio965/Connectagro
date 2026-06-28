"""Testes diretos do serviço de relatórios (Fase 6.2)."""
import pytest

from app.extensions import db
from app.services.relatorios_service import (
    FiltroInvalidoError,
    montar_relatorio_aplicacoes,
    montar_relatorio_financeiro,
    validar_periodo,
)


def _propriedade():
    from app.models import Usuario, Propriedade, FinanceiroLancamento

    u = Usuario(nome="s", email="s@connectagro.com", perfil="tecnico", ativo=True,
                senha_hash="x")
    db.session.add(u)
    db.session.commit()
    p = Propriedade(usuario_id=u.id, nome="Fazenda S")
    db.session.add(p)
    db.session.commit()
    db.session.add(FinanceiroLancamento(propriedade_id=p.id, tipo="receita",
                                        valor=200.0, data="2026-01-01"))
    db.session.add(FinanceiroLancamento(propriedade_id=p.id, tipo="despesa",
                                        valor=80.0, data="2026-01-05"))
    db.session.commit()
    return p


@pytest.fixture
def app_db(app):
    with app.app_context():
        db.create_all()
    return app


def test_validar_periodo_ok():
    assert validar_periodo("2026-01-01", "2026-02-01") is None
    assert validar_periodo(None, None) is None


def test_validar_periodo_invalido():
    with pytest.raises(FiltroInvalidoError):
        validar_periodo("2026-03-01", "2026-01-01")


def test_financeiro_totais(app_db):
    with app_db.app_context():
        p = _propriedade()
        dados = montar_relatorio_financeiro(p)
        assert dados["receitas"] == 200.0
        assert dados["despesas"] == 80.0
        assert dados["saldo"] == 120.0
        assert dados["quantidade"] == 2


def test_financeiro_tipo_invalido(app_db):
    with app_db.app_context():
        p = _propriedade()
        with pytest.raises(FiltroInvalidoError):
            montar_relatorio_financeiro(p, tipo="xpto")


def test_aplicacoes_classe_invalida(app_db):
    with app_db.app_context():
        p = _propriedade()
        with pytest.raises(FiltroInvalidoError):
            montar_relatorio_aplicacoes(p, classe="xpto")
