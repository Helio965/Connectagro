"""Testes da Fase 7.3 — Auditoria/logs administrativos.

Cobre model/schema, serviço, tela (admin-only), eventos de autenticação,
recuperação de senha, painel de usuários, permissão negada, upload, CRUDs,
escopo por propriedade e ausência de dados sensíveis nos logs.
"""
import io

import pytest

from app.extensions import db
from app.utils.auth import gerar_hash_senha

SENHA = "senha123"


def _criar_usuario(nome, email, perfil, ativo=True):
    from app.models import Usuario

    usuario = Usuario(nome=nome, email=email, perfil=perfil, ativo=ativo,
                      senha_hash=gerar_hash_senha(SENHA))
    db.session.add(usuario)
    db.session.commit()
    return usuario


def _vincular(usuario, propriedade):
    from app.models import UsuarioPropriedade

    db.session.add(UsuarioPropriedade(usuario_id=usuario.id,
                                      propriedade_id=propriedade.id, ativo=True))
    db.session.commit()


def _popular(app):
    from app.models import (Cultura, CulturaGleba, Gleba, ProdutoBase,
                            Propriedade)

    with app.app_context():
        admin = _criar_usuario("Admin", "admin@connectagro.com", "admin")
        tecnico = _criar_usuario("Técnico", "tecnico@connectagro.com", "tecnico")
        trab = _criar_usuario("Trab", "trabalhador@connectagro.com", "trabalhador")
        prop = Propriedade(usuario_id=admin.id, nome="Fazenda Auditoria")
        db.session.add(prop)
        db.session.commit()
        for u in (admin, tecnico, trab):
            _vincular(u, prop)

        gleba = Gleba(propriedade_id=prop.id, nome="Gleba A", area_ha=10)
        cultura = Cultura(propriedade_id=prop.id, nome="Soja", status="em_andamento")
        produto = ProdutoBase(nome="Produto Aud", slug="produto-aud",
                              classe="defensivo", categoria="herbicida",
                              status_sistema="pre_cadastrado",
                              status_regulatorio="nao_validado_agrofit")
        db.session.add_all([gleba, cultura, produto])
        db.session.commit()
        cg = CulturaGleba(cultura_id=cultura.id, gleba_id=gleba.id)
        db.session.add(cg)
        db.session.commit()

        # segunda propriedade (para escopo)
        outro_admin = _criar_usuario("Outro", "outro@connectagro.com", "admin")
        outra_prop = Propriedade(usuario_id=outro_admin.id, nome="Fazenda Externa")
        db.session.add(outra_prop)
        db.session.commit()
        _vincular(outro_admin, outra_prop)

        return {
            "prop_id": prop.id, "outra_prop_id": outra_prop.id,
            "gleba_id": gleba.id, "cultura_id": cultura.id,
            "cg_id": cg.id, "produto_id": produto.id,
            "tecnico_id": tecnico.id, "trab_id": trab.id,
        }


@pytest.fixture
def app_aud(app, tmp_path):
    app.config["UPLOAD_FOLDER"] = str(tmp_path)
    app.config["MAX_CONTENT_LENGTH"] = 1024 * 1024
    with app.app_context():
        db.create_all()
    app.aud_ids = _popular(app)
    return app


def _login(client, email="admin@connectagro.com"):
    resp = client.post("/auth/login", data={"email": email, "senha": SENHA})
    assert resp.status_code == 302
    return resp


def _logs(app, **filtros):
    from app.models import LogAuditoria

    with app.app_context():
        q = LogAuditoria.query
        for campo, valor in filtros.items():
            q = q.filter(getattr(LogAuditoria, campo) == valor)
        return q.all()


def _acoes(app):
    from app.models import LogAuditoria

    with app.app_context():
        return [l.acao for l in LogAuditoria.query.all()]


# --- Model/schema ----------------------------------------------------------

def test_model_log_auditoria_existe(app):
    from app.models import LogAuditoria

    assert LogAuditoria.__tablename__ == "log_auditoria"
    cols = {"id", "usuario_id", "propriedade_id", "acao", "entidade",
            "entidade_id", "resultado", "descricao", "ip", "user_agent",
            "criado_em"}
    assert cols <= set(db.metadata.tables["log_auditoria"].columns.keys())


