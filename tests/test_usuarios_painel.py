"""Testes da Fase 7.1 — painel de usuários da propriedade."""
import re

import pytest

from app.extensions import db
from app.utils.auth import gerar_hash_senha

TOKEN_RE = re.compile(r'name="csrf_token" value="([^"]+)"')


def extrair_csrf_token(html):
    match = TOKEN_RE.search(html)
    assert match, "csrf_token não encontrado no HTML"
    return match.group(1)


def _criar_usuario(nome, email, perfil="admin", senha="senha123", ativo=True):
    from app.models import Usuario

    usuario = Usuario(
        nome=nome,
        email=email,
        perfil=perfil,
        ativo=ativo,
        senha_hash=gerar_hash_senha(senha),
    )
    db.session.add(usuario)
    db.session.commit()
    return usuario


def _vincular(usuario, propriedade, criado_por_id=None, ativo=True):
    from app.models import UsuarioPropriedade

    vinculo = UsuarioPropriedade(
        usuario_id=usuario.id,
        propriedade_id=propriedade.id,
        ativo=ativo,
        criado_por_id=criado_por_id,
    )
    db.session.add(vinculo)
    db.session.commit()
    return vinculo


def _popular_usuarios():
    from app.models import Propriedade

    admin = _criar_usuario("Admin", "admin@connectagro.com", "admin")
    tecnico = _criar_usuario("Técnico", "tecnico@connectagro.com", "tecnico")
    trabalhador = _criar_usuario(
        "Trabalhador", "trabalhador@connectagro.com", "trabalhador")
    propriedade = Propriedade(usuario_id=admin.id, nome="Fazenda Painel")
    db.session.add(propriedade)
    db.session.commit()

    for usuario in (admin, tecnico, trabalhador):
        _vincular(usuario, propriedade, criado_por_id=admin.id)

    outra_admin = _criar_usuario("Outra Admin", "outra@connectagro.com", "admin")
    outro_usuario = _criar_usuario("Outro Usuário", "outro@connectagro.com", "trabalhador")
    outra_propriedade = Propriedade(usuario_id=outra_admin.id, nome="Fazenda Externa")
    db.session.add(outra_propriedade)
    db.session.commit()
    _vincular(outra_admin, outra_propriedade, criado_por_id=outra_admin.id)
    _vincular(outro_usuario, outra_propriedade, criado_por_id=outra_admin.id)

    return {
        "admin_id": admin.id,
        "tecnico_id": tecnico.id,
        "trabalhador_id": trabalhador.id,
        "propriedade_id": propriedade.id,
        "outro_usuario_id": outro_usuario.id,
    }


@pytest.fixture
def painel_app(app):
    with app.app_context():
        db.create_all()
        app.painel_ids = _popular_usuarios()
    return app


def _login(client, email="admin@connectagro.com", senha="senha123"):
    resp = client.post("/auth/login", data={"email": email, "senha": senha})
    assert resp.status_code == 302
    return resp


def _login_csrf(client, email="admin@connectagro.com", senha="senha123"):
    token = extrair_csrf_token(client.get("/auth/login").data.decode("utf-8"))
    resp = client.post("/auth/login", data={
        "email": email,
        "senha": senha,
        "csrf_token": token,
    })
    assert resp.status_code == 302
    return resp


def _token_da_pagina(client, url):
    resp = client.get(url)
    assert resp.status_code == 200
    return extrair_csrf_token(resp.data.decode("utf-8"))


def test_painel_usuarios_exige_login(painel_app):
    resp = painel_app.test_client().get("/usuarios/")
    assert resp.status_code == 302
    assert "/auth/login" in resp.headers["Location"]


@pytest.mark.parametrize("perfil,email,esperado", [
    ("admin", "admin@connectagro.com", 200),
    ("tecnico", "tecnico@connectagro.com", 403),
    ("trabalhador", "trabalhador@connectagro.com", 403),
])
def test_apenas_admin_acessa_painel_usuarios(painel_app, perfil, email, esperado):
    client = painel_app.test_client()
    _login(client, email)
    resp = client.get("/usuarios/")
    assert resp.status_code == esperado
    if perfil == "admin":
        corpo = resp.data.decode("utf-8")
        assert "Painel de usuários interno" in corpo
        assert "+ Novo usuário" in corpo


