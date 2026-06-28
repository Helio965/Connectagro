# 06.1 — Arquitetura Técnica do MVP

## Status do documento

**Arquitetura técnica — v0.17 (CRUDs + catálogo + upload + dashboard + mapa + IA simulada + relatórios operacionais + permissões finas).**

> **Permissões finas por perfil (Fase 6.3):** `src/app/utils/permissions.py`
> concentra `PERMISSOES_POR_PERFIL`, `require_permission(...)`, `can(...)` e a
> matriz dos perfis `admin`, `tecnico` e `trabalhador`. A autorização é aplicada
> no backend com retorno **403** e refletida nos templates apenas como apoio
> visual. Não houve migration, alteração de model, tabela de permissões ou
> dependência nova.
>
> **Relatórios Operacionais (Fase 6.2):** `services/relatorios_service.py` reúne
> agregações **somente leitura** (geral, financeiro, agrícola, aplicações,
> uploads), reutilizando helpers de consulta do `dashboard_service` e escopando
> tudo pela propriedade atual. Renderização em HTML (Jinja2); **sem PDF/exportação**
> nesta fase — a impressão é feita pelo navegador (`window.print()`). Os
> relatórios não criam/alteram/removem dados.

Este documento **complementa** o [06 — Arquitetura do Sistema](./06-arquitetura-do-sistema.md):

- O documento **06** é a **visão conceitual/geral** (camadas em alto nível).
- O documento **06.1** (este) é o **guia técnico detalhado** da implementação do
  MVP em Flask.

> **Estado atual:** estão prontos a fundação Flask, modelos SQLAlchemy (15
> tabelas), migrations, importação do catálogo técnico via CLI, autenticação real,
> permissões finas por perfil, **Dashboard Operacional** somente leitura, **Mapa
> real simplificado** somente leitura, **IA Simulada Operacional** baseada em
> regras locais, **Relatórios Operacionais HTML**, CRUDs de Glebas, Culturas,
> Equipe, Financeiro, Colheita, Aplicações de Insumo e **Upload de Arquivos**,
> além da consulta somente leitura de Defensivos e Fertilizantes.
> `ProdutoPreco`/`ProdutoImagem` seguem vazios no MVP.
>
> **Dashboard Operacional:** agrega dados já existentes da propriedade atual,
> usando consultas aos módulos operacionais. Ele não cria registros, não altera
> models e não exige migration.
>
> **Mapa real simplificado:** usa os campos já existentes em `gleba` (`latitude`,
> `longitude`, `poligono_geojson`) para renderizar uma visualização operacional em
> `/mapa/` e expor dados em `/mapa/dados`. Ele não cria registros, não altera
> models e não exige migration.
>
> **IA Simulada Operacional:** usa `services/ia_simulada_service.py` para gerar
> respostas por regras simples e consultas locais. Registra perguntas e respostas
> em `ia_interacao`, escopadas por usuário e propriedade. Não usa LLM, API
> externa, internet, machine learning ou OCR.
>
> **Upload de Arquivos:** usa `UPLOAD_FOLDER`, salva arquivos localmente fora da
> pasta pública `static` (`instance/uploads` por padrão), em subpastas por
> propriedade, aplica `secure_filename`, gera nome único com UUID e grava em
> `upload_arquivo` apenas metadados e caminho relativo. Arquivos reais enviados
> por usuários ficam fora do Git e não devem ser servidos diretamente por
> `/static/uploads`.
>
> **Pendente:** CSRF/Flask-WTF e revisão final do MVP.

## Objetivo

Definir **como** o MVP é construído tecnicamente, oferecendo um guia claro e
consistente para a implementação incremental.

---

## 1. Visão técnica geral

O MVP é uma **aplicação web monolítica** em **Flask**, renderizada no servidor
(Server-Side Rendering com Jinja2), com banco **SQLite** e frontend em
**HTML/CSS/JavaScript**. A organização segue separação por camadas e por módulos
(blueprints), favorecendo manutenção, testes e evolução futura.

```text
Navegador (HTML/CSS/JS)
        │  HTTP
        ▼
Flask (rotas/blueprints)  ──►  Serviços/helpers  ──►  Modelos/Acesso a dados
        │                                                       │
        ▼                                                       ▼
   Templates Jinja2                                         SQLite (instance/)
```

### Princípios técnicos

- **Application Factory** (`create_app`) para criar a aplicação de forma
  configurável e testável.
