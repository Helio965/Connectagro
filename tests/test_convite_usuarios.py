"""Convite por e-mail para definição de senha de novos usuários.

Nenhum teste envia e-mail real: MAIL_ATIVO é falso em TestingConfig e o
envio é simulado com monkeypatch quando o cenário exige SMTP "ativo".
"""
import hashlib
import re

import pytest

from app.extensions import db
from app.models import LogAuditoria, Propriedade, SenhaResetToken, Usuario, UsuarioPropriedade
from app.utils.auth import gerar_hash_senha, verificar_senha


def _criar_usuario(nome, email, perfil, senha="senha123", ativo=True):
    usuario = Usuario(
        nome=nome, email=email, perfil=perfil, ativo=ativo,
        senha_hash=gerar_hash_senha(senha),
    )
    db.session.add(usuario)
    db.session.flush()
    return usuario


@pytest.fixture
def app_convite(app):
    with app.app_context():
        db.create_all()
        admin = _criar_usuario("Admin", "admin@connectagro.com", "admin", "admin123")
        tecnico = _criar_usuario("Gerente", "tecnico@connectagro.com", "tecnico")
        trabalhador = _criar_usuario("Trab", "trabalhador@connectagro.com", "trabalhador")
        prop = Propriedade(usuario_id=admin.id, nome="Propriedade Convite")
        db.session.add(prop)
        db.session.flush()
        for u in (admin, tecnico, trabalhador):
            db.session.add(UsuarioPropriedade(
                usuario_id=u.id, propriedade_id=prop.id, ativo=True,
                criado_por_id=admin.id,
            ))
        db.session.commit()
        app.ids = {"admin": admin.id, "tecnico": tecnico.id,
                   "trabalhador": trabalhador.id, "prop": prop.id}
    return app


def _login(app, email="admin@connectagro.com", senha="admin123"):
    client = app.test_client()
    assert client.post("/auth/login", data={"email": email, "senha": senha}).status_code == 302
    return client


def _extrair_link_definir(html):
    m = re.search(r'/auth/definir-senha/([A-Za-z0-9_\-]+)', html)
    return m.group(0) if m else None


def _criar_por_convite(client, rota, email, nome="Convidado"):
    """Cria usuário pela rota e devolve o link de definição exibido em dev."""
    resp = client.post(rota, data={
        "nome": nome, "email": email, "ativo": "1",
        "perfil": "tecnico" if "gerente" in rota else "trabalhador",
    }, follow_redirects=True)
    assert resp.status_code == 200
    return _extrair_link_definir(resp.data.decode("utf-8"))


def test_formularios_dedicados_nao_pedem_senha(app_convite):
    client = _login(app_convite)
    for rota in ("/usuarios/novo/gerente", "/usuarios/novo/trabalhador"):
        form = client.get(rota).data.decode("utf-8")
        assert 'name="senha"' not in form
        assert 'name="confirmar_senha"' not in form
        assert "convite" in form.lower()


def test_criacao_gera_token_hash_e_link_dev(app_convite):
    client = _login(app_convite)
    link = _criar_por_convite(client, "/usuarios/novo/gerente",
                              "novo.gerente@example.com")
    # Em dev sem SMTP, o link aparece (PASSWORD_RESET_SHOW_DEV_LINK=true).
    assert link is not None
    token_puro = link.rsplit("/", 1)[1]
    with app_convite.app_context():
        usuario = Usuario.query.filter_by(email="novo.gerente@example.com").one()
        registro = SenhaResetToken.query.filter_by(usuario_id=usuario.id, usado=False).one()
        # Só o hash SHA-256 é persistido — nunca o token puro.
        assert registro.token_hash != token_puro
        assert registro.token_hash == hashlib.sha256(token_puro.encode()).hexdigest()
        convites = LogAuditoria.query.filter_by(acao="usuarios.convite_enviado").count()
        assert convites == 1
        # Auditoria não contém o token.
        evento = LogAuditoria.query.filter_by(acao="usuarios.convite_enviado").one()
        assert token_puro not in (evento.descricao or "")


