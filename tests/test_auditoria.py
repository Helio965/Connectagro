"""Auditoria agrupada por usuário/perfil e tipo de ação."""
from types import SimpleNamespace

from app.extensions import db
from app.models import LogAuditoria, Propriedade, Usuario, UsuarioPropriedade
from app.utils.auth import gerar_hash_senha


def _usuario(nome, email, perfil):
    usuario = Usuario(
        nome=nome,
        email=email,
        perfil=perfil,
        ativo=True,
        senha_hash=gerar_hash_senha("senha123"),
    )
    db.session.add(usuario)
    db.session.flush()
    return usuario


def _log(usuario_id, propriedade_id, acao, entidade, descricao, criado_em):
    return LogAuditoria(
        usuario_id=usuario_id,
        propriedade_id=propriedade_id,
        acao=acao,
        entidade=entidade,
        resultado="sucesso",
        descricao=descricao,
        ip="127.0.0.1",
        criado_em=criado_em,
    )


def test_classificar_acao_auditoria_cobre_categorias_principais():
    from app.blueprints.auditoria.routes import classificar_acao_auditoria

    casos = [
        ("auth.login.sucesso", "usuario", "Login realizado", "Acessos"),
        ("culturas.create", "cultura", "Cultura criada", "Cadastros"),
        ("glebas.create", "propriedade", "Propriedade criada", "Mapa / Propriedades"),
        ("relatorios.view", "relatorios", "Acesso à central", "Relatórios"),
        ("exportacao.gerada", "relatorio", "Exportação PDF", "Exportações"),
        ("financeiro.create", "financeiro_lancamento", "Lançamento criado", "Financeiro"),
        ("aplicacoes.create", "aplicacao_insumo", "Aplicação registrada", "Aplicações"),
        ("colheita.create", "colheita_registro", "Colheita registrada", "Colheitas"),
        ("upload.create", "upload_arquivo", "Arquivo enviado", "Uploads"),
        ("usuarios.edit", "usuario", "Usuário atualizado", "Edições"),
        ("usuarios.deactivate", "usuario", "Usuário inativado", "Exclusões"),
    ]

    for acao, entidade, descricao, categoria in casos:
        log = SimpleNamespace(acao=acao, entidade=entidade, descricao=descricao)
        assert classificar_acao_auditoria(log) == categoria


def test_tela_auditoria_agrupa_por_usuario_e_categoria(app):
    with app.app_context():
        db.create_all()
        admin = _usuario("Administrador ConnectAgro", "admin@connectagro.com", "admin")
        tecnico = _usuario("Técnico ConnectAgro", "tecnico@connectagro.com", "tecnico")
        trabalhador = _usuario(
            "Trabalhador ConnectAgro", "trabalhador@connectagro.com", "trabalhador"
        )
        propriedade = Propriedade(usuario_id=admin.id, nome="Fazenda Auditoria")
        db.session.add(propriedade)
        db.session.flush()
        for usuario in (admin, tecnico, trabalhador):
            db.session.add(
                UsuarioPropriedade(
                    usuario_id=usuario.id,
                    propriedade_id=propriedade.id,
                    criado_por_id=admin.id,
                    ativo=True,
                )
            )
        db.session.add_all(
            [
                _log(admin.id, propriedade.id, "auth.login.sucesso", "usuario",
                     "Login de a***@connectagro.com", "2026-07-02T16:30:00"),
                _log(admin.id, propriedade.id, "culturas.create", "cultura",
                     "Cultura criada", "2026-07-02T16:28:00"),
                _log(tecnico.id, propriedade.id, "aplicacoes.create", "aplicacao_insumo",
                     "Aplicação registrada", "2026-07-02T16:20:00"),
                _log(trabalhador.id, propriedade.id, "colheita.create", "colheita_registro",
                     "Registro de colheita criado", "2026-07-02T16:10:00"),
                _log(None, propriedade.id, "exportacao.gerada", "relatorio",
                     "Exportação PDF do relatório financeiro", "2026-07-02T16:00:00"),
            ]
        )
        db.session.commit()

    client = app.test_client()
    client.post("/auth/login", data={"email": "admin@connectagro.com", "senha": "senha123"})
    resp = client.get("/auditoria/")

    assert resp.status_code == 200
    html = resp.data.decode("utf-8")
    assert "Administrador ConnectAgro" in html
    assert "Técnico ConnectAgro" in html
    assert "Trabalhador ConnectAgro" in html
    assert "Sistema / Registro antigo" in html
    assert "Acessos" in html
    assert "Cadastros" in html
    assert "Aplicações" in html
    assert "Colheitas" in html
    assert "Exportações" in html
    assert "senha123" not in html
    assert "token_hash" not in html
