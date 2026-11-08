# ConnectAgro — Etapa 01: auditoria técnica, funcional e linha de base

Data: **07/11/2026**, fuso `America/Sao_Paulo`. Auditoria de diagnóstico, sem correções funcionais.

**Resultado:** o sistema inicializa e os fluxos válidos examinados funcionam em SQLite e PostgreSQL. A suíte oficial passou integralmente, mas verificações adicionais reproduziram falhas de segurança, validação e integridade que ela não cobre. O funcionamento deve ser considerado **parcialmente validado**, não uma aprovação para produção. O mapa visual ficou bloqueado pela rede deste ambiente.

## A. Identificação e ambiente

### A.1. Código efetivamente analisado

| Item | Evidência |
| --- | --- |
| Checkout | `/workspace/Connectagro` |
| Origem | `github.com/Helio965/Connectagro.git`, conferida pelo remoto `origin` |
| Branch local | `work` |
| Commit local | `92273e2b3a4bdb6db4dc0a3b74b003ec702777d8` |
| Último commit | Merge pull request #50 from Helio965/claude/connectagro-technical-stabilization-f29e83; data registrada pelo Git: 10/07/2026, 18:49:30 -0300 |
| Referência remota | `git ls-remote origin refs/heads/main` retornou o mesmo SHA; não havia uma `main` mais recente na consulta |
| Estado inicial | Nenhum arquivo modificado ou não versionado no checkout; dependências, caches e banco do onboarding eram ignorados pelo Git |
| Estado pretendido ao entregar | Somente este relatório novo; código, testes, modelos, migrations, requisitos e interfaces preservados |

O SHA histórico fornecido coincidiu com a versão remota atual; essa coincidência foi verificada, não presumida. Não foram executados `reset`, `clean`, `pull`, troca de branch, push ou publicação. Não foram encontradas instruções `AGENTS.md` aplicáveis no projeto ou em seus ancestrais.

### A.2. Ambiente e dependências

- Debian GNU/Linux 13 (trixie), Linux x86_64, Python **3.12.14**.
- Ambiente isolado existente: `/workspace/Connectagro/.venv`; não foi necessário instalar ou mudar versões nesta etapa.
- `pip check`: **No broken requirements found**. Nenhum erro de importação, configuração ou dependência na suíte.
- O pip avisou que o cache padrão do usuário não era gravável; isso não impediu a verificação das dependências. Não houve desativação de TLS ou de checksums.
- Não há lockfile nem versão de Python fixada no repositório. Os requisitos abaixo aceitam o ambiente instalado; isso não garante resoluções idênticas em instalações futuras.

| Dependência direta | Exigência em `requirements.txt` | Instalada |
| --- | --- | --- |
| Flask | `>=3.0` | 3.1.3 |
| Flask-SQLAlchemy | `>=3.1` | 3.1.1 |
| Flask-Migrate | `>=4.0` | 4.1.0 |
| Flask-WTF | `>=1.2` | 1.3.0 |
| Flask-Mail | `>=0.9.1` | 0.10.0 |
| python-dotenv | `>=1.0` | 1.2.4 |
| psycopg2-binary | `>=2.9,<3` | 2.9.13 |
| Pillow | `>=10.4,<12` | 11.3.0 |
| ReportLab | `>=4.0,<5` | 4.5.1 |
| pytest | `>=8.0` | 9.2.0 |

Dependências transitivas/ferramentas instaladas: SQLAlchemy 2.1.8; Alembic 1.20.1; Werkzeug 3.1.9; Jinja2 3.1.6; WTForms 3.3.2; itsdangerous 2.2.0; blinker 1.9.0; click 8.5.1; MarkupSafe 3.0.4; Mako 1.4.3; typing_extensions 4.16.0; charset-normalizer 3.5.2; packaging 26.3; pluggy 1.7.0; iniconfig 2.3.1; Pygments 2.21.0; pip 25.0.1.

### A.3. Isolamento e configuração

Antes das migrations, foram verificadas apenas a presença e os nomes das variáveis, sem revelar valores. `DATABASE_URL`, `DIRECT_URL`, `SECRET_KEY`, `FLASK_ENV`, `FLASK_DEBUG`, `MAIL_SERVER`, `MAIL_USERNAME`, `MAIL_PASSWORD` e `UPLOAD_FOLDER` estavam ausentes; `.env` e `.flaskenv` também não existiam.

As verificações da auditoria usaram exclusivamente:

1. SQLite em memória, imposto por `TestingConfig` na suíte oficial.
2. SQLite descartável novo em `/tmp/connectagro-audit/audit.sqlite`, com **as duas URLs** explicitamente direcionadas a esse arquivo antes de migrar; uploads em `/tmp/connectagro-audit/uploads`.
3. PostgreSQL **16.15**, em contêiner oficial descartável `postgres:16-bookworm`, publicado somente em `127.0.0.1` em porta temporária. Credencial aleatória existiu somente em memória/processos; nenhuma credencial real foi utilizada ou escrita neste relatório. Contêiner encerrado e removido automaticamente após a verificação.

Imagem PostgreSQL utilizada: `sha256:5264710be20f409750ac6dc4e5706dcef929c87e241605463f0f9aefa932a8d9`. Docker local 29.9.2 verificado pelo socket explícito `/var/run/docker.sock`, sem contexto remoto.

O servidor HTTP da auditoria usou o entrypoint `src/run.py` via Flask CLI, na porta 5001, com ambiente development, CSRF ativo, chave aleatória de processo, SMTP desativado e sem debugger/reloader. A porta diferente evitou interferir no servidor do onboarding. A simulação de `ProductionConfig` descrita em AUD-001 também apontou somente para o SQLite descartável: **não foi um acesso a produção**.