def test_admin_cria_usuario_vinculado_a_propriedade_atual(painel_app):
    from app.models import Usuario, UsuarioPropriedade

    client = painel_app.test_client()
    _login(client)
    resp = client.post("/usuarios/novo", data={
        "nome": "Operador Novo",
        "email": "operador@connectagro.com",
        "perfil": "trabalhador",
        "senha": "operador123",
        "confirmar_senha": "operador123",
        "ativo": "1",
    })
    assert resp.status_code == 302

    with painel_app.app_context():
        usuario = Usuario.query.filter_by(email="operador@connectagro.com").one()
        assert usuario.senha_hash != "operador123"
        vinculo = UsuarioPropriedade.query.filter_by(usuario_id=usuario.id).one()
        assert vinculo.propriedade_id == painel_app.painel_ids["propriedade_id"]
        assert vinculo.ativo is True

    login_resp = painel_app.test_client().post("/auth/login", data={
        "email": "operador@connectagro.com",
        "senha": "operador123",
    })
    assert login_resp.status_code == 302


@pytest.mark.parametrize("dados,mensagem", [
    ({
        "nome": "Duplicado",
        "email": "tecnico@connectagro.com",
        "perfil": "tecnico",
        "senha": "senha123",
        "confirmar_senha": "senha123",
        "ativo": "1",
    }, "Já existe um usuário com este e-mail."),
    ({
        "nome": "Perfil Inválido",
        "email": "perfil-invalido@connectagro.com",
        "perfil": "produtor",
        "senha": "senha123",
        "confirmar_senha": "senha123",
        "ativo": "1",
    }, "Perfil inválido."),
    ({
        "nome": "Senha Curta",
        "email": "senha-curta@connectagro.com",
        "perfil": "trabalhador",
        "senha": "123",
        "confirmar_senha": "123",
        "ativo": "1",
    }, "A senha temporária deve ter pelo menos 6 caracteres."),
])
def test_admin_criacao_valida_dados_obrigatorios(painel_app, dados, mensagem):
    client = painel_app.test_client()
    _login(client)
    resp = client.post("/usuarios/novo", data=dados)
    assert resp.status_code == 400
    assert mensagem in resp.data.decode("utf-8")


def test_admin_edita_usuario_sem_alterar_email(painel_app):
    from app.models import Usuario, UsuarioPropriedade

    tecnico_id = painel_app.painel_ids["tecnico_id"]
    client = painel_app.test_client()
    _login(client)
    resp = client.post(f"/usuarios/{tecnico_id}/editar", data={
        "nome": "Técnico Atualizado",
        "email": "tentativa@connectagro.com",
        "perfil": "trabalhador",
        "ativo": "1",
    })
    assert resp.status_code == 302

    with painel_app.app_context():
        usuario = db.session.get(Usuario, tecnico_id)
        vinculo = UsuarioPropriedade.query.filter_by(usuario_id=tecnico_id).one()
        assert usuario.nome == "Técnico Atualizado"
        assert usuario.email == "tecnico@connectagro.com"
        assert usuario.perfil == "trabalhador"
        assert usuario.ativo is True
        assert vinculo.ativo is True


def test_admin_inativa_usuario_sem_excluir(painel_app):
    from app.models import Usuario, UsuarioPropriedade

    trabalhador_id = painel_app.painel_ids["trabalhador_id"]
    client = painel_app.test_client()
    _login(client)
    resp = client.post(f"/usuarios/{trabalhador_id}/inativar")
    assert resp.status_code == 302

    with painel_app.app_context():
        usuario = db.session.get(Usuario, trabalhador_id)
        vinculo = UsuarioPropriedade.query.filter_by(usuario_id=trabalhador_id).one()
        assert usuario is not None
        assert usuario.ativo is False
        assert vinculo.ativo is False

    login_resp = painel_app.test_client().post("/auth/login", data={
        "email": "trabalhador@connectagro.com",
        "senha": "senha123",
    })
    assert login_resp.status_code == 403


def test_admin_nao_inativa_ultimo_admin_da_propriedade(painel_app):
    admin_id = painel_app.painel_ids["admin_id"]
    client = painel_app.test_client()
    _login(client)
    resp = client.post(f"/usuarios/{admin_id}/inativar")
    assert resp.status_code == 400
    assert "A propriedade precisa manter pelo menos um admin ativo." in resp.data.decode("utf-8")


