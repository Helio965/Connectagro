"""Atividade agrícola geral e seus itens, sem duplicar aplicações históricas."""
from ..extensions import db
from ..utils.decimal_exato import DecimalExato
from ._helpers import iso_now


class AtividadeOperacional(db.Model):
    __tablename__ = "atividade_operacional"
    __table_args__ = (db.UniqueConstraint(
        "chave_envio", name="uq_atividade_operacional_chave_envio"),)

    id = db.Column(db.Integer, primary_key=True)
    gleba_id = db.Column(db.Integer, db.ForeignKey("gleba.id"), nullable=False)
    cultura_gleba_id = db.Column(db.Integer, db.ForeignKey("cultura_gleba.id"), nullable=True)
    tipo_atividade = db.Column(db.String(120), nullable=False)
    data_execucao = db.Column(db.String(40), nullable=False)
    responsavel = db.Column(db.String(120), nullable=True)
    responsavel_usuario_id = db.Column(db.Integer, db.ForeignKey("usuario.id"), nullable=True)
    observacao = db.Column(db.Text, nullable=True)
    criado_por_id = db.Column(db.Integer, db.ForeignKey("usuario.id"), nullable=True)
    criado_em = db.Column(db.String(40), nullable=False, default=iso_now)
    atualizado_por_id = db.Column(db.Integer, db.ForeignKey("usuario.id"), nullable=True)
    atualizado_em = db.Column(db.String(40), nullable=True)
    cancelado_por_id = db.Column(db.Integer, db.ForeignKey("usuario.id"), nullable=True)
    cancelado_em = db.Column(db.String(40), nullable=True)
    chave_envio = db.Column(db.String(64), nullable=True)

    gleba = db.relationship("Gleba", back_populates="atividades")
    cultura_gleba = db.relationship("CulturaGleba", back_populates="atividades")
    itens = db.relationship("AtividadeItem", back_populates="atividade",
                           passive_deletes="all", order_by="AtividadeItem.id")
    responsavel_usuario = db.relationship("Usuario", foreign_keys=[responsavel_usuario_id])
    criado_por = db.relationship("Usuario", foreign_keys=[criado_por_id])
    atualizado_por = db.relationship("Usuario", foreign_keys=[atualizado_por_id])
    cancelado_por = db.relationship("Usuario", foreign_keys=[cancelado_por_id])


class AtividadeItem(db.Model):
    __tablename__ = "atividade_item"

    id = db.Column(db.Integer, primary_key=True)
    atividade_id = db.Column(db.Integer, db.ForeignKey("atividade_operacional.id"), nullable=False)
    produto_base_id = db.Column(db.Integer, db.ForeignKey("produto_base.id"), nullable=False)
    dose = db.Column(DecimalExato(18, 6), nullable=True)
    unidade_dose = db.Column(db.String(20), nullable=True)
    quantidade_utilizada = db.Column(DecimalExato(18, 6), nullable=True)
    unidade_quantidade = db.Column(db.String(20), nullable=True)
    custo_unitario = db.Column(DecimalExato(18, 6), nullable=True)
    custo_total = db.Column(DecimalExato(18, 2), nullable=True)
    moeda = db.Column(db.String(3), nullable=True)
    origem_custo = db.Column(db.String(40), nullable=True)
    cancelado_em = db.Column(db.String(40), nullable=True)
    cancelado_por_id = db.Column(db.Integer, db.ForeignKey("usuario.id"), nullable=True)

    atividade = db.relationship("AtividadeOperacional", back_populates="itens")
    produto = db.relationship("ProdutoBase", foreign_keys=[produto_base_id])
    cancelado_por = db.relationship("Usuario", foreign_keys=[cancelado_por_id])