Configuração relevante: `DATABASE_URL` seleciona a base; `DIRECT_URL` permite migrations por conexão direta PostgreSQL; `SECRET_KEY` assina sessões/CSRF; `UPLOAD_FOLDER` e `MAX_CONTENT_LENGTH` controlam arquivos; `MAIL_*` e `APP_BASE_URL` controlam e-mails; `PASSWORD_RESET_*` e `PASSWORD_INVITE_TOKEN_MINUTES` controlam tokens. O modo local não depende de SMTP, Supabase ou API de IA. Nenhuma dessas credenciais opcionais foi solicitada.

## B. Estrutura e funcionamento

### B.1. Arquitetura e inventário

Foram inventariados 238 arquivos nos diretórios solicitados (`src`, `migrations`, `tests`, `scripts`, `data`, `docs`) e examinados os arquivos de configuração indicados no pedido. A arquitetura existente é coerente: Application Factory em `src/app/__init__.py`, extensões compartilhadas em `extensions.py`, registro central de blueprints, modelos SQLAlchemy, serviços, helpers, templates Jinja e arquivos estáticos. A aplicação registrou **16 blueprints e 70 regras de rota**, contando a rota estática e `/health`.

Não há build frontend obrigatório ou dependências Node declaradas para executar o produto. HTML/CSS/JS são servidos pelo Flask; apenas o mapa depende de recursos externos Leaflet/Leaflet.draw e tiles.

Na tabela abaixo, caminhos sem prefixo partem de `src/app/`; nomes de testes partem de `tests/`. “Verificado” se restringe aos cenários descritos, não implica cobertura de todos os estados possíveis.

| Módulo/finalidade | Arquivos e dependências principais | Implementação, testes existentes e resultado |
| --- | --- | --- |
| Inicialização/configuração | `__init__.py`, `config.py`, `extensions.py`, `../run.py`; Flask, dotenv, SQLAlchemy, Migrate, CSRF, Mail | Factory, handlers e health funcionam; `test_app_factory.py`, `test_config_database.py`, `test_placeholder_routes.py`. Ressalva de produção em AUD-001. |
| Autenticação e recuperação | `blueprints/auth/routes.py`, `utils/auth.py`, `services/password_reset_service.py`, `services/email_service.py`, `templates/auth`, `templates/emails`; Werkzeug, itsdangerous/Flask, Flask-Mail | Login, rejeição de credenciais, cookie, logout e reset por token exercitados; `test_auth.py`, `test_password_reset.py`, `test_csrf.py`. **Parcial:** AUD-002, AUD-007 e AUD-011. Envio SMTP real não verificado. |
| Usuários, convites e permissões | `blueprints/usuarios/routes.py`, `utils/permissions.py`, `models/usuario.py`, `models/usuario_propriedade.py`, `templates/usuarios` | Criação por convite, edição, inativação e vínculos; gerente é `tecnico`, com restrição aos trabalhadores. `test_usuarios_painel.py`, `test_convite_usuarios.py`, `test_permissions.py`. Fluxos válidos funcionam; autorização de sessões antigas falha (AUD-002), logs AUD-010. |
| Propriedade de contexto | `utils/contexto.py`, `models/propriedade.py`, `models/usuario_propriedade.py`; ORM e sessão | Resolve primeiro vínculo ativo e mantém compatibilidade com proprietário legado; cria contexto padrão. Exercitado nos testes de escopo/usuários e nas integrações. **Não existe CRUD dedicado do modelo Propriedade:** não confundir com o CRUD de Gleba rotulado “Propriedades” na UI. |
| Glebas/áreas | `blueprints/glebas/routes.py`, `models/gleba.py`, `templates/glebas`; propriedade e permissões | Cadastro/edição/remoção e bloqueio de exclusão com histórico; `test_glebas_culturas_crud.py`, `test_integridade_exclusao.py`. Persistência e isolamento verificados. Validação não finita compartilha AUD-003. |
| Culturas/associações | `blueprints/culturas/routes.py`, `models/cultura.py`, `templates/culturas`; Gleba, CulturaGleba | CRUD, estados, associação própria e proteção de históricos; mesmos testes de glebas/integridade. Fluxo válido verificado; datas sem validação de calendário (AUD-004). |
| Equipe operacional | `blueprints/equipe/routes.py`, `models/equipe.py`, `templates/equipe` | Cadastro distinto de contas de acesso; CRUD e status. `test_equipe_financeiro_crud.py`, `test_permissions.py`; criação/listagem e suíte funcionam. |
| Colheitas | `blueprints/colheita/routes.py`, `models/colheita.py`, `templates/colheita`; CulturaGleba | CRUD e soma por unidade; `test_colheita_crud.py`. Persistência válida verificada nos dois SGBDs; ressalvas AUD-003/004 e escopo defensivo C-04. |
| Aplicações de insumos | `blueprints/aplicacoes/routes.py`, `models/aplicacao.py`, `templates/aplicacoes`; CulturaGleba, ProdutoBase | Histórico operacional, produto elegível e validação de associação; `test_aplicacoes_crud.py`. Fluxos válidos funcionam nos dois SGBDs; ressalvas AUD-003/004. Não recomenda produto nem dose agronômica. |
| Catálogo de defensivos/fertilizantes | `blueprints/defensivos`, `blueprints/fertilizantes`, `utils/catalogo.py`, `models/produto.py`, `templates/catalogo`, `static/img/catalogo/produtos`; `services/catalogo_seed.py`, JSON em `data/seeds` | Consulta/busca/categoria/detalhe e importação idempotente. `test_catalogo_seed.py`, `test_catalogo_consulta.py`. 60 produtos, 60 técnicos, 60 imagens; preços vazios. Navegador carregou as 30 imagens da listagem de defensivos, sem imagens quebradas. |
| Financeiro | `blueprints/financeiro/routes.py`, `models/financeiro.py`, `templates/financeiro`; contexto e ORM | CRUD receitas/despesas e totais; `test_equipe_financeiro_crud.py`. Fluxo válido funciona; entradas especiais e datas tornam o módulo **parcial** (AUD-003/004). |
| Dashboard | `blueprints/dashboard/routes.py`, `services/dashboard_service.py`, `templates/dashboard`; modelos operacionais | Indicadores por propriedade e catálogo global; `test_dashboard_operacional.py`. HTTP e navegador funcionam; os totais dependem da integridade das entradas financeiras/operacionais. |
| Relatórios e exportações | `blueprints/relatorios/routes.py`, `services/relatorios_service.py`, `services/exportacoes_service.py`, `templates/relatorios`, `utils/formatters.py`; csv stdlib e ReportLab | Cinco relatórios HTML e dez exportações CSV/PDF verificadas em SQLite; PDF também no PostgreSQL. `test_relatorios_operacionais.py`, `test_relatorios_service.py`, `test_exportacoes.py`. Ressalvas de datas e fórmulas em CSV (AUD-004/009). |
| Arquivos | `blueprints/upload/routes.py`, `models/upload.py`, `templates/upload`; filesystem, UUID, secure_filename, ORM | Upload/download, allowlist, escopo, limite de tamanho e remoção; `test_upload_crud.py`, `test_csrf.py`. Integração comprovou gravação física, bytes recuperados, 404 para outra propriedade, 400 para extensão proibida, 413 acima de 16 MiB. Atomicidade FS/SQL permanece candidata C-07. |
| Mapa | `blueprints/mapa/routes.py`, `services/mapa_service.py`, `templates/mapa/index.html`, `static/js/mapa.js`; Gleba, Leaflet 1.9.4, Leaflet.draw 1.0.4, OpenStreetMap | Backend salva/recupera polígonos, valida formato/faixa/fechamento/tamanho e aplica CSRF/permissões; `test_mapa_real.py`, `test_mapa_avancado.py`. Persistência válida comprovada nos dois SGBDs. **Parcial:** payloads AUD-005; interface bloqueada AUD-008; interação C-01 pendente. |
| Assistente interno | `blueprints/ia/routes.py`, `services/ia_simulada_service.py`, `models/ia.py`, `templates/ia`; regras e modelos locais | Respostas, alertas e histórico por usuário/propriedade; `test_ia_simulada.py`, `test_ia_simulada_service.py`. Pergunta sobre financeiro respondeu e persistiu uma interação. Regra específica apresenta AUD-012; não utiliza IA generativa. |
| Auditoria administrativa | `blueprints/auditoria/routes.py`, `services/auditoria_service.py`, `models/log_auditoria.py`, `templates/auditoria` | Eventos, agrupamento, filtros e consulta admin; `test_auditoria.py`, testes de permissões/exportações. Funciona, mas e-mails integrais contradizem a política documentada (AUD-010). |
| Interface compartilhada | `templates/base.html`, `static/css/main.css`, `static/js/main.js`; Jinja e matriz de permissões | Navegação, formulários, flashes e layout; `test_csrf.py`, `test_permissions.py`, `test_revisao_tecnica_final.py`. Login/dashboard/catálogo exercitados no Chromium. Não foi realizada inspeção visual exaustiva de todas as telas e resoluções. |

