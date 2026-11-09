"""Catálogo local por Propriedade: integração HTTP e preservação do histórico."""
from decimal import Decimal
import json
import re
from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy import event
from werkzeug.datastructures import MultiDict

from app.extensions import db
from app.models import (AplicacaoInsumo, AtividadeItem, AtividadeOperacional,
                        Cultura, CulturaGleba, EquipeMembro, FinanceiroLancamento,
                        Gleba, LogAuditoria, ProdutoBase, ProdutoImagem,
                        ProdutoPreco, ProdutoTecnico, Usuario)
from app.utils.auth import gerar_hash_senha
from tests.factories import criar_propriedade_com_vinculo, vincular_usuario_propriedade


_PASSWORD = "catalogo-integration-test"
_HASH = gerar_hash_senha(_PASSWORD)
PRIVATE_MARKERS = ("PRIVATE_FINANCE_B", "PRIVATE_TEAM_B", "PRIVATE_AREA_B")


@pytest.fixture
def catalogo_ctx(app):
    from app.models import (CatalogoRevisao, ProdutoLocal,
                            ProdutoPersonalizacao, SolicitacaoCatalogo)

    with app.app_context():
        db.create_all()
        pessoas = {}
        for alias, perfil in (("admin", "admin"), ("manager", "tecnico"),
                              ("worker", "trabalhador"), ("foreign", "admin"),
                              ("reviewer", "admin"), ("invalid_reviewer", "tecnico")):
            user = Usuario(nome=f"Pessoa {alias}", email=f"{alias}@catalogo.invalid",
                           perfil=perfil, senha_hash=_HASH, ativo=True)
            if alias in {"reviewer", "invalid_reviewer"}:
                user.catalogo_global_aprovador = True
            db.session.add(user)
            pessoas[alias] = user
        db.session.flush()
        a = criar_propriedade_com_vinculo(pessoas["admin"].id, nome="Contexto Catálogo A")
        b = criar_propriedade_com_vinculo(pessoas["foreign"].id, nome="Contexto Catálogo B")
        c = criar_propriedade_com_vinculo(pessoas["admin"].id, nome="Outra propriedade autorizada")
        for alias in ("manager", "worker", "invalid_reviewer"):
            vincular_usuario_propriedade(pessoas[alias].id, a.id)
        area = Gleba(propriedade_id=a.id, nome="Área original A", area_ha=12.25,
                     poligono_geojson='{"type":"Polygon","coordinates":[[[0,0],[1,0],[1,1],[0,0]]]}')
        area_b = Gleba(propriedade_id=b.id, nome=PRIVATE_MARKERS[2], area_ha=8.5)
        cultura = Cultura(propriedade_id=a.id, nome="Cultura original A")
        globais = [
            ProdutoBase(id=101, nome="Produto global principal", slug="global-principal", classe="fertilizante",
                        descricao_curta="Descrição global original", descricao_completa="Ficha descritiva global original",
                        status_sistema="pre_cadastrado", status_regulatorio="tipo_tecnico_generico"),
            ProdutoBase(id=102, nome="Defensivo global", slug="defensivo-global", classe="defensivo"),
            ProdutoBase(id=103, nome="Global bloqueado sistema", slug="bloqueado-sistema", classe="fertilizante",
                        status_sistema="bloqueado_historico", status_regulatorio="tipo_tecnico_generico"),
            ProdutoBase(id=104, nome="Global bloqueado regulatório", slug="bloqueado-regulatorio", classe="fertilizante",
                        status_sistema="pre_cadastrado", status_regulatorio="bloqueado_historico"),
        ]
        db.session.add_all([area, area_b, cultura, *globais])
        db.session.flush()
        cg = CulturaGleba(cultura_id=cultura.id, gleba_id=area.id)
        db.session.add(cg)
        db.session.flush()
        db.session.add_all([
            ProdutoTecnico(produto_id=101, composicao="COMPOSICAO_GLOBAL_ORIGINAL", fonte_tecnica="Fonte original"),
            ProdutoImagem(produto_id=101, url="img/global-original.svg", fonte="Licença original", status_validacao="nao_consolidado"),
            ProdutoPreco(produto_id=101, valor=777.77, moeda="BRL", unidade="kg", status_validacao="pendente"),
            AplicacaoInsumo(cultura_gleba_id=cg.id, produto_base_id=101, data_aplicacao="2026-11-01",
                            dose=2.0, unidade="L/ha", quantidade_utilizada=Decimal("15.125"),
                            unidade_quantidade="L", custo_total=Decimal("18.25"), moeda="BRL",
                            origem_custo="informado_usuario", responsavel="Executor histórico", criado_por_id=pessoas["admin"].id),
            FinanceiroLancamento(propriedade_id=b.id, tipo="despesa", descricao=PRIVATE_MARKERS[0],
                                 valor=12345.67, data="2026-11-01"),
            EquipeMembro(propriedade_id=b.id, nome=PRIVATE_MARKERS[1], ativo=True),
        ])
        atividade = AtividadeOperacional(gleba_id=area.id, cultura_gleba_id=cg.id,
            tipo_atividade="Atividade histórica", data_execucao="2026-11-01", responsavel="Executor original",
            criado_por_id=pessoas["admin"].id)
        db.session.add(atividade)
        db.session.flush()
        db.session.add(AtividadeItem(atividade_id=atividade.id, produto_base_id=101,
            dose=Decimal("2.125"), unidade_dose="L/ha", quantidade_utilizada=Decimal("4.125"),
            unidade_quantidade="kg", custo_total=Decimal("6.67"), moeda="BRL", origem_custo="informado_usuario"))
        db.session.commit()
        ids = {alias: pessoa.id for alias, pessoa in pessoas.items()}
        ids.update(a=a.id, b=b.id, c=c.id, area=area.id, area_b=area_b.id, cg=cg.id,
                   global_id=101, defensivo=102, blocked_system=103, blocked_regulatory=104)
    return SimpleNamespace(app=app, ids=ids, ProdutoLocal=ProdutoLocal,
                           ProdutoPersonalizacao=ProdutoPersonalizacao,
                           CatalogoRevisao=CatalogoRevisao, SolicitacaoCatalogo=SolicitacaoCatalogo)


