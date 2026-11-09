"""Integração HTTP da Etapa 06: autorização, itens, custos e histórico.

As bases SQLite em memória são exclusivas de cada teste. Os registros são
criados pelas rotas reais, salvo fixtures de cadastro e corrupção deliberada.
"""
from decimal import Decimal
import re
from uuid import uuid4

import pytest
from werkzeug.datastructures import MultiDict

from app.extensions import db
from app.models import (AplicacaoInsumo, AtividadeItem, AtividadeOperacional,
                        ColheitaRegistro, Cultura, CulturaGleba,
                        FinanceiroLancamento, Gleba, LogAuditoria, ProdutoBase,
                        ProdutoPreco, Usuario, UsuarioPropriedade)
from app.utils.auth import gerar_hash_senha
from tests.factories import criar_propriedade_com_vinculo, vincular_usuario_propriedade


_SENHA_HASH = gerar_hash_senha("senha-operacional-teste")


@pytest.fixture
def operacional(app):
    with app.app_context():
        db.create_all()
        pessoas = {}
        for perfil, nome in (("admin", "Administradora local"),
                             ("tecnico", "Gerente local"),
                             ("trabalhador", "Trabalhador local"),
                             ("externo", "Conta externa reservada"),
                             ("inativo", "Conta globalmente inativa"),
                             ("vinculo_inativo", "Conta sem vínculo ativo")):
            usuario = Usuario(nome=nome, email=f"{perfil}@operacional.test",
                              perfil="admin" if perfil == "externo" else
                                     (perfil if perfil in {"admin", "tecnico", "trabalhador"} else "trabalhador"),
                              senha_hash=_SENHA_HASH, ativo=perfil != "inativo")
            db.session.add(usuario)
            pessoas[perfil] = usuario
        db.session.flush()
        prop = criar_propriedade_com_vinculo(pessoas["admin"].id, nome="Fazenda local")
        externa = criar_propriedade_com_vinculo(pessoas["externo"].id, nome="Fazenda externa reservada")
        for perfil in ("tecnico", "trabalhador", "inativo", "vinculo_inativo"):
            vincular_usuario_propriedade(pessoas[perfil].id, prop.id, ativo=perfil != "vinculo_inativo")
        gleba = Gleba(propriedade_id=prop.id, nome="Área Norte", area_ha=21.5,
                      poligono_geojson='{"type":"Polygon","coordinates":[[[0,0],[1,0],[1,1],[0,0]]]}')
        outra_gleba = Gleba(propriedade_id=prop.id, nome="Área Sul", area_ha=7)
        gleba_externa = Gleba(propriedade_id=externa.id, nome="Área externa reservada")
        cultura = Cultura(propriedade_id=prop.id, nome="Milho", status="em_andamento")
        cultura_externa = Cultura(propriedade_id=externa.id, nome="Cultura externa reservada")
        produtos = [ProdutoBase(nome="Produto local A", slug="produto-operacional-a", classe="fertilizante",
                                status_regulatorio="tipo_tecnico_generico"),
                    ProdutoBase(nome="Produto local B", slug="produto-operacional-b", classe="defensivo")]
        db.session.add_all([gleba, outra_gleba, gleba_externa, cultura, cultura_externa, *produtos])
        db.session.flush()
        cg = CulturaGleba(cultura_id=cultura.id, gleba_id=gleba.id)
        cg_sul = CulturaGleba(cultura_id=cultura.id, gleba_id=outra_gleba.id)
        cg_externo = CulturaGleba(cultura_id=cultura_externa.id, gleba_id=gleba_externa.id)
        db.session.add_all([cg, cg_sul, cg_externo])
        db.session.commit()
        ids = {perfil: pessoa.id for perfil, pessoa in pessoas.items()}
        ids.update(propriedade=prop.id, externa=externa.id, gleba=gleba.id,
                   outra_gleba=outra_gleba.id, gleba_externa=gleba_externa.id,
                   cultura=cultura.id, cultura_externa=cultura_externa.id,
                   cg=cg.id, cg_sul=cg_sul.id, cg_externo=cg_externo.id,
                   produto=produtos[0].id, produto_b=produtos[1].id)
    return app, ids


def _login(operacional, perfil="admin"):
    app, ids = operacional
    client = app.test_client()
    resposta = client.post("/auth/login", data={"email": f"{perfil}@operacional.test",
                                               "senha": "senha-operacional-teste"})
    assert resposta.status_code == 302
    with client.session_transaction() as sessao:
        sessao["propriedade_ativa_id"] = ids["externa" if perfil == "externo" else "propriedade"]
    return client


