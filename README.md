# ConnectAgro

Plataforma web de **gestão agrícola** para pequenos, médios e grandes produtores.
O ConnectAgro centraliza o controle de culturas, glebas, insumos, finanças,
equipe, colheita e mapa, oferecendo ainda apoio por uma camada de IA e um
catálogo técnico de produtos agrícolas para consulta rápida.

> **Status do projeto:** fundação Flask, **modelos SQLAlchemy** (15 tabelas),
> **migrations** (Flask-Migrate), **importação do catálogo técnico** (via CLI),
> **autenticação real** (login/logout), **CRUDs** de **Glebas**, **Culturas**
> (com associação cultura↔gleba), **Equipe**, **Financeiro** (com totais) e
> **Colheita**, além da **consulta somente leitura** do catálogo de
> **Defensivos** e **Fertilizantes** (busca, filtros e detalhe). Os demais
> módulos seguem como placeholders protegidos por login. Não há CRUD de produtos;
> `produto_preco`/`produto_imagem` continuam **vazios** no MVP (preço e imagem
> **pendentes** para o sistema final). O sistema **não vende produtos**; o banco
> populado **não** é versionado.

---

## Visão geral

O objetivo do ConnectAgro é dar ao produtor uma ferramenta simples e organizada
para acompanhar a operação da propriedade do plantio à colheita, com registro
financeiro, gestão de equipe e visualização em mapa.

O sistema será desenvolvido inicialmente como **MVP** (Produto Mínimo Viável) e,
em etapas posteriores, evoluirá para a versão completa.

### O que o ConnectAgro **é**

- Uma plataforma de **gestão e consulta**.
- Um catálogo técnico de produtos agrícolas usado como **base de consulta rápida**.

### O que o ConnectAgro **não é**

- O sistema **não vende** produtos.
- Os valores de produtos servem **apenas como consulta rápida**.
- O catálogo é uma **base técnica inicial**, não uma verdade regulatória definitiva.

> **Importante sobre dados de produtos:** no MVP, **preço e imagem** devem ser
> tratados como **pendência / dado não consolidado**. A validação diária do menor
> valor atualizado fica para o sistema final. Não há, neste momento, validação
> oficial AGROFIT/MAPA — nenhum produto deve ser apresentado como "validado
> oficialmente" sem fonte real comprovada.

---

## Módulos do MVP

| Módulo         | Descrição resumida                                              |
| -------------- | --------------------------------------------------------------- |
| Login          | Autenticação e controle de acesso                               |
| Dashboard      | Visão consolidada da propriedade                                |
| Culturas       | Cadastro e acompanhamento das culturas                          |
| Glebas         | Cadastro e gestão das áreas/talhões                             |
| Defensivos     | Consulta de defensivos a partir do catálogo                     |
| Fertilizantes  | Consulta de fertilizantes a partir do catálogo                  |
| Financeiro     | Registro de receitas e despesas                                 |
| Upload         | Envio e armazenamento de documentos/arquivos                    |
| Equipe         | Gestão de membros e funções                                     |
| Colheita       | Registro e acompanhamento de colheita                           |
| Mapa real      | Visualização das glebas em mapa                                 |
| IA simulada    | Camada de apoio por IA (respostas simuladas no MVP)             |
| Relatórios     | Geração de relatórios operacionais e financeiros                |

---

## Stack tecnológica (MVP)

- **Backend:** Python + Flask
- **Banco de dados:** SQLite
- **Frontend:** HTML, CSS, JavaScript

---

## Estrutura do repositório

```txt
.
├── docs/                  # Documentação do projeto (visão, escopo, requisitos, DER...)
│   └── catalogo-produtos/ # Documentação e especificação do catálogo de produtos
├── data/                  # Dados de apoio do projeto
│   └── seeds/             # Seed técnico do catálogo (JSON/CSV) — importável via CLI
├── migrations/            # Flask-Migrate/Alembic (migration inicial das 15 tabelas)
├── src/                   # Código-fonte da aplicação Flask
│   ├── run.py             # ponto de entrada
│   └── app/               # package Flask (Application Factory)
│       ├── __init__.py    # create_app
│       ├── config.py      # configuração por ambiente
│       ├── extensions.py  # extensões (Flask-SQLAlchemy, Flask-Migrate)
│       ├── blueprints/    # auth + CRUD (glebas/culturas/equipe/financeiro/colheita) + catálogo (defensivos/fertilizantes, leitura) + placeholders
│       ├── models/        # modelos SQLAlchemy de domínio (15 tabelas)
│       ├── commands.py    # CLI: init-db, validate/import-catalog-seed, seed-users
│       ├── services/      # regras de negócio (ex.: catalogo_seed.py)
│       ├── utils/         # utilitários (auth.py, contexto.py)
│       ├── templates/     # HTML (Jinja2)
│       └── static/        # css/, js/, uploads/
├── tests/                 # testes (pytest)
├── requirements.txt       # dependências
└── .env.example           # exemplo de variáveis de ambiente
```

