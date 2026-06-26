"""Modelo de arquivo enviado (upload)."""
from ..extensions import db
from ._helpers import iso_now


class UploadArquivo(db.Model):
    __tablename__ = "upload_arquivo"

    id = db.Column(db.Integer, primary_key=True)
    propriedade_id = db.Column(db.Integer, db.ForeignKey("propriedade.id"), nullable=False)
    nome_original = db.Column(db.String(255), nullable=False)
    caminho = db.Column(db.String(500), nullable=False)
    tipo_mime = db.Column(db.String(120), nullable=True)
    tamanho = db.Column(db.Integer, nullable=True)
    descricao = db.Column(db.Text, nullable=True)
    enviado_em = db.Column(db.String(40), nullable=False, default=iso_now)

    propriedade = db.relationship("Propriedade", back_populates="arquivos")

    def __repr__(self):
        return f"<UploadArquivo {self.id} {self.nome_original}>"
