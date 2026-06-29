"""Associação entre contas de usuário e propriedades."""
from ..extensions import db
from ._helpers import iso_now


class UsuarioPropriedade(db.Model):
    __tablename__ = "usuario_propriedade"
    __table_args__ = (
        db.UniqueConstraint(
            "usuario_id", "propriedade_id",
            name="uq_usuario_propriedade_usuario_propriedade",
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuario.id"), nullable=False)
    propriedade_id = db.Column(db.Integer, db.ForeignKey("propriedade.id"), nullable=False)
    ativo = db.Column(db.Boolean, nullable=False, default=True)
    criado_por_id = db.Column(db.Integer, db.ForeignKey("usuario.id"), nullable=True)
    criado_em = db.Column(db.String(40), nullable=False, default=iso_now)
    atualizado_em = db.Column(db.String(40), nullable=True)

    usuario = db.relationship(
        "Usuario",
        foreign_keys=[usuario_id],
        back_populates="vinculos_propriedade",
    )
    propriedade = db.relationship("Propriedade", back_populates="vinculos_usuario")
    criado_por = db.relationship("Usuario", foreign_keys=[criado_por_id])

    def __repr__(self):
        return f"<UsuarioPropriedade usuario={self.usuario_id} propriedade={self.propriedade_id}>"
