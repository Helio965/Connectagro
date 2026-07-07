"""Painel administrativo de usuários."""
import pytest

from app.extensions import db
from app.models import LogAuditoria, Propriedade, Usuario, UsuarioPropriedade
from app.utils.auth import gerar_hash_senha, verificar_senha


def _criar_usuario(nome, email, perfil, senha="senha123", ativo=True):
    usuario = Usuario(
        nome=nome,
        email=email,
        perfil=perfil,
        ativo=ativo,
        senha_hash=gerar_hash_senha(senha),
    )
    db.session.add(usuario)
    db.session.flush()
    return usuario


@pytest.fixture
def app_usuarios(app):
    with app.app_context():
        db.create_all()
        admin = _criar_usuario("Administrador ConnectAgro", "admin@connectagro.com", "admin", "admin123")
        tecnico = _criar_usuario("Técnico ConnectAgro", "tecnico@connectagro.com", "tecnico")
        trabalhador = _criar_usuario("Trabalhador ConnectAgro", "trabalhador@connectagro.com", "trabalhador")
        propriedade = Propriedade(usuario_id=admin.id, nome="Minha propriedade")
        db.session.add(propriedade)
        db.session.flush()
        for usuario in (admin, tecnico, trabalhador):
            db.session.add(UsuarioPropriedade(
                usuario_id=usuario.id,
                propriedade_id=propriedade.id,
                ativo=True,
                criado_por_id=admin.id,
            ))
        db.session.commit()
        app.usuario_ids = {
            "admin": admin.id,
            "tecnico": tecnico.id,
            "trabalhador": trabalhador.id,
            "propriedade": propriedade.id,
        }
    return app


def _login(app, email="admin@connectagro.com", senha="admin123"):
    client = app.test_client()
    resp = client.post("/auth/login", data={"email": email, "senha": senha})
    assert resp.status_code == 302
    return client


def test_admin_cria_usuario_com_confirmacao_e_hash(app_usuarios):
    client = _login(app_usuarios)
    form = client.get("/usuarios/novo").data.decode("utf-8")
    assert "Gerente de Plantio" in form
    assert "Trabalhador" in form
    assert 'value="admin"' not in form

    resp = client.post("/usuarios/novo", data={
        "nome": "Novo Técnico",
        "email": "novo.tecnico@connectagro.com",
        "perfil": "tecnico",
        "senha": "nova123",
        "confirmar_senha": "nova123",
        "ativo": "1",
    })

    assert resp.status_code == 302
    with app_usuarios.app_context():
        usuario = Usuario.query.filter_by(email="novo.tecnico@connectagro.com").one()
        assert usuario.nome == "Novo Técnico"
        assert usuario.perfil == "tecnico"
        assert usuario.ativo is True
        assert usuario.senha_hash != "nova123"
        assert verificar_senha(usuario.senha_hash, "nova123")
        assert UsuarioPropriedade.query.filter_by(usuario_id=usuario.id).count() == 1
        assert LogAuditoria.query.filter_by(acao="usuarios.create", entidade_id=usuario.id).count() == 1

    login_novo = app_usuarios.test_client().post(
        "/auth/login",
        data={"email": "novo.tecnico@connectagro.com", "senha": "nova123"},
    )
    assert login_novo.status_code == 302


def test_admin_nao_cria_segundo_admin_nem_promove_para_admin(app_usuarios):
    client = _login(app_usuarios)

    criar_admin = client.post("/usuarios/novo", data={
        "nome": "Outro Admin",
        "email": "outro.admin@connectagro.com",
        "perfil": "admin",
        "senha": "admin123",
        "confirmar_senha": "admin123",
        "ativo": "1",
    })
    assert criar_admin.status_code == 403

    trabalhador_id = app_usuarios.usuario_ids["trabalhador"]
    promover = client.post(f"/usuarios/{trabalhador_id}/editar", data={
        "nome": "Trabalhador Promovido",
        "email": "trabalhador@connectagro.com",
        "perfil": "admin",
        "ativo": "1",
    })
    assert promover.status_code == 403
    with app_usuarios.app_context():
        assert Usuario.query.filter_by(perfil="admin", ativo=True).count() == 1