- **Blueprints** para isolar cada módulo do MVP.
- **Separação de responsabilidades:** rotas simples, helpers locais para CRUDs e
  serviços quando houver regra compartilhada.
- **Dashboard como agregação somente leitura:** consulta dados existentes e não
  modifica estado.
- **Mapa como visualização somente leitura:** usa coordenadas já cadastradas em
  Glebas, não cria dados e não altera schema.
- **IA simulada por regras:** usa dados locais e não executa integração externa.
- **Relatórios como consultas HTML somente leitura:** sem exportação/PDF nesta fase.
- **Autorização por perfil em código:** protege rotas no backend e ajuda a
  renderizar menus/botões conforme perfil.
- **Configuração por ambiente** via variáveis de ambiente (`.env`), sem segredos
  versionados.
- Alinhamento total com os nomes de tabelas/campos do
  [dicionário de dados](./05-dicionario-de-dados.md).

---

## 2. Stack planejada

| Camada           | Tecnologia planejada                         | Observações                                    |
|------------------|----------------------------------------------|------------------------------------------------|
| Linguagem        | Python 3.11+                                 | Testado localmente também em Python 3.12       |
| Framework web    | Flask                                        | Monólito com blueprints                        |
| Templates        | Jinja2                                       | SSR                                            |
| Banco de dados   | SQLite                                       | Arquivo local em `instance/`                   |
| Acesso a dados   | Flask-SQLAlchemy                             | ORM adotado                                    |
| Migrations       | Flask-Migrate (Alembic)                      | Pasta `migrations/` versionada                 |
| Upload local     | Werkzeug `secure_filename` + Flask `send_from_directory` | Arquivos fora de `static` e do Git |
| Mapa frontend    | Leaflet.js via CDN                           | Sem dependência Python/NPM nova                |
| IA simulada      | Regras locais em Python                      | Sem LLM/API externa/internet                   |
| Relatórios       | Serviços Python + Jinja2                     | HTML somente leitura; sem PDF/exportação       |
| Autenticação     | Sessão Flask + hash de senha (Werkzeug)      | Helpers em `utils/auth.py`                     |
| Autorização      | Matriz em código                             | `utils/permissions.py`; sem tabela nova        |
| Formulários/CSRF | Sem Flask-WTF nesta etapa                    | CSRF dedicado permanece pendente               |
| Frontend         | HTML, CSS, JavaScript                        | Sem framework JS obrigatório no MVP            |
| Testes           | pytest                                       | SQLite em memória e pasta temporária para upload |

---

## 3. Estrutura Flask

```text
src/
├── run.py
└── app/
    ├── __init__.py              # create_app / Application Factory
    ├── config.py                # inclui UPLOAD_FOLDER e MAX_CONTENT_LENGTH
    ├── extensions.py            # db, migrate
    ├── commands.py              # init-db, validate/import-catalog-seed, seed-users
    ├── blueprints/
    │   ├── __init__.py          # registro central dos blueprints
    │   ├── auth/  dashboard/  culturas/  glebas/
    │   ├── defensivos/  fertilizantes/  aplicacoes/
    │   ├── financeiro/  upload/  equipe/  colheita/
    │   └── mapa/  ia/  relatorios/
    ├── models/                  # modelos SQLAlchemy de domínio (15 tabelas)
    ├── services/                # catalogo_seed.py, dashboard_service.py, ia_simulada_service.py, relatorios_service.py
    ├── utils/                   # auth.py, contexto.py, catalogo.py, formatters.py, permissions.py
    ├── templates/               # base.html, módulos, erros
    └── static/                  # css/, js/ (arquivos públicos)

instance/
├── connectagro.db               # banco local quando usado em desenvolvimento
└── uploads/                     # arquivos enviados no MVP, fora de static
```

> O banco SQLite e os uploads locais padrão ficam em `instance/`, pasta ignorada
> pelo Git. Uploads de usuário não devem ficar em `src/app/static`, porque esse
> diretório é público no Flask e pode ser exposto por `/static/...`.

---

## 4. Application Factory + Blueprints

- `create_app(config_name)` em `app/__init__.py` instancia o Flask, carrega a
  configuração, inicializa `db`/`migrate`, registra modelos, blueprints,
  comandos CLI, context processors e handlers de erro.
- O context processor injeta `current_user`, `is_authenticated` e `can` nos
  templates Jinja.
