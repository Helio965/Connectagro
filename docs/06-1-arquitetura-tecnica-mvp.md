# 06.1 — Arquitetura Técnica do MVP

## Status do documento

**Arquitetura técnica — v0.3 (fundação Flask criada; próxima etapa: modelos
SQLAlchemy).**

Este documento **complementa** o [06 — Arquitetura do Sistema](./06-arquitetura-do-sistema.md):

- O documento **06** é a **visão conceitual/geral** (camadas em alto nível).
- O documento **06.1** (este) é o **guia técnico detalhado** da implementação do
  MVP em Flask.

> **Estado atual:** a **fundação Flask já foi criada** (`src/run.py` + `src/app/`
> com Application Factory, blueprints placeholders, layout base, `/health`),
> já há **dependências declaradas** em [`requirements.txt`](../requirements.txt)
> e **testes mínimos** em `tests/`.
>
> **Ainda NÃO existem:** CRUDs reais, modelos SQLAlchemy de domínio, banco
> populado, migrations, seed real importado nem autenticação real. Preços e
> imagens do catálogo **continuam pendentes** para o sistema final.
>
> Este guia deriva do [DER](./04-modelagem-banco-der.md), do
> [dicionário de dados](./05-dicionario-de-dados.md) e dos
> [requisitos](./02-requisitos-do-sistema.md).
>
> **Próximo passo oficial:** criar os **modelos SQLAlchemy de domínio** com base
> no DER e no dicionário de dados, **sem popular o banco e sem importar o seed de
> produtos ainda** (Etapa 4.1).

## Objetivo

Definir **como** o MVP será construído tecnicamente, oferecendo um guia claro e
consistente para a etapa de implementação.

---

## 1. Visão técnica geral

O MVP será uma **aplicação web monolítica** em **Flask**, renderizada no servidor
(Server-Side Rendering com Jinja2), com banco **SQLite** e frontend em
**HTML/CSS/JavaScript**. A organização segue separação por camadas e por módulos
(blueprints), favorecendo manutenção, testes e evolução futura.

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
- **Separação de responsabilidades:** rotas finas, regras em serviços, acesso a
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
| Acesso a dados   | **Flask-SQLAlchemy (ORM)** — **adotado**     | Decisão final (§6); `sqlite3` puro fica como alternativa histórica |
| Migrations       | Flask-Migrate (Alembic) — **futuro**         | Não no MVP inicial                             |
| Autenticação     | Sessão Flask + hash de senha (Werkzeug)      | `werkzeug.security`                            |
| Formulários/CSRF | Flask-WTF — proposto                         | Proteção CSRF e validação                      |
| Frontend         | HTML, CSS, JavaScript                        | Sem framework JS obrigatório no MVP            |
| Mapa             | Biblioteca de mapa JS (ex.: Leaflet)         | Mapa real; começa simples                      |
| Testes           | pytest                                       | Ver §11                                        |

> **Flask**, **Flask-SQLAlchemy**, **python-dotenv** e **pytest** já estão
> declarados no [`requirements.txt`](../requirements.txt) — ou seja, as
> dependências do **projeto** estão definidas. Isso **não** significa que o
> ambiente local de quem clona o repositório já está instalado: é preciso rodar
> `pip install -r requirements.txt` (ver "Como executar" no README).
>
> **Flask-Migrate** e **Flask-WTF** permanecem **futuro/proposto** e **não**
> devem ser adicionados ao `requirements.txt` agora, pois ainda não são usados.
> Continuam fora desta etapa: migrations, seed real, banco populado, CRUD,
> autenticação real, validação AGROFIT/MAPA automatizada e a validação diária de
> preço (sistema final).

---

## 3. Estrutura profissional (Flask)

> ✅ **A estrutura base já foi criada** na fundação Flask (`src/run.py` +
> `src/app/` com Application Factory, blueprints placeholders, templates,
> estáticos e testes). **`src/app/models/` existe, mas ainda está vazio de
> modelos reais** — os arquivos de modelos são previstos para a **Etapa 4.1**.
> CRUD, migrations, seed real e banco populado permanecem para etapas futuras.

### Estrutura criada atualmente

```text
src/
├── run.py                       # ponto de entrada (chama create_app)
└── app/
    ├── __init__.py              # create_app / Application Factory
    ├── config.py                # classes de configuração por ambiente
    ├── extensions.py            # instâncias de extensões (db = SQLAlchemy)
    ├── blueprints/              # um pacote por módulo do MVP (placeholders)
    │   ├── __init__.py          # registro central dos blueprints
    │   ├── auth/  dashboard/  culturas/  glebas/  defensivos/
    │   ├── fertilizantes/  financeiro/  upload/  equipe/
    │   └── colheita/  mapa/  ia/  relatorios/
    ├── models/
    │   └── __init__.py          # nenhum modelo definido nesta etapa
    ├── services/
    │   └── __init__.py
    ├── utils/
    │   └── __init__.py
    ├── templates/               # base.html, dashboard/, placeholders/, errors/
    └── static/                  # css/, js/, uploads/ (conteúdo ignorado no git)
```

