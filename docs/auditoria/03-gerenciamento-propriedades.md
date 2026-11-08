# Etapa 03 — gerenciamento de propriedades

Data de referência: 07/11/2026 (America/Sao_Paulo; parte das execuções terminou em 08/11 UTC).

## 1. Estado anterior e escopo

Repositório `/workspace/Connectagro`, branch `work`, HEAD `92273e2b3a4bdb6db4dc0a3b74b003ec702777d8`. As alterações locais da Etapa 02 já estavam presentes e foram preservadas. Os relatórios `01-linha-de-base.md` e `02-seguranca-autenticacao.md` foram lidos integralmente e mantidos. Não houve commit, push, merge, reset ou alteração do banco real/de desenvolvimento existente.

Antes das mudanças, os testes de autenticação, sessão, produção, CSRF, permissões, recuperação/convite e painel de usuários passaram: **178 aprovados**, zero falhas, em 46,83 s. Evidência desta execução: `/tmp/connectagro-stage3/baseline.xml`.

O projeto já possuía `Propriedade`, responsável legado em `usuario_id`, `UsuarioPropriedade`, `Gleba` e filtros territoriais em vários módulos. O resolvedor escolhia o primeiro vínculo, recorria ao responsável legado, reativava vínculo inativo e criava “Minha propriedade” ao consultar contexto sem propriedade. Login/auditoria também podiam alcançar esse caminho. Não havia seleção explícita de ambiente nem constraint única no par usuário/propriedade.

Arquitetura Flask, SQLAlchemy, Alembic, modelos agrícolas e tecnologias existentes foram mantidos. A modelagem de Áreas de Plantio independentes e a organização geográfica completa não fazem parte desta etapa.

## 2. Problemas identificados e impactos

| Problema | Impacto | Correção |
| --- | --- | --- |
| Primeiro vínculo e fallback automático | Ambiente imprevisível e troca silenciosa após revogação | Seleção explícita; nenhuma alternativa automática na requisição invalidada |
| Leitura criava propriedade/vínculo ou reativava vínculo | Escritas involuntárias e revogação sem efeito | Consulta sem inserção; reconciliação por migration explícita |
| Ausência de tratamento comum para falta de contexto | Consumidores acessavam `.id` sem propriedade válida | Guarda central antes dos módulos operacionais |
| Duplicatas de vínculos possíveis | Autorização ambígua e risco de corrida | UNIQUE no banco; preflight sem exclusão |
| Colheita validava apenas o lado Cultura | Associação legada cruzada podia expor o outro ambiente | Exigir também a propriedade da Gleba |
| Upload autorizado cujo caminho apontasse para outro ambiente | Download/remoção física fora da propriedade | Verificar prefixo por propriedade e contenção do caminho real |
| Remoção/edição de associação legada cruzada | Possível perda silenciosa de relacionamento antigo | Bloquear com 409, preservando o registro para conciliação |
| Alteração de conta compartilhada | Efeito global em propriedades fora da autoridade do operador | Status local e bloqueio de alteração global fora do escopo |
| Formulário antigo após troca em outra aba | Cadastro de A poderia ser gravado silenciosamente em B | Invalidar CSRF ao trocar ou perder contexto |
| Textos chamavam Gleba de Propriedade | Confusão entre ambiente e unidade agrícola | Rótulos “Área de Plantio”, preservando nomes técnicos |

## 3. Alterações e arquivos

Todos os caminhos abaixo são relativos à raiz absoluta `/workspace/Connectagro/`.

