# 00 — Visão Geral

## O que é o ConnectAgro

O ConnectAgro é uma **plataforma web de gestão agrícola** voltada para
pequenos, médios e grandes produtores. Seu propósito é centralizar, em um único
lugar, o acompanhamento da operação da propriedade — do planejamento das
culturas e glebas até a colheita —, somando a isso o controle financeiro, a
gestão de equipe, a visualização em mapa e uma camada de apoio por IA.

## Problema que resolve

A gestão agrícola costuma ficar dispersa entre planilhas, cadernos e sistemas
desconexos. O ConnectAgro propõe um ambiente organizado para:

- registrar e acompanhar **culturas** e **glebas**;
- consultar informações técnicas de **defensivos** e **fertilizantes**;
- controlar **receitas e despesas** da propriedade;
- gerenciar a **equipe** e o **fluxo de colheita**;
- visualizar as áreas em um **mapa**;
- centralizar **documentos** via upload;
- gerar **relatórios** de apoio à decisão.

## Público-alvo

Produtores rurais de pequeno, médio e grande porte e suas equipes de gestão.

## Princípios e limites do projeto

Estes princípios orientam todas as decisões de produto e devem ser respeitados
em todas as etapas:

1. **Não é uma loja.** O ConnectAgro não vende produtos. O catálogo serve para
   **consulta rápida** e referência técnica.
2. **Valores são consulta, não cotação oficial.** Os preços exibidos são
   referência. A validação diária do menor valor atualizado fica para o
   **sistema final**, não para o MVP.
3. **Preço e imagem no MVP são pendência.** Devem ser tratados como
   **dado não consolidado** enquanto não houver fonte confiável.
4. **Sem validação regulatória inventada.** Não se deve afirmar validação
   AGROFIT/MAPA nem dizer que um produto está "validado oficialmente" sem
   comprovação por fonte real.
5. **Catálogo é base técnica inicial.** Não é verdade regulatória definitiva.

## Stack do MVP

- **Backend:** Python + Flask
- **Banco de dados:** SQLite
- **Frontend:** HTML, CSS, JavaScript

## Documentos relacionados

- [01 — Escopo do Projeto](./01-escopo-do-projeto.md)
- [02 — Requisitos do Sistema](./02-requisitos-do-sistema.md)
- [03 — Regras de Negócio](./03-regras-de-negocio.md)
- [04 — Modelagem do Banco (DER)](./04-modelagem-banco-der.md)
- [05 — Dicionário de Dados](./05-dicionario-de-dados.md)
- [06 — Arquitetura do Sistema](./06-arquitetura-do-sistema.md)
- [07 — Roadmap do MVP](./07-roadmap-mvp.md)
- [Catálogo de Produtos](./catalogo-produtos/README.md)