- `src/app/blueprints/__init__.py` centraliza `ALL_BLUEPRINTS`.
- Cada módulo do MVP tem `__init__.py` com `Blueprint` e `routes.py` com as rotas.
- O handler 403 renderiza `templates/errors/403.html` com mensagem amigável, sem
  expor nomes internos de permissões.

---

## 5. Mapeamento de módulos → blueprints

| Módulo (MVP)       | Blueprint        | Prefixo        | Entidades principais                              |
|--------------------|------------------|----------------|---------------------------------------------------|
| Login              | `auth`           | `/auth`        | `usuario`                                         |
| Dashboard          | `dashboard`      | `/`            | agregações somente leitura                        |
| Culturas           | `culturas`       | `/culturas`    | `cultura`, `cultura_gleba`                        |
| Glebas             | `glebas`         | `/glebas`      | `gleba`, `cultura_gleba`                          |
| Defensivos         | `defensivos`     | `/defensivos`  | `produto_base`, `produto_tecnico`                 |
| Fertilizantes      | `fertilizantes`  | `/fertilizantes` | `produto_base`, `produto_tecnico`               |
| Aplicações         | `aplicacoes`     | `/aplicacoes`  | `aplicacao_insumo`, `cultura_gleba`, `produto_base` |
| Financeiro         | `financeiro`     | `/financeiro`  | `financeiro_lancamento`                           |
| Upload             | `upload`         | `/upload`      | `upload_arquivo`                                  |
| Equipe             | `equipe`         | `/equipe`      | `equipe_membro`                                   |
| Colheita           | `colheita`       | `/colheita`    | `colheita_registro`, `cultura_gleba`              |
| Mapa real          | `mapa`           | `/mapa`        | `gleba`                                           |
| IA simulada        | `ia`             | `/ia`          | `ia_interacao`                                    |
| Relatórios         | `relatorios`     | `/relatorios`  | leitura de múltiplas entidades                    |

---

## 6. Acesso a dados, banco SQLite e arquivos

- **Banco:** arquivo SQLite em `instance/` ou caminho configurado por ambiente.
- **ORM:** `Flask-SQLAlchemy`, com instância `db` em `src/app/extensions.py`.
- **Migrations:** `Flask-Migrate/Alembic`, com migration inicial das 15 tabelas.
- **Seeds:** `flask --app src/run.py import-catalog-seed` popula apenas
  `produto_base` + `produto_tecnico`. `produto_preco`/`produto_imagem` continuam
  vazios no MVP.
- **Dashboard:** não exige migration nova porque apenas consulta tabelas já
  existentes.
- **Aplicações de Insumo:** não exigem migration nova porque a tabela
  `aplicacao_insumo` já existe no schema inicial.
- **Upload:** não exige migration nova porque a tabela `upload_arquivo` já existe
  no schema inicial.
- **Mapa real simplificado:** não exige migration nova porque usa campos já
  existentes em `gleba`.
- **IA simulada:** não exige migration nova porque usa a tabela `ia_interacao` já
  existente.
- **Relatórios:** não exigem migration nova porque apenas consultam dados já
  existentes.
- **Permissões finas:** não exigem migration nova porque usam `usuario.perfil` e
  matriz em código.

### Dashboard operacional

- `src/app/blueprints/dashboard/routes.py` resolve a propriedade atual e renderiza
  `dashboard/index.html`.
- `src/app/services/dashboard_service.py` concentra as consultas e agregações.
- Todas as métricas operacionais são filtradas por `propriedade_id` ou, no caso
  de Colheita e Aplicações, via join com `CulturaGleba`, `Cultura` e `Gleba` da
  propriedade atual.
- O catálogo é global e aparece apenas como contagem técnica de consulta.
- O Dashboard é somente leitura: não cria, edita ou remove registros.
- Não usa biblioteca externa de gráfico e não altera schema.

### Mapa real simplificado

- `src/app/blueprints/mapa/routes.py` resolve a propriedade atual e renderiza
  `templates/mapa/index.html` em `/mapa/`.
- `/mapa/dados` retorna JSON somente leitura com `propriedade`, `glebas` e
  `sem_coordenadas`.
- A consulta usa somente `Gleba.query.filter_by(propriedade_id=propriedade.id)`,
  evitando vazamento de dados entre propriedades.
