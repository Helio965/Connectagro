"""Validação compartilhada de registros operacionais, sem preços inferidos.

Valores novos usam Decimal e unidades explícitas. Nenhuma função cria usuários,
produtos, lançamentos financeiros ou movimentos de estoque.
"""
from datetime import date
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP, localcontext
import re

from flask import abort

from ..models import Usuario, UsuarioPropriedade
from ..utils.auth import usuario_atual
from ..utils.permissions import has_permission

_DECIMAL = re.compile(r"^[+-]?(?:[0-9]+(?:[.,][0-9]*)?|[.,][0-9]+)$")
CAMPOS_CUSTO = frozenset({"custo_unitario", "custo_total", "moeda", "origem_custo"})


def parse_id(valor, opcional=False):
    texto = str(valor or "").strip()
    if not texto and opcional:
        return None
    if not texto.isascii() or not texto.isdigit() or len(texto) > 10:
        raise ValueError("Selecione uma opção válida.")
    numero = int(texto)
    if not 1 <= numero <= 2**31 - 1:
        raise ValueError("Selecione uma opção válida.")
    return numero


def validar_data_iso(valor):
    texto = str(valor or "").strip()
    if not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", texto):
        raise ValueError("Informe uma data válida no formato dia/mês/ano.")
    try:
        return date.fromisoformat(texto).isoformat()
    except ValueError:
        raise ValueError("Informe uma data válida no formato dia/mês/ano.") from None


def validar_decimal(valor, precision=18, scale=6, positivo=True, opcional=True):
    texto = str(valor if valor is not None else "").strip()
    if not texto and opcional:
        return None
    if len(texto) > 64 or not _DECIMAL.fullmatch(texto):
        raise ValueError("Informe um número decimal finito, sem separador de milhares.")
    try:
        numero = Decimal(texto.replace(",", "."))
        with localcontext() as ctx:
            ctx.prec = 80
            exato = numero.quantize(Decimal(1).scaleb(-scale))
    except InvalidOperation:
        raise ValueError("Informe um número decimal válido.") from None
    if not numero.is_finite() or numero != exato or abs(numero) >= Decimal(10)**(precision-scale):
        raise ValueError(f"Use até {precision-scale} dígitos inteiros e {scale} casas decimais.")
    if (positivo and numero <= 0) or (not positivo and numero < 0):
        raise ValueError("Informe um valor maior que zero." if positivo else "O valor não pode ser negativo.")
    return exato


def _valor(registro, campo):
    if registro is None:
        return None
    return registro.get(campo) if isinstance(registro, dict) else getattr(registro, campo, None)


def _usuarios_ativos(propriedade_id):
    return (Usuario.query.join(UsuarioPropriedade,
            UsuarioPropriedade.usuario_id == Usuario.id)
            .filter(UsuarioPropriedade.propriedade_id == propriedade_id,
                    UsuarioPropriedade.ativo.is_(True), Usuario.ativo.is_(True)))


def opcoes_responsaveis(propriedade_id, registro=None):
    query = _usuarios_ativos(propriedade_id)
    if not has_permission("equipe.view"):
        query = query.filter(Usuario.id == usuario_atual()["id"])
    opcoes = [(u.id, u.nome) for u in query.order_by(Usuario.nome, Usuario.id).all()]
    anterior = _valor(registro, "responsavel_usuario_id")
    if anterior and anterior not in {uid for uid, _ in opcoes}:
        # Somente o snapshot já visível no registro, nunca dados atuais externos.
        opcoes.append((anterior, (_valor(registro, "responsavel") or "Responsável") + " (registro histórico)"))
    return opcoes


