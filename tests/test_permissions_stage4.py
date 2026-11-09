"""Contrato de acesso da Etapa 04, sem conceder permissões nas fixtures."""
import base64
import re
import zlib

import pytest

from app.extensions import db
from app.models import EquipeMembro, FinanceiroLancamento, IaInteracao, LogAuditoria, Usuario
from app.utils.auth import gerar_hash_senha
from app.utils.permissions import PERMISSOES_POR_PERFIL
from tests.factories import criar_propriedade_com_vinculo, vincular_usuario_propriedade


PASSWORD = "stage4-test-password"
PRIVATE_MARKERS = (
    "PRIVATE_FINANCE_DESCRIPTION_A", "PRIVATE_FINANCE_CATEGORY_A",
    "PRIVATE_TEAM_NAME_A", "PRIVATE_TEAM_FUNCTION_A", "PRIVATE_TEAM_EMAIL_A",
    "PRIVATE_FINANCE_DESCRIPTION_B", "PRIVATE_TEAM_NAME_B",
)
FINANCIAL_ROUTES = (
    "/relatorios/financeiro", "/relatorios/financeiro/exportar.csv",
    "/relatorios/financeiro/exportar.pdf",
)


@pytest.fixture
def policy_app(app):
    with app.app_context():
        db.create_all()
        password_hash = gerar_hash_senha(PASSWORD)
        users = {}
        for alias, role in (("admin_a", "admin"), ("manager_a", "tecnico"),
                            ("worker_a", "trabalhador"), ("manager_b", "tecnico"),
                            ("worker_b", "trabalhador")):
            user = Usuario(nome=alias, email=f"{alias}@stage4.invalid", perfil=role,
                           ativo=True, senha_hash=password_hash)
            db.session.add(user)
            db.session.flush()
            users[alias] = user
        prop_a = criar_propriedade_com_vinculo(users["admin_a"].id, nome="Contexto A")
        prop_b = criar_propriedade_com_vinculo(users["manager_b"].id, nome="Contexto B")
        for alias in ("manager_a", "worker_a"):
            vincular_usuario_propriedade(users[alias].id, prop_a.id)
        vincular_usuario_propriedade(users["worker_b"].id, prop_b.id)
        db.session.add_all([
            FinanceiroLancamento(propriedade_id=prop_a.id, tipo="receita", valor=1000,
                data="2026-03-17", categoria=PRIVATE_MARKERS[1], descricao=PRIVATE_MARKERS[0]),
            FinanceiroLancamento(propriedade_id=prop_a.id, tipo="despesa", valor=200,
                data="2026-03-18", descricao="PRIVATE_EXPENSE_DESCRIPTION_A"),
            EquipeMembro(propriedade_id=prop_a.id, nome=PRIVATE_MARKERS[2],
                funcao=PRIVATE_MARKERS[3], email=PRIVATE_MARKERS[4], ativo=True),
            EquipeMembro(propriedade_id=prop_a.id, nome="PRIVATE_INACTIVE_MEMBER_A", ativo=False),
            FinanceiroLancamento(propriedade_id=prop_b.id, tipo="receita", valor=99999,
                data="2026-03-17", descricao=PRIVATE_MARKERS[5]),
            EquipeMembro(propriedade_id=prop_b.id, nome=PRIVATE_MARKERS[6], ativo=True),
        ])
        db.session.commit()
        app.policy_ids = {alias: user.id for alias, user in users.items()}
        app.policy_ids.update(property_a=prop_a.id, property_b=prop_b.id)
    return app


def _login(application, alias):
    client = application.test_client()
    response = client.post("/auth/login", data={
        "email": f"{alias}@stage4.invalid", "senha": PASSWORD,
    })
    assert response.status_code == 302
    return client


def _pdf_content(data):
    """Inspeciona também os streams comprimidos do PDF gerado pelo ReportLab."""
    assert data.startswith(b"%PDF-")
    streams = []
    for raw in re.findall(rb"stream\r?\n(.*?)endstream", data, flags=re.S):
        raw = raw.strip()
        if raw.endswith(b"~>"):
            raw = base64.a85decode(raw[:-2])
        try:
            streams.append(zlib.decompress(raw))
        except zlib.error:
            streams.append(raw)
    assert streams, "PDF deve conter conteúdo verificável"
    content = b"\n".join(streams).decode("latin-1")
    return content.replace(r"\(", "(").replace(r"\)", ")")


