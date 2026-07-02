"""Modelo de token de recuperação de senha (Fase 7.2).

Armazena apenas o **hash** (SHA-256) do token — o token puro nunca é
persistido. Cada token é de uso único e expirável.
"""
from ..extensions import db
from ._helpers import iso_now


class SenhaResetToken(db.Model):
    __tablename__ = "senha_reset_token"

    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuario.id"), nullable=False)
    token_hash = db.Column(db.String(64), nullable=False, unique=True)
    criado_em = db.Column(db.String(40), nullable=False, default=iso_now)
    expira_em = db.Column(db.String(40), nullable=False)
    usado = db.Column(db.Boolean, nullable=False, default=False)
    usado_em = db.Column(db.String(40), nullable=True)

    # Relacionamento
    usuario = db.relationship("Usuario", back_populates="tokens_reset")

    def __repr__(self):
        return f"<SenhaResetToken {self.id} user={self.usuario_id} usado={self.usado}>"
