# 07 — Roadmap do MVP

> Documento-base. O roadmap orienta a sequência de trabalho e será ajustado a
> cada etapa concluída em branch + Pull Request.

## Etapa 0 — Organização do repositório ✅

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

## Etapa 3 — Catálogo de produtos ✅

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

## Etapa 4.1 — Modelos e banco SQLite ✅

- [x] **Modelos SQLAlchemy de domínio** (`src/app/models/`, 15 tabelas iniciais;
  schema atual com 18 após as Fases 7.1, 7.2 e 7.3).
- [x] **Schema validável** por `db.create_all()` nos testes e via `flask init-db`.

> Adotado **Flask-SQLAlchemy** como ORM. O banco real **não** é versionado.

## Etapa 4.2 — Migrations e importação do seed técnico ✅

- [x] **Flask-Migrate/Alembic** configurado (`migrations/` versionada).
- [x] **Migration inicial** das 15 tabelas (`flask db upgrade`) e migrations
  posteriores de `usuario_propriedade` (Fase 7.1), `senha_reset_token` (Fase 7.2)
  e `log_auditoria` (Fase 7.3).
- [x] **Validação** do seed técnico (`flask validate-catalog-seed`).
- [x] **Importação idempotente** do catálogo (`flask import-catalog-seed`):
  popula `produto_base` + `produto_tecnico`.
- [x] `produto_preco`/`produto_imagem` permanecem **vazios**; itens
  bloqueados (Paraquate/Oxamil) **não** importados.

> O seed é **importado sob demanda** via CLI; o banco populado **não** é
> versionado. Preço e imagem seguem pendentes para o sistema final.

## Etapa 5.1 — Autenticação real ✅

- [x] Login/logout com **sessão Flask** + **werkzeug.security** (hash de senha).
- [x] Tela de login (`templates/auth/login.html`) e mensagens flash.
- [x] **Proteção de rotas** dos módulos (`@login_required`); `/health` público.
- [x] Usuário atual disponível nos templates (context processor).
- [x] Comando `flask seed-users` (idempotente) com perfis **admin/tecnico/trabalhador**.
- [x] Testes de autenticação (`tests/test_auth.py`).

> Sem cadastro público, recuperação de senha, JWT ou painel de administração de
> usuários nesta fase.

## Etapa 5.2 — CRUD de Glebas e Culturas ✅

- [x] **CRUD de Glebas** (criar/listar/editar/remover), escopo por propriedade.
- [x] **CRUD de Culturas** (criar/listar/editar/remover) com `status`.
- [x] **Associação cultura↔gleba** (`cultura_gleba`) sincronizada no formulário.
- [x] Propriedade do usuário resolvida em `utils/contexto.py` (padrão criada se
  não existir).
- [x] Testes de CRUD e escopo (`tests/test_glebas_culturas_crud.py`).

## Etapa 5.3 — CRUD de Equipe e Financeiro ✅

- [x] **CRUD de Equipe** (criar/listar/editar/remover); `ativo`, e-mail
  normalizado; escopo por propriedade.
- [x] **CRUD de Financeiro** (criar/listar/editar/remover) com validação de
  `tipo` (receita/despesa), `valor > 0` e `data` obrigatória.
- [x] Listagem financeira com **totais**: receitas, despesas e saldo.
- [x] Testes de CRUD, validações, totais e escopo
  (`tests/test_equipe_financeiro_crud.py`).

## Etapa 5.4 — CRUD de Colheita ✅

- [x] **CRUD de Colheita** (criar/listar/editar/remover), vinculado a uma
  associação **cultura↔gleba** da propriedade atual.
- [x] Validações: `cultura_gleba_id` válido e da propriedade, `data` obrigatória,
  `quantidade` (se informada) número > 0 (vírgula/ponto).
- [x] Listagem com cultura, gleba, quantidade, unidade, qualidade + resumo.
- [x] Orientação ao usuário quando não há associação cultura↔gleba.
- [x] Testes de CRUD, validações e escopo (`tests/test_colheita_crud.py`).

## Etapa 5.5 — Consulta do Catálogo (Defensivos/Fertilizantes) ✅

- [x] **Consulta somente leitura** de Defensivos e Fertilizantes (listagem +
  detalhe por `slug`), filtrando por `classe`.
- [x] Busca textual (`q`) e filtros por `categoria` e `status_regulatorio`.
- [x] Detalhe com dados de `ProdutoBase` + `ProdutoTecnico`.
- [x] Avisos: base técnica de consulta, **não vende**, preço/imagem pendentes,
  status regulatório **sem** validação oficial automática.