> O banco SQLite ficará em `instance/` (não versionado) quando o schema for
> criado. Cada blueprint tem hoje `__init__.py` + `routes.py`; `forms.py`/
> `services.py` poderão ser adicionados quando fizer sentido.

### Arquivos previstos para a Etapa 4.1

> ⚠️ **Os arquivos abaixo ainda NÃO devem ser criados agora.** São previstos
> para a próxima etapa (modelos SQLAlchemy) e **não fazem parte da fundação
> Flask já concluída**.

```text
src/app/models/
├── usuario.py
├── propriedade.py
├── cultura.py
├── gleba.py
├── produto.py           # produto_base, produto_tecnico, produto_preco, produto_imagem
├── financeiro.py
├── equipe.py
├── colheita.py
├── upload.py
└── ia.py
```

---

## 4. Padrão de aplicação: Application Factory + Blueprints

- `create_app(config_name)` em `app/__init__.py` instancia o Flask, carrega a
  configuração, inicializa as extensões (`db`, CSRF, etc.) e registra os
  blueprints. `run.py` apenas chama essa fábrica.
- Cada **blueprint** corresponde a um módulo do MVP, com URL prefix próprio.
- Vantagens: testabilidade (app de teste com config isolada), isolamento de
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

---

## 6. Acesso a dados e banco SQLite

- **Banco:** arquivo SQLite em `src/instance/connectagro.db` (a pasta `instance/`
  e arquivos `*.db` já estão no [.gitignore](../.gitignore); o banco **não** é
  versionado).
- **Decisão final:** ✅ adotado **Flask-SQLAlchemy** como ORM do MVP, mapeando os
  modelos às tabelas do [dicionário de dados](./05-dicionario-de-dados.md). A
  instância `db` está centralizada em `src/app/extensions.py` e é inicializada na
  Application Factory.
  - *Justificativa:* ~15 tabelas com vários relacionamentos; um ORM reduz SQL
    repetitivo, melhora manutenção e facilita testes.
  - *Alternativa histórica/documentada:* `sqlite3` puro com uma fina camada de
    repositório — **não** adotado.
- **Tipos:** seguir o dicionário — `TEXT` para datas (ISO 8601), `BOOLEAN` como
  `0/1`, listas como `TEXT`/JSON no MVP (normalização futura).
- **Migrations:** Flask-Migrate/Alembic ficam para **etapa futura**. **Nenhuma
  migration é criada nesta etapa**, e o **banco real não é versionado**.
- **Seeds:** o seed definitivo **ainda não existe** (ver
  [data/seeds/README.md](../data/seeds/README.md)); preço e imagem permanecem
  pendentes.

---

## 7. Fluxo principal do MVP

Fluxo geral esperado do uso do sistema:

1. Usuário acessa o sistema.
2. Faz **login**.
3. Entra no **dashboard**.
4. Cadastra ou consulta **propriedade / glebas / culturas**.
5. Consulta o **catálogo** de defensivos/fertilizantes.
6. Registra **aplicações ou uso de insumos** (`aplicacao_insumo`).
7. Registra **despesas/receitas** no financeiro.
8. Registra **colheita**.
9. Consulta **mapa** e **relatórios**.
10. Usa a **IA simulada** apenas como apoio informativo no MVP.

> **IA simulada:** **não** emite recomendação agronômica definitiva. Funciona
> apenas como **apoio textual/informativo e organizacional**.

---

## 8. Fluxo do catálogo de produtos

- O catálogo **não vende** produtos — serve para **consulta rápida**, organização
  da propriedade, registro de aplicação de insumos e apoio ao planejamento.
- Estrutura de dados (ver [DER](./04-modelagem-banco-der.md)):
  - Produtos ficam em **`produto_base`**.
  - Dados técnicos ficam em **`produto_tecnico`**.
  - Preços ficam em **`produto_preco`**.
  - Imagens ficam em **`produto_imagem`**.
- No MVP, **preço e imagem são pendentes / não consolidados**
  (`status_validacao`).
- A **validação diária do menor preço atualizado** fica **somente para o sistema
  final**.
