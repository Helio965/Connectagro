"""Regressões de consumo, autoria e integridade dos registros legados (Etapa 06)."""
from decimal import Decimal
from uuid import uuid4

import pytest

from app.extensions import db
from app.models import (
    AplicacaoInsumo, AtividadeOperacional, ColheitaRegistro, Cultura, CulturaGleba,
    FinanceiroLancamento, Gleba, LogAuditoria, ProdutoBase, ProdutoPreco, Usuario,
    UsuarioPropriedade,
)
from app.utils.auth import gerar_hash_senha
from tests.factories import criar_propriedade_com_vinculo, vincular_usuario_propriedade


PASSWORD = "test-legacy-stage6-password"


@pytest.fixture
def legacy_app(app):
    with app.app_context():
        db.create_all()
        password_hash = gerar_hash_senha(PASSWORD)
        users = {}
        for alias, role in (("admin", "admin"), ("manager", "tecnico"),
                            ("worker", "trabalhador"), ("executor", "trabalhador"),
                            ("inactive", "trabalhador"), ("revoked", "trabalhador"),
                            ("foreign", "admin")):
            user = Usuario(nome=f"Nome {alias}", email=f"{alias}@legacy-stage6.invalid",
                           perfil=role, ativo=alias != "inactive", senha_hash=password_hash)
            db.session.add(user)
            db.session.flush()
            users[alias] = user
        prop = criar_propriedade_com_vinculo(users["admin"].id, nome="Propriedade local")
        other = criar_propriedade_com_vinculo(users["foreign"].id, nome="Propriedade externa")
        for alias in ("manager", "worker", "executor", "inactive", "revoked"):
            vincular_usuario_propriedade(users[alias].id, prop.id, ativo=alias != "revoked")
        gleba = Gleba(propriedade_id=prop.id, nome="Área local", area_ha=20)
        gleba_b = Gleba(propriedade_id=other.id, nome="Área externa", area_ha=30)
        empty_gleba = Gleba(propriedade_id=prop.id, nome="Área sem cultura", area_ha=10)
        cultura = Cultura(propriedade_id=prop.id, nome="Cultura local")
        cultura_b = Cultura(propriedade_id=other.id, nome="Cultura externa")
        produto = ProdutoBase(nome="Produto permitido", slug="produto-permitido",
                              classe="fertilizante", status_sistema="pre_cadastrado",
                              status_regulatorio="tipo_tecnico_generico")
        bloqueado = ProdutoBase(nome="Produto bloqueado", slug="produto-bloqueado",
                                classe="defensivo", status_sistema="bloqueado_historico",
                                status_regulatorio="bloqueado_historico")
        db.session.add_all([gleba, gleba_b, empty_gleba, cultura, cultura_b, produto, bloqueado])
        db.session.flush()
        cg = CulturaGleba(cultura_id=cultura.id, gleba_id=gleba.id)
        cg_b = CulturaGleba(cultura_id=cultura_b.id, gleba_id=gleba_b.id)
        inconsistent = CulturaGleba(cultura_id=cultura.id, gleba_id=gleba_b.id)
        db.session.add_all([cg, cg_b, inconsistent])
        db.session.flush()
        db.session.add(ProdutoPreco(produto_id=produto.id, valor=99999.99,
                                    status_validacao="pendente"))
        db.session.commit()
        app.legacy_ids = {alias: user.id for alias, user in users.items()}
        app.legacy_ids.update(prop=prop.id, other=other.id, gleba=gleba.id,
                              gleba_b=gleba_b.id, empty_gleba=empty_gleba.id,
                              cultura=cultura.id, cultura_b=cultura_b.id,
                              cg=cg.id, cg_b=cg_b.id, inconsistent=inconsistent.id,
                              produto=produto.id, bloqueado=bloqueado.id)
    return app


def _login(app, alias="admin"):
    client = app.test_client()
    assert client.post("/auth/login", data={
        "email": f"{alias}@legacy-stage6.invalid", "senha": PASSWORD,
    }).status_code == 302
    return client