# --- Serviço ---------------------------------------------------------------

def test_registrar_evento_cria_log(app_aud):
    from app.services.auditoria_service import registrar_evento
    from app.models import LogAuditoria

    ids = app_aud.aud_ids
    with app_aud.app_context():
        log = registrar_evento("teste.acao", entidade="x", entidade_id=1,
                               resultado="sucesso", descricao="ok",
                               usuario_id=ids["tecnico_id"],
                               propriedade_id=ids["prop_id"])
        assert log is not None
        salvo = db.session.get(LogAuditoria, log.id)
        assert salvo.acao == "teste.acao"
        assert salvo.resultado == "sucesso"
        assert salvo.usuario_id == ids["tecnico_id"]
        assert salvo.propriedade_id == ids["prop_id"]


def test_descricao_truncada(app_aud):
    from app.services.auditoria_service import registrar_evento

    ids = app_aud.aud_ids
    with app_aud.app_context():
        log = registrar_evento("teste.trunca", descricao="a" * 1000,
                               propriedade_id=ids["prop_id"])
        assert len(log.descricao) <= 500


def test_resultado_invalido_vira_sucesso(app_aud):
    from app.services.auditoria_service import registrar_evento

    with app_aud.app_context():
        log = registrar_evento("teste.res", resultado="qualquer-coisa")
        assert log.resultado == "sucesso"


def test_falha_de_auditoria_nao_quebra_fluxo(app_aud, monkeypatch):
    from app.services import auditoria_service

    def explode():
        raise RuntimeError("falha simulada de commit")

    with app_aud.app_context():
        monkeypatch.setattr(auditoria_service.db.session, "commit", explode)
        # não deve levantar exceção
        resultado = auditoria_service.registrar_evento("teste.falha")
        assert resultado is None


def test_mascarar_email():
    from app.services.auditoria_service import mascarar_email

    assert mascarar_email("admin@connectagro.com") == "a***@connectagro.com"
    assert mascarar_email("") is None
    assert mascarar_email("sem-arroba") is None


# --- Tela / acesso ---------------------------------------------------------

def test_auditoria_exige_login(app_aud):
    resp = app_aud.test_client().get("/auditoria/")
    assert resp.status_code == 302
    assert "/auth/login" in resp.headers["Location"]


def test_admin_acessa_auditoria(app_aud):
    client = app_aud.test_client()
    _login(client, "admin@connectagro.com")
    resp = client.get("/auditoria/")
    assert resp.status_code == 200
    assert b"Auditoria" in resp.data


def test_tecnico_nao_acessa_auditoria(app_aud):
    client = app_aud.test_client()
    _login(client, "tecnico@connectagro.com")
    assert client.get("/auditoria/").status_code == 403


def test_trabalhador_nao_acessa_auditoria(app_aud):
    client = app_aud.test_client()
    _login(client, "trabalhador@connectagro.com")
    assert client.get("/auditoria/").status_code == 403


def test_link_auditoria_no_menu_admin(app_aud):
    client = app_aud.test_client()
    _login(client, "admin@connectagro.com")
    html = client.get("/").data.decode("utf-8")
    assert "/auditoria/" in html


def test_link_auditoria_ausente_para_outros_perfis(app_aud):
    client = app_aud.test_client()
    _login(client, "tecnico@connectagro.com")
    html = client.get("/").data.decode("utf-8")
    assert "/auditoria/" not in html


def test_filtro_por_acao(app_aud):
    client = app_aud.test_client()
    _login(client, "admin@connectagro.com")  # gera auth.login.sucesso
    resp = client.get("/auditoria/?acao=auth.login.sucesso")
    assert resp.status_code == 200
    assert b"auth.login.sucesso" in resp.data


# --- Autenticação ----------------------------------------------------------

def test_login_sucesso_gera_log(app_aud):
    _login(app_aud.test_client(), "admin@connectagro.com")
    assert "auth.login.sucesso" in _acoes(app_aud)


def test_login_falha_gera_log(app_aud):
    app_aud.test_client().post("/auth/login",
                               data={"email": "admin@connectagro.com", "senha": "errada"})
    assert "auth.login.falha" in _acoes(app_aud)