- O MVP **não** deve buscar preços automaticamente.
- O MVP **não** deve afirmar que um defensivo foi validado oficialmente no
  AGROFIT/MAPA sem comprovação real.
- **`status_regulatorio` é informativo** (enum MVP: `nao_validado_agrofit`,
  `atencao_regulatoria`, `sujeito_a_sipeagro_nao_validado`,
  `tipo_tecnico_generico`, `bloqueado_historico`).
- Itens **bloqueados/históricos**, como **Paraquate**
  (`status_sistema = bloqueado_historico`), **não** devem ser recomendados nem
  permitidos em registro de aplicação (`aplicacao_insumo`).

---

## 9. Detalhamento dos módulos do MVP

> Apenas documentação — os módulos **não** são implementados nesta etapa.

### Login
- **Objetivo:** autenticar o usuário e proteger o acesso aos demais módulos.
- **Dados principais:** `usuario` (`email`, `senha_hash`, `perfil`, `ativo`).
- **Blueprint:** `auth` (`/auth`).
- **Implementação futura:** hash com Werkzeug, sessão Flask, decorator de "login
  obrigatório", controle por `perfil`.

### Dashboard
- **Objetivo:** visão consolidada da propriedade após o login.
- **Dados principais:** agregações de culturas, glebas, financeiro e colheita.
- **Blueprint:** `dashboard` (`/`).
- **Implementação futura:** consultas de leitura/resumo; sem escrita.

### Culturas
- **Objetivo:** cadastrar e acompanhar culturas.
- **Dados principais:** `cultura`, `cultura_gleba`.
- **Blueprint:** `culturas` (`/culturas`).
- **Implementação futura:** CRUD, `status` (`planejada`/`em_andamento`/`colhida`/
  `cancelada`), associação a glebas.

### Glebas
- **Objetivo:** cadastrar e gerir áreas/talhões.
- **Dados principais:** `gleba`, `cultura_gleba`.
- **Blueprint:** `glebas` (`/glebas`).
- **Implementação futura:** CRUD; `latitude`/`longitude`/`poligono_geojson` para o
  mapa; mapa começa simples.

### Defensivos
- **Objetivo:** consultar defensivos do catálogo.
- **Dados principais:** `produto_base` (classe `defensivo`), `produto_tecnico`,
  `produto_preco`, `produto_imagem`.
- **Blueprint:** `defensivos` (`/defensivos`).
- **Implementação futura:** consulta/busca; preço e imagem como pendência;
  `status_regulatorio` informativo; itens bloqueados não recomendados.

### Fertilizantes
- **Objetivo:** consultar fertilizantes do catálogo.
- **Dados principais:** `produto_base` (classe `fertilizante`) e tabelas
  `produto_*`.
- **Blueprint:** `fertilizantes` (`/fertilizantes`).
- **Implementação futura:** mesma consulta do catálogo, filtrando por `classe`;
  genéricos (Ureia, MAP, DAP, Calcário) como tipo técnico.

### Financeiro
- **Objetivo:** registrar receitas e despesas.
- **Dados principais:** `financeiro_lancamento` (`tipo` = `receita`/`despesa`).
- **Blueprint:** `financeiro` (`/financeiro`).
- **Implementação futura:** CRUD, filtros por período/categoria, totais.

### Upload
- **Objetivo:** enviar e armazenar documentos/arquivos.
- **Dados principais:** `upload_arquivo` (metadados).
- **Blueprint:** `upload` (`/upload`).
- **Implementação futura:** `secure_filename`, validação de extensão/tamanho,
  armazenamento em `static/uploads/` (conteúdo ignorado no git).

### Equipe
- **Objetivo:** gerir membros e funções.
- **Dados principais:** `equipe_membro`.
- **Blueprint:** `equipe` (`/equipe`).
- **Implementação futura:** CRUD; `funcao` poderá condicionar permissões.

### Colheita
- **Objetivo:** registrar e acompanhar a colheita.
- **Dados principais:** `colheita_registro`, `cultura_gleba`.
- **Blueprint:** `colheita` (`/colheita`).
- **Implementação futura:** registro de quantidade/unidade/qualidade por
  cultura/gleba.

### Mapa real
- **Objetivo:** visualizar as glebas em mapa.
- **Dados principais:** `gleba` (`latitude`, `longitude`, `poligono_geojson`).
- **Blueprint:** `mapa` (`/mapa`).
- **Implementação futura:** biblioteca de mapa (ex.: Leaflet); começa simples
  (ponto/lista), evolui para polígonos.

