"""Modelos de dados do ConnectAgro (SQLAlchemy).

Importa todos os modelos para que o SQLAlchemy registre as tabelas quando
``db.create_all()`` for chamado. Usa a instância ``db`` de ``app.extensions``.
"""
from .usuario import Usuario
from .propriedade import Propriedade
from .usuario_propriedade import UsuarioPropriedade
from .equipe import EquipeMembro
from .cultura import Cultura, CulturaGleba
from .gleba import Gleba
from .produto import ProdutoBase, ProdutoTecnico, ProdutoPreco, ProdutoImagem
from .aplicacao import AplicacaoInsumo
from .colheita import ColheitaRegistro
from .financeiro import FinanceiroLancamento
from .upload import UploadArquivo
from .ia import IaInteracao
from .senha_reset_token import SenhaResetToken
from .log_auditoria import LogAuditoria

__all__ = [
    "Usuario",
    "Propriedade",
    "UsuarioPropriedade",
    "SenhaResetToken",
    "LogAuditoria",
    "EquipeMembro",
    "Cultura",
    "CulturaGleba",
    "Gleba",
    "ProdutoBase",
    "ProdutoTecnico",
    "ProdutoPreco",
    "ProdutoImagem",
    "AplicacaoInsumo",
    "ColheitaRegistro",
    "FinanceiroLancamento",
    "UploadArquivo",
    "IaInteracao",
]
