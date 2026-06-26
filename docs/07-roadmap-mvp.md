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

## Etapa 4.1 — Modelos e banco SQLite ⏳ (próxima etapa)

> **Próximo passo oficial:** criar os **modelos SQLAlchemy** com base no
> [DER](./04-modelagem-banco-der.md) e no
> [dicionário de dados](./05-dicionario-de-dados.md), **sem popular o banco e sem
> importar o seed de produtos ainda**.

- [ ] Modelos SQLAlchemy de domínio (`src/app/models/`).
- [ ] Criação real das tabelas (schema).
- [ ] Migrations (Flask-Migrate/Alembic).
- [ ] Importação do seed técnico do catálogo.
- [ ] Seed real / banco populado.

## Etapa 5 — Implementação dos módulos

Ordem sugerida (sujeita a ajuste):

- [ ] Login
- [ ] Dashboard
- [ ] Culturas
- [ ] Glebas
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

> Os **testes mínimos da fundação Flask já existem** em `tests/`
> (`test_app_factory.py`, `test_placeholder_routes.py`).

- [x] Testes mínimos da fundação (app factory, `/health`, rotas placeholders).
- [ ] Expandir os testes existentes em `tests/` para cobrir modelos, banco,
  autenticação, CRUDs, regras de negócio, seed técnico e fluxos principais.
- [ ] Revisão e ajustes do MVP.

---

## Documentos relacionados

- [01 — Escopo do Projeto](./01-escopo-do-projeto.md)
- [06 — Arquitetura do Sistema](./06-arquitetura-do-sistema.md)
- [06.1 — Arquitetura Técnica do MVP](./06-1-arquitetura-tecnica-mvp.md)