def _item(ids, **alteracoes):
    dados = {"item_id": "", "produto_base_id": str(ids["produto"]), "dose": "",
             "unidade_dose": "", "quantidade_utilizada": "1", "unidade_quantidade": "kg"}
    for campo, valor in alteracoes.items():
        dados[campo] = valor
    return dados


def _form(ids, itens=(), **alteracoes):
    dados = MultiDict({"gleba_id": str(ids["gleba"]), "cultura_gleba_id": str(ids["cg"]),
                       "tipo_atividade": "Adubação registrada", "data_execucao": "2026-11-08",
                       "responsavel": "Executora informada", "responsavel_usuario_id": "",
                       "observacao": "Registro operacional de teste", "chave_envio": uuid4().hex})
    for campo, valor in alteracoes.items():
        dados[campo] = valor
    # O navegador envia uma posição em cada coluna, inclusive campos vazios.
    campos_item = sorted({campo for item in itens for campo in item})
    for item in itens:
        for campo in campos_item:
            dados.add(campo, item.get(campo, ""))
    return dados


def _criar(client, ids, itens=(), **alteracoes):
    resposta = client.post("/atividades/nova", data=_form(ids, itens, **alteracoes))
    assert resposta.status_code == 302, resposta.get_data(as_text=True)[-3000:]


def _registro(operacional):
    app, _ = operacional
    with app.app_context():
        atividade = AtividadeOperacional.query.order_by(AtividadeOperacional.id.desc()).first()
        return atividade.id


def _snapshot(operacional, atividade_id):
    app, _ = operacional
    with app.app_context():
        atividade = db.session.get(AtividadeOperacional, atividade_id)
        return ({col.name: getattr(atividade, col.name) for col in AtividadeOperacional.__table__.columns},
                [{col.name: getattr(item, col.name) for col in AtividadeItem.__table__.columns}
                 for item in atividade.itens])


@pytest.mark.parametrize("url", ["/atividades/", "/atividades/nova", "/atividades/1/editar"])
def test_atividades_exigem_login(operacional, url):
    resposta = operacional[0].test_client().get(url)
    assert resposta.status_code == 302
    assert "/auth/login" in resposta.headers["Location"]


@pytest.mark.parametrize("perfil", ["admin", "tecnico", "trabalhador"])
def test_perfis_criam_visualizam_sem_produtos_e_sem_custo(operacional, perfil):
    app, ids = operacional
    client = _login(operacional, perfil)
    _criar(client, ids, cultura_gleba_id="", responsavel_usuario_id=str(ids[perfil]), responsavel="")
    with app.app_context():
        atividade = AtividadeOperacional.query.one()
        assert atividade.gleba_id == ids["gleba"]
        assert atividade.cultura_gleba_id is None
        assert atividade.criado_por_id == ids[perfil]
        assert atividade.responsavel_usuario_id == ids[perfil]
        assert atividade.itens == []
        assert atividade.criado_em and atividade.criado_em != atividade.data_execucao
        assert atividade.atualizado_por_id is None
    assert client.get("/atividades/").status_code == 200


def test_varios_itens_preservam_produto_dose_consumo_e_autoria(operacional):
    app, ids = operacional
    client = _login(operacional)
    _criar(client, ids, [_item(ids, dose="2,5", unidade_dose="L/ha", quantidade_utilizada="15,000001", unidade_quantidade="L"),
                        _item(ids, produto_base_id=str(ids["produto_b"]), quantidade_utilizada="3.75", unidade_quantidade="kg")],
           criado_por_id=str(ids["externo"]), responsavel_usuario_id=str(ids["trabalhador"]), responsavel="Não usar este nome")
    with app.app_context():
        atividade = AtividadeOperacional.query.one()
        assert atividade.criado_por_id == ids["admin"]
        assert atividade.responsavel_usuario_id == ids["trabalhador"]
        assert atividade.responsavel == "Trabalhador local"
        assert len(atividade.itens) == 2
        primeiro, segundo = atividade.itens
        assert primeiro.dose == Decimal("2.500000")
        assert primeiro.quantidade_utilizada == Decimal("15.000001")
        assert primeiro.unidade_dose == "L/ha" and primeiro.unidade_quantidade == "L"
        assert segundo.produto_base_id == ids["produto_b"]
        assert segundo.quantidade_utilizada == Decimal("3.750000")
        assert segundo.unidade_quantidade == "kg"
        assert FinanceiroLancamento.query.count() == AplicacaoInsumo.query.count() == ColheitaRegistro.query.count() == 0


