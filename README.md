# ConnectAgro

Plataforma web de **gestão agrícola** para pequenos, médios e grandes produtores.
O ConnectAgro centraliza o controle de culturas, glebas, insumos, finanças,
equipe, colheita, upload de documentos e mapa, oferecendo ainda apoio por uma
camada de IA e um catálogo técnico de produtos agrícolas para consulta rápida.

> **Status do projeto:** fundação Flask, **modelos SQLAlchemy** (15 tabelas),
> **migrations** (Flask-Migrate), **importação do catálogo técnico** (via CLI),
> **autenticação real** (login/logout), **CRUDs** de **Glebas**, **Culturas**
> (com associação cultura↔gleba), **Equipe**, **Financeiro** (com totais),
> **Colheita**, **Aplicações de Insumo** (registro histórico operacional) e
> **Upload de Arquivos** (armazenamento local com metadados), além da **consulta
> somente leitura** do catálogo de **Defensivos** e **Fertilizantes**. Dashboard,
> Mapa, IA e Relatórios seguem pendentes. Não há CRUD de produtos;
> `produto_preco`/`produto_imagem` continuam **vazios** no MVP. O sistema **não
> vende produtos**, não recomenda produtos, não valida dose e não faz OCR/IA/
> extração automática de arquivos; o banco populado e uploads reais **não** são
> versionados.

---

## Visão geral

O objetivo do ConnectAgro é dar ao produtor uma ferramenta simples e organizada
para acompanhar a operação da propriedade do plantio à colheita, com registro
financeiro, gestão de equipe, documentos e visualização em mapa.

O sistema será desenvolvido inicialmente como **MVP** (Produto Mínimo Viável) e,
em etapas posteriores, evoluirá para a versão completa.

### O que o ConnectAgro **é**

- Uma plataforma de **gestão e consulta**.
- Um catálogo técnico de produtos agrícolas usado como **base de consulta rápida**.
- Um sistema para registrar aplicações de insumo como **histórico operacional**.
- Um sistema para armazenar localmente documentos da propriedade no MVP.

### O que o ConnectAgro **não é**

- O sistema **não vende** produtos.
- Os valores de produtos servem **apenas como consulta rápida**.
- O catálogo é uma **base técnica inicial**, não uma verdade regulatória definitiva.
- O registro de aplicação de insumo **não recomenda produtos** e **não valida dose**.
- O upload **não** faz OCR, IA, extração automática ou validação documental avançada.

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
| Aplicações     | Registro histórico operacional de aplicações de insumo          |
| Financeiro     | Registro de receitas e despesas                                 |
| Upload         | Envio, listagem, download e remoção de arquivos da propriedade  |
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
├── instance/              # Banco SQLite e uploads locais em execução — não versionado
├── src/                   # Código-fonte da aplicação Flask
│   ├── run.py             # ponto de entrada
│   └── app/               # package Flask (Application Factory)
│       ├── __init__.py    # create_app
│       ├── config.py      # configuração por ambiente
│       ├── extensions.py  # extensões (Flask-SQLAlchemy, Flask-Migrate)
│       ├── blueprints/    # auth + CRUDs + catálogo + placeholders protegidos
│       ├── models/        # modelos SQLAlchemy de domínio (15 tabelas)
│       ├── commands.py    # CLI: init-db, validate/import-catalog-seed, seed-users
│       ├── services/      # regras de negócio (ex.: catalogo_seed.py)
│       ├── utils/         # utilitários (auth.py, contexto.py)
│       ├── templates/     # HTML (Jinja2)
│       └── static/        # css/, js/ (arquivos públicos)
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

### Upload de arquivos

O módulo Upload armazena arquivos localmente no MVP usando
`UPLOAD_FOLDER` (`instance/uploads` por padrão), em subpastas por propriedade
(`propriedade_<id>/`). Essa pasta padrão fica fora de `src/app/static`, então os
arquivos enviados não são servidos diretamente por `/static/uploads`; o acesso
continua passando pela rota protegida de download, com validação da propriedade.

O banco guarda apenas metadados e caminho relativo seguro; arquivos reais
enviados por usuários são ignorados pelo Git.

Extensões permitidas no MVP: `pdf`, `png`, `jpg`, `jpeg`, `csv`, `xlsx`, `txt` e
`docx`. Executáveis, scripts, compactados e HTML/PHP/Python são bloqueados pela
allowlist. O módulo não faz OCR, IA, leitura automática, classificação ou
extração de dados.

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
técnico/seed, a **fundação Flask**, os **modelos SQLAlchemy de domínio** (15
tabelas), migrations, autenticação real, CRUDs de glebas/culturas/equipe/
financeiro/colheita/aplicações de insumo/upload e consulta somente leitura de
Defensivos/Fertilizantes.

O **próximo passo recomendado** é implementar o **Dashboard operacional**,
mantendo pendentes Mapa real, IA simulada, Relatórios, permissões finas por perfil
e CSRF dedicado.

Consulte o [Roadmap do MVP](./docs/07-roadmap-mvp.md) para o detalhamento.

---

## Licença

A definir.
