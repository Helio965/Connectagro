# tests/

Testes automatizados do **ConnectAgro** (pytest).

## Estado atual

Os testes usam a **Application Factory** (`create_app("testing")`) com banco
**SQLite em memória** (ver `conftest.py`) e **não** dependem de banco `.db` real.

Arquivos existentes:

- **`conftest.py`** — coloca `src/` no path; fixtures `app` e `client`.
- **`test_app_factory.py`** — criação da app no modo testing; `/health`; rota `/`.
- **`test_placeholder_routes.py`** — rotas públicas respondem 200; rotas dos
  módulos protegidos redirecionam sem login e respondem 200 com login.
- **`test_models_schema.py`** — registro das 15 tabelas no metadata; colunas
  principais; `db.create_all()`; inserção mínima; unicidade de `usuario.email` e
  `produto_base.slug`; `produto_preco`/`produto_imagem` existem mas vazias; seed
  não importado automaticamente.
- **`test_catalogo_seed.py`** — Flask-Migrate inicializado sem quebrar a app;
  validação do seed (ids/slugs duplicados, FK inválida, preço/imagem não vazios);
  importação idempotente (popula `produto_base`/`produto_tecnico`, não popula
  preço/imagem, ignora itens bloqueados; listas salvas como JSON; campos
  `uso_principal`/`tipo_liberacao`).
- **`test_auth.py`** — autenticação: `/auth/login`, login válido, senha errada,
  usuário inativo, logout, rotas protegidas, `/health` público, sessão sem senha,
  senha armazenada como hash e `seed-users` idempotente.
- **`test_glebas_culturas_crud.py`** — CRUD de Glebas e Culturas, associação
  cultura↔gleba, escopo por propriedade e exigência de login.
- **`test_equipe_financeiro_crud.py`** — CRUD de Equipe e Financeiro, validações,
  totais financeiros, escopo por propriedade e exigência de login.
- **`test_colheita_crud.py`** — CRUD de Colheita, validação de `cultura_gleba_id`,
  data obrigatória, quantidade opcional com vírgula/ponto e > 0, escopo por
  propriedade, listagem, orientação sem associação e exigência de login.
- **`test_catalogo_consulta.py`** — consulta somente leitura do catálogo: exige
  login; listagens filtram por `classe`; busca e filtros; detalhe por slug e 404;
  ausência de termos de compra; aviso de preço/imagem pendentes; render de campos
  JSON; `produto_preco`/`produto_imagem` seguem vazios.
- **`test_aplicacoes_crud.py`** — CRUD de Aplicações de Insumo: exige login;
  cria/edita/remove aplicação válida; valida `cultura_gleba_id`, produto e data;
  bloqueia produto histórico por `status_sistema` ou `status_regulatorio`; impede
  cultura↔gleba de outra propriedade; aceita dose com vírgula/ponto e recusa dose
  inválida ou não positiva; garante 404 para acesso a aplicação de outra
  propriedade; exibe cultura, gleba, produto, dose, unidade e responsável; orienta
  quando faltam associação ou catálogo; evita ações de venda; e confirma que
  `ProdutoPreco`/`ProdutoImagem` não são criados.

> As rotas protegidas e a rota `/` são testadas também em
> `test_placeholder_routes.py` (redirecionam sem login; respondem 200 com login).

Para rodar: `pytest` (a partir da raiz do projeto).

## Pendente para etapas futuras

- Testes dos módulos ainda pendentes (Upload, Dashboard, Mapa real, IA simulada e
  Relatórios) quando forem implementados.
- Testes de **permissões finas** por perfil/módulo.
- Testes de **fluxos completos** do MVP.

## Convenções

- Arquivos de teste nomeados como `test_*.py`.
- Cada módulo do MVP deve ter testes correspondentes antes de ser considerado
  concluído.

---

## Documentos relacionados

- [02 — Requisitos do Sistema](../docs/02-requisitos-do-sistema.md)
- [06.1 — Arquitetura Técnica do MVP](../docs/06-1-arquitetura-tecnica-mvp.md)
- [07 — Roadmap do MVP](../docs/07-roadmap-mvp.md)