def _data(app, kind="aplicacoes", **extra):
    dados = {"cultura_gleba_id": str(app.legacy_ids["cg"]),
             "responsavel": "Executor textual", "observacao": "Registro sintético"}
    if kind == "aplicacoes":
        dados.update(produto_base_id=str(app.legacy_ids["produto"]),
                     data_aplicacao="2026-05-10", dose="2,5", unidade="L/ha")
    else:
        dados.update(data_colheita="2026-05-10", quantidade="12,25", unidade="kg")
    dados.update(extra)
    return dados


def _model(kind):
    return AplicacaoInsumo if kind == "aplicacoes" else ColheitaRegistro


def _record(app, kind):
    with app.app_context():
        return db.session.query(_model(kind)).one().id


@pytest.mark.parametrize("kind", ["aplicacoes", "colheita"])
def test_autoria_de_sessao_e_executor_conta_sao_distintos(legacy_app, kind):
    client = _login(legacy_app)
    dados = _data(legacy_app, kind,
                  responsavel_usuario_id=str(legacy_app.legacy_ids["executor"]),
                  criado_por_id=str(legacy_app.legacy_ids["foreign"]),
                  criado_em="1900-01-01", atualizado_por_id=str(legacy_app.legacy_ids["foreign"]))
    assert client.post(f"/{kind}/nova", data=dados).status_code == 302
    with legacy_app.app_context():
        row = db.session.query(_model(kind)).one()
        assert row.criado_por_id == legacy_app.legacy_ids["admin"]
        assert row.responsavel_usuario_id == legacy_app.legacy_ids["executor"]
        assert row.responsavel == "Nome executor"
        assert row.criado_em != "1900-01-01"
        assert row.atualizado_por_id is None
        criado_em = row.criado_em
    dados["observacao"] = "Revisão do gerente"
    assert _login(legacy_app, "manager").post(f"/{kind}/{_record(legacy_app, kind)}/editar", data=dados).status_code == 302
    with legacy_app.app_context():
        row = db.session.query(_model(kind)).one()
        assert row.criado_por_id == legacy_app.legacy_ids["admin"]
        assert row.criado_em == criado_em
        assert row.atualizado_por_id == legacy_app.legacy_ids["manager"]
        assert row.atualizado_em


@pytest.mark.parametrize("kind", ["aplicacoes", "colheita"])
@pytest.mark.parametrize("alias", ["inactive", "revoked", "foreign"])
def test_responsavel_deve_ter_conta_e_vinculo_ativos(legacy_app, kind, alias):
    response = _login(legacy_app).post(f"/{kind}/nova", data=_data(
        legacy_app, kind, responsavel_usuario_id=str(legacy_app.legacy_ids[alias])))
    assert response.status_code == 400
    with legacy_app.app_context():
        assert db.session.query(_model(kind)).count() == 0


@pytest.mark.parametrize("kind", ["aplicacoes", "colheita"])
def test_worker_so_seleciona_propria_conta_mas_pode_registrar_texto(legacy_app, kind):
    client = _login(legacy_app, "worker")
    assert client.post(f"/{kind}/nova", data=_data(legacy_app, kind,
        responsavel_usuario_id=str(legacy_app.legacy_ids["executor"]))).status_code == 400
    assert client.post(f"/{kind}/nova", data=_data(legacy_app, kind,
        responsavel_usuario_id=str(legacy_app.legacy_ids["worker"]))).status_code == 302
    assert client.post(f"/{kind}/nova", data=_data(legacy_app, kind,
        responsavel="Pessoa sem conta", responsavel_usuario_id="")).status_code == 302
    with legacy_app.app_context():
        rows = db.session.query(_model(kind)).order_by(_model(kind).id).all()
        assert rows[0].responsavel_usuario_id == legacy_app.legacy_ids["worker"]
        assert rows[0].criado_por_id == legacy_app.legacy_ids["worker"]
        assert rows[1].responsavel_usuario_id is None
        assert rows[1].responsavel == "Pessoa sem conta"


