"""Modelo de propriedade rural."""
from ..extensions import db
from ._helpers import iso_now


class Propriedade(db.Model):
    __tablename__ = "propriedade"

    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuario.id"), nullable=False)
    nome = db.Column(db.String(150), nullable=False)
    municipio = db.Column(db.String(120), nullable=True)
    uf = db.Column(db.String(2), nullable=True)
    area_total_ha = db.Column(db.Float, nullable=True)
    criado_em = db.Column(db.String(40), nullable=False, default=iso_now)
    atualizado_em = db.Column(db.String(40), nullable=True)

    # Relacionamentos
    usuario = db.relationship("Usuario", back_populates="propriedades")
    membros = db.relationship("EquipeMembro", back_populates="propriedade")
    culturas = db.relationship("Cultura", back_populates="propriedade")
    glebas = db.relationship("Gleba", back_populates="propriedade")
    lancamentos = db.relationship("FinanceiroLancamento", back_populates="propriedade")
    arquivos = db.relationship("UploadArquivo", back_populates="propriedade")
    interacoes_ia = db.relationship("IaInteracao", back_populates="propriedade")

    def __repr__(self):
        return f"<Propriedade {self.id} {self.nome}>"
