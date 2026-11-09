"""Solicitações e revisão global com autoridade explícita e transações reais."""
import json
import re

import pytest
from sqlalchemy import event

from app.extensions import db
from app.models import (AplicacaoInsumo, AtividadeItem, FinanceiroLancamento,
                        LogAuditoria, ProdutoBase, ProdutoImagem, ProdutoPreco,
                        ProdutoTecnico, Usuario)
from tests.test_catalogo_local_workflow import (
    PRIVATE_MARKERS, catalogo_ctx, criar_local, criar_overlay, local_form, login,
    overlay_form, rejeitar_auditoria, snapshot_antigo, solicitar_local,
    solicitar_overlay,
)


@pytest.mark.parametrize("alias", ["admin", "manager", "worker"])
def test_todos_solicitam_sem_publicar_automaticamente(catalogo_ctx, alias):
    ctx = catalogo_ctx
    client = login(ctx, alias)
    pid = criar_local(ctx, client)
    antes = snapshot_antigo(ctx)
    sid = solicitar_local(ctx, client, pid)
    with ctx.app.app_context():
        obj = db.session.get(ctx.SolicitacaoCatalogo, sid)
        assert obj.estado == "pendente" and obj.tipo == "inclusao"
        assert obj.propriedade_id == ctx.ids["a"] and obj.solicitado_por_id == ctx.ids[alias]
        assert obj.origem_versao == 1 and obj.solicitado_em
        assert obj.produto_publicado_id is None and obj.decidido_por_id is None
        conteudo = json.loads(obj.conteudo_json)
        assert conteudo["nome"] == "Produto local informado"
        assert "observacoes" not in conteudo and "NOTA_PRIVADA_LOCAL" not in obj.conteudo_json
    assert snapshot_antigo(ctx) == antes
    assert client.get(f"/catalogo/local/solicitacoes/{sid}").status_code == 200


def test_solicitacao_e_snapshot_imutavel_e_reenvio_nao_duplica(catalogo_ctx):
    ctx = catalogo_ctx
    client = login(ctx, "worker")
    pid = criar_local(ctx, client)
    sid = solicitar_local(ctx, client, pid)
    sid2 = solicitar_local(ctx, client, pid)
    assert sid == sid2
    with ctx.app.app_context():
        original = db.session.get(ctx.SolicitacaoCatalogo, sid).conteudo_json
        assert ctx.SolicitacaoCatalogo.query.count() == 1
    editor = login(ctx, "manager")
    dados = local_form(nome="Produto alterado depois do envio", versao="1")
    dados.pop("chave_envio")
    assert editor.post(f"/catalogo/local/{pid}/editar", data=dados).status_code == 302
    with ctx.app.app_context():
        assert db.session.get(ctx.SolicitacaoCatalogo, sid).conteudo_json == original


@pytest.mark.parametrize("campo,valor", [("propriedade_id", "2"), ("solicitado_por_id", "5"),
    ("estado", "aprovada"), ("status_regulatorio", "tipo_tecnico_generico"),
    ("produto_publicado_id", "101"), ("catalogo_global_aprovador", "1")])
def test_solicitacao_nao_aceita_campos_protegidos(catalogo_ctx, campo, valor):
    ctx = catalogo_ctx
    client = login(ctx, "worker")
    pid = criar_local(ctx, client)
    payload = dict(nome="Nome proposto", classe="fertilizante", versao_origem="1", **{campo: valor})
    assert client.post(f"/catalogo/local/{pid}/solicitar", data=payload).status_code == 403
    with ctx.app.app_context():
        assert ctx.SolicitacaoCatalogo.query.count() == 0
        assert ProdutoBase.query.count() == 4


def test_versao_de_origem_forjada_ou_obsoleta_nao_cria_pedido(catalogo_ctx):
    ctx = catalogo_ctx
    client = login(ctx)
    pid = criar_local(ctx, client)
    response = client.post(f"/catalogo/local/{pid}/solicitar", data={"nome": "Proposta", "classe": "fertilizante", "versao_origem": "999"})
    assert response.status_code == 409
    with ctx.app.app_context():
        assert ctx.SolicitacaoCatalogo.query.count() == 0


