# tests/

Testes automatizados do **ConnectAgro** (pytest).

## Estado atual

Os testes usam a **Application Factory** (`create_app("testing")`) com banco
**SQLite em memória** (ver `conftest.py`) e **não** dependem de banco `.db` real.
Testes de upload usam pasta temporária (`tmp_path`) para não escrever arquivos
reais no repositório. O `TestingConfig` mantém `WTF_CSRF_ENABLED = False` por
padrão para preservar os testes existentes; `test_csrf.py` ativa CSRF
explicitamente quando valida essa proteção.

Na Fase 6.5, a suíte foi usada como validação final do **MVP base** e os avisos
simples de `LegacyAPIWarning` em `test_ia_simulada_service.py` foram removidos
usando `db.session.get(...)`, sem alterar models ou comportamento funcional. A
Fase 6.5 encerrou o **MVP base**, não o produto: por decisão de produto, foi
aberto o **MVP ampliado** (Fase 7). As Fases 7.1 (painel de usuários), 7.2
(recuperação de senha), 7.3 (auditoria/logs), 7.4 (PDF/exportações) e 7.5 (mapa
avançado) adicionaram testes próprios; a Fase 7.6 (revisão final) manteve toda
a suíte passando sem adicionar funcionalidade nova.

Arquivos existentes:

- **`conftest.py`** — coloca `src/` no path; fixtures `app` e `client`.
- **`test_app_factory.py`** — criação da app no modo testing; `/health`; rota `/`.
- **`test_placeholder_routes.py`** — rotas públicas respondem 200; rotas dos
  módulos protegidos redirecionam sem login e respondem 200 com login quando o
  perfil possui permissão.
- **`test_models_schema.py`** — registro das 18 tabelas no metadata; colunas
  principais; `db.create_all()`; inserção mínima; unicidade de `usuario.email` e
  `produto_base.slug`; `produto_preco`/`produto_imagem` existem mas vazias; seed
  não importado automaticamente.
- **`test_catalogo_seed.py`** — Flask-Migrate inicializado sem quebrar a app;
  validação do seed; importação idempotente; preço/imagem vazios; itens
  bloqueados ignorados.
- **`test_auth.py`** — autenticação: `/auth/login`, login válido, senha errada,
  usuário inativo, logout, rotas protegidas, `/health` público, sessão sem senha,
  senha armazenada como hash e `seed-users` idempotente.
- **`test_permissions.py`** — Fase 6.3: matriz de permissões por perfil,
  bloqueio backend com 403, rotas públicas preservadas, usuário sem login
  redirecionado, menus/botões escondidos por `can()`, escopo por propriedade
  preservado e garantia de que ação sem permissão não cria registro.
- **`test_csrf.py`** — Fase 6.4: CSRF desativado por padrão no `TestingConfig`,
  inicialização do `CSRFProtect`, token nos formulários POST, POST sem token
  retornando 400, POST com token válido funcionando, Upload multipart protegido,
  rotas GET sem token, mensagem amigável de erro e convivência com permissões
  403 quando o token é válido.
- **`test_usuarios_painel.py`** — Fase 7.1: painel interno de usuários; exige
  `admin`; cria/edita/inativa usuários; valida dados obrigatórios; preserva
  escopo por propriedade; impede inativar o último admin ativo; testa
  `usuario_propriedade`, compatibilidade com base legada, `seed-users`
  idempotente e convivência com CSRF/permissões.
- **`test_password_reset.py`** — Fase 7.2: recuperação de senha; link "Esqueci
  minha senha"; mensagem genérica (sem enumeração); token criado só para usuário
  ativo, com hash (sem token puro) e expiração; link dev exibido/ocultado por
  configuração; validação/expiração/uso único do token; validações de nova senha;
  login com senha antiga falha e com nova funciona; usuário inativado depois não
  redefine; novo token invalida anteriores; e CSRF nos POSTs.
