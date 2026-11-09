"""Modelo de registro de colheita (operação agrícola)."""
from ..extensions import db
from ._helpers import iso_now


class ColheitaRegistro(db.Model):
    __tablename__ = "colheita_registro"
    __table_args__ = (db.UniqueConstraint(
        "chave_envio", name="uq_colheita_registro_chave_envio"),)

    id = db.Column(db.Integer, primary_key=True)
    cultura_gleba_id = db.Column(db.Integer, db.ForeignKey("cultura_gleba.id"), nullable=False)
    data_colheita = db.Column(db.String(40), nullable=False)
    quantidade = db.Column(db.Float, nullable=True)
    unidade = db.Column(db.String(20), nullable=True)
    qualidade = db.Column(db.String(80), nullable=True)
    observacao = db.Column(db.Text, nullable=True)
    criado_em = db.Column(db.String(40), nullable=False, default=iso_now)
    responsavel = db.Column(db.String(120), nullable=True)
    responsavel_usuario_id = db.Column(db.Integer, db.ForeignKey(
        "usuario.id", name="fk_colheita_registro_responsavel_usuario_id_usuario"), nullable=True)
    criado_por_id = db.Column(db.Integer, db.ForeignKey(
        "usuario.id", name="fk_colheita_registro_criado_por_id_usuario"), nullable=True)
    atualizado_por_id = db.Column(db.Integer, db.ForeignKey(
        "usuario.id", name="fk_colheita_registro_atualizado_por_id_usuario"), nullable=True)
    atualizado_em = db.Column(db.String(40), nullable=True)
    chave_envio = db.Column(db.String(64), nullable=True)

    cultura_gleba = db.relationship("CulturaGleba", back_populates="colheitas")
    responsavel_usuario = db.relationship("Usuario", foreign_keys=[responsavel_usuario_id])
    criado_por = db.relationship("Usuario", foreign_keys=[criado_por_id])
    atualizado_por = db.relationship("Usuario", foreign_keys=[atualizado_por_id])

    def __repr__(self):
        return f"<ColheitaRegistro {self.id}>"
