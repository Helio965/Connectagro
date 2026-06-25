# data/

Pasta destinada aos **dados de apoio** do projeto ConnectAgro.

## Conteúdo

- [`seeds/`](./seeds/README.md) — dados de carga inicial (seeds) para popular o
  banco em desenvolvimento. **Ainda não definitivos.**

## Observações importantes

- O **banco de dados** (arquivos `.db`/`.sqlite`) **não** é versionado — ver
  [`.gitignore`](../.gitignore). Esta pasta guarda apenas dados de apoio em
  formatos versionáveis (ex.: `.csv`, `.json`), quando definidos.
- Nenhum dado de produto deve ser **inventado**. Preço e imagem, quando
  indisponíveis, são tratados como **pendência / não consolidado** (ver
  [Regras de Negócio](../docs/03-regras-de-negocio.md)).

## Estado atual

⚠️ Ainda **não há** seeds nem dados consolidados. O conteúdo será adicionado nas
próximas etapas do [roadmap](../docs/07-roadmap-mvp.md).