@pytest.mark.parametrize("campo,referencia", [("gleba_id", "gleba_externa"),
                                               ("cultura_gleba_id", "cg_externo"),
                                               ("cultura_gleba_id", "cg_sul")])
def test_contexto_territorial_forjado_nao_cria_registro(operacional, campo, referencia):
    app, ids = operacional
    resposta = _login(operacional).post("/atividades/nova", data=_form(ids, **{campo: str(ids[referencia])}))
    assert resposta.status_code == 400
    with app.app_context():
        assert AtividadeOperacional.query.count() == AtividadeItem.query.count() == 0


@pytest.mark.parametrize("referencia", ["externo", "inativo", "vinculo_inativo"])
def test_responsavel_exige_conta_e_vinculo_ativos_locais(operacional, referencia):
    app, ids = operacional
    resposta = _login(operacional).post("/atividades/nova", data=_form(ids, responsavel_usuario_id=str(ids[referencia])))
    assert resposta.status_code == 400
    with app.app_context():
        assert AtividadeOperacional.query.count() == 0


def test_worker_so_seleciona_propria_conta_sem_diretorio_de_equipe(operacional):
    app, ids = operacional
    client = _login(operacional, "trabalhador")
    corpo = client.get("/atividades/nova").get_data(as_text=True)
    select = re.search(r'<select[^>]+name="responsavel_usuario_id"[^>]*>(.*?)</select>', corpo, re.S).group(1)
    assert "Trabalhador local" in select
    assert "Administradora local" not in select and "Gerente local" not in select
    assert "Conta externa reservada" not in corpo
    resposta = client.post("/atividades/nova", data=_form(ids, responsavel_usuario_id=str(ids["admin"])))
    assert resposta.status_code == 400
    with app.app_context():
        assert AtividadeOperacional.query.count() == 0


@pytest.mark.parametrize("campo,valor", [("tipo_atividade", ""), ("tipo_atividade", "A"*121),
                                         ("data_execucao", "2026-02-30"), ("data_execucao", "2026-2-1"),
                                         ("data_execucao", "não é data"), ("data_execucao", "2026-11-08T12:00:00"),
                                         ("responsavel", ""), ("responsavel", "R"*121),
                                         ("gleba_id", "99999999999999999999999999999"),
                                         ("cultura_gleba_id", "99999999999999999999999999999"),
                                         ("responsavel_usuario_id", "99999999999999999999999999999"),
                                         ("chave_envio", "chave inválida")])
def test_campos_invalidos_retornam_400_sem_persistencia_parcial(operacional, campo, valor):
    app, ids = operacional
    resposta = _login(operacional).post("/atividades/nova", data=_form(ids, [_item(ids)], **{campo: valor}))
    assert resposta.status_code == 400
    with app.app_context():
        assert AtividadeOperacional.query.count() == AtividadeItem.query.count() == 0


@pytest.mark.parametrize("campo", ["dose", "quantidade_utilizada"])
@pytest.mark.parametrize("valor", ["-1", "0", "NaN", "Infinity", "-Inf", "1e309", "texto", "0.0000001", "1000000000000"])
def test_dose_e_consumo_invalidos_sao_rejeitados(operacional, campo, valor):
    app, ids = operacional
    resposta = _login(operacional).post("/atividades/nova", data=_form(ids, [_item(ids, unidade_dose="L/ha", **{campo: valor})]))
    assert resposta.status_code == 400
    with app.app_context():
        assert AtividadeOperacional.query.count() == AtividadeItem.query.count() == 0


@pytest.mark.parametrize("alteracao", [{"quantidade_utilizada": "3", "unidade_quantidade": ""},
                                      {"dose": "2", "unidade_dose": ""},
                                      {"unidade_quantidade": "u"*21}, {"unidade_dose": "u"*21}])
def test_unidades_necessarias_e_limitadas(operacional, alteracao):
    app, ids = operacional
    assert _login(operacional).post("/atividades/nova", data=_form(ids, [_item(ids, **alteracao)])).status_code == 400
    with app.app_context():
        assert AtividadeItem.query.count() == 0


@pytest.mark.parametrize("status", ["status_sistema", "status_regulatorio"])
def test_produto_bloqueado_por_qualquer_status_nao_pode_ser_registrado(operacional, status):
    app, ids = operacional
    with app.app_context():
        setattr(db.session.get(ProdutoBase, ids["produto"]), status, "bloqueado_historico")
        db.session.commit()
    resposta = _login(operacional).post("/atividades/nova", data=_form(ids, [_item(ids)]))
    assert resposta.status_code == 400
    with app.app_context():
        assert AtividadeOperacional.query.count() == 0


