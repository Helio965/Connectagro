"""Modelo de lançamento financeiro."""
from ..extensions import db
from ._helpers import iso_now


class FinanceiroLancamento(db.Model):
    __tablename__ = "financeiro_lancamento"

    id = db.Column(db.Integer, primary_key=True)
    propriedade_id = db.Column(db.Integer, db.ForeignKey("propriedade.id"), nullable=False)
    # tipo: receita | despesa
    tipo = db.Column(db.String(10), nullable=False)
    categoria = db.Column(db.String(80), nullable=True)
    descricao = db.Column(db.Text, nullable=True)
    valor = db.Column(db.Float, nullable=False)
    data = db.Column(db.String(40), nullable=False)
    criado_em = db.Column(db.String(40), nullable=False, default=iso_now)
    atualizado_em = db.Column(db.String(40), nullable=True)

    propriedade = db.relationship("Propriedade", back_populates="lancamentos")

    def __repr__(self):
        return f"<FinanceiroLancamento {self.id} {self.tipo}>"
