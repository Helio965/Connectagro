"""Helpers de contexto do usuário logado para os CRUDs do MVP.

Glebas e culturas pertencem a uma **propriedade**. No MVP, cada usuário opera
sobre sua propriedade atual; se ainda não houver, uma propriedade padrão é criada
de forma transparente (não há, nesta etapa, um módulo de cadastro de propriedade).
"""
from ..extensions import db
from ..models import Propriedade
from .auth import usuario_atual


def propriedade_atual():
    """Retorna a propriedade do usuário logado, criando uma padrão se necessário.

    Retorna ``None`` se não houver usuário autenticado.
    """
    usuario = usuario_atual()
    if usuario is None:
        return None
    prop = (Propriedade.query
            .filter_by(usuario_id=usuario["id"])
            .order_by(Propriedade.id)
            .first())
    if prop is None:
        prop = Propriedade(usuario_id=usuario["id"], nome="Minha propriedade")
        db.session.add(prop)
        db.session.commit()
    return prop


def parse_float(valor):
    """Converte string em float; retorna ``None`` se vazio/ inválido."""
    if valor is None:
        return None
    valor = str(valor).strip().replace(",", ".")
    if valor == "":
        return None
    try:
        return float(valor)
    except ValueError:
        return None


def vazio_para_none(valor):
    """Normaliza string vazia para ``None``; faz strip caso contrário."""
    if valor is None:
        return None
    valor = str(valor).strip()
    return valor or None