def test_criacao_bloqueia_email_duplicado_e_confirmacao_diferente(app_usuarios):
    client = _login(app_usuarios)

    duplicado = client.post("/usuarios/novo", data={
        "nome": "Duplicado",
        "email": "tecnico@connectagro.com",
        "perfil": "tecnico",
        "senha": "nova123",
        "confirmar_senha": "nova123",
        "ativo": "1",
    })
    assert duplicado.status_code == 400
    assert "Já existe um usuário com esse e-mail." in duplicado.data.decode("utf-8")

    senha_diferente = client.post("/usuarios/novo", data={
        "nome": "Senha Diferente",
        "email": "senha.diferente@connectagro.com",
        "perfil": "trabalhador",
        "senha": "nova123",
        "confirmar_senha": "outra123",
        "ativo": "1",
    })
    assert senha_diferente.status_code == 400
    assert "A senha e a confirmação não coincidem." in senha_diferente.data.decode("utf-8")


def test_admin_edita_email_perfil_status_e_senha_opcional(app_usuarios):
    client = _login(app_usuarios)
    tecnico_id = app_usuarios.usuario_ids["tecnico"]

    form = client.get(f"/usuarios/{tecnico_id}/editar").data.decode("utf-8")
    assert 'name="email"' in form
    assert "Nova senha" in form
    assert "Confirmar nova senha" in form

    resp = client.post(f"/usuarios/{tecnico_id}/editar", data={
        "nome": "Técnico Editado",
        "email": "tecnico.editado@connectagro.com",
        "perfil": "trabalhador",
        "senha": "editada123",
        "confirmar_senha": "editada123",
    })

    assert resp.status_code == 302
    with app_usuarios.app_context():
        usuario = db.session.get(Usuario, tecnico_id)
        assert usuario.nome == "Técnico Editado"
        assert usuario.email == "tecnico.editado@connectagro.com"
        assert usuario.perfil == "trabalhador"
        assert usuario.ativo is False
        assert verificar_senha(usuario.senha_hash, "editada123")
        vinculo = UsuarioPropriedade.query.filter_by(usuario_id=tecnico_id).one()
        assert vinculo.ativo is False
        assert LogAuditoria.query.filter_by(acao="usuarios.password_reset", entidade_id=tecnico_id).count() == 1
        assert LogAuditoria.query.filter_by(acao="usuarios.profile_change", entidade_id=tecnico_id).count() == 1
        assert LogAuditoria.query.filter_by(acao="usuarios.deactivate", entidade_id=tecnico_id).count() == 1

    login_antigo = app_usuarios.test_client().post(
        "/auth/login",
        data={"email": "tecnico@connectagro.com", "senha": "senha123"},
    )
    assert login_antigo.status_code == 401

    login_inativo = app_usuarios.test_client().post(
        "/auth/login",
        data={"email": "tecnico.editado@connectagro.com", "senha": "editada123"},
    )
    assert login_inativo.status_code == 403


def test_edicao_sem_nova_senha_mantem_hash_atual(app_usuarios):
    client = _login(app_usuarios)
    trabalhador_id = app_usuarios.usuario_ids["trabalhador"]
    with app_usuarios.app_context():
        hash_antes = db.session.get(Usuario, trabalhador_id).senha_hash

    resp = client.post(f"/usuarios/{trabalhador_id}/editar", data={
        "nome": "Trabalhador Sem Troca",
        "email": "trabalhador@connectagro.com",
        "perfil": "trabalhador",
        "ativo": "1",
    })

    assert resp.status_code == 302
    with app_usuarios.app_context():
        usuario = db.session.get(Usuario, trabalhador_id)
        assert usuario.senha_hash == hash_antes
        assert verificar_senha(usuario.senha_hash, "senha123")


