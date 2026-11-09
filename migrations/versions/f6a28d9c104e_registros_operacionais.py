"""Atividades gerais, consumo/custos opcionais e autoria operacional.

Revision ID: f6a28d9c104e
Revises: e4ca60b1d732
"""
from alembic import op
import sqlalchemy as sa

from app.utils.decimal_exato import DecimalExato

revision = "f6a28d9c104e"
down_revision = "e4ca60b1d732"
branch_labels = None
depends_on = None


def _autoria(tabela, responsavel_textual=False):
    campos = []
    if responsavel_textual:
        campos.append(sa.Column("responsavel", sa.String(120), nullable=True))
    for nome in ("responsavel_usuario_id", "criado_por_id", "atualizado_por_id"):
        campos.append(sa.Column(nome, sa.Integer(), sa.ForeignKey(
            "usuario.id", name=f"fk_{tabela}_{nome}_usuario"), nullable=True))
    campos.extend([
        sa.Column("atualizado_em", sa.String(40), nullable=True),
        sa.Column("chave_envio", sa.String(64), nullable=True),
    ])
    return campos


def _consumo():
    return [
        sa.Column("quantidade_utilizada", DecimalExato(18, 6), nullable=True),
        sa.Column("unidade_quantidade", sa.String(20), nullable=True),
        sa.Column("custo_unitario", DecimalExato(18, 6), nullable=True),
        sa.Column("custo_total", DecimalExato(18, 2), nullable=True),
        sa.Column("moeda", sa.String(3), nullable=True),
        sa.Column("origem_custo", sa.String(40), nullable=True),
    ]


def _colunas_legado():
    return {
        "aplicacao_insumo": _autoria("aplicacao_insumo") + _consumo(),
        "colheita_registro": _autoria("colheita_registro", responsavel_textual=True),
    }


def upgrade():
    # As duas tabelas existentes são folhas: não há FK de entrada. O batch
    # SQLite pode acrescentar FKs/UNIQUE sem desligar foreign_keys nem afetar
    # os pais Cultura/Gleba/Produto/Usuario. Nenhum backfill é executado.
    for tabela, colunas in _colunas_legado().items():
        with op.batch_alter_table(tabela) as batch:
            for coluna in colunas:
                batch.add_column(coluna)
            batch.create_unique_constraint(f"uq_{tabela}_chave_envio", ["chave_envio"])

    op.create_table(
        "atividade_operacional",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("gleba_id", sa.Integer(), sa.ForeignKey("gleba.id"), nullable=False),
        sa.Column("cultura_gleba_id", sa.Integer(), sa.ForeignKey("cultura_gleba.id"), nullable=True),
        sa.Column("tipo_atividade", sa.String(120), nullable=False),
        sa.Column("data_execucao", sa.String(40), nullable=False),
        sa.Column("responsavel", sa.String(120), nullable=True),
        sa.Column("responsavel_usuario_id", sa.Integer(), sa.ForeignKey("usuario.id"), nullable=True),
        sa.Column("observacao", sa.Text(), nullable=True),
        sa.Column("criado_por_id", sa.Integer(), sa.ForeignKey("usuario.id"), nullable=True),
        sa.Column("criado_em", sa.String(40), nullable=False),
        sa.Column("atualizado_por_id", sa.Integer(), sa.ForeignKey("usuario.id"), nullable=True),
        sa.Column("atualizado_em", sa.String(40), nullable=True),
        sa.Column("cancelado_por_id", sa.Integer(), sa.ForeignKey("usuario.id"), nullable=True),
        sa.Column("cancelado_em", sa.String(40), nullable=True),
        sa.Column("chave_envio", sa.String(64), nullable=True),
        sa.UniqueConstraint("chave_envio", name="uq_atividade_operacional_chave_envio"),
    )
    op.create_table(
        "atividade_item",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("atividade_id", sa.Integer(), sa.ForeignKey("atividade_operacional.id"), nullable=False),
        sa.Column("produto_base_id", sa.Integer(), sa.ForeignKey("produto_base.id"), nullable=False),
        sa.Column("dose", DecimalExato(18, 6), nullable=True),
        sa.Column("unidade_dose", sa.String(20), nullable=True),
        *_consumo(),
        sa.Column("cancelado_em", sa.String(40), nullable=True),
        sa.Column("cancelado_por_id", sa.Integer(), sa.ForeignKey("usuario.id"), nullable=True),
    )


def downgrade():
    bind = op.get_bind()
    # Preflight completo antes de qualquer DDL. Até texto vazio, custo zero ou
    # registro cancelado são dados: nenhuma forma é descartada silenciosamente.
    for nome in ("atividade_item", "atividade_operacional"):
        tabela = sa.table(nome, sa.column("id", sa.Integer()))
        if bind.execute(sa.select(1).select_from(tabela).limit(1)).first():
            raise RuntimeError("Downgrade bloqueado: há atividades operacionais/itens. "
                               "Preserve o histórico e planeje a reversão com backup.")
    colunas_legado = _colunas_legado()
    for nome, colunas in colunas_legado.items():
        tabela = sa.table(nome, *(sa.column(c.name, c.type) for c in colunas))
        if bind.execute(sa.select(1).select_from(tabela).where(sa.or_(
                *(c.is_not(None) for c in tabela.c))).limit(1)).first():
            raise RuntimeError("Downgrade bloqueado: há autoria, consumo ou custos "
                               "operacionais cadastrados. Preserve-os em backup.")
    op.drop_table("atividade_item")
    op.drop_table("atividade_operacional")
    for nome, colunas in colunas_legado.items():
        with op.batch_alter_table(nome) as batch:
            batch.drop_constraint(f"uq_{nome}_chave_envio", type_="unique")
            for coluna in colunas:
                if coluna.foreign_keys:
                    batch.drop_constraint(f"fk_{nome}_{coluna.name}_usuario", type_="foreignkey")
            for coluna in reversed(colunas):
                batch.drop_column(coluna.name)