| Arquivos | Alteração |
| --- | --- |
| `src/app/utils/contexto.py` | Consulta, seleção e invalidação separadas; cache limitado à requisição; helper explícito de vínculo sem reativação/commit próprio; invalidação dos formulários antigos |
| `src/app/__init__.py`, `src/app/blueprints/__init__.py` | Registro do blueprint; guarda de contexto; dados do seletor nos templates |
| `src/app/blueprints/propriedades/__init__.py`, `routes.py` | Listagem, detalhe, criação, edição, seleção e bloqueio de remoção |
| `src/app/utils/permissions.py` | View/select para os perfis; create/edit para administrador e gerente |
| `src/app/models/propriedade.py`, `usuario_propriedade.py` | Não reciclar IDs de propriedade no SQLite; UNIQUE do par |
| `migrations/versions/d3b94f5a0c21_unique_vinculos_propriedades.py` | Preflight e reconciliação conservadora do responsável legado |
| `src/app/blueprints/colheita/routes.py`, `culturas/routes.py`, `glebas/routes.py` | Isolamento dos dois lados das associações e bloqueio de remoção inconsistente |
| `src/app/blueprints/upload/routes.py` | Autorização também do caminho físico do arquivo |
| `src/app/blueprints/usuarios/routes.py`, `src/app/templates/usuarios/form.html`, `list.html` | Status do vínculo, administrador por contexto e proteção de conta compartilhada |
| `src/app/services/auditoria_service.py` | Resolver contexto sem selecionar implicitamente; preparar log para transação única de cadastro/edição de propriedade |
| `src/app/templates/propriedades/list.html`, `form.html`, `detail.html`, `sem_contexto.html` | Gestão, seleção, estados vazios e contexto perdido |
| `src/app/templates/base.html`, `src/app/static/css/main.css` | Seletor no menu lateral existente e apresentação responsiva |
| `src/app/templates/glebas/{list,form}.html`, `culturas/{list,form}.html`, `aplicacoes/{list,form}.html`, `colheita/{list,form}.html`, `dashboard/index.html` | Separação textual entre Propriedade e Área de Plantio |
| `src/app/templates/mapa/index.html`, `src/app/static/js/mapa.js`, `src/app/blueprints/mapa/routes.py` | Rótulos da área e entidade dos novos eventos de auditoria |
| `src/app/templates/relatorios/{index,geral,agricola,aplicacoes}.html`, `src/app/services/exportacoes_service.py`, `ia_simulada_service.py` | Rótulos coerentes em relatórios, CSV/PDF e respostas do assistente |
| `docs/03-regras-de-negocio.md` | Decisões aprovadas, contexto por vínculo e retenção bloqueada |
| `tests/test_propriedades.py`, `test_propriedades_migration.py` | Regressões de contexto, isolamento, compartilhamento e migrations reais |
| `tests/factories.py` e fixtures existentes | Dados de teste com propriedade/vínculo explícitos, sem depender de criação automática |

Fixtures adaptadas em `tests/test_aplicacoes_crud.py`, `test_auth.py`, `test_colheita_crud.py`, `test_csrf.py`, `test_dashboard_operacional.py`, `test_equipe_financeiro_crud.py`, `test_glebas_culturas_crud.py`, `test_ia_simulada.py`, `test_integridade_exclusao.py`, `test_mapa_real.py`, `test_permissions.py`, `test_placeholder_routes.py`, `test_relatorios_operacionais.py`, `test_upload_crud.py`, `test_session_security.py` e `test_usuarios_painel.py`. Asserções textuais, inclusive em `test_ia_simulada_service.py`, acompanham a nomenclatura corrigida. Não foi adicionado bypass de autorização/CSRF nem fixture global que conceda acesso automaticamente.

Os arquivos de segurança/autenticação da Etapa 02 que já estavam modificados continuam no diff acumulado, incluindo `.env.example`, `config.py`, `commands.py`, `models/usuario.py`, `utils/auth.py`, rotas de autenticação e testes de segurança. A migration `c2a83e4f9b10` continua predecessora de `d3b94f5a0c21`.

## 4. Seleção e validação do contexto

`session["propriedade_ativa_id"]` contém apenas um ID inteiro positivo dentro da faixa de 64 bits. Ele é uma preferência, não autorização. A cada requisição, o usuário é validado pelo mecanismo da Etapa 02 e a consulta exige propriedade existente e `UsuarioPropriedade.ativo=True` para esse usuário. Não há fallback por `Propriedade.usuario_id` em navegação.