@pytest.mark.parametrize("kind", ["aplicacoes", "colheita"])
def test_executor_inativo_depois_do_registro_preserva_snapshot_na_edicao(legacy_app, kind):
    dados = _data(legacy_app, kind, responsavel_usuario_id=str(legacy_app.legacy_ids["executor"]))
    assert _login(legacy_app).post(f"/{kind}/nova", data=dados).status_code == 302
    with legacy_app.app_context():
        user = db.session.get(Usuario, legacy_app.legacy_ids["executor"])
        user.ativo = False
        user.nome = "Nome posterior diferente"
        db.session.commit()
    dados["responsavel"] = "Não deve sobrescrever o snapshot"
    dados["observacao"] = "Outra observação"
    assert _login(legacy_app, "manager").post(f"/{kind}/{_record(legacy_app, kind)}/editar", data=dados).status_code == 302
    with legacy_app.app_context():
        row = db.session.query(_model(kind)).one()
        assert row.responsavel == "Nome executor"
        assert row.responsavel_usuario_id == legacy_app.legacy_ids["executor"]


@pytest.mark.parametrize("kind,campo", [("aplicacoes", "dose"), ("colheita", "quantidade")])
@pytest.mark.parametrize("valor", ["NaN", "inf", "-inf", "1e999", "0", "-2", "abc"])
def test_numeros_legados_invalidos_nao_persistem(legacy_app, kind, campo, valor):
    assert _login(legacy_app).post(f"/{kind}/nova", data=_data(
        legacy_app, kind, **{campo: valor})).status_code == 400
    with legacy_app.app_context():
        assert db.session.query(_model(kind)).count() == 0


@pytest.mark.parametrize("kind,campo", [("aplicacoes", "data_aplicacao"), ("colheita", "data_colheita")])
@pytest.mark.parametrize("valor", ["2026-02-30", "2026-2-01", "nao-e-data", ""])
def test_datas_invalidas_nao_persistem(legacy_app, kind, campo, valor):
    assert _login(legacy_app).post(f"/{kind}/nova", data=_data(
        legacy_app, kind, **{campo: valor})).status_code == 400
    with legacy_app.app_context():
        assert db.session.query(_model(kind)).count() == 0


@pytest.mark.parametrize("kind", ["aplicacoes", "colheita"])
@pytest.mark.parametrize("cg", ["cg_b", "inconsistent"])
def test_contexto_exige_cultura_e_area_no_mesmo_ambiente(legacy_app, kind, cg):
    assert _login(legacy_app).post(f"/{kind}/nova", data=_data(
        legacy_app, kind, cultura_gleba_id=str(legacy_app.legacy_ids[cg]))).status_code == 400
    with legacy_app.app_context():
        assert db.session.query(_model(kind)).count() == 0


@pytest.mark.parametrize("kind", ["aplicacoes", "colheita"])
def test_ids_enormes_nao_chegam_como_bind_ao_banco(legacy_app, kind):
    client = _login(legacy_app)
    huge = "9" * 5000
    assert client.post(f"/{kind}/nova", data=_data(legacy_app, kind,
        cultura_gleba_id=huge)).status_code == 400
    assert client.get(f"/{kind}/{2**80}/editar").status_code == 404
    assert client.post(f"/{kind}/{2**80}/remover").status_code == 404
    if kind == "aplicacoes":
        assert client.post("/aplicacoes/nova", data=_data(legacy_app,
            produto_base_id=huge)).status_code == 400


def test_dose_consumo_e_custo_manual_nao_usam_preco_catalogo(legacy_app):
    dados = _data(legacy_app, quantidade_utilizada="15,125", unidade_quantidade="L",
                  custo_unitario="1,25", moeda="BRL")
    assert _login(legacy_app).post("/aplicacoes/nova", data=dados).status_code == 302
    with legacy_app.app_context():
        row = AplicacaoInsumo.query.one()
        assert row.dose == 2.5 and row.unidade == "L/ha"
        assert row.quantidade_utilizada == Decimal("15.125000")
        assert row.unidade_quantidade == "L"
        assert row.custo_unitario == Decimal("1.250000")
        assert row.custo_total == Decimal("18.91")
        assert row.moeda == "BRL"
        assert row.origem_custo == "calculado_quantidade_unitario"
        assert FinanceiroLancamento.query.count() == 0
        assert ProdutoPreco.query.one().valor == 99999.99


