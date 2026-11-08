"""Regressões de autenticação e revogação com usuários reais e dois clientes."""
import pytest
from flask import session
from sqlalchemy import event

from app.extensions import db
from app.models import Usuario
from app.utils.auth import gerar_hash_senha, is_authenticated, usuario_atual
from app.utils.permissions import can
from tests.factories import criar_propriedade_com_vinculo, vincular_usuario_propriedade


@pytest.fixture
def security_app(app):
    with app.app_context():
        db.create_all()
        user = Usuario(nome="Gerente teste", email="session@example.invalid",
                       senha_hash=gerar_hash_senha("test-password"),
                       perfil="tecnico", ativo=True)
        db.session.add(user)
        db.session.flush()
        propriedade = criar_propriedade_com_vinculo(user.id, nome="Fazenda segurança do alvo")
        db.session.commit()
        app.security_uid = user.id
        app.security_pid = propriedade.id
    return app


def login(app):
    client = app.test_client()
    assert client.post("/auth/login", data={
        "email": "session@example.invalid", "senha": "test-password",
    }).status_code == 302
    assert client.post("/propriedades/selecionar", data={
        "propriedade_id": str(app.security_pid),
    }).status_code == 302
    return client


def test_inativacao_revoga_dois_clientes_e_reativacao_nao_ressuscita(security_app):
    a, b = login(security_app), login(security_app)
    cookie = a.get_cookie("session").value
    with security_app.app_context():
        u = db.session.get(Usuario, security_app.security_uid)
        u.ativo = False
        db.session.commit()
    assert a.get("/glebas/").status_code == 302
    assert b.get("/glebas/").status_code == 302
    with security_app.app_context():
        u = db.session.get(Usuario, security_app.security_uid)
        u.ativo = True
        db.session.commit()
        assert u.auth_version == 3
    a.set_cookie("session", cookie)
    assert a.get("/glebas/").status_code == 302
    assert login(security_app).get("/glebas/").status_code == 200


def test_usuario_excluido_nao_autentica_cookie_anterior(security_app):
    client = login(security_app)
    with security_app.app_context():
        # Simula remoção administrativa externa somente nesta fixture.
        # Propriedade/vínculo já foram criados explicitamente; não testamos cascatas.
        db.session.execute(db.delete(Usuario).where(Usuario.id == security_app.security_uid))
        db.session.commit()
    assert client.get("/glebas/").status_code == 302
    with client.session_transaction() as sess:
        assert "user_id" not in sess


def test_sqlite_nao_reutiliza_id_nem_cookie_de_conta_excluida(security_app):
    client = login(security_app)
    with security_app.app_context():
        old_id = security_app.security_uid
        db.session.execute(db.delete(Usuario).where(Usuario.id == old_id))
        db.session.commit()
        replacement = Usuario(nome="Outra conta", email="replacement@example.invalid",
                              perfil="admin", ativo=True,
                              senha_hash=gerar_hash_senha("different-password"))
        db.session.add(replacement)
        db.session.commit()
        assert replacement.id > old_id
    assert client.get("/auditoria/").status_code == 302


def test_rebaixamento_revoga_sessao_e_novo_login_aplica_permissoes(security_app):
    client = login(security_app)
    assert client.get("/glebas/nova").status_code == 200
    with security_app.app_context():
        u = db.session.get(Usuario, security_app.security_uid)
        u.perfil = "trabalhador"
        db.session.commit()
    assert client.get("/glebas/nova").status_code == 302
    assert login(security_app).get("/glebas/nova").status_code == 403


def test_perfil_falso_no_cookie_nao_concede_privilegio(security_app):
    client = login(security_app)
    with client.session_transaction() as sess:
        sess["user_perfil"] = "admin"
        sess["user_nome"] = "Administrador falso"
    assert client.get("/auditoria/").status_code == 403


def test_perfil_desconhecido_no_banco_bloqueia_login_e_sessao(security_app):
    client = login(security_app)
    with security_app.app_context():
        u = db.session.get(Usuario, security_app.security_uid)
        u.perfil = "superadmin"
        db.session.commit()
    assert client.get("/glebas/").status_code == 302
    assert security_app.test_client().post("/auth/login", data={
        "email": "session@example.invalid", "senha": "test-password",
    }).status_code == 403


