"""Modelo de aplicação de insumo (operacional/histórico).

Esta tabela registra o uso de insumos do catálogo. É operacional/histórica:
não contém recomendação agronômica, não valida dose e não permite seed
automático nesta etapa.
"""
from ..extensions import db
from ._helpers import iso_now


class AplicacaoInsumo(db.Model):
    __tablename__ = "aplicacao_insumo"

    id = db.Column(db.Integer, primary_key=True)
    cultura_gleba_id = db.Column(db.Integer, db.ForeignKey("cultura_gleba.id"), nullable=False)
    produto_base_id = db.Column(db.Integer, db.ForeignKey("produto_base.id"), nullable=False)
    data_aplicacao = db.Column(db.String(40), nullable=False)
    dose = db.Column(db.Float, nullable=True)
    unidade = db.Column(db.String(20), nullable=True)
    responsavel = db.Column(db.String(120), nullable=True)
    observacao = db.Column(db.Text, nullable=True)
    criado_em = db.Column(db.String(40), nullable=False, default=iso_now)

    cultura_gleba = db.relationship("CulturaGleba", back_populates="aplicacoes")
    produto = db.relationship("ProdutoBase", back_populates="aplicacoes")

    def __repr__(self):
        return f"<AplicacaoInsumo {self.id}>"
