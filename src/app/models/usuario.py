"""Modelo de usuário (gestão e acesso)."""
from ..extensions import db
from ._helpers import iso_now


class Usuario(db.Model):
    __tablename__ = "usuario"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(180), nullable=False, unique=True)
    senha_hash = db.Column(db.String(255), nullable=False)
    # perfil: admin | tecnico | trabalhador (perfis oficiais do MVP)
    perfil = db.Column(db.String(20), nullable=False, default="trabalhador")
    ativo = db.Column(db.Boolean, nullable=False, default=True)
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