def login(ctx, alias="admin", *, selecionar=True):
    client = ctx.app.test_client()
    resposta = client.post("/auth/login", data={"email": f"{alias}@catalogo.invalid", "senha": _PASSWORD})
    assert resposta.status_code == 302
    if selecionar and alias != "reviewer":
        with client.session_transaction() as sessao:
            sessao["propriedade_ativa_id"] = ctx.ids["b" if alias == "foreign" else "a"]
    return client


def local_form(**mudancas):
    form = {"nome": "Produto local informado", "classe": "fertilizante", "categoria": "Categoria local",
            "descricao_curta": "Descrição curta local", "descricao_completa": "Descrição local completa",
            "unidade_referencia": "kg", "observacoes": "NOTA_PRIVADA_LOCAL", "fonte": "Fonte informada pelo usuário",
            "chave_envio": uuid4().hex}
    form.update(mudancas)
    return form


def overlay_form(**mudancas):
    form = {"nome_local": "Apelido nesta propriedade", "descricao_local": "Complemento local informado",
            "unidade_referencia": "L", "observacoes": "NOTA_PRIVADA_OVERLAY", "fonte": "Caderno da propriedade"}
    form.update(mudancas)
    return form


def criar_local(ctx, client=None, **mudancas):
    client = client or login(ctx)
    form = local_form(**mudancas)
    resposta = client.post("/catalogo/local/novo", data=form)
    assert resposta.status_code == 302, resposta.get_data(as_text=True)[-2000:]
    with ctx.app.app_context():
        obj = ctx.ProdutoLocal.query.filter_by(chave_envio=form["chave_envio"]).one()
        return obj.id


def criar_overlay(ctx, client=None, produto_id=None, **mudancas):
    client = client or login(ctx)
    pid = produto_id or ctx.ids["global_id"]
    resposta = client.post(f"/catalogo/local/personalizar/{pid}", data=overlay_form(**mudancas))
    assert resposta.status_code == 302, resposta.get_data(as_text=True)[-2000:]
    with client.session_transaction() as sessao:
        propriedade_id = sessao["propriedade_ativa_id"]
    with ctx.app.app_context():
        return ctx.ProdutoPersonalizacao.query.filter_by(produto_base_id=pid, propriedade_id=propriedade_id).one().id


