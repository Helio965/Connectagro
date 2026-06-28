"""Testes do CRUD de Equipe e Financeiro (Etapa 5.3) — escopo por propriedade."""
import pytest

from app.extensions import db
from app.utils.auth import gerar_hash_senha


def _criar_usuario(email):
    from app.models import Usuario

    u = Usuario(nome=email, email=email, perfil="tecnico", ativo=True,
                senha_hash=gerar_hash_senha("senha123"))
    db.session.add(u)
    db.session.commit()
    return u


@pytest.fixture
def app_db(app):
    with app.app_context():
        db.create_all()
        _criar_usuario("a@connectagro.com")
        _criar_usuario("b@connectagro.com")
    return app


def _login(app_db, email):
    client = app_db.test_client()
    client.post("/auth/login", data={"email": email, "senha": "senha123"})
    return client


# --- Equipe ---------------------------------------------------------------

def test_criar_membro(app_db):
    from app.models import EquipeMembro

    client = _login(app_db, "a@connectagro.com")
    resp = client.post("/equipe/novo",
                       data={"nome": "João", "funcao": "Operador",
                             "email": "JOAO@EX.COM", "ativo": "1"})
    assert resp.status_code == 302
    with app_db.app_context():
        m = EquipeMembro.query.filter_by(nome="João").first()
        assert m is not None
        assert m.email == "joao@ex.com"  # normalizado
        assert m.ativo is True


def test_membro_exige_nome(app_db):
    client = _login(app_db, "a@connectagro.com")
    assert client.post("/equipe/novo", data={"nome": ""}).status_code == 400


def test_editar_membro(app_db):
    from app.models import EquipeMembro

    client = _login(app_db, "a@connectagro.com")
    client.post("/equipe/novo", data={"nome": "M1", "ativo": "1"})
    with app_db.app_context():
        mid = EquipeMembro.query.filter_by(nome="M1").first().id
    # edita sem marcar ativo -> fica inativo
    resp = client.post(f"/equipe/{mid}/editar", data={"nome": "M1 editado"})
    assert resp.status_code == 302
    with app_db.app_context():
        m = db.session.get(EquipeMembro, mid)
        assert m.nome == "M1 editado"
        assert m.ativo is False
        assert m.atualizado_em is not None


def test_remover_membro(app_db):
    from app.models import EquipeMembro

    client = _login(app_db, "a@connectagro.com")
    client.post("/equipe/novo", data={"nome": "M-del"})
    with app_db.app_context():
        mid = EquipeMembro.query.filter_by(nome="M-del").first().id
    assert client.post(f"/equipe/{mid}/remover").status_code == 302
    with app_db.app_context():
        assert db.session.get(EquipeMembro, mid) is None


def test_escopo_membro_por_propriedade(app_db):
    from app.models import EquipeMembro

    ca = _login(app_db, "a@connectagro.com")
    ca.post("/equipe/novo", data={"nome": "Membro A"})
    with app_db.app_context():
        mid = EquipeMembro.query.filter_by(nome="Membro A").first().id
    cb = _login(app_db, "b@connectagro.com")
    assert cb.get(f"/equipe/{mid}/editar").status_code == 404
    assert cb.post(f"/equipe/{mid}/remover").status_code == 404


def test_equipe_exige_login(app_db):
    resp = app_db.test_client().get("/equipe/novo")
    assert resp.status_code == 302
    assert "/auth/login" in resp.headers["Location"]


# --- Financeiro -----------------------------------------------------------

def test_criar_receita(app_db):
    from app.models import FinanceiroLancamento

    client = _login(app_db, "a@connectagro.com")
    resp = client.post("/financeiro/novo",
                       data={"tipo": "receita", "valor": "1000,50",
                             "data": "2026-01-10", "categoria": "venda"})
    assert resp.status_code == 302
    with app_db.app_context():
        l = FinanceiroLancamento.query.filter_by(tipo="receita").first()
        assert l is not None
        assert l.valor == 1000.50


