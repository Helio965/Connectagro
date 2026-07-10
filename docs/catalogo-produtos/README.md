# Catálogo de Produtos

Esta pasta documenta o **catálogo técnico de produtos agrícolas** do ConnectAgro.

## Finalidade

O catálogo é uma **base técnica inicial** de **consulta rápida** e fonte futura
do seed do banco. Serve para:

- consulta rápida e organização de insumos;
- apoio ao registro futuro de aplicação de insumos;
- base inicial para o seed do banco configurado via ORM;
- documentação técnica do sistema.

Abrange as categorias: **Defensivos**, **Fertilizantes**, **Corretivos**,
**Inoculantes** e **Biofertilizantes**.

> O ConnectAgro **não vende produtos**. O catálogo **não** é loja nem marketplace.

## Documentos desta pasta

- **[catalogo-tecnico-connectagro-mvp.md](./catalogo-tecnico-connectagro-mvp.md)** —
  documento humano principal (tabelas de defensivos e fertilizantes, itens
  bloqueados, critérios, limitações e regras de uso no banco).
- **[pendencias-validacao.md](./pendencias-validacao.md)** — pendências de
  validação (AGROFIT/MAPA, SIPEAGRO/MAPA, preço, imagem, fabricante, fonte técnica).
- **Seed técnico:** [`data/seeds/connectagro_produtos_seed.json`](../../data/seeds/connectagro_produtos_seed.json)
  e [`...seed_compacto.csv`](../../data/seeds/connectagro_produtos_seed_compacto.csv).

## O que entra no MVP

- **`produto_base`** (id, slug, nome, classe, categoria, descrições, status) e
  **`produto_tecnico`** (dados técnicos): **preenchidos** como base técnica.
- **`produto_imagem`**: uma imagem local de referência por produto, com
  fonte/licença rastreadas e status não consolidado.
- 30 defensivos + 30 fertilizantes/corretivos/inoculantes pré-cadastrados.

## O que fica para o sistema final

- **`produto_preco`**: pendente / não consolidado no MVP (tabela vazia no seed).
- Imagens oficiais/do fabricante e eventual consolidação das referências atuais.
- **Validação diária do menor valor** atualizado de cada produto (com fonte,
  data, unidade, URL e status).
- Validação oficial **AGROFIT/MAPA** (defensivos) e **SIPEAGRO/MAPA**
  (fertilizantes).
- Separação formal entre **produto técnico/genérico** e **produto comercial
  específico**.

## Conceitos importantes

- **Defensivo × Fertilizante:** *defensivo* é agrotóxico/produto fitossanitário
  (inseticida, fungicida, herbicida, acaricida, moluscicida...); *fertilizante*
  é insumo nutricional (mineral, orgânico, organomineral) ou correção de solo.
- **Produto técnico × produto comercial:** no MVP os itens são **tipos
  técnicos/genéricos** (ingrediente ativo ou tipo de insumo), **não** marcas/
  produtos comerciais com fabricante. Fertilizantes como **Ureia, MAP, DAP,
  Calcário Dolomítico** entram como **tipo técnico/genérico**.
- **Validação regulatória:** **nenhum** defensivo tem validação oficial
  AGROFIT/MAPA dentro do repositório; `status_regulatorio` é **informativo**.

## Princípios obrigatórios

> Inegociáveis para qualquer dado adicionado aqui.

1. **Consulta, não venda.** Valores são apenas referência de consulta rápida.
2. **Preço é pendência; imagens exigem fonte/licença rastreável** — nunca inventados.
3. **Sem validação oficial inventada** (AGROFIT/MAPA ou SIPEAGRO/MAPA) sem fonte real.
4. **Base técnica, não verdade regulatória.**
5. **Validação diária de menor valor fica para o sistema final.**
6. **Não é receituário agronômico** — não substitui a orientação de um
   engenheiro agrônomo.

## Modelagem de referência

Tabelas `produto_base`, `produto_tecnico`, `produto_preco` e `produto_imagem` —
ver [DER](../04-modelagem-banco-der.md) e
[dicionário de dados](../05-dicionario-de-dados.md).

---

## Documentos relacionados

- [Catálogo Técnico (MVP)](./catalogo-tecnico-connectagro-mvp.md)
- [Pendências de Validação](./pendencias-validacao.md)
- [03 — Regras de Negócio](../03-regras-de-negocio.md)
- [04 — Modelagem do Banco (DER)](../04-modelagem-banco-der.md)
- [data/seeds](../../data/seeds/README.md)
