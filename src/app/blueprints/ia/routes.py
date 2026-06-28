"""Rotas do módulo IA simulada operacional do MVP."""
from flask import flash, render_template, request

from . import ia_bp
from ...services.ia_simulada_service import (
    gerar_alertas_operacionais,
    gerar_resumo_operacional,
    listar_interacoes_ia,
    registrar_interacao_ia,
    responder_pergunta_simulada,
)
from ...utils.auth import login_required, usuario_atual
from ...utils.contexto import propriedade_atual

MIN_PERGUNTA = 2
MAX_PERGUNTA = 1000


def _render_ia(propriedade, usuario, resposta_atual=None, pergunta_atual="", status=200):
    return render_template(
        "ia/index.html",
        propriedade=propriedade,
        resumo_operacional=gerar_resumo_operacional(propriedade),
        alertas=gerar_alertas_operacionais(propriedade),
        interacoes=listar_interacoes_ia(usuario, propriedade),
        resposta_atual=resposta_atual,
        pergunta_atual=pergunta_atual,
    ), status


@ia_bp.route("/", methods=["GET", "POST"])
@login_required
def index():
    propriedade = propriedade_atual()
    usuario = usuario_atual()

    if request.method == "POST":
        pergunta = (request.form.get("pergunta") or "").strip()
        if len(pergunta) < MIN_PERGUNTA:
            flash("Informe uma pergunta com pelo menos 2 caracteres.", "error")
            return _render_ia(propriedade, usuario, pergunta_atual=pergunta, status=400)
        if len(pergunta) > MAX_PERGUNTA:
            flash("A pergunta deve ter no máximo 1000 caracteres.", "error")
            return _render_ia(propriedade, usuario, pergunta_atual=pergunta, status=400)

        resposta = responder_pergunta_simulada(propriedade, pergunta)
        registrar_interacao_ia(usuario, propriedade, pergunta, resposta, tipo="simulada")
        flash("Pergunta respondida pela IA simulada.", "success")
        return _render_ia(
            propriedade,
            usuario,
            resposta_atual=resposta,
            pergunta_atual=pergunta,
        )

    return _render_ia(propriedade, usuario)