@pytest.mark.parametrize("alias,expected", [
    ("admin_a", 200), ("manager_a", 200), ("worker_a", 403),
])
@pytest.mark.parametrize("route", FINANCIAL_ROUTES)
def test_relatorio_financeiro_detalhado_exige_permissao_no_backend(policy_app, alias, expected, route):
    response = _login(policy_app, alias).get(route)
    assert response.status_code == expected
    if expected == 403:
        assert response.mimetype == "text/html"
        assert not response.headers.get("Content-Disposition")
        assert PRIVATE_MARKERS[0].encode() not in response.data


@pytest.mark.parametrize("suffix", ["", "/exportar.csv", "/exportar.pdf"])
def test_trabalhador_mantem_totais_gerais_sem_detalhes(policy_app, suffix):
    response = _login(policy_app, "worker_a").get("/relatorios/geral" + suffix)
    assert response.status_code == 200
    content = _pdf_content(response.data) if suffix.endswith("pdf") else response.get_data(as_text=True)
    for value in ("1.000,00", "200,00", "800,00"):
        assert value in content
    for marker in PRIVATE_MARKERS + ("PRIVATE_EXPENSE_DESCRIPTION_A", "PRIVATE_INACTIVE_MEMBER_A"):
        assert marker not in content
    assert "99.999,00" not in content
    if not suffix:
        assert re.search(r"Total de membros:</strong>\s*2", content)
    elif suffix.endswith("csv"):
        assert "Membros de equipe;2" in content
        assert "Ativos;1" in content
    else:
        assert "Equipe" in content and "(ativos)" in content


def test_ia_e_historico_do_trabalhador_continuam_agregados(policy_app):
    client = _login(policy_app, "worker_a")
    for response in (client.get("/ia/"), client.post("/ia/", data={"pergunta": "Como está o financeiro?"}),
                     client.get("/ia/")):
        assert response.status_code == 200
        content = response.get_data(as_text=True)
        assert "800,00" in content
        for marker in PRIVATE_MARKERS:
            assert marker not in content
        assert "99.999,00" not in content
    with policy_app.app_context():
        row = IaInteracao.query.filter_by(usuario_id=policy_app.policy_ids["worker_a"]).one()
        assert "Receitas: R$ 1.000,00" in row.resposta
        assert "Despesas: R$ 200,00" in row.resposta
        assert "Saldo: R$ 800,00" in row.resposta
        assert all(marker not in row.resposta for marker in PRIVATE_MARKERS)


@pytest.mark.parametrize("alias,visible", [("admin_a", True), ("manager_a", True), ("worker_a", False)])
def test_card_financeiro_detalhado_corresponde_a_permissao(policy_app, alias, visible):
    content = _login(policy_app, alias).get("/relatorios/").get_data(as_text=True)
    assert ('href="/relatorios/financeiro"' in content) is visible
    assert 'href="/relatorios/geral"' in content


def test_acesso_negado_auditado_com_identificador_compativel_com_postgresql(policy_app):
    client = _login(policy_app, "worker_a")
    assert client.get(FINANCIAL_ROUTES[0]).status_code == 403
    with policy_app.app_context():
        log = LogAuditoria.query.filter_by(acao="permissao.negada").one()
        assert log.entidade == "permission"
        assert log.entidade_id is None
        assert log.usuario_id == policy_app.policy_ids["worker_a"]
        assert log.propriedade_id == policy_app.policy_ids["property_a"]
        assert log.resultado == "negado"
        assert log.descricao == "Permissão negada: financeiro.view"


@pytest.mark.parametrize("method,endpoint", [("get", "editar"), ("post", "editar"),
    ("post", "inativar"), ("post", "reenviar-convite")])
def test_gerente_nao_consulta_ou_altera_trabalhador_exclusivo_de_outro_contexto(policy_app, method, endpoint):
    client = _login(policy_app, "manager_a")
    target_id = policy_app.policy_ids["worker_b"]
    response = getattr(client, method)(f"/usuarios/{target_id}/{endpoint}", data={
        "nome": "Forjado", "email": "forjado@stage4.invalid", "perfil": "admin", "ativo": "1",
    })
    assert response.status_code == 404
    with policy_app.app_context():
        user = db.session.get(Usuario, target_id)
        assert (user.nome, user.email, user.perfil, user.ativo, user.auth_version) == (
            "worker_b", "worker_b@stage4.invalid", "trabalhador", True, 1)
        assert not user.tokens_reset