- Coordenadas válidas exigem latitude e longitude preenchidas, latitude entre
  `-90` e `90` e longitude entre `-180` e `180`. Valores ausentes ou fora da faixa
  são tratados como sem coordenadas válidas sem alterar o banco.
- `poligono_geojson`, quando preenchido com JSON/GeoJSON simples válido, é
  enviado ao frontend. Conteúdo inválido é ignorado com segurança e retorna nulo.
- `src/app/static/js/mapa.js` usa Leaflet.js via CDN, centro padrão no Brasil
  `[-15.7801, -47.9292]`, marcadores, popup e ajuste de bounds.
- A página renderiza sem internet nos testes; sem a biblioteca Leaflet carregada,
  o script mostra mensagem de indisponibilidade do mapa visual.
- O módulo não cria, edita ou remove glebas, não mede área, não desenha polígonos,
  não importa/exporta GeoJSON, não usa GPS em tempo real, não usa PostGIS e não
  adiciona dependência Python/NPM.

### IA simulada operacional

- `src/app/blueprints/ia/routes.py` expõe `/ia/` com `GET` e `POST`, protegido por
  `@login_required` e permissão de visualização da IA.
- `GET /ia/` renderiza `templates/ia/index.html` com formulário, atalhos rápidos,
  resumo automático, alertas e últimas 10 interações.
- `POST /ia/` valida pergunta obrigatória, mínimo de 2 caracteres e máximo de
  1000 caracteres; entradas inválidas retornam HTTP 400 com flash.
- `src/app/services/ia_simulada_service.py` contém funções testáveis:
  `montar_contexto_operacional`, `gerar_resumo_operacional`,
  `gerar_alertas_operacionais`, `classificar_intencao_simples`,
  `responder_pergunta_simulada`, `registrar_interacao_ia` e
  `listar_interacoes_ia`.
- A IA classifica intenções por palavras-chave: resumo, financeiro, glebas,
  culturas, colheita, aplicações, documentos, catálogo e fallback de ajuda.
- Todas as consultas operacionais usam a propriedade atual. Colheita e Aplicações
  são filtradas por joins com `CulturaGleba`, `Cultura` e `Gleba` da propriedade.
- O histórico é persistido em `ia_interacao` com `usuario_id`, `propriedade_id`,
  `pergunta`, `resposta` e `tipo="simulada"`.
- A listagem do histórico filtra simultaneamente por `usuario_id` e
  `propriedade_id`, ordenando por `criado_em desc` e `id desc`.
- A IA não usa LLM, OpenAI, Claude, Gemini, API externa, internet, machine
  learning, OCR ou leitura automática de uploads.
- A IA não recomenda produtos, não valida dose, não faz diagnóstico agronômico,
  não afirma validação oficial AGROFIT/MAPA ou SIPEAGRO/MAPA e não vende produtos.

### Upload local

- `UPLOAD_FOLDER` define a pasta base de armazenamento local. O padrão é
  `instance/uploads`, fora de `src/app/static`.
- `MAX_CONTENT_LENGTH` define o limite máximo aceito pela aplicação.
- Cada propriedade usa subpasta própria: `UPLOAD_FOLDER/propriedade_<id>/`.
- O arquivo salvo usa `secure_filename` e UUID, por exemplo
  `uuid4hex_nome-seguro.pdf`.
- O campo `upload_arquivo.caminho` guarda caminho relativo seguro, por exemplo
  `propriedade_1/uuid_nome.pdf`, nunca caminho absoluto.
- Download usa busca por id + validação de `propriedade_id` + resolução dentro de
  `UPLOAD_FOLDER`, sem aceitar caminho vindo diretamente da URL.
- Os arquivos não devem ficar acessíveis por `/static/uploads`; o acesso correto é
  sempre a rota protegida `/upload/<id>/download`.
- Remoção apaga o registro e tenta apagar o arquivo físico; se o arquivo físico
  já não existir, o registro ainda é removido com aviso simples.
- Extensões permitidas: `pdf`, `png`, `jpg`, `jpeg`, `csv`, `xlsx`, `txt`, `docx`.
- Executáveis, scripts, compactados e extensões fora da allowlist são bloqueados.
- Upload não faz OCR, IA, extração automática, classificação ou validação avançada
  de conteúdo no MVP.

### Relatórios operacionais

- `src/app/blueprints/relatorios/routes.py` expõe a central `/relatorios/` e os
  relatórios `geral`, `financeiro`, `agricola`, `aplicacoes` e `uploads`.
