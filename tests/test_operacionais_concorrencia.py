"""Corridas reais entre conexões SQLite distintas, com snapshots e FKs desligadas.

Eventos coordenam a ordem; nenhuma espera temporal é usada como prova de lock.
O PostgreSQL é validado separadamente na integração descartável da etapa.
"""
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from threading import Event

from flask import g, request
import pytest

from app import create_app
from app.config import TestingConfig
from app.extensions import db
from app.models import (
    AplicacaoInsumo, AtividadeItem, AtividadeOperacional, Cultura, CulturaGleba,
    Gleba, Usuario, UsuarioPropriedade,
)
from app.services import operacionais_lock
from app.utils.auth import gerar_hash_senha
from tests.factories import criar_propriedade_com_vinculo, vincular_usuario_propriedade


PASSWORD = "temporary-concurrency-password"


@pytest.fixture
def concurrent_app(tmp_path, monkeypatch):
    uri = "sqlite:///" + str(tmp_path / "concorrencia.sqlite")
    monkeypatch.setattr(TestingConfig, "SQLALCHEMY_DATABASE_URI", uri)
    monkeypatch.setattr(TestingConfig, "SQLALCHEMY_DIRECT_URI", uri)
    monkeypatch.setattr(TestingConfig, "SQLALCHEMY_ENGINE_OPTIONS", {
        "connect_args": {"timeout": 2, "check_same_thread": False}}, raising=False)
    application = create_app("testing")
    with application.app_context():
        db.create_all()
        with db.engine.connect() as connection:
            assert connection.exec_driver_sql("PRAGMA journal_mode=WAL").scalar().lower() == "wal"
            assert connection.exec_driver_sql("PRAGMA foreign_keys").scalar() == 0
            connection.commit()
        users = {}
        password_hash = gerar_hash_senha(PASSWORD)
        for alias, perfil in (("admin", "admin"), ("manager", "tecnico"), ("worker", "trabalhador")):
            user = Usuario(nome=alias, email=f"{alias}@concorrencia.invalid", senha_hash=password_hash,
                           perfil=perfil, ativo=True)
            db.session.add(user)
            db.session.flush()
            users[alias] = user
        prop = criar_propriedade_com_vinculo(users["admin"].id, nome="Propriedade das corridas")
        for alias in ("manager", "worker"):
            vincular_usuario_propriedade(users[alias].id, prop.id)
        gleba = Gleba(propriedade_id=prop.id, nome="Área utilizada", area_ha=10)
        vazia = Gleba(propriedade_id=prop.id, nome="Área sem histórico", area_ha=20)
        cultura = Cultura(propriedade_id=prop.id, nome="Cultura utilizada")
        cultura_vazia = Cultura(propriedade_id=prop.id, nome="Cultura sem histórico")
        from app.models import ProdutoBase
        produto = ProdutoBase(nome="Produto das corridas", slug="produto-corridas", classe="fertilizante",
                              status_sistema="pre_cadastrado", status_regulatorio="tipo_tecnico_generico")
        db.session.add_all([gleba, vazia, cultura, cultura_vazia, produto])
        db.session.flush()
        cg = CulturaGleba(cultura_id=cultura.id, gleba_id=gleba.id)
        cg_vazio = CulturaGleba(cultura_id=cultura_vazia.id, gleba_id=vazia.id)
        db.session.add_all([cg, cg_vazio])
        db.session.flush()
        aplicacao = AplicacaoInsumo(cultura_gleba_id=cg.id, produto_base_id=produto.id,
            data_aplicacao="2026-05-10", dose=2, unidade="L/ha", responsavel="Executor",
            quantidade_utilizada=Decimal("3"), unidade_quantidade="L", criado_por_id=users["admin"].id)
        atividade = AtividadeOperacional(gleba_id=gleba.id, cultura_gleba_id=cg.id,
            tipo_atividade="Operação informada", data_execucao="2026-05-10", responsavel="Executor",
            criado_por_id=users["admin"].id)
        atividade.itens.append(AtividadeItem(produto_base_id=produto.id,
            dose=Decimal("2"), unidade_dose="L/ha", quantidade_utilizada=Decimal("3"),
            unidade_quantidade="L"))
        db.session.add_all([aplicacao, atividade])
        db.session.commit()
        application.race_ids = {alias: user.id for alias, user in users.items()}
        application.race_ids.update(prop=prop.id, gleba=gleba.id, vazia=vazia.id,
            cultura_vazia=cultura_vazia.id, cg=cg.id, cg_vazio=cg_vazio.id,
            produto=produto.id, aplicacao=aplicacao.id, atividade=atividade.id,
            item=atividade.itens[0].id)
    yield application
    with application.app_context():
        db.session.remove()
        db.engine.dispose()


def _login(application, alias):
    client = application.test_client()
    assert client.post("/auth/login", data={"email": f"{alias}@concorrencia.invalid",
        "senha": PASSWORD}).status_code == 302
    return client


