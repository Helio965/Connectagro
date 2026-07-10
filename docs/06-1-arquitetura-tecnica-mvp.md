# 06.1 — Arquitetura Técnica do MVP

## Status do documento

**Arquitetura técnica — v0.26 (MVP base consolidado + MVP ampliado concluído: painel de usuários + recuperação de senha + auditoria/logs + PDF/exportações + mapa avançado + CRUDs + catálogo + upload + dashboard + IA simulada + relatórios operacionais + permissões finas + CSRF + revisão final).**

> **Mapa avançado (Fase 7.5):** o módulo Mapa passa a permitir **editar, salvar e
> limpar** o polígono (`gleba.poligono_geojson`) de cada gleba, com Leaflet +
> **Leaflet.draw** (via CDN). Adiciona `services/mapa_service.py` (validação/
> normalização de GeoJSON) e as rotas POST `/mapa/glebas/<id>/poligono` e
> `.../poligono/limpar`, com `mapa.edit` (admin/técnico; trabalhador só
> visualiza), CSRF (token via header `X-CSRFToken`), escopo por propriedade e
> auditoria (`mapa.poligono.update`/`delete`/`falha`). **Sem** migration/model/
> tabela/dependência Python nova — usa o campo já existente.
>
> **Revisão final do MVP ampliado (Fase 7.6):** valida a suíte completa, corrige
> documentação contraditória, cria o checklist final do MVP ampliado e encerra a
> Fase 7 sem criar rota funcional, model, migration, tabela ou dependência.

> **PDF/exportações (Fase 7.4):** o MVP ampliado adiciona
> `services/exportacoes_service.py` e rotas `/relatorios/<slug>/exportar.csv` e
> `.../exportar.pdf` para os cinco relatórios. CSV usa a biblioteca padrão
> (`csv`); PDF usa **ReportLab** (única dependência nova), tudo gerado **em
> memória** (`io.StringIO`/`io.BytesIO`), sem arquivo em disco. As exportações
> reutilizam `relatorios_service`, respeitam `relatorios.view`, os mesmos filtros
> (400 sem gerar arquivo em filtro inválido) e o escopo por propriedade, e
> registram auditoria `exportacao.gerada`. Não há tabela/migration/model novos.

> **Auditoria/logs (Fase 7.3):** o MVP ampliado adiciona o modelo `LogAuditoria`
> (tabela `log_auditoria`, migration própria), `services/auditoria_service.py`,
> o blueprint `/auditoria/` (somente `admin`, permissão `auditoria.view`) e a
> instrumentação das rotas sensíveis (autenticação, recuperação de senha, painel
> de usuários, CRUDs, upload/download e permissão negada). Os logs guardam apenas
> dados mínimos — **nunca** senha, token, hash, CSRF ou conteúdo de
> formulário/arquivo —, são escopados por propriedade e a auditoria **nunca**
> quebra o fluxo principal.

> **Recuperação de senha (Fase 7.2):** o MVP ampliado adiciona o modelo
> `SenhaResetToken` (tabela `senha_reset_token`, migration própria),
> `services/password_reset_service.py` e as rotas públicas
> `/auth/esqueci-senha` e `/auth/redefinir-senha/<token>`. O token é seguro
> (`secrets.token_urlsafe`), expirável e de **uso único**; apenas o **hash**
> (SHA-256) é armazenado. Com `MAIL_ATIVO` e SMTP configurados, o link é enviado
> por Flask-Mail; sem envio ativo, aparece em tela apenas em local/dev/teste
> quando `PASSWORD_RESET_SHOW_DEV_LINK=true`.
> Usuário inativo não recupera senha e não é reativado; a tabela `usuario` não
> é alterada.