- [x] Testes (`tests/test_catalogo_consulta.py`).

> **Somente leitura:** sem cadastro/edição/remoção de produto. `produto_preco`/
> `produto_imagem` seguem **vazios**; sem migration nova.

## Etapa 5.6 — Registro de Aplicação de Insumo ✅

- [x] **CRUD de Aplicações de Insumo** (criar/listar/editar/remover), protegido
  por login e escopado por propriedade.
- [x] Cada aplicação vincula uma associação **cultura↔gleba** da propriedade
  atual a um `ProdutoBase` do catálogo.
- [x] Produtos com status histórico/bloqueado não aparecem no select e não podem
  ser registrados.
- [x] Validações: cultura↔gleba, produto, data e dose opcional numérica maior que zero.
- [x] Avisos: histórico operacional, sem recomendação agronômica, sem validação
  técnica de dose e sem venda/carrinho/cotação.
- [x] Testes (`tests/test_aplicacoes_crud.py`).

> Sem migration nova. Sem CRUD de produto, sem preço, sem imagem e sem recomendação agronômica.

## Etapa 5.7 — Upload de Arquivos ✅

- [x] **Upload de Arquivos** com listagem, envio, download e remoção, protegido
  por login e escopado por propriedade.
- [x] Arquivos físicos salvos em `UPLOAD_FOLDER`, organizados por subpasta
  `propriedade_<id>/`.
- [x] Metadados gravados em `upload_arquivo`: nome original, caminho relativo,
  MIME, tamanho, descrição e propriedade.
- [x] Uso de `secure_filename` e nome único com UUID para evitar sobrescrita.
- [x] Allowlist de extensões: `pdf`, `png`, `jpg`, `jpeg`, `csv`, `xlsx`, `txt`, `docx`.
- [x] Bloqueio de executáveis, scripts, compactados e demais extensões fora da allowlist.
- [x] Download e remoção retornam 404 para arquivo de outra propriedade.
- [x] Pasta padrão corrigida para `instance/uploads`, fora de `src/app/static`.
- [x] Testes (`tests/test_upload_crud.py`).

> Sem migration nova: o modelo/tabela `UploadArquivo` já existia. Sem OCR, IA,
> extração automática, upload de imagem de produto ou armazenamento em nuvem.

## Etapa 5.8 — Dashboard Operacional ✅

- [x] Dashboard em `/`, protegido por login e escopado pela propriedade atual.
- [x] Agregações somente leitura via `src/app/services/dashboard_service.py`.
- [x] Indicadores de Glebas, Culturas, Financeiro, Equipe, Colheita, Aplicações,
  Upload e Catálogo.
- [x] Últimos registros financeiros, colheitas, aplicações e uploads.
- [x] Atalhos rápidos para módulos já existentes.
- [x] Estados vazios para propriedade sem dados operacionais.
- [x] Testes de escopo, totais, estados vazios, catálogo global e ausência de
  termos de venda (`tests/test_dashboard_operacional.py`).

> Sem migration nova, sem models novos, sem CRUD novo, sem gráficos externos,
> sem mapa, sem IA, sem relatórios/PDF e sem recomendação agronômica.

## Etapa 5.9 — Mapa real simplificado ✅

- [x] Mapa em `/mapa/`, protegido por login e escopado pela propriedade atual.
- [x] Endpoint JSON `/mapa/dados` somente leitura, sem dados de usuário/e-mail.
- [x] Separação entre glebas com coordenadas válidas e glebas sem coordenadas válidas.
- [x] Validação de latitude/longitude em faixa aceitável, sem alterar dados gravados.
- [x] Renderização de marcadores com Leaflet via CDN e centro padrão no Brasil.
- [x] Suporte simples a `poligono_geojson` válido, ignorando conteúdo inválido.
- [x] Estados vazios para propriedade sem glebas e sem coordenadas válidas.
- [x] Testes (`tests/test_mapa_real.py`).

> Sem migration nova, sem models novos, sem CRUD de coordenadas, sem desenho de
> polígonos, sem medição de área, sem GPS em tempo real, sem PostGIS, sem camadas
> avançadas e sem dependência Python/NPM nova.

## Fase 6.1 — IA Simulada Operacional ✅

- [x] IA em `/ia/`, protegida por login e escopada pela propriedade atual.
- [x] Serviço `src/app/services/ia_simulada_service.py` com regras simples e sem
  dependência externa.
