"""Revalidação da autoridade global após espera real entre conexões SQLite."""
from concurrent.futures import ThreadPoolExecutor
from threading import Event

from flask import request

from app import create_app
from app.config import TestingConfig
from app.extensions import db
from app.models import (
    CatalogoControle, ProdutoBase, ProdutoLocal, Propriedade, SolicitacaoCatalogo,
    Usuario,
)
from app.services import catalogo_governanca_service
from app.services.catalogo_local_service import json_canonico
from app.utils.auth import gerar_hash_senha


def test_aprovador_revogado_durante_espera_nao_publica(tmp_path, monkeypatch):
    uri = "sqlite:///" + str(tmp_path / "catalogo-concorrente.sqlite")
    monkeypatch.setattr(TestingConfig, "SQLALCHEMY_DATABASE_URI", uri)
    monkeypatch.setattr(TestingConfig, "SQLALCHEMY_DIRECT_URI", uri)
    monkeypatch.setattr(TestingConfig, "SQLALCHEMY_ENGINE_OPTIONS", {
        "connect_args": {"timeout": 5, "check_same_thread": False}}, raising=False)
    app = create_app("testing")
    with app.app_context():
        db.create_all()
        with db.engine.connect() as conexao:
            assert conexao.exec_driver_sql("PRAGMA journal_mode=WAL").scalar().lower() == "wal"
            conexao.commit()
        dono = Usuario(nome="Dono", email="dono@corrida8.invalid", senha_hash="sem-login",
                       perfil="admin", ativo=True)
        revisor = Usuario(nome="Revisor global", email="revisor@corrida8.invalid",
                          senha_hash=gerar_hash_senha("Corrida-catalogo8!"),
                          perfil="admin", ativo=True, catalogo_global_aprovador=True)
        db.session.add_all([dono, revisor, CatalogoControle(id=1)])
        db.session.flush()
        origem = Propriedade(usuario_id=dono.id, nome="Origem privada")
        db.session.add(origem)
        db.session.flush()
        local = ProdutoLocal(propriedade_id=origem.id, nome="Produto proposto",
                             classe="fertilizante", criado_por_id=dono.id)
        db.session.add(local)
        db.session.flush()
        pedido = SolicitacaoCatalogo(propriedade_id=origem.id, produto_local_id=local.id,
            tipo="inclusao", origem_versao=1, solicitado_por_id=dono.id,
            conteudo_json=json_canonico({"nome": "Produto proposto", "classe": "fertilizante"}))
        db.session.add(pedido)
        db.session.commit()
        revisor_id, pedido_id = revisor.id, pedido.id

    cliente = app.test_client()
    assert cliente.post("/auth/login", data={"email": "revisor@corrida8.invalid",
                                             "senha": "Corrida-catalogo8!"}).status_code == 302
    tentando = Event()
    adquirir_original = catalogo_governanca_service.adquirir_lock_catalogo

    def observar_lock(sessao):
        if request.headers.get("X-Corrida-Catalogo") == "sim":
            tentando.set()
        return adquirir_original(sessao)

    monkeypatch.setattr(catalogo_governanca_service, "adquirir_lock_catalogo", observar_lock)
    try:
        with app.app_context():
            with db.engine.connect() as escritor:
                escritor.exec_driver_sql("BEGIN IMMEDIATE")
                escritor.execute(db.update(Usuario.__table__).where(
                    Usuario.id == revisor_id).values(catalogo_global_aprovador=False))
                with ThreadPoolExecutor(max_workers=1) as pool:
                    futuro = pool.submit(cliente.post, f"/catalogo/revisao/{pedido_id}/aprovar",
                        data={}, headers={"X-Corrida-Catalogo": "sim"})
                    try:
                        # O fluxo ultrapassou a autorização inicial lendo a
                        # versão anterior e chegou ao lock realmente ocupado.
                        assert tentando.wait(5)
                        assert not futuro.done()
                        escritor.commit()
                        resposta = futuro.result(timeout=10)
                    finally:
                        escritor.rollback()
                assert resposta.status_code == 403
            db.session.expire_all()
            assert not db.session.get(Usuario, revisor_id).catalogo_global_aprovador
            assert db.session.get(SolicitacaoCatalogo, pedido_id).estado == "pendente"
            assert ProdutoBase.query.count() == 0
    finally:
        with app.app_context():
            db.session.remove()
            db.engine.dispose()
