# Catálogo de Produtos

Esta pasta documenta o **catálogo técnico de produtos agrícolas** do ConnectAgro.

## Propósito

O catálogo é uma **base técnica inicial** de consulta rápida. Ele abrange as
seguintes categorias de produtos:

- Defensivos
- Fertilizantes
- Corretivos
- Inoculantes
- Biofertilizantes

## Princípios obrigatórios

> Estas regras são inegociáveis e valem para qualquer dado adicionado aqui.

1. **Consulta, não venda.** O ConnectAgro **não** vende produtos. Os valores são
   apenas referência de consulta rápida.
2. **Preço e imagem são pendência no MVP.** Quando não houver fonte confiável,
   esses campos devem ser marcados como **dado não consolidado** — nunca
   inventados.
3. **Sem validação oficial inventada.** Não afirmar validação **AGROFIT/MAPA**
   nem dizer que um produto está "validado oficialmente" sem **fonte real**
   comprovada.
4. **Base técnica, não verdade regulatória.** O catálogo não substitui consulta
   às fontes oficiais.
5. **Validação diária de menor valor fica para o sistema final**, não para o MVP.

## Estado atual

- ⚠️ **Nenhum dado de produto foi cadastrado ainda.**
- O catálogo **corrigido** (sem dados inventados) será fornecido em etapa
  posterior — ver [Roadmap, Etapa 3](../07-roadmap-mvp.md).
- Os dados de carga (seeds) ficarão em [`data/seeds/`](../../data/seeds/README.md)
  quando definidos.

## Modelagem de referência

O catálogo é modelado nas tabelas `produto_base`, `produto_tecnico`,
`produto_preco` e `produto_imagem` — ver
[DER](../04-modelagem-banco-der.md) e [dicionário de dados](../05-dicionario-de-dados.md).
Pontos-chave:

- `produto_base.status_regulatorio` controla a situação regulatória
  (`nao_validado`, `autorizado_sujeito_a_verificacao`, `sujeito_a_sipeagro`,
  `bloqueado`, `nao_se_aplica`). Defensivos nunca começam como "validado
  oficialmente".
- Fertilizantes genéricos (Ureia, MAP, DAP, Calcário Dolomítico) entram como
  **tipo técnico/genérico**, separáveis de produtos comerciais no futuro.
- `produto_preco` e `produto_imagem` têm `status_validacao` e ficam
  **pendentes** no MVP.

## Conteúdo previsto desta pasta

- Especificação dos campos de cada categoria de produto.
- Critérios de classificação e organização do catálogo.
- Marcação de campos pendentes (preço, imagem) e de origem dos dados.

---

## Documentos relacionados

- [03 — Regras de Negócio](../03-regras-de-negocio.md)
- [04 — Modelagem do Banco (DER)](../04-modelagem-banco-der.md)
- [data/seeds](../../data/seeds/README.md)
