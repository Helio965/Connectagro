"""Criação explícita de contexto operacional nas fixtures de testes.

Os helpers fazem flush; cada fixture confirma a própria transação. Não usam o
resolvedor de contexto nem reconciliam vínculos preexistentes implicitamente.
"""
from app.extensions import db
from app.models import Propriedade, UsuarioPropriedade


def vincular_usuario_propriedade(usuario_id, propriedade_id, *, ativo=True,
                                 criado_por_id=None):
    vinculo = UsuarioPropriedade(usuario_id=usuario_id,
                                propriedade_id=propriedade_id, ativo=ativo,
                                criado_por_id=criado_por_id)
    db.session.add(vinculo)
    db.session.flush()
    return vinculo


def criar_propriedade_com_vinculo(usuario_id, *, nome, **campos):
    propriedade = Propriedade(usuario_id=usuario_id, nome=nome, **campos)
    db.session.add(propriedade)
    db.session.flush()
    vincular_usuario_propriedade(usuario_id, propriedade.id)
    return propriedade
