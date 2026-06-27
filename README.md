# ConnectAgro

Plataforma web de **gestão agrícola** para pequenos, médios e grandes produtores.
O ConnectAgro centraliza o controle de culturas, glebas, insumos, finanças,
equipe, colheita e mapa, oferecendo ainda apoio por uma camada de IA e um
catálogo técnico de produtos agrícolas para consulta rápida.

> **Status do projeto:** fundação Flask criada e **modelos SQLAlchemy de domínio
> implementados** (15 tabelas). O projeto ainda **não** possui banco populado,
> CRUD, migrations, seed importado nem autenticação real — os módulos seguem como
> placeholders. Preço e imagem do catálogo continuam **pendentes** para o sistema
> final.

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
│   └── seeds/             # Seed técnico do catálogo (JSON/CSV) — não importado ainda
├── src/                   # Código-fonte da aplicação Flask
│   ├── run.py             # ponto de entrada
│   └── app/               # package Flask (Application Factory)
│       ├── __init__.py    # create_app
│       ├── config.py      # configuração por ambiente
│       ├── extensions.py  # extensões (Flask-SQLAlchemy)
│       ├── blueprints/    # um blueprint por módulo do MVP (placeholders)
│       ├── models/        # modelos SQLAlchemy de domínio (15 tabelas)
│       ├── commands.py    # CLI: flask init-db (cria schema, sem popular)
│       ├── services/      # regras de negócio (vazio nesta etapa)
│       ├── utils/         # utilitários (vazio nesta etapa)
│       ├── templates/     # HTML (Jinja2)
│       └── static/        # css/, js/, uploads/
├── tests/                 # testes (pytest)
├── requirements.txt       # dependências
└── .env.example           # exemplo de variáveis de ambiente
```

A documentação detalhada está em [`docs/`](./docs). Comece pela
[Visão Geral](./docs/00-visao-geral.md).

## Como executar (MVP)

```bash
python -m venv .venv
# ative o ambiente conforme seu SO (ex.: source .venv/bin/activate)
pip install -r requirements.txt
python src/run.py
```

A aplicação sobe com a rota inicial `/`, o health check `/health` e as páginas
placeholder dos módulos. Para rodar os testes: `pytest`.

### Criar o schema do banco (opcional)

O comando abaixo cria as tabelas no SQLite (a partir da raiz do projeto), **sem
popular dados e sem importar o seed**. O arquivo de banco gerado **não** é
versionado.

```bash
flask --app src/run.py init-db
```

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
