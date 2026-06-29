"""Testes das permissões finas por perfil (Fase 6.3)."""
import io
import os
from contextlib import contextmanager

import pytest
from flask import session

from app.extensions import db
from app.utils.auth import gerar_hash_senha

EMAILS = {
    "admin": "admin@connectagro.com",
    "tecnico": "tecnico@connectagro.com",
    "trabalhador": "trabalhador@connectagro.com",
    "desconhecido": "desconhecido@connectagro.com",
}


def _criar_usuario(email, perfil):
    from app.models import Usuario

    usuario = Usuario(nome=email, email=email, perfil=perfil, ativo=True,
                      senha_hash=gerar_hash_senha("senha123"))
    db.session.add(usuario)
    db.session.commit()
    return usuario


def _criar_produto():
    from app.models import ProdutoBase

    produto = ProdutoBase(nome="Produto Permissões", slug="produto-permissoes",
                          classe="defensivo", categoria="herbicida",
                          status_sistema="pre_cadastrado",
                          status_regulatorio="nao_validado_agrofit")
    db.session.add(produto)
    db.session.commit()
    return produto


def _criar_dados_operacionais(usuario, produto, upload_folder):
    from app.models import (AplicacaoInsumo, ColheitaRegistro, Cultura, CulturaGleba,
                            EquipeMembro, FinanceiroLancamento, Gleba, Propriedade,
                            UploadArquivo)

    prefixo = usuario.perfil
    propriedade = Propriedade(usuario_id=usuario.id, nome=f"Fazenda {prefixo}")
    db.session.add(propriedade)
    db.session.commit()

    gleba = Gleba(propriedade_id=propriedade.id, nome=f"Gleba {prefixo}", area_ha=10)
    cultura = Cultura(propriedade_id=propriedade.id, nome=f"Cultura {prefixo}", status="em_andamento")
    equipe = EquipeMembro(propriedade_id=propriedade.id, nome=f"Membro {prefixo}")
    financeiro = FinanceiroLancamento(propriedade_id=propriedade.id, tipo="receita",
                                      valor=100, data="2026-01-10")
    db.session.add_all([gleba, cultura, equipe, financeiro])
    db.session.commit()

    cultura_gleba = CulturaGleba(cultura_id=cultura.id, gleba_id=gleba.id)
    db.session.add(cultura_gleba)
    db.session.commit()

    colheita = ColheitaRegistro(cultura_gleba_id=cultura_gleba.id,
                                data_colheita="2026-02-10", quantidade=10,
                                unidade="kg")
    aplicacao = AplicacaoInsumo(cultura_gleba_id=cultura_gleba.id,
                                produto_base_id=produto.id,
                                data_aplicacao="2026-02-12", dose=2,
                                unidade="L/ha")
    db.session.add_all([colheita, aplicacao])
    db.session.commit()

    pasta_relativa = f"propriedade_{propriedade.id}"
    pasta_absoluta = os.path.join(upload_folder, pasta_relativa)
    os.makedirs(pasta_absoluta, exist_ok=True)
    nome_arquivo = f"{prefixo}.txt"
    with open(os.path.join(pasta_absoluta, nome_arquivo), "wb") as arquivo_fisico:
        arquivo_fisico.write(b"abc")
    upload = UploadArquivo(propriedade_id=propriedade.id,
                           nome_original=nome_arquivo,
                           caminho=f"{pasta_relativa}/{nome_arquivo}",
                           tipo_mime="text/plain", tamanho=3)
    db.session.add(upload)
    db.session.commit()

    return {
        "usuario_id": usuario.id,
        "gleba_id": gleba.id,
        "cultura_id": cultura.id,
        "cultura_gleba_id": cultura_gleba.id,
        "equipe_id": equipe.id,
        "financeiro_id": financeiro.id,
        "colheita_id": colheita.id,
        "aplicacao_id": aplicacao.id,
        "upload_id": upload.id,
        "produto_id": produto.id,
    }


@pytest.fixture
def app_db(app, tmp_path):
    app.config["UPLOAD_FOLDER"] = str(tmp_path)
    app.config["MAX_CONTENT_LENGTH"] = 1024 * 1024
    with app.app_context():
        db.create_all()
        produto = _criar_produto()
        ids = {}
        for perfil, email in EMAILS.items():
            usuario = _criar_usuario(email, perfil)
            ids[perfil] = _criar_dados_operacionais(usuario, produto, str(tmp_path))
    app.permission_test_ids = ids
    return app


def _login(app_db, perfil):
    client = app_db.test_client()
    client.post("/auth/login", data={"email": EMAILS[perfil], "senha": "senha123"})
    return client