> **Redefinição do MVP ampliado (Fase 7.0):** por decisão de produto, o MVP foi
> ampliado. As fases 7.x passam a incluir painel de usuários, recuperação de
> senha, auditoria/logs, PDF/exportações e mapa avançado (ver a seção
> [14 — Arquitetura planejada para o MVP ampliado](#14-arquitetura-planejada-para-o-mvp-ampliado)
> e o [09 — Roadmap do MVP Ampliado](./09-roadmap-mvp-ampliado.md)). A Fase 7.0 é
> **somente documental** — não há implementação de funcionalidade nova.

> **Painel de Usuários (Fase 7.1):** o MVP ampliado adiciona `usuarios_bp`
> (`/usuarios`), `services/usuarios_service.py`, o modelo
> `UsuarioPropriedade`, a migration `usuario_propriedade` e permissões
> `usuarios.*` apenas para `admin`. O painel é interno, sem cadastro público,
> sem remoção física e sem recuperação de senha nesta fase.

> **Revisão Final do MVP (Fase 6.5):** o MVP foi revisado como conjunto
> funcional, com validação da suíte automatizada, conferência de formulários POST
> com CSRF, permissões por perfil, textos de interface, documentação final e
> checklist de entrega em `docs/08-checklist-final-mvp.md`.

> **CSRF/Flask-WTF (Fase 6.4):** `Flask-WTF` foi adicionado às dependências e
> `CSRFProtect` é inicializado pela Application Factory. Todos os formulários
> POST renderizam `csrf_token()`, incluindo Upload multipart e IA simulada. CSRF
> fica ativo por padrão em desenvolvimento/produção e desativado no
> `TestingConfig`; `tests/test_csrf.py` ativa a proteção explicitamente para
> validar 400 sem token e fluxos com token válido.
>
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
> tudo pela propriedade atual. Na Fase 6.2 a renderização era HTML (Jinja2) com
> impressão pelo navegador (`window.print()`); as exportações CSV/PDF foram
> adicionadas depois na Fase 7.4. Os relatórios não criam/alteram/removem dados.

Este documento **complementa** o [06 — Arquitetura do Sistema](./06-arquitetura-do-sistema.md):

- O documento **06** é a **visão conceitual/geral** (camadas em alto nível).
- O documento **06.1** (este) é o **guia técnico detalhado** da implementação do
  MVP em Flask.

> **Estado final do MVP ampliado:** estão prontos a fundação Flask, modelos SQLAlchemy (18
> tabelas), migrations, importação do catálogo técnico via CLI, autenticação real,
> permissões finas por perfil, proteção **CSRF/Flask-WTF**, **Dashboard
> Operacional** somente leitura, **Mapa avançado operacional** com edição de
> polígonos por admin/técnico,
> **IA Simulada Operacional** baseada em
> regras locais, **Relatórios Operacionais HTML + exportações CSV/PDF**, CRUDs de Glebas, Culturas,
> Equipe, Financeiro, Colheita, Aplicações de Insumo, **Upload de Arquivos** e
> **Painel de Usuários**, **Recuperação de Senha**, **Auditoria/logs**,
> **Exportações CSV/PDF** e **Mapa avançado**,
> além da consulta somente leitura de Defensivos e Fertilizantes.
> `ProdutoPreco` segue vazio; `ProdutoImagem` é populado com uma imagem local de
> referência por produto, com fonte/licença rastreadas.
>
> **Dashboard Operacional:** agrega dados já existentes da propriedade atual,
> usando consultas aos módulos operacionais. Ele não cria registros, não altera
> models e não exige migration.
>
> **Mapa avançado:** usa os campos já existentes em `gleba` (`latitude`,
> `longitude`, `poligono_geojson`) para renderizar uma visualização operacional em
> `/mapa/`, expor dados em `/mapa/dados` e editar/salvar/limpar polígonos com
> permissão `mapa.edit`. Ele não cria registros, não altera models e não exige
> migration.
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
> **Estado final:** MVP base consolidado e MVP ampliado concluído. Validação
> regulatória real, preço atualizado, imagens oficiais/do fabricante, OCR,
> deploy completo e IA externa ficam fora do MVP ampliado.

## Objetivo

Definir **como** o MVP é construído tecnicamente, oferecendo um guia claro e
consistente para a implementação incremental.

---

## 1. Visão técnica geral

O MVP é uma **aplicação web monolítica** em **Flask**, renderizada no servidor
(Server-Side Rendering com Jinja2), com **SQLite** como banco local padrão ou
**PostgreSQL/Supabase** por configuração e frontend em **HTML/CSS/JavaScript**.
A organização segue separação por camadas e por módulos
(blueprints), favorecendo manutenção, testes e evolução futura.

```text
Navegador (HTML/CSS/JS)
        │  HTTP
        ▼
Flask (rotas/blueprints)  ──►  Serviços/helpers  ──►  Modelos/Acesso a dados
        │                                                       │
        ▼                                                       ▼
   Templates Jinja2                                  SQLite / PostgreSQL
```

### Princípios técnicos

- **Application Factory** (`create_app`) para criar a aplicação de forma
  configurável e testável.
- **Blueprints** para isolar cada módulo do MVP.
- **Separação de responsabilidades:** rotas simples, helpers locais para CRUDs e
  serviços quando houver regra compartilhada.
- **Dashboard como agregação somente leitura:** consulta dados existentes e não
  modifica estado.
- **Mapa avançado operacional:** usa coordenadas e `poligono_geojson` já
  cadastrados em Glebas; admin/técnico editam polígonos com validação e sem
  alterar schema.
- **IA simulada por regras:** usa dados locais e não executa integração externa.
- **Relatórios como consultas HTML somente leitura + exportações CSV/PDF:**
  exportações são operacionais, em memória e sem documento comercial.
- **Autorização por perfil em código:** protege rotas no backend e ajuda a
  renderizar menus/botões conforme perfil.
- **CSRF em formulários POST:** proteção global com Flask-WTF/CSRFProtect e
  tokens renderizados nos templates.
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
| Banco de dados   | SQLite ou PostgreSQL                         | SQLite local; Supabase via configuração        |
| Acesso a dados   | Flask-SQLAlchemy                             | ORM adotado                                    |
| Migrations       | Flask-Migrate (Alembic)                      | Pasta `migrations/` versionada                 |
| Upload local     | Werkzeug `secure_filename` + Flask `send_from_directory` | Arquivos fora de `static` e do Git |
| Mapa frontend    | Leaflet.js + Leaflet.draw via CDN            | Edição de polígono; sem dependência Python/NPM |
| IA simulada      | Regras locais em Python                      | Sem LLM/API externa/internet                   |
| Relatórios       | Serviços Python + Jinja2                     | HTML somente leitura + CSV/PDF operacional     |
| Exportações      | `csv` (lib padrão) + ReportLab (PDF)         | CSV/PDF em memória; `exportacoes_service.py`   |
| Autenticação     | Sessão Flask + hash de senha (Werkzeug)      | Helpers em `utils/auth.py`                     |
| Autorização      | Matriz em código                             | `utils/permissions.py`; sem tabela de roles    |
| Formulários/CSRF | Flask-WTF / CSRFProtect                     | Token em formulários POST; testes específicos  |
| E-mail transacional | Flask-Mail + SMTP                        | Convites e recuperação quando configurado      |
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
    ├── extensions.py            # db, migrate, csrf
    ├── commands.py              # init-db, validate/import-catalog-seed, seed-users
    ├── blueprints/
    │   ├── __init__.py          # registro central dos blueprints
    │   ├── auth/  dashboard/  culturas/  glebas/
    │   ├── defensivos/  fertilizantes/  aplicacoes/
    │   ├── financeiro/  upload/  equipe/  colheita/
    │   ├── mapa/  ia/  relatorios/
    │   └── usuarios/  auditoria/
    ├── models/                  # modelos SQLAlchemy de domínio (18 tabelas)
    ├── services/                # catalogo_seed.py, dashboard_service.py, ia_simulada_service.py, relatorios_service.py, usuarios_service.py, password_reset_service.py, auditoria_service.py, exportacoes_service.py, mapa_service.py
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
  configuração, inicializa `db`/`migrate`/`csrf`, registra modelos, blueprints,
  comandos CLI, context processors e handlers de erro.
- O context processor injeta `current_user`, `is_authenticated` e `can` nos
  templates Jinja.
- `src/app/blueprints/__init__.py` centraliza `ALL_BLUEPRINTS`.
- Cada módulo do MVP tem `__init__.py` com `Blueprint` e `routes.py` com as rotas.
- O handler 403 renderiza `templates/errors/403.html` com mensagem amigável, sem
  expor nomes internos de permissões.
- O handler de `CSRFError` renderiza `templates/errors/400.html` com mensagem
  amigável e status **400**, sem expor detalhes técnicos do token.

---

## 5. Mapeamento de módulos → blueprints

| Módulo (MVP)       | Blueprint        | Prefixo        | Entidades principais                              |
|--------------------|------------------|----------------|---------------------------------------------------|
| Login / Senha      | `auth`           | `/auth`        | `usuario`, `senha_reset_token`                    |
| Dashboard          | `dashboard`      | `/`            | agregações somente leitura                        |
| Culturas           | `culturas`       | `/culturas`    | `cultura`, `cultura_gleba`                        |
| Glebas             | `glebas`         | `/glebas`      | `gleba`, `cultura_gleba`                          |
| Defensivos         | `defensivos`     | `/defensivos`  | `produto_base`, `produto_tecnico`                 |
| Fertilizantes      | `fertilizantes`  | `/fertilizantes` | `produto_base`, `produto_tecnico`               |
| Aplicações         | `aplicacoes`     | `/aplicacoes`  | `aplicacao_insumo`, `cultura_gleba`, `produto_base` |
| Financeiro         | `financeiro`     | `/financeiro`  | `financeiro_lancamento`                           |
| Upload             | `upload`         | `/upload`      | `upload_arquivo`                                  |
| Usuários           | `usuarios`       | `/usuarios`    | `usuario`, `usuario_propriedade`, `propriedade`   |
| Equipe             | `equipe`         | `/equipe`      | `equipe_membro`                                   |
| Colheita           | `colheita`       | `/colheita`    | `colheita_registro`, `cultura_gleba`              |
| Mapa (avançado)    | `mapa`           | `/mapa`        | `gleba` (edição de `poligono_geojson`)            |
| IA simulada        | `ia`             | `/ia`          | `ia_interacao`                                    |
| Relatórios         | `relatorios`     | `/relatorios`  | leitura de múltiplas entidades                    |
| Auditoria          | `auditoria`      | `/auditoria`   | `log_auditoria` (somente `admin`)                 |

---

## 6. Acesso a dados, bancos e arquivos

- **Banco:** SQLite em `instance/` por padrão local; PostgreSQL/Supabase por
  `DATABASE_URL`, com `DIRECT_URL` opcional para migrations/conexão direta.
- **ORM:** `Flask-SQLAlchemy`, com instância `db` em `src/app/extensions.py`.
- **Migrations:** `Flask-Migrate/Alembic`, com migration inicial e evoluções
  versionadas.
- **Seeds:** `flask --app src/run.py import-catalog-seed` popula `produto_base` +
  `produto_tecnico` + `produto_imagem`. `produto_preco` continua vazio no MVP.
- **Dashboard:** não exige migration nova porque apenas consulta tabelas já
  existentes.
- **Aplicações de Insumo:** não exigem migration nova porque a tabela
  `aplicacao_insumo` já existe no schema inicial.
- **Upload:** não exige migration nova porque a tabela `upload_arquivo` já existe
  no schema inicial.
- **Mapa inicial / mapa avançado:** não exige migration nova porque usa campos
  já existentes em `gleba`.
- **IA simulada:** não exige migration nova porque usa a tabela `ia_interacao` já
  existente.
- **Relatórios:** não exigem migration nova porque apenas consultam dados já
  existentes.
- **Permissões finas:** não exigem migration nova porque usam `usuario.perfil` e
  matriz em código.
- **CSRF/Flask-WTF:** não exige migration nova porque protege formulários e não
  altera schema.
- **Painel de Usuários:** exige migration própria para `usuario_propriedade`, com
  backfill a partir de `propriedade.usuario_id`.
- **Recuperação de senha:** exige migration própria para `senha_reset_token`
  (índice em `usuario_id`, unicidade em `token_hash`); **não** altera a tabela
  `usuario`.
- **Auditoria/logs:** exige migration própria para `log_auditoria` (índices em
  `usuario_id`, `propriedade_id`, `acao` e `criado_em`); **não** altera as
  tabelas existentes.
- **Mapa avançado:** **não** exige migration nova porque a edição de polígonos
  usa o campo já existente `gleba.poligono_geojson`.

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

### Mapa avançado operacional

- `src/app/blueprints/mapa/routes.py` resolve a propriedade atual e renderiza
  `templates/mapa/index.html` em `/mapa/`.
- `/mapa/dados` retorna JSON de leitura com `propriedade`, `glebas` e
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

#### Edição de polígonos (Fase 7.5)

- `templates/mapa/index.html` expõe `data-csrf-token` e `data-can-edit` no
  container do mapa; os controles de edição (select de gleba, "Salvar"/"Limpar")
  só aparecem para quem tem `mapa.edit`.
- `mapa.js` usa **Leaflet.draw** (CDN) para desenhar/editar **um polígono por
  gleba**; o salvamento é um `fetch` POST com header `X-CSRFToken`. Se
  Leaflet.draw não carregar, o mapa segue como somente leitura.
- `POST /mapa/glebas/<id>/poligono` valida o GeoJSON via
  `services/mapa_service.validar_poligono_geojson` (Polygon/MultiPolygon/Feature;
  fecha anéis; coordenadas em faixa; **≤ 100 KB**; recusa FeatureCollection/
  GeometryCollection), grava em `gleba.poligono_geojson`, atualiza `atualizado_em`
  e responde JSON. GeoJSON inválido → **400** (`{"ok": false, "error": ...}`).
- `POST /mapa/glebas/<id>/poligono/limpar` zera o polígono.
- Ambas exigem login + `mapa.edit`; gleba de outra propriedade → **404**.
  Auditoria: `mapa.poligono.update`/`mapa.poligono.delete`/`mapa.poligono.falha`,
  **sem** gravar GeoJSON/coordenadas no log.
- O mapa **não** mede área, não importa/exporta arquivos geográficos
  (shapefile/KML), não usa GPS em tempo real nem PostGIS, e não adiciona
  dependência Python/NPM (Leaflet.draw é via CDN). A edição de polígonos é apoio
  operacional e não substitui medição técnica ou georreferenciamento oficial.

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
- Exportações CSV/PDF (Fase 7.4) reutilizam estes mesmos serviços/filtros — ver
  "Exportações (CSV/PDF)" abaixo. Não há Excel/XLSX nem exportação automática.

### Exportações (CSV/PDF)

- `src/app/services/exportacoes_service.py` gera **CSV** (módulo `csv` da
  biblioteca padrão, `io.StringIO`, UTF-8 sem BOM, separador vírgula) e **PDF**
  (ReportLab, `io.BytesIO`, A4 paisagem), **sem** escrever arquivo em disco.
- Rotas em `relatorios/routes.py`: `/relatorios/<slug>/exportar.csv` e
  `.../exportar.pdf` para `geral`, `financeiro`, `agricola`, `aplicacoes` e
  `uploads`, todas com `@login_required` + `require_permission("relatorios.view")`.
- As exportações chamam os mesmos `montar_relatorio_*` e aplicam os mesmos
  filtros (financeiro: período/tipo; aplicações: período/classe). Filtro inválido
  (`FiltroInvalidoError`) registra `exportacao.falha` e retorna **400**, **sem**
  gerar arquivo nem registrar sucesso.
- Cada exportação bem-sucedida registra auditoria `exportacao.gerada` (entidade
  `relatorio`, `entidade_id` = slug), **sem** gravar o conteúdo do relatório.
- Todo CSV/PDF inclui um aviso fixo: "Relatório operacional interno. Não é
  cotação, venda, recomendação agronômica ou documento comercial."
- Os templates dos relatórios ganham botões "Exportar CSV/PDF" que **preservam os
  filtros atuais** (financeiro e aplicações via querystring).
- Sem nova tabela, migration, model ou permissão; única dependência nova:
  `ReportLab>=4.0`.

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
| `admin` | Acessa todos os módulos; cria, edita e remove registros nos CRUDs da sua propriedade; envia, baixa e remove uploads; gerencia usuários internos da propriedade; consulta a auditoria/logs (`auditoria.view`); edita polígonos no mapa (`mapa.edit`). |
| `tecnico` | Acessa dashboard, mapa, catálogo, relatórios, IA, equipe e financeiro em leitura; cria/edita glebas, culturas, colheitas e aplicações; **edita polígonos no mapa** (`mapa.edit`); envia e baixa uploads; não remove registros críticos nem gerencia equipe/financeiro. |
| `trabalhador` | Acessa dashboard, mapa, catálogo, relatórios e IA; **visualiza** o mapa mas **não** edita polígonos; visualiza glebas, culturas, colheitas e aplicações; cria colheitas, aplicações e uploads; baixa uploads; não acessa equipe/financeiro e não edita/remove registros críticos. |

### Painel de usuários

- `src/app/blueprints/usuarios/routes.py` expõe `/usuarios/`,
  `/usuarios/novo`, `/usuarios/<id>/editar` e `/usuarios/<id>/inativar`.
- Todas as rotas exigem login, CSRF em POST e permissões `usuarios.*`; no MVP
  ampliado, essas permissões pertencem apenas ao perfil `admin`.
- `src/app/services/usuarios_service.py` concentra criação, edição, inativação,
  listagem e validações do painel.
- `src/app/models/usuario_propriedade.py` representa a associação explícita entre
  conta e propriedade, com par (`usuario_id`, `propriedade_id`) único.
- `utils/contexto.py` resolve a propriedade atual primeiro por vínculo ativo em
  `usuario_propriedade`. Se a base ainda usa apenas `propriedade.usuario_id`, a
  associação ativa é criada automaticamente para manter compatibilidade.
- `seed-users` cria/garante os três usuários de teste, uma propriedade demo e os
  vínculos ativos, sem sobrescrever senhas existentes e sem duplicar associações.
- O painel não implementa cadastro público, recuperação de senha, auditoria,
  remoção física de usuário, tabela de roles/permissões ou múltiplas propriedades
  selecionáveis.
- A inativação marca `usuario.ativo = 0` e `usuario_propriedade.ativo = 0`; o
  serviço impede deixar a propriedade sem nenhum `admin` ativo.

### Recuperação de senha

- `src/app/blueprints/auth/routes.py` expõe as rotas **públicas**
  `/auth/esqueci-senha` (GET/POST) e `/auth/redefinir-senha/<token>` (GET/POST);
  o login tem o link "Esqueci minha senha".
- `src/app/services/password_reset_service.py` concentra a lógica:
  `gerar_token_reset`, `hash_token`, `solicitar_reset_por_email`,
  `validar_token_reset`, `redefinir_senha_com_token`,
  `invalidar_tokens_abertos_do_usuario`, `token_expirado` e
  `limpar_tokens_expirados_opcional`.
- `src/app/models/senha_reset_token.py` (`SenhaResetToken`) guarda apenas o
  **hash** (SHA-256) do token, `expira_em`, `usado`/`usado_em` e dados mínimos da
  solicitação (`ip_solicitacao`, `user_agent_solicitacao`). O token puro nunca é
  persistido e nenhuma senha é gravada nessa tabela.
- O token é gerado com `secrets.token_urlsafe(32)`, expira conforme
  `PASSWORD_RESET_TOKEN_MINUTES` (padrão 30) e é de **uso único**. Solicitar novo
  reset invalida os tokens abertos anteriores do usuário.
- A solicitação responde sempre com **mensagem genérica** (sem enumeração de
  e-mails). E-mail inexistente ou usuário inativo **não** geram token válido.
- Com `MAIL_ATIVO` e as credenciais SMTP configurados,
  `services/email_service.py` envia o link via Flask-Mail. Sem envio ativo, a
  tela pode exibir o link somente em local/dev/teste quando
  `PASSWORD_RESET_SHOW_DEV_LINK=true`; em produção, nunca.
- A redefinição valida o token novamente, exige nova senha (mínimo 6 caracteres)
  e confirmação, grava o **hash** da nova senha, marca o token como usado, **não
  reativa** usuário inativo e **não** autentica automaticamente (redireciona ao
  login).
- Todas as rotas POST enviam token CSRF; `TestingConfig` mantém CSRF desativado
  por padrão e `tests/test_password_reset.py` ativa a proteção quando valida CSRF.

### Auditoria/logs

- `src/app/models/log_auditoria.py` (`LogAuditoria`) define a tabela
  `log_auditoria` com `acao`, `entidade`, `entidade_id`, `resultado`
  (`sucesso`/`falha`/`negado`), `descricao`, `ip`, `user_agent`, `usuario_id`,
  `propriedade_id` e `criado_em`.
- `src/app/services/auditoria_service.py` concentra `registrar_evento`,
  `registrar_sucesso`, `registrar_falha`, `registrar_negado`, `listar_logs`,
  `normalizar_descricao`, `mascarar_email` e `_extrair_request_info`.
- **Nunca quebra o fluxo principal:** toda a gravação fica em `try/except` com
  `rollback`; uma falha de auditoria retorna `None` sem propagar exceção. Eventos
  públicos (login falho, e-mail inexistente) **não** resolvem/criam propriedade.
- O serviço grava apenas **dados mínimos** e limita a descrição (≤ 500 chars).
  As rotas passam descrições curtas e **nunca** `request.form`, senha, token,
  hash ou `csrf_token`. E-mails em descrições são **mascarados**
  (`a***@dominio.com`).
- Instrumentação: `auth` (login sucesso/falha, logout, reset solicitado/
  redefinido/token inválido), `usuarios` (create/edit/deactivate), CRUDs de
  glebas/culturas/equipe/financeiro/colheita/aplicações (create/edit/delete),
  `upload` (create/download/delete), `relatorios` (acesso à central) e
  `permissao.negada` (registrada em `require_permission` antes do `abort(403)`,
  com import local para evitar ciclo).
- `src/app/blueprints/auditoria/routes.py` expõe `/auditoria/` (somente `admin`,
  permissão `auditoria.view`), com filtros simples (ação, resultado, entidade,
  usuário) e limite de 100 registros mais recentes, escopados pela propriedade
  atual. O template trunca o user-agent e não exibe dados sensíveis.
- A ação `exportacao.gerada` fica **preparada/documentada** para a Fase 7.4
  (PDF/exportações) e ainda não é emitida.

### CSRF/Flask-WTF

- `Flask-WTF>=1.2` é a única dependência nova da Fase 6.4.
- `src/app/extensions.py` cria a instância central `csrf = CSRFProtect()`.
- `create_app` chama `csrf.init_app(app)` junto das demais extensões.
- `BaseConfig.WTF_CSRF_ENABLED` fica ativo por padrão, com possibilidade de
  ajuste por variável de ambiente `WTF_CSRF_ENABLED`.
- `TestingConfig.WTF_CSRF_ENABLED = False` preserva a suíte existente, que já
  fazia POSTs sem token.
- Todos os formulários `method="post"` renderizam:

```html
<input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
```

- Formulários multipart (`enctype="multipart/form-data"`) também enviam o token.
- Rotas GET, como `/health`, catálogo, dashboard, relatórios e `/mapa/dados`, não
  exigem token CSRF.
- `CSRFError` retorna **400** com mensagem amigável em `templates/errors/400.html`.
- CSRF é uma camada adicional: autenticação, permissões e escopo por propriedade
  continuam sendo validados separadamente.

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
- No MVP, **preço permanece pendente**; imagens locais de referência são
  importadas com fonte/licença rastreadas e status não consolidado.
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

### CSRF/Flask-WTF ✅
- Proteção global com `CSRFProtect`.
- CSRF ativo por padrão em desenvolvimento/produção.
- CSRF desativado no `TestingConfig` para preservar os testes legados.
- `csrf_token()` em todos os formulários POST.
- Upload multipart protegido com token.
- Handler 400 amigável para erro CSRF.
- Testes específicos em `tests/test_csrf.py`.

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

### Mapa avançado ✅
- Visualização das glebas em `/mapa/` com edição de polígonos por admin/técnico.
- Endpoint `/mapa/dados` com JSON filtrado pela propriedade atual.
- Usa `latitude`, `longitude` e `poligono_geojson` existentes em `Gleba`.
- Separa glebas sem coordenadas válidas e ignora GeoJSON inválido com segurança.
- Permite desenhar, salvar e limpar um polígono por gleba com validação backend,
  CSRF e auditoria. Trabalhador apenas visualiza.
- Sem medição de área, GPS em tempo real, PostGIS, shapefile/KML ou
  georreferenciamento oficial.

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
- HTML somente leitura, escopado por propriedade, com exportação CSV/PDF
  operacional em memória.
- Sem Excel/XLSX, exportação automática/agendada, alteração de dados,
  recomendação de produto, validação de dose, leitura de conteúdo dos uploads,
  cotação, venda ou documento comercial.

---

## 10. Configuração, autenticação e segurança

- Configuração por ambiente em `app/config.py`.
- Sessão Flask assinada por `SECRET_KEY`, guardando dados mínimos do usuário.
- Senhas com `werkzeug.security`.
- Autenticação em `utils/auth.py` com `login_required`.
- Autorização em `utils/permissions.py` com `PERMISSOES_POR_PERFIL`,
  `require_permission(...)` e `can(...)`.
- Handler/template 403 para ações sem permissão.
- Handler/template 400 para falha de CSRF.
- CSRF/Flask-WTF ativo nos formulários POST; `TestingConfig` mantém CSRF
  desativado por padrão e `tests/test_csrf.py` ativa a proteção explicitamente.
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
- `tests/test_csrf.py` cobre CSRF desativado por padrão em testes, inicialização
  do `CSRFProtect`, token nos formulários, POST sem token retornando 400, POST
  com token válido funcionando, Upload multipart com/sem token, rotas GET sem
  token, erro amigável e convivência com permissões 403.
- `tests/test_usuarios_painel.py` cobre acesso somente por `admin`,
  criação/edição/inativação de usuários, vínculo por propriedade, bloqueio do
  último admin ativo, compatibilidade com base legada, `seed-users` idempotente e
  convivência com CSRF/permissões.
- `tests/test_password_reset.py` cobre link "Esqueci minha senha", mensagem
  genérica (sem enumeração), criação de token só para usuário ativo, hash do
  token sem token puro, expiração, link dev exibido/ocultado por configuração,
  validação/expiração/uso único do token, validações de nova senha, login com
  senha antiga/nova após redefinir, usuário inativado depois e CSRF nos POSTs.
- `tests/test_auditoria.py` cobre model/schema, o serviço (criação de log,
  truncamento, resultado inválido → sucesso, falha de auditoria não quebra o
  fluxo, máscara de e-mail), a tela `/auditoria/` (login, admin 200, técnico/
  trabalhador 403, link no menu por perfil, filtro), eventos de autenticação,
  recuperação de senha, painel de usuários, permissão negada, upload e CRUDs,
  escopo por propriedade e ausência de senha/token/CSRF nos logs.
- `tests/test_exportacoes.py` cobre as exportações CSV/PDF dos cinco relatórios:
  exigência de login, acesso por `relatorios.view` (admin e técnico), headers e
  `Content-Disposition` de CSV/PDF, assinatura `%PDF-`, conteúdo escopado pela
  propriedade (sem dados de outra), filtros válidos e inválidos (400 sem gerar
  arquivo), preservação de filtros nos links, auditoria `exportacao.gerada`/
  `exportacao.falha`, ausência de dados sensíveis no log e garantia de que
  exportar não cria dados nem `ProdutoPreco`/`ProdutoImagem`.
- `tests/test_mapa_avancado.py` cobre a edição de polígonos: matriz de `mapa.edit`
  (admin/técnico sim, trabalhador não); GET do mapa para todos os perfis; salvar
  polígono (admin/técnico 200, trabalhador 403, sem login redireciona, gleba de
  outra propriedade 404); validação de GeoJSON (inválido, fora de faixa, anel
  curto, payload grande → 400; Polygon/MultiPolygon/Feature aceitos;
  FeatureCollection recusado); persistência/substituição e `atualizado_em`;
  limpar polígono; auditoria `mapa.poligono.update/delete/falha` sem GeoJSON nos
  logs e escopada por propriedade; `data-csrf-token`/`data-can-edit` e controles
  por perfil no template; e CSRF nos POSTs via `X-CSRFToken`.

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
- Mapa avançado deve permanecer operacional: admin/técnico podem editar
  polígonos, trabalhador visualiza, e o recurso não substitui medição técnica ou
  georreferenciamento oficial.
- IA deve permanecer simulada por regras no MVP, sem LLM, API externa, internet,
  OCR, leitura de uploads, recomendação agronômica, validação de dose ou
  diagnóstico técnico.
- Relatórios devem permanecer HTML somente leitura, com CSV/PDF operacional em
  memória, sem alteração de dados, Excel/XLSX, cotação, venda ou documento
  comercial.
- Permissões devem bloquear no backend com 403; `can()` em template é apenas
  apoio visual.
- Permissões por perfil não substituem escopo por propriedade.
- Todo formulário POST deve renderizar `csrf_token()`.
- Upload multipart também deve enviar token CSRF.
- CSRF não substitui autenticação, permissões nem escopo por propriedade.
- No MVP, **preço** deve aparecer como pendente; imagens de referência podem
  aparecer com status não consolidado e placeholder apenas como fallback.
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
- [x] Estratégia de seed definida (`produto_base` + `produto_tecnico` +
  `produto_imagem`; preço vazio no MVP)
- [x] Decisão final sobre ORM: Flask-SQLAlchemy
- [x] Fundação Flask criada (`src/run.py` + `src/app/`)
- [x] Blueprints placeholders criados
- [x] Modelos SQLAlchemy de domínio criados (15 tabelas iniciais; 18 no schema
  atual após `usuario_propriedade`, `senha_reset_token` e `log_auditoria`)
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
- [x] Mapa avançado operacional (edição de polígonos por admin/técnico, escopado por propriedade)
- [x] IA Simulada Operacional (regras locais, histórico escopado)
- [x] Relatórios Operacionais HTML + exportações CSV/PDF
- [x] Permissões finas por perfil (matriz em código, backend 403, `can()` em templates)
- [x] CSRF/Flask-WTF nos formulários POST
- [x] Testes de fundação, schema, seed, autenticação, CRUDs, Dashboard, Mapa, IA, Relatórios, Permissões, CSRF e consulta do catálogo
- [x] Revisão e ajustes finais do MVP
- [x] Checklist final de entrega do MVP (`docs/08-checklist-final-mvp.md`)

**MVP ampliado (Fase 7):**

- [x] Painel de usuários (Fase 7.1)
- [x] Recuperação de senha (Fase 7.2)
- [x] Auditoria/logs administrativos (Fase 7.3)
- [x] PDF/exportações (Fase 7.4)
- [x] Mapa avançado (Fase 7.5)
- [x] Revisão final do MVP ampliado (Fase 7.6)

**Fora do MVP ampliado (avaliados depois):**

- [ ] Validação regulatória real do catálogo
- [ ] Preço com fontes reais e atualização periódica; imagens oficiais/do fabricante
- [ ] OCR/leitura automática de uploads
- [ ] Deploy/produção completo
- [ ] IA real/LLM, se futuramente aprovado

**Fora do produto (regra permanente):** venda, carrinho, checkout e cotação.

---

## 14. Arquitetura do MVP ampliado

> Esta seção descreve, em **alto nível**, a arquitetura implementada nas fases
> 7.x. As Fases 7.1 a 7.6 estão concluídas.

### Painel de usuários (Fase 7.1 — implementado)

- Gestão interna dos usuários da propriedade pelo `admin` (listar, criar, editar
  perfil/status, inativar); **sem** cadastro público.
- Tabela de associação `usuario_propriedade` com migration própria e backfill a
  partir de `propriedade.usuario_id`.
- `utils/contexto.py` usa vínculo ativo como fonte da propriedade atual, mantendo
  compatibilidade com bases antigas.
- Mantém as **permissões por perfil** (`utils/permissions.py`); a gestão de
  usuários exige permissões `usuarios.*`, concedidas apenas ao `admin`.
- Não inclui remoção física de usuário nem tabela de roles/permissões. Recuperação
  de senha e auditoria/logs foram entregues em fluxos próprios.

### Recuperação de senha (Fase 7.2 — implementado)

- Tabela de tokens `senha_reset_token` (migration própria) com **expiração**.
- Token **armazenado apenas como hash** (SHA-256), nunca em claro; uso único.
- Fluxo que **não expõe** senha nem token; na entrega original, o link aparecia
  apenas em local/dev/teste. O envio por Flask-Mail/SMTP foi incorporado
  posteriormente e é usado quando configurado.
- Mensagem genérica (sem enumeração); usuário inativo não recupera senha e não é
  reativado. Detalhes na seção "Recuperação de senha" acima.

### Auditoria/logs (Fase 7.3 — implementado)

- Tabela `log_auditoria` (migration própria) para eventos sensíveis.
- Eventos: criação/edição/remoção dos CRUDs, login/logout, recuperação de senha,
  painel de usuários, acesso negado, upload/download/remoção e exportações
  (`exportacao.gerada`/`exportacao.falha`).
- Registro **sem** senha, token, hash, CSRF ou conteúdo de formulário/arquivo;
  escopado por propriedade; consulta em `/auditoria/` apenas pelo `admin`.
  Detalhes na seção "Auditoria/logs" acima.

### PDF/exportações (Fase 7.4 — implementado)

- `services/exportacoes_service.py` reutiliza `relatorios_service` para gerar
  **CSV** (biblioteca padrão) e **PDF** (ReportLab) em memória.
- Exportações **escopadas por propriedade** e por permissão (`relatorios.view`),
  com os mesmos filtros dos relatórios; filtro inválido → 400 sem gerar arquivo.
- Única dependência nova: **ReportLab>=4.0**; CSV usa o módulo `csv`.
- Exportação é relatório operacional, **nunca** cotação/venda, e gera auditoria
  `exportacao.gerada`. Detalhes na seção "Exportações (CSV/PDF)" acima.

### Mapa avançado (Fase 7.5 — implementado)

- Edição visual do polígono (`gleba.poligono_geojson`) com Leaflet + Leaflet.draw
  (CDN); validação de GeoJSON no backend (`services/mapa_service.py`).
- Rotas POST com `mapa.edit` (admin/técnico), CSRF, escopo por propriedade e
  auditoria. **Sem** migration/model/dependência Python nova.
- **Sem PostGIS**, GPS em tempo real, shapefile/KML ou medição oficial; o cálculo
  de área aproximada **não** foi implementado nesta fase. Detalhes na seção
  "Edição de polígonos (Fase 7.5)" acima.

### Revisão final do MVP ampliado (Fase 7.6 — implementado)

- Validação completa com `python -m pytest`, `flask --app src/run.py db upgrade`
  e `flask --app src/run.py seed-users`.
- Correção de documentação contraditória sobre mapa, exportações, contagem de
  tabelas e status do MVP ampliado.
- Criação do checklist final em `docs/10-checklist-final-mvp-ampliado.md`.
- Sem rota funcional nova, model, migration, tabela, dependência ou recurso
  pós-MVP.

### Fora do MVP ampliado

Permanecem fora do MVP ampliado, como pós-MVP: **IA real/LLM**, **validação
regulatória real** do catálogo, **preço atualizado**, **imagens oficiais/do
fabricante**, **OCR/leitura automática** de uploads e **deploy/produção
completo**. A IA do
produto continua **simulada**. **Venda, carrinho, checkout e cotação** nunca
entram no produto.

---

## Documentos relacionados

- [00 — Visão Geral](./00-visao-geral.md)
- [02 — Requisitos do Sistema](./02-requisitos-do-sistema.md)
- [04 — Modelagem do Banco (DER)](./04-modelagem-banco-der.md)
- [05 — Dicionário de Dados](./05-dicionario-de-dados.md)
- [06 — Arquitetura do Sistema (visão conceitual)](./06-arquitetura-do-sistema.md)
- [07 — Roadmap do MVP](./07-roadmap-mvp.md)
- [08 — Checklist Final do MVP](./08-checklist-final-mvp.md)
- [09 — Roadmap do MVP Ampliado](./09-roadmap-mvp-ampliado.md)
- [10 — Checklist Final do MVP Ampliado](./10-checklist-final-mvp-ampliado.md)
- [Catálogo de Produtos](./catalogo-produtos/README.md)