@pytest.mark.parametrize("alias", ["admin", "manager", "worker", "invalid_reviewer"])
@pytest.mark.parametrize("suffix,method", [("", "get"), ("/aprovar", "post"), ("/rejeitar", "post")])
def test_aprovacao_global_nao_deriva_do_perfil_ou_cookie(catalogo_ctx, alias, suffix, method):
    ctx = catalogo_ctx
    sid = solicitar_local(ctx, login(ctx), criar_local(ctx))
    client = login(ctx, alias)
    with client.session_transaction() as sessao:
        sessao["catalogo_global_aprovador"] = True
        sessao["perfil"] = "admin"
    response = getattr(client, method)(f"/catalogo/revisao/{sid}{suffix}", data={"justificativa": "Pedido forjado"})
    assert response.status_code == 403
    with ctx.app.app_context():
        assert db.session.get(ctx.SolicitacaoCatalogo, sid).estado == "pendente"
        assert ProdutoBase.query.count() == 4


def test_revisor_sem_contexto_ve_so_proposta_e_nao_operacoes_terceiras(catalogo_ctx):
    ctx = catalogo_ctx
    origem = login(ctx, "foreign")
    pid = criar_local(ctx, origem, nome="Proposta apresentada pelo contexto B")
    sid = solicitar_local(ctx, origem, pid)
    revisor = login(ctx, "reviewer", selecionar=False)
    assert revisor.get("/catalogo/revisao/").status_code == 200
    response = revisor.get(f"/catalogo/revisao/{sid}")
    assert response.status_code == 200
    text = response.get_data(as_text=True)
    assert "Proposta apresentada pelo contexto B" in text
    assert "NOTA_PRIVADA_LOCAL" not in text
    for marker in PRIVATE_MARKERS:
        assert marker not in text
    for path in (f"/catalogo/local/{pid}", "/financeiro/", "/equipe/", "/mapa/dados"):
        response = revisor.get(path)
        assert response.status_code != 200
        for marker in PRIVATE_MARKERS:
            assert marker not in response.get_data(as_text=True)


@pytest.mark.parametrize("alias", ["admin", "manager", "worker"])
def test_solicitacoes_privadas_de_outra_propriedade_nao_aparecem(catalogo_ctx, alias):
    ctx = catalogo_ctx
    foreign = login(ctx, "foreign")
    pid = criar_local(ctx, foreign, nome="SOLICITACAO_PRIVADA_B")
    sid = solicitar_local(ctx, foreign, pid)
    client = login(ctx, alias)
    assert client.get(f"/catalogo/local/solicitacoes/{sid}").status_code == 404
    assert "SOLICITACAO_PRIVADA_B" not in client.get("/catalogo/local/solicitacoes").get_data(as_text=True)
    assert client.post(f"/catalogo/local/solicitacoes/{sid}/cancelar").status_code in (403, 404)
    with ctx.app.app_context():
        assert db.session.get(ctx.SolicitacaoCatalogo, sid).estado == "pendente"


def test_rejeicao_e_repeticao_preservam_global_e_decisao(catalogo_ctx):
    ctx = catalogo_ctx
    client = login(ctx)
    sid = solicitar_local(ctx, client, criar_local(ctx, client))
    antes = snapshot_antigo(ctx)
    revisor = login(ctx, "reviewer", selecionar=False)
    assert revisor.post(f"/catalogo/revisao/{sid}/rejeitar", data={"justificativa": "Informações insuficientes"}).status_code == 302
    assert revisor.post(f"/catalogo/revisao/{sid}/rejeitar", data={"justificativa": "Informações insuficientes"}).status_code == 302
    with ctx.app.app_context():
        req = db.session.get(ctx.SolicitacaoCatalogo, sid)
        assert req.estado == "rejeitada" and req.produto_publicado_id is None
        assert req.decidido_por_id == ctx.ids["reviewer"] and req.decidido_em
        assert req.justificativa == "Informações insuficientes"
    assert snapshot_antigo(ctx) == antes
    assert revisor.post(f"/catalogo/revisao/{sid}/aprovar").status_code == 409


@pytest.mark.parametrize("classe,regulatorio", [("defensivo", "nao_validado_agrofit"),
    ("fertilizante", "sujeito_a_sipeagro_nao_validado")])