- [x] Classificação por palavras-chave: resumo, financeiro, glebas, culturas,
  colheita, aplicações, documentos, catálogo e fallback de ajuda.
- [x] Respostas baseadas em dados locais da propriedade atual.
- [x] Alertas operacionais simples para dados incompletos.
- [x] Registro de perguntas/respostas em `ia_interacao` com `tipo="simulada"`.
- [x] Histórico das últimas 10 interações filtrado por usuário e propriedade.
- [x] Avisos obrigatórios: sem recomendação de produto, sem validação de dose,
  sem diagnóstico agronômico, sem internet/fontes oficiais em tempo real e sem
  leitura de conteúdo de uploads.
- [x] Testes (`tests/test_ia_simulada.py` e `tests/test_ia_simulada_service.py`).

> Sem migration nova, sem alteração de models, sem dependência nova, sem LLM/API
> externa, sem OCR, sem leitura automática de uploads, sem recomendação
> agronômica, sem validação técnica de dose, sem relatórios/PDF e sem CSRF/Flask-WTF.

## Fase 6.2 — Relatórios Operacionais HTML ✅

- [x] Central de relatórios em `/relatorios/` + rotas `geral`, `financeiro`,
  `agricola`, `aplicacoes`, `uploads` (todas protegidas por login e via
  `propriedade_atual()`).
- [x] Serviço `src/app/services/relatorios_service.py` (somente leitura,
  reutiliza helpers do `dashboard_service`).
- [x] Relatório financeiro com filtros de período e tipo (receita/despesa) e
  totais (receitas/despesas/saldo); período/tipo inválido → 400.
- [x] Relatório de aplicações com filtros de período e classe; avisos de não
  recomendação e não validação de dose.
- [x] Relatórios geral, agrícola e de uploads (download por rota protegida).
- [x] Botão "Imprimir" (`window.print()`) e CSS de impressão; exportações
  CSV/PDF ficaram para a Fase 7.4 e já foram implementadas.
- [x] Testes (`tests/test_relatorios_operacionais.py` e
  `tests/test_relatorios_service.py`).

> Somente leitura: não cria/altera/remove dados; escopado por propriedade
> (nenhuma rota aceita `propriedade_id`). Sem migration, sem model novo, sem
> dependência nova, sem Excel, sem gráficos externos. Naquele momento ficaram
> pendentes permissões finas, CSRF/Flask-WTF, exportações CSV/PDF e revisão final;
> esses itens foram concluídos nas fases seguintes.

## Fase 6.3 — Permissões finas por perfil ✅

- [x] Utilitário central `src/app/utils/permissions.py`.
- [x] Perfis oficiais: `admin`, `tecnico`, `trabalhador`.
- [x] Matriz `PERMISSOES_POR_PERFIL` em código, sem migration/model/dependência nova.
- [x] `require_permission(...)` aplicado nas rotas sensíveis.
- [x] Backend retorna **403** para ação sem permissão.
- [x] `can(...)` disponível nos templates por context processor.
- [x] Menu, atalhos e botões de ação escondidos conforme permissão.
- [x] Página/handler 403 amigável.
- [x] Escopo por propriedade preservado.
- [x] Testes em `tests/test_permissions.py`.

> Permissões finas não substituem o isolamento por propriedade e não criam tabela
> de roles/permissões. A proteção CSRF foi tratada na Fase 6.4.

## Fase 6.4 — CSRF/Flask-WTF ✅

- [x] Dependência `Flask-WTF>=1.2` adicionada.
- [x] `CSRFProtect` centralizado em `src/app/extensions.py`.
- [x] `csrf.init_app(app)` inicializado na Application Factory.
- [x] CSRF ativo por padrão em desenvolvimento/produção.
- [x] `TestingConfig.WTF_CSRF_ENABLED = False` preservado para a suíte existente.
- [x] `csrf_token()` renderizado em todos os formulários POST do MVP.
- [x] Upload multipart envia token CSRF.
- [x] Handler/template 400 amigável para erro CSRF.
- [x] Testes específicos em `tests/test_csrf.py`.
- [x] Permissões continuam retornando 403 quando a requisição tem token válido.

> Sem WTForms completo, sem refatoração geral de formulários, sem migration, sem
> model novo, sem alteração de permissões, sem CRUD novo e sem mudança em seed,
> catálogo, preço ou imagem.

## Fase 6.5 — Revisão Final do MVP ✅