def test_consumo_e_custos_ausentes_continuam_nulos(legacy_app):
    assert _login(legacy_app).post("/aplicacoes/nova", data=_data(legacy_app)).status_code == 302
    with legacy_app.app_context():
        row = AplicacaoInsumo.query.one()
        for campo in ("quantidade_utilizada", "unidade_quantidade", "custo_unitario",
                      "custo_total", "moeda", "origem_custo"):
            assert getattr(row, campo) is None
        assert FinanceiroLancamento.query.count() == 0


@pytest.mark.parametrize("extra", [
    {"quantidade_utilizada": "-1", "unidade_quantidade": "kg"},
    {"quantidade_utilizada": "NaN", "unidade_quantidade": "kg"},
    {"quantidade_utilizada": "1.0000001", "unidade_quantidade": "kg"},
    {"quantidade_utilizada": "1", "unidade_quantidade": ""},
    {"quantidade_utilizada": "2", "unidade_quantidade": "kg", "custo_unitario": "3", "custo_total": "5"},
    {"custo_total": "-1"}, {"custo_total": "inf"}, {"custo_total": "1", "moeda": "USD"},
])
def test_consumo_e_custo_invalidos_sao_atomicos(legacy_app, extra):
    assert _login(legacy_app).post("/aplicacoes/nova", data=_data(legacy_app, **extra)).status_code == 400
    with legacy_app.app_context():
        assert AplicacaoInsumo.query.count() == 0
        assert FinanceiroLancamento.query.count() == 0


@pytest.mark.parametrize("alias", ["manager", "worker"])
@pytest.mark.parametrize("campo", ["custo_unitario", "custo_total", "moeda", "origem_custo"])
def test_campos_de_custo_forjados_sao_negados_no_backend(legacy_app, alias, campo):
    assert _login(legacy_app, alias).post("/aplicacoes/nova", data=_data(
        legacy_app, **{campo: ""})).status_code == 403
    with legacy_app.app_context():
        assert AplicacaoInsumo.query.count() == 0


def test_gerente_preserva_custo_mas_nao_altera_base_custeada(legacy_app):
    dados = _data(legacy_app, quantidade_utilizada="3", unidade_quantidade="kg", custo_unitario="2.50")
    assert _login(legacy_app).post("/aplicacoes/nova", data=dados).status_code == 302
    rid = _record(legacy_app, "aplicacoes")
    dados.pop("custo_unitario")
    dados["observacao"] = "Gerente revisou a observação"
    manager = _login(legacy_app, "manager")
    assert manager.post(f"/aplicacoes/{rid}/editar", data=dados).status_code == 302
    dados["quantidade_utilizada"] = "4"
    assert manager.post(f"/aplicacoes/{rid}/editar", data=dados).status_code == 403
    with legacy_app.app_context():
        row = db.session.get(AplicacaoInsumo, rid)
        assert row.quantidade_utilizada == Decimal("3")
        assert row.custo_total == Decimal("7.50")
        assert row.custo_unitario == Decimal("2.50")
        assert row.observacao == "Gerente revisou a observação"


@pytest.mark.parametrize("kind", ["aplicacoes", "colheita"])
def test_envio_repetido_identico_nao_duplica_mas_payload_diferente_conflita(legacy_app, kind):
    client = _login(legacy_app)
    dados = _data(legacy_app, kind, chave_envio=str(uuid4()))
    assert client.post(f"/{kind}/nova", data=dados).status_code == 302
    assert client.post(f"/{kind}/nova", data=dados).status_code == 302
    dados["observacao"] = "Outro conteúdo"
    assert client.post(f"/{kind}/nova", data=dados).status_code == 409
    with legacy_app.app_context():
        assert db.session.query(_model(kind)).count() == 1
        assert LogAuditoria.query.filter_by(acao=f"{kind}.create").count() == 1


