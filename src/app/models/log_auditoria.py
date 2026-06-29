"""Log de auditoria de ações sensíveis (MVP ampliado — Fase 7.3).

Registra ações administrativas e operacionais relevantes com dados **mínimos**:
nunca armazena senha, token puro, hash de senha/token, CSRF ou conteúdo completo
de formulário/arquivo. Datas/horas em ``TEXT`` (ISO 8601), conforme o dicionário
de dados.
"""
from ..extensions import db
from ._helpers import iso_now


class LogAuditoria(db.Model):
    __tablename__ = "log_auditoria"

    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(
        db.Integer, db.ForeignKey("usuario.id"), nullable=True, index=True
    )
    propriedade_id = db.Column(
        db.Integer, db.ForeignKey("propriedade.id"), nullable=True, index=True
    )
    acao = db.Column(db.String(80), nullable=False, index=True)
    entidade = db.Column(db.String(80), nullable=True)
    entidade_id = db.Column(db.String(80), nullable=True)
    # resultado: sucesso | falha | negado
    resultado = db.Column(db.String(30), nullable=False, default="sucesso")
    descricao = db.Column(db.String(500), nullable=True)
    ip = db.Column(db.String(64), nullable=True)
    user_agent = db.Column(db.String(255), nullable=True)
    criado_em = db.Column(db.String(40), nullable=False, default=iso_now, index=True)

    usuario = db.relationship("Usuario")
    propriedade = db.relationship("Propriedade")

    def __repr__(self):
        return f"<LogAuditoria {self.acao} {self.resultado} u={self.usuario_id}>"