Com uma única opção, a sessão pode selecioná-la automaticamente. Com várias, o usuário escolhe. Sem opções, a interface orienta cadastro autorizado ou solicitação de vínculo, sem INSERT. Se a opção anterior deixou de existir ou foi revogada, a seleção é limpa; a mesma requisição nunca passa a executar em outra propriedade. GET/HEAD operacionais HTML direcionam à seleção; JSON e mutações sem contexto retornam 409. CSRF inválido pode produzir 400 antes da guarda de contexto. IDs inválidos/inacessíveis de seleção retornam 404; JSON que não seja objeto retorna 400.

A seleção usa POST protegido por CSRF. Uma troca efetiva remove o token CSRF da sessão e do cache da requisição, obrigando formulários abertos no contexto antigo a serem recarregados. Isso também se aplica à invalidação por revogação. Escolher novamente a mesma propriedade mantém os formulários válidos. Não há redirecionamento externo por parâmetro `next`.

O cache usa a identidade do objeto da requisição e do usuário; não persiste entre requisições, mesmo sob `app_context` prolongado. O seletor consulta somente vínculos ativos. Login/logout mantêm a limpeza e revogação de sessão da Etapa 02.

## 5. Permissões e contas compartilhadas

As duas decisões foram obtidas diretamente do usuário nesta etapa: **“Administrador e gerente criam e editam”** Propriedade e **“Inativar somente o vínculo local”** quando a conta possui vínculos em outros ambientes. O perfil interno de Gerente permanece `tecnico`.

| Operação | Regra aplicada |
| --- | --- |
| Listar/ver/selecionar | Administrador, gerente e trabalhador, somente com vínculo ativo |
| Criar Propriedade | Administrador e gerente; responsável é o próprio ator autenticado |
| Editar Propriedade | Administrador e gerente, exigindo vínculo ativo; campos permitidos não incluem transferência de responsável |
| Remover/desativar Propriedade | Bloqueado para preservar dependências e histórico até definir retenção |
| Desativar conta compartilhada | Apenas vínculo na propriedade atual; outros vínculos e `Usuario.ativo` preservados |
| Editar nome/e-mail/perfil/senha ou reenviar convite de conta fora do escopo | Bloqueado; formulário só permite status local |

Administrador não ganhou acesso global. As permissões anteriores sobre perfis editáveis continuam aplicadas. Alterações globais de outra conta compartilhada exigem que todas as propriedades dessa conta estejam no acesso do operador; editar a própria identidade mantém as restrições existentes. Para uma conta com um único vínculo, preservou-se o comportamento anterior do status global e local em conjunto. Uma conta globalmente inativa não autentica e não é reativada globalmente ao ativar apenas seu vínculo compartilhado.

A classificação de conta compartilhada considera também vínculos inativos, preservando o alcance global de uma identidade mesmo durante uma suspensão local. A contagem/proteção de administrador ativo usa o contexto atual e o vínculo ativo. Nome de perfil, cookie e responsável legado não substituem o vínculo. Não foram introduzidas permissões por propriedade ou por Área de Plantio nesta etapa.

## 6. Isolamento por módulo

A guarda central cobre dashboard, culturas, glebas, aplicações, colheita, equipe, financeiro, upload, mapa, IA, relatórios, usuários e auditoria. Autenticação, health, estáticos, catálogos globais e gestão/seleção de propriedades podem ser usados sem contexto operacional escolhido, respeitando suas próprias permissões.

Listagens e lookups individuais mantêm os filtros por propriedade, inclusive IDs recebidos em URL/formulário. Aplicações, colheita, relatórios e assistente exigem que Cultura e Gleba da associação pertençam ao contexto. O teste com vínculo legado cruzado confirma ausência de vazamento e preservação do relacionamento ao bloquear remoção/edição inconsistente.