def test_criar_despesa_ponto_decimal(app_db):
    from app.models import FinanceiroLancamento

    client = _login(app_db, "a@connectagro.com")
    resp = client.post("/financeiro/novo",
                       data={"tipo": "despesa", "valor": "250.75", "data": "2026-01-11"})
    assert resp.status_code == 302
    with app_db.app_context():
        l = FinanceiroLancamento.query.filter_by(tipo="despesa").first()
        assert l.valor == 250.75


def test_valor_invalido_400(app_db):
    client = _login(app_db, "a@connectagro.com")
    assert client.post("/financeiro/novo",
                       data={"tipo": "receita", "valor": "", "data": "2026-01-10"}).status_code == 400
    assert client.post("/financeiro/novo",
                       data={"tipo": "receita", "valor": "abc", "data": "2026-01-10"}).status_code == 400


def test_valor_nao_positivo_400(app_db):
    client = _login(app_db, "a@connectagro.com")
    assert client.post("/financeiro/novo",
                       data={"tipo": "receita", "valor": "0", "data": "2026-01-10"}).status_code == 400
    assert client.post("/financeiro/novo",
                       data={"tipo": "despesa", "valor": "-5", "data": "2026-01-10"}).status_code == 400


def test_tipo_invalido_400(app_db):
    client = _login(app_db, "a@connectagro.com")
    assert client.post("/financeiro/novo",
                       data={"tipo": "outro", "valor": "10", "data": "2026-01-10"}).status_code == 400


def test_data_obrigatoria_400(app_db):
    client = _login(app_db, "a@connectagro.com")
    assert client.post("/financeiro/novo",
                       data={"tipo": "receita", "valor": "10", "data": ""}).status_code == 400


def test_editar_lancamento(app_db):
    from app.models import FinanceiroLancamento

    client = _login(app_db, "a@connectagro.com")
    client.post("/financeiro/novo", data={"tipo": "receita", "valor": "10", "data": "2026-01-10"})
    with app_db.app_context():
        lid = FinanceiroLancamento.query.first().id
    resp = client.post(f"/financeiro/{lid}/editar",
                       data={"tipo": "despesa", "valor": "20", "data": "2026-02-01"})
    assert resp.status_code == 302
    with app_db.app_context():
        l = db.session.get(FinanceiroLancamento, lid)
        assert l.tipo == "despesa"
        assert l.valor == 20.0
        assert l.atualizado_em is not None


def test_remover_lancamento(app_db):
    from app.models import FinanceiroLancamento

    client = _login(app_db, "a@connectagro.com")
    client.post("/financeiro/novo", data={"tipo": "receita", "valor": "10", "data": "2026-01-10"})
    with app_db.app_context():
        lid = FinanceiroLancamento.query.first().id
    assert client.post(f"/financeiro/{lid}/remover").status_code == 302
    with app_db.app_context():
        assert db.session.get(FinanceiroLancamento, lid) is None


def test_escopo_lancamento_por_propriedade(app_db):
    from app.models import FinanceiroLancamento

    ca = _login(app_db, "a@connectagro.com")
    ca.post("/financeiro/novo", data={"tipo": "receita", "valor": "10", "data": "2026-01-10"})
    with app_db.app_context():
        lid = FinanceiroLancamento.query.first().id
    cb = _login(app_db, "b@connectagro.com")
    assert cb.get(f"/financeiro/{lid}/editar").status_code == 404
    assert cb.post(f"/financeiro/{lid}/remover").status_code == 404


def test_totais_receitas_despesas_saldo(app_db):
    client = _login(app_db, "a@connectagro.com")
    client.post("/financeiro/novo", data={"tipo": "receita", "valor": "100", "data": "2026-01-10"})
    client.post("/financeiro/novo", data={"tipo": "receita", "valor": "50", "data": "2026-01-11"})
    client.post("/financeiro/novo", data={"tipo": "despesa", "valor": "30", "data": "2026-01-12"})
    resp = client.get("/financeiro/")
    corpo = resp.data.decode("utf-8")
    assert resp.status_code == 200
    assert "150.00" in corpo   # receitas
    assert "30.00" in corpo    # despesas
    assert "120.00" in corpo   # saldo


def test_financeiro_exige_login(app_db):
    resp = app_db.test_client().get("/financeiro/novo")
    assert resp.status_code == 302
    assert "/auth/login" in resp.headers["Location"]
