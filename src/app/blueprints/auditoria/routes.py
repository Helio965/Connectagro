"""Logs de auditoria — somente admin, escopo: propriedade atual (Fase 7.3).

Exibe logs de ações sensíveis da propriedade atual. Sem dashboard gráfico,
exportação de logs, retenção automática ou integração externa.
"""
from collections import OrderedDict
import unicodedata

from flask import render_template

from ...models import Usuario
from ...models.log_auditoria import LogAuditoria
from ...services.auditoria_service import mascarar_email
from ...utils.auth import login_required
from ...utils.contexto import propriedade_atual
from ...utils.permissions import require_permission, role_label
from . import auditoria_bp

CATEGORIAS_AUDITORIA = (
    "Acessos",
    "Cadastros",
    "Edições",
    "Exclusões",
    "Relatórios",
    "Exportações",
    "Uploads",
    "Aplicações",
    "Colheitas",
    "Mapa / Propriedades",
    "Financeiro",
    "Sistema",
    "Outras ações",
)

def _normalizar(texto):
    texto = unicodedata.normalize("NFKD", texto or "")
    texto = texto.encode("ascii", "ignore").decode("ascii")
    return texto.lower()


def classificar_acao_auditoria(log):
    """Classifica um log em uma categoria visual da tela de auditoria."""
    acao = _normalizar(log.acao)
    entidade = _normalizar(log.entidade)
    descricao = _normalizar(log.descricao)
    combinado = f"{acao} {entidade} {descricao}"

    if "auth." in acao or "login" in combinado or "logout" in combinado:
        return "Acessos"
    if "export" in combinado or "exportacao" in combinado:
        return "Exportações"
    if "relatorio" in combinado or "relatorios" in combinado:
        return "Relatórios"
    if "mapa" in combinado or "gleba" in combinado or "propriedade" in combinado:
        return "Mapa / Propriedades"
    if "upload" in combinado or "arquivo" in combinado:
        return "Uploads"
    if "financeiro" in combinado or "lancamento" in combinado:
        return "Financeiro"
    if "colheita" in combinado:
        return "Colheitas"
    if "aplicacao" in combinado or "aplicacoes" in combinado:
        return "Aplicações"
    if (
        ".create" in acao
        or ".novo" in acao
        or " criada" in descricao
        or " criado" in descricao
        or " cadastrad" in descricao
    ):
        return "Cadastros"
    if (
        ".edit" in acao
        or ".update" in acao
        or " editad" in descricao
        or " atualizad" in descricao
    ):
        return "Edições"
    if (
        ".delete" in acao
        or ".remove" in acao
        or ".deactivate" in acao
        or " removid" in descricao
        or " exclu" in descricao
        or " inativ" in descricao
    ):
        return "Exclusões"
    if "negado" in combinado or "permiss" in combinado or "falha" in acao:
        return "Sistema"
    return "Outras ações"


def _formatar_data(valor):
    return valor[:19].replace("T", " ") if valor else "—"


def _descricao_segura(descricao):
    if not descricao:
        return "—"

    normalizada = _normalizar(descricao)
    marcadores_sensiveis = (
        "senha=",
        "password=",
        "token=",
        "token_hash",
        "csrf",
        "cookie",
        "session=",
        "set-cookie",
        "authorization",
    )
    if any(marcador in normalizada for marcador in marcadores_sensiveis):
        return "Descrição omitida por segurança."
    return descricao


def _log_para_view(log):
    entidade = log.entidade or "—"
    if log.entidade_id is not None:
        entidade = f"{entidade} #{log.entidade_id}"
    return {
        "data": _formatar_data(log.criado_em),
        "acao": log.acao,
        "entidade": entidade,
        "resultado": log.resultado,
        "resultado_classe": _normalizar(log.resultado or "sucesso") or "sucesso",
        "descricao": _descricao_segura(log.descricao),
        "ip": log.ip or "—",
    }


def _grupo_usuario(log, usuarios_por_id):
    usuario = usuarios_por_id.get(log.usuario_id)
    if usuario is None:
        if log.usuario_id:
            return {
                "chave": f"usuario-removido-{log.usuario_id}",
                "titulo": f"Usuário #{log.usuario_id}",
                "subtitulo": "Cadastro não encontrado para este log",
                "perfil": "desconhecido",
            }
        return {
            "chave": "sistema-registro-antigo",
            "titulo": "Sistema / Registro antigo",
            "subtitulo": "Logs sem usuário identificado",
            "perfil": "sistema",
        }

    perfil_label = role_label(usuario.perfil)
    return {
        "chave": f"usuario-{usuario.id}",
        "titulo": usuario.nome or perfil_label,
        "subtitulo": f"{perfil_label} • {mascarar_email(usuario.email)}",
        "perfil": usuario.perfil,
    }


def agrupar_logs_auditoria(logs):
    usuario_ids = sorted({log.usuario_id for log in logs if log.usuario_id})
    usuarios_por_id = {}
    if usuario_ids:
        usuarios = Usuario.query.filter(Usuario.id.in_(usuario_ids)).all()
        usuarios_por_id = {usuario.id: usuario for usuario in usuarios}

    grupos = OrderedDict()
    for log in logs:
        grupo_base = _grupo_usuario(log, usuarios_por_id)
        chave = grupo_base["chave"]
        if chave not in grupos:
            grupos[chave] = {
                **grupo_base,
                "total": 0,
                "ultima_acao": _formatar_data(log.criado_em),
                "categorias": OrderedDict((cat, []) for cat in CATEGORIAS_AUDITORIA),
            }

        categoria = classificar_acao_auditoria(log)
        grupos[chave]["total"] += 1
        grupos[chave]["categorias"][categoria].append(_log_para_view(log))

    resultado = []
    for grupo in grupos.values():
        grupo["categorias"] = [
            {"nome": nome, "total": len(itens), "logs": itens}
            for nome, itens in grupo["categorias"].items()
            if itens
        ]
        resultado.append(grupo)
    return resultado


@auditoria_bp.route("/")
@login_required
@require_permission("auditoria.view")
def index():
    propriedade = propriedade_atual()
    logs = (LogAuditoria.query
            .filter_by(propriedade_id=propriedade.id)
            .order_by(LogAuditoria.id.desc())
            .limit(200)
            .all())
    return render_template(
        "auditoria/list.html",
        logs=logs,
        auditoria_agrupada=agrupar_logs_auditoria(logs),
    )
