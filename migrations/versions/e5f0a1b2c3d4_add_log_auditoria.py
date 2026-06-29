"""add log_auditoria

Revision ID: e5f0a1b2c3d4
Revises: c3a7e8f1b2d4
Create Date: 2026-06-29 19:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e5f0a1b2c3d4'
down_revision = 'c3a7e8f1b2d4'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'log_auditoria',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('usuario_id', sa.Integer(), nullable=True),
        sa.Column('propriedade_id', sa.Integer(), nullable=True),
        sa.Column('acao', sa.String(length=80), nullable=False),
        sa.Column('entidade', sa.String(length=80), nullable=True),
        sa.Column('entidade_id', sa.String(length=80), nullable=True),
        sa.Column('resultado', sa.String(length=30), nullable=False),
        sa.Column('descricao', sa.String(length=500), nullable=True),
        sa.Column('ip', sa.String(length=64), nullable=True),
        sa.Column('user_agent', sa.String(length=255), nullable=True),
        sa.Column('criado_em', sa.String(length=40), nullable=False),
        sa.ForeignKeyConstraint(['usuario_id'], ['usuario.id'], ),
        sa.ForeignKeyConstraint(['propriedade_id'], ['propriedade.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_log_auditoria_usuario_id', 'log_auditoria', ['usuario_id'], unique=False)
    op.create_index('ix_log_auditoria_propriedade_id', 'log_auditoria', ['propriedade_id'], unique=False)
    op.create_index('ix_log_auditoria_acao', 'log_auditoria', ['acao'], unique=False)
    op.create_index('ix_log_auditoria_criado_em', 'log_auditoria', ['criado_em'], unique=False)


def downgrade():
    op.drop_index('ix_log_auditoria_criado_em', table_name='log_auditoria')
    op.drop_index('ix_log_auditoria_acao', table_name='log_auditoria')
    op.drop_index('ix_log_auditoria_propriedade_id', table_name='log_auditoria')
    op.drop_index('ix_log_auditoria_usuario_id', table_name='log_auditoria')
    op.drop_table('log_auditoria')