def test_link_define_senha_e_permite_login(app_convite):
    client = _login(app_convite)
    link = _criar_por_convite(client, "/usuarios/novo/trabalhador",
                              "novo.trab@example.com")
    anon = app_convite.test_client()
    # Antes de definir: login falha com qualquer senha.
    falha = anon.post("/auth/login", data={
        "email": "novo.trab@example.com", "senha": "qualquer123"})
    assert falha.status_code == 401
    # Tela de definição usa o texto de boas-vindas.
    tela = anon.get(link).data.decode("utf-8")
    assert "Definir senha" in tela
    # Define a senha própria.
    resp = anon.post(link, data={
        "nova_senha": "minhasenha1", "confirmar_senha": "minhasenha1"})
    assert resp.status_code == 302
    # Agora o login funciona.
    ok = app_convite.test_client().post("/auth/login", data={
        "email": "novo.trab@example.com", "senha": "minhasenha1"})
    assert ok.status_code == 302
    with app_convite.app_context():
        usuario = Usuario.query.filter_by(email="novo.trab@example.com").one()
        assert usuario.senha_hash != "minhasenha1"
        assert verificar_senha(usuario.senha_hash, "minhasenha1")


def test_token_de_convite_e_uso_unico(app_convite):
    client = _login(app_convite)
    link = _criar_por_convite(client, "/usuarios/novo/trabalhador",
                              "uso.unico@example.com")
    anon = app_convite.test_client()
    assert anon.post(link, data={
        "nova_senha": "senha123", "confirmar_senha": "senha123"}).status_code == 302
    # Reuso do mesmo link: inválido — e a senha definida permanece a primeira.
    de_novo = anon.post(link, data={
        "nova_senha": "outra123", "confirmar_senha": "outra123"})
    assert de_novo.status_code == 400
    with app_convite.app_context():
        usuario = Usuario.query.filter_by(email="uso.unico@example.com").one()
        assert verificar_senha(usuario.senha_hash, "senha123")
        assert not verificar_senha(usuario.senha_hash, "outra123")


def test_token_expirado_nao_funciona(app_convite):
    client = _login(app_convite)
    link = _criar_por_convite(client, "/usuarios/novo/trabalhador",
                              "expirado@example.com")
    with app_convite.app_context():
        usuario = Usuario.query.filter_by(email="expirado@example.com").one()
        registro = SenhaResetToken.query.filter_by(usuario_id=usuario.id, usado=False).one()
        registro.expira_em = "2000-01-01T00:00:00+00:00"
        db.session.commit()
    anon = app_convite.test_client()
    resp = anon.post(link, data={
        "nova_senha": "senha123", "confirmar_senha": "senha123"})
    assert resp.status_code == 400


def test_email_de_convite_e_chamado_quando_mail_ativo(app_convite, monkeypatch):
    from app.blueprints.usuarios import routes as usuarios_routes
    chamados = []
    monkeypatch.setattr(usuarios_routes, "email_ativo", lambda: True)
    monkeypatch.setattr(usuarios_routes, "email_convite_definir_senha",
                        lambda usuario, link: chamados.append((usuario.email, link)) or True)
    client = _login(app_convite)
    resp = client.post("/usuarios/novo/trabalhador", data={
        "nome": "Com SMTP", "email": "com.smtp@example.com", "ativo": "1",
        "perfil": "trabalhador",
    }, follow_redirects=True)
    corpo = resp.data.decode("utf-8")
    assert chamados and chamados[0][0] == "com.smtp@example.com"
    assert "/auth/definir-senha/" in chamados[0][1]
    # Com SMTP ativo, o link NÃO aparece na tela.
    assert _extrair_link_definir(corpo) is None
    assert "Convite enviado" in corpo