- `src/app/services/relatorios_service.py` concentra as consultas e reutiliza
  helpers já existentes quando faz sentido.
- Todos os relatórios resolvem a propriedade atual; nenhuma rota aceita
  `propriedade_id` por parâmetro.
- O relatório financeiro aceita filtros de período e tipo (`receita`/`despesa`) e
  retorna 400 para filtros inválidos.
- O relatório de aplicações aceita filtros de período e classe, mas não recomenda
  produtos e não valida dose.
- O relatório de uploads lista metadados e download protegido; não lê conteúdo do
  arquivo e não faz OCR/IA/extração.
- Relatórios são HTML somente leitura: não criam, alteram ou removem dados.
- Não há PDF, CSV, Excel, API externa ou exportação automática nesta fase.

### Autorização por perfil

- `src/app/utils/permissions.py` define `PERFIS_OFICIAIS`,
  `PERMISSOES_POR_PERFIL`, `perfil_atual()`, `has_permission(permission)`,
  `can(permission)` e `require_permission(permission)`.
- A matriz usa permissões explícitas como `glebas.create`, `financeiro.view`,
  `upload.delete`, `relatorios.view`, `mapa.view` e `ia.view`.
- `require_permission(...)` é aplicado nas rotas sensíveis junto de
  `@login_required`. Usuário sem sessão continua sendo redirecionado para login;
  usuário autenticado sem permissão recebe **403**.
- `can(...)` é injetado nos templates pelo `create_app` e usado para esconder
  menus, atalhos e botões não permitidos.
- A camada visual não substitui a validação do backend.
- Permissões não alteram o escopo por propriedade: quando o perfil pode executar
  uma ação, registros de outra propriedade continuam retornando **404**.

Matriz resumida:

| Perfil | Resumo |
|--------|--------|
| `admin` | Acessa todos os módulos; cria, edita e remove registros nos CRUDs da sua propriedade; envia, baixa e remove uploads. |
| `tecnico` | Acessa dashboard, mapa, catálogo, relatórios, IA, equipe e financeiro em leitura; cria/edita glebas, culturas, colheitas e aplicações; envia e baixa uploads; não remove registros críticos nem gerencia equipe/financeiro. |
| `trabalhador` | Acessa dashboard, mapa, catálogo, relatórios e IA; visualiza glebas, culturas, colheitas e aplicações; cria colheitas, aplicações e uploads; baixa uploads; não acessa equipe/financeiro e não edita/remove registros críticos. |

---

## 7. Fluxo principal do MVP

1. Usuário acessa o sistema.
2. Faz **login**.
3. Entra no **dashboard operacional**.
4. Cadastra ou consulta **propriedade / glebas / culturas** conforme permissão.
5. Consulta o **catálogo** de defensivos/fertilizantes.
6. Registra **aplicações de insumos** em associações cultura↔gleba quando o perfil permite.
7. Registra **despesas/receitas** no financeiro quando o perfil permite.
8. Envia documentos da propriedade no **Upload** quando o perfil permite.
9. Registra **colheita** quando o perfil permite.
10. Consulta o **mapa** das glebas com coordenadas cadastradas.
11. Usa a **IA simulada** para apoio operacional baseado em dados locais.
12. Consulta **relatórios operacionais HTML** somente leitura.

---

## 8. Fluxo do catálogo de produtos

- O catálogo **não vende** produtos — serve para consulta rápida, organização da
  propriedade e registro histórico de aplicações.
- Produtos ficam em **`produto_base`**; dados técnicos em **`produto_tecnico`**;
  preços em **`produto_preco`**; imagens em **`produto_imagem`**.
- No MVP, **preço e imagem são pendentes / não consolidados**.
- O MVP **não** busca preços automaticamente e **não** afirma validação oficial
  AGROFIT/MAPA ou SIPEAGRO/MAPA sem fonte real.
- `status_regulatorio` é informativo.
- Itens **bloqueados/históricos**, como Paraquate, não devem ser recomendados e
  **não** podem ser registrados como aplicação válida.
- A importação do catálogo é feita via CLI; não há CRUD de produto nesta fase.

---

## 9. Detalhamento dos módulos do MVP

### Login ✅
- Autenticação real com sessão Flask e hash de senha.
- Rotas protegidas por `@login_required`.
- Rotas públicas preservadas: `/auth/login` e `/health`.