Uploads exigem registro no contexto, primeiro componente `propriedade_<id>` e `realpath` contido na subpasta autorizada e na base de uploads. Caminhos de outra propriedade, travessia que escape da subpasta autorizada e escape por symlink não passam. A própria pasta da propriedade não pode ser um symlink para outra subpasta, inclusive irmã na mesma base. Cadastro, download e remoção verificam o caminho físico.

Marcadores exclusivos de dados A/B foram usados nos testes de troca e isolamento; C representa uma propriedade inacessível ao ator. As suítes cobrem dashboard, financeiro, culturas, aplicações, colheita, arquivos, relatórios/exportações, mapa, IA e auditoria. A troca altera o conjunto lido sem modificar os registros anteriores. Consultar opções do seletor pode exibir o nome das outras propriedades autorizadas, sem exibir seus registros operacionais.

Novos eventos de seleção, cadastro e edição identificam ator e contexto. Cadastro e edição de Propriedade adicionam o log à mesma transação dos dados; falha SQL do log desfaz a operação inteira e retorna 409. Os atalhos independentes de auditoria dos demais fluxos mantêm seu comportamento anterior. Auditoria sem contexto não cria propriedade nem vínculo. Eventos antigos não foram reescritos. Eventos de Gleba agora usam entidade técnica `gleba`, com descrição “Área de Plantio”.

## 7. Banco de dados e compatibilidade legada

Nova revisão: `d3b94f5a0c21`, após `c2a83e4f9b10`.

1. Verifica todos os pares duplicados, incluindo ativos/inativos, antes de qualquer escrita ou DDL. Havendo duplicata, aborta com orientação de conciliação manual; não escolhe um vínculo nem remove registros.
2. Verifica referências órfãs de responsáveis e vínculos; aborta sem inventar usuário ou propriedade.
3. Habilita AUTOINCREMENT de `propriedade` no SQLite, copiando os registros com mesmos IDs e responsáveis pelo mecanismo batch Alembic. Isso evita reutilizar ID apagado e tornar uma seleção/vínculo antigo aplicável a um novo registro.
4. Cria `uq_usuario_propriedade_usuario_propriedade` sobre os dois IDs. A constraint resolve também inserções concorrentes no banco.
5. Insere apenas o vínculo ausente do responsável legado. Usa o status global do usuário como status inicial; respeita qualquer vínculo já existente, mesmo inativo. Não altera responsável, histórico ou vínculo de terceiros, nem fabrica `criado_por_id`.

Repetir `upgrade` não duplica dados. `downgrade` remove a constraint, mantendo vínculos reconciliados e proteção dos IDs; não é uma limpeza de dados. Migrations novas não foram aplicadas ao banco real nem ao SQLite de desenvolvimento existente.

SQLite: upgrade real desde a revisão anterior; nomes como “Minha propriedade”, responsáveis, IDs, vínculo inativo e vínculo de terceiros preservados; snapshot exato de gleba/polígono, cultura, associação, financeiro, caminho de upload e auditoria permanece igual; `PRAGMA foreign_key_check` sem violações. Reconciliação de dois pares ausentes; `compare_metadata` sem divergência; três combinações de duplicatas e responsável órfão abortam preservando as linhas e a revisão.

PostgreSQL **16.15**, imagem oficial `postgres:16-bookworm`, container e bases exclusivamente descartáveis: mesmas verificações de preservação; constraint presente e efetiva; repetição e downgrade/upgrade sem duplicação; `flask db check` sem divergência. Três bases com pares ativo/ativo, ativo/inativo e inativo/inativo abortaram com snapshots de dados intactos, revisão ainda em c2 e sem constraint parcialmente aplicada. O container foi removido ao final. Não se usou `create_all()` como substituto de migration nessas validações.

Antes de uma implantação futura: fazer backup verificável, executar a migration primeiro em cópia restaurada, conciliar manualmente duplicatas/órfãos se o preflight bloquear, aplicar em janela controlada e verificar revisão e integridade. O relatório não autoriza aplicação em base real.