def test_sem_smtp_e_sem_flag_dev_link_nao_aparece(app_convite):
    # Simula produção: sem SMTP e sem exibição de link dev.
    app_convite.config["PASSWORD_RESET_SHOW_DEV_LINK"] = False
    client = _login(app_convite)
    resp = client.post("/usuarios/novo/trabalhador", data={
        "nome": "Sem Link", "email": "sem.link@example.com", "ativo": "1",
        "perfil": "trabalhador",
    }, follow_redirects=True)
    corpo = resp.data.decode("utf-8")
    assert _extrair_link_definir(corpo) is None
    with app_convite.app_context():
        assert Usuario.query.filter_by(email="sem.link@example.com").count() == 1


def test_reenviar_convite_invalida_token_anterior(app_convite):
    client = _login(app_convite)
    link_antigo = _criar_por_convite(client, "/usuarios/novo/trabalhador",
                                     "reenvio@example.com")
    with app_convite.app_context():
        usuario_id = Usuario.query.filter_by(email="reenvio@example.com").one().id
    resp = client.post(f"/usuarios/{usuario_id}/reenviar-convite",
                       follow_redirects=True)
    corpo = resp.data.decode("utf-8")
    link_novo = _extrair_link_definir(corpo)
    assert link_novo and link_novo != link_antigo
    anon = app_convite.test_client()
    # Link antigo foi invalidado.
    assert anon.post(link_antigo, data={
        "nova_senha": "senha123", "confirmar_senha": "senha123"}).status_code == 400
    # Link novo funciona.
    assert anon.post(link_novo, data={
        "nova_senha": "senha123", "confirmar_senha": "senha123"}).status_code == 302
    with app_convite.app_context():
        assert LogAuditoria.query.filter_by(acao="usuarios.convite_reenviado").count() == 1


def test_reenviar_convite_respeita_hierarquia(app_convite):
    admin_id = app_convite.ids["admin"]
    tecnico_id = app_convite.ids["tecnico"]
    trabalhador_id = app_convite.ids["trabalhador"]

    # Ninguém reenvia para admin.
    client = _login(app_convite)
    assert client.post(f"/usuarios/{admin_id}/reenviar-convite").status_code == 403

    # Gerente reenvia para trabalhador, mas não para outro gerente.
    gerente = _login(app_convite, "tecnico@connectagro.com", "senha123")
    assert gerente.post(f"/usuarios/{trabalhador_id}/reenviar-convite").status_code == 302
    assert gerente.post(f"/usuarios/{tecnico_id}/reenviar-convite").status_code == 403

    # Trabalhador não reenvia nada.
    trab = _login(app_convite, "trabalhador@connectagro.com", "senha123")
    assert trab.post(f"/usuarios/{trabalhador_id}/reenviar-convite").status_code == 403


def test_esqueci_senha_envia_email_quando_mail_ativo(app_convite, monkeypatch):
    from app.blueprints.auth import routes as auth_routes
    chamados = []
    monkeypatch.setattr(auth_routes, "email_ativo", lambda: True)
    monkeypatch.setattr(auth_routes, "email_recuperacao_senha",
                        lambda usuario, link: chamados.append((usuario.email, link)) or True)
    client = app_convite.test_client()
    resp = client.post("/auth/esqueci-senha",
                       data={"email": "admin@connectagro.com"})
    assert resp.status_code == 200
    assert chamados and chamados[0][0] == "admin@connectagro.com"
    assert "/auth/redefinir-senha/" in chamados[0][1]
    # Com SMTP ativo, o dev-link não é exibido.
    assert "/auth/redefinir-senha/" not in resp.data.decode("utf-8")


def test_usuarios_existentes_preservados_no_fluxo_de_convite(app_convite):
    client = _login(app_convite)
    with app_convite.app_context():
        hashes_antes = {u.email: u.senha_hash for u in Usuario.query.all()}
    _criar_por_convite(client, "/usuarios/novo/trabalhador", "novato@example.com")
    with app_convite.app_context():
        for email, h in hashes_antes.items():
            usuario = Usuario.query.filter_by(email=email).one()
            assert usuario.senha_hash == h  # senhas existentes intactas
