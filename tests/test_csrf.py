"""Testes da Fase 6.4 — proteção CSRF com Flask-WTF."""
import io
import os
import re

import pytest

from app.extensions import db
from app.utils.auth import gerar_hash_senha

TOKEN_RE = re.compile(r'name="csrf_token" value="([^"]+)"')


def extrair_csrf_token(html):
    match = TOKEN_RE.search(html)
    assert match, "csrf_token não encontrado no HTML"
    return match.group(1)


def _criar_usuario(email, perfil="admin"):
    from app.models import Propriedade, Usuario

    usuario = Usuario(nome=email, email=email, perfil=perfil, ativo=True,
                      senha_hash=gerar_hash_senha("senha123"))
    db.session.add(usuario)
    db.session.commit()
    propriedade = Propriedade(usuario_id=usuario.id, nome=f"Fazenda {perfil}")
    db.session.add(propriedade)
    db.session.commit()
    return usuario, propriedade


def _popular_dados_base():
    from app.models import Cultura, CulturaGleba, Gleba, ProdutoBase

    admin, propriedade = _criar_usuario("admin@connectagro.com", "admin")
    _criar_usuario("trabalhador@connectagro.com", "trabalhador")

    gleba = Gleba(propriedade_id=propriedade.id, nome="Gleba CSRF", area_ha=10)
    cultura = Cultura(propriedade_id=propriedade.id, nome="Soja CSRF",
                      status="em_andamento")
    produto = ProdutoBase(nome="Produto CSRF", slug="produto-csrf",
                          classe="defensivo", categoria="herbicida",
                          status_sistema="pre_cadastrado",
                          status_regulatorio="nao_validado_agrofit")
    db.session.add_all([gleba, cultura, produto])
    db.session.commit()

    cultura_gleba = CulturaGleba(cultura_id=cultura.id, gleba_id=gleba.id)
    db.session.add(cultura_gleba)
    db.session.commit()

    return {
        "admin_id": admin.id,
        "gleba_id": gleba.id,
        "cultura_gleba_id": cultura_gleba.id,
        "produto_id": produto.id,
    }


@pytest.fixture
def app_csrf(app, tmp_path):
    app.config["WTF_CSRF_ENABLED"] = True
    app.config["UPLOAD_FOLDER"] = str(tmp_path)
    app.config["MAX_CONTENT_LENGTH"] = 1024 * 1024
    with app.app_context():
        db.create_all()
        app.csrf_test_ids = _popular_dados_base()
    return app


def _login(client, email="admin@connectagro.com"):
    token = extrair_csrf_token(client.get("/auth/login").data.decode("utf-8"))
    resp = client.post("/auth/login", data={
        "email": email,
        "senha": "senha123",
        "csrf_token": token,
    })
    assert resp.status_code == 302
    return resp


def _token_da_pagina(client, url):
    resp = client.get(url)
    assert resp.status_code == 200
    return extrair_csrf_token(resp.data.decode("utf-8"))


def test_csrf_desativado_por_padrao_no_testing_config(app):
    assert app.config["WTF_CSRF_ENABLED"] is False


def test_csrfprotect_inicializado_na_aplicacao(app_csrf):
    assert app_csrf.config["WTF_CSRF_ENABLED"] is True
    assert "csrf" in app_csrf.extensions
    assert "csrf_token" in app_csrf.jinja_env.globals


def test_paginas_com_formularios_post_renderizam_csrf_token(app_csrf):
    client = app_csrf.test_client()
    assert "csrf_token" in client.get("/auth/login").data.decode("utf-8")
    _login(client)

    for url in (
        "/glebas/nova",
        "/culturas/nova",
        "/financeiro/novo",
        "/colheita/nova",
        "/aplicacoes/nova",
        "/upload/novo",
        "/ia/",
        "/glebas/",
    ):
        resp = client.get(url)
        assert resp.status_code == 200
        assert 'name="csrf_token"' in resp.data.decode("utf-8")


def test_post_sem_token_retorna_400_com_mensagem_amigavel(app_csrf):
    client = app_csrf.test_client()
    _login(client)
    resp = client.post("/financeiro/novo",
                       data={"tipo": "receita", "valor": "10", "data": "2026-01-01"})
    corpo = resp.data.decode("utf-8")
    assert resp.status_code == 400
    assert "Não foi possível validar a segurança do formulário." in corpo
    assert "csrf_token" not in corpo