- **`test_auditoria.py`** — Fase 7.3: auditoria/logs; model/schema; serviço
  (criação de log, truncamento de descrição, resultado inválido → sucesso, falha
  de auditoria não quebra o fluxo, máscara de e-mail); tela `/auditoria/` (login,
  admin 200, técnico/trabalhador 403, link no menu por perfil, filtro); eventos
  de login/logout, recuperação de senha, painel de usuários, permissão negada,
  upload e CRUDs; escopo por propriedade; e ausência de senha/token/CSRF nos logs.
- **`test_exportacoes.py`** — Fase 7.4: exportações CSV/PDF dos cinco relatórios;
  exigência de login e acesso por `relatorios.view`; headers/`Content-Disposition`
  de CSV e PDF; assinatura `%PDF-`; conteúdo escopado pela propriedade (sem dados
  de outra); filtros válidos e inválidos (400 sem gerar arquivo); preservação de
  filtros nos links; auditoria `exportacao.gerada`/`exportacao.falha` sem dados
  sensíveis; e garantia de que exportar não cria dados nem `ProdutoPreco`/
  `ProdutoImagem`.
- **`test_mapa_avancado.py`** — Fase 7.5: edição de polígonos; matriz `mapa.edit`
  (admin/técnico sim, trabalhador não); salvar/limpar polígono (200 admin/técnico,
  403 trabalhador, 404 fora da propriedade, 302 sem login); validação de GeoJSON
  (Polygon/MultiPolygon/Feature aceitos; inválido/fora de faixa/anel curto/payload
  grande/FeatureCollection → 400); persistência/substituição e `atualizado_em`;
  auditoria `mapa.poligono.update/delete/falha` sem GeoJSON nos logs e escopada
  por propriedade; `data-csrf-token`/`data-can-edit` e controles por perfil no
  template; e CSRF nos POSTs via `X-CSRFToken`.
- **`test_dashboard_operacional.py`** — Dashboard Operacional: exige login;
  responde 200 com login; mostra propriedade atual; calcula totais de glebas,
  culturas, financeiro, equipe, colheita, aplicações e uploads; não vaza dados de
  outra propriedade; mostra totais globais do catálogo; exibe estados vazios;
  contém atalhos principais; e não contém termos de venda.
- **`test_mapa_real.py`** — Mapa real simplificado: exige login; `/mapa/` e
  `/mapa/dados` respondem com login; JSON é escopado pela propriedade atual e não
  expõe usuário/e-mail; separa glebas com coordenadas válidas das sem coordenadas
  válidas; ignora GeoJSON inválido sem quebrar; não possui rotas POST; mostra
  estados vazios; e não apresenta recursos avançados como funcionalidade ativa.
- **`test_ia_simulada.py`** — IA Simulada Operacional: exige login; `/ia/`
  responde com login; mostra avisos obrigatórios; POST válido salva
  `IaInteracao`; valida pergunta vazia e limite de 1000 caracteres; vincula
  usuário/propriedade atuais; histórico não vaza entre usuários/propriedades;
  respostas por tema cobrem financeiro, glebas, culturas, colheita, aplicações,
  documentos, catálogo e fallback; e respostas não usam termos proibidos.
- **`test_ia_simulada_service.py`** — Serviço de IA simulada: classifica intenção,
  monta contexto operacional, gera alertas, responde resumo e registra/lista
  interações sem passar pela rota.
- **`test_relatorios_operacionais.py`** — Relatórios HTML (geral, financeiro,
  agrícola, aplicações, uploads): exige login; totais e filtros (período/tipo/
  classe) com 400 em filtro inválido; escopo por propriedade (sem vazamento);
  avisos de não recomendação/validação e de não leitura de uploads; ausência de
  termos de venda/recomendação; relatórios não criam registros.
- **`test_relatorios_service.py`** — Serviço de relatórios: validação de período,
  totais financeiros e erros de tipo/classe inválidos.
- **`test_glebas_culturas_crud.py`** — CRUD de Glebas e Culturas, associação
  cultura↔gleba, escopo por propriedade e exigência de login.
- **`test_equipe_financeiro_crud.py`** — CRUD de Equipe e Financeiro, validações,
  totais financeiros, escopo por propriedade e exigência de login.
