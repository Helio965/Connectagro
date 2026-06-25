# tests/

Testes automatizados do **ConnectAgro**.

## Estado atual

> ⚠️ **Ainda não há testes implementados.** Eles serão adicionados quando a
> implementação do código começar — após a aprovação da
> [arquitetura técnica](../docs/06-1-arquitetura-tecnica-mvp.md) (ver
> [Roadmap, Etapa 6](../docs/07-roadmap-mvp.md)).

## Abordagem planejada

- **Framework:** `pytest`.
- App de teste criado via **Application Factory** (`create_app('testing')`) com
  banco isolado (ex.: SQLite em memória).
- Estrutura espelhando o package da aplicação (`src/app/`), por módulo/blueprint.
- Cobertura priorizando regras de negócio e fluxos críticos
  (autenticação, financeiro, catálogo/consulta, registro de aplicação de insumo).

## Convenções (planejadas)

- Arquivos de teste nomeados como `test_*.py`.
- Cada módulo do MVP deve ter testes correspondentes antes de ser considerado
  concluído.

---

## Documentos relacionados

- [02 — Requisitos do Sistema](../docs/02-requisitos-do-sistema.md)
- [06.1 — Arquitetura Técnica do MVP](../docs/06-1-arquitetura-tecnica-mvp.md)
- [07 — Roadmap do MVP](../docs/07-roadmap-mvp.md)
