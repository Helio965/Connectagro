"""Validação e importação do seed técnico do catálogo de produtos.

Regras do MVP (ver docs/03-regras-de-negocio.md e data/seeds/README.md):

- Importa ``produto_base`` + ``produto_tecnico`` + ``produto_imagem``.
- **Não** importa ``produto_preco`` (pendente no MVP; fica no sistema final).
- **Não** importa ``itens_bloqueados_ou_excluidos`` (ex.: Paraquate, Oxamil).
- Importação **idempotente**: rodar duas vezes não duplica registros.
- Não inventa preço, fabricante nem validação oficial. As imagens são
  referências visuais de fonte pública (Wikimedia Commons), rastreadas no
  manifesto ``data/seeds/catalogo_imagens_manifest.*``.
"""
import hashlib
import json
from pathlib import Path
import re

from sqlalchemy import func, text
from sqlalchemy.exc import IntegrityError

# Caminho padrão do seed (raiz do projeto → data/seeds/...).
DEFAULT_SEED_PATH = (
    Path(__file__).resolve().parents[3] / "data" / "seeds"
    / "connectagro_produtos_seed.json"
)

CHAVES_OBRIGATORIAS = ("produto_base", "produto_tecnico", "produto_preco", "produto_imagem")

STATUS_REGULATORIO_VALIDOS = {
    "nao_validado_agrofit",
    "atencao_regulatoria",
    "sujeito_a_sipeagro_nao_validado",
    "tipo_tecnico_generico",
    "bloqueado_historico",
}
STATUS_SISTEMA_VALIDOS = {"pre_cadastrado", "cadastrado_usuario", "definitivo", "bloqueado_historico"}
_STATUS_BLOQUEADO = "bloqueado_historico"
_CAMPOS_IMAGEM = ("url", "fonte", "status_validacao", "observacoes")


class SeedInvalidoError(ValueError):
    """Erro de validação do seed técnico do catálogo."""


def carregar_seed(caminho=DEFAULT_SEED_PATH):
    """Carrega o seed JSON do disco e retorna o dicionário."""
    with open(caminho, "r", encoding="utf-8") as f:
        return json.load(f)