- **`test_colheita_crud.py`** — CRUD de Colheita, validação de `cultura_gleba_id`,
  data obrigatória, quantidade opcional com vírgula/ponto e > 0, escopo por
  propriedade, listagem, orientação sem associação e exigência de login.
- **`test_catalogo_consulta.py`** — consulta somente leitura do catálogo: exige
  login; listagens filtram por `classe`; busca e filtros; detalhe por slug e 404;
  ausência de termos de compra; aviso de preço/imagem pendentes; render de campos
  JSON; `produto_preco`/`produto_imagem` seguem vazios.
- **`test_aplicacoes_crud.py`** — CRUD de Aplicações de Insumo: exige login;
  cria/edita/remove aplicação válida; valida `cultura_gleba_id`, produto e data;
  bloqueia produto histórico; impede cultura↔gleba de outra propriedade; aceita
  dose com vírgula/ponto e recusa dose inválida ou não positiva; garante 404 para
  acesso a aplicação de outra propriedade; evita ações de venda; e confirma que
  `ProdutoPreco`/`ProdutoImagem` não são criados.
- **`test_upload_crud.py`** — Upload de Arquivos: exige login; GET `/upload/`
  com login responde 200; upload válido cria registro e arquivo físico em pasta
  temporária; nome salvo usa `secure_filename` e UUID; upload sem arquivo ou com
  extensão proibida retorna 400; extensões permitidas funcionam; nome malicioso
  não sai da pasta de upload; listagem exibe nome, descrição e download; download
  próprio funciona; download/remoção de arquivo de outra propriedade retorna 404;
  remoção apaga registro e arquivo físico; ausência do arquivo físico não quebra
  remoção; caminho salvo não é absoluto; e upload não cria `ProdutoPreco` nem
  `ProdutoImagem`.

> As rotas protegidas e a rota `/` são testadas também em
> `test_placeholder_routes.py` e `test_permissions.py` (redirecionam sem login;
> respondem conforme login e perfil).

Para rodar:

```bash
pytest
```

## Testes do MVP ampliado (Fase 7)

Cada fase do MVP ampliado deverá adicionar seus próprios testes, mantendo toda a
suíte atual passando:

- Painel de usuários (Fase 7.1) — concluído; listagem/criação/edição/inativação por `admin`,
  escopo por propriedade e permissões.
- Recuperação de senha (Fase 7.2) — concluído; token seguro/expirável, hash sem
  token puro, uso único, mensagem genérica e link dev só em local/teste.
- Auditoria/logs (Fase 7.3) — concluído; eventos sensíveis, tela só admin, escopo
  por propriedade, sem senha/token/CSRF, auditoria não quebra o fluxo.
- PDF/exportações (Fase 7.4) — concluído; CSV/PDF em memória, escopo por
  propriedade/permissão, filtros preservados, auditoria, nunca cotação/venda.
- Mapa avançado (Fase 7.5) — concluído; edição/validação de `poligono_geojson`,
  `mapa.edit` (admin/técnico), CSRF, auditoria sem GeoJSON, escopo por propriedade.
- Revisão final do MVP ampliado (Fase 7.6) — concluída; saneamento documental e
  validação da suíte completa sem adicionar funcionalidade nova.

## Evolução pós-MVP

- Testes end-to-end de interface, caso o projeto passe a ter uma camada de
  validação visual/navegador.
- Testes para itens fora do MVP ampliado: IA real/LLM, validação regulatória real,
  preço/imagem real, OCR/leitura automática de uploads e deploy/produção.

## Convenções

- Arquivos de teste nomeados como `test_*.py`.
- Cada módulo do MVP deve ter testes correspondentes antes de ser considerado
  concluído.

---

## Documentos relacionados

- [02 — Requisitos do Sistema](../docs/02-requisitos-do-sistema.md)
- [06.1 — Arquitetura Técnica do MVP](../docs/06-1-arquitetura-tecnica-mvp.md)
- [07 — Roadmap do MVP](../docs/07-roadmap-mvp.md)
- [09 — Roadmap do MVP Ampliado](../docs/09-roadmap-mvp-ampliado.md)
