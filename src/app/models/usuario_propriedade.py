"""Modelo de vínculo entre usuário e propriedade (MVP ampliado)."""
from ..extensions import db
from ._helpers import iso_now


class UsuarioPropriedade(db.Model):
    __tablename__ = "usuario_propriedade"

    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuario.id"), nullable=False)
    propriedade_id = db.Column(db.Integer, db.ForeignKey("propriedade.id"), nullable=False)
    ativo = db.Column(db.Boolean, nullable=False, default=True)
    criado_por_id = db.Column(db.Integer, db.ForeignKey("usuario.id"), nullable=True)
    criado_em = db.Column(db.String(40), nullable=False, default=iso_now)
    atualizado_em = db.Column(db.String(40), nullable=True)

    # Relacionamentos
    usuario = db.relationship(
        "Usuario",
        foreign_keys=[usuario_id],
        back_populates="vinculos_propriedade",
    )
    propriedade = db.relationship("Propriedade", back_populates="vinculos_usuario")

    def __repr__(self):
        return f"<UsuarioPropriedade {self.id} u={self.usuario_id} p={self.propriedade_id}>"
