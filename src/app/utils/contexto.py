"""Helpers de contexto do usuário logado para os CRUDs do MVP.

Glebas e culturas pertencem a uma **propriedade**. No MVP ampliado, a
propriedade atual passa a ser resolvida por vínculo usuário↔propriedade, com
compatibilidade para propriedades antigas ainda ligadas diretamente por
``propriedade.usuario_id``.
"""
from ..extensions import db
from ..models import Propriedade, UsuarioPropriedade
from .auth import usuario_atual


def garantir_vinculo_usuario_propriedade(usuario_id, propriedade_id, criado_por_id=None):
    """Garante vínculo usuário↔propriedade e o retorna."""
    vinculo = UsuarioPropriedade.query.filter_by(
        usuario_id=usuario_id,
        propriedade_id=propriedade_id,
    ).first()
    if vinculo is None:
        vinculo = UsuarioPropriedade(
            usuario_id=usuario_id,
            propriedade_id=propriedade_id,
            ativo=True,
            criado_por_id=criado_por_id,
        )
        db.session.add(vinculo)
        db.session.commit()
    elif not vinculo.ativo:
        vinculo.ativo = True
        db.session.commit()
    return vinculo


def propriedade_atual():
    """Retorna a propriedade do usuário logado, criando uma padrão se necessário.

    Retorna ``None`` se não houver usuário autenticado.
    """
    usuario = usuario_atual()
    if usuario is None:
        return None

    vinculo = (UsuarioPropriedade.query
               .filter_by(usuario_id=usuario["id"], ativo=True)
               .order_by(UsuarioPropriedade.id)
               .first())
    if vinculo is not None:
        return vinculo.propriedade

    prop = (Propriedade.query
            .filter_by(usuario_id=usuario["id"])
            .order_by(Propriedade.id)
            .first())
    if prop is not None:
        garantir_vinculo_usuario_propriedade(usuario["id"], prop.id, usuario["id"])
        return prop

    prop = Propriedade(usuario_id=usuario["id"], nome="Minha propriedade")
    db.session.add(prop)
    db.session.commit()
    garantir_vinculo_usuario_propriedade(usuario["id"], prop.id, usuario["id"])
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