def _dados(application, kind, *, quantidade="4"):
    ids = application.race_ids
    dados = {"cultura_gleba_id": str(ids["cg"]), "produto_base_id": str(ids["produto"]),
             "responsavel": "Executor", "dose": "2", "quantidade_utilizada": quantidade,
             "unidade_quantidade": "L", "observacao": "Revisão concorrente"}
    if kind == "aplicacao":
        dados.update(data_aplicacao="2026-05-10", unidade="L/ha")
        return f"/aplicacoes/{ids['aplicacao']}/editar", dados
    dados.update(gleba_id=str(ids["gleba"]), tipo_atividade="Operação informada",
                 data_execucao="2026-05-10", unidade_dose="L/ha", item_id=str(ids["item"]))
    return f"/atividades/{ids['atividade']}/editar", dados


def _snapshot_anterior(application, kind, loaded, *, physical=False):
    @application.before_request
    def carregar_snapshot_antes_do_lock():
        if request.headers.get("X-Corrida") != "sim":
            return
        if physical:
            db.session.connection().exec_driver_sql("BEGIN")
        model = AplicacaoInsumo if kind == "aplicacao" else AtividadeItem
        rid = application.race_ids[kind if kind == "aplicacao" else "item"]
        g._snapshot_da_corrida = db.session.get(model, rid)
        assert g._snapshot_da_corrida.custo_total is None
        loaded.set()


@pytest.mark.parametrize("kind", ["aplicacao", "atividade"])
def test_gerente_revalida_custo_confirmado_por_admin_enquanto_aguardava_lock(concurrent_app, monkeypatch, kind):
    loaded, attempting = Event(), Event()
    _snapshot_anterior(concurrent_app, kind, loaded)
    client = _login(concurrent_app, "manager")
    original = operacionais_lock._adquirir_lock

    def observar_lock(connection, property_id):
        if request.headers.get("X-Corrida") == "sim":
            attempting.set()
        return original(connection, property_id)

    monkeypatch.setattr(operacionais_lock, "_adquirir_lock", observar_lock)
    path, dados = _dados(concurrent_app, kind)
    with concurrent_app.app_context():
        model = AplicacaoInsumo if kind == "aplicacao" else AtividadeItem
        rid = concurrent_app.race_ids[kind if kind == "aplicacao" else "item"]
        with db.engine.connect() as writer:
            writer.exec_driver_sql("BEGIN IMMEDIATE")
            writer.execute(db.update(model.__table__).where(model.id == rid).values(
                custo_unitario=Decimal("2"), custo_total=Decimal("6"), moeda="BRL",
                origem_custo="calculado_quantidade_unitario"))
            with ThreadPoolExecutor(max_workers=1) as pool:
                future = pool.submit(client.post, path, data=dados, headers={"X-Corrida": "sim"})
                try:
                    assert loaded.wait(5), "O gerente deve ter lido o snapshot sem custo"
                    assert attempting.wait(5), "A requisição deve adquirir o lock comum"
                    assert not future.done()
                    writer.commit()
                    response = future.result(timeout=10)
                finally:
                    writer.rollback()
            assert response.status_code == 403
        db.session.expire_all()
        row = db.session.get(model, rid)
        assert row.quantidade_utilizada == Decimal("3")
        assert row.custo_unitario == Decimal("2")
        assert row.custo_total == Decimal("6")


@pytest.mark.parametrize("alteracao,expected", [
    ("vinculo", 403), ("perfil", 403), ("ativo", 302), ("epoch", 302),
])
def test_autorizacao_e_revalidada_apos_a_espera(concurrent_app, monkeypatch, alteracao, expected):
    loaded, attempting = Event(), Event()
    _snapshot_anterior(concurrent_app, "aplicacao", loaded)
    client = _login(concurrent_app, "manager")
    original = operacionais_lock._adquirir_lock

    def observar_lock(connection, property_id):
        if request.headers.get("X-Corrida") == "sim":
            attempting.set()
        return original(connection, property_id)

    monkeypatch.setattr(operacionais_lock, "_adquirir_lock", observar_lock)
    path, dados = _dados(concurrent_app, "aplicacao", quantidade="3")
    ids = concurrent_app.race_ids
    with concurrent_app.app_context():
        with db.engine.connect() as writer:
            writer.exec_driver_sql("BEGIN IMMEDIATE")
            if alteracao == "vinculo":
                writer.execute(db.update(UsuarioPropriedade.__table__).where(
                    UsuarioPropriedade.usuario_id == ids["manager"],
                    UsuarioPropriedade.propriedade_id == ids["prop"]).values(ativo=False))
            else:
                valores = ({"perfil": "trabalhador"} if alteracao == "perfil" else
                           {"ativo": False} if alteracao == "ativo" else
                           {"auth_version": Usuario.auth_version + 1})
                writer.execute(db.update(Usuario.__table__).where(Usuario.id == ids["manager"]).values(**valores))
            with ThreadPoolExecutor(max_workers=1) as pool:
                future = pool.submit(client.post, path, data=dados, headers={"X-Corrida": "sim"})
                try:
                    assert loaded.wait(5)
                    assert attempting.wait(5)
                    writer.commit()
                    response = future.result(timeout=10)
                finally:
                    writer.rollback()
            assert response.status_code == expected
            if expected == 302:
                assert "/auth/login" in response.headers["Location"]
        assert db.session.get(AplicacaoInsumo, ids["aplicacao"]).observacao is None