@contextmanager
def _session_perfil(app_db, perfil):
    ids = app_db.permission_test_ids[perfil]
    with app_db.test_request_context("/"):
        session["user_id"] = ids["usuario_id"]
        session["user_email"] = EMAILS[perfil]
        session["user_nome"] = EMAILS[perfil]
        session["user_perfil"] = perfil
        yield


def _post_upload(client, nome="novo.txt", conteudo=b"abc"):
    return client.post(
        "/upload/novo",
        data={"arquivo": (io.BytesIO(conteudo), nome), "descricao": "teste"},
        content_type="multipart/form-data",
    )


# --- Utilitário ------------------------------------------------------------


def test_matriz_de_permissoes_por_perfil(app_db):
    from app.utils.permissions import can, has_permission

    esperadas = {
        "admin": ("glebas.delete", "financeiro.create", "equipe.delete", "upload.delete",
                  "usuarios.view", "usuarios.create", "usuarios.edit",
                  "usuarios.deactivate"),
        "tecnico": ("dashboard.view", "glebas.create", "culturas.edit", "colheita.edit",
                    "aplicacoes.edit", "upload.download", "financeiro.view", "equipe.view"),
        "trabalhador": ("dashboard.view", "glebas.view", "culturas.view", "colheita.create",
                        "aplicacoes.create", "upload.create", "upload.download"),
    }
    negadas = {
        "tecnico": ("glebas.delete", "culturas.delete", "colheita.delete",
                    "aplicacoes.delete", "upload.delete", "financeiro.create",
                    "equipe.create", "usuarios.view", "usuarios.create"),
        "trabalhador": ("glebas.create", "culturas.create", "colheita.edit",
                        "aplicacoes.edit", "financeiro.view", "equipe.view",
                        "upload.delete", "usuarios.view", "usuarios.create"),
        "desconhecido": ("dashboard.view", "glebas.delete"),
    }

    for perfil, permissoes in esperadas.items():
        with _session_perfil(app_db, perfil):
            for permissao in permissoes:
                assert can(permissao)

    for perfil, permissoes in negadas.items():
        with _session_perfil(app_db, perfil):
            for permissao in permissoes:
                assert not has_permission(permissao)


# --- Acesso geral ----------------------------------------------------------


def test_sem_login_redireciona_para_login(app_db):
    resp = app_db.test_client().get("/glebas/")
    assert resp.status_code == 302
    assert "/auth/login" in resp.headers["Location"]


@pytest.mark.parametrize("rota", ["/auth/login", "/health"])
def test_rotas_publicas_continuam_publicas(app_db, rota):
    assert app_db.test_client().get(rota).status_code == 200


@pytest.mark.parametrize("rota", [
    "/", "/mapa/", "/defensivos/", "/fertilizantes/", "/relatorios/", "/ia/",
])
def test_tecnico_acessa_modulos_de_consulta_e_apoio(app_db, rota):
    assert _login(app_db, "tecnico").get(rota).status_code == 200


@pytest.mark.parametrize("rota", [
    "/glebas/", "/culturas/", "/colheita/", "/aplicacoes/", "/upload/",
])
def test_trabalhador_acessa_modulos_operacionais_em_leitura(app_db, rota):
    assert _login(app_db, "trabalhador").get(rota).status_code == 200


# --- Admin -----------------------------------------------------------------


def test_admin_acessa_equipe_financeiro_e_remove_registros(app_db):
    from app.models import AplicacaoInsumo, ColheitaRegistro, UploadArquivo

    ids = app_db.permission_test_ids["admin"]
    client = _login(app_db, "admin")
    assert client.get("/equipe/").status_code == 200
    assert client.get("/financeiro/").status_code == 200
    assert client.get("/usuarios/").status_code == 200
    assert client.post(f"/upload/{ids['upload_id']}/remover").status_code == 302
    assert client.post(f"/colheita/{ids['colheita_id']}/remover").status_code == 302
    assert client.post(f"/aplicacoes/{ids['aplicacao_id']}/remover").status_code == 302
    with app_db.app_context():
        assert db.session.get(UploadArquivo, ids["upload_id"]) is None
        assert db.session.get(ColheitaRegistro, ids["colheita_id"]) is None
        assert db.session.get(AplicacaoInsumo, ids["aplicacao_id"]) is None


def test_admin_cria_edita_remove_gleba(app_db):
    from app.models import Gleba

    client = _login(app_db, "admin")
    assert client.post("/glebas/nova", data={"nome": "Gleba Admin Nova"}).status_code == 302
    with app_db.app_context():
        gleba_id = Gleba.query.filter_by(nome="Gleba Admin Nova").one().id
    assert client.post(f"/glebas/{gleba_id}/editar", data={"nome": "Gleba Admin Editada"}).status_code == 302
    assert client.post(f"/glebas/{gleba_id}/remover").status_code == 302
    with app_db.app_context():
        assert db.session.get(Gleba, gleba_id) is None