@pytest.mark.parametrize("uid,version", [
    (True, 1), ("1", 1), ([], 1), (0, 1), (-1, 1),
    (1, None), (1, True), (1, "1"), (1, 0), (1, []),
    (10**1000, 1), (1, 10**1000), (1.0, 1),
])
def test_identificadores_ou_versoes_malformados_nao_autenticam(security_app, uid, version):
    client = security_app.test_client()
    with client.session_transaction() as sess:
        sess["user_id"] = uid
        sess["auth_version"] = version
    assert client.get("/glebas/").status_code == 302


def test_cookie_legado_sem_versao_exige_login(security_app):
    client = security_app.test_client()
    with client.session_transaction() as sess:
        sess["user_id"] = security_app.security_uid
        sess["user_perfil"] = "admin"
    assert client.get("/glebas/").status_code == 302


def test_revogacao_administrativa_persistente(security_app):
    a, b = login(security_app), login(security_app)
    with security_app.app_context():
        u = db.session.get(Usuario, security_app.security_uid)
        u.revogar_sessoes()
        db.session.commit()
    assert a.get("/glebas/").status_code == 302
    assert b.get("/glebas/").status_code == 302


def test_rollback_de_alteracao_nao_revoga_versao_persistida(security_app):
    client = login(security_app)
    with security_app.app_context():
        u = db.session.get(Usuario, security_app.security_uid)
        u.ativo = False
        db.session.flush()
        db.session.rollback()
        assert u.ativo and u.auth_version == 1
    assert client.get("/glebas/").status_code == 200


def test_revogacoes_com_versoes_lidas_antigas_nao_perdem_incremento(security_app):
    from sqlalchemy.orm import Session

    with security_app.app_context():
        with Session(db.engine) as a, Session(db.engine) as b:
            first = a.get(Usuario, security_app.security_uid)
            stale = b.get(Usuario, security_app.security_uid)
            assert first.auth_version == stale.auth_version == 1
            first.revogar_sessoes()
            a.commit()
            stale.revogar_sessoes()
            b.commit()
        assert db.session.get(Usuario, security_app.security_uid).auth_version == 3


def test_cookie_expirado_nao_autentica(security_app, monkeypatch):
    import time
    import itsdangerous.timed

    old_time = time.time() - 9 * 60 * 60
    with monkeypatch.context() as patch:
        patch.setattr(itsdangerous.timed.time, "time", lambda: old_time)
        client = login(security_app)
    assert client.get("/glebas/").status_code == 302


def test_cache_uma_consulta_por_request_sem_reusar_contexto_anterior(security_app):
    selects = []
    def observe(connection, cursor, statement, parameters, context, executemany):
        if statement.lstrip().upper().startswith("SELECT") and "FROM usuario" in statement:
            selects.append(statement)

    with security_app.app_context():
        event.listen(db.engine, "before_cursor_execute", observe)
        try:
            for expected in (1, 2):
                with security_app.test_request_context("/"):
                    session["user_id"] = security_app.security_uid
                    session["auth_version"] = 1
                    assert is_authenticated()
                    assert usuario_atual()["perfil"] == "tecnico"
                    assert can("glebas.create")
                    assert is_authenticated()
                    assert len(selects) == expected
        finally:
            event.remove(db.engine, "before_cursor_execute", observe)


def test_logout_post_revoga_cookie_copiado_e_outro_cliente(security_app):
    a, b = login(security_app), login(security_app)
    copied = a.get_cookie("session").value
    assert a.post("/auth/logout").status_code == 302
    assert a.get("/glebas/").status_code == 302
    assert b.get("/glebas/").status_code == 302
    a.set_cookie("session", copied)
    assert a.get("/glebas/").status_code == 302
    # Cookie revogado não pode derrubar uma nova sessão válida no logout.
    fresh = login(security_app)
    a.set_cookie("session", copied)
    assert a.post("/auth/logout").status_code == 302
    assert fresh.get("/glebas/").status_code == 200


def test_get_logout_nao_altera_sessao(security_app):
    client = login(security_app)
    assert client.get("/auth/logout").status_code == 405
    assert client.get("/glebas/").status_code == 200