Arquivos de suporte: `.gitignore` cobre ambiente virtual, `.env`, bases e uploads; `pytest.ini` seleciona apenas `tests/`; `scripts/` contém utilitários administrativos, inspecionados sem executar; `docs/` registra decisões e limites do MVP, mas contém divergências listadas adiante. Não foram identificados imports ociosos comprovados que justifiquem remoção: registros de modelos, rotas e reexports têm efeitos necessários.

### B.2. Banco de dados

As migrations executaram do zero em ambos os bancos, na cadeia linear:

```text
97642b24c238  ->  e3e72eacc334  ->  b4f2c9d8a1e7 (head)
schema inicial    usuários/reset/log    status da gleba; remoção de latitude/longitude
```

Foram criadas **18 tabelas de domínio**, mais `alembic_version`: `usuario`, `propriedade`, `usuario_propriedade`, `equipe_membro`, `cultura`, `gleba`, `cultura_gleba`, `produto_base`, `produto_tecnico`, `produto_preco`, `produto_imagem`, `aplicacao_insumo`, `colheita_registro`, `financeiro_lancamento`, `upload_arquivo`, `ia_interacao`, `senha_reset_token` e `log_auditoria`.

- Todos os modelos possuem chave primária. O schema refletido no SQLite declarou **20 FKs**; aplicação e migração carregaram todos os modelos sem erro.
- Relacionamentos: usuário/propriedade e vínculo N:N; propriedade com glebas, culturas, equipe, lançamentos e arquivos; cultura/gleba N:N; aplicação com produto e associação; colheita com associação; produto com técnicos/preços/imagens; reset com usuário; IA com usuário/contexto.
- Unicidades de e-mail, slug e hash de token estão declaradas. Ausência de unicidades compostas é candidata C-02.
- `flask db check` não detectou novas operações em SQLite nem PostgreSQL. `compare_metadata` no SQLite retornou lista vazia. Isso não representa comparação exaustiva de todos os defaults: o modelo usa defaults Python e a migration da gleba também estabelece default SQL.
- `log_auditoria` não declara FKs para usuário/propriedade; pode ser decisão para preservar histórico e não foi considerado defeito automaticamente. Cascatas de produtos/tokens e proteção de históricos operacionais devem ser preservadas.
- PostgreSQL rejeitou INSERT órfão com `IntegrityError`. SQLite aceitou a mesma classe de INSERT em transação revertida, com `PRAGMA foreign_keys = 0` (AUD-006).
- As URLs PostgreSQL são normalizadas para psycopg2 e parâmetros exclusivos de pooler são removidos. `DIRECT_URL` tem tratamento separado em `migrations/env.py`, com `NullPool`. O ensaio PostgreSQL usou URLs iguais locais; conexão direta distinta, PgBouncer/Supabase, autenticação de provedor e TLS remoto **não foram verificados**.