def solicitar_local(ctx, client, produto_id, **mudancas):
    with ctx.app.app_context():
        origem = db.session.get(ctx.ProdutoLocal, produto_id)
        form = {"nome": origem.nome, "classe": origem.classe, "categoria": origem.categoria or "",
                "descricao_curta": origem.descricao_curta or "", "descricao_completa": origem.descricao_completa or "",
                "fonte": origem.fonte or "", "versao_origem": str(origem.versao)}
    form.update(mudancas)
    resposta = client.post(f"/catalogo/local/{produto_id}/solicitar", data=form)
    assert resposta.status_code == 302, resposta.get_data(as_text=True)[-2000:]
    with ctx.app.app_context():
        return ctx.SolicitacaoCatalogo.query.filter_by(produto_local_id=produto_id).order_by(ctx.SolicitacaoCatalogo.id.desc()).first().id


def solicitar_overlay(ctx, client, personalizacao_id, **mudancas):
    with ctx.app.app_context():
        origem = db.session.get(ctx.ProdutoPersonalizacao, personalizacao_id)
        form = {"descricao_curta": "Descrição curta proposta", "descricao_completa": "Descrição completa proposta",
                "fonte": "Fonte explícita da proposta", "versao_origem": str(origem.versao)}
    form.update(mudancas)
    resposta = client.post(f"/catalogo/local/personalizacoes/{personalizacao_id}/solicitar", data=form)
    assert resposta.status_code == 302, resposta.get_data(as_text=True)[-2000:]
    with ctx.app.app_context():
        return ctx.SolicitacaoCatalogo.query.filter_by(personalizacao_id=personalizacao_id).one().id


def snapshot_antigo(ctx):
    with ctx.app.app_context():
        modelos = (ProdutoBase, ProdutoTecnico, ProdutoImagem, ProdutoPreco,
                   AplicacaoInsumo, AtividadeOperacional, AtividadeItem,
                   FinanceiroLancamento, Gleba)
        return {m.__tablename__: [{c.name: getattr(o, c.name) for c in m.__table__.columns}
                                 for o in m.query.order_by(m.id).all()] for m in modelos}


def rejeitar_auditoria(sessao, *_):
    if any(isinstance(obj, LogAuditoria) and obj.acao.startswith("catalogo") for obj in sessao.new):
        raise RuntimeError("Falha de auditoria sintética")


@pytest.mark.parametrize("path", ["/catalogo/local/", "/catalogo/local/novo", "/catalogo/local/solicitacoes",
                                  "/catalogo/local/personalizar/101", "/catalogo/revisao/"])
def test_novas_paginas_exigem_login(catalogo_ctx, path):
    response = catalogo_ctx.app.test_client().get(path)
    assert response.status_code == 302 and "/auth/login" in response.headers["Location"]


@pytest.mark.parametrize("alias", ["admin", "manager", "worker"])
def test_todos_criam_produtos_locais_no_contexto_e_autoria_da_sessao(catalogo_ctx, alias):
    ctx = catalogo_ctx
    antes = snapshot_antigo(ctx)
    client = login(ctx, alias)
    pid = criar_local(ctx, client)
    with ctx.app.app_context():
        produto = db.session.get(ctx.ProdutoLocal, pid)
        assert produto.propriedade_id == ctx.ids["a"]
        assert produto.criado_por_id == ctx.ids[alias]
        assert produto.versao == 1 and produto.ativo and produto.criado_em
        assert ctx.CatalogoRevisao.query.filter_by(produto_local_id=pid).count() == 1
    assert client.get(f"/catalogo/local/{pid}").status_code == 200
    assert snapshot_antigo(ctx) == antes