# --- Técnico ---------------------------------------------------------------


def test_tecnico_cria_edita_gleba_e_cultura_mas_nao_remove(app_db):
    from app.models import Cultura, Gleba

    client = _login(app_db, "tecnico")
    assert client.post("/glebas/nova", data={"nome": "Gleba Tecnico"}).status_code == 302
    assert client.post("/culturas/nova", data={"nome": "Cultura Tecnico"}).status_code == 302
    with app_db.app_context():
        gleba_id = Gleba.query.filter_by(nome="Gleba Tecnico").one().id
        cultura_id = Cultura.query.filter_by(nome="Cultura Tecnico").one().id
    assert client.post(f"/glebas/{gleba_id}/editar", data={"nome": "Gleba Tecnico Editada"}).status_code == 302
    assert client.post(f"/culturas/{cultura_id}/editar",
                       data={"nome": "Cultura Tecnico Editada", "status": "em_andamento"}).status_code == 302
    assert client.post(f"/glebas/{gleba_id}/remover").status_code == 403
    assert client.post(f"/culturas/{cultura_id}/remover").status_code == 403


def test_tecnico_cria_edita_colheita_aplicacao_e_nao_remove(app_db):
    from app.models import AplicacaoInsumo, ColheitaRegistro

    ids = app_db.permission_test_ids["tecnico"]
    client = _login(app_db, "tecnico")
    assert client.post("/colheita/nova", data={
        "cultura_gleba_id": str(ids["cultura_gleba_id"]),
        "data_colheita": "2026-03-01",
        "quantidade": "12",
    }).status_code == 302
    assert client.post("/aplicacoes/nova", data={
        "cultura_gleba_id": str(ids["cultura_gleba_id"]),
        "produto_base_id": str(ids["produto_id"]),
        "data_aplicacao": "2026-03-01",
    }).status_code == 302
    with app_db.app_context():
        colheita_id = ColheitaRegistro.query.order_by(ColheitaRegistro.id.desc()).first().id
        aplicacao_id = AplicacaoInsumo.query.order_by(AplicacaoInsumo.id.desc()).first().id
    assert client.post(f"/colheita/{colheita_id}/editar", data={
        "cultura_gleba_id": str(ids["cultura_gleba_id"]),
        "data_colheita": "2026-03-02",
    }).status_code == 302
    assert client.post(f"/aplicacoes/{aplicacao_id}/editar", data={
        "cultura_gleba_id": str(ids["cultura_gleba_id"]),
        "produto_base_id": str(ids["produto_id"]),
        "data_aplicacao": "2026-03-02",
    }).status_code == 302
    assert client.post(f"/colheita/{colheita_id}/remover").status_code == 403
    assert client.post(f"/aplicacoes/{aplicacao_id}/remover").status_code == 403


def test_tecnico_visualiza_mas_nao_gerencia_financeiro_e_equipe(app_db):
    ids = app_db.permission_test_ids["tecnico"]
    client = _login(app_db, "tecnico")
    assert client.get("/financeiro/").status_code == 200
    assert client.get("/equipe/").status_code == 200
    assert client.get("/financeiro/novo").status_code == 403
    assert client.post("/financeiro/novo", data={"tipo": "receita", "valor": "10", "data": "2026-01-01"}).status_code == 403
    assert client.get(f"/financeiro/{ids['financeiro_id']}/editar").status_code == 403
    assert client.post(f"/financeiro/{ids['financeiro_id']}/remover").status_code == 403
    assert client.get("/equipe/novo").status_code == 403
    assert client.post("/equipe/novo", data={"nome": "Novo"}).status_code == 403
    assert client.get(f"/equipe/{ids['equipe_id']}/editar").status_code == 403
    assert client.post(f"/equipe/{ids['equipe_id']}/remover").status_code == 403


def test_tecnico_envia_baixa_upload_mas_nao_remove(app_db):
    ids = app_db.permission_test_ids["tecnico"]
    client = _login(app_db, "tecnico")
    assert _post_upload(client, nome="tecnico-novo.txt").status_code == 302
    assert client.get(f"/upload/{ids['upload_id']}/download").status_code == 200
    assert client.post(f"/upload/{ids['upload_id']}/remover").status_code == 403


# --- Trabalhador -----------------------------------------------------------