@pytest.mark.parametrize("produto_id", ["999999", "2147483648", "9"*500, "texto"])
def test_produto_inexistente_ou_id_excessivo_nao_provoca_500(operacional, produto_id):
    app, ids = operacional
    resposta = _login(operacional).post("/atividades/nova", data=_form(ids, [_item(ids, produto_base_id=produto_id)]))
    assert resposta.status_code == 400
    with app.app_context():
        assert AtividadeOperacional.query.count() == 0


def test_item_invalido_impede_toda_atividade_e_preserva_formulario(operacional):
    app, ids = operacional
    resposta = _login(operacional).post("/atividades/nova", data=_form(ids, [
        _item(ids, quantidade_utilizada="123,456789"),
        _item(ids, produto_base_id=str(ids["produto_b"]), quantidade_utilizada="inválido")],
        tipo_atividade="Inspeção com observação preservada", observacao="Texto que precisa continuar no formulário"))
    assert resposta.status_code == 400
    corpo = resposta.get_data(as_text=True)
    assert "Inspeção com observação preservada" in corpo
    assert "Texto que precisa continuar no formulário" in corpo
    assert "123,456789" in corpo and "inválido" in corpo
    assert 'aria-invalid="true"' in corpo
    with app.app_context():
        assert AtividadeOperacional.query.count() == AtividadeItem.query.count() == 0


def test_limite_itens_e_listas_desalinhadas_nao_truncam_dados(operacional):
    app, ids = operacional
    client = _login(operacional)
    assert client.post("/atividades/nova", data=_form(ids, [_item(ids) for _ in range(21)])).status_code == 400
    dados = _form(ids, [_item(ids), _item(ids)])
    dados.setlist("dose", ["1"])
    assert client.post("/atividades/nova", data=dados).status_code == 400
    with app.app_context():
        assert AtividadeOperacional.query.count() == AtividadeItem.query.count() == 0


def test_custos_desconhecidos_nao_usam_preco_catalogo_nem_geram_financeiro(operacional):
    app, ids = operacional
    with app.app_context():
        db.session.add(ProdutoPreco(produto_id=ids["produto"], valor=987654.32, moeda="BRL",
                                   unidade="kg", status_validacao="nao_consolidado"))
        db.session.commit()
    client = _login(operacional)
    _criar(client, ids, [_item(ids, dose="2", unidade_dose="L/ha", quantidade_utilizada="", unidade_quantidade="",
                             custo_unitario="", custo_total="", moeda="BRL")])
    with app.app_context():
        item = AtividadeItem.query.one()
        assert item.dose == Decimal("2")
        assert item.quantidade_utilizada is None
        assert item.custo_unitario is item.custo_total is item.moeda is item.origem_custo is None
        assert FinanceiroLancamento.query.count() == 0
        assert ProdutoPreco.query.one().valor == 987654.32


@pytest.mark.parametrize("quantidade,unitario,total", [("3", "0,335", "1.01"),
                                                       ("1", "0.005", "0.01"),
                                                       ("0.1", "0.2", "0.02"),
                                                       ("123,456789", "2.000001", "246.91")])
def test_calculo_monetario_exato_com_arredondamento_comercial(operacional, quantidade, unitario, total):
    app, ids = operacional
    _criar(_login(operacional), ids, [_item(ids, quantidade_utilizada=quantidade, custo_unitario=unitario,
                                         custo_total="", moeda="BRL")])
    with app.app_context():
        item = AtividadeItem.query.one()
        assert item.quantidade_utilizada == Decimal(quantidade.replace(",", "."))
        assert item.custo_unitario == Decimal(unitario.replace(",", "."))
        assert item.custo_total == Decimal(total)
        assert item.origem_custo == "calculado_quantidade_unitario"
        assert item.moeda == "BRL"
        assert FinanceiroLancamento.query.count() == 0


@pytest.mark.parametrize("valor", ["0", "87654321,09"])
def test_custo_total_informado_sem_unitario_nao_e_inventado(operacional, valor):
    app, ids = operacional
    _criar(_login(operacional), ids, [_item(ids, custo_total=valor, moeda="BRL")])
    with app.app_context():
        item = AtividadeItem.query.one()
        assert item.custo_total == Decimal(valor.replace(",", "."))
        assert item.custo_unitario is None
        assert item.origem_custo == "informado_usuario"


