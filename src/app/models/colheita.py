"""Modelo de registro de colheita (operação agrícola)."""
from ..extensions import db
from ._helpers import iso_now


class ColheitaRegistro(db.Model):
    __tablename__ = "colheita_registro"

    id = db.Column(db.Integer, primary_key=True)
    cultura_gleba_id = db.Column(db.Integer, db.ForeignKey("cultura_gleba.id"), nullable=False)
    data_colheita = db.Column(db.String(40), nullable=False)
    quantidade = db.Column(db.Float, nullable=True)
    unidade = db.Column(db.String(20), nullable=True)
    qualidade = db.Column(db.String(80), nullable=True)
    observacao = db.Column(db.Text, nullable=True)
    criado_em = db.Column(db.String(40), nullable=False, default=iso_now)

    cultura_gleba = db.relationship("CulturaGleba", back_populates="colheitas")

    def __repr__(self):
        return f"<ColheitaRegistro {self.id}>"
