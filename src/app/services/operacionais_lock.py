"""Serializa validação e escrita operacional no contexto da Propriedade.

Todos os registros e seus pais usam a mesma linha de lock. A autorização é
revalidada depois da espera, e objetos ORM lidos antes dela são atualizados.
"""
from functools import wraps

from flask import abort, flash, g, redirect, request, url_for
from sqlalchemy.exc import OperationalError

from ..extensions import db
from ..models import Propriedade
from ..utils.auth import usuario_atual
from ..utils.contexto import invalidar_contexto, propriedade_atual
from ..utils.permissions import has_permission
from .auditoria_service import registrar_negado


def _adquirir_lock(conexao, propriedade_id):
    """Adquire o lock sem confirmar a transação nem carregar snapshots ORM."""
    if conexao.dialect.name == "sqlite":
        if conexao.connection.driver_connection.in_transaction:
            # Um snapshot físico anterior pode falhar no upgrade. Nesse caso,
            # rejeitamos a escrita em vez de repetir validação com estado antigo.
            return conexao.execute(db.update(Propriedade.__table__).where(
                Propriedade.id == propriedade_id).values(id=Propriedade.id)).rowcount > 0
        conexao.exec_driver_sql("BEGIN IMMEDIATE")
        return conexao.execute(db.select(Propriedade.id).where(
            Propriedade.id == propriedade_id)).first() is not None
    return conexao.execute(db.select(Propriedade.id).where(
        Propriedade.id == propriedade_id).with_for_update()).first() is not None


def _ocupado(erro, dialect):
    if dialect == "sqlite":
        codigo = getattr(erro.orig, "sqlite_errorcode", 0) or 0
        return (codigo & 0xff) in {5, 6}  # SQLITE_BUSY / SQLITE_LOCKED, inclusive SNAPSHOT
    return getattr(erro.orig, "pgcode", None) in {"40001", "40P01", "55P03"}


def serializar_operacao(permissao):
    """Protege writes após login/permissão; GET/HEAD não adquirem lock.

    As views continuam responsáveis pelo commit da operação. O rollback final
    libera o lock em validação, negativa ou exceção, sem desfazer commits já
    confirmados. Nenhuma alteração de domínio pode anteceder este decorator.
    """
    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if request.method in {"GET", "HEAD", "OPTIONS"}:
                return view(*args, **kwargs)
            propriedade = propriedade_atual()
            ator = usuario_atual()
            if propriedade is None or ator is None:
                abort(409)
            propriedade_id, ator_id = propriedade.id, ator["id"]
            conexao = db.session.connection()
            dialect = conexao.dialect.name
            try:
                with db.session.no_autoflush:
                    if not _adquirir_lock(conexao, propriedade_id):
                        abort(404)
                    # Expire também os objetos lidos por filtros e hooks antes
                    # da espera; identidade de Python não é um snapshot atual.
                    db.session.expire_all()
                    g.pop("_auth_request", None)
                    g.pop("_auth_usuario", None)
                    invalidar_contexto()
                    if usuario_atual() is None:
                        flash("Seu acesso foi atualizado. Faça login novamente.", "warning")
                        return redirect(url_for("auth.login"))
                    atual = propriedade_atual(selecionar_unica=False)
                    if (atual is None or atual.id != propriedade_id
                            or not has_permission(permissao)):
                        db.session.rollback()
                        registrar_negado(
                            "operacionais.acesso.revogado", entidade="permission",
                            descricao=f"Acesso atualizado durante a operação: {permissao}",
                            usuario_id=ator_id, propriedade_id=propriedade_id, request=request)
                        abort(403)
                return view(*args, **kwargs)
            except OperationalError as erro:
                if not _ocupado(erro, dialect):
                    raise
                db.session.rollback()
                flash("Outra alteração está em andamento. Recarregue e tente novamente.", "warning")
                abort(409)
            finally:
                # SQLAlchemy pode ter iniciado outra transação para renderizar
                # a resposta após o commit; ela também termina sem novas escritas.
                db.session.rollback()

        return wrapped
    return decorator