## 8. Interface

O menu lateral existente foi preservado. O bloco “Propriedade ativa” contém seletor, POST “Trocar” com CSRF e link de gestão. A lista exibe somente propriedades autorizadas, identifica a atual e oferece cadastro aos dois perfis aprovados. Há orientação para zero vínculos e resposta segura para perda de contexto.

Gleba continua sendo a tabela/modelo técnico e é apresentada como “Área de Plantio”. Não foram renomeadas tabelas, rotas, chaves JSON nem associações. O mapa continua mostrando o nome da propriedade atual; o seletor interno do mapa escolhe uma Área de Plantio.

## 9. Testes e evidências

Comandos executados a partir de `/workspace/Connectagro`, com Python 3.12.14 e dependências instaladas na `.venv`:

```bash
.venv/bin/python -m compileall -q src tests
.venv/bin/python -m pytest -q --junitxml=/tmp/connectagro-stage3/full-final.xml
.venv/bin/python -m pip check
git diff --check
```

A compilação, `pip check` e `git diff --check` passaram. A suíte final executou **648 testes: 648 aprovados, zero reprovados, zero erros e zero ignorados**, em **181,05 s**, com código de saída 0. Os oito módulos de segurança/autenticação do baseline somam agora **179 aprovados**, incluindo a regressão adicional de leitura legada sem criação automática. Houve 26 avisos de depreciação de `get_engine()`, sem impedir as migrations.

A rodada intermediária de integração teve 632 aprovados e 11 falhas por expectativas textuais antigas; foram ajustadas para Área de Plantio, mantendo as assertivas de segurança e dados. Outra execução foi interrompida deliberadamente para incluir a atomicidade de auditoria antes da rodada final. Não houve falha remanescente nessa rodada final.

Validações específicas concluídas:

| Verificação | Resultado efetivo | Evidência |
| --- | --- | --- |
| Suíte completa final | **648 aprovados; zero falhas/erros/ignorados; 181,05 s** | `/tmp/connectagro-stage3/full-final.xml`, `full-final.log` |
| Segurança anterior, antes de alterar a Etapa 03 | 178 aprovados, zero falhas | `/tmp/connectagro-stage3/baseline.xml` |
| Propriedades e migration antes dos últimos reforços | 52 aprovados, zero falhas | `/tmp/connectagro-stage3/propriedades-final.xml` |
| Upload, dashboard, IA, mapas, permissões, relatórios e propriedades após correção dos rótulos/symlinks | 186 aprovados, zero falhas | `/tmp/connectagro-stage3/regression.xml` |
| Migration SQLite com snapshot do histórico e referências | 5 aprovados, zero falhas | `/tmp/connectagro-stage3/migration-final.xml` |
| Propriedades, atomicidade, auditoria e migrations no código final | 59 aprovados, zero falhas | `/tmp/connectagro-stage3/atomic.xml` |
| PostgreSQL 16.15 descartável | Preservação, preflight, UNIQUE, rollback/downgrade, isolamento e CSRF aprovados | `/tmp/connectagro-stage3/postgres.json`, `postgres.log`, `postgres.py` |
| Chromium/Playwright real, sem mocks | 62 assertivas aprovadas, zero falhas e zero erros JavaScript registrados | `/tmp/stage3-ui-summary.md`, `/tmp/connectagro-stage3-ui-0xkpm_st/result.json` |

No navegador foram usados desktop 1440×900, tablet 820×1180 e celular 390×844. Seletor, sidebar e dashboard sem overflow horizontal; seletor dentro do viewport com menu aberto. Login e troca reais com CSRF, marcadores financeiros isolados, propriedade C ausente/404, criação explícita por administrador e gerente, trabalhador com uma opção e trabalhador sem vínculo foram verificados. As duas criações explícitas aumentaram o banco de 3 para 5 propriedades e de 6 para 8 vínculos; as demais navegações não inseriram contexto. Servidor encerrado ao final. A revisão posterior da atomicidade foi validada pelos testes HTTP/banco de sucesso e rollback, sem alteração visual.