- [x] Suíte completa validada antes e depois dos ajustes finais.
- [x] Textos de interface revisados para refletir o MVP consolidado.
- [x] Formulários POST conferidos com token CSRF.
- [x] Navegação e botões revisados conforme permissões por perfil.
- [x] Limpeza simples dos `LegacyAPIWarning` em testes, sem alterar models.
- [x] README, arquitetura técnica, regras, roadmap e documentação de testes alinhados.
- [x] Checklist final de entrega criado em `docs/08-checklist-final-mvp.md`.

> Sem recurso pós-MVP, sem migration, sem model novo, sem dependência nova, sem
> CRUD novo, sem alteração de permissões e sem mudança no seed técnico.

## MVP base consolidado

O **MVP base** fica consolidado com autenticação, permissões finas, CSRF, CRUDs
operacionais, catálogo em consulta, upload seguro, dashboard, mapa simplificado,
IA simulada e relatórios HTML. Ele continua válido e testado. Por decisão de
produto, foi aberto o **MVP ampliado** (Fase 7) antes do encerramento definitivo.

## Fase 7 — MVP ampliado

> Decisão de produto: o MVP base está consolidado e o escopo foi **ampliado**. As
> fases abaixo passam a fazer parte do MVP (não são mais pós-MVP). Ver detalhes em
> [09 — Roadmap do MVP Ampliado](./09-roadmap-mvp-ampliado.md).

### Fase 7.0 — Redefinição oficial do MVP ampliado ✅ (concluída)

- [x] Documentação, roadmap, regras e checklist alinhados ao MVP ampliado.
- [x] Escopo ampliado registrado (entra / fica fora do ampliado / fora do produto).
- [x] **Nenhuma** funcionalidade nova implementada (fase somente documental).

### Fase 7.1 — Painel de usuários ✅ (concluída)

- [x] Admin lista usuários da propriedade; cria, edita perfil/status e inativa.
- [x] Sem cadastro público; mantém permissões por perfil e escopo por propriedade.
- [x] Associação `usuario_propriedade` criada com migration e compatibilidade com
  `propriedade.usuario_id`.
- [x] `seed-users` garante propriedade demo e vínculos dos usuários de teste.
- [x] Testes em `tests/test_usuarios_painel.py`.

### Fase 7.2 — Recuperação de senha ✅ (concluída)

- [x] Fluxo `/auth/esqueci-senha` e `/auth/redefinir-senha/<token>`, com link
  "Esqueci minha senha" no login.
- [x] Token seguro (`secrets.token_urlsafe`), expirável e de **uso único**;
  armazenado apenas como **hash** (SHA-256) em `senha_reset_token`.
- [x] Mensagem genérica (sem enumeração de e-mails); usuário inativo não recupera
  senha e não é reativado.
- [x] Sem envio real de e-mail: link de redefinição visível apenas em
  local/dev/teste (`PASSWORD_RESET_SHOW_DEV_LINK`).
- [x] Migration `senha_reset_token` (sem alterar `usuario`); CSRF nos POSTs.
- [x] Testes em `tests/test_password_reset.py`.

### Fase 7.3 — Auditoria/logs ✅ (concluída)

- [x] Tabela/model `log_auditoria` (migration própria, índices em
  `usuario_id`/`propriedade_id`/`acao`/`criado_em`).
- [x] Serviço central `auditoria_service.py` que nunca quebra o fluxo principal.
- [x] Eventos: login/logout, recuperação de senha, painel de usuários, CRUDs
  principais, upload/download/remoção, permissão negada e acesso a relatórios.
- [x] Tela `/auditoria/` **somente admin** (`auditoria.view`), escopo por
  propriedade e filtros simples.
- [x] Logs sem senha, token, hash, CSRF ou conteúdo de formulário/arquivo.
- [x] Testes em `tests/test_auditoria.py`.

### Fase 7.4 — PDF/exportações ✅ (concluída)

- [x] Exportação **CSV** (biblioteca padrão) e **PDF** (ReportLab) dos cinco
  relatórios (geral, financeiro, agrícola, aplicações, uploads), gerados em
  memória; serviço `exportacoes_service.py`.
- [x] Reaproveita `relatorios_service` e os mesmos filtros; escopo por
  propriedade; filtro inválido → 400 sem gerar arquivo.
- [x] Permissão `relatorios.view`; botões "Exportar CSV/PDF" preservando filtros.
- [x] Auditoria `exportacao.gerada` (e `exportacao.falha` em filtro inválido).
- [x] Dependência nova **ReportLab>=4.0**; sem nova tabela/migration/model.
- [x] Testes em `tests/test_exportacoes.py`.