def test_campos_opcionais_locais_nao_sao_exigidos(catalogo_ctx):
    ctx = catalogo_ctx
    client = login(ctx, "worker")
    form = {"nome": "Cadastro mínimo informado", "classe": "defensivo", "chave_envio": uuid4().hex}
    assert client.post("/catalogo/local/novo", data=form).status_code == 302
    with ctx.app.app_context():
        obj = ctx.ProdutoLocal.query.one()
        assert obj.categoria is None and obj.fonte is None and obj.unidade_referencia is None
        assert ProdutoPreco.query.count() == 1


@pytest.mark.parametrize("campo,valor", [
    ("propriedade_id", "2"), ("criado_por_id", "4"), ("status_sistema", "definitivo"),
    ("status_regulatorio", "tipo_tecnico_generico"), ("catalogo_global_aprovador", "1"),
    ("produto_publicado_id", "101"), ("estado", "aprovada"),
])
def test_campos_protegidos_forjados_nao_criam_registro(catalogo_ctx, campo, valor):
    ctx = catalogo_ctx
    client = login(ctx, "worker")
    assert client.post("/catalogo/local/novo", data=local_form(**{campo: valor})).status_code == 403
    with ctx.app.app_context():
        assert ctx.ProdutoLocal.query.count() == 0
        assert not db.session.get(Usuario, ctx.ids["worker"]).catalogo_global_aprovador


@pytest.mark.parametrize("campo,valor", [("nome", ""), ("nome", "x"*151), ("classe", "classe-inventada"),
                                         ("categoria", "x"*41), ("unidade_referencia", "x"*21),
                                         ("fonte", "x"*256), ("chave_envio", "nao-uuid")])
def test_cadastro_invalido_nao_persiste_parcialmente(catalogo_ctx, campo, valor):
    ctx = catalogo_ctx
    client = login(ctx)
    response = client.post("/catalogo/local/novo", data=local_form(**{campo: valor}))
    assert response.status_code == 400
    with ctx.app.app_context():
        assert ctx.ProdutoLocal.query.count() == ctx.CatalogoRevisao.query.count() == 0


def test_dados_e_erro_do_campo_permanecem_no_formulario(catalogo_ctx):
    ctx = catalogo_ctx
    response = login(ctx).post("/catalogo/local/novo", data=local_form(nome="Nome a preservar", classe="inválida"))
    assert response.status_code == 400
    content = response.get_data(as_text=True)
    assert "Nome a preservar" in content and "Descrição local completa" in content
    assert 'aria-invalid="true"' in content


def test_reenvio_idempotente_e_chave_conflitante(catalogo_ctx):
    ctx = catalogo_ctx
    client = login(ctx)
    dados = local_form()
    assert client.post("/catalogo/local/novo", data=dados).status_code == 302
    assert client.post("/catalogo/local/novo", data=dados).status_code == 302
    dados["nome"] = "Outro conteúdo com a mesma chave"
    assert client.post("/catalogo/local/novo", data=dados).status_code == 409
    with ctx.app.app_context():
        assert ctx.ProdutoLocal.query.count() == ctx.CatalogoRevisao.query.count() == 1


def test_nome_semelhante_exige_revisao_sem_fusao_automatica(catalogo_ctx):
    ctx = catalogo_ctx
    client = login(ctx)
    primeiro = criar_local(ctx, client)
    dados = local_form()
    assert client.post("/catalogo/local/novo", data=dados).status_code == 400
    dados["confirmar_semelhante"] = "1"
    assert client.post("/catalogo/local/novo", data=dados).status_code == 302
    with ctx.app.app_context():
        assert ctx.ProdutoLocal.query.count() == 2
        assert db.session.get(ctx.ProdutoLocal, primeiro).nome == dados["nome"]
        assert ProdutoBase.query.count() == 4