def test_admin_nao_edita_usuario_de_outra_propriedade(painel_app):
    outro_id = painel_app.painel_ids["outro_usuario_id"]
    client = painel_app.test_client()
    _login(client)
    assert client.get(f"/usuarios/{outro_id}/editar").status_code == 404
    assert client.post(f"/usuarios/{outro_id}/inativar").status_code == 404


def test_painel_nao_expoe_remocao_fisica_de_usuario(painel_app):
    trabalhador_id = painel_app.painel_ids["trabalhador_id"]
    client = painel_app.test_client()
    _login(client)
    assert client.post(f"/usuarios/{trabalhador_id}/remover").status_code == 404


def test_propriedade_atual_cria_vinculo_para_base_legada(app):
    from app.models import Propriedade, UsuarioPropriedade

    with app.app_context():
        db.create_all()
        usuario = _criar_usuario("Legado", "legado@connectagro.com", "admin")
        propriedade = Propriedade(usuario_id=usuario.id, nome="Fazenda Legada")
        db.session.add(propriedade)
        db.session.commit()
        usuario_id = usuario.id
        propriedade_id = propriedade.id
        assert UsuarioPropriedade.query.count() == 0

    client = app.test_client()
    _login(client, "legado@connectagro.com")
    assert client.get("/usuarios/").status_code == 200

    with app.app_context():
        vinculo = UsuarioPropriedade.query.filter_by(
            usuario_id=usuario_id,
            propriedade_id=propriedade_id,
        ).one()
        assert vinculo.ativo is True


def test_seed_users_cria_propriedade_demo_e_vinculos_idempotentes(app):
    from app.models import Propriedade, Usuario, UsuarioPropriedade

    with app.app_context():
        db.create_all()
    runner = app.test_cli_runner()

    r1 = runner.invoke(args=["seed-users"])
    assert r1.exit_code == 0
    with app.app_context():
        assert Usuario.query.count() == 3
        assert Propriedade.query.count() == 1
        assert Propriedade.query.one().nome == "Propriedade Demo ConnectAgro"
        assert UsuarioPropriedade.query.count() == 3
        propriedade_id = Propriedade.query.one().id
        assert {v.propriedade_id for v in UsuarioPropriedade.query.all()} == {propriedade_id}

    r2 = runner.invoke(args=["seed-users"])
    assert r2.exit_code == 0
    with app.app_context():
        assert Usuario.query.count() == 3
        assert Propriedade.query.count() == 1
        assert UsuarioPropriedade.query.count() == 3


@pytest.fixture
def painel_app_csrf(app):
    app.config["WTF_CSRF_ENABLED"] = True
    with app.app_context():
        db.create_all()
        app.painel_ids = _popular_usuarios()
    return app


def test_csrf_usuarios_sem_token_retorna_400(painel_app_csrf):
    client = painel_app_csrf.test_client()
    _login_csrf(client)
    resp = client.post("/usuarios/novo", data={
        "nome": "Sem Token",
        "email": "sem-token@connectagro.com",
        "perfil": "trabalhador",
        "senha": "senha123",
        "ativo": "1",
    })
    assert resp.status_code == 400


def test_csrf_usuarios_com_token_valido_respeita_permissao_403(painel_app_csrf):
    client = painel_app_csrf.test_client()
    _login_csrf(client, "tecnico@connectagro.com")
    token = _token_da_pagina(client, "/ia/")
    resp = client.post("/usuarios/novo", data={
        "nome": "Bloqueado",
        "email": "bloqueado@connectagro.com",
        "perfil": "trabalhador",
        "senha": "senha123",
        "csrf_token": token,
    })
    assert resp.status_code == 403


def test_csrf_usuarios_com_token_valido_permite_admin(painel_app_csrf):
    from app.models import Usuario

    client = painel_app_csrf.test_client()
    _login_csrf(client)
    token = _token_da_pagina(client, "/usuarios/novo")
    resp = client.post("/usuarios/novo", data={
        "nome": "Com Token",
        "email": "com-token@connectagro.com",
        "perfil": "trabalhador",
        "senha": "senha123",
        "confirmar_senha": "senha123",
        "ativo": "1",
        "csrf_token": token,
    })
    assert resp.status_code == 302
    with painel_app_csrf.app_context():
        assert Usuario.query.filter_by(email="com-token@connectagro.com").count() == 1
