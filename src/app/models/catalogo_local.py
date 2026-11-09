"""Cadastros locais e governança do catálogo, separados da base global.

Nenhuma FK operacional é alterada. Revisões e solicitações conservam sua origem
e não têm cascatas de exclusão que eliminem rastreabilidade.
"""
from ..extensions import db
from ._helpers import iso_now


class CatalogoControle(db.Model):
    __tablename__ = "catalogo_controle"
    __table_args__ = (db.CheckConstraint("id = 1", name="ck_catalogo_controle_singleton"),)

    id = db.Column(db.Integer, primary_key=True)


class ProdutoLocal(db.Model):
    __tablename__ = "produto_local"
    __table_args__ = (
        db.CheckConstraint("versao >= 1", name="ck_produto_local_versao"),
        db.UniqueConstraint("chave_envio", name="uq_produto_local_chave_envio"),
    )

    id = db.Column(db.Integer, primary_key=True)
    propriedade_id = db.Column(db.Integer, db.ForeignKey("propriedade.id"), nullable=False)
    nome = db.Column(db.String(150), nullable=False)
    classe = db.Column(db.String(30), nullable=False)
    categoria = db.Column(db.String(40), nullable=True)
    descricao_curta = db.Column(db.String(255), nullable=True)
    descricao_completa = db.Column(db.Text, nullable=True)
    unidade_referencia = db.Column(db.String(20), nullable=True)
    observacoes = db.Column(db.Text, nullable=True)
    fonte = db.Column(db.String(255), nullable=True)
    ativo = db.Column(db.Boolean, nullable=False, default=True)
    versao = db.Column(db.Integer, nullable=False, default=1)
    criado_por_id = db.Column(db.Integer, db.ForeignKey("usuario.id"), nullable=False)
    criado_em = db.Column(db.String(40), nullable=False, default=iso_now)
    atualizado_por_id = db.Column(db.Integer, db.ForeignKey("usuario.id"), nullable=True)
    atualizado_em = db.Column(db.String(40), nullable=True)
    chave_envio = db.Column(db.String(64), nullable=True)

    propriedade = db.relationship("Propriedade", foreign_keys=[propriedade_id])
    criado_por = db.relationship("Usuario", foreign_keys=[criado_por_id])
    atualizado_por = db.relationship("Usuario", foreign_keys=[atualizado_por_id])


class ProdutoPersonalizacao(db.Model):
    __tablename__ = "produto_personalizacao"
    __table_args__ = (
        db.UniqueConstraint("propriedade_id", "produto_base_id",
                            name="uq_produto_personalizacao_propriedade_produto"),
        db.CheckConstraint("versao >= 1", name="ck_produto_personalizacao_versao"),
    )

    id = db.Column(db.Integer, primary_key=True)
    propriedade_id = db.Column(db.Integer, db.ForeignKey("propriedade.id"), nullable=False)
    produto_base_id = db.Column(db.Integer, db.ForeignKey("produto_base.id"), nullable=False)
    nome_local = db.Column(db.String(150), nullable=True)
    descricao_local = db.Column(db.Text, nullable=True)
    unidade_referencia = db.Column(db.String(20), nullable=True)
    observacoes = db.Column(db.Text, nullable=True)
    fonte = db.Column(db.String(255), nullable=True)
    ativo = db.Column(db.Boolean, nullable=False, default=True)
    versao = db.Column(db.Integer, nullable=False, default=1)
    criado_por_id = db.Column(db.Integer, db.ForeignKey("usuario.id"), nullable=False)
    criado_em = db.Column(db.String(40), nullable=False, default=iso_now)
    atualizado_por_id = db.Column(db.Integer, db.ForeignKey("usuario.id"), nullable=True)
    atualizado_em = db.Column(db.String(40), nullable=True)

    produto = db.relationship("ProdutoBase", foreign_keys=[produto_base_id])
    propriedade = db.relationship("Propriedade", foreign_keys=[propriedade_id])
    criado_por = db.relationship("Usuario", foreign_keys=[criado_por_id])
    atualizado_por = db.relationship("Usuario", foreign_keys=[atualizado_por_id])


