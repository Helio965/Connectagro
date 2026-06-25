# 06 — Arquitetura Técnica do MVP

## Status do documento

**Arquitetura técnica — v0.1 (MVP).**

Este documento é a **fonte técnica** para a futura implementação do código Flask
do MVP. Ele detalha a stack, a organização do projeto, os padrões e as decisões
técnicas planejadas. **Nesta etapa nada é implementado**: não há código, banco,
migrations, seeds definitivos nem instalação de dependências — apenas o
planejamento.

> Complementa o documento conceitual [06 — Arquitetura do Sistema](./06-arquitetura-do-sistema.md):
> enquanto aquele descreve a visão de camadas em alto nível, **este** desce ao
> nível técnico de implementação (estrutura de pastas, blueprints, acesso a
> dados, configuração, segurança e testes). Deriva diretamente do
> [DER](./04-modelagem-banco-der.md), do [dicionário de dados](./05-dicionario-de-dados.md)
> e dos [requisitos](./02-requisitos-do-sistema.md).

## Objetivo

Definir **como** o MVP será construído tecnicamente, de modo que a próxima etapa
(implementação) tenha um guia claro e consistente com a documentação existente.

---

## 1. Visão geral da arquitetura

O MVP será uma **aplicação web monolítica** em **Flask**, renderizada no servidor
(Server-Side Rendering com Jinja2), com banco **SQLite** e frontend em
**HTML/CSS/JavaScript**. A organização segue uma separação por camadas e por
módulos (blueprints), favorecendo manutenção e evolução futura.

```text
Navegador (HTML/CSS/JS)
        │  HTTP
        ▼
Flask (rotas/blueprints)  ──►  Serviços (regras de negócio)  ──►  Modelos/Acesso a dados
        │                                                              │
        ▼                                                              ▼
   Templates Jinja2                                                SQLite (instance/)
```

### Princípios técnicos

- **Application Factory** (`create_app`) para criar a aplicação de forma
  configurável e testável.
- **Blueprints** para isolar cada módulo do MVP.
- **Separação de responsabilidades**: rotas finas, regras em serviços, acesso a
  dados na camada de modelos.
- **Configuração por ambiente** via variáveis de ambiente (`.env`), sem segredos
  versionados.
- Alinhamento total com os nomes de tabelas/campos do
  [dicionário de dados](./05-dicionario-de-dados.md).

---

## 2. Stack planejada

| Camada           | Tecnologia planejada                         | Observações                                    |
|------------------|----------------------------------------------|------------------------------------------------|
| Linguagem        | Python 3.11+                                 | Versão a confirmar na implementação            |
| Framework web    | Flask                                        | Monólito com blueprints                        |
| Templates        | Jinja2 (incluído no Flask)                   | SSR                                            |
| Banco de dados   | SQLite                                       | Arquivo local em `instance/`                   |
| Acesso a dados   | **Flask-SQLAlchemy (ORM)** — proposto        | Ver decisão em §6; alternativa: `sqlite3` puro |
| Migrations       | Flask-Migrate (Alembic) — **futuro**         | Não no MVP inicial                             |
| Autenticação     | Sessão Flask + hash de senha (Werkzeug)      | `werkzeug.security`                            |
| Formulários/CSRF | Flask-WTF — proposto                         | Proteção CSRF e validação                      |
| Frontend         | HTML, CSS, JavaScript                        | Sem framework JS obrigatório no MVP            |
| Mapa             | Biblioteca de mapa JS (ex.: Leaflet)         | Mapa real; começa simples                      |
| Testes           | pytest                                       | Ver §12                                        |

> As bibliotecas acima são **planejadas**, não instaladas nesta etapa. As versões
> exatas serão fixadas em `requirements.txt` na etapa de implementação.

---

## 3. Estrutura de pastas proposta (`src/`)

Estrutura sujeita a ajuste no início da implementação:

```text
src/
├── app.py                  # ponto de entrada / create_app (Application Factory)
├── config.py               # classes de configuração por ambiente
├── extensions.py           # instâncias de extensões (db, csrf, etc.)
├── models/                 # modelos de dados (espelham o DER)
│   ├── __init__.py
│   ├── usuario.py
│   ├── propriedade.py
│   ├── cultura.py
│   ├── gleba.py
│   ├── produto.py          # produto_base, produto_tecnico, produto_preco, produto_imagem
│   ├── financeiro.py
│   └── ...
├── blueprints/             # um pacote por módulo do MVP
│   ├── auth/               # login
│   ├── dashboard/
│   ├── culturas/
│   ├── glebas/
│   ├── defensivos/
│   ├── fertilizantes/
│   ├── financeiro/
│   ├── upload/
│   ├── equipe/
│   ├── colheita/
│   ├── mapa/
│   ├── ia/                 # IA simulada
│   └── relatorios/
├── services/               # regras de negócio reutilizáveis
├── templates/              # HTML (Jinja2), organizado por módulo
│   ├── base.html
│   └── <modulo>/...
├── static/                 # CSS, JS, imagens
│   ├── css/
│   ├── js/
│   └── uploads/            # arquivos enviados (conteúdo ignorado no git)
└── utils/                  # helpers (datas, validações, etc.)
```

