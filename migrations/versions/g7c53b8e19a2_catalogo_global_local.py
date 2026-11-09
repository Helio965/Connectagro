"""Catálogo local separado, revisões e autoridade global explicitamente habilitada.

Revision ID: g7c53b8e19a2
Revises: f6a28d9c104e
"""
from alembic import op
import sqlalchemy as sa

revision = "g7c53b8e19a2"
down_revision = "f6a28d9c104e"
branch_labels = None
depends_on = None


def _autoria():
    return [
        sa.Column("ativo", sa.Boolean(), nullable=False),
        sa.Column("versao", sa.Integer(), nullable=False),
        sa.Column("criado_por_id", sa.Integer(), sa.ForeignKey("usuario.id"), nullable=False),
        sa.Column("criado_em", sa.String(40), nullable=False),
        sa.Column("atualizado_por_id", sa.Integer(), sa.ForeignKey("usuario.id"), nullable=True),
        sa.Column("atualizado_em", sa.String(40), nullable=True),
    ]


def upgrade():
    # ADD COLUMN direto: não recriar Usuario/ProdutoImagem (pais com FKs) nem
    # atribuir proveniência de imagens ou autoridade a contas preexistentes.
    op.add_column("usuario", sa.Column("catalogo_global_aprovador", sa.Boolean(),
                                       nullable=False, server_default=sa.false()))
    op.add_column("produto_imagem", sa.Column("origem_seed", sa.String(150), nullable=True))
    op.add_column("produto_imagem", sa.Column("seed_fingerprint", sa.String(64), nullable=True))
    op.create_table("catalogo_controle", sa.Column("id", sa.Integer(), primary_key=True),
                    sa.CheckConstraint("id = 1", name="ck_catalogo_controle_singleton"))
    op.bulk_insert(sa.table("catalogo_controle", sa.column("id", sa.Integer())), [{"id": 1}])
    op.create_table(
        "produto_local",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("propriedade_id", sa.Integer(), sa.ForeignKey("propriedade.id"), nullable=False),
        sa.Column("nome", sa.String(150), nullable=False),
        sa.Column("classe", sa.String(30), nullable=False),
        sa.Column("categoria", sa.String(40), nullable=True),
        sa.Column("descricao_curta", sa.String(255), nullable=True),
        sa.Column("descricao_completa", sa.Text(), nullable=True),
        sa.Column("unidade_referencia", sa.String(20), nullable=True),
        sa.Column("observacoes", sa.Text(), nullable=True),
        sa.Column("fonte", sa.String(255), nullable=True),
        *_autoria(),
        sa.Column("chave_envio", sa.String(64), nullable=True),
        sa.CheckConstraint("versao >= 1", name="ck_produto_local_versao"),
        sa.UniqueConstraint("chave_envio", name="uq_produto_local_chave_envio"),
    )
    op.create_table(
        "produto_personalizacao",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("propriedade_id", sa.Integer(), sa.ForeignKey("propriedade.id"), nullable=False),
        sa.Column("produto_base_id", sa.Integer(), sa.ForeignKey("produto_base.id"), nullable=False),
        sa.Column("nome_local", sa.String(150), nullable=True),
        sa.Column("descricao_local", sa.Text(), nullable=True),
        sa.Column("unidade_referencia", sa.String(20), nullable=True),
        sa.Column("observacoes", sa.Text(), nullable=True),
        sa.Column("fonte", sa.String(255), nullable=True),
        *_autoria(),
        sa.UniqueConstraint("propriedade_id", "produto_base_id",
                            name="uq_produto_personalizacao_propriedade_produto"),
        sa.CheckConstraint("versao >= 1", name="ck_produto_personalizacao_versao"),
    )
    op.create_table(
        "catalogo_revisao",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("propriedade_id", sa.Integer(), sa.ForeignKey("propriedade.id"), nullable=False),
        sa.Column("produto_local_id", sa.Integer(), sa.ForeignKey("produto_local.id"), nullable=True),
        sa.Column("personalizacao_id", sa.Integer(), sa.ForeignKey("produto_personalizacao.id"), nullable=True),
        sa.Column("versao", sa.Integer(), nullable=False),
        sa.Column("snapshot_json", sa.Text(), nullable=False),
        sa.Column("alterado_por_id", sa.Integer(), sa.ForeignKey("usuario.id"), nullable=False),
        sa.Column("criado_em", sa.String(40), nullable=False),
        sa.Column("acao", sa.String(30), nullable=False),
        sa.CheckConstraint(
            "(produto_local_id IS NOT NULL AND personalizacao_id IS NULL) OR "
            "(produto_local_id IS NULL AND personalizacao_id IS NOT NULL)",
            name="ck_catalogo_revisao_origem"),
        sa.CheckConstraint("versao >= 1", name="ck_catalogo_revisao_versao"),
        sa.UniqueConstraint("produto_local_id", "versao", name="uq_catalogo_revisao_local_versao"),
        sa.UniqueConstraint("personalizacao_id", "versao", name="uq_catalogo_revisao_personalizacao_versao"),
    )
    op.create_table(
        "solicitacao_catalogo",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("propriedade_id", sa.Integer(), sa.ForeignKey("propriedade.id"), nullable=False),
        sa.Column("produto_local_id", sa.Integer(), sa.ForeignKey("produto_local.id"), nullable=True),
        sa.Column("personalizacao_id", sa.Integer(), sa.ForeignKey("produto_personalizacao.id"), nullable=True),
        sa.Column("tipo", sa.String(20), nullable=False),
        sa.Column("origem_versao", sa.Integer(), nullable=False),
        sa.Column("conteudo_json", sa.Text(), nullable=False),
        sa.Column("global_fingerprint", sa.String(64), nullable=True),
        sa.Column("estado", sa.String(20), nullable=False),
        sa.Column("solicitado_por_id", sa.Integer(), sa.ForeignKey("usuario.id"), nullable=False),
        sa.Column("solicitado_em", sa.String(40), nullable=False),
        sa.Column("decidido_por_id", sa.Integer(), sa.ForeignKey("usuario.id"), nullable=True),
        sa.Column("decidido_em", sa.String(40), nullable=True),
        sa.Column("justificativa", sa.Text(), nullable=True),
        sa.Column("produto_publicado_id", sa.Integer(), sa.ForeignKey("produto_base.id"), nullable=True),
        sa.Column("global_anterior_json", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "(produto_local_id IS NOT NULL AND personalizacao_id IS NULL) OR "
            "(produto_local_id IS NULL AND personalizacao_id IS NOT NULL)",
            name="ck_solicitacao_catalogo_origem"),
        sa.CheckConstraint("origem_versao >= 1", name="ck_solicitacao_catalogo_versao"),
        sa.UniqueConstraint("produto_local_id", "origem_versao", name="uq_solicitacao_catalogo_local_versao"),
        sa.UniqueConstraint("personalizacao_id", "origem_versao", name="uq_solicitacao_catalogo_personalizacao_versao"),
    )