def test_trabalhador_nao_cria_edita_remove_gleba_ou_cultura(app_db):
    ids = app_db.permission_test_ids["trabalhador"]
    client = _login(app_db, "trabalhador")
    assert client.get("/glebas/nova").status_code == 403
    assert client.post("/glebas/nova", data={"nome": "Bloqueada"}).status_code == 403
    assert client.get(f"/glebas/{ids['gleba_id']}/editar").status_code == 403
    assert client.post(f"/glebas/{ids['gleba_id']}/remover").status_code == 403
    assert client.get("/culturas/nova").status_code == 403
    assert client.post("/culturas/nova", data={"nome": "Bloqueada"}).status_code == 403
    assert client.get(f"/culturas/{ids['cultura_id']}/editar").status_code == 403
    assert client.post(f"/culturas/{ids['cultura_id']}/remover").status_code == 403


def test_trabalhador_cria_colheita_aplicacao_upload_mas_nao_edita_remove(app_db):
    ids = app_db.permission_test_ids["trabalhador"]
    client = _login(app_db, "trabalhador")
    assert client.post("/colheita/nova", data={
        "cultura_gleba_id": str(ids["cultura_gleba_id"]),
        "data_colheita": "2026-03-01",
    }).status_code == 302
    assert client.post("/aplicacoes/nova", data={
        "cultura_gleba_id": str(ids["cultura_gleba_id"]),
        "produto_base_id": str(ids["produto_id"]),
        "data_aplicacao": "2026-03-01",
    }).status_code == 302
    assert _post_upload(client, nome="trabalhador-novo.txt").status_code == 302
    assert client.get(f"/upload/{ids['upload_id']}/download").status_code == 200
    assert client.get(f"/colheita/{ids['colheita_id']}/editar").status_code == 403
    assert client.post(f"/colheita/{ids['colheita_id']}/remover").status_code == 403
    assert client.get(f"/aplicacoes/{ids['aplicacao_id']}/editar").status_code == 403
    assert client.post(f"/aplicacoes/{ids['aplicacao_id']}/remover").status_code == 403
    assert client.post(f"/upload/{ids['upload_id']}/remover").status_code == 403


def test_trabalhador_nao_acessa_equipe_financeiro(app_db):
    ids = app_db.permission_test_ids["trabalhador"]
    client = _login(app_db, "trabalhador")
    assert client.get("/equipe/").status_code == 403
    assert client.get("/financeiro/").status_code == 403
    assert client.post("/financeiro/novo", data={"tipo": "receita", "valor": "10", "data": "2026-01-01"}).status_code == 403
    assert client.post(f"/financeiro/{ids['financeiro_id']}/remover").status_code == 403
    assert client.post("/equipe/novo", data={"nome": "Bloqueado"}).status_code == 403
    assert client.post(f"/equipe/{ids['equipe_id']}/remover").status_code == 403


# --- Templates -------------------------------------------------------------


def test_templates_escondem_menu_e_acoes_sem_permissao(app_db):
    trabalhador_home = _login(app_db, "trabalhador").get("/").data.decode("utf-8")
    assert "Equipe" not in trabalhador_home
    assert "Financeiro" not in trabalhador_home
    assert "Usuários" not in trabalhador_home

    tecnico = _login(app_db, "tecnico")
    assert "Usuários" not in tecnico.get("/").data.decode("utf-8")
    financeiro = tecnico.get("/financeiro/").data.decode("utf-8")
    assert "Financeiro" in financeiro
    assert "+ Novo lançamento" not in financeiro
    for rota in ("/glebas/", "/culturas/", "/colheita/", "/aplicacoes/", "/upload/"):
        assert "Remover" not in tecnico.get(rota).data.decode("utf-8")

    admin = _login(app_db, "admin")
    assert "Usuários" in admin.get("/").data.decode("utf-8")
    assert "+ Nova gleba" in admin.get("/glebas/").data.decode("utf-8")
    assert "+ Novo lançamento" in admin.get("/financeiro/").data.decode("utf-8")
    assert "Remover" in admin.get("/upload/").data.decode("utf-8")


# --- Restrições gerais -----------------------------------------------------


def test_permissoes_nao_alteram_escopo_por_propriedade(app_db):
    admin_ids = app_db.permission_test_ids["admin"]
    client = _login(app_db, "tecnico")
    assert client.get(f"/glebas/{admin_ids['gleba_id']}/editar").status_code == 404
    assert client.get(f"/upload/{admin_ids['upload_id']}/download").status_code == 404


def test_acao_sem_permissao_nao_cria_registro(app_db):
    from app.models import FinanceiroLancamento

    client = _login(app_db, "trabalhador")
    with app_db.app_context():
        antes = FinanceiroLancamento.query.count()
    resp = client.post("/financeiro/novo", data={"tipo": "receita", "valor": "99", "data": "2026-01-01"})
    assert resp.status_code == 403
    with app_db.app_context():
        assert FinanceiroLancamento.query.count() == antes
