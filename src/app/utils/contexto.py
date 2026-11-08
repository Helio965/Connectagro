"""Helpers de contexto do usuário logado para os CRUDs do MVP.

Glebas e culturas pertencem a uma **propriedade**. O contexto exige vínculo
ativo; a migration reconcilia as propriedades antigas de ``usuario_id``.
"""
from flask import current_app, g, has_request_context, request, session

from ..extensions import db
from ..models import Propriedade, UsuarioPropriedade
from .auth import usuario_atual


def garantir_vinculo_usuario_propriedade(usuario_id, propriedade_id, criado_por_id=None):
    """Operação explícita interna; chamador autoriza e confirma a transação.

    Não reativa vínculos existentes. Reconciliação antiga pertence à migration.
    A constraint única protege também inserções concorrentes.
    """
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
    return vinculo


def invalidar_contexto():
    """Invalida somente o cache da requisição, não os vínculos persistidos."""
    if has_request_context():
        g.pop("_contexto_request", None)
        g.pop("_contexto", None)


def _invalidar_formularios():
    """Formulários de outro contexto não podem gravar no contexto novo."""
    campo = current_app.config.get("WTF_CSRF_FIELD_NAME", "csrf_token")
    session.pop(campo, None)
    g.pop(campo, None)


def _contexto_validado():
    usuario = usuario_atual()
    if usuario is None or not has_request_context():
        return None
    if (g.get("_contexto_request") is request._get_current_object()
            and g._contexto["usuario_id"] == usuario["id"]):
        return g._contexto
    propriedades = (Propriedade.query.join(UsuarioPropriedade,
        UsuarioPropriedade.propriedade_id == Propriedade.id).filter(
        UsuarioPropriedade.usuario_id == usuario["id"], UsuarioPropriedade.ativo.is_(True))
        .order_by(Propriedade.nome, Propriedade.id).populate_existing().all())
    selecionada = session.get("propriedade_ativa_id")
    id_valido = type(selecionada) is int and 1 <= selecionada <= 2**63 - 1
    atual = next((p for p in propriedades if id_valido and p.id == selecionada), None)
    invalidada = "propriedade_ativa_id" in session and atual is None
    if invalidada:
        session.pop("propriedade_ativa_id", None)
        _invalidar_formularios()
    contexto = {"usuario_id": usuario["id"], "propriedades": propriedades,
                "atual": atual, "invalidada": invalidada}
    g._contexto_request = request._get_current_object()
    g._contexto = contexto
    return contexto


def propriedades_autorizadas():
    """Lista apenas propriedades existentes com vínculo ativo, sem escritas."""
    contexto = _contexto_validado()
    return contexto["propriedades"] if contexto else []


def propriedade_atual(*, selecionar_unica=True):
    """Consulta contexto autorizado; nunca cria propriedades ou vínculos.

    Uma única opção pode ser selecionada na sessão, mas uma seleção revogada
    nunca cai silenciosamente em outra propriedade na mesma requisição.
    """
    contexto = _contexto_validado()
    if contexto is None:
        return None
    if (selecionar_unica and contexto["atual"] is None
            and not contexto["invalidada"] and len(contexto["propriedades"]) == 1):
        contexto["atual"] = contexto["propriedades"][0]
        session["propriedade_ativa_id"] = contexto["atual"].id
    return contexto["atual"]


def selecionar_propriedade(propriedade_id):
    """Seleciona somente ID já autorizado; inválido não altera seleção válida."""
    if type(propriedade_id) is not int or not 1 <= propriedade_id <= 2**63 - 1:
        return None
    propriedade = next((p for p in propriedades_autorizadas() if p.id == propriedade_id), None)
    if propriedade is not None:
        if session.get("propriedade_ativa_id") != propriedade.id:
            _invalidar_formularios()
        session["propriedade_ativa_id"] = propriedade.id
        invalidar_contexto()
    return propriedade


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