def downgrade():
    bind = op.get_bind()
    # Todo o preflight antecede o primeiro DDL, inclusive decisão rejeitada,
    # registro inativo, zero/texto vazio e proveniência preenchida parcialmente.
    for nome in ("solicitacao_catalogo", "catalogo_revisao", "produto_personalizacao", "produto_local"):
        tabela = sa.table(nome, sa.column("id", sa.Integer()))
        if bind.execute(sa.select(1).select_from(tabela).limit(1)).first():
            raise RuntimeError("Downgrade bloqueado: há cadastros, personalizações, revisões ou solicitações de catálogo. Preserve o histórico em backup.")
    usuario = sa.table("usuario", sa.column("catalogo_global_aprovador", sa.Boolean()))
    if bind.execute(sa.select(1).select_from(usuario).where(
            usuario.c.catalogo_global_aprovador != sa.false()).limit(1)).first():
        raise RuntimeError("Downgrade bloqueado: há autoridade global de catálogo habilitada. Planeje a reversão sem perder permissões.")
    imagem = sa.table("produto_imagem", sa.column("origem_seed", sa.String()),
                      sa.column("seed_fingerprint", sa.String()))
    if bind.execute(sa.select(1).select_from(imagem).where(sa.or_(
            imagem.c.origem_seed.is_not(None), imagem.c.seed_fingerprint.is_not(None))).limit(1)).first():
        raise RuntimeError("Downgrade bloqueado: há proveniência de imagem cadastrada. Preserve os dados antes da reversão.")
    for nome in ("solicitacao_catalogo", "catalogo_revisao", "produto_personalizacao", "produto_local", "catalogo_controle"):
        op.drop_table(nome)
    op.drop_column("produto_imagem", "seed_fingerprint")
    op.drop_column("produto_imagem", "origem_seed")
    op.drop_column("usuario", "catalogo_global_aprovador")