### Permissões ✅
- Matriz por perfil em `src/app/utils/permissions.py`.
- Perfis oficiais: `admin`, `tecnico`, `trabalhador`.
- `require_permission(...)` nas rotas sensíveis.
- `can(...)` nos templates para menus, atalhos e botões.
- Handler/template 403.
- Sem migration, sem model novo, sem dependência nova e sem tabela de permissões.
- Escopo por propriedade preservado.

### Dashboard ✅
- Painel operacional somente leitura em `/`.
- Escopo por propriedade atual em dados operacionais.
- Agrega Glebas, Culturas, Financeiro, Equipe, Colheita, Aplicações e Upload.
- Exibe totais globais do catálogo técnico sem transformar catálogo em venda.
- Usa `can()` em atalhos e blocos conforme perfil.
- Não cria dados, não altera schema e não usa gráficos externos.

### Culturas ✅
- CRUD com `status` (`planejada`, `em_andamento`, `colhida`, `cancelada`).
- Associação a glebas sincronizada no formulário.
- Ações de criar/editar/remover respeitam permissão por perfil.

### Glebas ✅
- CRUD de áreas/talhões.
- Campos `latitude`, `longitude` e `poligono_geojson` alimentam a visualização do mapa.
- Ações de criar/editar/remover respeitam permissão por perfil.

### Defensivos ✅
- Consulta somente leitura de `ProdutoBase` com classe `defensivo`.
- Busca, filtros e detalhe técnico.
- Sem CRUD de produto.

### Fertilizantes ✅
- Consulta somente leitura de `ProdutoBase` com classe `fertilizante`.
- Busca, filtros e detalhe técnico.
- Sem CRUD de produto.

### Aplicações de Insumo ✅
- CRUD de `AplicacaoInsumo` vinculado a `CulturaGleba` e `ProdutoBase`.
- Produto histórico/bloqueado é recusado.
- Dose é apenas valor histórico/informativo, sem validação agronômica.
- Não cria preço, imagem, venda, carrinho, cotação ou orçamento.
- Criar/editar/remover respeitam permissão por perfil.

### Financeiro ✅
- CRUD de receitas/despesas com validação de tipo, valor positivo e data.
- Listagem com totais de receitas, despesas e saldo.
- Técnico pode visualizar, mas não criar/editar/remover.
- Trabalhador não acessa o módulo.

### Upload ✅
- CRUD operacional de arquivos: listagem, envio, download e remoção.
- Escopo por propriedade em todas as operações.
- Arquivos locais organizados em subpasta por propriedade, fora de `static`.
- Download passa por rota protegida e valida a propriedade antes de servir o arquivo.
- Metadados em `upload_arquivo`; arquivo físico fora do Git.
- `secure_filename`, UUID e allowlist de extensões.
- Sem OCR, IA, APIs externas, antivírus real, armazenamento em nuvem ou extração automática.
- Remoção respeita permissão por perfil.

### Equipe ✅
- CRUD de membros e funções, escopado por propriedade.
- Técnico pode visualizar, mas não criar/editar/remover.
- Trabalhador não acessa o módulo.
- `funcao` poderá condicionar permissões finas futuramente.

### Colheita ✅
- CRUD vinculado a associação cultura↔gleba.
- Validação numérica simples de quantidade opcional.
- Criar/editar/remover respeitam permissão por perfil.

### Mapa real ✅
- Visualização somente leitura das glebas em `/mapa/`.
- Endpoint `/mapa/dados` com JSON filtrado pela propriedade atual.
- Usa `latitude`, `longitude` e `poligono_geojson` existentes em `Gleba`.
- Separa glebas sem coordenadas válidas e ignora GeoJSON inválido com segurança.
- Sem edição de coordenadas, desenho de polígonos, medição de área, GPS em tempo real, PostGIS ou camadas avançadas.

### IA simulada ✅
- Apoio operacional por regras simples em `/ia/`.
- Usa dados locais da propriedade atual: dashboard operacional, glebas, culturas,
  financeiro, colheita, aplicações, uploads e catálogo.
- Persiste histórico em `ia_interacao` com `tipo="simulada"`.
- Histórico visível apenas para o usuário e propriedade correspondentes.
- Sem LLM, API externa, internet, OCR, leitura de arquivos, recomendação
  agronômica, validação de dose ou diagnóstico técnico.