@pytest.mark.parametrize("kind", ["aplicacoes", "colheita"])
def test_chave_de_outro_autor_nao_redireciona_para_registro(legacy_app, kind):
    dados = _data(legacy_app, kind, chave_envio=str(uuid4()))
    assert _login(legacy_app).post(f"/{kind}/nova", data=dados).status_code == 302
    assert _login(legacy_app, "manager").post(f"/{kind}/nova", data=dados).status_code == 409
    with legacy_app.app_context():
        assert db.session.query(_model(kind)).count() == 1


@pytest.mark.parametrize("kind", ["aplicacoes", "colheita"])
def test_edicao_de_registro_preexistente_nao_inventa_autoria(legacy_app, kind):
    with legacy_app.app_context():
        args = {"cultura_gleba_id": legacy_app.legacy_ids["cg"], "criado_em": "2020-01-01T00:00:00"}
        if kind == "aplicacoes":
            args.update(produto_base_id=legacy_app.legacy_ids["produto"], data_aplicacao="2020-01-01", responsavel="Nome histórico")
        else:
            args.update(data_colheita="2020-01-01")
        row = _model(kind)(**args)
        db.session.add(row)
        db.session.commit()
        rid = row.id
    dados = _data(legacy_app, kind, responsavel="Nome histórico")
    assert _login(legacy_app, "manager").post(f"/{kind}/{rid}/editar", data=dados).status_code == 302
    with legacy_app.app_context():
        row = db.session.get(_model(kind), rid)
        assert row.criado_por_id is None
        assert row.criado_em == "2020-01-01T00:00:00"
        assert row.atualizado_por_id == legacy_app.legacy_ids["manager"]


@pytest.mark.parametrize("cancelada", [False, True])
@pytest.mark.parametrize("tem_cultura", [False, True])
def test_atividade_inclusive_cancelada_bloqueia_exclusao_da_area(legacy_app, cancelada, tem_cultura):
    with legacy_app.app_context():
        row = AtividadeOperacional(
            gleba_id=legacy_app.legacy_ids["gleba"] if tem_cultura else legacy_app.legacy_ids["empty_gleba"],
            cultura_gleba_id=legacy_app.legacy_ids["cg"] if tem_cultura else None,
            tipo_atividade="Inspeção informada", data_execucao="2026-05-10",
            cancelado_em="2026-05-11T00:00:00" if cancelada else None)
        db.session.add(row)
        db.session.commit()
        rid, gid = row.id, row.gleba_id
    response = _login(legacy_app).post(f"/glebas/{gid}/remover", follow_redirects=True)
    assert response.status_code == 200
    assert b"dados hist" in response.data
    with legacy_app.app_context():
        assert db.session.get(Gleba, gid)
        assert db.session.get(AtividadeOperacional, rid)


@pytest.mark.parametrize("cancelada", [False, True])
def test_atividade_bloqueia_desassociacao_e_exclusao_da_cultura(legacy_app, cancelada):
    with legacy_app.app_context():
        # Remove apenas a fixture inconsistente, para isolar o bloqueio de histórico.
        db.session.delete(db.session.get(CulturaGleba, legacy_app.legacy_ids["inconsistent"]))
        row = AtividadeOperacional(gleba_id=legacy_app.legacy_ids["gleba"],
            cultura_gleba_id=legacy_app.legacy_ids["cg"], tipo_atividade="Inspeção",
            data_execucao="2026-05-10", cancelado_em="2026-05-11" if cancelada else None)
        db.session.add(row)
        db.session.commit()
    client = _login(legacy_app)
    cid = legacy_app.legacy_ids["cultura"]
    assert client.post(f"/culturas/{cid}/editar", data={"nome": "Não alterar"}).status_code == 400
    assert client.post(f"/culturas/{cid}/remover", follow_redirects=True).status_code == 200
    with legacy_app.app_context():
        assert db.session.get(CulturaGleba, legacy_app.legacy_ids["cg"])
        assert db.session.get(Cultura, cid).nome == "Cultura local"
