"""Modelo de interação com a IA (simulada no MVP).

A IA do MVP é simulada e não emite recomendação agronômica definitiva.
"""
from ..extensions import db
from ._helpers import iso_now


class IaInteracao(db.Model):
    __tablename__ = "ia_interacao"

    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuario.id"), nullable=False)
    propriedade_id = db.Column(db.Integer, db.ForeignKey("propriedade.id"), nullable=True)
    pergunta = db.Column(db.Text, nullable=False)
    resposta = db.Column(db.Text, nullable=True)
    # tipo: simulada | apoio | relatorio | duvida
    tipo = db.Column(db.String(20), nullable=False, default="simulada")
    criado_em = db.Column(db.String(40), nullable=False, default=iso_now)

    usuario = db.relationship("Usuario", back_populates="interacoes_ia")
    propriedade = db.relationship("Propriedade", back_populates="interacoes_ia")

    def __repr__(self):
        return f"<IaInteracao {self.id} {self.tipo}>"
