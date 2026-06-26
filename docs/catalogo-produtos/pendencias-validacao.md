# Pendências de Validação — Catálogo de Produtos

> Registro das **pendências** do catálogo do ConnectAgro. Enquanto não
> resolvidas, os dados correspondentes **não** devem ser tratados como oficiais
> ou consolidados.
>
> ⚠️ **As informações deste catálogo não substituem a orientação de um
> engenheiro agrônomo nem o cadastro/bula oficial dos produtos.**

## 1. Validação AGROFIT/MAPA — Defensivos

- **Situação:** **pendente**. Nenhum defensivo foi validado oficialmente no
  AGROFIT/MAPA dentro do repositório.
- Todos os defensivos estão com `status_regulatorio = nao_validado_agrofit`
  (exceto Clorpirifós, marcado como `atencao_regulatoria`).
- **Ação futura:** verificar registro, culturas, alvos e doses na fonte oficial
  (AGROFIT) e na bula antes de qualquer afirmação de validação.

## 2. Validação SIPEAGRO/MAPA — Fertilizantes

- **Situação:** **pendente**.
- Fertilizantes minerais/comerciais estão com
  `status_regulatorio = sujeito_a_sipeagro_nao_validado`.
- Orgânicos genéricos estão com `status_regulatorio = tipo_tecnico_generico`.
- **Ação futura:** validar registro/regularização no SIPEAGRO/MAPA quando houver
  produto comercial específico associado.

## 3. Preço

- **Situação:** **pendente / não consolidado**. A tabela `produto_preco` está
  **vazia** no seed.
- No MVP **não** há busca automática de preço nem valor simulado tratado como
  oficial.
- A **validação diária do menor valor** atualizado é funcionalidade do **sistema
  final**, que deverá guardar **fonte, data, unidade, URL e status de validação**.

## 4. Imagem

- **Situação:** **pendente / não consolidada**. A tabela `produto_imagem` está
  **vazia** no seed.
- Nenhuma URL de imagem foi inventada. Imagens só poderão ser incluídas com
  **fonte/licença confiável** (preferencialmente oficial/do fabricante).

## 5. Fabricante / produto comercial

- **Situação:** **pendente**.
- Os itens estão como **tipo técnico/genérico**, sem fabricante nem produto
  comercial específico associado.
- A separação formal **produto técnico × produto comercial** fica para o
  **sistema final**.

## 6. Fonte técnica

- **Situação:** **pendente**.
- O campo `fonte_tecnica` contém **conhecimento técnico geral**, ainda **não
  validado** por fonte oficial (bula/AGROFIT/literatura referenciada).

---

## Observação final

Este documento é **base técnica para cadastro e consulta**, **não** é receituário
agronômico. Qualquer decisão de aplicação de insumos deve seguir a bula, a
legislação vigente e a orientação de um **engenheiro agrônomo** responsável.

## Documentos relacionados

- [Catálogo Técnico — ConnectAgro (MVP)](./catalogo-tecnico-connectagro-mvp.md)
- [Catálogo de Produtos — README](./README.md)
- [03 — Regras de Negócio](../03-regras-de-negocio.md)
