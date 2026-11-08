"""Modelo de usuário (gestão e acesso)."""
from sqlalchemy import event, inspect

from ..extensions import db
from ._helpers import iso_now


class Usuario(db.Model):
    __tablename__ = "usuario"
    # SQLite não deve reutilizar o ID de uma conta removida: um cookie antigo
    # nunca pode se tornar a identidade de uma nova conta com versão inicial 1.
    __table_args__ = {"sqlite_autoincrement": True}

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(180), nullable=False, unique=True)
    senha_hash = db.Column(db.String(255), nullable=False)
    # perfil: admin | tecnico | trabalhador (perfis oficiais do MVP)
    perfil = db.Column(db.String(20), nullable=False, default="trabalhador")
    ativo = db.Column(db.Boolean, nullable=False, default=True)
    # Epoch persistente: cookies emitidos com outra versão não autenticam.
    auth_version = db.Column(db.Integer, nullable=False, default=1,
                             server_default=db.text("1"))
    criado_em = db.Column(db.String(40), nullable=False, default=iso_now)
    atualizado_em = db.Column(db.String(40), nullable=True)

    # Relacionamentos
    propriedades = db.relationship("Propriedade", back_populates="usuario")
    vinculos_propriedade = db.relationship(
        "UsuarioPropriedade",
        foreign_keys="UsuarioPropriedade.usuario_id",
        back_populates="usuario",
    )
    interacoes_ia = db.relationship("IaInteracao", back_populates="usuario")
    tokens_reset = db.relationship(
        "SenhaResetToken",
        back_populates="usuario",
        cascade="all, delete-orphan",
    )

    def __repr__(self):
        return f"<Usuario {self.id} {self.email}>"

    def revogar_sessoes(self):
        """Revoga todas as sessões no próximo flush, sem commit separado.

        A expressão SQL evita perder incrementos em revogações concorrentes.
        Chamadores administrativos devem confirmar sua transação normalmente.
        """
        self.auth_version = Usuario.auth_version + 1


@event.listens_for(Usuario, "before_update")
def _revogar_apos_alteracao_de_seguranca(mapper, connection, usuario):
    """Cobre painel, reset/convite e scripts que atualizam objetos ORM.

    Não usar UPDATE em massa/SQL direto para senha, perfil ou ativação: essas
    operações ignoram eventos do mapper e precisam revogar explicitamente.
    """
    estado = inspect(usuario)
    if any(estado.attrs[campo].history.has_changes()
           for campo in ("senha_hash", "perfil", "ativo")):
        usuario.revogar_sessoes()
