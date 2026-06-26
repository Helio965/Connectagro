"""Modelos do catálogo de produtos (base técnica de consulta).

O ConnectAgro não vende produtos. Preço e imagem são pendências no MVP.
Nenhum produto é tratado como validado oficialmente (AGROFIT/SIPEAGRO).
Campos de lista (nutrientes_principais, culturas_comuns, alvos_controle) são
``db.Text`` para armazenar JSON em texto.
"""
from ..extensions import db
from ._helpers import iso_now


class ProdutoBase(db.Model):
    __tablename__ = "produto_base"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(150), nullable=False)
    slug = db.Column(db.String(150), nullable=False, unique=True)
    # classe: defensivo | fertilizante
    classe = db.Column(db.String(30), nullable=False)
    categoria = db.Column(db.String(40), nullable=True)
    descricao_curta = db.Column(db.String(255), nullable=True)
    descricao_completa = db.Column(db.Text, nullable=True)
    # status_sistema: pre_cadastrado | cadastrado_usuario | definitivo | bloqueado_historico
    status_sistema = db.Column(db.String(30), nullable=False, default="pre_cadastrado")
    # status_regulatorio: nao_validado_agrofit | atencao_regulatoria |
    #   sujeito_a_sipeagro_nao_validado | tipo_tecnico_generico | bloqueado_historico
    status_regulatorio = db.Column(db.String(40), nullable=False, default="nao_validado_agrofit")
    criado_em = db.Column(db.String(40), nullable=False, default=iso_now)
    atualizado_em = db.Column(db.String(40), nullable=True)

    tecnicos = db.relationship(
        "ProdutoTecnico", back_populates="produto", cascade="all, delete-orphan")
    precos = db.relationship(
        "ProdutoPreco", back_populates="produto", cascade="all, delete-orphan")
    imagens = db.relationship(
        "ProdutoImagem", back_populates="produto", cascade="all, delete-orphan")
    aplicacoes = db.relationship("AplicacaoInsumo", back_populates="produto")

    def __repr__(self):
        return f"<ProdutoBase {self.id} {self.slug}>"


class ProdutoTecnico(db.Model):
    __tablename__ = "produto_tecnico"

    id = db.Column(db.Integer, primary_key=True)
    produto_id = db.Column(db.Integer, db.ForeignKey("produto_base.id"), nullable=False)
    grupo_quimico = db.Column(db.String(120), nullable=True)
    composicao = db.Column(db.Text, nullable=True)
    # Listas em JSON (TEXT): normalização futura.
    nutrientes_principais = db.Column(db.Text, nullable=True)
    culturas_comuns = db.Column(db.Text, nullable=True)
    alvos_controle = db.Column(db.Text, nullable=True)
    modo_aplicacao = db.Column(db.String(120), nullable=True)
    fonte_tecnica = db.Column(db.String(255), nullable=True)
    observacoes = db.Column(db.Text, nullable=True)

    produto = db.relationship("ProdutoBase", back_populates="tecnicos")

    def __repr__(self):
        return f"<ProdutoTecnico {self.id} produto={self.produto_id}>"


class ProdutoPreco(db.Model):
    """Preço de referência (consulta rápida). Pendência no MVP — ``valor`` pode
    ser NULL. O menor preço diário fica para o sistema final."""

    __tablename__ = "produto_preco"

    id = db.Column(db.Integer, primary_key=True)
    produto_id = db.Column(db.Integer, db.ForeignKey("produto_base.id"), nullable=False)
    valor = db.Column(db.Float, nullable=True)
    moeda = db.Column(db.String(8), nullable=True)
    unidade = db.Column(db.String(20), nullable=True)
    data_coleta = db.Column(db.String(40), nullable=True)
    fonte = db.Column(db.String(255), nullable=True)
    # status_validacao: pendente | nao_consolidado
    status_validacao = db.Column(db.String(20), nullable=False, default="pendente")
    observacoes = db.Column(db.Text, nullable=True)
    criado_em = db.Column(db.String(40), nullable=False, default=iso_now)

    produto = db.relationship("ProdutoBase", back_populates="precos")

    def __repr__(self):
        return f"<ProdutoPreco {self.id} produto={self.produto_id}>"


class ProdutoImagem(db.Model):
    """Imagem do produto. Pendência no MVP — ``url`` pode ser NULL; não usar
    imagem sem fonte."""

    __tablename__ = "produto_imagem"

    id = db.Column(db.Integer, primary_key=True)
    produto_id = db.Column(db.Integer, db.ForeignKey("produto_base.id"), nullable=False)
    url = db.Column(db.String(500), nullable=True)
    fonte = db.Column(db.String(255), nullable=True)
    # status_validacao: pendente | nao_consolidado
    status_validacao = db.Column(db.String(20), nullable=False, default="pendente")
    observacoes = db.Column(db.Text, nullable=True)
    criado_em = db.Column(db.String(40), nullable=False, default=iso_now)

    produto = db.relationship("ProdutoBase", back_populates="imagens")

    def __repr__(self):
        return f"<ProdutoImagem {self.id} produto={self.produto_id}>"