> Cada blueprint conterá tipicamente `routes.py` (rotas), podendo ter `forms.py`
> e `services.py` próprios quando fizer sentido.

---

## 4. Padrão de aplicação: Application Factory + Blueprints

- `create_app(config_name)` em `app.py` instancia o Flask, carrega a
  configuração, inicializa as extensões (`db`, CSRF, etc.) e registra todos os
  blueprints.
- Cada **blueprint** corresponde a um módulo do MVP, com URL prefix próprio
  (ex.: `/culturas`, `/financeiro`).
- Vantagens: testabilidade (criar app de teste com config isolada), isolamento de
  módulos e clareza de roteamento.

---

## 5. Mapeamento de módulos → blueprints

| Módulo (MVP)  | Blueprint        | Prefixo sugerido | Entidades principais (DER)                          |
|---------------|------------------|------------------|-----------------------------------------------------|
| Login         | `auth`           | `/auth`          | `usuario`                                           |
| Dashboard     | `dashboard`      | `/`              | agregações de várias entidades                      |
| Culturas      | `culturas`       | `/culturas`      | `cultura`, `cultura_gleba`                          |
| Glebas        | `glebas`         | `/glebas`        | `gleba`, `cultura_gleba`                            |
| Defensivos    | `defensivos`     | `/defensivos`    | `produto_base` (classe defensivo) + `produto_*`     |
| Fertilizantes | `fertilizantes`  | `/fertilizantes` | `produto_base` (classe fertilizante) + `produto_*`  |
| Financeiro    | `financeiro`     | `/financeiro`    | `financeiro_lancamento`                             |
| Upload        | `upload`         | `/upload`        | `upload_arquivo`                                    |
| Equipe        | `equipe`         | `/equipe`        | `equipe_membro`                                     |
| Colheita      | `colheita`       | `/colheita`      | `colheita_registro`, `cultura_gleba`               |
| Mapa real     | `mapa`           | `/mapa`          | `gleba` (`latitude`/`longitude`/`poligono_geojson`) |
| IA simulada   | `ia`             | `/ia`            | `ia_interacao`                                      |
| Relatórios    | `relatorios`     | `/relatorios`    | leitura de múltiplas entidades                      |

> Defensivos e fertilizantes consultam o **mesmo** catálogo (`produto_base`),
> filtrando por `classe`. Não há venda — apenas consulta rápida, organização e
> registro de aplicação via `aplicacao_insumo`.

---

## 6. Acesso a dados e banco SQLite

- **Banco:** arquivo SQLite em `instance/connectagro.db` (a pasta `instance/` e
  arquivos `*.db` já estão no [.gitignore](../.gitignore); o banco **não** é
  versionado).
- **Decisão proposta:** usar **Flask-SQLAlchemy** como ORM, mapeando os modelos
  diretamente às tabelas do [dicionário de dados](./05-dicionario-de-dados.md).
  - *Justificativa:* o DER tem ~15 tabelas com vários relacionamentos; um ORM
    reduz SQL repetitivo, melhora manutenção e facilita testes.
  - *Alternativa registrada:* `sqlite3` puro com uma fina camada de repositório,
    caso se queira minimizar dependências. **A decisão final fica para o início
    da implementação.**
- **Tipos:** seguir o dicionário — `TEXT` para datas (ISO 8601), `BOOLEAN` como
  `0/1`, listas como `TEXT`/JSON no MVP (normalização futura).
- **Migrations:** não no MVP inicial (o schema nasce dos modelos). Flask-Migrate
  poderá ser adotado quando o schema estabilizar. **Nenhuma migration é criada
  nesta etapa.**
- **Seeds:** o seed definitivo **ainda não existe** (ver
  [data/seeds/README.md](../data/seeds/README.md)); preço e imagem
  permanecem pendentes.

---

## 7. Autenticação, sessão e perfis

- Login por e-mail e senha; senha verificada contra `usuario.senha_hash`.
- Hash com `werkzeug.security` (`generate_password_hash` /
  `check_password_hash`) — **nunca** senha em texto puro.
- Sessão via cookie de sessão do Flask (assinado por `SECRET_KEY`).
- Controle de acesso baseado em `usuario.perfil` (`admin`, `produtor`, `membro`)
  e, futuramente, em `equipe_membro.funcao`. No MVP, um decorator simples de
  "login obrigatório" protege as rotas.

---

## 8. Configuração e variáveis de ambiente

