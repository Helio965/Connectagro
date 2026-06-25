# 06 — Arquitetura do Sistema

> Documento-base. A arquitetura definitiva será detalhada conforme a
> implementação avança. Esta versão registra a direção pretendida para o MVP.
>
> **Este documento é a visão conceitual/geral.** O detalhamento técnico para a
> futura implementação (estrutura profissional Flask, fluxos, módulos, regras e
> checklist) está em
> [06.1 — Arquitetura Técnica do MVP](./06-1-arquitetura-tecnica-mvp.md).

## Visão geral

O ConnectAgro (MVP) será uma aplicação web monolítica baseada em **Flask**, com
banco **SQLite** e frontend renderizado em **HTML/CSS/JavaScript**. A
organização favorece a separação por módulos para facilitar evolução futura.

## Camadas

- **Apresentação (frontend):** páginas HTML com CSS e JavaScript; templates
  servidos pelo Flask.
- **Aplicação (backend):** rotas/controladores Flask por módulo, contendo a
  lógica de cada funcionalidade.
- **Domínio / regras:** regras de negócio aplicadas no backend (ver
  [03 — Regras de Negócio](./03-regras-de-negocio.md)).
- **Dados:** camada de acesso ao SQLite.

## Organização técnica

A estrutura técnica detalhada da futura implementação está documentada em
[06.1 — Arquitetura Técnica do MVP](./06-1-arquitetura-tecnica-mvp.md).

Este documento **06 não define a estrutura de pastas final** — ele apenas
apresenta a visão conceitual da arquitetura. A estrutura oficial planejada para
implementação deve seguir o documento 06.1.

De forma resumida e alinhada ao 06.1: a implementação futura deverá seguir o
padrão **Flask com Application Factory, Blueprints, camada de serviços, modelos e
templates**, conforme detalhado no documento 06.1.

## Decisões e restrições

- **Stack fixa no MVP:** Python/Flask, SQLite, HTML/CSS/JS.
- **IA simulada:** no MVP, o módulo de IA retorna respostas simuladas; não há
  integração com modelos em produção.
- **Catálogo como consulta:** sem venda; preço/imagem como pendência quando não
  consolidados.
- **Sem serviços externos obrigatórios:** o MVP deve rodar localmente de forma
  simples.

## Evolução futura

- Possível migração de SQLite para um SGBD mais robusto no sistema final.
- Integração de IA real e da validação diária de menor valor de produtos.

---

## Documentos relacionados

- [02 — Requisitos do Sistema](./02-requisitos-do-sistema.md)
- [04 — Modelagem do Banco (DER)](./04-modelagem-banco-der.md)
- [06.1 — Arquitetura Técnica do MVP](./06-1-arquitetura-tecnica-mvp.md)
- [07 — Roadmap do MVP](./07-roadmap-mvp.md)
