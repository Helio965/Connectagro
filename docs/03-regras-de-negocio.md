# 03 — Regras de Negócio

> Documento-base. As regras abaixo consolidam as restrições já definidas para o
> projeto e serão expandidas conforme o detalhamento dos módulos.

## Como ler este documento

- **RN** = Regra de Negócio.

---

## Regras gerais do produto

- RN-01 — O ConnectAgro é uma plataforma de **gestão e consulta**; **não vende**
  produtos e **não** possui carrinho/checkout.
- RN-02 — Os valores de produtos têm finalidade de **consulta rápida** e não
  constituem cotação ou oferta de venda.

## Regras do catálogo de produtos

- RN-03 — O catálogo cobre defensivos, fertilizantes, corretivos, inoculantes e
  biofertilizantes, servindo como **base técnica inicial**.
- RN-04 — O catálogo **não** é verdade regulatória definitiva.
- RN-05 — No MVP, **preço** deve ser tratado como **pendência / dado não
  consolidado** quando não houver fonte confiável. Nunca inventar valores.
- RN-06 — No MVP, **imagem** do produto também é tratada como **pendência**
  quando indisponível.
- RN-07 — A **validação diária do menor valor atualizado** é responsabilidade do
  **sistema final**, não do MVP.
- RN-08 — **Não** afirmar validação **AGROFIT/MAPA** nem dizer que um produto
  está "validado oficialmente" sem comprovação por **fonte real**.
- RN-09 — Dados de produto sem origem confiável devem ser sinalizados como
  **não consolidados**, e não exibidos como definitivos.
- RN-09a — Cada produto possui um **`status_regulatorio`**
  (`nao_validado`, `autorizado_sujeito_a_verificacao`, `sujeito_a_sipeagro`,
  `bloqueado`, `nao_se_aplica`). **Defensivos** começam como `nao_validado` ou
  `autorizado_sujeito_a_verificacao` — **nunca** "validado oficialmente" sem
  fonte real.
- RN-09b — **Fertilizantes genéricos** (ex.: Ureia, MAP, DAP, Calcário
  Dolomítico) usam `nao_se_aplica` ou `sujeito_a_sipeagro`, como **tipo
  técnico/genérico**, separável de produtos comerciais específicos no futuro.
- RN-09c — **Paraquate**, se citado, é tratado como `bloqueado_historico` (uso
  proibido no Brasil), não recomendado. **Oxamil** não entra como produto
  recomendado no seed inicial.
- RN-09d — Preço (`produto_preco`) e imagem (`produto_imagem`) possuem
  **`status_validacao`**; no MVP ficam `pendente`/`nao_consolidado`.
- RN-09e — No **sistema final**, a validação diária do menor preço será apenas
  referência informativa e cada preço deverá registrar **fonte, data, unidade e
  status de validação**.

## Regras de acesso

- RN-10 — O acesso aos módulos exige **usuário autenticado**.
- RN-11 — Membros da equipe podem ter **funções** distintas, que poderão
  condicionar permissões (a detalhar).

## Regras operacionais (a detalhar)

- RN-12 — Uma **cultura** está associada a uma ou mais **glebas** (relação a ser
  formalizada no DER).
- RN-13 — Lançamentos **financeiros** classificam-se em **receita** ou
  **despesa**.
- RN-14 — Registros de **colheita** referenciam a cultura/gleba correspondente.

---

## Documentos relacionados

- [02 — Requisitos do Sistema](./02-requisitos-do-sistema.md)
- [04 — Modelagem do Banco (DER)](./04-modelagem-banco-der.md)
- [Catálogo de Produtos](./catalogo-produtos/README.md)