- `config.py` com classes por ambiente: `DevelopmentConfig`, `TestingConfig`,
  `ProductionConfig` (base comum).
- Variáveis sensíveis em `.env` (não versionado; haverá `.env.example`):
  - `SECRET_KEY`
  - `DATABASE_URL` ou caminho do SQLite
  - `FLASK_ENV` / `FLASK_DEBUG`
  - `UPLOAD_FOLDER`, limites de upload
- A aplicação seleciona a config pelo ambiente; testes usam `TestingConfig` com
  banco isolado (ex.: SQLite em memória).

---

## 9. Catálogo de produtos (consulta)

- Consulta a `produto_base` + `produto_tecnico`, filtrando por `classe`/
  `categoria`, com busca por `nome`/`slug`.
- **Preço** (`produto_preco`) e **imagem** (`produto_imagem`) são exibidos como
  **pendência / não consolidado** quando `status_validacao` não estiver
  consolidado — a UI deve deixar isso explícito e **nunca** inventar valores.
- `status_regulatorio` é apenas informativo; defensivos **nunca** são exibidos
  como "validado oficialmente" sem fonte real (sem validação AGROFIT/MAPA
  presumida). Itens como Paraquate aparecem como `bloqueado_historico`.
- A validação diária do menor preço é do **sistema final**, fora do escopo do MVP.

---

## 10. Serviços especiais do MVP

### IA simulada (`blueprints/ia` + `services`)
- Camada de serviço que recebe a pergunta e retorna uma **resposta simulada**
  (regras/templates fixos), persistindo em `ia_interacao`.
- **Não** emite recomendação agronômica definitiva; apenas apoio informativo e
  organizacional. Sem chamada a modelos externos no MVP.

### Upload de arquivos (`blueprints/upload`)
- Salva arquivos em `static/uploads/` (ou `UPLOAD_FOLDER`), registrando metadados
  em `upload_arquivo` (`nome_original`, `caminho`, `tipo_mime`, `tamanho`).
- Validar extensão/tamanho e usar `secure_filename`. O conteúdo enviado é
  ignorado pelo git.

### Mapa real (`blueprints/mapa`)
- Frontend com biblioteca de mapa (ex.: Leaflet) consumindo `latitude`/
  `longitude` e `poligono_geojson` das glebas. No MVP pode começar simples
  (ponto/lista), evoluindo para polígonos.

### Relatórios (`blueprints/relatorios`)
- Leitura agregada de culturas, glebas, financeiro e colheita, renderizada em
  HTML (exportação ex.: CSV/PDF pode ser incremental).

---

## 11. Frontend (templates e estáticos)

- Templates Jinja2 com `base.html` (layout, navegação) e templates por módulo.
- CSS e JS próprios em `static/`; sem dependência obrigatória de framework JS.
- Mensagens ao usuário via *flash messages* do Flask.

---

## 12. Testes

- **pytest** com app criado via `create_app('testing')` e banco isolado.
- Organização em `tests/` espelhando `src/` (ver [tests/README.md](../tests/README.md)).
- Prioridade: regras de negócio e fluxos críticos (autenticação, financeiro,
  catálogo/consulta, registro de aplicação de insumo).
- Convenção: arquivos `test_*.py`; cada módulo deve ter testes antes de ser
  considerado concluído.

---

## 13. Segurança (MVP)

- Senhas com hash (Werkzeug); `SECRET_KEY` forte via ambiente.
- **CSRF** em formulários (Flask-WTF proposto).
- Validação de entrada e *escaping* automático do Jinja2 contra XSS.
- Uploads validados (extensão, tamanho, `secure_filename`).
- Sem dados sensíveis no repositório (`.env` ignorado).

---

## 14. Tratamento de erros e logging

- Páginas de erro amigáveis (404/500) via handlers do Flask.
- Logging configurável por ambiente (nível maior em produção); logs não
  versionados (já ignorados no `.gitignore`).

---

## 15. Decisões em aberto e pendências

- **ORM vs. `sqlite3` puro** (§6) — decisão final na implementação.
- Versões exatas das dependências (`requirements.txt`).
- Estratégia de migrations (adoção de Flask-Migrate e quando).
- Biblioteca de mapa definitiva e nível de detalhe do mapa no MVP.
- Formato de exportação de relatórios.
- Modelo de permissões detalhado por `perfil`/`funcao`.

---

## Documentos relacionados

- [02 — Requisitos do Sistema](./02-requisitos-do-sistema.md)
- [04 — Modelagem do Banco (DER)](./04-modelagem-banco-der.md)
- [05 — Dicionário de Dados](./05-dicionario-de-dados.md)
- [06 — Arquitetura do Sistema (visão conceitual)](./06-arquitetura-do-sistema.md)
- [07 — Roadmap do MVP](./07-roadmap-mvp.md)