def test_inclusao_global_aprovada_e_exata_idempotente_sem_precos(catalogo_ctx, classe, regulatorio):
    ctx = catalogo_ctx
    criador = login(ctx, "worker")
    pid = criar_local(ctx, criador, nome="Nova referência proposta", classe=classe)
    sid = solicitar_local(ctx, criador, pid)
    antes = snapshot_antigo(ctx)
    revisor = login(ctx, "reviewer", selecionar=False)
    dados = {"justificativa": "Inclusão administrativa, sem validação regulatória"}
    assert revisor.post(f"/catalogo/revisao/{sid}/aprovar", data=dados).status_code == 302
    with ctx.app.app_context():
        req = db.session.get(ctx.SolicitacaoCatalogo, sid)
        produto = db.session.get(ProdutoBase, req.produto_publicado_id)
        result_id = produto.id
        assert req.estado == "aprovada" and req.decidido_por_id == ctx.ids["reviewer"]
        assert produto.nome == "Nova referência proposta" and produto.classe == classe
        assert produto.status_regulatorio == regulatorio
        assert produto.status_sistema == "cadastrado_usuario"
        assert ProdutoPreco.query.filter_by(produto_id=result_id).count() == 0
        assert ProdutoImagem.query.filter_by(produto_id=result_id).count() == 0
        assert ctx.ProdutoLocal.query.count() == 1
        assert AplicacaoInsumo.query.one().produto_base_id == AtividadeItem.query.one().produto_base_id == 101
        assert ProdutoBase.query.count() == 5
        total_logs = LogAuditoria.query.count()
    assert revisor.post(f"/catalogo/revisao/{sid}/aprovar", data=dados).status_code == 302
    with ctx.app.app_context():
        req = db.session.get(ctx.SolicitacaoCatalogo, sid)
        assert req.produto_publicado_id == result_id and ProdutoBase.query.count() == 5
        assert LogAuditoria.query.count() == total_logs
    depois = snapshot_antigo(ctx)
    assert [row for row in depois["produto_base"] if row["id"] != result_id] == antes["produto_base"]
    for table in ("aplicacao_insumo", "atividade_item", "financeiro_lancamento", "produto_imagem", "produto_preco"):
        assert depois[table] == antes[table]
    assert revisor.post(f"/catalogo/revisao/{sid}/rejeitar").status_code == 409


def test_aprovacao_de_alteracao_preserva_identidade_ficha_e_operacoes(catalogo_ctx):
    ctx = catalogo_ctx
    criador = login(ctx, "worker")
    oid = criar_overlay(ctx, criador)
    sid = solicitar_overlay(ctx, criador, oid)
    antes = snapshot_antigo(ctx)
    response = login(ctx, "reviewer").post(f"/catalogo/revisao/{sid}/aprovar", data={"justificativa": "Complemento descritivo"})
    assert response.status_code == 302
    with ctx.app.app_context():
        produto = db.session.get(ProdutoBase, 101)
        assert produto.nome == "Produto global principal" and produto.slug == "global-principal"
        assert produto.classe == "fertilizante" and produto.status_regulatorio == "tipo_tecnico_generico"
        assert produto.descricao_curta == "Descrição curta proposta"
        assert produto.descricao_completa == "Descrição completa proposta"
        req = db.session.get(ctx.SolicitacaoCatalogo, sid)
        assert req.produto_publicado_id == 101 and "Descrição global original" in req.global_anterior_json
        assert ctx.ProdutoPersonalizacao.query.one().nome_local == "Apelido nesta propriedade"
    depois = snapshot_antigo(ctx)
    for table in ("produto_tecnico", "produto_imagem", "produto_preco", "aplicacao_insumo", "atividade_item", "financeiro_lancamento"):
        assert depois[table] == antes[table]


@pytest.mark.parametrize("acao_origem", ["editar", "inativar"])
def test_aprovacao_de_origem_modificada_ou_inativa_e_conflito(catalogo_ctx, acao_origem):
    ctx = catalogo_ctx
    client = login(ctx)
    pid = criar_local(ctx, client)
    sid = solicitar_local(ctx, client, pid)
    if acao_origem == "editar":
        dados = local_form(nome="Nova versão local", versao="1")
        dados.pop("chave_envio")
    else:
        dados = {"versao": "1"}
    assert client.post(f"/catalogo/local/{pid}/{acao_origem}", data=dados).status_code == 302
    antes = snapshot_antigo(ctx)
    assert login(ctx, "reviewer").post(f"/catalogo/revisao/{sid}/aprovar").status_code == 409
    with ctx.app.app_context():
        assert db.session.get(ctx.SolicitacaoCatalogo, sid).estado == "pendente"
    assert snapshot_antigo(ctx) == antes


