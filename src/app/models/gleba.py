"""Modelo de gleba/talhão (operação agrícola)."""
from ..extensions import db
from ._helpers import iso_now


class Gleba(db.Model):
    __tablename__ = "gleba"

    id = db.Column(db.Integer, primary_key=True)
    propriedade_id = db.Column(db.Integer, db.ForeignKey("propriedade.id"), nullable=False)
    nome = db.Column(db.String(120), nullable=False)
    area_ha = db.Column(db.Float, nullable=True)
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)
    # GeoJSON do polígono armazenado como TEXT (mapa real futuro)
    poligono_geojson = db.Column(db.Text, nullable=True)
    tipo_solo = db.Column(db.String(80), nullable=True)
    observacoes = db.Column(db.Text, nullable=True)
    criado_em = db.Column(db.String(40), nullable=False, default=iso_now)
    atualizado_em = db.Column(db.String(40), nullable=True)

    propriedade = db.relationship("Propriedade", back_populates="glebas")
    cultura_glebas = db.relationship("CulturaGleba", back_populates="gleba")

    def __repr__(self):
        return f"<Gleba {self.id} {self.nome}>"
