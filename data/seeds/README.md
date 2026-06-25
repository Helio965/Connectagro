# data/seeds/

Dados de **carga inicial (seeds)** do ConnectAgro.

## Estado atual

> Os seeds aqui são **técnicos/documentais** — base para a futura criação do
> banco. **Ainda não há banco, migrations nem aplicação.** Preço e imagem **não**
> entram como dados consolidados no MVP.

## Arquivos

- **`connectagro_produtos_seed.json`** — seed técnico do catálogo de produtos.
  Contém `produto_base` e `produto_tecnico` **preenchidos**; `produto_preco` e
  `produto_imagem` **vazios** (pendência do MVP); além de
  `itens_bloqueados_ou_excluidos` e `pendencias_validacao`.
- **`connectagro_produtos_seed_compacto.csv`** — visão compacta do `produto_base`
  com colunas `id,slug,nome,classe,categoria,status_sistema,status_regulatorio,
  fonte_tecnica,observacoes`.

## Regras dos seeds

1. O seed do MVP deve usar **`produto_base` + `produto_tecnico`**.
2. **`produto_preco` e `produto_imagem` são estruturas futuras** — permanecem
   **vazias** no MVP (preço/imagem não consolidados).
3. **Sem dados inventados:** nenhum preço, imagem, fabricante ou fonte oficial
   fictícios.
4. **Sem validação oficial não comprovada** (AGROFIT/MAPA, SIPEAGRO/MAPA).
5. Itens **bloqueados/excluídos** (ex.: Paraquate, Oxamil) ficam apenas em
   `itens_bloqueados_ou_excluidos` e **não** são oferecidos para registro de
   aplicação.
6. Estrutura alinhada ao [DER](../../docs/04-modelagem-banco-der.md) e ao
   [dicionário de dados](../../docs/05-dicionario-de-dados.md).

## Como validar o JSON antes de usar

Antes de utilizar o seed (ex.: ao iniciar a futura implementação), verifique:

```bash
# 1. JSON válido
python3 -m json.tool data/seeds/connectagro_produtos_seed.json > /dev/null && echo "JSON OK"

# 2. Sem ids/slugs duplicados e FKs íntegras (produto_tecnico.produto_id -> produto_base.id)
python3 - <<'PY'
import json
d = json.load(open("data/seeds/connectagro_produtos_seed.json"))
ids = [p["id"] for p in d["produto_base"]]
slugs = [p["slug"] for p in d["produto_base"]]
assert len(ids) == len(set(ids)), "ids duplicados"
assert len(slugs) == len(set(slugs)), "slugs duplicados"
base = set(ids)
assert all(t["produto_id"] in base for t in d["produto_tecnico"]), "FK invalida"
assert d["produto_preco"] == [] and d["produto_imagem"] == [], "preco/imagem devem estar vazios no MVP"
print("Seed OK:", len(d["produto_base"]), "produtos")
PY
```

---

## Documentos relacionados

- [Catálogo de Produtos](../../docs/catalogo-produtos/README.md)
- [Catálogo Técnico (MVP)](../../docs/catalogo-produtos/catalogo-tecnico-connectagro-mvp.md)
- [Pendências de Validação](../../docs/catalogo-produtos/pendencias-validacao.md)
- [Regras de Negócio](../../docs/03-regras-de-negocio.md)