def test_logout_gera_log(app_aud):
    client = app_aud.test_client()
    _login(client, "admin@connectagro.com")
    client.get("/auth/logout")
    assert "auth.logout" in _acoes(app_aud)


# --- Recuperação de senha --------------------------------------------------

def test_reset_solicitado_gera_log(app_aud):
    app_aud.test_client().post("/auth/esqueci-senha",
                               data={"email": "admin@connectagro.com"})
    assert "auth.password_reset.solicitado" in _acoes(app_aud)


def test_reset_redefinido_gera_log(app_aud):
    from app.services.password_reset_service import solicitar_reset_por_email

    with app_aud.app_context():
        token = solicitar_reset_por_email("admin@connectagro.com").get("token")
    app_aud.test_client().post(f"/auth/redefinir-senha/{token}",
                               data={"nova_senha": "nova-senha-x",
                                     "confirmar_senha": "nova-senha-x"})
    assert "auth.password_reset.redefinido" in _acoes(app_aud)


def test_reset_token_invalido_gera_log(app_aud):
    app_aud.test_client().get("/auth/redefinir-senha/token-falso")
    assert "auth.password_reset.token_invalido" in _acoes(app_aud)


def test_nenhum_log_contem_token_puro(app_aud):
    from app.services.password_reset_service import solicitar_reset_por_email
    from app.models import LogAuditoria

    with app_aud.app_context():
        token = solicitar_reset_por_email("admin@connectagro.com").get("token")
    app_aud.test_client().post(f"/auth/redefinir-senha/{token}",
                               data={"nova_senha": "nova-senha-x",
                                     "confirmar_senha": "nova-senha-x"})
    with app_aud.app_context():
        for log in LogAuditoria.query.all():
            blob = " ".join(filter(None, [log.descricao, log.entidade,
                                          log.entidade_id, log.ip, log.user_agent]))
            assert token not in blob


def test_nenhum_log_contem_senha(app_aud):
    from app.services.password_reset_service import solicitar_reset_por_email
    from app.models import LogAuditoria

    with app_aud.app_context():
        token = solicitar_reset_por_email("admin@connectagro.com").get("token")
    app_aud.test_client().post(f"/auth/redefinir-senha/{token}",
                               data={"nova_senha": "minha-senha-secreta",
                                     "confirmar_senha": "minha-senha-secreta"})
    with app_aud.app_context():
        for log in LogAuditoria.query.all():
            blob = " ".join(filter(None, [log.descricao, log.entidade,
                                          log.entidade_id]))
            assert "minha-senha-secreta" not in blob
            assert "senha123" not in blob


# --- Painel de usuários ----------------------------------------------------

def test_criar_usuario_gera_log(app_aud):
    client = app_aud.test_client()
    _login(client, "admin@connectagro.com")
    client.post("/usuarios/novo", data={
        "nome": "Novo", "email": "novo@connectagro.com", "perfil": "trabalhador",
        "senha": "temp123", "confirmar_senha": "temp123", "ativo": "1",
    })
    assert "usuarios.create" in _acoes(app_aud)


def test_editar_usuario_gera_log(app_aud):
    client = app_aud.test_client()
    _login(client, "admin@connectagro.com")
    tid = app_aud.aud_ids["tecnico_id"]
    client.post(f"/usuarios/{tid}/editar", data={
        "nome": "Técnico Editado", "perfil": "tecnico", "ativo": "1",
    })
    assert "usuarios.edit" in _acoes(app_aud)


def test_inativar_usuario_gera_log(app_aud):
    client = app_aud.test_client()
    _login(client, "admin@connectagro.com")
    tid = app_aud.aud_ids["tecnico_id"]
    client.post(f"/usuarios/{tid}/inativar")
    assert "usuarios.deactivate" in _acoes(app_aud)


# --- Permissão negada ------------------------------------------------------

def test_permissao_negada_gera_log(app_aud):
    client = app_aud.test_client()
    _login(client, "tecnico@connectagro.com")
    assert client.get("/usuarios/").status_code == 403
    logs = _logs(app_aud, acao="permissao.negada")
    assert logs
    assert all(l.resultado == "negado" for l in logs)


# --- Upload ----------------------------------------------------------------

def _upload(client, nome="doc.txt"):
    return client.post("/upload/novo", data={
        "arquivo": (io.BytesIO(b"conteudo"), nome), "descricao": "x",
    }, content_type="multipart/form-data")