def validar_responsavel(propriedade_id, raw_id, raw_texto, *, registro=None):
    erros = {}
    texto = str(raw_texto or "").strip() or None
    if texto and len(texto) > 120:
        erros["responsavel"] = "Use até 120 caracteres para o responsável."
    try:
        uid = parse_id(raw_id, opcional=True)
    except ValueError as exc:
        return None, texto, {"responsavel_usuario_id": str(exc)}
    if uid is None:
        return None, texto, erros
    anterior = _valor(registro, "responsavel_usuario_id")
    if registro is not None and uid == anterior:
        return uid, _valor(registro, "responsavel"), erros
    if not has_permission("equipe.view") and uid != usuario_atual()["id"]:
        erros["responsavel_usuario_id"] = "Selecione sua própria conta ou informe o responsável por texto."
        return None, texto, erros
    pessoa = _usuarios_ativos(propriedade_id).filter(Usuario.id == uid).first()
    if pessoa is None:
        erros["responsavel_usuario_id"] = "Selecione um responsável com conta e vínculo ativos nesta propriedade."
        return None, texto, erros
    return uid, pessoa.nome, erros


def validar_consumo_custo(form, *, existente=None, pode_criar_custo=False,
                         pode_editar_custo=False):
    """Valida consumo e custo manual; ausência não vira zero.

    O custo unitário refere-se à própria unidade de consumo informada. Não há
    conversão de unidades. Total calculado usa arredondamento comercial de
    centavos. Quem não pode editar custos também não pode alterar sua base.
    """
    erros = {}
    dados = {}
    pode_custo = pode_editar_custo if existente is not None else pode_criar_custo
    if not pode_custo and CAMPOS_CUSTO.intersection(form.keys()):
        abort(403)
    def recebido(campo):
        return form.get(campo) if campo in form else _valor(existente, campo)

    try:
        dados["quantidade_utilizada"] = validar_decimal(recebido("quantidade_utilizada"))
    except ValueError as exc:
        dados["quantidade_utilizada"] = None
        erros["quantidade_utilizada"] = str(exc)
    unidade = str(recebido("unidade_quantidade") or "").strip() or None
    dados["unidade_quantidade"] = unidade
    if unidade and len(unidade) > 20:
        erros["unidade_quantidade"] = "Use até 20 caracteres para a unidade de consumo."
    if dados["quantidade_utilizada"] is not None and not unidade:
        erros["unidade_quantidade"] = "Informe a unidade da quantidade efetivamente utilizada."
    tem_custo = any(_valor(existente, campo) is not None for campo in ("custo_unitario", "custo_total"))
    if not pode_custo:
        if tem_custo:
            mudou_base = any(dados[campo] != _valor(existente, campo)
                             for campo in ("quantidade_utilizada", "unidade_quantidade"))
            if "produto_base_id" in form:
                mudou_base = mudou_base or str(form.get("produto_base_id")) != str(_valor(existente, "produto_base_id"))
            if mudou_base:
                abort(403)
        for campo in CAMPOS_CUSTO:
            dados[campo] = _valor(existente, campo)
        return dados, erros
    for campo, scale in (("custo_unitario", 6), ("custo_total", 2)):
        try:
            dados[campo] = validar_decimal(recebido(campo), scale=scale, positivo=False)
        except ValueError as exc:
            dados[campo] = None
            erros[campo] = str(exc)
    unitario, total = dados["custo_unitario"], dados["custo_total"]
    moeda = str(form.get("moeda") or "BRL").strip().upper()
    if moeda != "BRL":
        erros["moeda"] = "A moeda disponível nesta etapa é BRL (real)."
    if unitario is not None and not unidade:
        erros["unidade_quantidade"] = "Informe a unidade à qual o custo unitário se refere."
    quantidade = dados["quantidade_utilizada"]
    if quantidade is not None and unitario is not None:
        with localcontext() as ctx:
            ctx.prec = 80
            calculado = (quantidade * unitario).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        if calculado >= Decimal("10000000000000000"):
            erros["custo_total"] = "O custo total excede o limite permitido."
        elif total is not None and total != calculado and "custo_total" in form:
            erros["custo_total"] = "O custo total informado difere de quantidade × custo unitário."
        else:
            dados["custo_total"] = calculado
    existe_custo = unitario is not None or dados["custo_total"] is not None
    dados["moeda"] = "BRL" if existe_custo else None
    dados["origem_custo"] = ("calculado_quantidade_unitario" if quantidade is not None and unitario is not None
                             else "informado_usuario") if existe_custo else None
    return dados, erros
