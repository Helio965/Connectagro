# 06.1 — Arquitetura Técnica do MVP

## Status do documento

**Arquitetura técnica — v0.17 (MVP com permissões finas por perfil).**

A Fase 6.3 adiciona autorização por perfil sem migration, sem alteração de model
e sem dependência nova. A matriz de permissões fica em
`src/app/utils/permissions.py` e é aplicada nas rotas por decorators, além de ser
refletida nos templates com `can()`.

---

## 1. Visão técnica geral

O MVP é uma aplicação web monolítica em Flask, renderizada no servidor com
Jinja2, usando SQLite e Flask-SQLAlchemy. A organização segue camadas simples:

```text
Navegador (HTML/CSS/JS)
        │
        ▼
Flask blueprints ──► services/helpers ──► modelos SQLAlchemy ──► SQLite
        │
        ▼
Templates Jinja2
```

Princípios mantidos:

- Application Factory em `src/app/__init__.py`.
- Blueprints por módulo.
- Rotas simples e serviços para agregações compartilhadas.
- Escopo por propriedade em todos os dados operacionais.
- Catálogo como consulta global somente leitura.
- Upload local fora de `static`.
- IA simulada por regras, sem LLM/API externa.
- Relatórios HTML somente leitura.
- Autenticação por sessão Flask + `werkzeug.security`.
- Autorização por perfil em código, sem RBAC externo.

---

## 2. Stack

| Camada | Tecnologia | Observações |
|---|---|---|
| Linguagem | Python 3.11+ | Testado também em Python 3.12 localmente |
| Framework | Flask | Application Factory + blueprints |
| Templates | Jinja2 | SSR |
| Banco | SQLite | Arquivo local em `instance/` |
| ORM | Flask-SQLAlchemy | Modelos em `src/app/models/` |
| Migrations | Flask-Migrate/Alembic | Migration inicial das 15 tabelas |
| Upload | Werkzeug `secure_filename` | Arquivos fora de `static` |
| Mapa | Leaflet.js via CDN | Sem dependência Python/NPM nova |
| Autenticação | Sessão Flask | `src/app/utils/auth.py` |
| Autorização | Matriz em código | `src/app/utils/permissions.py` |
| Testes | pytest | SQLite em memória |

---

## 3. Estrutura Flask

```text
src/
├── run.py
└── app/
    ├── __init__.py              # create_app, context processors, handlers de erro
    ├── config.py
    ├── extensions.py            # db, migrate
    ├── commands.py              # init-db, seed-users, catálogo
    ├── blueprints/              # auth, dashboard, CRUDs, catálogo, mapa, IA, relatórios
    ├── models/                  # 15 tabelas do domínio
    ├── services/                # dashboard, IA, relatórios, seed do catálogo
    ├── utils/                   # auth.py, contexto.py, catalogo.py, formatters.py, permissions.py
    ├── templates/               # base, módulos, erros
    └── static/                  # css/, js/

instance/
├── connectagro.db
└── uploads/
```

O banco SQLite real, `.env` e uploads de usuário não são versionados.

---

## 4. Application Factory

`create_app(config_name)` executa:

1. instancia Flask e carrega configuração;
2. inicializa `db` e `migrate`;
3. registra modelos no metadata;
4. registra blueprints;
5. registra comandos CLI;
6. injeta `current_user`, `is_authenticated` e `can` nos templates;
7. registra `/health`;
8. registra handlers 403, 404 e 500.

O handler 403 renderiza `templates/errors/403.html` com mensagem amigável, sem
vazar o nome interno da permissão.

---

## 5. Módulos e blueprints

| Módulo | Blueprint | Prefixo | Natureza |
|---|---|---|---|
| Login | `auth` | `/auth` | autenticação pública/login |
| Dashboard | `dashboard` | `/` | leitura operacional |
| Culturas | `culturas` | `/culturas` | CRUD |
| Glebas | `glebas` | `/glebas` | CRUD |
| Defensivos | `defensivos` | `/defensivos` | catálogo somente leitura |
| Fertilizantes | `fertilizantes` | `/fertilizantes` | catálogo somente leitura |
| Aplicações | `aplicacoes` | `/aplicacoes` | CRUD histórico operacional |
| Financeiro | `financeiro` | `/financeiro` | CRUD |
| Upload | `upload` | `/upload` | envio/download/remoção |
| Equipe | `equipe` | `/equipe` | CRUD |
| Colheita | `colheita` | `/colheita` | CRUD |
| Mapa | `mapa` | `/mapa` | leitura/JSON |
| IA | `ia` | `/ia` | apoio simulado |
| Relatórios | `relatorios` | `/relatorios` | HTML somente leitura |

---

## 6. Autenticação e autorização

### Autenticação

`src/app/utils/auth.py` mantém o fluxo existente:

- login/logout por sessão Flask;
- senha com hash Werkzeug;
- `login_required` redireciona usuário sem sessão para `/auth/login`;
- sessão guarda apenas `user_id`, `user_email`, `user_nome` e `user_perfil`.

### Permissões finas

`src/app/utils/permissions.py` concentra a autorização:

- `PERFIS_OFICIAIS = ("admin", "tecnico", "trabalhador")`;
- `PERMISSOES_POR_PERFIL` com strings explícitas (`glebas.create`,
  `financeiro.view`, `upload.delete`, etc.);
- `perfil_atual()` lê o perfil do usuário autenticado;
- `has_permission(permission)` retorna `True`/`False`;
- `can(permission)` é exposto aos templates;
- `require_permission(permission)` protege rotas e retorna 403 quando o usuário
  autenticado não possui a permissão.

A ordem usada nas rotas é consistente:

```python
@login_required
@require_permission("glebas.create")
def nova():
    ...
```

Mesmo com botões escondidos, a rota continua protegida no backend.

### Resumo da matriz

- `admin`: acessa todos os módulos e pode criar, editar e remover nos CRUDs da
  sua propriedade.
- `tecnico`: opera módulos agrícolas com criação/edição, visualiza equipe e
  financeiro, envia/baixa upload, mas não remove registros críticos nem gerencia
  equipe/financeiro.
- `trabalhador`: lê módulos operacionais, cria colheita/aplicação/upload e baixa
  upload, mas não edita/remove registros críticos e não acessa equipe/financeiro.

Permissões não alteram o escopo por propriedade: com permissão de ação, registros
de outra propriedade continuam retornando 404.

---

## 7. Templates

`base.html` exibe links do menu apenas quando `can("modulo.view")` permite.
Listagens escondem botões de criar/editar/remover/download conforme a permissão
correspondente.

Exemplos:

- `can("financeiro.create")` controla “Novo lançamento”.
- `can("upload.delete")` controla remoção de arquivo.
- `can("aplicacoes.edit")` controla edição de aplicação.

O Dashboard também usa `can()` nos atalhos rápidos e evita renderizar blocos de
Financeiro/Equipe para perfis que não podem visualizar esses módulos.

---

## 8. Escopo por propriedade

A autorização por perfil é uma camada adicional. O escopo por propriedade segue
nos módulos:

- Glebas, Culturas, Financeiro, Equipe e Upload filtram por `propriedade_id`.
- Colheita e Aplicações filtram por joins com `CulturaGleba`, `Cultura` e, quando
  necessário, `Gleba` da propriedade atual.
- Mapa retorna apenas glebas da propriedade atual.
- IA e Relatórios usam serviços com filtros pela propriedade atual.

---

## 9. Módulos concluídos

- Autenticação real.
- CRUDs de Glebas, Culturas, Equipe, Financeiro, Colheita, Aplicações e Upload.
- Consulta de Defensivos/Fertilizantes.
- Dashboard Operacional.
- Mapa real simplificado.
- IA Simulada Operacional.
- Relatórios Operacionais HTML.
- Permissões finas por perfil no MVP.

---

## 10. Testes

A suíte usa `create_app("testing")`, SQLite em memória e pasta temporária para
uploads.

Coberturas principais:

- autenticação e rotas públicas/protegidas;
- schema/modelos e seed do catálogo;
- CRUDs e escopo por propriedade;
- dashboard, mapa, IA e relatórios;
- upload seguro e download protegido;
- permissões finas por perfil em `tests/test_permissions.py`.

`tests/test_permissions.py` verifica:

- matriz de permissões de admin, técnico, trabalhador e perfil desconhecido;
- 403 no backend para ações não permitidas;
- usuário sem login redirecionando para login;
- rotas públicas preservadas;
- botões/links escondidos conforme `can()`;
- escopo por propriedade preservado;
- ausência de criação de registro em ação sem permissão.

---

## 11. Pendências do MVP

- CSRF/Flask-WTF.
- Revisão final do MVP.
- Melhorias futuras fora de escopo: painel de gestão de usuários, convites,
  recuperação de senha, permissões customizáveis em banco, auditoria completa,
  APIs externas, PDF/exportações avançadas.

---

## Documentos relacionados

- [00 — Visão Geral](./00-visao-geral.md)
- [02 — Requisitos do Sistema](./02-requisitos-do-sistema.md)
- [03 — Regras de Negócio](./03-regras-de-negocio.md)
- [04 — Modelagem do Banco (DER)](./04-modelagem-banco-der.md)
- [05 — Dicionário de Dados](./05-dicionario-de-dados.md)
- [07 — Roadmap do MVP](./07-roadmap-mvp.md)
- [Catálogo de Produtos](./catalogo-produtos/README.md)