Screenshots em `/tmp/connectagro-stage3-ui-0xkpm_st/`: `desktop-selector.png`, `tablet-selector.png`, `mobile-selector.png`, `mobile-no-binding.png`. Drivers: `/tmp/stage3-ui-driver.py` e `/tmp/stage3-ui.js`. Somente dados sintéticos, bancos/arquivos descartáveis e conexões locais foram usados. Nenhuma migração real foi aplicada a uma base do usuário.

Correspondência dos cenários solicitados:

| Cenários | Cobertura |
| --- | --- |
| T01 | `test_uma_propriedade_e_selecao_automatica`; navegador com um vínculo |
| T02–T04 | `test_varias_exigem_selecao_e_troca_nao_muda_dados`; troca A/B no navegador e PostgreSQL |
| T05 | `test_sem_propriedade_nao_cria_registros_ao_ler`; regressão de login legado em `test_auth.py`; persistência UI |
| T06, T07, T10 | `test_admin_nao_tem_acesso_global_nem_id_inexistente`; IDs malformados e JSON não objeto |
| T08, T09, T19 | Revogação de vínculo, usuário inativo e propriedade removida invalidam seleção; POST não migra para B |
| T11–T14 | `test_dados_operacionais_isolados_apos_troca`; suítes de relatório/exportação, auditoria e segurança existentes |
| T15 | Cadastro por administrador/gerente, responsável derivado da sessão, vínculo único, histórico anterior intacto; UI real |
| T16 | `test_remocao_bloqueada_e_vinculo_unico`; testes de integridade/exclusão anteriores |
| T17 | UNIQUE via ORM e migration; três tipos de duplicata abortam em SQLite/PostgreSQL sem exclusão |
| T18 | `test_trabalhador_nao_cria_edita_nem_perde_perfil_ao_trocar`; matriz existente de permissões |
| T20, T21 | Estados zero/um/vários e troca protegida por CSRF; navegador nas três resoluções |
| T22 | Suíte completa inclui segurança da Etapa 02; baseline anterior de 178 aprovados |
| T23, T24 | IDs estrangeiros, associação cruzada, exportação/download; caminhos cruzados, travessia e symlinks |
| T25 | Migrations reais SQLite e PostgreSQL preservam registros legados e vínculos; aplicação usa acesso reconciliado |

Regressões adicionais: status local preserva acesso da conta compartilhada em B; alterar identidade/senha/perfil e reenviar convite fora do escopo retorna 403; proprietário não muda por formulário forjado; formulário de A enviado após selecionar B retorna 400 e não grava; falha simulada de auditoria desfaz propriedade/vínculo ou edição, sem log parcial.

## 10. Pendências e limites

- Definir política de desativação/retenção de Propriedade; remoção segue bloqueada, inclusive para propriedade vazia.
- Refinar permissões de administrador, gerente e trabalhador por contexto na próxima etapa, preservando as duas decisões já aprovadas.
- Não foi adicionado fluxo de concessão de acesso de uma conta já existente a outra propriedade. Permanecem criação autorizada de usuários/unidades, vínculos existentes e reativação local; um novo fluxo deve seguir a política de permissões a ser refinada.
- Modelagem territorial completa, áreas independentes e delimitação geográfica da propriedade ficam para a etapa específica de mapas.
- Inconsistências legadas detectadas pelo preflight exigem conciliação humana em cópia/implantação; não há limpeza automática.
- O mapa visual depende de `unpkg.com` e `*.tile.openstreetmap.org`; os domínios constam no rascunho de configuração, mas não na política aplicada observada. Esta etapa não declara validada a edição visual de polígonos/tiles. O backend de mapa e seu isolamento são testados.
- Permanecem os achados fora deste escopo registrados na Etapa 01: validação de valores não finitos e datas em outros CRUDs, GeoJSON malformado, FK do SQLite, prefixos de fórmula em CSV e regra sombreada da IA simulada. Não foram ocultados nem tratados como regressões desta etapa.
- Há aviso de depreciação de `get_engine()` em `migrations/env.py`; não impediu as migrations. SMTP real e Supabase/serviços externos não foram validados.

