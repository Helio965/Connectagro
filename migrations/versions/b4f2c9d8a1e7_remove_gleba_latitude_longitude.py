"""remove gleba latitude longitude

Revision ID: b4f2c9d8a1e7
Revises: e3e72eacc334
Create Date: 2026-06-30 10:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "b4f2c9d8a1e7"
down_revision = "e3e72eacc334"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("gleba") as batch_op:
        batch_op.add_column(
            sa.Column(
                "status",
                sa.String(length=30),
                nullable=False,
                server_default="ativa",
            )
        )
        batch_op.drop_column("latitude")
        batch_op.drop_column("longitude")


def downgrade():
    with op.batch_alter_table("gleba") as batch_op:
        batch_op.add_column(sa.Column("longitude", sa.Float(), nullable=True))
        batch_op.add_column(sa.Column("latitude", sa.Float(), nullable=True))
        batch_op.drop_column("status")
