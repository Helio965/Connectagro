# tests/

Testes automatizados do **ConnectAgro** (pytest).

## Estado atual

Os testes usam a **Application Factory** (`create_app("testing")`) com banco
SQLite em memória e não dependem de banco `.db` real. Testes de upload usam pasta
temporária (`tmp_path`) para não escrever arquivos reais no repositório.

Arquivos principais:

- **`conftest.py`** — coloca `src/` no path; fixtures `app` e `client`.
- **`test_app_factory.py`** — criação da app no modo testing; `/health`; rota `/`.
- **`test_placeholder_routes.py`** — rotas públicas 200; rotas protegidas
  redirecionam sem login e respondem com login admin.
- **`test_models_schema.py`** — tabelas, colunas principais, `db.create_all()`,
  unicidade e tabelas de preço/imagem vazias.
- **`test_catalogo_seed.py`** — validação/importação idempotente do seed técnico.
- **`test_auth.py`** — login/logout, usuário inativo, sessão sem senha,
  `/health` público e `seed-users`.
- **`test_permissions.py`** — Fase 6.3: matriz de permissões por perfil,
  bloqueio backend com 403, menus/botões escondidos, rotas públicas preservadas,
  usuário sem login redirecionado, escopo por propriedade preservado e garantia
  de que ação sem permissão não cria registro.
- **`test_dashboard_operacional.py`** — Dashboard Operacional e escopo por
  propriedade.
- **`test_mapa_real.py`** — Mapa real simplificado e endpoint JSON.
- **`test_ia_simulada.py`** e **`test_ia_simulada_service.py`** — IA simulada por
  regras e histórico escopado.
- **`test_relatorios_operacionais.py`** e **`test_relatorios_service.py`** —
  relatórios HTML e serviços somente leitura.
- **`test_glebas_culturas_crud.py`** — CRUD de Glebas/Culturas e associação.
- **`test_equipe_financeiro_crud.py`** — CRUD de Equipe/Financeiro.
- **`test_colheita_crud.py`** — CRUD de Colheita.
- **`test_catalogo_consulta.py`** — consulta somente leitura do catálogo.
- **`test_aplicacoes_crud.py`** — CRUD de Aplicações de Insumo.
- **`test_upload_crud.py`** — Upload seguro, download e remoção.

Para rodar:

```bash
pytest
```

## Pendente para etapas futuras

- Testes de CSRF/Flask-WTF quando essa proteção entrar no escopo.
- Testes de fluxos completos finais do MVP.

## Convenções

- Arquivos de teste nomeados como `test_*.py`.
- Cada módulo do MVP deve ter testes correspondentes antes de ser considerado
  concluído.

---

## Documentos relacionados

- [02 — Requisitos do Sistema](../docs/02-requisitos-do-sistema.md)
- [06.1 — Arquitetura Técnica do MVP](../docs/06-1-arquitetura-tecnica-mvp.md)
- [07 — Roadmap do MVP](../docs/07-roadmap-mvp.md)