## C. Execuções, resultados e reprodução

### C.1. Suíte oficial

Comandos executados na raiz com o Python da `.venv`:

```bash
.venv/bin/python -m compileall -q src tests
DATABASE_URL=sqlite:////tmp/connectagro-audit/audit.sqlite \
DIRECT_URL=sqlite:////tmp/connectagro-audit/audit.sqlite \
FLASK_SKIP_DOTENV=1 FLASK_ENV=development \
MAIL_ATIVO=false MAIL_SUPPRESS_SEND=true \
.venv/bin/python -m pytest -q --junitxml=/tmp/connectagro-audit/pytest.xml
```

| Resultado desta execução | Quantidade |
| --- | ---: |
| Casos coletados/executados | **521** |
| Aprovados | **521** |
| Reprovados | **0** |
| Erros | **0** |
| Ignorados/skipped | **0** |
| Casos coletados não executados | **0** |

Tempo: **144,23 segundos**. `compileall` encerrou com código 0. Não houve traceback, incompatibilidade de dependência ou erro de inicialização na suíte. Nenhum teste foi alterado, desativado ou criado no repositório. O número histórico de 479 em `docs/11-revisao-tecnica-final.md:104` não foi usado como resultado atual.

`TestingConfig` usa SQLite em memória e desativa CSRF por padrão. Existem testes específicos que reativam CSRF; as integrações adicionais desta auditoria mantiveram CSRF ativo. A suíte usa `db.create_all` nos cenários, portanto seu sucesso sozinho não comprovaria as migrations: o upgrade real separado supriu essa lacuna.

### C.2. Migrations e carga descartável

Após confirmar que o arquivo temporário ainda não existia e que ambas as URIs resolvidas começavam pelo diretório da auditoria, foram executados, com as variáveis de isolamento acima:

```bash
.venv/bin/python -m flask --app src/run.py db upgrade
.venv/bin/python -m flask --app src/run.py db current
.venv/bin/python -m flask --app src/run.py db check
.venv/bin/python -m flask --app src/run.py validate-catalog-seed
.venv/bin/python -m flask --app src/run.py import-catalog-seed
.venv/bin/python -m flask --app src/run.py seed-users
.venv/bin/python -m flask --app src/run.py import-catalog-seed
.venv/bin/python -m flask --app src/run.py seed-users
```

Primeira carga: 60 produtos, 60 técnicos, 60 imagens, três usuários demo e uma propriedade demo. Segunda carga: **zero duplicações**; usuários/vínculos preservados; `produto_preco` permaneceu vazio. Mesmos comandos e repetição passaram no PostgreSQL descartável. Não foram usados os scripts de redefinição de dados.

### C.3. Integração adicional, HTTP e navegador

O roteiro temporário `/tmp/connectagro-audit/integration.py`, executado com `.venv/bin/python`, criou usuários sintéticos com senhas aleatórias e duas propriedades no SQLite migrado. Usou `Flask.test_client`, exercitando a aplicação WSGI sem socket. Não injetou sessões para substituir os testes de login: fez login por formulário, cookie e CSRF. Os fluxos válidos verificaram:

- `/health` com JSON `app=ConnectAgro`, `status=ok`; rota privada anônima com 302; credencial inválida com 401; POST sem CSRF com 400.
- Trabalhador bloqueado no financeiro (403), técnico bloqueado na criação financeira (403), acesso a gleba/arquivo de outra propriedade com 404.
- Cadastros persistidos de gleba, cultura vinculada, aplicação, colheita, equipe e receita financeira. Valores com vírgula decimal foram aceitos corretamente.
- Polígono válido salvo com 200 e conteúdo recuperado do banco; tipo Point rejeitado com 400; trabalhador bloqueado na edição com 403; `/mapa/dados` acessível com sessão.
- Upload por trabalhador, conteúdo físico e download idênticos; extensão proibida com 400; corpo acima do limite de 16 MiB com 413.
- Assistente respondeu e persistiu histórico; módulos principais responderam 200; cinco relatórios HTML e dez exportações responderam 200; PDFs começaram por `%PDF-`.
- Cenários adversos reproduziram os achados da seção D. **Essas observações de comportamento incorreto não são testes oficiais aprovados**, nem foram ocultadas no total da suíte.

Na inicialização HTTP foi usado `.venv/bin/python -m flask --app src/run.py run --host 127.0.0.1 --port 5001 --no-debugger --no-reload`, com URIs descartáveis, `FLASK_ENV=development`, `FLASK_DEBUG=0`, chave aleatória exportada somente ao processo e SMTP desativado. O único aviso de startup foi o aviso esperado de servidor de desenvolvimento do Werkzeug.

Playwright com `/usr/bin/chromium` confirmou login real, dashboard com título esperado e catálogo com **30 imagens carregadas, zero quebradas**. No mapa, o HTML respondeu 200, porém `window.L` ficou indefinido e não houve `.leaflet-container`; quatro requisições CSS/JS a `unpkg.com` falharam com `net::ERR_TUNNEL_CONNECTION_FAILED`. Probes HTTPS anteriores também receberam 403 do túnel para `unpkg.com` e `a.tile.openstreetmap.org`. Não foram usados mocks de CDN nem desativada a validação TLS para apresentar o mapa como funcional.