@pytest.mark.parametrize("alteracao", [{"custo_total": "-1"}, {"custo_unitario": "NaN"},
                                      {"custo_total": "Inf"}, {"custo_total": "1.001"},
                                      {"custo_unitario": "1.0000001"}, {"moeda": "USD", "custo_total": "1"},
                                      {"quantidade_utilizada": "3", "custo_unitario": "2", "custo_total": "7"},
                                      {"quantidade_utilizada": "999999999999", "custo_unitario": "999999999999"}])
def test_custo_invalido_ou_total_inconsistente_nao_salva(operacional, alteracao):
    app, ids = operacional
    resposta = _login(operacional).post("/atividades/nova", data=_form(ids, [_item(ids, **alteracao)]))
    assert resposta.status_code == 400
    with app.app_context():
        assert AtividadeOperacional.query.count() == AtividadeItem.query.count() == 0


@pytest.mark.parametrize("perfil", ["tecnico", "trabalhador"])
@pytest.mark.parametrize("campo,valor", [("custo_unitario", "1"), ("custo_total", "1"), ("moeda", "BRL")])
def test_custos_forjados_sao_negados_no_backend(operacional, perfil, campo, valor):
    app, ids = operacional
    resposta = _login(operacional, perfil).post("/atividades/nova", data=_form(ids, [_item(ids, **{campo: valor})]))
    assert resposta.status_code == 403
    with app.app_context():
        assert AtividadeOperacional.query.count() == AtividadeItem.query.count() == 0


def test_worker_nao_recebe_valores_de_custo_nem_controles_de_edicao(operacional):
    app, ids = operacional
    _criar(_login(operacional), ids, [_item(ids, custo_total="87654321.09", moeda="BRL")])
    aid = _registro(operacional)
    client = _login(operacional, "trabalhador")
    for url in ("/atividades/", "/atividades/nova"):
        corpo = client.get(url).get_data(as_text=True)
        assert "87654321" not in corpo
        assert 'name="custo_unitario"' not in corpo and 'name="custo_total"' not in corpo
        assert f'/atividades/{aid}/editar' not in corpo and f'/atividades/{aid}/cancelar' not in corpo
    assert client.get(f"/atividades/{aid}/editar").status_code == 403
    assert client.post(f"/atividades/{aid}/editar", data=_form(ids)).status_code == 403
    assert client.post(f"/atividades/{aid}/cancelar").status_code == 403


def test_gerente_edita_sem_alterar_custo_ou_autor_e_nao_cancela(operacional):
    app, ids = operacional
    _criar(_login(operacional), ids, [_item(ids, custo_total="87654321.09", moeda="BRL")],
           responsavel_usuario_id=str(ids["trabalhador"]))
    aid = _registro(operacional)
    antes, itens = _snapshot(operacional, aid)
    item = itens[0]
    client = _login(operacional, "tecnico")
    corpo = client.get(f"/atividades/{aid}/editar").get_data(as_text=True)
    assert "87654321" in corpo
    assert 'name="custo_total"' not in corpo and 'name="custo_unitario"' not in corpo
    resposta = client.post(f"/atividades/{aid}/editar", data=_form(ids, [_item(ids, item_id=str(item["id"]))],
                          observacao="Observação alterada pelo gerente", responsavel_usuario_id=str(ids["trabalhador"])))
    assert resposta.status_code == 302
    depois, novos_itens = _snapshot(operacional, aid)
    assert depois["observacao"] == "Observação alterada pelo gerente"
    assert depois["criado_por_id"] == antes["criado_por_id"] == ids["admin"]
    assert depois["criado_em"] == antes["criado_em"]
    assert depois["atualizado_por_id"] == ids["tecnico"] and depois["atualizado_em"]
    assert novos_itens == itens
    assert client.post(f"/atividades/{aid}/cancelar").status_code == 403


@pytest.mark.parametrize("mudanca", ["quantidade", "unidade", "produto", "remocao"])
def test_gerente_nao_altera_base_nem_remove_item_com_custo(operacional, mudanca):
    app, ids = operacional
    _criar(_login(operacional), ids, [_item(ids, custo_total="15.50", moeda="BRL")])
    aid = _registro(operacional)
    antes = _snapshot(operacional, aid)
    linha = _item(ids, item_id=str(antes[1][0]["id"]))
    if mudanca == "quantidade":
        linha["quantidade_utilizada"] = "2"
    elif mudanca == "unidade":
        linha["unidade_quantidade"] = "L"
    elif mudanca == "produto":
        linha["produto_base_id"] = str(ids["produto_b"])
    itens = [] if mudanca == "remocao" else [linha]
    resposta = _login(operacional, "tecnico").post(f"/atividades/{aid}/editar", data=_form(ids, itens))
    assert resposta.status_code == 403
    assert _snapshot(operacional, aid) == antes