def test_gerente_nao_cria_administrador_nem_eleva_proprio_perfil(policy_app):
    client = _login(policy_app, "manager_a")
    payload = dict(nome="Forjado", email="forjado@stage4.invalid", perfil="admin", ativo="1")
    assert client.post("/usuarios/novo", data=payload).status_code == 403
    assert client.post(f'/usuarios/{policy_app.policy_ids["manager_a"]}/editar', data=payload).status_code == 403
    with policy_app.app_context():
        assert not Usuario.query.filter_by(email=payload["email"]).first()
        assert db.session.get(Usuario, policy_app.policy_ids["manager_a"]).perfil == "tecnico"


def test_trabalhador_nao_altera_perfil_mesmo_com_csrf_valido(policy_app):
    client = _login(policy_app, "worker_a")
    policy_app.config["WTF_CSRF_ENABLED"] = True
    content = client.get("/propriedades/").get_data(as_text=True)
    token = re.search(r'name="csrf_token" value="([^"]+)"', content).group(1)
    response = client.post(f'/usuarios/{policy_app.policy_ids["worker_a"]}/editar', data={
        "csrf_token": token, "nome": "Forjado", "email": "forjado@stage4.invalid", "perfil": "admin", "ativo": "1",
    })
    assert response.status_code == 403
    with policy_app.app_context():
        user = db.session.get(Usuario, policy_app.policy_ids["worker_a"])
        assert (user.perfil, user.auth_version) == ("trabalhador", 1)


@pytest.mark.parametrize("alias", ["admin_a", "manager_a"])
def test_relatorios_financeiros_nao_adotam_propriedade_forjada(policy_app, alias):
    client = _login(policy_app, alias)
    for route in FINANCIAL_ROUTES:
        response = client.get(route, query_string={"propriedade_id": policy_app.policy_ids["property_b"]})
        assert response.status_code == 200
        content = _pdf_content(response.data) if route.endswith("pdf") else response.get_data(as_text=True)
        assert "99.999,00" not in content
        assert PRIVATE_MARKERS[5] not in content
        assert "Contexto A" in content


# Contrato aprovado, descrito por operação. Na Etapa 06 o usuário autorizou
# atividades gerais: Trabalhador cria/visualiza, Gerente também edita e Admin
# também cancela. As permissões anteriores permanecem comparadas exatamente.
_COMMON = {
    "catalogo.local.create", "catalogo.personalizar.create", "catalogo.solicitar",
    "atividades.view", "atividades.create",
    "propriedades.view", "propriedades.select", "dashboard.view", "mapa.view",
    "catalogo.view", "relatorios.view", "ia.view", "glebas.view", "culturas.view",
    "colheita.view", "colheita.create", "aplicacoes.view", "aplicacoes.create",
    "upload.view", "upload.create", "upload.download",
}
_MANAGEMENT = {
    "catalogo.local.edit", "catalogo.personalizar.edit",
    "atividades.edit",
    "propriedades.create", "propriedades.edit", "mapa.edit", "glebas.create", "glebas.edit",
    "culturas.create", "culturas.edit", "equipe.view", "financeiro.view", "colheita.edit",
    "aplicacoes.edit", "usuarios.view", "usuarios.create", "usuarios.edit", "usuarios.deactivate",
}
_ADMINISTRATION = {
    "atividades.delete",
    "glebas.delete", "culturas.delete", "equipe.create", "equipe.edit", "equipe.delete",
    "financeiro.create", "financeiro.edit", "financeiro.delete", "colheita.delete",
    "aplicacoes.delete", "upload.delete", "auditoria.view",
}


@pytest.mark.parametrize("role,expected", [
    ("trabalhador", _COMMON), ("tecnico", _COMMON | _MANAGEMENT),
    ("admin", _COMMON | _MANAGEMENT | _ADMINISTRATION),
])
def test_matriz_completa_corresponde_as_operacoes_aprovadas(role, expected):
    assert set(PERMISSOES_POR_PERFIL) == {"admin", "tecnico", "trabalhador"}
    assert set(PERMISSOES_POR_PERFIL[role]) == expected
