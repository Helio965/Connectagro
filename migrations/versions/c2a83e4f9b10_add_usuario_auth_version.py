"""add usuario auth_version for persistent session revocation

Revision ID: c2a83e4f9b10
Revises: b4f2c9d8a1e7
"""
from alembic import op
import sqlalchemy as sa

revision = "c2a83e4f9b10"
down_revision = "b4f2c9d8a1e7"
branch_labels = None
depends_on = None


def upgrade():
    column = sa.Column("auth_version", sa.Integer(), nullable=False,
                       server_default=sa.text("1"))
    if op.get_bind().dialect.name == "sqlite":
        # Preserva IDs e dados; AUTOINCREMENT impede que cookies de uma conta
        # removida autentiquem uma conta nova após reutilização automática de ID.
        with op.batch_alter_table("usuario", recreate="always",
                                  table_kwargs={"sqlite_autoincrement": True}) as batch_op:
            batch_op.add_column(column)
    else:
        op.add_column("usuario", column)


def downgrade():
    with op.batch_alter_table("usuario") as batch_op:
        batch_op.drop_column("auth_version")