def test_gerente_pode_editar_base_de_item_sem_custo(operacional):
    app, ids = operacional
    _criar(_login(operacional, "tecnico"), ids, [_item(ids)])
    aid = _registro(operacional)
    _, itens = _snapshot(operacional, aid)
    resposta = _login(operacional, "tecnico").post(f"/atividades/{aid}/editar", data=_form(ids, [
        _item(ids, item_id=str(itens[0]["id"]), quantidade_utilizada="2,125", unidade_quantidade="L")]))
    assert resposta.status_code == 302
    _, novos = _snapshot(operacional, aid)
    assert novos[0]["quantidade_utilizada"] == Decimal("2.125") and novos[0]["unidade_quantidade"] == "L"
    assert novos[0]["custo_total"] is None


def test_edicao_invalida_nao_altera_cabecalho_nem_itens(operacional):
    app, ids = operacional
    client = _login(operacional)
    _criar(client, ids, [_item(ids)])
    aid = _registro(operacional)
    antes = _snapshot(operacional, aid)
    resposta = client.post(f"/atividades/{aid}/editar", data=_form(ids, [
        _item(ids, item_id=str(antes[1][0]["id"]), quantidade_utilizada="3"),
        _item(ids, quantidade_utilizada="NaN")], tipo_atividade="Não pode persistir"))
    assert resposta.status_code == 400
    assert _snapshot(operacional, aid) == antes


def test_edicao_nao_transfere_atividade_para_outra_propriedade(operacional):
    app, ids = operacional
    client = _login(operacional)
    _criar(client, ids, [_item(ids)])
    aid = _registro(operacional)
    antes = _snapshot(operacional, aid)
    resposta = client.post(f"/atividades/{aid}/editar", data=_form(ids, gleba_id=str(ids["gleba_externa"]),
                                                                       cultura_gleba_id=str(ids["cg_externo"])))
    assert resposta.status_code == 400
    assert _snapshot(operacional, aid) == antes


def test_ids_de_item_externo_ou_duplicado_sao_recusados(operacional):
    app, ids = operacional
    client = _login(operacional)
    _criar(client, ids, [_item(ids)])
    primeiro = _registro(operacional)
    primeiro_antes = _snapshot(operacional, primeiro)
    item_a = primeiro_antes[1][0]["id"]
    _criar(client, ids, [_item(ids, produto_base_id=str(ids["produto_b"]))])
    segundo = _registro(operacional)
    segundo_antes = _snapshot(operacional, segundo)
    assert client.post(f"/atividades/{segundo}/editar", data=_form(ids, [_item(ids, item_id=str(item_a))])).status_code == 400
    dados = _form(ids, [_item(ids, item_id=str(item_a)), _item(ids, item_id=str(item_a))])
    assert client.post(f"/atividades/{primeiro}/editar", data=dados).status_code == 400
    assert _snapshot(operacional, primeiro) == primeiro_antes
    assert _snapshot(operacional, segundo) == segundo_antes


@pytest.mark.parametrize("acao", ["editar", "cancelar"])
def test_outro_contexto_nao_consulta_nem_modifica_atividade(operacional, acao):
    app, ids = operacional
    _criar(_login(operacional), ids, [_item(ids)])
    aid = _registro(operacional)
    antes = _snapshot(operacional, aid)
    externo = _login(operacional, "externo")
    assert "Adubação registrada" not in externo.get("/atividades/").get_data(as_text=True)
    if acao == "editar":
        assert externo.get(f"/atividades/{aid}/editar").status_code == 404
    assert externo.post(f"/atividades/{aid}/{acao}", data=_form(ids)).status_code == 404
    assert _snapshot(operacional, aid) == antes


@pytest.mark.parametrize("acao", ["editar", "cancelar"])
def test_id_de_rota_excessivo_retorna_404(operacional, acao):
    resposta = _login(operacional).post(f"/atividades/{'9'*100}/{acao}", data={})
    assert resposta.status_code == 404


