# 07 — Roadmap do MVP

> Documento-base. O roadmap orienta a sequência de trabalho e será ajustado a
> cada etapa concluída.

## Etapa 0 — Organização do repositório ✅ (em andamento)

- [x] README profissional.
- [x] Estrutura inicial de pastas (`docs/`, `data/`, `src/`, `tests/`).
- [x] Documentos-base em Markdown.
- [x] READMEs auxiliares nas pastas principais.
- [x] `.gitignore` para projeto Python/Flask.

## Etapa 1 — Documentação de produto ✅

- [x] Consolidar **escopo** definitivo.
- [x] Detalhar **requisitos** (RF/RNF) priorizados.
- [x] Fechar **regras de negócio**.

## Etapa 2 — Modelagem de dados ✅

- [x] Definir o **DER** oficial.
- [x] Preencher o **dicionário de dados**.

## Etapa 3 — Catálogo de produtos

- [x] Receber o **catálogo corrigido** (sem dados inventados) — ver
  [catálogo técnico](./catalogo-produtos/catalogo-tecnico-connectagro-mvp.md).
- [x] Definir formato dos dados em `data/seeds/`
  (`connectagro_produtos_seed.json` + `.csv`).
- [x] Tratar **preço e imagem** como pendência / não consolidado
  (`produto_preco`/`produto_imagem` vazios; ver
  [pendências](./catalogo-produtos/pendencias-validacao.md)).

## Etapa 4 — Fundação Flask da aplicação ✅

- [x] Aprovar arquitetura técnica do MVP ([06.1 — Arquitetura Técnica do MVP](./06-1-arquitetura-tecnica-mvp.md)).
- [x] Estruturar o projeto Flask em `src/` (`run.py` + `src/app/`).
- [x] Criar a **Application Factory** (`create_app`) e a configuração por ambiente.
- [x] Criar os **blueprints placeholders** dos módulos do MVP.
- [x] Criar o **layout base** (HTML/CSS/JS) e páginas de erro.
- [x] Criar a rota `/health`.
- [x] Criar **testes mínimos** (pytest).

> Adotado **Flask-SQLAlchemy** como ORM. O banco real **não** é versionado.

## Etapa 4.1 — Modelos e banco SQLite ✅

- [x] **Modelos SQLAlchemy de domínio** (`src/app/models/`, 15 tabelas).
- [x] **Schema validável** por `db.create_all()` nos testes e via `flask init-db`.

> Adotado **Flask-SQLAlchemy** como ORM. O banco real **não** é versionado.

## Etapa 4.2 — Migrations e importação do seed técnico ✅

- [x] **Flask-Migrate/Alembic** configurado (`migrations/` versionada).
- [x] **Migration inicial** das 15 tabelas (`flask db upgrade`).
- [x] **Validação** do seed técnico (`flask validate-catalog-seed`).
- [x] **Importação idempotente** do catálogo (`flask import-catalog-seed`):
  popula `produto_base` + `produto_tecnico`.
- [x] `produto_preco`/`produto_imagem` permanecem **vazios**; itens
  bloqueados (Paraquate/Oxamil) **não** importados.
- [x] `produto_preco`/`produto_imagem` permanecem **vazios**; itens
  bloqueados (Paraquate/Oxamil) **não** importados.

> O seed é **importado sob demanda** via CLI; o banco populado **não** é
> versionado. Preço e imagem seguem pendentes para o sistema final.

## Etapa 5.1 — Autenticação real ✅

- [x] Login/logout com **sessão Flask** + **werkzeug.security** (hash de senha).
- [x] Tela de login (`templates/auth/login.html`) e mensagens flash.
- [x] **Proteção de rotas** dos módulos (`@login_required`); `/health` público.
- [x] Usuário atual disponível nos templates (context processor).
- [x] Comando `flask seed-users` (idempotente) com perfis **admin/tecnico/trabalhador**.
- [x] Testes de autenticação (`tests/test_auth.py`).

> Sem cadastro público, recuperação de senha, JWT ou permissões finas por módulo
> (etapas futuras). Ainda **sem CRUD**.

## Etapa 5.2 — CRUD de Glebas e Culturas ✅

- [x] **CRUD de Glebas** (criar/listar/editar/remover), escopo por propriedade.
- [x] **CRUD de Culturas** (criar/listar/editar/remover) com `status`.
- [x] **Associação cultura↔gleba** (`cultura_gleba`) sincronizada no formulário.
- [x] Propriedade do usuário resolvida em `utils/contexto.py` (padrão criada se
  não existir).
- [x] Testes de CRUD e escopo (`tests/test_glebas_culturas_crud.py`).

> Cada usuário opera sobre sua propriedade; um usuário não acessa glebas/culturas
> de outro (404). Sem permissões finas por perfil ainda.

## Etapa 5 — Implementação dos módulos

Ordem sugerida (sujeita a ajuste):

- [x] Login (autenticação — ver Etapa 5.1)
- [ ] Dashboard
- [x] Culturas (CRUD — ver Etapa 5.2)
- [x] Glebas (CRUD — ver Etapa 5.2)
- [ ] Defensivos
- [ ] Fertilizantes
- [ ] Financeiro
- [ ] Upload
- [ ] Equipe
- [ ] Colheita
- [ ] Mapa real
- [ ] IA simulada
- [ ] Relatórios

## Etapa 6 — Testes e qualidade

> Já existem em `tests/`: testes da fundação (`test_app_factory.py`,
> `test_placeholder_routes.py`), de schema/modelos (`test_models_schema.py`) e de
> validação/importação do seed (`test_catalogo_seed.py`).

- [x] Testes da fundação (app factory, `/health`, rotas placeholders).
- [x] Testes de schema/modelos (15 tabelas, unicidade, schema validável).
- [x] Testes de validação e importação do seed técnico.
- [ ] Expandir os testes para **autenticação, CRUDs, regras de negócio e fluxos
  principais** do MVP.
- [ ] Revisão e ajustes do MVP.

---

## Documentos relacionados

- [01 — Escopo do Projeto](./01-escopo-do-projeto.md)
- [06 — Arquitetura do Sistema](./06-arquitetura-do-sistema.md)
- [06.1 — Arquitetura Técnica do MVP](./06-1-arquitetura-tecnica-mvp.md)