class CatalogoRevisao(db.Model):
    __tablename__ = "catalogo_revisao"
    __table_args__ = (
        db.CheckConstraint(
            "(produto_local_id IS NOT NULL AND personalizacao_id IS NULL) OR "
            "(produto_local_id IS NULL AND personalizacao_id IS NOT NULL)",
            name="ck_catalogo_revisao_origem"),
        db.CheckConstraint("versao >= 1", name="ck_catalogo_revisao_versao"),
        db.UniqueConstraint("produto_local_id", "versao", name="uq_catalogo_revisao_local_versao"),
        db.UniqueConstraint("personalizacao_id", "versao", name="uq_catalogo_revisao_personalizacao_versao"),
    )

    id = db.Column(db.Integer, primary_key=True)
    propriedade_id = db.Column(db.Integer, db.ForeignKey("propriedade.id"), nullable=False)
    produto_local_id = db.Column(db.Integer, db.ForeignKey("produto_local.id"), nullable=True)
    personalizacao_id = db.Column(db.Integer, db.ForeignKey("produto_personalizacao.id"), nullable=True)
    versao = db.Column(db.Integer, nullable=False)
    snapshot_json = db.Column(db.Text, nullable=False)
    alterado_por_id = db.Column(db.Integer, db.ForeignKey("usuario.id"), nullable=False)
    criado_em = db.Column(db.String(40), nullable=False, default=iso_now)
    acao = db.Column(db.String(30), nullable=False)

    propriedade = db.relationship("Propriedade", foreign_keys=[propriedade_id])
    produto_local = db.relationship("ProdutoLocal", foreign_keys=[produto_local_id])
    personalizacao = db.relationship("ProdutoPersonalizacao", foreign_keys=[personalizacao_id])
    alterado_por = db.relationship("Usuario", foreign_keys=[alterado_por_id])


class SolicitacaoCatalogo(db.Model):
    __tablename__ = "solicitacao_catalogo"
    __table_args__ = (
        db.CheckConstraint(
            "(produto_local_id IS NOT NULL AND personalizacao_id IS NULL) OR "
            "(produto_local_id IS NULL AND personalizacao_id IS NOT NULL)",
            name="ck_solicitacao_catalogo_origem"),
        db.CheckConstraint("origem_versao >= 1", name="ck_solicitacao_catalogo_versao"),
        db.UniqueConstraint("produto_local_id", "origem_versao", name="uq_solicitacao_catalogo_local_versao"),
        db.UniqueConstraint("personalizacao_id", "origem_versao", name="uq_solicitacao_catalogo_personalizacao_versao"),
    )

    id = db.Column(db.Integer, primary_key=True)
    propriedade_id = db.Column(db.Integer, db.ForeignKey("propriedade.id"), nullable=False)
    produto_local_id = db.Column(db.Integer, db.ForeignKey("produto_local.id"), nullable=True)
    personalizacao_id = db.Column(db.Integer, db.ForeignKey("produto_personalizacao.id"), nullable=True)
    tipo = db.Column(db.String(20), nullable=False)
    origem_versao = db.Column(db.Integer, nullable=False)
    conteudo_json = db.Column(db.Text, nullable=False)
    global_fingerprint = db.Column(db.String(64), nullable=True)
    estado = db.Column(db.String(20), nullable=False, default="pendente")
    solicitado_por_id = db.Column(db.Integer, db.ForeignKey("usuario.id"), nullable=False)
    solicitado_em = db.Column(db.String(40), nullable=False, default=iso_now)
    decidido_por_id = db.Column(db.Integer, db.ForeignKey("usuario.id"), nullable=True)
    decidido_em = db.Column(db.String(40), nullable=True)
    justificativa = db.Column(db.Text, nullable=True)
    produto_publicado_id = db.Column(db.Integer, db.ForeignKey("produto_base.id"), nullable=True)
    global_anterior_json = db.Column(db.Text, nullable=True)

    produto_local = db.relationship("ProdutoLocal", foreign_keys=[produto_local_id])
    personalizacao = db.relationship("ProdutoPersonalizacao", foreign_keys=[personalizacao_id])
    propriedade = db.relationship("Propriedade", foreign_keys=[propriedade_id])
    solicitado_por = db.relationship("Usuario", foreign_keys=[solicitado_por_id])
    decidido_por = db.relationship("Usuario", foreign_keys=[decidido_por_id])
    produto_publicado = db.relationship("ProdutoBase", foreign_keys=[produto_publicado_id])
