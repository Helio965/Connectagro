# tests/

Testes automatizados do **ConnectAgro** (pytest).

## Estado atual

Os testes usam a **Application Factory** (`create_app("testing")`) com banco
**SQLite em memória** (ver `conftest.py`) e **não** dependem de banco `.db` real.

Arquivos existentes:

- **`conftest.py`** — coloca `src/` no path; fixtures `app` e `client`.
- **`test_app_factory.py`** — criação da app no modo testing; `/health`; rota `/`.
- **`test_placeholder_routes.py`** — as 14 rotas (incl. `/health` e placeholders)
  respondem HTTP 200.
- **`test_models_schema.py`** — registro das 15 tabelas no metadata; colunas
  principais; `db.create_all()`; inserção mínima (usuário, propriedade, produto
  base e técnico); unicidade de `usuario.email` e `produto_base.slug`;
  `produto_preco`/`produto_imagem` existem mas vazias; seed não importado
  automaticamente.
- **`test_catalogo_seed.py`** — Flask-Migrate inicializado sem quebrar a app;
  validação do seed (ids/slugs duplicados, FK inválida, preço/imagem não vazios);
  importação idempotente (popula `produto_base`/`produto_tecnico`, não popula
  preço/imagem, ignora itens bloqueados; listas salvas como JSON; campos
  `uso_principal`/`tipo_liberacao`).
- **`test_auth.py`** — autenticação: `/auth/login` (GET 200), login válido
  redireciona ao dashboard, senha errada não autentica (401), usuário inativo
  não loga (403), logout limpa a sessão, rotas protegidas redirecionam sem login,
  `/health` público, sessão sem senha, senha armazenada como hash, e
  `seed-users` idempotente (3 usuários, sem duplicar).

- **`test_glebas_culturas_crud.py`** — CRUD de Glebas e Culturas: criar/editar/
  remover, validação de nome obrigatório, associação cultura↔gleba (criação e
  sincronização na edição), escopo por propriedade (um usuário não acessa dados
  de outro → 404) e exigência de login.

> As rotas protegidas e a rota `/` são testadas também em
> `test_placeholder_routes.py` (redirecionam sem login; respondem 200 com login).

Para rodar: `pytest` (a partir da raiz do projeto).

## Pendente para etapas futuras

- Testes de **CRUDs** dos demais módulos (equipe, financeiro, colheita, upload).
- Testes de **permissões finas** por perfil/módulo.
- Testes de **regras de negócio** e **fluxos completos** do MVP.

## Convenções

- Arquivos de teste nomeados como `test_*.py`.
- Cada módulo do MVP deve ter testes correspondentes antes de ser considerado
  concluído.

---

## Documentos relacionados

- [02 — Requisitos do Sistema](../docs/02-requisitos-do-sistema.md)
- [06.1 — Arquitetura Técnica do MVP](../docs/06-1-arquitetura-tecnica-mvp.md)
- [07 — Roadmap do MVP](../docs/07-roadmap-mvp.md)