def test_upload_create_download_delete_geram_log(app_aud):
    from app.models import UploadArquivo

    client = app_aud.test_client()
    _login(client, "admin@connectagro.com")
    assert _upload(client).status_code == 302
    with app_aud.app_context():
        arq_id = UploadArquivo.query.one().id
    assert client.get(f"/upload/{arq_id}/download").status_code == 200
    assert client.post(f"/upload/{arq_id}/remover").status_code == 302
    acoes = _acoes(app_aud)
    assert "upload.create" in acoes
    assert "upload.download" in acoes
    assert "upload.delete" in acoes


# --- CRUDs -----------------------------------------------------------------

def test_gleba_crud_gera_logs(app_aud):
    client = app_aud.test_client()
    _login(client, "admin@connectagro.com")
    client.post("/glebas/nova", data={"nome": "Nova Gleba"})
    gid = app_aud.aud_ids["gleba_id"]
    client.post(f"/glebas/{gid}/editar", data={"nome": "Gleba Editada"})
    acoes = _acoes(app_aud)
    assert "glebas.create" in acoes
    assert "glebas.edit" in acoes


def test_financeiro_crud_gera_logs(app_aud):
    client = app_aud.test_client()
    _login(client, "admin@connectagro.com")
    client.post("/financeiro/novo", data={"tipo": "receita", "valor": "50",
                                          "data": "2026-01-01"})
    assert "financeiro.create" in _acoes(app_aud)


def test_colheita_create_gera_log(app_aud):
    client = app_aud.test_client()
    _login(client, "admin@connectagro.com")
    client.post("/colheita/nova", data={
        "cultura_gleba_id": app_aud.aud_ids["cg_id"],
        "data_colheita": "2026-02-01", "quantidade": "10", "unidade": "sc",
    })
    assert "colheita.create" in _acoes(app_aud)


def test_aplicacao_create_gera_log(app_aud):
    client = app_aud.test_client()
    _login(client, "admin@connectagro.com")
    client.post("/aplicacoes/nova", data={
        "cultura_gleba_id": app_aud.aud_ids["cg_id"],
        "produto_base_id": app_aud.aud_ids["produto_id"],
        "data_aplicacao": "2026-02-01", "dose": "2", "unidade": "L/ha",
    })
    assert "aplicacoes.create" in _acoes(app_aud)


# --- Escopo por propriedade ------------------------------------------------

def test_admin_ve_apenas_logs_da_propriedade(app_aud):
    from app.services.auditoria_service import listar_logs, registrar_evento
    from app.models import Propriedade

    ids = app_aud.aud_ids
    with app_aud.app_context():
        registrar_evento("teste.minha", propriedade_id=ids["prop_id"])
        registrar_evento("teste.outra", propriedade_id=ids["outra_prop_id"])
        prop = db.session.get(Propriedade, ids["prop_id"])
        logs = listar_logs(prop)
        acoes = {l.acao for l in logs}
        assert "teste.minha" in acoes
        assert "teste.outra" not in acoes
        assert all(l.propriedade_id == ids["prop_id"] for l in logs)


def test_tela_auditoria_nao_mostra_log_de_outra_propriedade(app_aud):
    from app.services.auditoria_service import registrar_evento

    ids = app_aud.aud_ids
    with app_aud.app_context():
        registrar_evento("marca.outra.propriedade",
                         propriedade_id=ids["outra_prop_id"])
    client = app_aud.test_client()
    _login(client, "admin@connectagro.com")
    resp = client.get("/auditoria/")
    assert b"marca.outra.propriedade" not in resp.data


# --- Sem dados de CSRF/form ------------------------------------------------

def test_logs_nao_contem_csrf(app_aud):
    from app.models import LogAuditoria

    client = app_aud.test_client()
    _login(client, "admin@connectagro.com")
    client.post("/glebas/nova", data={"nome": "G", "csrf_token": "fake-csrf-value"})
    with app_aud.app_context():
        for log in LogAuditoria.query.all():
            blob = " ".join(filter(None, [log.descricao, log.entidade,
                                          log.entidade_id]))
            assert "csrf" not in blob.lower()
            assert "fake-csrf-value" not in blob