def test_alteracao_global_concorrente_invalida_fingerprint_da_solicitacao(catalogo_ctx):
    ctx = catalogo_ctx
    client = login(ctx)
    oid = criar_overlay(ctx, client)
    sid = solicitar_overlay(ctx, client, oid)
    with ctx.app.app_context():
        db.session.get(ProdutoBase, 101).descricao_curta = "Alteração global posterior"
        db.session.commit()
    assert login(ctx, "reviewer").post(f"/catalogo/revisao/{sid}/aprovar").status_code == 409
    with ctx.app.app_context():
        assert db.session.get(ProdutoBase, 101).descricao_curta == "Alteração global posterior"
        assert db.session.get(ctx.SolicitacaoCatalogo, sid).estado == "pendente"


def test_slug_global_ja_existente_nao_e_reutilizado_implicitamente(catalogo_ctx):
    ctx = catalogo_ctx
    client = login(ctx)
    pid = criar_local(ctx, client, nome="Referência independente")
    sid = solicitar_local(ctx, client, pid)
    antes = snapshot_antigo(ctx)
    response = login(ctx, "reviewer").post(f"/catalogo/revisao/{sid}/aprovar", data={"slug_global": "global-principal"})
    assert response.status_code == 409
    assert snapshot_antigo(ctx) == antes


def test_revisor_pode_escolher_global_existente_sem_fusao_ou_reescrita(catalogo_ctx):
    ctx = catalogo_ctx
    client = login(ctx)
    pid = criar_local(ctx, client, nome="Nome local alternativo")
    sid = solicitar_local(ctx, client, pid)
    antes = snapshot_antigo(ctx)
    response = login(ctx, "reviewer").post(f"/catalogo/revisao/{sid}/aprovar", data={"produto_global_existente_id": "101"})
    assert response.status_code == 302
    with ctx.app.app_context():
        req = db.session.get(ctx.SolicitacaoCatalogo, sid)
        assert req.estado == "aprovada" and req.produto_publicado_id == 101
        assert ctx.ProdutoLocal.query.one().nome == "Nome local alternativo"
    assert snapshot_antigo(ctx) == antes


@pytest.mark.parametrize("target", ["103", "104", "999999", "9"*200])
def test_resultado_global_bloqueado_inexistente_ou_id_imenso_nao_aprova(catalogo_ctx, target):
    ctx = catalogo_ctx
    client = login(ctx)
    sid = solicitar_local(ctx, client, criar_local(ctx, client))
    response = login(ctx, "reviewer").post(f"/catalogo/revisao/{sid}/aprovar", data={"produto_global_existente_id": target})
    assert response.status_code in (400, 404, 409)
    with ctx.app.app_context():
        assert db.session.get(ctx.SolicitacaoCatalogo, sid).estado == "pendente"
        assert ProdutoBase.query.count() == 4


def test_revogar_capacidade_no_banco_invalida_cookie_ja_emitido(catalogo_ctx):
    ctx = catalogo_ctx
    client = login(ctx)
    sid = solicitar_local(ctx, client, criar_local(ctx, client))
    reviewer = login(ctx, "reviewer")
    assert reviewer.get(f"/catalogo/revisao/{sid}").status_code == 200
    with ctx.app.app_context():
        db.session.get(Usuario, ctx.ids["reviewer"]).catalogo_global_aprovador = False
        db.session.commit()
    assert reviewer.post(f"/catalogo/revisao/{sid}/aprovar").status_code == 403
    with ctx.app.app_context():
        assert db.session.get(ctx.SolicitacaoCatalogo, sid).estado == "pendente"


def test_falha_da_auditoria_na_decisao_desfaz_produto_e_estado(catalogo_ctx):
    ctx = catalogo_ctx
    client = login(ctx)
    sid = solicitar_local(ctx, client, criar_local(ctx, client))
    reviewer = login(ctx, "reviewer")
    cls = db.session.session_factory.class_
    event.listen(cls, "before_flush", rejeitar_auditoria)
    try:
        with pytest.raises(RuntimeError, match="auditoria sintética"):
            reviewer.post(f"/catalogo/revisao/{sid}/aprovar")
    finally:
        event.remove(cls, "before_flush", rejeitar_auditoria)
    with ctx.app.app_context():
        req = db.session.get(ctx.SolicitacaoCatalogo, sid)
        assert req.estado == "pendente" and req.produto_publicado_id is None
        assert ProdutoBase.query.count() == 4


