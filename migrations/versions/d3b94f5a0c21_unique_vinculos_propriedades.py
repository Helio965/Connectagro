"""unique user/property membership and explicit legacy reconciliation

Revision ID: d3b94f5a0c21
Revises: c2a83e4f9b10
"""
from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa

revision = "d3b94f5a0c21"
down_revision = "c2a83e4f9b10"
branch_labels = None
depends_on = None
CONSTRAINT = "uq_usuario_propriedade_usuario_propriedade"


def upgrade():
    bind = op.get_bind()
    usuario = sa.table("usuario", sa.column("id", sa.Integer), sa.column("ativo", sa.Boolean))
    prop = sa.table("propriedade", sa.column("id", sa.Integer), sa.column("usuario_id", sa.Integer))
    vinculo = sa.table("usuario_propriedade", sa.column("usuario_id", sa.Integer),
                       sa.column("propriedade_id", sa.Integer), sa.column("ativo", sa.Boolean),
                       sa.column("criado_em", sa.String))
    # Preflight antes de qualquer escrita/DDL: não escolher nem apagar duplicatas.
    duplicado = bind.execute(sa.select(vinculo.c.usuario_id).group_by(
        vinculo.c.usuario_id, vinculo.c.propriedade_id).having(sa.func.count() > 1).limit(1)).first()
    if duplicado:
        raise RuntimeError("Vínculos duplicados: concilie os pares usuário/propriedade antes da migration; nenhum registro foi removido.")
    owner_orfao = bind.execute(sa.select(prop.c.id).select_from(prop.outerjoin(
        usuario, usuario.c.id == prop.c.usuario_id)).where(usuario.c.id.is_(None)).limit(1)).first()
    vinculo_orfao = bind.execute(sa.select(vinculo.c.usuario_id).select_from(
        vinculo.outerjoin(usuario, usuario.c.id == vinculo.c.usuario_id).outerjoin(
            prop, prop.c.id == vinculo.c.propriedade_id)).where(
                sa.or_(usuario.c.id.is_(None), prop.c.id.is_(None))).limit(1)).first()
    if owner_orfao or vinculo_orfao:
        raise RuntimeError("Há referências órfãs de propriedade/vínculo; exige conciliação manual, sem exclusão automática.")

    if bind.dialect.name == "sqlite":
        with op.batch_alter_table("propriedade", recreate="always",
                                  table_kwargs={"sqlite_autoincrement": True}):
            pass
    with op.batch_alter_table("usuario_propriedade") as batch:
        batch.create_unique_constraint(CONSTRAINT, ["usuario_id", "propriedade_id"])

    ausente = ~sa.exists(sa.select(1).select_from(vinculo).where(
        vinculo.c.usuario_id == prop.c.usuario_id,
        vinculo.c.propriedade_id == prop.c.id))
    # Só o par ausente do responsável legado. Nunca reativa pares existentes,
    # troca responsáveis, apaga vínculos ou atribui um ator histórico inventado.
    dados = sa.select(prop.c.usuario_id, prop.c.id, usuario.c.ativo,
                      sa.literal(datetime.now(timezone.utc).isoformat())).select_from(
                          prop.join(usuario, usuario.c.id == prop.c.usuario_id)).where(ausente)
    bind.execute(sa.insert(vinculo).from_select(
        ["usuario_id", "propriedade_id", "ativo", "criado_em"], dados))


def downgrade():
    with op.batch_alter_table("usuario_propriedade") as batch:
        batch.drop_constraint(CONSTRAINT, type_="unique")
    # Vínculos reconciliados e IDs continuam preservados; não apagar dados.
