"""add usuario_propriedade

Revision ID: 7b1d9f0c4a21
Revises: 97642b24c238
Create Date: 2026-06-29 13:40:00.000000

"""
from datetime import datetime

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '7b1d9f0c4a21'
down_revision = '97642b24c238'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'usuario_propriedade',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('usuario_id', sa.Integer(), nullable=False),
        sa.Column('propriedade_id', sa.Integer(), nullable=False),
        sa.Column('ativo', sa.Boolean(), nullable=False),
        sa.Column('criado_por_id', sa.Integer(), nullable=True),
        sa.Column('criado_em', sa.String(length=40), nullable=False),
        sa.Column('atualizado_em', sa.String(length=40), nullable=True),
        sa.ForeignKeyConstraint(['criado_por_id'], ['usuario.id'], ),
        sa.ForeignKeyConstraint(['propriedade_id'], ['propriedade.id'], ),
        sa.ForeignKeyConstraint(['usuario_id'], ['usuario.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint(
            'usuario_id', 'propriedade_id',
            name='uq_usuario_propriedade_usuario_propriedade',
        ),
    )
    op.create_index(
        'ix_usuario_propriedade_usuario_id',
        'usuario_propriedade',
        ['usuario_id'],
        unique=False,
    )
    op.create_index(
        'ix_usuario_propriedade_propriedade_id',
        'usuario_propriedade',
        ['propriedade_id'],
        unique=False,
    )

    bind = op.get_bind()
    bind.execute(
        sa.text(
            """
            INSERT INTO usuario_propriedade
                (usuario_id, propriedade_id, ativo, criado_por_id, criado_em)
            SELECT usuario_id, id, 1, usuario_id, :criado_em
            FROM propriedade
            """
        ),
        {"criado_em": datetime.utcnow().isoformat()},
    )


def downgrade():
    op.drop_index('ix_usuario_propriedade_propriedade_id', table_name='usuario_propriedade')
    op.drop_index('ix_usuario_propriedade_usuario_id', table_name='usuario_propriedade')
    op.drop_table('usuario_propriedade')