def validar_seed(dados):
    """Valida o seed técnico do catálogo. Lança ``SeedInvalidoError`` em falha.

    Retorna ``True`` quando o seed é válido.
    """
    if not isinstance(dados, dict):
        raise SeedInvalidoError("Seed inválido: raiz não é um objeto JSON.")

    for chave in CHAVES_OBRIGATORIAS:
        if chave not in dados:
            raise SeedInvalidoError(f"Seed inválido: chave ausente '{chave}'.")
        if not isinstance(dados[chave], list):
            raise SeedInvalidoError(f"Seed inválido: '{chave}' deve ser uma lista.")
        if any(not isinstance(item, dict) for item in dados[chave]):
            raise SeedInvalidoError(f"Seed inválido: itens de '{chave}' devem ser objetos.")

    def identificador(valor, campo):
        if type(valor) is not int or not 1 <= valor <= 2**31 - 1:
            raise SeedInvalidoError(f"Seed inválido: {campo} deve ser um inteiro positivo válido.")

    def texto(cadastro, campo, limite=None, obrigatorio=False):
        valor = cadastro.get(campo)
        if valor is None and not obrigatorio:
            return
        if not isinstance(valor, str) or (obrigatorio and not valor.strip()):
            raise SeedInvalidoError(f"Seed inválido: {campo} deve ser texto não vazio.")
        if limite is not None and len(valor) > limite:
            raise SeedInvalidoError(f"Seed inválido: {campo} excede {limite} caracteres.")

    base = dados["produto_base"]
    tecnico = dados["produto_tecnico"]

    for produto in base:
        identificador(produto.get("id"), "produto_base.id")
        texto(produto, "slug", 150, obrigatorio=True)
        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", produto["slug"]):
            raise SeedInvalidoError("Seed inválido: slug deve usar letras minúsculas, números e hífens.")
        texto(produto, "nome", 150, obrigatorio=True)
        if not isinstance(produto.get("classe"), str) or produto["classe"] not in {"defensivo", "fertilizante"}:
            raise SeedInvalidoError("Seed inválido: classe deve ser defensivo ou fertilizante.")
        for campo, limite in (("categoria", 40), ("descricao_curta", 255), ("descricao_completa", None)):
            texto(produto, campo, limite)
        sistema = produto.get("status_sistema", "pre_cadastrado")
        if not isinstance(sistema, str) or sistema not in STATUS_SISTEMA_VALIDOS:
            raise SeedInvalidoError("Seed inválido: status_sistema fora do enum.")
        regulatorio = produto.get("status_regulatorio")
        if not isinstance(regulatorio, str) or regulatorio not in STATUS_REGULATORIO_VALIDOS:
            raise SeedInvalidoError("Seed inválido: status_regulatorio fora do enum.")
        if _STATUS_BLOQUEADO in (sistema, regulatorio):
            raise SeedInvalidoError("Seed inválido: produto bloqueado/histórico não pode ser importado.")

    # ids e slugs únicos em produto_base
    ids = [p.get("id") for p in base]
    slugs = [p.get("slug") for p in base]
    if len(ids) != len(set(ids)):
        raise SeedInvalidoError("Seed inválido: ids duplicados em produto_base.")
    if len(slugs) != len(set(slugs)):
        raise SeedInvalidoError("Seed inválido: slugs duplicados em produto_base.")

    # FK: produto_tecnico.produto_id deve referenciar produto_base.id
    base_ids = set(ids)
    for t in tecnico:
        identificador(t.get("produto_id"), "produto_tecnico.produto_id")
        if t.get("produto_id") not in base_ids:
            raise SeedInvalidoError(
                f"Seed inválido: produto_tecnico.produto_id "
                f"{t.get('produto_id')} sem produto_base correspondente."
            )
        for campo, limite in (("grupo_quimico", 120), ("composicao", None),
                              ("uso_principal", 120), ("modo_aplicacao", 120),
                              ("forma_aplicacao", 120), ("tipo_liberacao", 40),
                              ("fonte_tecnica", 255), ("observacoes", None)):
            texto(t, campo, limite)
        for campo in ("nutrientes_principais", "culturas_comuns", "alvos_controle"):
            valor = t.get(campo)
            if valor is not None and not isinstance(valor, (str, list, dict)):
                raise SeedInvalidoError(f"Seed inválido: {campo} deve ser texto ou JSON.")
            try:
                json.dumps(valor, allow_nan=False)
            except (TypeError, ValueError, RecursionError):
                raise SeedInvalidoError(f"Seed inválido: {campo} contém JSON inválido.") from None
    if len(tecnico) != len({t["produto_id"] for t in tecnico}):
        raise SeedInvalidoError("Seed inválido: produto_tecnico duplicado para o mesmo produto.")

    # preço continua vazio no MVP (menor valor diário fica no sistema final)
    if dados["produto_preco"]:
        raise SeedInvalidoError("Seed inválido: produto_preco deve estar vazio no MVP.")

    # imagens são opcionais; quando presentes, cada uma referencia um
    # produto_base válido e traz um caminho/url não vazio.
    for img in dados["produto_imagem"]:
        identificador(img.get("produto_id"), "produto_imagem.produto_id")
        if img.get("produto_id") not in base_ids:
            raise SeedInvalidoError(
                f"Seed inválido: produto_imagem.produto_id "
                f"{img.get('produto_id')} sem produto_base correspondente."
            )
        if not isinstance(img.get("url"), str) or not img["url"].strip():
            raise SeedInvalidoError(
                f"Seed inválido: produto_imagem sem url "
                f"(produto_id={img.get('produto_id')})."
            )
        for campo, limite in (("url", 500), ("fonte", 255), ("observacoes", None)):
            texto(img, campo, limite)
        status_imagem = img.get("status_validacao", "nao_consolidado")
        if not isinstance(status_imagem, str) or status_imagem not in {"pendente", "nao_consolidado"}:
            raise SeedInvalidoError("Seed inválido: status_validacao de imagem fora do enum.")
    imagens = dados["produto_imagem"]
    if len(imagens) != len({img["produto_id"] for img in imagens}):
        raise SeedInvalidoError("Seed inválido: produto_imagem duplicada para o mesmo produto.")

    # itens bloqueados/excluídos não podem aparecer como produto_base
    lista_bloqueados = dados.get("itens_bloqueados_ou_excluidos", [])
    if not isinstance(lista_bloqueados, list) or any(not isinstance(b, dict) for b in lista_bloqueados):
        raise SeedInvalidoError("Seed inválido: itens_bloqueados_ou_excluidos deve ser lista de objetos.")
    for bloqueado in lista_bloqueados:
        texto(bloqueado, "slug", 150, obrigatorio=True)
    bloqueados = {b["slug"] for b in lista_bloqueados}
    if bloqueados & set(slugs):
        raise SeedInvalidoError(
            "Seed inválido: item bloqueado/excluído presente em produto_base "
            f"({bloqueados & set(slugs)})."
        )

    return True