def test_gerente_cria_e_edita_apenas_trabalhadores(app_usuarios):
    tecnico = _login(app_usuarios, "tecnico@connectagro.com", "senha123")
    trabalhador_id = app_usuarios.usuario_ids["trabalhador"]
    admin_id = app_usuarios.usuario_ids["admin"]
    tecnico_id = app_usuarios.usuario_ids["tecnico"]

    pagina = tecnico.get("/usuarios/").data.decode("utf-8")
    assert tecnico.get("/usuarios/").status_code == 200
    assert "Trabalhador ConnectAgro" in pagina
    assert "Administrador ConnectAgro" not in pagina

    form = tecnico.get("/usuarios/novo").data.decode("utf-8")
    assert tecnico.get("/usuarios/novo").status_code == 200
    assert 'value="trabalhador"' in form
    assert 'value="tecnico"' not in form
    assert 'value="admin"' not in form

    criado = tecnico.post("/usuarios/novo", data={
        "nome": "Trabalhador do Gerente",
        "email": "trabalhador.gerente@connectagro.com",
        "perfil": "trabalhador",
        "senha": "worker123",
        "confirmar_senha": "worker123",
        "ativo": "1",
    })
    assert criado.status_code == 302
    with app_usuarios.app_context():
        novo = Usuario.query.filter_by(email="trabalhador.gerente@connectagro.com").one()
        assert novo.perfil == "trabalhador"
        assert verificar_senha(novo.senha_hash, "worker123")

    criar_gerente = tecnico.post("/usuarios/novo", data={
        "nome": "Gerente Bloqueado",
        "email": "gerente.bloqueado@connectagro.com",
        "perfil": "tecnico",
        "senha": "senha123",
        "confirmar_senha": "senha123",
        "ativo": "1",
    })
    assert criar_gerente.status_code == 403

    criar_admin = tecnico.post("/usuarios/novo", data={
        "nome": "Admin Bloqueado",
        "email": "admin.bloqueado@connectagro.com",
        "perfil": "admin",
        "senha": "senha123",
        "confirmar_senha": "senha123",
        "ativo": "1",
    })
    assert criar_admin.status_code == 403

    assert tecnico.get(f"/usuarios/{admin_id}/editar").status_code == 403
    assert tecnico.get(f"/usuarios/{tecnico_id}/editar").status_code == 403

    editar_worker = tecnico.post(f"/usuarios/{trabalhador_id}/editar", data={
        "nome": "Trabalhador Editado pelo Gerente",
        "email": "trabalhador.editado.gerente@connectagro.com",
        "perfil": "trabalhador",
        "ativo": "1",
    })
    assert editar_worker.status_code == 302
    with app_usuarios.app_context():
        trabalhador = db.session.get(Usuario, trabalhador_id)
        assert trabalhador.nome == "Trabalhador Editado pelo Gerente"
        assert trabalhador.email == "trabalhador.editado.gerente@connectagro.com"
        assert trabalhador.perfil == "trabalhador"

    promover_worker = tecnico.post(f"/usuarios/{trabalhador_id}/editar", data={
        "nome": "Trabalhador Promovido",
        "email": "trabalhador.editado.gerente@connectagro.com",
        "perfil": "tecnico",
        "ativo": "1",
    })
    assert promover_worker.status_code == 403


def test_trabalhador_nao_acessa_gerenciamento_usuarios(app_usuarios):
    trabalhador = _login(app_usuarios, "trabalhador@connectagro.com", "senha123")

    assert trabalhador.get("/usuarios/").status_code == 403
    assert trabalhador.get("/usuarios/novo").status_code == 403
    assert trabalhador.post("/usuarios/novo", data={
        "nome": "Bloqueado",
        "email": "bloqueado@connectagro.com",
        "perfil": "trabalhador",
        "senha": "senha123",
        "confirmar_senha": "senha123",
        "ativo": "1",
    }).status_code == 403


