"""Governança por contexto, incluindo requests concorrentes em SQLite real."""
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest

from app import create_app
from app.blueprints.usuarios import routes
from app.extensions import db
from app.models import LogAuditoria, Propriedade, Usuario, UsuarioPropriedade
from app.utils.auth import gerar_hash_senha


@pytest.fixture
def governance_app(monkeypatch, tmp_path):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///" + str(tmp_path / "governance.sqlite"))
    monkeypatch.delenv("DIRECT_URL", raising=False)
    application = create_app("development")
    application.config.update(TESTING=True, DEBUG=False, WTF_CSRF_ENABLED=False,
                              MAIL_ATIVO=False, MAIL_SUPPRESS_SEND=True)
    with application.app_context():
        db.create_all()
        users = [Usuario(nome=name, email=f"{name}@governance.invalid", perfil=role,
                         ativo=True, senha_hash=gerar_hash_senha("governance-password"))
                 for name, role in [("admin-a", "admin"), ("admin-b", "admin"),
                                    ("worker", "trabalhador")]]
        db.session.add_all(users)
        db.session.flush()
        prop = Propriedade(usuario_id=users[0].id, nome="Contexto governança")
        db.session.add(prop)
        db.session.flush()
        db.session.add_all([UsuarioPropriedade(usuario_id=u.id,
            propriedade_id=prop.id, ativo=True) for u in users])
        db.session.commit()
        application.governance_ids = {u.nome: u.id for u in users}
        application.governance_ids["property"] = prop.id
    yield application
    with application.app_context():
        db.session.remove()
        db.engine.dispose()


def _login(application, name):
    client = application.test_client()
    assert client.post("/auth/login", data={"email": f"{name}@governance.invalid",
        "senha": "governance-password"}).status_code == 302
    return client


def _deactivation(name, uid, endpoint):
    data = None if endpoint == "inativar" else {
        "nome": name, "email": f"{name}@governance.invalid", "perfil": "admin",
        # Checkbox ausente: inativar pelo formulário de edição.
    }
    return f"/usuarios/{uid}/{endpoint}", data


@pytest.mark.parametrize("endpoints", [
    ("inativar", "inativar"), ("editar", "editar"), ("inativar", "editar"),
])
@pytest.mark.parametrize("shared", [False, True])
def test_duas_inativacoes_cruzadas_preservam_administrador(
        governance_app, monkeypatch, endpoints, shared):
    ids = governance_app.governance_ids
    if shared:
        with governance_app.app_context():
            other = Propriedade(usuario_id=ids["admin-a"], nome="Outro contexto")
            db.session.add(other)
            db.session.flush()
            other_id = other.id
            db.session.add_all([UsuarioPropriedade(usuario_id=ids[name],
                propriedade_id=other.id, ativo=True) for name in ("admin-a", "admin-b")])
            db.session.commit()
    clients = [_login(governance_app, name) for name in ("admin-a", "admin-b")]
    if shared:
        for client in clients:
            assert client.post("/propriedades/selecionar", data={
                "propriedade_id": str(ids["property"])}).status_code == 302
    cookies = [c.get_cookie("session").value for c in clients]
    barrier = Barrier(2)
    original = routes._serializar_alteracao_usuario

    def simultaneous(prop, permission):
        # Ambos passaram autenticação/contexto antes de disputar o mesmo lock.
        barrier.wait(timeout=15)
        return original(prop, permission)

    monkeypatch.setattr(routes, "_serializar_alteracao_usuario", simultaneous)

    def request(index):
        target = ("admin-b", "admin-a")[index]
        path, data = _deactivation(target, ids[target], endpoints[index])
        client = governance_app.test_client()
        client.set_cookie("session", cookies[index])
        response = client.post(path, data=data)
        return response.status_code, response.headers.get("Location", "")

    with ThreadPoolExecutor(max_workers=2) as executor:
        pending = [executor.submit(request, index) for index in range(2)]
        outcomes = [future.result(timeout=25) for future in pending]
    assert sum(status == 302 and location.endswith("/usuarios/")
               for status, location in outcomes) == 1
    assert sum((status == 403 if shared else
                status == 302 and location.endswith("/auth/login"))
               for status, location in outcomes) == 1
    with governance_app.app_context():
        active = (Usuario.query.join(UsuarioPropriedade,
            UsuarioPropriedade.usuario_id == Usuario.id).filter(
                Usuario.perfil == "admin", Usuario.ativo.is_(True),
                UsuarioPropriedade.propriedade_id == ids["property"],
                UsuarioPropriedade.ativo.is_(True)).count())
        assert active == 1
        assert LogAuditoria.query.filter_by(acao="usuarios.deactivate").count() == 1
        if shared:
            assert Usuario.query.filter_by(perfil="admin", ativo=True).count() == 2
            assert UsuarioPropriedade.query.filter_by(propriedade_id=other_id, ativo=True).count() == 2
            assert all(db.session.get(Usuario, ids[name]).auth_version == 1
                       for name in ("admin-a", "admin-b"))


@pytest.mark.parametrize("change", ["status", "profile", "epoch", "membership"])
def test_ator_e_revalidado_depois_da_espera(governance_app, monkeypatch, change):
    ids = governance_app.governance_ids
    client = _login(governance_app, "admin-a")
    original = routes._serializar_alteracao_usuario

    def access_changed(prop, permission):
        # Simula outra transação que confirmou uma revogação após o guard.
        with governance_app.app_context():
            actor = db.session.get(Usuario, ids["admin-a"])
            if change == "membership":
                UsuarioPropriedade.query.filter_by(usuario_id=actor.id,
                    propriedade_id=ids["property"]).one().ativo = False
            elif change == "status":
                actor.ativo = False
            elif change == "profile":
                actor.perfil = "trabalhador"
            else:
                actor.revogar_sessoes()
            db.session.commit()
        return original(prop, permission)

    monkeypatch.setattr(routes, "_serializar_alteracao_usuario", access_changed)
    response = client.post(f"/usuarios/{ids['worker']}/inativar")
    assert response.status_code == (403 if change == "membership" else 302)
    if change != "membership":
        assert response.headers["Location"].endswith("/auth/login")
    with governance_app.app_context():
        assert db.session.get(Usuario, ids["worker"]).ativo
        assert UsuarioPropriedade.query.filter_by(usuario_id=ids["worker"],
            propriedade_id=ids["property"]).one().ativo
        assert LogAuditoria.query.filter_by(acao="usuarios.deactivate").count() == 0


def test_transacao_sqlite_ja_iniciada_e_preservada_sem_commit_antecipado(
        governance_app, monkeypatch):
    ids = governance_app.governance_ids
    client = _login(governance_app, "admin-a")
    original = routes._serializar_alteracao_usuario

    def transaction_started(prop, permission):
        connection = db.session.connection()
        connection.exec_driver_sql("BEGIN")
        connection.execute(db.update(Propriedade).where(Propriedade.id == prop.id)
                           .values(municipio="Ainda não confirmado"))
        actor = original(prop, permission)
        # Um observador independente não vê a escrita antes do commit da rota.
        with db.engine.connect() as observer:
            assert observer.execute(db.select(Propriedade.municipio).where(
                Propriedade.id == prop.id)).scalar_one() is None
        return actor

    monkeypatch.setattr(routes, "_serializar_alteracao_usuario", transaction_started)
    assert client.post(f"/usuarios/{ids['worker']}/inativar").status_code == 302
    with governance_app.app_context():
        assert db.session.get(Propriedade, ids["property"]).municipio == "Ainda não confirmado"
        assert not db.session.get(Usuario, ids["worker"]).ativo
