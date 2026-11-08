"""optional independent property outline

Revision ID: e4ca60b1d732
Revises: d3b94f5a0c21
"""
from alembic import op
import sqlalchemy as sa

revision = "e4ca60b1d732"
down_revision = "d3b94f5a0c21"
branch_labels = None
depends_on = None


def upgrade():
    # Sem backfill ou cópia de Gleba: a ausência de contorno é válida.
    op.add_column("propriedade", sa.Column("poligono_geojson", sa.Text(), nullable=True))


def downgrade():
    propriedade = sa.table("propriedade", sa.column("poligono_geojson", sa.Text()))
    preenchido = op.get_bind().execute(sa.select(1).select_from(propriedade).where(
        propriedade.c.poligono_geojson.is_not(None)).limit(1)).first()
    if preenchido:
        raise RuntimeError("Downgrade bloqueado: há contornos de Propriedade cadastrados. "
                           "Preserve-os em backup e planeje a reversão sem perda de dados.")
    op.drop_column("propriedade", "poligono_geojson")