O roteiro `/tmp/connectagro-audit/postgres.py` iniciou o PostgreSQL oficial local com credencial aleatória, executou os comandos da seção C.2, e fez login/CSRF, gleba, cultura, aplicação, colheita, financeiro, salvamento de polígono, dashboard e PDF via `Flask.test_client` (WSGI). Verificou os registros persistidos e a rejeição de FK inválida. Não iniciou servidor HTTP Flask próprio: o ensaio HTTP por socket/navegador acima foi separado e usou SQLite. **Não executou os 521 casos contra PostgreSQL**: a suíte oficial fixa SQLite; a validação PostgreSQL foi representativa e separada. O contêiner foi encerrado com sucesso.

### C.4. Evidências e limites de reprodução

Artefatos auxiliares desta instância: `/tmp/connectagro-audit/pytest.xml`, `integration.py`, `integration.json`, `postgres.py` e `postgres.json`. O JSON de integração contém 18 observações agrupadas, não uma segunda contagem de casos pytest. Os auxiliares não são parte do código entregue e podem desaparecer quando a máquina for descartada; este relatório registra comandos, entradas, estados e respostas necessários para refazer os ensaios. Para repetir o roteiro inteiro, use nova pasta/base descartável, pois ele cria fixtures e não limpa dados.

Não foram verificados: SMTP real/entrega de e-mails, Supabase/PgBouncer/conexão direta distinta, infraestrutura de produção/TLS/reverse proxy, carga e concorrência, todas as resoluções de tela, edição visual do mapa e interpretação de CSV por um aplicativo de planilha. Não foram usados bancos ou credenciais reais. Não foi executado scanner de vulnerabilidades de dependências; compatibilidade e ausência de conflitos não equivalem a ausência de CVEs.

## D. Problemas encontrados

Prioridades: **P0** crítico; **P1** alto; **P2** médio/baixo. A classificação é do impacto técnico; condições de exploração e limitações são explícitas. Nenhuma correção abaixo foi aplicada.

### AUD-001 — P0 condicional: produção aceita chave de sessão conhecida no fonte

- **Local:** `src/app/config.py:109` e `:184`; confiança no cookie em `src/app/utils/auth.py:41` e `src/app/utils/permissions.py:129`.
- **Evidência:** subprocesso local sem `SECRET_KEY`, com `create_app('production')` e SQLite descartável, iniciou normalmente. O fallback literal do fonte foi usado somente em memória para assinar uma sessão admin; `/auditoria/` retornou **200 sem login**. Chave e cookie não foram publicados.
- **Causa/impacto:** modo de produção herda uma chave padrão previsível. Uma implantação nessa condição permite falsificar a identidade/perfil assinados. **Não foi constatada uma implantação real vulnerável**, nem o ensaio acessou produção. Com chave forte configurada, esse ensaio não demonstra quebra criptográfica da sessão.
- **Correção recomendada:** falhar na inicialização de produção se a chave estiver ausente, vazia ou for o fallback conhecido; exigir configuração forte e testar esse contrato antes de implantar.

### AUD-002 — P1 confirmado: sessões mantêm acesso após rebaixamento, inativação e reset

- **Local:** `src/app/utils/auth.py:27`, `:41`, `:58`; `src/app/utils/permissions.py:116`; `src/app/blueprints/usuarios/routes.py:210`, `:561`; `src/app/services/password_reset_service.py:158`.
- **Reprodução:** cliente A entrou como técnico; admin B editou A para trabalhador pelo endpoint real, com CSRF. A ainda recebeu **200** em `/glebas/nova` e criou uma gleba (**302 e persistência**); login novo de A recebeu **403** nessa tela. Outro cliente inativado continuou recebendo **200** no dashboard. Após redefinir a senha por token válido, a sessão admin anterior continuou recebendo **200**.
- **Causa/impacto:** autorização usa o perfil copiado para a sessão; a autenticação só verifica a presença de `user_id`. Não há revalidação global de usuário ativo/perfil ou versão de sessão. Alterar o banco não revoga cookies já emitidos. O fallback de contexto ainda pode criar nova propriedade para usuário sem vínculo ativo; se for proprietário legado, pode reativar vínculo (leitura de `utils/contexto.py:13`, `:34`).
- **Correção recomendada:** revalidar usuário e vínculo em cada request, derivar permissões do perfil atual e introduzir mecanismo de revogação/versionamento em alterações de senha, status e perfil. Cobrir os fluxos com dois clientes independentes, preservando a arquitetura Flask.

### AUD-003 — P1 confirmado: números não finitos entram na validação operacional

- **Local:** `src/app/utils/contexto.py:65`; `src/app/blueprints/financeiro/routes.py:29`, `:34`, `:73`; validadores equivalentes em `glebas/routes.py:48`, `colheita/routes.py:66`, `aplicacoes/routes.py:111`.
- **Reprodução:** POST financeiro autenticado com CSRF, tipo receita e data válida: `valor=inf` retornou **302** e persistiu infinito; `valor=nan` retornou **500**. Nenhuma informação de uma base real foi envolvida.
- **Causa:** `float` aceita esses valores e `<= 0` não os rejeita. Um ensaio complementar com propagação de exceções confirmou `IntegrityError`, causa SQLite `NOT NULL constraint failed: financeiro_lancamento.valor`, ao persistir NaN. Infinito pode contaminar somas e relatórios. Os demais validadores compartilham o risco pelo código; o 500 foi reproduzido especificamente no financeiro/SQLite.
- **Correção recomendada:** rejeitar números não finitos no backend antes de persistir, com resposta de validação 400. Avaliar precisão monetária separadamente; não é necessário remodelar o sistema nesta etapa.

