"""Serviços do painel de usuários da propriedade."""
from ..extensions import db
from ..models import Usuario, UsuarioPropriedade
from ..models._helpers import iso_now
from ..utils.auth import gerar_hash_senha
from ..utils.permissions import PERFIS_OFICIAIS


def normalizar_email(valor):
    """Normaliza e-mail para unicidade simples."""
    valor = (valor or "").strip().lower()
    return valor or None


def listar_usuarios_da_propriedade(propriedade):
    """Lista vínculos de usuários da propriedade atual."""
    return (UsuarioPropriedade.query
            .join(Usuario, UsuarioPropriedade.usuario_id == Usuario.id)
            .filter(UsuarioPropriedade.propriedade_id == propriedade.id)
            .order_by(UsuarioPropriedade.ativo.desc(), Usuario.nome)
            .all())


def obter_vinculo_usuario(propriedade, usuario_id):
    """Retorna vínculo do usuário com a propriedade, ou ``None``."""
    return (UsuarioPropriedade.query
            .filter_by(propriedade_id=propriedade.id, usuario_id=usuario_id)
            .first())


def contar_admins_ativos(propriedade, excluir_usuario_id=None):
    """Conta admins ativos na propriedade."""
    consulta = (UsuarioPropriedade.query
                .join(Usuario, UsuarioPropriedade.usuario_id == Usuario.id)
                .filter(UsuarioPropriedade.propriedade_id == propriedade.id)
                .filter(UsuarioPropriedade.ativo.is_(True))
                .filter(Usuario.ativo.is_(True))
                .filter(Usuario.perfil == "admin"))
    if excluir_usuario_id is not None:
        consulta = consulta.filter(Usuario.id != excluir_usuario_id)
    return consulta.count()


def _validar_dados_base(nome, perfil):
    erros = []
    if not nome:
        erros.append("O nome do usuário é obrigatório.")
    if perfil not in PERFIS_OFICIAIS:
        erros.append("Perfil inválido.")
    return erros


def _deixaria_sem_admin(propriedade, usuario, novo_perfil, novo_ativo):
    novo_admin_ativo = novo_ativo and novo_perfil == "admin"
    if novo_admin_ativo:
        return False
    if usuario.perfil == "admin" and usuario.ativo:
        return contar_admins_ativos(propriedade, excluir_usuario_id=usuario.id) == 0
    return False


def criar_usuario_da_propriedade(propriedade, dados, criado_por_id):
    """Cria usuário interno e vínculo ativo com a propriedade."""
    nome = (dados.get("nome") or "").strip()
    email = normalizar_email(dados.get("email"))
    perfil = (dados.get("perfil") or "").strip()
    senha = dados.get("senha") or ""
    confirmar_senha = dados.get("confirmar_senha") or ""
    ativo = dados.get("ativo", "1") == "1"

    erros = _validar_dados_base(nome, perfil)
    if not email:
        erros.append("O e-mail é obrigatório.")
    elif Usuario.query.filter_by(email=email).first() is not None:
        erros.append("Já existe um usuário com este e-mail.")
    if len(senha) < 6:
        erros.append("A senha temporária deve ter pelo menos 6 caracteres.")
    if confirmar_senha and senha != confirmar_senha:
        erros.append("A confirmação de senha não confere.")
    if erros:
        return None, erros

    usuario = Usuario(
        nome=nome,
        email=email,
        perfil=perfil,
        ativo=ativo,
        senha_hash=gerar_hash_senha(senha),
    )
    db.session.add(usuario)
    db.session.flush()
    db.session.add(UsuarioPropriedade(
        usuario_id=usuario.id,
        propriedade_id=propriedade.id,
        ativo=ativo,
        criado_por_id=criado_por_id,
    ))
    db.session.commit()
    return usuario, []


def editar_usuario_da_propriedade(propriedade, vinculo, dados):
    """Edita nome, perfil e status do usuário vinculado."""
    usuario = vinculo.usuario
    nome = (dados.get("nome") or "").strip()
    perfil = (dados.get("perfil") or "").strip()
    ativo = bool(dados.get("ativo"))

    erros = _validar_dados_base(nome, perfil)
    if _deixaria_sem_admin(propriedade, usuario, perfil, ativo):
        erros.append("A propriedade precisa manter pelo menos um admin ativo.")
    if erros:
        return erros

    usuario.nome = nome
    usuario.perfil = perfil
    usuario.ativo = ativo
    usuario.atualizado_em = iso_now()
    vinculo.ativo = ativo
    vinculo.atualizado_em = iso_now()
    db.session.commit()
    return []


def inativar_usuario_da_propriedade(propriedade, vinculo):
    """Inativa usuário e vínculo, sem exclusão física."""
    usuario = vinculo.usuario
    if _deixaria_sem_admin(propriedade, usuario, usuario.perfil, False):
        return ["A propriedade precisa manter pelo menos um admin ativo."]
    usuario.ativo = False
    usuario.atualizado_em = iso_now()
    vinculo.ativo = False
    vinculo.atualizado_em = iso_now()
    db.session.commit()
    return []