def test_unico_admin_ativo_nao_pode_ser_desativado_ou_rebaixado(app_usuarios):
    client = _login(app_usuarios)
    admin_id = app_usuarios.usuario_ids["admin"]
    propriedade_id = app_usuarios.usuario_ids["propriedade"]

    rebaixar = client.post(f"/usuarios/{admin_id}/editar", data={
        "nome": "Administrador ConnectAgro",
        "email": "admin@connectagro.com",
        "perfil": "tecnico",
        "ativo": "1",
    })
    assert rebaixar.status_code == 403

    inativar_edit = client.post(f"/usuarios/{admin_id}/editar", data={
        "nome": "Administrador ConnectAgro",
        "email": "admin@connectagro.com",
        "perfil": "admin",
    })
    assert inativar_edit.status_code == 400
    assert "Você não pode inativar seu próprio usuário administrador." in inativar_edit.data.decode("utf-8")

    inativar_rota = client.post(f"/usuarios/{admin_id}/inativar")
    assert inativar_rota.status_code == 400

    with app_usuarios.app_context():
        outro_admin = _criar_usuario(
            "Admin Inativo",
            "admin.inativo@connectagro.com",
            "admin",
            ativo=False,
        )
        db.session.add(UsuarioPropriedade(
            usuario_id=outro_admin.id,
            propriedade_id=propriedade_id,
            ativo=False,
            criado_por_id=admin_id,
        ))
        db.session.commit()
        outro_admin_id = outro_admin.id

    ativar_outro_admin = client.post(f"/usuarios/{outro_admin_id}/editar", data={
        "nome": "Admin Inativo",
        "email": "admin.inativo@connectagro.com",
        "perfil": "admin",
        "ativo": "1",
    })
    assert ativar_outro_admin.status_code == 400
    assert "Não é possível ativar outro administrador." in ativar_outro_admin.data.decode("utf-8")

    with app_usuarios.app_context():
        admin = db.session.get(Usuario, admin_id)
        assert admin.perfil == "admin"
        assert admin.ativo is True
        assert Usuario.query.filter_by(perfil="admin", ativo=True).count() == 1


# --- Usuários e Acessos: listagem em blocos e rotas com perfil travado ----

def test_admin_ve_blocos_e_botoes_separados(app_usuarios):
    client = _login(app_usuarios)
    corpo = client.get("/usuarios/").data.decode("utf-8")
    assert "Usuários e Acessos" in corpo
    assert "Administrador" in corpo
    assert "Gerentes de Plantio" in corpo
    assert "Trabalhadores" in corpo
    assert "+ Novo gerente" in corpo
    assert "+ Novo trabalhador" in corpo
    assert "Admin principal" in corpo


def test_gerente_ve_apenas_bloco_e_botao_de_trabalhador(app_usuarios):
    client = _login(app_usuarios, "tecnico@connectagro.com", "senha123")
    corpo = client.get("/usuarios/").data.decode("utf-8")
    assert "Trabalhadores" in corpo
    assert "+ Novo trabalhador" in corpo
    assert "+ Novo gerente" not in corpo
    assert "Gerentes de Plantio</h2>" not in corpo
    assert "Administrador</h2>" not in corpo


def test_rota_novo_gerente_trava_perfil_no_formulario(app_usuarios):
    client = _login(app_usuarios)
    corpo = client.get("/usuarios/novo/gerente").data.decode("utf-8")
    assert "Novo Gerente de Plantio" in corpo
    assert 'type="hidden" name="perfil" value="tecnico"' in corpo
    assert "<select" not in corpo


def test_admin_cria_gerente_pela_rota_dedicada(app_usuarios):
    client = _login(app_usuarios)
    resp = client.post("/usuarios/novo/gerente", data={
        "nome": "Gerente Novo", "email": "gerente.novo@example.com",
        "senha": "senha123", "confirmar_senha": "senha123", "ativo": "1",
        "perfil": "tecnico",
    })
    assert resp.status_code == 302
    with app_usuarios.app_context():
        criado = Usuario.query.filter_by(email="gerente.novo@example.com").one()
        assert criado.perfil == "tecnico"


