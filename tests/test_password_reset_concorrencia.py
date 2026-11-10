"""Uso único e rollback de senha/convite em conexões SQLite independentes."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from threading import Barrier

import pytest
from sqlalchemy import event

from app import create_app
from app.config import TestingConfig
from app.extensions import db
from app.models import SenhaResetToken, Usuario
from app.services import password_reset_service as service
from app.utils.auth import gerar_hash_senha, verificar_senha


@pytest.fixture
def reset_app(monkeypatch, tmp_path):
    uri = "sqlite:///" + str(tmp_path / "reset-concorrencia.sqlite")
    monkeypatch.setattr(TestingConfig, "SQLALCHEMY_DATABASE_URI", uri)
    monkeypatch.setattr(TestingConfig, "SQLALCHEMY_DIRECT_URI", uri)
    application = create_app("testing")
    with application.app_context():
        db.create_all()
        usuario = Usuario(nome="Conta de teste", email="reset@concorrencia.invalid",
                          perfil="trabalhador", ativo=True,
                          senha_hash=gerar_hash_senha("senha-anterior"))
        db.session.add(usuario)
        db.session.commit()
        application.reset_uid = usuario.id
    yield application
    with application.app_context():
        db.session.remove()
        db.engine.dispose()


def _emitir(application, tipo="reset"):
    with application.app_context():
        if tipo == "convite":
            return service.gerar_token_definicao_senha(
                db.session.get(Usuario, application.reset_uid))
        return service.solicitar_reset_por_email("reset@concorrencia.invalid")["token"]


@pytest.mark.parametrize("tipo", ["reset", "convite"])
def test_duas_conexoes_nao_consumem_o_mesmo_token(reset_app, monkeypatch, tipo):
    token = _emitir(reset_app, tipo)
    barreira = Barrier(2)
    original = service.gerar_hash_senha

    def hash_simultaneo(senha):
        resultado = original(senha)
        # Ambas as requisições já aceitaram o token antes da disputa de escrita.
        # O banco e seus commits são reais; só a ordem de chegada é coordenada.
        barreira.wait(timeout=15)
        return resultado

    monkeypatch.setattr(service, "gerar_hash_senha", hash_simultaneo)

    def consumir(senha):
        with reset_app.app_context():
            return service.redefinir_senha_com_token(token, senha, senha)

    senhas = ["senha-concorrente-a", "senha-concorrente-b"]
    with ThreadPoolExecutor(max_workers=2) as executor:
        futuros = [executor.submit(consumir, senha) for senha in senhas]
        resultados = [f.result(timeout=25) for f in futuros]
    assert sum(ok for ok, _ in resultados) == 1
    perdedor = next(erros for ok, erros in resultados if not ok)
    assert "inválido, expirado ou já utilizado" in perdedor[0]
    vencedora = senhas[next(i for i, (ok, _) in enumerate(resultados) if ok)]
    with reset_app.app_context():
        usuario = db.session.get(Usuario, reset_app.reset_uid)
        assert verificar_senha(usuario.senha_hash, vencedora)
        assert usuario.auth_version == 2
        assert SenhaResetToken.query.one().usado is True
        assert service.validar_token_reset(token) is None


@pytest.mark.parametrize("mudanca", ["inativacao", "expiracao"])
def test_estado_e_revalidado_apos_calcular_hash(reset_app, monkeypatch, mudanca):
    token = _emitir(reset_app)
    original = service.gerar_hash_senha

    def hash_com_mudanca(senha):
        resultado = original(senha)
        # Outra sessão confirma a mudança depois da leitura inicial do token.
        with reset_app.app_context():
            if mudanca == "inativacao":
                db.session.get(Usuario, reset_app.reset_uid).ativo = False
            else:
                SenhaResetToken.query.one().expira_em = (
                    datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()
            db.session.commit()
        return resultado

    monkeypatch.setattr(service, "gerar_hash_senha", hash_com_mudanca)
    with reset_app.app_context():
        ok, erros = service.redefinir_senha_com_token(token, "senha-nova", "senha-nova")
        assert not ok and erros
        usuario = db.session.get(Usuario, reset_app.reset_uid)
        assert verificar_senha(usuario.senha_hash, "senha-anterior")
        assert usuario.auth_version == (2 if mudanca == "inativacao" else 1)
        assert SenhaResetToken.query.one().usado is False


def test_falha_da_senha_desfaz_consumo_e_revogacao(reset_app):
    token = _emitir(reset_app)

    def falhar(mapper, connection, usuario):
        raise RuntimeError("Falha de persistência controlada")

    event.listen(Usuario, "before_update", falhar)
    try:
        with reset_app.app_context():
            with pytest.raises(RuntimeError, match="Falha de persistência"):
                service.redefinir_senha_com_token(token, "senha-nova", "senha-nova")
            # O serviço libera sua transação, sem exigir rollback do chamador.
            usuario = db.session.get(Usuario, reset_app.reset_uid)
            assert verificar_senha(usuario.senha_hash, "senha-anterior")
            assert usuario.auth_version == 1
            assert SenhaResetToken.query.one().usado is False
    finally:
        event.remove(Usuario, "before_update", falhar)
    with reset_app.app_context():
        assert service.redefinir_senha_com_token(token, "senha-nova", "senha-nova") == (True, [])
        assert db.session.get(Usuario, reset_app.reset_uid).auth_version == 2
