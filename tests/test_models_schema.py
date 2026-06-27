"""Testes do schema SQLAlchemy (Etapa 4.1).

Usam ``create_app('testing')`` (via fixture ``app``) e SQLite em memória. Não
importam seed nem dependem de arquivo .db. Usam o fixture ``app`` para garantir
que os modelos já foram importados/registrados antes de inspecionar o metadata.
"""
import pytest
from sqlalchemy import inspect

from app.extensions import db

TABELAS_ESPERADAS = {
    "usuario",
    "propriedade",
    "equipe_membro",
    "cultura",
    "gleba",
    "cultura_gleba",
    "aplicacao_insumo",
    "colheita_registro",
    "produto_base",
    "produto_tecnico",
    "produto_preco",
    "produto_imagem",
    "financeiro_lancamento",
    "upload_arquivo",
    "ia_interacao",
}


def test_todas_as_tabelas_registradas(app):
    """Todas as 15 tabelas esperadas estão registradas no metadata."""
    tabelas = set(db.metadata.tables.keys())
    faltando = TABELAS_ESPERADAS - tabelas
    assert not faltando, f"tabelas ausentes: {faltando}"


@pytest.mark.parametrize(
    "tabela,coluna",
    [
        ("usuario", "email"),
        ("produto_base", "slug"),
        ("produto_base", "status_regulatorio"),
        ("produto_preco", "status_validacao"),
        ("produto_imagem", "status_validacao"),
    ],
)
def test_colunas_principais(app, tabela, coluna):
    assert coluna in db.metadata.tables[tabela].columns


def test_create_all_em_memoria(app):
    """db.create_all() funciona no ambiente de teste (SQLite em memória)."""
    with app.app_context():
        db.create_all()
        insp = inspect(db.engine)
        nomes = set(insp.get_table_names())
        assert TABELAS_ESPERADAS.issubset(nomes)


def test_insercao_minima(app):
    """Insere registros mínimos sem depender de seed nem de arquivo .db."""
    from app.models import Usuario, Propriedade, ProdutoBase, ProdutoTecnico

    with app.app_context():
        db.create_all()

        u = Usuario(nome="Teste", email="teste@example.com",
                    senha_hash="x", perfil="produtor")
        db.session.add(u)
        db.session.commit()

        p = Propriedade(usuario_id=u.id, nome="Fazenda Teste")
        db.session.add(p)
        db.session.commit()

        prod = ProdutoBase(
            nome="Glifosato", slug="glifosato", classe="defensivo",
            categoria="herbicida", status_sistema="pre_cadastrado",
            status_regulatorio="nao_validado_agrofit",
        )
        db.session.add(prod)
        db.session.commit()

        tec = ProdutoTecnico(produto_id=prod.id, grupo_quimico="Glicina substituída")
        db.session.add(tec)
        db.session.commit()

        assert u.id is not None
        assert p.usuario_id == u.id
        assert prod.slug == "glifosato"
        assert tec.produto.id == prod.id
        assert prod.tecnicos[0].id == tec.id
