"""Modelo de membro de equipe."""
from ..extensions import db
from ._helpers import iso_now


class EquipeMembro(db.Model):
    __tablename__ = "equipe_membro"

    id = db.Column(db.Integer, primary_key=True)
    propriedade_id = db.Column(db.Integer, db.ForeignKey("propriedade.id"), nullable=False)
    nome = db.Column(db.String(120), nullable=False)
    funcao = db.Column(db.String(80), nullable=True)
    email = db.Column(db.String(180), nullable=True)
    telefone = db.Column(db.String(40), nullable=True)
    ativo = db.Column(db.Boolean, nullable=False, default=True)
    criado_em = db.Column(db.String(40), nullable=False, default=iso_now)
    atualizado_em = db.Column(db.String(40), nullable=True)

    propriedade = db.relationship("Propriedade", back_populates="membros")

    def __repr__(self):
        return f"<EquipeMembro {self.id} {self.nome}>"
