"""Serviço central de auditoria (Fase 7.3 — MVP ampliado).

Registra ações sensíveis sem nunca falhar o fluxo principal (try/except) e sem
armazenar dados sensíveis (senha, token, hash, CSRF, corpo de formulário/arquivo).
Logs são escopados por propriedade e consultados apenas pelo `admin`.
"""
from ..extensions import db
from ..models import LogAuditoria, Propriedade, UsuarioPropriedade
from ..utils.auth import usuario_atual

DESCRICAO_MAX = 500
ACAO_MAX = 80
ENTIDADE_MAX = 80
ENTIDADE_ID_MAX = 80
RESULTADO_MAX = 30
IP_MAX = 64
USER_AGENT_MAX = 255

RESULTADOS = ("sucesso", "falha", "negado")


def _truncar(valor, limite):
    if valor is None:
        return None
    valor = str(valor)
    return valor[:limite]


def normalizar_descricao(descricao):
    """Normaliza e limita a descrição a um tamanho seguro."""
    if descricao is None:
        return None
    return _truncar(str(descricao).strip(), DESCRICAO_MAX)


def mascarar_email(email):
    """Mascarara um e-mail para uso em descrições (ex.: a***@dominio.com)."""
    email = (email or "").strip()
    if "@" not in email:
        return None
    local, dominio = email.split("@", 1)
    if not local:
        return None
    visivel = local[0]
    return f"{visivel}***@{dominio}"


def _extrair_request_info(request):
    """Extrai IP e User-Agent do request, se houver. Nunca lê o corpo/form."""
    if request is None:
        return None, None
    ip = _truncar(getattr(request, "remote_addr", None), IP_MAX)
    ua = _truncar(request.headers.get("User-Agent") if request.headers else None,
                  USER_AGENT_MAX)
    return ip, ua


def _propriedade_id_padrao(usuario_id):
    """Resolve a propriedade do usuário **sem** criar nenhum registro."""
    if not usuario_id:
        return None
    vinculo = (UsuarioPropriedade.query
               .filter_by(usuario_id=usuario_id, ativo=True)
               .order_by(UsuarioPropriedade.id)
               .first())
    if vinculo is not None:
        return vinculo.propriedade_id
    prop = (Propriedade.query
            .filter_by(usuario_id=usuario_id)
            .order_by(Propriedade.id)
            .first())
    return prop.id if prop is not None else None


def registrar_evento(acao, entidade=None, entidade_id=None, resultado="sucesso",
                     descricao=None, usuario_id=None, propriedade_id=None,
                     request=None):
    """Registra um evento de auditoria. Nunca quebra o fluxo principal.

    Quando ``usuario_id``/``propriedade_id`` não são informados, tenta resolvê-los
    a partir da sessão atual, **sem** criar propriedade (eventos públicos como
    login falho ficam sem propriedade).
    """
    try:
        if usuario_id is None:
            # Fora de um request (ex.: chamada direta/serviço) não há sessão;
            # nesse caso o evento fica sem usuário em vez de falhar.
            try:
                atual = usuario_atual()
                usuario_id = atual["id"] if atual else None
            except Exception:
                usuario_id = None
        if propriedade_id is None and usuario_id is not None:
            propriedade_id = _propriedade_id_padrao(usuario_id)

        ip, user_agent = _extrair_request_info(request)
        resultado = resultado if resultado in RESULTADOS else "sucesso"

        log = LogAuditoria(
            usuario_id=usuario_id,
            propriedade_id=propriedade_id,
            acao=_truncar(acao, ACAO_MAX),
            entidade=_truncar(entidade, ENTIDADE_MAX),
            entidade_id=_truncar(entidade_id, ENTIDADE_ID_MAX),
            resultado=_truncar(resultado, RESULTADO_MAX),
            descricao=normalizar_descricao(descricao),
            ip=ip,
            user_agent=user_agent,
        )
        db.session.add(log)
        db.session.commit()
        return log
    except Exception:
        # Auditoria nunca pode derrubar a ação principal.
        try:
            db.session.rollback()
        except Exception:
            pass
        return None


def registrar_sucesso(acao, **kwargs):
    kwargs["resultado"] = "sucesso"
    return registrar_evento(acao, **kwargs)


def registrar_falha(acao, **kwargs):
    kwargs["resultado"] = "falha"
    return registrar_evento(acao, **kwargs)


def registrar_negado(acao, **kwargs):
    kwargs["resultado"] = "negado"
    return registrar_evento(acao, **kwargs)


def listar_logs(propriedade, filtros=None, limite=100):
    """Lista logs da propriedade atual, com filtros simples. Mais recentes 1º."""
    consulta = LogAuditoria.query.filter_by(propriedade_id=propriedade.id)
    filtros = filtros or {}

    acao = (filtros.get("acao") or "").strip()
    resultado = (filtros.get("resultado") or "").strip()
    entidade = (filtros.get("entidade") or "").strip()
    usuario_id = (filtros.get("usuario_id") or "").strip()

    if acao:
        consulta = consulta.filter(LogAuditoria.acao == acao)
    if resultado:
        consulta = consulta.filter(LogAuditoria.resultado == resultado)
    if entidade:
        consulta = consulta.filter(LogAuditoria.entidade == entidade)
    if usuario_id.isdigit():
        consulta = consulta.filter(LogAuditoria.usuario_id == int(usuario_id))

    return (consulta
            .order_by(LogAuditoria.criado_em.desc(), LogAuditoria.id.desc())
            .limit(limite)
            .all())