### Fase 7.5 — Mapa avançado ✅ (concluída)

- [x] Edição/salvamento/limpeza do polígono da gleba (`poligono_geojson`) no mapa,
  com Leaflet + Leaflet.draw (CDN); um polígono por gleba.
- [x] Rotas POST `/mapa/glebas/<id>/poligono` e `.../poligono/limpar` com login,
  `mapa.edit`, CSRF e escopo por propriedade (404 fora da propriedade).
- [x] Validação de GeoJSON no backend (`services/mapa_service.py`): Polygon/
  MultiPolygon/Feature, faixa de coordenadas e tamanho; inválido → 400.
- [x] Permissão nova `mapa.edit` (admin/técnico); trabalhador só visualiza.
- [x] Auditoria `mapa.poligono.update`/`delete`/`falha` sem gravar GeoJSON.
- [x] Sem migration/model/tabela/dependência Python nova; testes em
  `tests/test_mapa_avancado.py`.

### Fase 7.6 — Revisão final do MVP ampliado ✅ (concluída)

- [x] Suíte completa validada: `python -m pytest` com **475 passed**.
- [x] `flask --app src/run.py db upgrade` validado.
- [x] `flask --app src/run.py seed-users` validado.
- [x] README, requisitos, regras, arquitetura, roadmap e documentação de testes
  revisados para refletir o MVP ampliado concluído.
- [x] Checklist final do MVP ampliado criado em
  `docs/10-checklist-final-mvp-ampliado.md`.
- [x] Sem recurso novo, CRUD novo, model, migration, tabela ou dependência.

## Etapa 5 — Implementação dos módulos

Ordem concluída:

- [x] Login (autenticação — ver Etapa 5.1)
- [x] Dashboard (ver Etapa 5.8)
- [x] Culturas (CRUD — ver Etapa 5.2)
- [x] Glebas (CRUD — ver Etapa 5.2)
- [x] Defensivos (consulta — ver Etapa 5.5)
- [x] Fertilizantes (consulta — ver Etapa 5.5)
- [x] Aplicações de Insumo (CRUD — ver Etapa 5.6)
- [x] Financeiro (CRUD — ver Etapa 5.3)
- [x] Upload (ver Etapa 5.7)
- [x] Equipe (CRUD — ver Etapa 5.3)
- [x] Colheita (CRUD — ver Etapa 5.4)
- [x] Mapa real (ver Etapa 5.9)
- [x] IA simulada (ver Fase 6.1)
- [x] Relatórios (ver Fase 6.2)

## Etapa 6 — Testes e qualidade

- [x] Testes da fundação (app factory, `/health`, rotas protegidas).
- [x] Testes de schema/modelos (18 tabelas, unicidade, schema validável).
- [x] Testes de validação e importação do seed técnico.
- [x] Testes de autenticação, CRUDs já entregues, Upload e consulta do catálogo.
- [x] Dashboard.
- [x] Mapa real.
- [x] IA simulada.
- [x] Relatórios operacionais HTML.
- [x] Permissões finas por perfil/módulo.
- [x] CSRF/Flask-WTF.
- [x] Revisão e ajustes finais do MVP.

---

## Próximo passo recomendado

**Pós-MVP — priorização de evoluções futuras.**

O MVP foi ampliado: painel de usuários, recuperação de senha, auditoria/logs,
PDF/exportações e mapa avançado **fazem parte do MVP ampliado** (Fase 7) e **não**
são mais pós-MVP. As Fases 7.1 a 7.6 foram entregues e o **MVP ampliado está
concluído**.

Permanecem como **pós-MVP** (avaliados depois):

- IA real/LLM, se futuramente aprovado;
- validação regulatória real do catálogo;
- preço/imagem com fontes reais e atualização periódica;
- OCR/leitura automática de uploads;
- deploy/produção completo;
- melhorias avançadas que não entrarem na Fase 7.

> **Observação:** venda, carrinho, checkout e cotação **não** são pós-MVP — são
> **fora do produto** (regra permanente), salvo mudança radical de produto
> explicitamente aprovada.

---

## Documentos relacionados

- [01 — Escopo do Projeto](./01-escopo-do-projeto.md)
- [06 — Arquitetura do Sistema](./06-arquitetura-do-sistema.md)
- [06.1 — Arquitetura Técnica do MVP](./06-1-arquitetura-tecnica-mvp.md)
- [08 — Checklist Final do MVP](./08-checklist-final-mvp.md)
- [09 — Roadmap do MVP Ampliado](./09-roadmap-mvp-ampliado.md)