def test_auditoria_tem_atores_e_decisao_sem_corpo_privado(catalogo_ctx):
    ctx = catalogo_ctx
    client = login(ctx, "worker")
    sid = solicitar_local(ctx, client, criar_local(ctx, client))
    assert login(ctx, "reviewer").post(f"/catalogo/revisao/{sid}/aprovar").status_code == 302
    with ctx.app.app_context():
        logs = LogAuditoria.query.filter(LogAuditoria.acao.like("catalogo%"), LogAuditoria.resultado == "sucesso").all()
        assert len(logs) >= 3
        assert any(log.usuario_id == ctx.ids["worker"] for log in logs)
        assert any(log.usuario_id == ctx.ids["reviewer"] for log in logs)
        texto = " ".join(log.descricao or "" for log in logs)
        assert "NOTA_PRIVADA_LOCAL" not in texto
        assert "Descrição local completa" not in texto
        assert "csrf_token" not in texto and "senha" not in texto.lower()


def test_cancelamento_local_de_solicitacao_nao_exclui_origem(catalogo_ctx):
    ctx = catalogo_ctx
    worker = login(ctx, "worker")
    pid = criar_local(ctx, worker)
    sid = solicitar_local(ctx, worker, pid)
    assert worker.post(f"/catalogo/local/solicitacoes/{sid}/cancelar").status_code == 403
    assert login(ctx, "manager").post(f"/catalogo/local/solicitacoes/{sid}/cancelar").status_code == 302
    with ctx.app.app_context():
        assert db.session.get(ctx.SolicitacaoCatalogo, sid).estado == "cancelada"
        assert db.session.get(ctx.ProdutoLocal, pid) is not None
    assert login(ctx, "reviewer").post(f"/catalogo/revisao/{sid}/aprovar").status_code == 409


def test_decisao_global_exige_csrf_mesmo_com_capacidade(catalogo_ctx):
    ctx = catalogo_ctx
    client = login(ctx)
    sid = solicitar_local(ctx, client, criar_local(ctx, client))
    ctx.app.config["WTF_CSRF_ENABLED"] = True
    reviewer = ctx.app.test_client()
    html = reviewer.get("/auth/login").get_data(as_text=True)
    token = re.search(r'name="csrf_token"[^>]*value="([^"]+)"', html).group(1)
    from tests.test_catalogo_local_workflow import _PASSWORD
    assert reviewer.post("/auth/login", data={"email": "reviewer@catalogo.invalid", "senha": _PASSWORD,
                                               "csrf_token": token}).status_code == 302
    html = reviewer.get(f"/catalogo/revisao/{sid}").get_data(as_text=True)
    token = re.search(r'name="csrf_token"[^>]*value="([^"]+)"', html).group(1)
    assert reviewer.post(f"/catalogo/revisao/{sid}/aprovar").status_code == 400
    with ctx.app.app_context():
        assert db.session.get(ctx.SolicitacaoCatalogo, sid).estado == "pendente"
    assert reviewer.post(f"/catalogo/revisao/{sid}/aprovar", data={"csrf_token": token}).status_code == 302


def test_cli_concede_e_revoga_apenas_capacidade_explicita_sem_mudar_perfil(catalogo_ctx):
    ctx = catalogo_ctx
    client = login(ctx)
    with ctx.app.app_context():
        conta = db.session.get(Usuario, ctx.ids["admin"])
        assert not conta.catalogo_global_aprovador
        original = (conta.perfil, conta.auth_version, conta.ativo)
    assert client.get("/catalogo/revisao/").status_code == 403
    runner = ctx.app.test_cli_runner()
    args = ["catalogo-global-permissao", "--usuario-id", str(ctx.ids["admin"])]
    motivo = "MOTIVO_OPERADOR_NAO_COPIAR_NO_LOG"
    result = runner.invoke(args=args+["--habilitar", "--motivo", motivo])
    assert result.exit_code == 0, result.output
    assert client.get("/catalogo/revisao/").status_code == 200
    with ctx.app.app_context():
        conta = db.session.get(Usuario, ctx.ids["admin"])
        assert conta.catalogo_global_aprovador
        assert (conta.perfil, conta.auth_version, conta.ativo) == original
        logs = LogAuditoria.query.filter_by(acao="catalogo.global.habilitar", entidade_id=conta.id).all()
        assert len(logs) == 1 and motivo not in logs[0].descricao
    result = runner.invoke(args=args+["--revogar"])
    assert result.exit_code == 0, result.output
    assert client.get("/catalogo/revisao/").status_code == 403
    with ctx.app.app_context():
        conta = db.session.get(Usuario, ctx.ids["admin"])
        assert not conta.catalogo_global_aprovador
        assert (conta.perfil, conta.auth_version, conta.ativo) == original