A documentação detalhada está em [`docs/`](./docs). Comece pela
[Visão Geral](./docs/00-visao-geral.md).

## Como executar (MVP)

Fluxo recomendado, a partir da raiz do projeto:

```bash
# 1. Ambiente virtual
python -m venv .venv
# ative o ambiente conforme seu SO (ex.: source .venv/bin/activate)

# 2. Dependências
pip install -r requirements.txt

# 3. Schema do banco (migrations — Flask-Migrate/Alembic)
flask --app src/run.py db upgrade

# 4. Importar o catálogo técnico (opcional; idempotente)
flask --app src/run.py validate-catalog-seed
flask --app src/run.py import-catalog-seed

# 5. Criar os usuários de teste (idempotente)
flask --app src/run.py seed-users

# 6. Subir a aplicação
python src/run.py

# 7. Acessar /auth/login e entrar com um usuário de teste

# 8. Rodar os testes
pytest
```

O acesso exige **login** (sessão Flask + `werkzeug.security`): a rota `/` e os
módulos são protegidos e redirecionam para `/auth/login`; `/health` é público. O
arquivo de banco gerado **não** é versionado.

### Usuários de teste (`seed-users`)

| Perfil      | E-mail                       | Senha           |
| ----------- | ---------------------------- | --------------- |
| admin       | admin@connectagro.com        | admin123        |
| tecnico     | tecnico@connectagro.com      | tecnico123      |
| trabalhador | trabalhador@connectagro.com  | trabalhador123  |

> A importação do catálogo popula apenas `produto_base` + `produto_tecnico`;
> `produto_preco`/`produto_imagem` permanecem vazios no MVP e itens bloqueados
> (Paraquate/Oxamil) não são importados. Alternativa pontual ao passo 3 (sem
> migrations): `flask --app src/run.py init-db`.

### Documentação principal

- [00 — Visão Geral](./docs/00-visao-geral.md)
- [01 — Escopo do Projeto](./docs/01-escopo-do-projeto.md)
- [04 — Modelagem do Banco (DER)](./docs/04-modelagem-banco-der.md)
- [05 — Dicionário de Dados](./docs/05-dicionario-de-dados.md)
- [06 — Arquitetura do Sistema](./docs/06-arquitetura-do-sistema.md) — **visão conceitual**
- [06.1 — Arquitetura Técnica do MVP](./docs/06-1-arquitetura-tecnica-mvp.md) — **guia técnico para futura implementação**
- [07 — Roadmap do MVP](./docs/07-roadmap-mvp.md)
- [Catálogo de Produtos](./docs/catalogo-produtos/README.md) — inclui o [catálogo técnico](./docs/catalogo-produtos/catalogo-tecnico-connectagro-mvp.md) e o **seed técnico** ([`data/seeds/`](./data/seeds/README.md))

---

## Próximos passos

Concluídos: documentação de produto, modelagem (DER + dicionário), catálogo
técnico/seed, a **fundação Flask** e os **modelos SQLAlchemy de domínio** (15
tabelas; schema criável via `flask init-db`).

O **próximo passo não é o CRUD ainda**. A sequência prevista é:

1. ~~Criar os modelos SQLAlchemy~~ — **concluído** (`src/app/models/`).
2. Configurar **migrations** (Flask-Migrate) e importar o **catálogo de
   produtos**, que hoje permanece como **seed técnico/documental** (ainda **não**
   importado no banco). **Preço e imagem continuam pendentes** para a versão final.
3. Em seguida, autenticação e o **CRUD módulo a módulo**.

Consulte o [Roadmap do MVP](./docs/07-roadmap-mvp.md) para o detalhamento.

---

## Licença

A definir.