## 11. Compatibilidade e situação de entrega

Preservados: Flask/SQLAlchemy/Alembic, dados e responsáveis, relações agrícolas, catálogos, rotas e exports existentes, hashes, recuperação/convite de senha, CSRF, autenticação com validação no banco e revogação persistente de sessões. O mecanismo de criação demo continua sendo comando explícito, bloqueado em produção, sem voltar para consultas de contexto.

Instalações anteriores precisam aplicar a migration antes de depender de acesso legado por responsável sem vínculo. Propriedades legítimas com nome “Minha propriedade” são preservadas. Vínculos inativos não são reativados nem pelo backfill nem pela navegação.

**Etapa 03 concluída no escopo acordado.** Seleção autorizada, contexto invalidável, isolamento no backend, ausência de criação automática, preservação legada e interface responsiva foram validados. A suíte completa passou, incluindo a segurança da Etapa 02 e os módulos agrícolas. O sistema está preparado para o refinamento das permissões de Administrador, Gerente e Trabalhador, com as pendências específicas da seção 10 registradas.

Git permanece em `work` no mesmo HEAD, com 76 arquivos modificados/novos acumulados das etapas anteriores e desta etapa. Nenhuma alteração foi commitada ou enviada. O inventário absoluto segue abaixo.

O `start_skill` do ambiente foi atualizado e salvo no rascunho, preservando instalação, repositório e domínios já propostos. As instruções refletem head d3, seleção/CSRF e restrição de migrations/testes a bancos adequados. Esse salvamento não executou setup/migrations, não alterou a política de rede em vigor e não publicou o ambiente. Para reutilizar a configuração atualizada, o usuário deve revisar/salvar nas configurações e publicar pelo produto. Restauração em uma nova tarefa não foi testada.

## Anexo — inventário Git acumulado

Snapshot de arquivos versionados modificados e novos das Etapas 01–03; inclui alterações anteriores preservadas. `M` indica modificado e `??` indica ainda não rastreado. Arquivos locais ignorados de instalação/teste não integram esta lista.

