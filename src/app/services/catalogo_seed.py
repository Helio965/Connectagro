"""Validação e importação do seed técnico do catálogo de produtos.

Regras do MVP (ver docs/03-regras-de-negocio.md e data/seeds/README.md):

- Importa apenas ``produto_base`` + ``produto_tecnico``.
- **Não** importa ``produto_preco`` nem ``produto_imagem`` (pendentes no MVP).
- **Não** importa ``itens_bloqueados_ou_excluidos`` (ex.: Paraquate, Oxamil).
- Importação **idempotente**: rodar duas vezes não duplica registros.
- Não inventa preço, imagem, fabricante nem validação oficial.
"""
import json
from pathlib import Path

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

    base = dados["produto_base"]
    tecnico = dados["produto_tecnico"]

    # ids e slugs únicos em produto_base
    ids = [p.get("id") for p in base]
    slugs = [p.get("slug") for p in base]
    if len(ids) != len(set(ids)):
        raise SeedInvalidoError("Seed inválido: ids duplicados em produto_base.")
    if len(slugs) != len(set(slugs)):
        raise SeedInvalidoError("Seed inválido: slugs duplicados em produto_base.")

    # status_regulatorio dentro do enum oficial
    for p in base:
        sr = p.get("status_regulatorio")
        if sr not in STATUS_REGULATORIO_VALIDOS:
            raise SeedInvalidoError(
                f"Seed inválido: status_regulatorio '{sr}' fora do enum "
                f"(produto id={p.get('id')})."
            )

    # FK: produto_tecnico.produto_id deve referenciar produto_base.id
    base_ids = set(ids)
    for t in tecnico:
        if t.get("produto_id") not in base_ids:
            raise SeedInvalidoError(
                f"Seed inválido: produto_tecnico.produto_id "
                f"{t.get('produto_id')} sem produto_base correspondente."
            )

    # preço e imagem devem estar vazios no MVP
    if dados["produto_preco"]:
        raise SeedInvalidoError("Seed inválido: produto_preco deve estar vazio no MVP.")
    if dados["produto_imagem"]:
        raise SeedInvalidoError("Seed inválido: produto_imagem deve estar vazio no MVP.")

    # itens bloqueados/excluídos não podem aparecer como produto_base
    bloqueados = {b.get("slug") for b in dados.get("itens_bloqueados_ou_excluidos", [])}
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


def importar_seed_catalogo(db_session, dados):
    """Importa ``produto_base`` + ``produto_tecnico`` de forma idempotente.

    Não importa preço, imagem nem itens bloqueados. Retorna um resumo com as
    contagens de registros inseridos e ignorados.
    """
    from ..models import ProdutoBase, ProdutoTecnico

    validar_seed(dados)

    resumo = {"base_inseridos": 0, "base_ignorados": 0,
              "tecnico_inseridos": 0, "tecnico_ignorados": 0}

    # Idempotência de produto_base pela chave slug.
    slugs_existentes = {p.slug for p in db_session.query(ProdutoBase).all()}
    for item in dados["produto_base"]:
        if item["slug"] in slugs_existentes:
            resumo["base_ignorados"] += 1
            continue
        db_session.add(ProdutoBase(
            id=item.get("id"),
            nome=item["nome"],
            slug=item["slug"],
            classe=item["classe"],
            categoria=item.get("categoria"),
            descricao_curta=item.get("descricao_curta"),
            descricao_completa=item.get("descricao_completa"),
            status_sistema=item.get("status_sistema", "pre_cadastrado"),
            status_regulatorio=item["status_regulatorio"],
        ))
        slugs_existentes.add(item["slug"])
        resumo["base_inseridos"] += 1

    # Garante os ids de produto_base antes de vincular os técnicos.
    db_session.flush()

    # Idempotência de produto_tecnico por produto_id.
    tec_existentes = {t.produto_id for t in db_session.query(ProdutoTecnico).all()}
    for t in dados["produto_tecnico"]:
        pid = t.get("produto_id")
        if pid in tec_existentes:
            resumo["tecnico_ignorados"] += 1
            continue
        if db_session.get(ProdutoBase, pid) is None:
            # produto_base não importado (não deveria ocorrer após validação)
            resumo["tecnico_ignorados"] += 1
            continue
        # forma_aplicacao mapeia para modo_aplicacao quando este não existir.
        modo = t.get("modo_aplicacao") or t.get("forma_aplicacao")
        db_session.add(ProdutoTecnico(
            produto_id=pid,
            grupo_quimico=t.get("grupo_quimico"),
            composicao=t.get("composicao"),
            nutrientes_principais=_to_json(t.get("nutrientes_principais")),
            culturas_comuns=_to_json(t.get("culturas_comuns")),
            alvos_controle=_to_json(t.get("alvos_controle")),
            uso_principal=t.get("uso_principal"),
            modo_aplicacao=modo,
            tipo_liberacao=t.get("tipo_liberacao"),
            fonte_tecnica=t.get("fonte_tecnica"),
            observacoes=t.get("observacoes"),
        ))
        tec_existentes.add(pid)
        resumo["tecnico_inseridos"] += 1

    db_session.commit()
    return resumo