### AUD-004 — P1 confirmado: datas inválidas são persistidas

- **Local:** `src/app/blueprints/financeiro/routes.py:30`, `:36`; `src/app/services/relatorios_service.py:38`; campos equivalentes em `culturas/routes.py:105`, `colheita/routes.py:55` e `aplicacoes/routes.py:87`.
- **Reprodução:** POST financeiro com valor positivo finito e `data=nao-e-data` retornou **302**; o texto foi recuperado no banco.
- **Causa/impacto:** validação exige apenas texto não vazio; filtros e ordenação comparam strings. O controle HTML `type=date` não protege um POST direto, e datas inválidas deixam de representar ordem/calendário corretos.
- **Correção recomendada:** validar ISO e calendário no servidor, e intervalos quando aplicável, retornando 400. Outros campos equivalentes foram identificados estaticamente, sem afirmar que cada rota foi submetida ao mesmo payload.

### AUD-005 — P1 confirmado: GeoJSON malformado provoca exceção não tratada

- **Local:** `src/app/services/mapa_service.py:38`, `:114`; chamada em `src/app/blueprints/mapa/routes.py:106`.
- **Reprodução:** com login e CSRF válidos, POST de `{"type":[]}` retornou **500**; Polygon contendo coordenada inteira `10**1000` também retornou **500**. Serviço direto lançou, respectivamente, `TypeError: unhashable type: 'list'` e `OverflowError: int too large to convert to float`.
- **Impacto:** entradas inválidas autenticadas escapam do contrato de resposta 400; produzem erro de servidor em vez de mensagem de validação. Isso não é evidência de execução de código ou perda de polígonos.
- **Correção recomendada:** validar o tipo primitivo antes da associação em sets e limitar/rejeitar coordenadas antes da conversão numérica. Preservar as verificações existentes de faixa, finitude, fechamento e tamanho.

### AUD-006 — P1 confirmado: SQLite declara FKs, mas não as aplica

- **Local:** inicialização em `src/app/extensions.py:13`; modelos com `db.ForeignKey`; nenhuma ativação por conexão encontrada em `src`/`migrations`.
- **Reprodução:** engine real do app no banco migrado retornou `PRAGMA foreign_keys = 0`. Um INSERT de Gleba com propriedade inexistente foi aceito em transação explicitamente revertida. O PostgreSQL descartável rejeitou o equivalente com `IntegrityError`.
- **Impacto:** a integridade declarada não é garantida pelo SGBD usado em desenvolvimento/testes, ocultando divergências e permitindo órfãos em escritas inconsistentes. Não foi demonstrada uma rota HTTP que crie esse órfão; o ensaio foi deliberadamente no nível SQL.
- **Correção recomendada:** ativar FKs por conexão SQLite e acrescentar verificações de integridade com migrations reais. Revalidar exclusões e históricos com o enforcement ligado; não apagar registros existentes como atalho.

### AUD-007 — P1 confirmado: e-mail de recuperação pode conter link relativo

- **Local:** `src/app/blueprints/auth/routes.py:148`; `src/app/services/email_service.py:25`, `:33`; promessa de fallback em `src/app/config.py:152`.
- **Reprodução:** envio capturado apenas em memória com `mail.record_messages`, supressão de SMTP e `APP_BASE_URL` vazio: foi produzida uma mensagem cujo botão usava caminho `/auth/redefinir-senha/...`, sem origem absoluta. Token e mensagem não foram impressos.
- **Causa/impacto:** reset chama `url_for` sem `_external=True` e o helper devolve o caminho quando não existe base configurada. O convite implementa fallback absoluto em `usuarios/routes.py:377`; o reset não. O link relativo é inadequado para o cliente de e-mail; com `APP_BASE_URL` válido a condição não ocorre.
- **Correção recomendada:** exigir base pública configurada ou implementar fallback absoluto consistente e validado. Entrega SMTP real continua não verificada.

### AUD-008 — P1 ambiental: mapa visual bloqueado pela política de rede

- **Local da dependência:** `src/app/templates/mapa/index.html:6`, `:88`; `src/app/static/js/mapa.js:26`.
- **Evidência:** Chromium não carregou os quatro arquivos de Leaflet/Leaflet.draw em `unpkg.com`; `window.L` indefinido, nenhum contêiner Leaflet, apesar de HTML 200. A política efetivamente aplicada informa lista customizada vazia. Tiles de OpenStreetMap também não têm permissão confirmada.
- **Impacto/classificação:** impedimento de ambiente, **não uma prova de defeito de código ou persistência**. O backend e o armazenamento de polígonos funcionaram independentemente.
- **Ação necessária:** aplicar as permissões já propostas no onboarding para `unpkg.com` e `*.tile.openstreetmap.org`, preservando os presets existentes; repetir carregamento, desenho, edição, troca de área e recuperação do mapa com conexões novas. Esta auditoria não presumiu que salvar o rascunho anterior aplicou a rede.

### AUD-009 — P1 de exportação: conteúdo de usuário chega ao CSV como fórmula

- **Local:** `src/app/services/exportacoes_service.py:190`; padrão equivalente nas linhas `:145` e `:177`.
- **Reprodução:** trabalhador enviou arquivo temporário com descrição `=1+1`; exportação de uploads realizada pelo admin manteve essa descrição como célula com prefixo de fórmula. Não foi aberta planilha nem executada fórmula.
- **Impacto:** campo controlado por usuário pode ser interpretado como fórmula quando o destinatário abre o CSV em planilha. Quoting CSV não neutraliza essa interpretação. Exfiltração, execução de comandos e comportamento de um cliente específico **não foram demonstrados**.
- **Correção recomendada:** definir e testar neutralização de células perigosas no formato de exportação, incluindo prefixos de fórmula e caracteres iniciais relevantes, sem alterar silenciosamente os dados armazenados.

