"""Modelos de cultura e associação cultura-gleba (operação agrícola)."""
from ..extensions import db
from ._helpers import iso_now


class Cultura(db.Model):
    __tablename__ = "cultura"

    id = db.Column(db.Integer, primary_key=True)
    propriedade_id = db.Column(db.Integer, db.ForeignKey("propriedade.id"), nullable=False)
    nome = db.Column(db.String(120), nullable=False)
    variedade = db.Column(db.String(120), nullable=True)
    safra = db.Column(db.String(20), nullable=True)
    data_inicio = db.Column(db.String(40), nullable=True)
    data_fim = db.Column(db.String(40), nullable=True)
    # status: planejada | em_andamento | colhida | cancelada
    status = db.Column(db.String(20), nullable=False, default="planejada")
    criado_em = db.Column(db.String(40), nullable=False, default=iso_now)
    atualizado_em = db.Column(db.String(40), nullable=True)

    propriedade = db.relationship("Propriedade", back_populates="culturas")
    cultura_glebas = db.relationship("CulturaGleba", back_populates="cultura")

    def __repr__(self):
        return f"<Cultura {self.id} {self.nome}>"


class CulturaGleba(db.Model):
    """Associação N:N entre cultura e gleba."""

    __tablename__ = "cultura_gleba"

    id = db.Column(db.Integer, primary_key=True)
    cultura_id = db.Column(db.Integer, db.ForeignKey("cultura.id"), nullable=False)
    gleba_id = db.Column(db.Integer, db.ForeignKey("gleba.id"), nullable=False)
    data_inicio = db.Column(db.String(40), nullable=True)
    data_fim = db.Column(db.String(40), nullable=True)
    observacoes = db.Column(db.Text, nullable=True)

    cultura = db.relationship("Cultura", back_populates="cultura_glebas")
    gleba = db.relationship("Gleba", back_populates="cultura_glebas")
    aplicacoes = db.relationship("AplicacaoInsumo", back_populates="cultura_gleba")
    colheitas = db.relationship("ColheitaRegistro", back_populates="cultura_gleba")

    def __repr__(self):
        return f"<CulturaGleba {self.id} c={self.cultura_id} g={self.gleba_id}>"