def test_post_com_token_valido_funciona(app_csrf):
    from app.models import FinanceiroLancamento

    client = app_csrf.test_client()
    _login(client)
    token = _token_da_pagina(client, "/financeiro/novo")
    resp = client.post("/financeiro/novo", data={
        "tipo": "receita",
        "valor": "100",
        "data": "2026-01-01",
        "csrf_token": token,
    })
    assert resp.status_code == 302
    with app_csrf.app_context():
        assert FinanceiroLancamento.query.filter_by(valor=100).count() == 1


def test_formulario_de_remocao_com_token_valido_funciona(app_csrf):
    from app.models import Gleba

    client = app_csrf.test_client()
    _login(client)
    token = _token_da_pagina(client, "/glebas/")
    gleba_id = app_csrf.csrf_test_ids["gleba_id"]
    resp = client.post(f"/glebas/{gleba_id}/remover", data={"csrf_token": token})
    assert resp.status_code == 302
    with app_csrf.app_context():
        assert db.session.get(Gleba, gleba_id) is None


def test_upload_multipart_sem_token_retorna_400(app_csrf):
    client = app_csrf.test_client()
    _login(client)
    resp = client.post(
        "/upload/novo",
        data={"arquivo": (io.BytesIO(b"abc"), "sem-token.txt"), "descricao": "x"},
        content_type="multipart/form-data",
    )
    assert resp.status_code == 400


def test_upload_multipart_com_token_valido_funciona(app_csrf):
    from app.models import UploadArquivo

    client = app_csrf.test_client()
    _login(client)
    token = _token_da_pagina(client, "/upload/novo")
    resp = client.post(
        "/upload/novo",
        data={
            "arquivo": (io.BytesIO(b"abc"), "com-token.txt"),
            "descricao": "documento",
            "csrf_token": token,
        },
        content_type="multipart/form-data",
    )
    assert resp.status_code == 302
    with app_csrf.app_context():
        arquivo = UploadArquivo.query.filter_by(nome_original="com-token.txt").one()
        assert os.path.exists(os.path.join(app_csrf.config["UPLOAD_FOLDER"],
                                           *arquivo.caminho.split("/")))


def test_ia_post_com_token_valido_funciona(app_csrf):
    from app.models import IaInteracao

    client = app_csrf.test_client()
    _login(client)
    token = _token_da_pagina(client, "/ia/")
    resp = client.post("/ia/", data={
        "pergunta": "Faça um resumo da propriedade.",
        "csrf_token": token,
    })
    assert resp.status_code == 200
    with app_csrf.app_context():
        assert IaInteracao.query.filter_by(
            pergunta="Faça um resumo da propriedade.").count() == 1


def test_rotas_get_continuam_funcionando_sem_token(app_csrf):
    client = app_csrf.test_client()
    assert client.get("/health").status_code == 200
    _login(client)
    assert client.get("/mapa/dados").status_code == 200
    assert client.get("/relatorios/").status_code == 200


def test_permissao_sem_token_retorna_400(app_csrf):
    client = app_csrf.test_client()
    _login(client, "trabalhador@connectagro.com")
    resp = client.post("/glebas/nova", data={"nome": "Bloqueada"})
    assert resp.status_code == 400


def test_permissao_com_token_valido_retorna_403(app_csrf):
    client = app_csrf.test_client()
    _login(client, "trabalhador@connectagro.com")
    token = _token_da_pagina(client, "/ia/")
    resp = client.post("/glebas/nova", data={
        "nome": "Bloqueada",
        "csrf_token": token,
    })
    assert resp.status_code == 403


def test_sem_login_com_token_valido_continua_redirecionando_para_login(app_csrf):
    client = app_csrf.test_client()
    token = extrair_csrf_token(client.get("/auth/login").data.decode("utf-8"))
    resp = client.post("/glebas/nova", data={
        "nome": "Sem login",
        "csrf_token": token,
    })
    assert resp.status_code == 302
    assert "/auth/login" in resp.headers["Location"]