### AUD-010 — P2 confirmado: e-mails integrais em descrições de auditoria

- **Local:** `src/app/blueprints/usuarios/routes.py:361`, `:363`, `:515`; `src/app/services/auditoria_service.py:85`.
- **Evidência:** criação de usuário sintético pelo painel gerou descrição persistida contendo o endereço completo; confirmação registrada apenas como booleano. Cadastro e troca de e-mail concatenam os endereços, enquanto o serviço apenas trunca a descrição.
- **Impacto:** retenção de dado pessoal desnecessário e contradição com a promessa de mascaramento do README. Não foi alegada exposição pública do painel admin.
- **Correção recomendada:** mascarar descrições de forma consistente e manter IDs para rastreio; não modificar logs preexistentes durante esta etapa.

### AUD-011 — P2 confirmado: logout altera estado por GET

- **Local:** `src/app/blueprints/auth/routes.py:103`.
- **Evidência:** GET `/auth/logout` encerrou a sessão local com 302, e a página privada seguinte redirecionou ao login. Esse método não recebe a proteção CSRF aplicada aos POSTs.
- **Impacto:** uma navegação externa pode induzir encerramento da sessão; não demonstra tomada de conta. Também não resolve a necessidade de revogar cookies anteriores descrita em AUD-002.
- **Correção recomendada:** logout por POST com CSRF e adaptação do controle de navegação na etapa de correção.

### AUD-012 — P2 confirmado: regra específica do assistente é sombreada

- **Local:** `src/app/services/ia_simulada_service.py:37`, `:38`, `:78`.
- **Evidência:** `classificar_intencao_simples('safra colhida')` retornou `culturas`, embora essa expressão esteja cadastrada para `colheita`.
- **Causa/impacto:** a palavra genérica `safra` é verificada antes da frase específica. O assistente responde, mas pode escolher o assunto errado.
- **Correção recomendada:** priorizar correspondências específicas e cobrir esse caso; preservar o assistente por regras, sem introduzir IA generativa.

### AUD-013 — P2 confirmado: documentação e comentários não refletem o código atual

- **Locais:** `README.md:262`; `docs/04-modelagem-banco-der.md:116`; `docs/05-dicionario-de-dados.md:197`; `src/app/blueprints/relatorios/routes.py:3`; `src/app/blueprints/usuarios/routes.py:1`; `src/app/services/catalogo_seed.py:120`.
- **Evidências:** documentação ainda referencia latitude/longitude removidas; cabeçalho dos relatórios diz não haver exportação/PDF; painel é descrito como somente admin embora gerente possa gerir trabalhadores; docstring do importador afirma não importar imagens, contrariando a execução e o código.
- **Impacto:** manutenção e validação acadêmica podem partir de contratos antigos. A nomenclatura “Propriedades” para objetos Gleba mistura área operacional e propriedade de contexto; requer decisão funcional, não criação automática de outro CRUD.
- **Correção recomendada:** atualizar documentos correntes, distinguindo textos históricos do estado atual. Preservar os números históricos de testes quando identificados como histórico.

### D.1. Suspeitas e candidatos que exigem confirmação adicional

Não são apresentados como falhas dinâmicas comprovadas:

| ID / prioridade provisória | Local e observação | Verificação/recomendação posterior |
| --- | --- | --- |
| C-01 / P1 funcional | `static/js/mapa.js:170`: sucesso de save elimina camada de leitura em `poligonoLayers` sem recriá-la; seleção em `:122` e limpeza em `:96` removem o desenho editável ao trocar área | Suspeita forte de desaparecimento visual do polígono salvo até reload, sem perda do banco. Reproduzir com duas áreas após liberar CDN; não foi comprovado visualmente nesta auditoria. |
| C-02 / P2 | `models/usuario_propriedade.py:6`, `models/cultura.py:28`: vínculos sem UNIQUE composto; helpers fazem check-then-insert | Duplicação sob concorrência não testada. Avaliar constraints depois de inspecionar dados existentes; não apagar duplicados na auditoria. |
| C-03 / P2 | `services/dashboard_service.py:48`, `services/ia_simulada_service.py:87`, `blueprints/ia/routes.py:24`: `.all()`, somas em Python e contexto recalculado; catálogo usa relações lazy; faltam índices de escopo/data explícitos | Risco de consultas repetidas/N+1 e escala, sem benchmark ou lentidão comprovada. Medir consultas, volume e planos antes de otimizar. |
| C-04 / P2 defensivo | `blueprints/colheita/routes.py:19`, `:32` filtra propriedade da Cultura sem checar a da Gleba, diferente de aplicações | Associações cruzadas não são criadas pela UI normal. Testar apenas dados legados/importados inconsistentes antes de afirmar vazamento explorável. |
| C-05 / P2 | `services/catalogo_seed.py:135`, `:158`, `:190` combina busca por slug e IDs fixos do seed | Carga vazia e repetição passaram nos dois bancos. Investigar base preexistente com slug em ID diferente, colisões e sequência PostgreSQL antes de futuras inserções automáticas. Não há CRUD de produto no MVP. |
| C-06 / P2 contextual | `config.py:106`: sem flags explícitas Secure/SameSite, prazo/revogação central ou limitação de tentativas | Na simulação production, Secure=False, HttpOnly=True, SameSite=None. Revisar junto com HTTPS/proxy e política de sessões. Rate limiting externo não foi inspecionado; não alegar ataque ocorrido. |
| C-07 / P2 | `blueprints/upload/routes.py:177`, `:224`: filesystem alterado antes do commit SQL; serviço de reset valida/consome token em passos separados | Atomicidade em falhas e corridas de consumo não foi testada por injeção de falhas/concorrência. Planejar testes sem desativar validações existentes. |