def test_admin_cria_trabalhador_pela_rota_dedicada(app_usuarios):
    client = _login(app_usuarios)
    resp = client.post("/usuarios/novo/trabalhador", data={
        "nome": "Trabalhador Novo", "email": "trab.novo@example.com",
        "senha": "senha123", "confirmar_senha": "senha123", "ativo": "1",
        "perfil": "trabalhador",
    })
    assert resp.status_code == 302
    with app_usuarios.app_context():
        criado = Usuario.query.filter_by(email="trab.novo@example.com").one()
        assert criado.perfil == "trabalhador"


def test_rota_travada_bloqueia_post_com_outro_perfil(app_usuarios):
    client = _login(app_usuarios)
    resp = client.post("/usuarios/novo/trabalhador", data={
        "nome": "Escalada", "email": "escalada@example.com",
        "senha": "senha123", "confirmar_senha": "senha123", "ativo": "1",
        "perfil": "tecnico",
    })
    assert resp.status_code == 403
    with app_usuarios.app_context():
        assert Usuario.query.filter_by(email="escalada@example.com").first() is None


def test_gerente_nao_acessa_rota_novo_gerente(app_usuarios):
    client = _login(app_usuarios, "tecnico@connectagro.com", "senha123")
    assert client.get("/usuarios/novo/gerente").status_code == 403
    resp = client.post("/usuarios/novo/gerente", data={
        "nome": "Gerente Ilegal", "email": "gerente.ilegal@example.com",
        "senha": "senha123", "confirmar_senha": "senha123",
        "perfil": "tecnico",
    })
    assert resp.status_code == 403
    with app_usuarios.app_context():
        assert Usuario.query.filter_by(email="gerente.ilegal@example.com").first() is None
        bloqueio = (LogAuditoria.query
                    .filter_by(acao="usuarios.create.blocked")
                    .order_by(LogAuditoria.id.desc())
                    .first())
        assert bloqueio is not None


def test_gerente_cria_trabalhador_pela_rota_dedicada(app_usuarios):
    client = _login(app_usuarios, "tecnico@connectagro.com", "senha123")
    resp = client.post("/usuarios/novo/trabalhador", data={
        "nome": "Trab do Gerente", "email": "trab.do.gerente@example.com",
        "senha": "senha123", "confirmar_senha": "senha123", "ativo": "1",
        "perfil": "trabalhador",
    })
    assert resp.status_code == 302
    with app_usuarios.app_context():
        criado = Usuario.query.filter_by(email="trab.do.gerente@example.com").one()
        assert criado.perfil == "trabalhador"


def test_trabalhador_nao_acessa_rotas_dedicadas(app_usuarios):
    client = _login(app_usuarios, "trabalhador@connectagro.com", "senha123")
    assert client.get("/usuarios/novo/gerente").status_code == 403
    assert client.get("/usuarios/novo/trabalhador").status_code == 403


def test_unico_admin_nao_mostra_botao_inativar_na_listagem(app_usuarios):
    client = _login(app_usuarios)
    corpo = client.get("/usuarios/").data.decode("utf-8")
    admin_id = app_usuarios.usuario_ids["admin"]
    assert f"/usuarios/{admin_id}/editar" in corpo
    assert f"/usuarios/{admin_id}/inativar" not in corpo


def test_listagem_nao_apaga_usuarios_existentes(app_usuarios):
    client = _login(app_usuarios)
    with app_usuarios.app_context():
        antes = Usuario.query.count()
    client.get("/usuarios/")
    client.post("/usuarios/novo/trabalhador", data={
        "nome": "Mais Um", "email": "mais.um@example.com",
        "senha": "senha123", "confirmar_senha": "senha123", "ativo": "1",
        "perfil": "trabalhador",
    })
    with app_usuarios.app_context():
        assert Usuario.query.count() == antes + 1
        for email in ("admin@connectagro.com", "tecnico@connectagro.com",
                      "trabalhador@connectagro.com"):
            assert Usuario.query.filter_by(email=email).first() is not None
