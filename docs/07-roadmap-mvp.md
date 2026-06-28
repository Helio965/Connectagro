# 07 — Roadmap do MVP

> Roadmap vivo do MVP. A sequência é ajustada conforme cada fase é consolidada
> em branch + Pull Request.

## Etapas concluídas

### Etapa 0 — Organização do repositório ✅

- [x] README profissional.
- [x] Estrutura inicial de pastas (`docs/`, `data/`, `src/`, `tests/`).
- [x] Documentos-base em Markdown.
- [x] `.gitignore` para Python/Flask.

### Etapa 1 — Documentação de produto ✅

- [x] Escopo definitivo.
- [x] Requisitos priorizados.
- [x] Regras de negócio.

### Etapa 2 — Modelagem de dados ✅

- [x] DER oficial.
- [x] Dicionário de dados.

### Etapa 3 — Catálogo de produtos ✅

- [x] Catálogo técnico inicial sem dados inventados.
- [x] Seed técnico em `data/seeds/`.
- [x] Preço/imagem tratados como pendência no MVP.

### Etapa 4 — Fundação Flask ✅

- [x] Application Factory.
- [x] Configuração por ambiente.
- [x] Blueprints.
- [x] Layout base e páginas de erro.
- [x] `/health` público.
- [x] Testes mínimos.

### Etapa 4.1 — Modelos e banco SQLite ✅

- [x] Modelos SQLAlchemy de domínio (15 tabelas).
- [x] Schema validável por `db.create_all()`.

### Etapa 4.2 — Migrations e seed técnico ✅

- [x] Flask-Migrate/Alembic.
- [x] Migration inicial.
- [x] Validação e importação idempotente do seed técnico.
- [x] `produto_preco`/`produto_imagem` vazios no MVP.

### Etapa 5.1 — Autenticação real ✅

- [x] Login/logout com sessão Flask e hash de senha.
- [x] `login_required` nos módulos protegidos.
- [x] Usuário atual nos templates.
- [x] `flask seed-users` com `admin`, `tecnico`, `trabalhador`.
- [x] Testes de autenticação.

### Etapa 5.2 — CRUD de Glebas e Culturas ✅

- [x] Glebas com criar/listar/editar/remover.
- [x] Culturas com criar/listar/editar/remover.
- [x] Associação cultura↔gleba.
- [x] Escopo por propriedade.
- [x] Testes.

### Etapa 5.3 — CRUD de Equipe e Financeiro ✅

- [x] Equipe com CRUD e `ativo`.
- [x] Financeiro com receitas/despesas, valor positivo e data obrigatória.
- [x] Totais financeiros.
- [x] Escopo por propriedade.
- [x] Testes.

### Etapa 5.4 — CRUD de Colheita ✅

- [x] Colheita vinculada a cultura↔gleba.
- [x] Validações de associação, data e quantidade.
- [x] Listagem e orientação sem associação.
- [x] Testes.

### Etapa 5.5 — Consulta do Catálogo ✅

- [x] Defensivos e Fertilizantes somente leitura.
- [x] Busca, filtros e detalhe técnico.
- [x] Avisos de limites do catálogo.
- [x] Testes.

### Etapa 5.6 — Aplicações de Insumo ✅

- [x] CRUD de aplicações como histórico operacional.
- [x] Produto bloqueado/histórico impedido.
- [x] Dose apenas histórica/informativa.
- [x] Sem venda, carrinho, cotação, preço ou imagem.
- [x] Testes.

### Etapa 5.7 — Upload de Arquivos ✅

- [x] Envio, listagem, download e remoção.
- [x] `secure_filename`, UUID e allowlist de extensões.
- [x] Upload fora de `static`.
- [x] Escopo por propriedade.
- [x] Testes.

### Etapa 5.8 — Dashboard Operacional ✅

- [x] Dashboard em `/`.
- [x] Agregações somente leitura.
- [x] Atalhos e estados vazios.
- [x] Escopo por propriedade.
- [x] Testes.

### Etapa 5.9 — Mapa real simplificado ✅

- [x] Mapa em `/mapa/`.
- [x] JSON em `/mapa/dados`.
- [x] Coordenadas válidas e GeoJSON simples.
- [x] Somente leitura.
- [x] Testes.

### Fase 6.1 — IA Simulada Operacional ✅

- [x] IA em `/ia/`.
- [x] Respostas por regras locais.
- [x] Histórico em `ia_interacao`.
- [x] Sem LLM/API externa/OCR.
- [x] Testes de rota e serviço.

### Fase 6.2 — Relatórios Operacionais HTML ✅

- [x] Central em `/relatorios/`.
- [x] Relatórios geral, financeiro, agrícola, aplicações e uploads.
- [x] Filtros em relatórios financeiros/aplicações.
- [x] HTML somente leitura, sem PDF/exportação.
- [x] Testes de rota e serviço.

### Fase 6.3 — Permissões finas por perfil ✅

- [x] Utilitário central `src/app/utils/permissions.py`.
- [x] Perfis oficiais: `admin`, `tecnico`, `trabalhador`.
- [x] Matriz de permissões em código, sem migration/model/dependência nova.
- [x] `require_permission(...)` aplicado nas rotas sensíveis.
- [x] Backend retorna **403** para ação sem permissão.
- [x] `can(...)` disponível nos templates.
- [x] Menu, atalhos e botões de ação escondidos conforme permissão.
- [x] Página/handler 403 amigável.
- [x] Escopo por propriedade preservado.
- [x] Testes em `tests/test_permissions.py`.

---

## Etapa 6 — Testes e qualidade

- [x] Fundação, schema/modelos e seed.
- [x] Autenticação.
- [x] CRUDs operacionais.
- [x] Catálogo.
- [x] Upload.
- [x] Dashboard.
- [x] Mapa.
- [x] IA simulada.
- [x] Relatórios.
- [x] Permissões finas por perfil.
- [ ] CSRF/Flask-WTF.
- [ ] Revisão e ajustes finais do MVP.

---

## Próximo passo recomendado

**CSRF/Flask-WTF**, mantendo o escopo restrito: proteger formulários POST sem
criar painel de usuários, APIs externas, PDF/exportação ou permissões por banco.

---

## Documentos relacionados

- [01 — Escopo do Projeto](./01-escopo-do-projeto.md)
- [03 — Regras de Negócio](./03-regras-de-negocio.md)
- [06 — Arquitetura do Sistema](./06-arquitetura-do-sistema.md)
- [06.1 — Arquitetura Técnica do MVP](./06-1-arquitetura-tecnica-mvp.md)
