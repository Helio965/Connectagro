# data/seeds/

Dados de **carga inicial (seeds)** do ConnectAgro.

## Estado atual

> Os seeds aqui são **técnicos/documentais**. Já existem a **aplicação Flask**, os
> **modelos SQLAlchemy** (`src/app/models/`), **migrations** (Flask-Migrate) e
> comandos CLI para **validar** e **importar** o catálogo. A importação popula
> `produto_base` + `produto_tecnico` + `produto_imagem`; `produto_preco`
> permanece **vazio** no MVP e itens bloqueados (Paraquate/Oxamil) **não** são
> importados. O **banco populado não é versionado**. O menor valor diário fica
> para o **sistema final** (apenas consulta rápida — o ConnectAgro não vende).

## Comandos (a partir da raiz do projeto)

```bash
# 1. Aplicar o schema (migrations)
flask --app src/run.py db upgrade

# 2. Validar o seed técnico (não importa nada)
flask --app src/run.py validate-catalog-seed

# 3. Importar o catálogo técnico (idempotente: rodar 2x não duplica)
flask --app src/run.py import-catalog-seed
```

## Arquivos

- **`connectagro_produtos_seed.json`** — seed técnico do catálogo de produtos.
  Contém `produto_base`, `produto_tecnico` e `produto_imagem` **preenchidos**;
  `produto_preco` vazio; além de
  `itens_bloqueados_ou_excluidos` e `pendencias_validacao`.
- **`connectagro_produtos_seed_compacto.csv`** — visão compacta do `produto_base`
  com colunas `id,slug,nome,classe,categoria,status_sistema,status_regulatorio,
  fonte_tecnica,observacoes`.

## Regras dos seeds

1. O seed do MVP usa **`produto_base` + `produto_tecnico` + `produto_imagem`**.
2. **`produto_preco` permanece vazio**. `produto_imagem` contém uma referência
   local por produto, com fonte/licença rastreadas e status não consolidado.
3. **Sem dados inventados:** nenhum preço, fabricante, validação oficial ou
   imagem sem fonte/licença rastreável.
4. **Sem validação oficial não comprovada** (AGROFIT/MAPA, SIPEAGRO/MAPA).
5. Itens **bloqueados/excluídos** (ex.: Paraquate, Oxamil) ficam apenas em
   `itens_bloqueados_ou_excluidos` e **não** são oferecidos para registro de
   aplicação.
6. Estrutura alinhada ao [DER](../../docs/04-modelagem-banco-der.md) e ao
   [dicionário de dados](../../docs/05-dicionario-de-dados.md).
7. **`produto_tecnico.id` é omitido no JSON.** No banco, `produto_tecnico.id` é
   PK autoincremento; na importação pelo ORM, o banco configurado gera esse
   identificador automaticamente. No seed, o vínculo com o produto é feito apenas
   por **`produto_id`** (FK para `produto_base.id`).
8. **`status_regulatorio`** segue o enum oficial do MVP: `nao_validado_agrofit`,
   `atencao_regulatoria`, `sujeito_a_sipeagro_nao_validado`,
   `tipo_tecnico_generico`, `bloqueado_historico`.

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
assert d["produto_preco"] == [], "preco deve estar vazio no MVP"
assert {i["produto_id"] for i in d["produto_imagem"]} == base, "imagem ausente"
print("Seed OK:", len(d["produto_base"]), "produtos")
PY
```

---

## Documentos relacionados

- [Catálogo de Produtos](../../docs/catalogo-produtos/README.md)
- [Catálogo Técnico (MVP)](../../docs/catalogo-produtos/catalogo-tecnico-connectagro-mvp.md)
- [Pendências de Validação](../../docs/catalogo-produtos/pendencias-validacao.md)
- [Regras de Negócio](../../docs/03-regras-de-negocio.md)