def test_snapshot_fisico_sqlite_desatualizado_e_recusado_sem_repetir_escrita(concurrent_app, monkeypatch):
    loaded, attempting, committed = Event(), Event(), Event()
    _snapshot_anterior(concurrent_app, "aplicacao", loaded, physical=True)
    client = _login(concurrent_app, "manager")
    original = operacionais_lock._adquirir_lock

    def esperar_commit(connection, property_id):
        if request.headers.get("X-Corrida") == "sim":
            attempting.set()
            assert committed.wait(5)
        return original(connection, property_id)

    monkeypatch.setattr(operacionais_lock, "_adquirir_lock", esperar_commit)
    path, dados = _dados(concurrent_app, "aplicacao")
    ids = concurrent_app.race_ids
    with concurrent_app.app_context():
        with db.engine.connect() as writer:
            writer.exec_driver_sql("BEGIN IMMEDIATE")
            writer.execute(db.update(AplicacaoInsumo.__table__).where(
                AplicacaoInsumo.id == ids["aplicacao"]).values(
                    custo_total=Decimal("6"), moeda="BRL", origem_custo="informado_usuario"))
            with ThreadPoolExecutor(max_workers=1) as pool:
                future = pool.submit(client.post, path, data=dados, headers={"X-Corrida": "sim"})
                try:
                    assert loaded.wait(5)
                    assert attempting.wait(5)
                    writer.commit()
                    committed.set()
                    response = future.result(timeout=10)
                finally:
                    writer.rollback()
                    committed.set()
            assert response.status_code == 409
        row = db.session.get(AplicacaoInsumo, ids["aplicacao"])
        assert row.quantidade_utilizada == Decimal("3")
        assert row.custo_total == Decimal("6")


@pytest.mark.parametrize("parent", ["glebas", "culturas"])
def test_remocao_do_pai_e_criacao_de_aplicacao_nao_geram_orfao_com_fk_off(concurrent_app, monkeypatch, parent):
    admin = _login(concurrent_app, "admin")
    worker = _login(concurrent_app, "worker")
    checked, worker_waiting, release = Event(), Event(), Event()
    if parent == "glebas":
        from app.blueprints.glebas import routes
        pid = concurrent_app.race_ids["vazia"]
    else:
        from app.blueprints.culturas import routes
        pid = concurrent_app.race_ids["cultura_vazia"]
    original_check = routes._cg_ids_com_historico
    original_lock = operacionais_lock._adquirir_lock

    def pausar_apos_verificar_historico(cg_ids):
        result = original_check(cg_ids)
        if request.headers.get("X-Excluir") == "sim":
            assert not result
            checked.set()
            assert release.wait(5)
        return result

    def observar_criacao(connection, property_id):
        if request.headers.get("X-Criar") == "sim":
            worker_waiting.set()
        return original_lock(connection, property_id)

    monkeypatch.setattr(routes, "_cg_ids_com_historico", pausar_apos_verificar_historico)
    monkeypatch.setattr(operacionais_lock, "_adquirir_lock", observar_criacao)
    dados = {"cultura_gleba_id": str(concurrent_app.race_ids["cg_vazio"]),
             "produto_base_id": str(concurrent_app.race_ids["produto"]),
             "data_aplicacao": "2026-05-10", "responsavel": "Executor"}
    with ThreadPoolExecutor(max_workers=2) as pool:
        deletion = pool.submit(admin.post, f"/{parent}/{pid}/remover", headers={"X-Excluir": "sim"})
        try:
            assert checked.wait(5)
            creation = pool.submit(worker.post, "/aplicacoes/nova", data=dados, headers={"X-Criar": "sim"})
            assert worker_waiting.wait(5)
            release.set()
            assert deletion.result(timeout=10).status_code == 302
            assert creation.result(timeout=10).status_code == 400
        finally:
            release.set()
    with concurrent_app.app_context():
        assert db.session.get(CulturaGleba, concurrent_app.race_ids["cg_vazio"]) is None
        assert AplicacaoInsumo.query.filter_by(cultura_gleba_id=concurrent_app.race_ids["cg_vazio"]).count() == 0


def test_get_nao_adquire_lock_e_validacao_400_libera_a_escrita(concurrent_app, monkeypatch):
    client = _login(concurrent_app, "admin")
    original = operacionais_lock._adquirir_lock

    def recusar_get(*args):
        assert request.method == "POST", "GET não deve reservar escrita"
        return original(*args)

    monkeypatch.setattr(operacionais_lock, "_adquirir_lock", recusar_get)
    assert client.get("/aplicacoes/nova").status_code == 200
    assert client.post("/aplicacoes/nova", data={"data_aplicacao": "inválida"}).status_code == 400
    with concurrent_app.app_context():
        with db.engine.connect() as connection:
            connection.exec_driver_sql("BEGIN IMMEDIATE")
            assert connection.connection.driver_connection.in_transaction
            connection.rollback()