### D.2. Código potencialmente obsoleto, redundâncias e scripts

- `src/app/utils/catalogo.py:69`, `status_disponiveis`: não foram encontradas chamadas em `src`/`tests`; candidato a remoção futura após confirmar uso externo. O parâmetro `status_regulatorio` existe no helper, mas as rotas atuais passam busca/categoria. A ausência desse filtro na interface não foi tratada como requisito novo obrigatório.
- `_cg_ids_com_historico` é duplicado em `blueprints/glebas/routes.py:22` e `blueprints/culturas/routes.py:26`. Há helpers de joins semelhantes entre dashboard e assistente; formatadores de tamanho também aparecem em `utils/formatters.py:22` e `blueprints/upload/routes.py:88`. Têm uso atual; redundância não é abandono.
- `src/app/services/password_reset_service.py:29` recebe `request` sem utilizá-lo; oportunidade de simplificação posterior, preservada.
- Imports de modelos na factory e imports de rotas nos packages têm finalidade de registro; reexports de `models/__init__.py` também são necessários. Nenhuma remoção foi feita com base apenas em análise de nomes.
- `scripts/update_admin_credentials.py:72` trata a base como arquivo; `scripts/reset_operational_data.py:131` consulta metadados SQLite e inclui `produto_imagem` na lista de exclusões em `:45`. São utilitários específicos de SQLite, não validados para PostgreSQL; foram **somente lidos**. O comportamento destrutivo do reset não foi executado nem recomendado nesta etapa.
- `placeholder-produto.svg`, `ProdutoPreco` e `ProdutoImagem` não são código morto: fallback visual e modelos fazem parte do contrato aprovado; imagens foram efetivamente importadas, e preços vazios são intencionais.
- Não foi encontrada referência ausente que impedisse a inicialização ou os fluxos válidos exercitados. A inspeção não comprova inexistência de referências dinâmicas raras ou de todo endpoint sem uso externo; a falta de chamadas internas de uma rota pública não basta para excluí-la.

## E. Recomendações para as próximas etapas

### E.1. Corrigir primeiro

1. Tratar AUD-001 como condição impeditiva de qualquer implantação em produção sem chave forte; criar teste de falha segura na inicialização.
2. Corrigir AUD-002 com revalidação/revogação de sessões; incluir inativação, rebaixamento, mudança de senha e dois clientes independentes. Essa é a prioridade da próxima etapa de segurança/autenticação/sessões.
3. Rejeitar números, datas e GeoJSON inválidos antes de gravar; cobrir os casos reproduzidos em AUD-003/004/005 sem alterar testes para esconder o comportamento.
4. Ativar integridade referencial SQLite e validar novamente históricos/remoções, mantendo compatibilidade PostgreSQL.
5. Corrigir links de recuperação e exportação CSV; aplicar o mascaramento prometido nos logs e ajustar logout com CSRF.
6. Aplicar as permissões de mapa no ambiente e concluir os testes visuais, incluindo C-01. A alteração de rede é independente das correções de código.

### E.2. Fazer depois, com evidência

Atualizar a documentação corrente e o classificador por regras; avaliar unicidades compostas, índices, consultas repetidas, lockfile e atomicidade de arquivos/tokens. Medir desempenho antes de otimizar. Investigar candidatos sem excluir código por suposição. A adoção de novas restrições de banco exigirá plano próprio, sem limpeza destrutiva automática.

### E.3. Preservar e decidir explicitamente

Preservar factory, blueprints, modelos, migrations históricas, serviços, escopo por propriedade, hashes de senha, tokens aleatórios com hash/expiração/uso único, CSRF, bloqueios de históricos e o catálogo somente de consulta. Manter IA simulada, preço não consolidado/vazio, imagens locais com fontes e ausência de comércio conforme escopo aprovado.

Dependem de decisão funcional/acadêmica: significado e rótulo de Propriedade versus Gleba/Área de Plantio; cardinalidade/regra global de administrador versus administrador por contexto; política de dados financeiros agregados para trabalhadores. O README permite dashboard, relatórios e assistente a esse perfil, apesar de bloquear o CRUD financeiro: isso não foi classificado como falha de autorização contra o escopo atual. Não implementar cadastro público, IA generativa, marketplace ou novo CRUD nesta fase.

## F. Conclusão

**Estado atual: parcialmente validado, com defeitos confirmados e limitações explícitas.** O ConnectAgro inicia, registra os 16 blueprints e passa os **521 testes oficiais**, sem falhas, erros ou skipped. Migrations e fluxos representativos com persistência funcionam em SQLite e PostgreSQL 16.15. Login/dashboard/catálogo também foram comprovados no navegador; o mapa visual não pôde ser validado devido à política de rede.

Testes aprovados não eliminam os riscos reproduzidos: chave de produção previsível se não configurada, sessões não revogadas, validação insuficiente de números/datas/GeoJSON, FKs SQLite desativadas, link relativo de recuperação e células de CSV sem neutralização. Não há conclusão de comprometimento de uma produção existente, nem foram usados seus dados ou credenciais.

**O projeto está preparado para iniciar a próxima etapa de correção de segurança, autenticação e controle de sessões**, usando esta linha de base e os cenários reproduzidos. Isso não significa que esteja liberado para produção. Antes de considerar essas correções concluídas, devem passar os testes atuais, regressões dos achados, migrations com integridade e a validação visual pendente após liberação de rede.

Único arquivo do projeto criado nesta etapa: `docs/auditoria/01-linha-de-base.md`. Nenhum código funcional, teste, modelo, migration, dependência ou credencial foi alterado; nenhum script destrutivo foi executado e nada foi publicado no GitHub.