@pytest.mark.parametrize("alias", ["admin", "manager"])
def test_edicao_versionada_preserva_autor_e_revisao_anterior(catalogo_ctx, alias):
    ctx = catalogo_ctx
    pid = criar_local(ctx, login(ctx, "worker"))
    editor = login(ctx, alias)
    dados = local_form(nome="Nome local revisado", versao="1")
    dados.pop("chave_envio")
    response = editor.post(f"/catalogo/local/{pid}/editar", data=dados)
    assert response.status_code == 302
    with ctx.app.app_context():
        produto = db.session.get(ctx.ProdutoLocal, pid)
        assert produto.nome == "Nome local revisado" and produto.versao == 2
        assert produto.criado_por_id == ctx.ids["worker"]
        assert produto.atualizado_por_id == ctx.ids[alias] and produto.atualizado_em
        revisoes = ctx.CatalogoRevisao.query.filter_by(produto_local_id=pid).order_by(ctx.CatalogoRevisao.versao).all()
        assert len(revisoes) == 2
        assert "Produto local informado" in revisoes[0].snapshot_json
        assert "Nome local revisado" in revisoes[1].snapshot_json
    dados["nome"] = "Edição obsoleta"
    assert editor.post(f"/catalogo/local/{pid}/editar", data=dados).status_code == 409


@pytest.mark.parametrize("suffix,method", [("editar", "get"), ("editar", "post"), ("inativar", "post"), ("reativar", "post")])
def test_trabalhador_nao_edita_ou_muda_estado_de_produto_local(catalogo_ctx, suffix, method):
    ctx = catalogo_ctx
    pid = criar_local(ctx, login(ctx, "worker"))
    worker = login(ctx, "worker")
    response = getattr(worker, method)(f"/catalogo/local/{pid}/{suffix}", data=local_form(versao="1"))
    assert response.status_code == 403
    with ctx.app.app_context():
        obj = db.session.get(ctx.ProdutoLocal, pid)
        assert obj.ativo and obj.versao == 1


def test_desativacao_e_reativacao_preservam_solicitacoes_e_revisoes(catalogo_ctx):
    ctx = catalogo_ctx
    client = login(ctx)
    pid = criar_local(ctx, client)
    sid = solicitar_local(ctx, client, pid)
    assert client.post(f"/catalogo/local/{pid}/inativar", data={"versao": "1"}).status_code == 302
    with ctx.app.app_context():
        obj = db.session.get(ctx.ProdutoLocal, pid)
        assert not obj.ativo and obj.versao == 2
        assert db.session.get(ctx.SolicitacaoCatalogo, sid).estado == "pendente"
        assert ctx.CatalogoRevisao.query.filter_by(produto_local_id=pid).count() == 2
    assert client.post(f"/catalogo/local/{pid}/reativar", data={"versao": "2"}).status_code == 302
    with ctx.app.app_context():
        assert db.session.get(ctx.ProdutoLocal, pid).ativo


@pytest.mark.parametrize("path", ["", "/editar", "/solicitar"])
def test_cadastro_de_outra_propriedade_nao_pode_ser_lido(catalogo_ctx, path):
    ctx = catalogo_ctx
    externo = login(ctx, "foreign")
    pid = criar_local(ctx, externo, nome="REGISTRO_PRIVADO_B")
    response = login(ctx).get(f"/catalogo/local/{pid}{path}")
    assert response.status_code == 404
    assert "REGISTRO_PRIVADO_B" not in response.get_data(as_text=True)


@pytest.mark.parametrize("suffix", ["editar", "inativar", "reativar", "solicitar"])
def test_post_externo_nao_altera_registro(catalogo_ctx, suffix):
    ctx = catalogo_ctx
    pid = criar_local(ctx, login(ctx, "foreign"), nome="REGISTRO_PRIVADO_B")
    response = login(ctx).post(f"/catalogo/local/{pid}/{suffix}", data=local_form(versao="1", versao_origem="1"))
    assert response.status_code == 404
    with ctx.app.app_context():
        obj = db.session.get(ctx.ProdutoLocal, pid)
        assert obj.nome == "REGISTRO_PRIVADO_B" and obj.ativo and obj.versao == 1


def test_outra_propriedade_autorizada_nao_e_o_contexto_ativo(catalogo_ctx):
    ctx = catalogo_ctx
    client = login(ctx)
    with client.session_transaction() as session:
        session["propriedade_ativa_id"] = ctx.ids["c"]
    pid = criar_local(ctx, client, nome="OUTRO_CONTEXTO_AUTORIZADO")
    with client.session_transaction() as session:
        session["propriedade_ativa_id"] = ctx.ids["a"]
    assert client.get(f"/catalogo/local/{pid}").status_code == 404
    assert "OUTRO_CONTEXTO_AUTORIZADO" not in client.get("/catalogo/local/").get_data(as_text=True)