### IA simulada
- **Objetivo:** apoio informativo por IA (simulada no MVP).
- **Dados principais:** `ia_interacao` (`pergunta`, `resposta`, `tipo`).
- **Blueprint:** `ia` (`/ia`).
- **Implementação futura:** serviço com respostas simuladas (regras/templates);
  **sem** recomendação agronômica definitiva; sem chamada a modelos externos.

### Relatórios
- **Objetivo:** gerar relatórios operacionais e financeiros.
- **Dados principais:** leitura agregada de culturas, glebas, financeiro,
  colheita.
- **Blueprint:** `relatorios` (`/relatorios`).
- **Implementação futura:** relatórios em HTML; exportação (CSV/PDF) incremental.

---

## 10. Configuração, autenticação e segurança

- **Configuração:** `app/config.py` com classes por ambiente
  (`Development`/`Testing`/`Production`). Variáveis sensíveis em `.env`
  (não versionado; haverá `.env.example`): `SECRET_KEY`, caminho do SQLite,
  `FLASK_ENV`/`FLASK_DEBUG`, `UPLOAD_FOLDER` e limites.
- **Autenticação:** login por e-mail e senha; hash com `werkzeug.security`;
  sessão assinada por `SECRET_KEY`; acesso por `usuario.perfil` (`admin`,
  `produtor`, `membro`) e futuramente `equipe_membro.funcao`.
- **Segurança:** CSRF em formulários (Flask-WTF proposto); *escaping* do Jinja2
  contra XSS; uploads validados; nenhum segredo no repositório.
- **Erros e logging:** páginas 404/500 amigáveis; logging por ambiente; logs não
  versionados.

---

## 11. Testes

- **pytest** é a ferramenta oficial; app criado via `create_app('testing')` com
  banco isolado (SQLite em memória), conforme `tests/conftest.py`.
- **Testes mínimos da fundação Flask já existem** em `tests/`
  (`test_app_factory.py`, `test_placeholder_routes.py`): validam a criação da
  aplicação, a rota `/health`, a rota inicial e as rotas placeholders dos módulos.
- Organização em `tests/` (na raiz) espelhando `src/app/` — ver
  [tests/README.md](../tests/README.md).
- **Para etapas futuras:** testes de regras de negócio, banco, autenticação,
  CRUD e seed.
- Convenção: arquivos `test_*.py`.

---

## 12. Regras para futura implementação

- **Não** criar funcionalidades fora do escopo do MVP sem atualizar a documentação.
- **Não** inventar dados de produtos.
- **Não** afirmar validação AGROFIT/MAPA sem fonte real.
- **Não** transformar o sistema em loja ou marketplace.
- **Não** vender produtos.
- **Não** exibir preço como cotação oficial.
- No MVP, **preço e imagem** devem aparecer como **pendentes / não consolidados**.
- A **validação diária do menor preço** pertence ao **sistema final**.
- Usar nomes de **tabelas e campos compatíveis** com o DER e o dicionário de dados.
- Priorizar código **simples, modular e testável**.
- Usar **Application Factory** e **Blueprints**.
- **Nunca** versionar `.env`, banco SQLite real, uploads de usuário ou arquivos
  sensíveis.
- Criar **testes** para fluxos críticos quando a implementação começar.

---

## 13. Checklist de prontidão para iniciar a Etapa 4.1 — Modelos SQLAlchemy

> Marcar apenas o que estiver **realmente** concluído.

- [x] Escopo consolidado
- [x] Requisitos revisados
- [x] Regras de negócio revisadas
- [x] DER revisado
- [x] Dicionário de dados revisado
- [x] Catálogo de produtos corrigido com IDs, slugs e classe
- [x] Estratégia de seed definida (`produto_base` + `produto_tecnico`; preço/imagem vazios no MVP)
- [x] Decisão final sobre ORM: **Flask-SQLAlchemy**
- [x] Fundação Flask criada (`src/run.py` + `src/app/`)
- [x] Blueprints placeholders criados
- [x] Testes mínimos criados
- [ ] Modelos SQLAlchemy de domínio criados
- [ ] Banco SQLite inicial criado
- [ ] Migrations configuradas
- [ ] Seed técnico importado

---

## Documentos relacionados

- [00 — Visão Geral](./00-visao-geral.md)
- [02 — Requisitos do Sistema](./02-requisitos-do-sistema.md)
- [04 — Modelagem do Banco (DER)](./04-modelagem-banco-der.md)
- [05 — Dicionário de Dados](./05-dicionario-de-dados.md)
- [06 — Arquitetura do Sistema (visão conceitual)](./06-arquitetura-do-sistema.md)
- [07 — Roadmap do MVP](./07-roadmap-mvp.md)
- [Catálogo de Produtos](./catalogo-produtos/README.md)