### Relatórios ✅
- Central em `/relatorios/`.
- Relatórios geral, financeiro, agrícola, aplicações e uploads.
- Filtros de período/tipo/classe onde aplicável.
- HTML somente leitura, escopado por propriedade.
- Sem PDF, CSV, Excel, exportação automática, alteração de dados, recomendação de
  produto, validação de dose ou leitura de conteúdo dos uploads.

---

## 10. Configuração, autenticação e segurança

- Configuração por ambiente em `app/config.py`.
- Sessão Flask assinada por `SECRET_KEY`, guardando dados mínimos do usuário.
- Senhas com `werkzeug.security`.
- Autenticação em `utils/auth.py` com `login_required`.
- Autorização em `utils/permissions.py` com `PERMISSOES_POR_PERFIL`,
  `require_permission(...)` e `can(...)`.
- Handler/template 403 para ações sem permissão.
- Sem Flask-WTF/CSRF dedicado nesta etapa.
- Templates Jinja com escaping padrão.
- Dashboard filtra dados operacionais pela propriedade atual; Colheita e
  Aplicações usam join com `CulturaGleba`, `Cultura` e `Gleba`.
- Mapa filtra glebas por `propriedade_id` da propriedade atual e não retorna
  e-mail, perfil ou dados sensíveis de usuário em `/mapa/dados`.
- IA filtra histórico por `usuario_id` e `propriedade_id`; respostas não incluem
  senha, e-mail ou dados de usuário fora do contexto operacional.
- Relatórios usam a propriedade atual e não aceitam `propriedade_id` por parâmetro.
- Uploads ficam fora da pasta pública `static` por padrão; arquivos devem ser
  acessados apenas pelas rotas protegidas do módulo Upload.
- Banco real, `.env`, uploads de usuário e arquivos sensíveis não são versionados.

---

## 11. Testes

- `pytest` é a ferramenta oficial.
- O app de teste é criado por `create_app("testing")` com SQLite em memória.
- Testes existentes cobrem: app factory, rotas protegidas, schema/modelos, seed,
  autenticação, CRUDs de Glebas/Culturas, Equipe/Financeiro, Colheita, consulta
  do catálogo, Aplicações de Insumo, Upload, Dashboard, Mapa real, IA simulada,
  Relatórios e Permissões.
- `tests/test_dashboard_operacional.py` cobre login, resposta 200, nome da
  propriedade, totais por propriedade, culturas por status, financeiro, equipe,
  colheita por unidade, aplicações, uploads, totais globais do catálogo, estados
  vazios, atalhos principais e ausência de termos de venda.
- `tests/test_mapa_real.py` cobre login, endpoint JSON, escopo por propriedade,
  coordenadas válidas/inválidas, GeoJSON inválido, ausência de POST, estados
  vazios e ausência de recursos avançados como funcionalidade ativa.
- `tests/test_ia_simulada.py` cobre login, avisos obrigatórios, POST válido,
  validações de pergunta, persistência em `ia_interacao`, escopo de histórico,
  respostas por intenção e ausência de termos proibidos.
- `tests/test_ia_simulada_service.py` cobre classificação de intenção, montagem
  de contexto, alertas, geração de resposta e registro/listagem do histórico.
- `tests/test_relatorios_operacionais.py` cobre login, relatórios HTML, filtros,
  escopo por propriedade, ausência de criação de dados e limites do MVP.
- `tests/test_relatorios_service.py` cobre validações e agregações dos serviços de relatórios.
- `tests/test_permissions.py` cobre matriz de permissões, bloqueio backend 403,
  rotas públicas preservadas, menus/botões escondidos por `can()`, escopo por
  propriedade e garantia de que ação sem permissão não cria registro.
- `tests/test_upload_crud.py` usa pasta temporária para uploads e cobre login,
  envio válido, arquivo físico, nome seguro, extensão proibida/permitida, caminho
  malicioso, listagem, download, remoção, escopo por propriedade, garantia de
  pasta padrão fora de `static` e garantia de que `ProdutoPreco`/`ProdutoImagem`
  não são criados.

---

## 12. Regras para implementação