@pytest.mark.parametrize("alias", ["admin", "manager", "worker"])
def test_personalizacao_e_local_sem_modificar_produto_global(catalogo_ctx, alias):
    ctx = catalogo_ctx
    antes = snapshot_antigo(ctx)
    client = login(ctx, alias)
    oid = criar_overlay(ctx, client)
    with ctx.app.app_context():
        obj = db.session.get(ctx.ProdutoPersonalizacao, oid)
        assert obj.propriedade_id == ctx.ids["a"] and obj.produto_base_id == 101
        assert obj.criado_por_id == ctx.ids[alias] and obj.versao == 1
    assert snapshot_antigo(ctx) == antes
    own = client.get("/fertilizantes/global-principal").get_data(as_text=True)
    other = login(ctx, "foreign").get("/fertilizantes/global-principal").get_data(as_text=True)
    assert "Apelido nesta propriedade" in own
    assert "Apelido nesta propriedade" not in other and "NOTA_PRIVADA_OVERLAY" not in other
    assert "Produto global principal" in own


def test_trabalhador_nao_sobrescreve_personalizacao_existente(catalogo_ctx):
    ctx = catalogo_ctx
    oid = criar_overlay(ctx, login(ctx, "worker"))
    response = login(ctx, "worker").post("/catalogo/local/personalizar/101", data=overlay_form(nome_local="Tentativa", versao="1"))
    assert response.status_code == 403
    with ctx.app.app_context():
        assert db.session.get(ctx.ProdutoPersonalizacao, oid).nome_local == "Apelido nesta propriedade"
        assert ctx.ProdutoPersonalizacao.query.count() == 1


@pytest.mark.parametrize("alias", ["admin", "manager"])
def test_edicao_overlay_tem_historico_e_nao_atualiza_atividades(catalogo_ctx, alias):
    ctx = catalogo_ctx
    antes = snapshot_antigo(ctx)
    oid = criar_overlay(ctx, login(ctx, "worker"))
    response = login(ctx, alias).post("/catalogo/local/personalizar/101", data=overlay_form(nome_local="Apelido revisado", versao="1"))
    assert response.status_code == 302
    with ctx.app.app_context():
        obj = db.session.get(ctx.ProdutoPersonalizacao, oid)
        assert obj.versao == 2 and obj.criado_por_id == ctx.ids["worker"]
        assert ctx.CatalogoRevisao.query.filter_by(personalizacao_id=oid).count() == 2
    assert snapshot_antigo(ctx) == antes
    response = login(ctx, "worker").get("/relatorios/operacionais")
    text = response.get_data(as_text=True)
    assert response.status_code == 200 and "Produto global principal" in text
    assert "Apelido revisado" not in text


@pytest.mark.parametrize("campo", ["status_sistema", "status_regulatorio", "produto_base_id", "propriedade_id", "catalogo_global_aprovador"])
def test_personalizacao_nao_aceita_sobrescrita_protegida(catalogo_ctx, campo):
    ctx = catalogo_ctx
    antes = snapshot_antigo(ctx)
    response = login(ctx, "worker").post("/catalogo/local/personalizar/101", data=overlay_form(**{campo: "1"}))
    assert response.status_code == 403
    assert snapshot_antigo(ctx) == antes
    with ctx.app.app_context():
        assert ctx.ProdutoPersonalizacao.query.count() == 0


def test_personalizacao_e_seu_historico_nao_saem_do_contexto(catalogo_ctx):
    ctx = catalogo_ctx
    foreign = login(ctx, "foreign")
    oid = criar_overlay(ctx, foreign, nome_local="PERSONALIZACAO_PRIVADA_B")
    client = login(ctx)
    assert client.get(f"/catalogo/local/personalizacoes/{oid}/solicitar").status_code == 404
    assert client.post(f"/catalogo/local/personalizacoes/{oid}/estado", data={"versao": "1", "ativo": "0"}).status_code == 404
    response = client.get(f"/catalogo/local/historico/personalizacao/{oid}")
    assert response.status_code == 404 and "PERSONALIZACAO_PRIVADA_B" not in response.get_data(as_text=True)


