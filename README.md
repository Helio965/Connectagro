# ConnectAgro

Plataforma web de **gestão agrícola** para pequenos, médios e grandes produtores.
O ConnectAgro centraliza o controle de culturas, glebas, insumos, finanças,
equipe, colheita, upload de documentos e mapa, oferecendo ainda apoio por uma
camada de IA e um catálogo técnico de produtos agrícolas para consulta rápida.

> **Status do projeto:** fundação Flask, **modelos SQLAlchemy** (15 tabelas),
> **migrations** (Flask-Migrate), **importação do catálogo técnico** (via CLI),
> **autenticação real** (login/logout), **Dashboard Operacional** somente leitura,
> **Mapa real simplificado** somente leitura, **IA Simulada Operacional** baseada
> em regras locais, **CRUDs** de **Glebas**, **Culturas** (com associação
> cultura↔gleba), **Equipe**, **Financeiro** (com totais), **Colheita**,
> **Aplicações de Insumo** (registro histórico operacional) e **Upload de Arquivos**
> (armazenamento local com metadados), além da **consulta somente leitura** do
> catálogo de **Defensivos** e **Fertilizantes**. Relatórios seguem pendentes. Não
> há CRUD de produtos; `produto_preco`/`produto_imagem` continuam **vazios** no
> MVP. O sistema **não vende produtos**, não recomenda produtos, não valida dose,
> não usa LLM/API externa, não faz OCR/IA/extração automática de arquivos e não
> oferece recursos avançados de mapa; o banco populado e uploads reais **não** são
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
- Um dashboard operacional somente leitura para resumir dados já cadastrados.
- Um catálogo técnico de produtos agrícolas usado como **base de consulta rápida**.
- Um sistema para registrar aplicações de insumo como **histórico operacional**.
- Um sistema para armazenar localmente documentos da propriedade no MVP.
- Uma visualização simples das glebas em mapa, baseada nas coordenadas cadastradas.
- Uma IA simulada por regras para apoiar a leitura operacional dos dados locais da propriedade.

### O que o ConnectAgro **não é**

- O sistema **não vende** produtos.
- Os valores de produtos servem **apenas como consulta rápida**.
- O catálogo é uma **base técnica inicial**, não uma verdade regulatória definitiva.
- O registro de aplicação de insumo **não recomenda produtos** e **não valida dose**.
- A IA simulada **não** usa LLM/API externa, não substitui profissional habilitado,
  não recomenda produtos, não valida dose e não faz diagnóstico agronômico.
- O upload **não** faz OCR, IA, extração automática ou validação documental avançada.
- O mapa do MVP **não** mede área, não desenha polígonos e não usa GPS em tempo real.

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
| Dashboard      | Resumo operacional somente leitura da propriedade atual         |
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
| IA simulada    | Apoio operacional por regras, com histórico por propriedade     |
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
│       ├── blueprints/    # auth + CRUDs + catálogo + módulos protegidos
│       ├── models/        # modelos SQLAlchemy de domínio (15 tabelas)
│       ├── commands.py    # CLI: init-db, validate/import-catalog-seed, seed-users
│       ├── services/      # regras de negócio e agregações (ex.: dashboard_service.py, ia_simulada_service.py)
│       ├── utils/         # utilitários (auth.py, contexto.py, formatters.py)
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

### Dashboard operacional

O Dashboard em `/` é protegido por login e mostra um resumo somente leitura da
propriedade atual. Ele agrega dados já existentes de Glebas, Culturas,
Financeiro, Equipe, Colheita, Aplicações de Insumo, Upload e Catálogo.

Indicadores principais:

- total de glebas, área somada e glebas sem área informada;
- culturas por status e associações cultura↔gleba;
- receitas, despesas, saldo e últimos lançamentos financeiros;
- membros de equipe ativos/inativos;
- registros e somas de colheita por unidade;
- aplicações recentes como histórico operacional;
- total e tamanho aproximado dos uploads;
- totais globais do catálogo técnico por classe e produtos bloqueados/históricos.

O Dashboard não cria dados, não altera schema e não implementa gráficos externos.

### Mapa real simplificado

O módulo Mapa em `/mapa/` é protegido por login e mostra uma visualização somente
leitura das glebas da propriedade atual usando as coordenadas já cadastradas em
`Gleba.latitude` e `Gleba.longitude`. A rota `/mapa/dados` entrega JSON escopado
pela propriedade atual, sem dados de usuário/e-mail e separando glebas sem
coordenadas válidas.

O frontend usa Leaflet via CDN e renderiza marcadores. Quando `poligono_geojson`
contém GeoJSON válido, ele pode ser exibido em modo somente leitura; conteúdo
inválido é ignorado com segurança. A página continua renderizando mesmo sem
internet, embora o mapa visual dependa da biblioteca externa.

O módulo não cria, edita ou remove glebas, não altera schema, não usa PostGIS,
não mede área, não desenha polígonos, não importa/exporta GeoJSON e não usa GPS
em tempo real.

### IA simulada operacional

O módulo IA em `/ia/` é protegido por login e oferece apoio operacional por regras
simples. Ele usa dados locais já cadastrados na propriedade atual para responder
sobre resumo geral, financeiro, glebas, culturas, colheita, aplicações de insumo,
documentos e catálogo.

Cada pergunta/resposta válida é registrada em `ia_interacao` com `usuario_id`,
`propriedade_id`, `pergunta`, `resposta` e `tipo="simulada"`. O histórico exibido
mostra apenas as últimas interações do usuário e da propriedade atual.

A IA simulada não usa LLM, OpenAI, Claude, Gemini, API externa, internet ou
machine learning. Ela não recomenda produtos, não valida dose, não faz diagnóstico
agronômico, não consulta fontes oficiais em tempo real e não lê o conteúdo dos
arquivos enviados.

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
tabelas), migrations, autenticação real, Dashboard Operacional, Mapa real
simplificado, IA Simulada Operacional, CRUDs de glebas/culturas/equipe/financeiro/
colheita/aplicações de insumo/upload e consulta somente leitura de Defensivos/
Fertilizantes.

O **próximo passo recomendado** é implementar **Relatórios**, mantendo pendentes
permissões finas por perfil, CSRF dedicado e revisão final do MVP.

Consulte o [Roadmap do MVP](./docs/07-roadmap-mvp.md) para o detalhamento.

---

## Licença

A definir.