def test_idempotencia_reenvio_igual_nao_duplica_e_diferente_retorna_409(operacional):
    app, ids = operacional
    client = _login(operacional)
    dados = _form(ids, [_item(ids, custo_unitario="1.005", custo_total="", moeda="BRL")])
    assert client.post("/atividades/nova", data=dados).status_code == 302
    aid = _registro(operacional)
    antes = _snapshot(operacional, aid)
    assert client.post("/atividades/nova", data=dados).status_code == 302
    alterados = dados.copy()
    alterados["tipo_atividade"] = "Outra atividade com a mesma chave"
    assert client.post("/atividades/nova", data=alterados).status_code == 409
    assert _snapshot(operacional, aid) == antes
    with app.app_context():
        assert AtividadeOperacional.query.count() == AtividadeItem.query.count() == 1
        assert LogAuditoria.query.filter_by(acao="atividades.create").count() == 1


def test_chave_de_envio_de_outro_autor_nao_reaproveita_registro(operacional):
    app, ids = operacional
    dados = _form(ids)
    assert _login(operacional).post("/atividades/nova", data=dados).status_code == 302
    assert _login(operacional, "tecnico").post("/atividades/nova", data=dados).status_code == 409
    with app.app_context():
        assert AtividadeOperacional.query.count() == 1


def test_cancelamento_e_remocao_de_item_preservam_historico_auditoria(operacional):
    app, ids = operacional
    client = _login(operacional)
    _criar(client, ids, [_item(ids), _item(ids, produto_base_id=str(ids["produto_b"]), custo_total="19.99", moeda="BRL")])
    aid = _registro(operacional)
    _, anteriores = _snapshot(operacional, aid)
    restante = anteriores[0]
    assert client.post(f"/atividades/{aid}/editar", data=_form(ids, [
        _item(ids, item_id=str(restante["id"]))])).status_code == 302
    _, itens = _snapshot(operacional, aid)
    assert len(itens) == 2 and itens[1]["cancelado_em"] and itens[1]["cancelado_por_id"] == ids["admin"]
    assert itens[1]["custo_total"] == Decimal("19.99")
    assert client.post(f"/atividades/{aid}/cancelar").status_code == 302
    assert client.post(f"/atividades/{aid}/cancelar").status_code == 302
    depois, itens_finais = _snapshot(operacional, aid)
    assert depois["cancelado_em"] and depois["cancelado_por_id"] == ids["admin"]
    assert itens_finais == itens
    assert client.get(f"/atividades/{aid}/editar").status_code == 409
    with app.app_context():
        assert AtividadeOperacional.query.count() == 1 and AtividadeItem.query.count() == 2
        eventos = LogAuditoria.query.filter(LogAuditoria.acao.like("atividades.%")).order_by(LogAuditoria.id).all()
        assert [log.acao for log in eventos] == ["atividades.create", "atividades.edit", "atividades.cancel"]
        assert all(log.usuario_id == ids["admin"] and log.propriedade_id == ids["propriedade"] and log.entidade_id == aid for log in eventos)
        assert all("19.99" not in (log.descricao or "") and "csrf" not in (log.descricao or "") for log in eventos)


def test_responsavel_historico_inativado_nao_e_reassociado_ou_renomeado(operacional):
    app, ids = operacional
    client = _login(operacional)
    _criar(client, ids, responsavel_usuario_id=str(ids["trabalhador"]), responsavel="")
    aid = _registro(operacional)
    with app.app_context():
        usuario = db.session.get(Usuario, ids["trabalhador"])
        usuario.nome = "Nome posterior que não deve substituir o histórico"
        usuario.ativo = False
        db.session.commit()
    assert client.post(f"/atividades/{aid}/editar", data=_form(ids, responsavel_usuario_id=str(ids["trabalhador"]),
                          responsavel="texto que não deve substituir o vínculo", observacao="Inspeção posterior")).status_code == 302
    depois, _ = _snapshot(operacional, aid)
    assert depois["responsavel_usuario_id"] == ids["trabalhador"]
    assert depois["responsavel"] == "Trabalhador local"


