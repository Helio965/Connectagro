"""Modelo de aplicação de insumo (operacional/histórico).

Esta tabela registra o uso de insumos do catálogo. É operacional/histórica:
não contém recomendação agronômica, não valida dose e não permite seed
automático nesta etapa.
"""
from ..extensions import db
from ._helpers import iso_now
from ..utils.decimal_exato import DecimalExato


class AplicacaoInsumo(db.Model):
    __tablename__ = "aplicacao_insumo"
    __table_args__ = (db.UniqueConstraint(
        "chave_envio", name="uq_aplicacao_insumo_chave_envio"),)

    id = db.Column(db.Integer, primary_key=True)
    cultura_gleba_id = db.Column(db.Integer, db.ForeignKey("cultura_gleba.id"), nullable=False)
    produto_base_id = db.Column(db.Integer, db.ForeignKey("produto_base.id"), nullable=False)
    data_aplicacao = db.Column(db.String(40), nullable=False)
    dose = db.Column(db.Float, nullable=True)
    unidade = db.Column(db.String(20), nullable=True)
    responsavel = db.Column(db.String(120), nullable=True)
    observacao = db.Column(db.Text, nullable=True)
    criado_em = db.Column(db.String(40), nullable=False, default=iso_now)
    # Ausência nos históricos é preservada; executor não é a autoria do cadastro.
    responsavel_usuario_id = db.Column(db.Integer, db.ForeignKey(
        "usuario.id", name="fk_aplicacao_insumo_responsavel_usuario_id_usuario"), nullable=True)
    criado_por_id = db.Column(db.Integer, db.ForeignKey(
        "usuario.id", name="fk_aplicacao_insumo_criado_por_id_usuario"), nullable=True)
    atualizado_por_id = db.Column(db.Integer, db.ForeignKey(
        "usuario.id", name="fk_aplicacao_insumo_atualizado_por_id_usuario"), nullable=True)
    atualizado_em = db.Column(db.String(40), nullable=True)
    chave_envio = db.Column(db.String(64), nullable=True)
    quantidade_utilizada = db.Column(DecimalExato(18, 6), nullable=True)
    unidade_quantidade = db.Column(db.String(20), nullable=True)
    custo_unitario = db.Column(DecimalExato(18, 6), nullable=True)
    custo_total = db.Column(DecimalExato(18, 2), nullable=True)
    moeda = db.Column(db.String(3), nullable=True)
    origem_custo = db.Column(db.String(40), nullable=True)

    cultura_gleba = db.relationship("CulturaGleba", back_populates="aplicacoes")
    produto = db.relationship("ProdutoBase", back_populates="aplicacoes")
    responsavel_usuario = db.relationship("Usuario", foreign_keys=[responsavel_usuario_id])
    criado_por = db.relationship("Usuario", foreign_keys=[criado_por_id])
    atualizado_por = db.relationship("Usuario", foreign_keys=[atualizado_por_id])

    def __repr__(self):
        return f"<AplicacaoInsumo {self.id}>"