def test_historico_de_produto_local_de_outro_contexto_e_privado(catalogo_ctx):
    ctx = catalogo_ctx
    pid = criar_local(ctx, login(ctx, "foreign"), nome="HISTORICO_PRIVADO_B")
    response = login(ctx).get(f"/catalogo/local/historico/local/{pid}")
    assert response.status_code == 404 and "NOTA_PRIVADA_LOCAL" not in response.get_data(as_text=True)


def test_catalogo_global_sem_contexto_nao_expoe_dados_locais(catalogo_ctx):
    ctx = catalogo_ctx
    criar_local(ctx, login(ctx), nome="NOME_LOCAL_PRIVADO_A")
    criar_overlay(ctx, login(ctx))
    client = login(ctx, "admin", selecionar=False)
    for path in ("/fertilizantes/", "/fertilizantes/global-principal", "/defensivos/"):
        response = client.get(path)
        assert response.status_code == 200
        text = response.get_data(as_text=True)
        assert "NOME_LOCAL_PRIVADO_A" not in text and "Apelido nesta propriedade" not in text
    assert client.get("/catalogo/local/").status_code == 302


def test_produto_local_nao_entra_nos_seletores_globais_ou_operacoes(catalogo_ctx):
    ctx = catalogo_ctx
    client = login(ctx)
    pid = criar_local(ctx, client, nome="SOMENTE_CADASTRO_LOCAL")
    assert pid != ctx.ids["global_id"]
    for path in ("/aplicacoes/nova", "/atividades/nova"):
        response = client.get(path)
        assert response.status_code == 200 and "SOMENTE_CADASTRO_LOCAL" not in response.get_data(as_text=True)
    response = client.post("/aplicacoes/nova", data={"cultura_gleba_id": ctx.ids["cg"], "produto_base_id": pid,
        "data_aplicacao": "2026-11-09", "dose": "1", "unidade": "kg", "responsavel": "Executor"})
    assert response.status_code == 400
    with ctx.app.app_context():
        assert AplicacaoInsumo.query.count() == 1 and ProdutoBase.query.count() == 4


@pytest.mark.parametrize("nome", ["Global bloqueado sistema", "Global bloqueado regulatório", "Paraquate"])
def test_novo_nome_local_nao_contorna_referencia_bloqueada(catalogo_ctx, nome):
    ctx = catalogo_ctx
    response = login(ctx, "worker").post("/catalogo/local/novo", data=local_form(nome=nome))
    assert response.status_code == 400
    with ctx.app.app_context():
        assert ctx.ProdutoLocal.query.count() == 0
        assert db.session.get(ProdutoBase, 103).status_sistema == "bloqueado_historico"
        assert db.session.get(ProdutoBase, 104).status_regulatorio == "bloqueado_historico"


@pytest.mark.parametrize("produto_id", [103, 104])
def test_personalizacao_nao_libera_aplicacao_de_global_bloqueado(catalogo_ctx, produto_id):
    ctx = catalogo_ctx
    client = login(ctx)
    criar_overlay(ctx, client, produto_id=produto_id, nome_local="Nome apenas complementar")
    response = client.post("/aplicacoes/nova", data={"cultura_gleba_id": ctx.ids["cg"], "produto_base_id": produto_id,
        "data_aplicacao": "2026-11-09", "dose": "1", "unidade": "kg", "responsavel": "Executor"})
    assert response.status_code == 400
    with ctx.app.app_context():
        assert AplicacaoInsumo.query.count() == 1


def test_campos_duplicados_ou_desconhecidos_nao_sao_ignorados(catalogo_ctx):
    ctx = catalogo_ctx
    client = login(ctx)
    dados = MultiDict(local_form())
    dados.add("nome", "Nome conflitante")
    assert client.post("/catalogo/local/novo", data=dados).status_code == 400
    assert client.post("/catalogo/local/novo", data=local_form(campo_desconhecido="valor")).status_code == 400
    with ctx.app.app_context():
        assert ctx.ProdutoLocal.query.count() == 0


