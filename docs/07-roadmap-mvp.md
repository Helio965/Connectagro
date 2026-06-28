# 07 — Roadmap do MVP

> Documento-base. O roadmap orienta a sequência de trabalho e será ajustado a
> cada etapa concluída.

## Etapa 0 — Organização do repositório ✅ (em andamento)

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

## Etapa 3 — Catálogo de produtos

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

- [x] **Modelos SQLAlchemy de domínio** (`src/app/models/`, 15 tabelas).
- [x] **Schema validável** por `db.create_all()` nos testes e via `flask init-db`.

> Adotado **Flask-SQLAlchemy** como ORM. O banco real **não** é versionado.

## Etapa 4.2 — Migrations e importação do seed técnico ✅

- [x] **Flask-Migrate/Alembic** configurado (`migrations/` versionada).
- [x] **Migration inicial** das 15 tabelas (`flask db upgrade`).
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

> Sem cadastro público, recuperação de senha, JWT ou permissões finas por módulo
> (etapas futuras).

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
> agronômica, sem validação técnica de dose, sem relatórios/PDF, sem permissões
> finas e sem CSRF/Flask-WTF.

## Fase 6.2 — Relatórios Operacionais HTML ✅

- [x] Central de relatórios em `/relatorios/` + rotas `geral`, `financeiro`,
  `agricola`, `aplicacoes`, `uploads` (todas `@login_required` e via
  `propriedade_atual()`).
- [x] Serviço `src/app/services/relatorios_service.py` (somente leitura,
  reutiliza helpers do `dashboard_service`).
- [x] Relatório financeiro com filtros de período e tipo (receita/despesa) e
  totais (receitas/despesas/saldo); período/tipo inválido → 400.
- [x] Relatório de aplicações com filtros de período e classe; avisos de não
  recomendação e não validação de dose.
- [x] Relatórios geral, agrícola e de uploads (download por rota protegida).
- [x] Botão "Imprimir" (`window.print()`) e CSS de impressão; sem PDF/exportação.
- [x] Testes (`tests/test_relatorios_operacionais.py` e
  `tests/test_relatorios_service.py`).

> Somente leitura: não cria/altera/remove dados; escopado por propriedade
> (nenhuma rota aceita `propriedade_id`). Sem migration, sem model novo, sem
> dependência nova, sem PDF/CSV/Excel, sem gráficos externos. Pendentes:
> permissões finas, CSRF/Flask-WTF e revisão final do MVP.

## Etapa 5 — Implementação dos módulos

Ordem sugerida (sujeita a ajuste):

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
- [x] Testes de schema/modelos (15 tabelas, unicidade, schema validável).
- [x] Testes de validação e importação do seed técnico.
- [x] Testes de autenticação, CRUDs já entregues, Upload e consulta do catálogo.
- [x] Dashboard.
- [x] Mapa real.
- [x] IA simulada.
- [x] Relatórios (operacionais HTML).
- [ ] Permissões finas por perfil/módulo
- [ ] CSRF/Flask-WTF
- [ ] Revisão e ajustes do MVP.

---

## Documentos relacionados

- [01 — Escopo do Projeto](./01-escopo-do-projeto.md)
- [06 — Arquitetura do Sistema](./06-arquitetura-do-sistema.md)
- [06.1 — Arquitetura Técnica do MVP](./06-1-arquitetura-tecnica-mvp.md)
