"""Modelo de log de auditoria (Fase 7.3).

Armazena apenas dados mínimos de ações sensíveis. Nunca grava senha, hash,
token, csrf_token nem conteúdo de formulários/arquivos.
"""
from ..extensions import db
from ._helpers import iso_now


class LogAuditoria(db.Model):
    __tablename__ = "log_auditoria"

    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, nullable=True)
    propriedade_id = db.Column(db.Integer, nullable=True)
    acao = db.Column(db.String(80), nullable=False)
    entidade = db.Column(db.String(80), nullable=True)
    entidade_id = db.Column(db.Integer, nullable=True)
    resultado = db.Column(db.String(20), nullable=False, default="sucesso")
    descricao = db.Column(db.String(500), nullable=True)
    ip = db.Column(db.String(45), nullable=True)
    user_agent = db.Column(db.String(300), nullable=True)
    criado_em = db.Column(db.String(40), nullable=False, default=iso_now)

    def __repr__(self):
        return f"<LogAuditoria {self.id} {self.acao} {self.resultado}>"