def test_csrf_real_exige_token_e_rejeita_token_de_contexto_anterior(operacional):
    app, ids = operacional
    app.config["WTF_CSRF_ENABLED"] = True
    client = app.test_client()
    login_html = client.get("/auth/login").get_data(as_text=True)
    token = re.search(r'name="csrf_token"[^>]*value="([^"]+)"', login_html).group(1)
    assert client.post("/auth/login", data={"email": "admin@operacional.test", "senha": "senha-operacional-teste",
                                            "csrf_token": token}).status_code == 302
    form_html = client.get("/atividades/nova").get_data(as_text=True)
    csrf = re.search(r'name="csrf_token"[^>]*value="([^"]+)"', form_html).group(1)
    chave = re.search(r'name="chave_envio"[^>]*value="([^"]+)"', form_html).group(1)
    dados = _form(ids, chave_envio=chave)
    assert client.post("/atividades/nova", data=dados).status_code == 400
    dados["csrf_token"] = "token adulterado"
    assert client.post("/atividades/nova", data=dados).status_code == 400
    dados["csrf_token"] = csrf
    assert client.post("/atividades/nova", data=dados).status_code == 302
    with app.app_context():
        vincular_usuario_propriedade(ids["admin"], ids["externa"])
        db.session.commit()
    assert client.post("/propriedades/selecionar", data={"propriedade_id": str(ids["externa"]), "csrf_token": csrf}).status_code == 302
    dados["chave_envio"] = uuid4().hex
    assert client.post("/atividades/nova", data=dados).status_code == 400
    with app.app_context():
        assert AtividadeOperacional.query.count() == 1


def test_revogacao_vinculo_impede_nova_operacao(operacional):
    app, ids = operacional
    client = _login(operacional, "trabalhador")
    assert client.get("/atividades/nova").status_code == 200
    with app.app_context():
        vinculo = UsuarioPropriedade.query.filter_by(usuario_id=ids["trabalhador"], propriedade_id=ids["propriedade"]).one()
        vinculo.ativo = False
        db.session.commit()
    resposta = client.post("/atividades/nova", data=_form(ids))
    assert resposta.status_code == 409
    with app.app_context():
        assert AtividadeOperacional.query.count() == 0


def test_dados_territoriais_e_catalogo_permanecem_intactos(operacional):
    app, ids = operacional
    with app.app_context():
        gleba = db.session.get(Gleba, ids["gleba"])
        antes = (gleba.area_ha, gleba.poligono_geojson)
        produto = db.session.get(ProdutoBase, ids["produto"])
        catalogo = (produto.nome, produto.status_sistema, produto.status_regulatorio)
    client = _login(operacional)
    _criar(client, ids, [_item(ids, quantidade_utilizada="15")])
    aid = _registro(operacional)
    assert client.post(f"/atividades/{aid}/cancelar").status_code == 302
    with app.app_context():
        gleba = db.session.get(Gleba, ids["gleba"])
        assert (gleba.area_ha, gleba.poligono_geojson) == antes
        produto = db.session.get(ProdutoBase, ids["produto"])
        assert (produto.nome, produto.status_sistema, produto.status_regulatorio) == catalogo
        assert Gleba.query.count() == 3 and CulturaGleba.query.count() == 3


def test_edicao_recalcula_custo_sem_reenviar_total_antigo_como_manual(operacional):
    app, ids = operacional
    client = _login(operacional)
    _criar(client, ids, [_item(ids, quantidade_utilizada="3", custo_unitario="0.335",
                             custo_total="", moeda="BRL")])
    aid = _registro(operacional)
    antes, itens = _snapshot(operacional, aid)
    html = client.get(f"/atividades/{aid}/editar").get_data(as_text=True)
    total_input = re.search(r'id="item-0-custo_total"[^>]*value="([^"]*)"', html)
    assert total_input is not None and total_input.group(1) == ""
    assert "recalculado ao salvar" in html
    resposta = client.post(f"/atividades/{aid}/editar", data=_form(ids, [
        _item(ids, item_id=str(itens[0]["id"]), quantidade_utilizada="6",
              custo_unitario="0.335", custo_total="", moeda="BRL")]))
    assert resposta.status_code == 302
    depois, novos = _snapshot(operacional, aid)
    assert depois["criado_em"] == antes["criado_em"]
    assert novos[0]["custo_total"] == Decimal("2.01")
    assert novos[0]["origem_custo"] == "calculado_quantidade_unitario"
    with app.app_context():
        assert FinanceiroLancamento.query.count() == 0


def test_falha_de_auditoria_atomica_nao_persiste_atividade_ou_itens(operacional, monkeypatch):
    from app.blueprints.atividades import routes

    app, ids = operacional
    client = _login(operacional)

    def falhar(*args, **kwargs):
        raise RuntimeError("Falha sintética de auditoria")

    monkeypatch.setattr(routes, "_auditar", falhar)
    with pytest.raises(RuntimeError, match="Falha sintética de auditoria"):
        client.post("/atividades/nova", data=_form(ids, [_item(ids), _item(ids)]))
    with app.app_context():
        assert AtividadeOperacional.query.count() == AtividadeItem.query.count() == 0
        assert LogAuditoria.query.filter_by(acao="atividades.create").count() == 0