def test_falha_de_auditoria_desfaz_cadastro_e_revisao(catalogo_ctx):
    ctx = catalogo_ctx
    client = login(ctx)
    cls = db.session.session_factory.class_
    event.listen(cls, "before_flush", rejeitar_auditoria)
    try:
        with pytest.raises(RuntimeError, match="auditoria sintética"):
            client.post("/catalogo/local/novo", data=local_form())
    finally:
        event.remove(cls, "before_flush", rejeitar_auditoria)
    with ctx.app.app_context():
        assert ctx.ProdutoLocal.query.count() == ctx.CatalogoRevisao.query.count() == 0


def test_formulario_local_exige_csrf_real(catalogo_ctx):
    ctx = catalogo_ctx
    ctx.app.config["WTF_CSRF_ENABLED"] = True
    client = ctx.app.test_client()
    login_html = client.get("/auth/login").get_data(as_text=True)
    token = re.search(r'name="csrf_token"[^>]*value="([^"]+)"', login_html).group(1)
    assert client.post("/auth/login", data={"csrf_token": token, "email": "worker@catalogo.invalid", "senha": _PASSWORD}).status_code == 302
    form_html = client.get("/catalogo/local/novo").get_data(as_text=True)
    token = re.search(r'name="csrf_token"[^>]*value="([^"]+)"', form_html).group(1)
    assert client.post("/catalogo/local/novo", data=local_form()).status_code == 400
    assert client.post("/catalogo/local/novo", data=local_form(csrf_token=token)).status_code == 302


@pytest.mark.parametrize("acao", ["inativar", "reativar", "personalizacao_estado", "cancelar_solicitacao"])
@pytest.mark.parametrize("ataque,status", [("extra", 400), ("duplicado", 400), ("protegido", 403)])
def test_acoes_curta_validacao_recusam_campos_sem_500_ou_mutacao(catalogo_ctx, acao, ataque, status):
    """Ações sem formulário de edição também validam a forma do payload."""
    ctx = catalogo_ctx
    client = login(ctx)
    if acao == "personalizacao_estado":
        oid = criar_overlay(ctx, client)
        path = f"/catalogo/local/personalizacoes/{oid}/estado"
        payload = MultiDict({"versao": "1", "ativo": "0"})
    else:
        pid = criar_local(ctx, client)
        if acao == "cancelar_solicitacao":
            sid = solicitar_local(ctx, client, pid)
            path = f"/catalogo/local/solicitacoes/{sid}/cancelar"
            payload = MultiDict()
        elif acao == "reativar":
            assert client.post(f"/catalogo/local/{pid}/inativar", data={"versao": "1"}).status_code == 302
            path = f"/catalogo/local/{pid}/reativar"
            payload = MultiDict({"versao": "2"})
        else:
            path = f"/catalogo/local/{pid}/inativar"
            payload = MultiDict({"versao": "1"})

    def snapshot():
        with ctx.app.app_context():
            modelos = (ctx.ProdutoLocal, ctx.ProdutoPersonalizacao,
                       ctx.CatalogoRevisao, ctx.SolicitacaoCatalogo)
            return {m.__tablename__: [{c.name: getattr(obj, c.name) for c in m.__table__.columns}
                                     for obj in m.query.order_by(m.id).all()] for m in modelos}

    antes = snapshot()
    if ataque == "protegido":
        payload["propriedade_id"] = str(ctx.ids["b"])
    elif ataque == "extra":
        payload["campo_extra"] = "valor não permitido"
    elif "versao" in payload:
        payload.add("versao", payload["versao"])
    else:
        # Cancelamento não possui campos de domínio permitidos: duplicar um
        # campo extra continua sendo entrada inválida, sem exceção HTTP 500.
        payload.add("campo_extra", "primeiro")
        payload.add("campo_extra", "segundo")
    response = client.post(path, data=payload)
    assert response.status_code == status
    assert snapshot() == antes
