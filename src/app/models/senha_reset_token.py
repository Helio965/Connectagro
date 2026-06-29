"""Token de recuperação/redefinição de senha (MVP ampliado — Fase 7.2).

Armazena apenas o **hash** do token (nunca o token puro) e dados mínimos da
solicitação. Datas/horas são gravadas como ``TEXT`` (ISO 8601), conforme o
dicionário de dados. Nenhuma senha é armazenada aqui.
"""
from ..extensions import db
from ._helpers import iso_now


class SenhaResetToken(db.Model):
    __tablename__ = "senha_reset_token"

    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(
        db.Integer, db.ForeignKey("usuario.id"), nullable=False, index=True
    )
    # SHA-256 hex do token puro — único; o token puro nunca é persistido.
    token_hash = db.Column(db.String(64), nullable=False, unique=True)
    usado = db.Column(db.Boolean, nullable=False, default=False)
    criado_em = db.Column(db.String(40), nullable=False, default=iso_now)
    expira_em = db.Column(db.String(40), nullable=False)
    usado_em = db.Column(db.String(40), nullable=True)
    ip_solicitacao = db.Column(db.String(64), nullable=True)
    user_agent_solicitacao = db.Column(db.String(255), nullable=True)

    usuario = db.relationship("Usuario", back_populates="tokens_reset")

    def __repr__(self):
        return f"<SenhaResetToken usuario={self.usuario_id} usado={self.usado}>"