def test_cli_idempotente_nao_duplica_eventos_de_concessao_ou_revogacao(catalogo_ctx):
    ctx = catalogo_ctx
    runner = ctx.app.test_cli_runner()
    args = ["catalogo-global-permissao", "--usuario-id", str(ctx.ids["admin"])]
    for flag in ("--habilitar", "--habilitar", "--revogar", "--revogar"):
        result = runner.invoke(args=args+[flag])
        assert result.exit_code == 0, result.output
    with ctx.app.app_context():
        assert LogAuditoria.query.filter_by(acao="catalogo.global.habilitar", entidade_id=ctx.ids["admin"]).count() == 1
        assert LogAuditoria.query.filter_by(acao="catalogo.global.revogar", entidade_id=ctx.ids["admin"]).count() == 1


@pytest.mark.parametrize("alias", ["manager", "worker", "invalid_reviewer", "inactive_admin", "missing"])
def test_cli_nao_habilita_perfis_nao_admin_conta_inativa_ou_inexistente(catalogo_ctx, alias):
    ctx = catalogo_ctx
    if alias == "missing":
        uid = 999999
        anterior = None
    else:
        uid = ctx.ids["foreign" if alias == "inactive_admin" else alias]
        with ctx.app.app_context():
            conta = db.session.get(Usuario, uid)
            if alias == "inactive_admin":
                conta.ativo = False
                db.session.commit()
            anterior = (conta.perfil, conta.ativo, conta.catalogo_global_aprovador)
    result = ctx.app.test_cli_runner().invoke(args=["catalogo-global-permissao", "--usuario-id", str(uid), "--habilitar"])
    assert result.exit_code == 1
    with ctx.app.app_context():
        conta = db.session.get(Usuario, uid)
        assert (conta.perfil, conta.ativo, conta.catalogo_global_aprovador) == anterior if conta else anterior is None
        assert LogAuditoria.query.filter_by(acao="catalogo.global.habilitar", entidade_id=uid).count() == 0


@pytest.mark.parametrize("flags", [[], ["--habilitar", "--revogar"]])
def test_cli_exige_decisao_exclusiva(catalogo_ctx, flags):
    ctx = catalogo_ctx
    result = ctx.app.test_cli_runner().invoke(args=["catalogo-global-permissao", "--usuario-id", str(ctx.ids["admin"]), *flags])
    assert result.exit_code == 1
    with ctx.app.app_context():
        assert not db.session.get(Usuario, ctx.ids["admin"]).catalogo_global_aprovador


def test_cli_revoga_capacidade_residual_de_conta_que_nao_e_admin(catalogo_ctx):
    ctx = catalogo_ctx
    uid = ctx.ids["invalid_reviewer"]
    with ctx.app.app_context():
        assert db.session.get(Usuario, uid).catalogo_global_aprovador
    result = ctx.app.test_cli_runner().invoke(args=["catalogo-global-permissao", "--usuario-id", str(uid), "--revogar"])
    assert result.exit_code == 0
    with ctx.app.app_context():
        conta = db.session.get(Usuario, uid)
        assert conta.perfil == "tecnico" and not conta.catalogo_global_aprovador


def test_cli_desfaz_concessao_se_auditoria_falhar(catalogo_ctx):
    ctx = catalogo_ctx
    cls = db.session.session_factory.class_
    event.listen(cls, "before_flush", rejeitar_auditoria)
    try:
        result = ctx.app.test_cli_runner().invoke(args=["catalogo-global-permissao", "--usuario-id", str(ctx.ids["admin"]), "--habilitar"])
    finally:
        event.remove(cls, "before_flush", rejeitar_auditoria)
    assert result.exit_code != 0
    assert isinstance(result.exception, RuntimeError)
    with ctx.app.app_context():
        assert not db.session.get(Usuario, ctx.ids["admin"]).catalogo_global_aprovador
        assert LogAuditoria.query.filter_by(acao="catalogo.global.habilitar", entidade_id=ctx.ids["admin"]).count() == 0