```text
 M /workspace/Connectagro/.env.example
 M /workspace/Connectagro/docs/03-regras-de-negocio.md
 M /workspace/Connectagro/src/app/__init__.py
 M /workspace/Connectagro/src/app/blueprints/__init__.py
 M /workspace/Connectagro/src/app/blueprints/aplicacoes/routes.py
 M /workspace/Connectagro/src/app/blueprints/auth/routes.py
 M /workspace/Connectagro/src/app/blueprints/colheita/routes.py
 M /workspace/Connectagro/src/app/blueprints/culturas/routes.py
 M /workspace/Connectagro/src/app/blueprints/glebas/routes.py
 M /workspace/Connectagro/src/app/blueprints/mapa/routes.py
 M /workspace/Connectagro/src/app/blueprints/upload/routes.py
 M /workspace/Connectagro/src/app/blueprints/usuarios/routes.py
 M /workspace/Connectagro/src/app/commands.py
 M /workspace/Connectagro/src/app/config.py
 M /workspace/Connectagro/src/app/models/propriedade.py
 M /workspace/Connectagro/src/app/models/usuario.py
 M /workspace/Connectagro/src/app/models/usuario_propriedade.py
 M /workspace/Connectagro/src/app/services/auditoria_service.py
 M /workspace/Connectagro/src/app/services/exportacoes_service.py
 M /workspace/Connectagro/src/app/services/ia_simulada_service.py
 M /workspace/Connectagro/src/app/static/css/main.css
 M /workspace/Connectagro/src/app/static/js/mapa.js
 M /workspace/Connectagro/src/app/templates/aplicacoes/form.html
 M /workspace/Connectagro/src/app/templates/aplicacoes/list.html
 M /workspace/Connectagro/src/app/templates/base.html
 M /workspace/Connectagro/src/app/templates/colheita/form.html
 M /workspace/Connectagro/src/app/templates/colheita/list.html
 M /workspace/Connectagro/src/app/templates/culturas/form.html
 M /workspace/Connectagro/src/app/templates/culturas/list.html
 M /workspace/Connectagro/src/app/templates/dashboard/index.html
 M /workspace/Connectagro/src/app/templates/glebas/form.html
 M /workspace/Connectagro/src/app/templates/glebas/list.html
 M /workspace/Connectagro/src/app/templates/mapa/index.html
 M /workspace/Connectagro/src/app/templates/relatorios/agricola.html
 M /workspace/Connectagro/src/app/templates/relatorios/aplicacoes.html
 M /workspace/Connectagro/src/app/templates/relatorios/geral.html
 M /workspace/Connectagro/src/app/templates/relatorios/index.html
 M /workspace/Connectagro/src/app/templates/usuarios/form.html
 M /workspace/Connectagro/src/app/templates/usuarios/list.html
 M /workspace/Connectagro/src/app/utils/auth.py
 M /workspace/Connectagro/src/app/utils/contexto.py
 M /workspace/Connectagro/src/app/utils/permissions.py
 M /workspace/Connectagro/tests/test_aplicacoes_crud.py
 M /workspace/Connectagro/tests/test_auth.py
 M /workspace/Connectagro/tests/test_colheita_crud.py
 M /workspace/Connectagro/tests/test_convite_usuarios.py
 M /workspace/Connectagro/tests/test_csrf.py
 M /workspace/Connectagro/tests/test_dashboard_operacional.py
 M /workspace/Connectagro/tests/test_equipe_financeiro_crud.py
 M /workspace/Connectagro/tests/test_glebas_culturas_crud.py
 M /workspace/Connectagro/tests/test_ia_simulada.py
 M /workspace/Connectagro/tests/test_ia_simulada_service.py
 M /workspace/Connectagro/tests/test_integridade_exclusao.py
 M /workspace/Connectagro/tests/test_mapa_real.py
 M /workspace/Connectagro/tests/test_permissions.py
 M /workspace/Connectagro/tests/test_placeholder_routes.py
 M /workspace/Connectagro/tests/test_relatorios_operacionais.py
 M /workspace/Connectagro/tests/test_upload_crud.py
 M /workspace/Connectagro/tests/test_usuarios_painel.py
?? /workspace/Connectagro/docs/auditoria/01-linha-de-base.md
?? /workspace/Connectagro/docs/auditoria/02-seguranca-autenticacao.md
?? /workspace/Connectagro/docs/auditoria/03-gerenciamento-propriedades.md
?? /workspace/Connectagro/migrations/versions/c2a83e4f9b10_add_usuario_auth_version.py
?? /workspace/Connectagro/migrations/versions/d3b94f5a0c21_unique_vinculos_propriedades.py
?? /workspace/Connectagro/src/app/blueprints/propriedades/__init__.py
?? /workspace/Connectagro/src/app/blueprints/propriedades/routes.py
?? /workspace/Connectagro/src/app/templates/propriedades/detail.html
?? /workspace/Connectagro/src/app/templates/propriedades/form.html
?? /workspace/Connectagro/src/app/templates/propriedades/list.html
?? /workspace/Connectagro/src/app/templates/propriedades/sem_contexto.html
?? /workspace/Connectagro/tests/factories.py
?? /workspace/Connectagro/tests/test_production_security.py
?? /workspace/Connectagro/tests/test_propriedades.py
?? /workspace/Connectagro/tests/test_propriedades_migration.py
?? /workspace/Connectagro/tests/test_session_migration.py
?? /workspace/Connectagro/tests/test_session_security.py
```