def test_logout_post_sem_csrf_e_rejeitado_e_formulario_preserva_protecao(security_app):
    client = login(security_app)
    security_app.config["WTF_CSRF_ENABLED"] = True
    assert client.post("/auth/logout").status_code == 400
    import re
    html = client.get("/").get_data(as_text=True)
    form = re.search(r'<form[^>]*action="/auth/logout"[^>]*>(.*?)</form>', html, re.S)
    assert form is not None
    token = re.search(r'name="csrf_token" value="([^"]+)"', form.group(1)).group(1)
    assert client.post("/auth/logout", data={"csrf_token": token}).status_code == 302
    assert client.get("/glebas/").status_code == 302


def test_logout_desconectado_e_idempotente(security_app):
    client = security_app.test_client()
    assert client.post("/auth/logout").status_code == 302
    assert client.post("/auth/logout").status_code == 302


@pytest.mark.parametrize("endpoint", ["redefinir-senha", "definir-senha"])
def test_reset_ou_definicao_revoga_dois_clientes_e_token_nao_reutiliza(security_app, endpoint):
    from app.services.password_reset_service import (
        gerar_token_definicao_senha, solicitar_reset_por_email,
    )

    a, b = login(security_app), login(security_app)
    with security_app.app_context():
        if endpoint == "definir-senha":
            token = gerar_token_definicao_senha(db.session.get(Usuario, security_app.security_uid))
        else:
            token = solicitar_reset_por_email("session@example.invalid")["token"]
    anonymous = security_app.test_client()
    path = f"/auth/{endpoint}/{token}"
    response = anonymous.post(path, data={"nova_senha": "new-password", "confirmar_senha": "new-password"})
    assert response.status_code == 302
    assert a.get("/glebas/").status_code == 302
    assert b.get("/glebas/").status_code == 302
    assert anonymous.post(path, data={"nova_senha": "another-password", "confirmar_senha": "another-password"}).status_code == 400
    assert anonymous.post("/auth/login", data={"email": "session@example.invalid", "senha": "new-password"}).status_code == 302


def test_alteracao_administrativa_revoga_alvo_sem_derrubar_admin(security_app):
    with security_app.app_context():
        admin = Usuario(nome="Admin", email="admin@example.invalid", perfil="admin",
                        ativo=True, senha_hash=gerar_hash_senha("admin-password"))
        db.session.add(admin)
        db.session.flush()
        prop = criar_propriedade_com_vinculo(admin.id, nome="Fixture segurança compartilhada")
        vincular_usuario_propriedade(security_app.security_uid, prop.id)
        # A edição global de senha/perfil exige que o operador acesse todos
        # os contextos do alvo, incluindo a propriedade original da fixture.
        vincular_usuario_propriedade(admin.id, security_app.security_pid)
        db.session.commit()
        propriedade_admin_id = prop.id
    admin_client = security_app.test_client()
    assert admin_client.post("/auth/login", data={"email": "admin@example.invalid", "senha": "admin-password"}).status_code == 302
    assert admin_client.post("/propriedades/selecionar", data={
        "propriedade_id": str(propriedade_admin_id),
    }).status_code == 302
    target_client = login(security_app)
    response = admin_client.post(f"/usuarios/{security_app.security_uid}/editar", data={
        "nome": "Gerente teste", "email": "updated@example.invalid",
        "perfil": "trabalhador", "ativo": "1", "senha": "new-password",
        "confirmar_senha": "new-password",
    })
    assert response.status_code == 302
    assert target_client.get("/glebas/nova").status_code == 302
    assert admin_client.get("/usuarios/").status_code == 200
    from app.models import LogAuditoria
    with security_app.app_context():
        change = LogAuditoria.query.filter_by(acao="usuarios.email_change").one()
        assert "session@example.invalid" not in change.descricao
        assert "updated@example.invalid" not in change.descricao


def test_link_email_reset_absoluto_sem_app_base_url(security_app, monkeypatch):
    import app.blueprints.auth.routes as routes

    links = []
    monkeypatch.setattr(routes, "email_ativo", lambda: True)
    monkeypatch.setattr(routes, "email_recuperacao_senha", lambda usuario, link: links.append(link))
    security_app.config["APP_BASE_URL"] = ""
    response = security_app.test_client().post("/auth/esqueci-senha", data={"email": "session@example.invalid"}, base_url="https://connectagro.example.invalid")
    assert response.status_code == 200
    assert len(links) == 1
    assert links[0].startswith("https://connectagro.example.invalid/auth/redefinir-senha/")
