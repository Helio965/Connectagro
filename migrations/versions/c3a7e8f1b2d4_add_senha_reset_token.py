"""add senha_reset_token

Revision ID: c3a7e8f1b2d4
Revises: 7b1d9f0c4a21
Create Date: 2026-06-29 16:10:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c3a7e8f1b2d4'
down_revision = '7b1d9f0c4a21'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'senha_reset_token',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('usuario_id', sa.Integer(), nullable=False),
        sa.Column('token_hash', sa.String(length=64), nullable=False),
        sa.Column('usado', sa.Boolean(), nullable=False),
        sa.Column('criado_em', sa.String(length=40), nullable=False),
        sa.Column('expira_em', sa.String(length=40), nullable=False),
        sa.Column('usado_em', sa.String(length=40), nullable=True),
        sa.Column('ip_solicitacao', sa.String(length=64), nullable=True),
        sa.Column('user_agent_solicitacao', sa.String(length=255), nullable=True),
        sa.ForeignKeyConstraint(['usuario_id'], ['usuario.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('token_hash', name='uq_senha_reset_token_token_hash'),
    )
    op.create_index(
        'ix_senha_reset_token_usuario_id',
        'senha_reset_token',
        ['usuario_id'],
        unique=False,
    )


def downgrade():
    op.drop_index('ix_senha_reset_token_usuario_id', table_name='senha_reset_token')
    op.drop_table('senha_reset_token')