- **Não** criar funcionalidades fora do escopo do MVP sem atualizar a documentação.
- **Não** inventar dados de produtos.
- **Não** afirmar validação AGROFIT/MAPA ou SIPEAGRO/MAPA sem fonte real.
- **Não** transformar o sistema em loja ou marketplace.
- **Não** vender produtos.
- **Não** exibir preço como cotação oficial.
- **Não** criar CRUD de produto no MVP atual.
- **Não** recomendar produto nem validar dose tecnicamente no módulo de aplicações.
- **Não** fazer OCR, IA, extração automática ou validação avançada no Upload do MVP.
- Dashboard deve permanecer somente leitura e sem criação de dados.
- Mapa deve permanecer como visualização somente leitura no MVP, sem edição de
  coordenadas, medição, desenho de polígonos, PostGIS ou GPS em tempo real.
- IA deve permanecer simulada por regras no MVP, sem LLM, API externa, internet,
  OCR, leitura de uploads, recomendação agronômica, validação de dose ou
  diagnóstico técnico.
- Relatórios devem permanecer HTML somente leitura no MVP, sem PDF/exportação e
  sem alteração de dados.
- Permissões devem bloquear no backend com 403; `can()` em template é apenas
  apoio visual.
- Permissões por perfil não substituem escopo por propriedade.
- No MVP, **preço e imagem** devem aparecer como pendentes / não consolidados.
- A **validação diária do menor preço** pertence ao sistema final.
- Usar nomes de tabelas e campos compatíveis com o DER e o dicionário de dados.
- Priorizar código simples, modular e testável.
- Usar Application Factory e Blueprints.
- Nunca versionar `.env`, banco SQLite real, uploads de usuário ou arquivos sensíveis.
- Não armazenar uploads de usuário dentro da pasta pública `src/app/static`.

---

## 13. Checklist de fechamento e prontidão

**Concluído:**

- [x] Escopo consolidado
- [x] Requisitos revisados
- [x] Regras de negócio revisadas
- [x] DER revisado
- [x] Dicionário de dados revisado
- [x] Catálogo de produtos corrigido com IDs, slugs e classe
- [x] Estratégia de seed definida (`produto_base` + `produto_tecnico`; preço/imagem vazios no MVP)
- [x] Decisão final sobre ORM: Flask-SQLAlchemy
- [x] Fundação Flask criada (`src/run.py` + `src/app/`)
- [x] Blueprints placeholders criados
- [x] Modelos SQLAlchemy de domínio criados (15 tabelas em `src/app/models/`)
- [x] Schema validável por `db.create_all()` e comando `flask init-db`
- [x] Flask-Migrate/Alembic configurado e migration inicial versionada
- [x] Validação do seed técnico (`flask validate-catalog-seed`)
- [x] Importação idempotente do catálogo (`flask import-catalog-seed`)
- [x] Autenticação real (login/logout, sessão, `login_required`, `seed-users`)
- [x] Dashboard Operacional somente leitura
- [x] CRUD de Glebas e Culturas (+ associação cultura↔gleba)
- [x] CRUD de Equipe e Financeiro (com totais receitas/despesas/saldo)
- [x] CRUD de Colheita (vinculada a cultura↔gleba)
- [x] Consulta do catálogo (Defensivos/Fertilizantes, somente leitura)
- [x] CRUD de Aplicações de Insumo (histórico operacional, sem recomendação)
- [x] Upload de Arquivos (local, seguro, escopado por propriedade)
- [x] Mapa real simplificado (somente leitura, escopado por propriedade)
- [x] IA Simulada Operacional (regras locais, histórico escopado)
- [x] Relatórios Operacionais HTML (somente leitura)
- [x] Permissões finas por perfil (matriz em código, backend 403, `can()` em templates)
- [x] Testes de fundação, schema, seed, autenticação, CRUDs, Dashboard, Mapa, IA, Relatórios, Permissões e consulta do catálogo

**Pendente:**

- [ ] CSRF/Flask-WTF
- [ ] Revisão e ajustes finais do MVP

---

## Documentos relacionados

- [00 — Visão Geral](./00-visao-geral.md)
- [02 — Requisitos do Sistema](./02-requisitos-do-sistema.md)
- [04 — Modelagem do Banco (DER)](./04-modelagem-banco-der.md)
- [05 — Dicionário de Dados](./05-dicionario-de-dados.md)
- [06 — Arquitetura do Sistema (visão conceitual)](./06-arquitetura-do-sistema.md)
- [07 — Roadmap do MVP](./07-roadmap-mvp.md)
- [Catálogo de Produtos](./catalogo-produtos/README.md)