def _to_json(valor):
    """Serializa listas como JSON em texto; mantém strings/None como estão."""
    if isinstance(valor, (list, dict)):
        return json.dumps(valor, ensure_ascii=False)
    return valor


def _conteudo_imagem(imagem):
    """Campos efetivamente aplicados; identidade e auditoria não entram no hash."""
    if isinstance(imagem, dict):
        return {campo: imagem.get(campo, "nao_consolidado" if campo == "status_validacao" else None)
                for campo in _CAMPOS_IMAGEM}
    return {campo: getattr(imagem, campo) for campo in _CAMPOS_IMAGEM}


def _fingerprint_imagem(imagem):
    conteudo = json.dumps(_conteudo_imagem(imagem), ensure_ascii=False,
                          sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(conteudo.encode("utf-8")).hexdigest()


def sincronizar_seq_produto_base(db_session):
    """Avança a sequence PG após IDs explícitos, sem commit e sem recuá-la.

    O chamador deve manter o lock comum do catálogo. Aprovação de novo produto
    chama este helper antes do INSERT automático; importação chama após o flush
    dos IDs explícitos. SQLite não exige ajuste e não executa SQL PostgreSQL.
    """
    bind = db_session.get_bind()
    if bind.dialect.name != "postgresql":
        return
    from ..models import ProdutoBase

    # Um ProdutoBase automático já pendente não pode ser autoflushado antes
    # de corrigir a sequence que produzirá seu identificador.
    with db_session.no_autoflush:
        maximo = db_session.query(func.max(ProdutoBase.id)).scalar()
        if maximo is None:
            return
        sequencia = db_session.execute(text(
            "SELECT n.nspname, c.relname FROM pg_class c "
            "JOIN pg_namespace n ON n.oid=c.relnamespace "
            "WHERE c.oid=CAST(pg_get_serial_sequence('produto_base','id') AS regclass)"
        )).first()
        if sequencia is None:
            raise SeedInvalidoError("Catálogo sem sequence automática de ProdutoBase; revisão necessária.")
        preparador = bind.dialect.identifier_preparer
        nome = preparador.quote_schema(sequencia[0]) + "." + preparador.quote(sequencia[1])
        # Identificadores vêm do catálogo PG e são escapados pelo dialect.
        ultimo, chamado = db_session.execute(text(
            f"SELECT last_value, is_called FROM {nome}"
        )).one()
        if ultimo < maximo or (ultimo == maximo and not chamado):
            db_session.execute(text("SELECT setval(CAST(:nome AS regclass), :maximo, true)"),
                               {"nome": nome, "maximo": maximo})


def importar_seed_catalogo(db_session, dados):
    """Importa referências globais atomicamente, preservando dados administrados.

    Não importa preços ou itens bloqueados. ProdutoBase e ficha técnica já
    existentes não são sobrescritos. Imagem só é atualizada quando a proveniência
    seed é explícita e seu conteúdo ainda corresponde ao último fingerprint
    aplicado. Legado incerto, imagem extra ou divergência são preservados.
    """
    from ..models import ProdutoBase, ProdutoTecnico, ProdutoImagem
    from .catalogo_governanca_service import adquirir_lock_catalogo

    resumo = {"base_inseridos": 0, "base_ignorados": 0,
              "tecnico_inseridos": 0, "tecnico_ignorados": 0,
              "imagem_inseridos": 0, "imagem_ignorados": 0,
              "imagem_atualizados": 0, "imagem_preservadas": 0}
    try:
        validar_seed(dados)
        with db_session.no_autoflush:
            adquirir_lock_catalogo(db_session)
            existentes = db_session.query(ProdutoBase).populate_existing().all()
            por_id = {produto.id: produto for produto in existentes}
            por_slug = {produto.slug: produto for produto in existentes}
            # Preflight de todas as identidades antes de adicionar base/ficha/imagem.
            for item in dados["produto_base"]:
                pelo_id, pelo_slug = por_id.get(item["id"]), por_slug.get(item["slug"])
                if ((pelo_id is not None and pelo_id.slug != item["slug"])
                        or (pelo_slug is not None and pelo_slug.id != item["id"])):
                    raise SeedInvalidoError(
                        "Conflito de identidade do catálogo: ID e slug do seed não "
                        "correspondem ao mesmo produto. Nenhum ID histórico foi alterado.")
            bloqueados_banco = {produto.id for produto in existentes if
                                _STATUS_BLOQUEADO in (produto.status_sistema, produto.status_regulatorio)}

        for item in dados["produto_base"]:
            if item["id"] in por_id:
                resumo["base_ignorados"] += 1
                continue
            db_session.add(ProdutoBase(
                id=item["id"], nome=item["nome"], slug=item["slug"], classe=item["classe"],
                categoria=item.get("categoria"), descricao_curta=item.get("descricao_curta"),
                descricao_completa=item.get("descricao_completa"),
                status_sistema=item.get("status_sistema", "pre_cadastrado"),
                status_regulatorio=item["status_regulatorio"],
            ))
            resumo["base_inseridos"] += 1
        db_session.flush()
        sincronizar_seq_produto_base(db_session)

        tec_existentes = {tecnico.produto_id for tecnico in db_session.query(ProdutoTecnico).all()}
        for tecnico in dados["produto_tecnico"]:
            pid = tecnico["produto_id"]
            if pid in tec_existentes or pid in bloqueados_banco:
                resumo["tecnico_ignorados"] += 1
                continue
            modo = tecnico.get("modo_aplicacao") or tecnico.get("forma_aplicacao")
            db_session.add(ProdutoTecnico(
                produto_id=pid, grupo_quimico=tecnico.get("grupo_quimico"),
                composicao=tecnico.get("composicao"),
                nutrientes_principais=_to_json(tecnico.get("nutrientes_principais")),
                culturas_comuns=_to_json(tecnico.get("culturas_comuns")),
                alvos_controle=_to_json(tecnico.get("alvos_controle")),
                uso_principal=tecnico.get("uso_principal"), modo_aplicacao=modo,
                tipo_liberacao=tecnico.get("tipo_liberacao"),
                fonte_tecnica=tecnico.get("fonte_tecnica"), observacoes=tecnico.get("observacoes"),
            ))
            tec_existentes.add(pid)
            resumo["tecnico_inseridos"] += 1

        imagens_por_produto = {}
        for imagem in db_session.query(ProdutoImagem).populate_existing().order_by(ProdutoImagem.id).all():
            imagens_por_produto.setdefault(imagem.produto_id, []).append(imagem)
        slugs = {item["id"]: item["slug"] for item in dados["produto_base"]}
        for imagem in dados["produto_imagem"]:
            pid = imagem["produto_id"]
            anteriores = imagens_por_produto.get(pid, [])
            if pid in bloqueados_banco:
                resumo["imagem_ignorados"] += 1
                resumo["imagem_preservadas"] += bool(anteriores)
                continue
            origem = slugs[pid]
            gerenciadas = [anterior for anterior in anteriores if anterior.origem_seed == origem]
            if anteriores:
                if (len(gerenciadas) != 1 or not gerenciadas[0].seed_fingerprint
                        or gerenciadas[0].seed_fingerprint != _fingerprint_imagem(gerenciadas[0])):
                    resumo["imagem_ignorados"] += 1
                    resumo["imagem_preservadas"] += 1
                    continue
                anterior = gerenciadas[0]
                novo_fingerprint = _fingerprint_imagem(imagem)
                if anterior.seed_fingerprint == novo_fingerprint:
                    resumo["imagem_ignorados"] += 1
                    continue
                for campo, valor in _conteudo_imagem(imagem).items():
                    setattr(anterior, campo, valor)
                anterior.seed_fingerprint = novo_fingerprint
                resumo["imagem_atualizados"] += 1
                continue
            nova = ProdutoImagem(produto_id=pid, origem_seed=origem,
                                 seed_fingerprint=_fingerprint_imagem(imagem),
                                 **_conteudo_imagem(imagem))
            db_session.add(nova)
            imagens_por_produto[pid] = [nova]
            resumo["imagem_inseridos"] += 1
        db_session.commit()
    except IntegrityError as erro:
        db_session.rollback()
        raise SeedInvalidoError(
            "Conflito de integridade durante importação; nenhuma alteração do catálogo foi confirmada.") from erro
    except Exception:
        db_session.rollback()
        raise
    return resumo
