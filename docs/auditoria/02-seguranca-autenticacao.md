# ConnectAgro — Etapa 02: segurança, autenticação e sessões

Data: **07/11/2026**, fuso `America/Sao_Paulo`.

**Estado da entrega: Etapa 02 concluída no escopo solicitado.** A suíte final executou **590 testes: 590 aprovados, zero falhas, erros ou ignorados**. A aplicação foi iniciada em banco descartável e login/logout dos três perfis foram verificados no Chromium. Isso não é liberação para produção: as pendências da seção G permanecem explícitas.

## A. Estado inicial

Checkout `/workspace/Connectagro`, branch `work`, HEAD `92273e2b3a4bdb6db4dc0a3b74b003ec702777d8`. A única alteração preexistente era o relatório não versionado `docs/auditoria/01-linha-de-base.md`, lido integralmente e preservado. Não houve reset, pull, descarte de alterações, commit, push ou merge.

Antes de modificar o código, foram executados `test_auth.py`, `test_permissions.py`, `test_password_reset.py`, `test_csrf.py`, `test_usuarios_painel.py`, `test_config_database.py` e `test_convite_usuarios.py`: **129 aprovados, zero falhas/erros/skipped, em 40,53 s**. A suíte utilizou SQLite em memória e URLs externas ao checkout foram explicitamente temporárias. Um registro inicial foi salvo em `/tmp/connectagro-stage2/estado-inicial.md`.

Problemas que orientaram a implementação:

| Referência | Evidência inicial / risco |
| --- | --- |
| AUD-001 | Produção aceitava chave demonstrativa e não exigia banco explícito; ambiente desconhecido caía silenciosamente em development. |
| AUD-002 | `is_authenticated()` verificava apenas `user_id`; `usuario_atual()` e permissões confiavam no perfil do cookie. Sessões continuavam válidas após rebaixamento, inativação e reset. |
| AUD-007 | Sem `APP_BASE_URL`, e-mail de recuperação podia conter caminho relativo. O fallback por Host também exigia proteção em produção. |
| AUD-010 | Cadastro/troca de e-mail gravavam endereço integral em descrições de auditoria, contrariando o mascaramento prometido. |
| AUD-011 | Logout por GET, sem CSRF, removia somente o estado local do navegador, sem revogar cookies anteriores. |
| Contas demonstrativas | `seed-users` podia ser chamado em produção, sem bloqueio anterior ao acesso ao banco. |

Além da auditoria anterior, a revisão identificou reutilização automática de IDs no SQLite como risco de um cookie de conta removida corresponder a uma conta nova com versão inicial igual. Foi acrescentada proteção específica sem mudar o identificador público ou as relações de domínio.

## B. Correções realizadas

### B.1. Arquivos e funções

| Arquivo | Alteração e motivo |
| --- | --- |
| `src/app/utils/auth.py` | Validação central `_usuario_validado`, cache associado ao request, limpeza segura local, login mínimo e logout com revogação persistente. `is_authenticated` e `usuario_atual` passaram a usar o usuário real; `login_required` continua chamando essa interface. |
| `src/app/models/usuario.py` | Coluna `auth_version`; método administrativo `revogar_sessoes`; evento `before_update` que revoga ao mudar senha, perfil ou ativação; `sqlite_autoincrement=True` para não reciclar IDs automaticamente. |
| `migrations/versions/c2a83e4f9b10_add_usuario_auth_version.py` | Migration nova, posterior a `b4f2c9d8a1e7`, preservando os usuários e inicializando versão 1. No SQLite também mantém os dados/IDs ao habilitar AUTOINCREMENT. |
| `src/app/blueprints/auth/routes.py` | Login recusa perfil desconhecido; logout aceita somente POST; reset constrói link absoluto quando não há base configurada. |
| `src/app/blueprints/usuarios/routes.py` | Removida sincronização de nome/e-mail/perfil no cookie e qualquer renovação implícita de sessão antiga. Novas descrições de cadastro/troca de e-mail usam `mascarar_email`. |
| `src/app/services/auditoria_service.py` | Identidade do ator obtida de `usuario_atual()` validado, em vez de ler diretamente um identificador arbitrário da sessão. |
| `src/app/config.py` | `configure_app` valida implantação antes das extensões; ambientes desconhecidos falham; produção exige chave forte, banco explícito e origem HTTPS canônica; flags seguras e prazo de sessão. |
| `src/app/__init__.py` | Factory chama `configure_app` antes de `db.init_app`, CSRF e Mail. |
| `src/app/commands.py` | `seed-users` permitido apenas com `APP_ENV` development/testing, antes de qualquer query ou escrita. |
| `src/app/templates/base.html` | Link “Sair” substituído por formulário POST com token CSRF, no mesmo rodapé lateral. |
| `src/app/static/css/main.css` | Formulário/botão preservam posição e aparência de link do controle “Sair”, sem reformular a interface. |
| `.env.example` | Documentados requisitos de produção, HTTPS, chave estável, migration obrigatória, prazo de sessão e bloqueio do seed. Nenhum segredo real incluído. |
| `tests/test_session_security.py` | Regressões de estado real, dois clientes, reativação, ID removido/reutilização, cookies falsos/legados/expirados, cache, logout, reset/convite, painel e mascaramento. |
| `tests/test_production_security.py` | Configuração inválida, chave estável, banco/origem explícitos, cookies, CSRF, debug, SMTP debug e bloqueio do seed sem SQL. |
| `tests/test_session_migration.py` | Upgrade real desde o head anterior, preservação de usuário, default SQL para novos inserts, comparação de schema e AUTOINCREMENT efetivo. |
| `tests/test_auth.py`, `tests/test_permissions.py` | Adaptação ao login legítimo com usuário real e versão; assertivas de sessão mínima; logout agora por POST. Perfis falsos continuam em casos adversos de rejeição. |
| `tests/test_csrf.py` | Mantida a verificação de mensagem amigável sem detalhes técnicos no conteúdo do erro; o layout agora contém legitimamente o token do formulário de logout. |
| `tests/test_convite_usuarios.py` | Preservada a cobertura anterior e acrescentadas assertivas de ausência de token puro/endereço integral nas descrições de auditoria. |
| `docs/auditoria/02-seguranca-autenticacao.md` | Este relatório. |

Não foi necessário alterar a matriz em `utils/permissions.py`: `perfil_atual`, `has_permission`, `can` e `require_permission` agora recebem dados autoritativos por meio da interface corrigida de autenticação. Os três perfis e suas permissões de negócio foram preservados.

O serviço `password_reset_service.py` e os scripts administrativos existentes já atribuem os campos a objetos ORM. O evento do modelo cobre esses caminhos sem duplicar hooks em cada chamador nem substituir seus fluxos. O consumo do token, hash, expiração, templates e integração Flask-Mail foram preservados. O script destrutivo de reset operacional foi somente inspecionado, nunca executado.

### B.2. Decisões de implementação

- Sessão assinada Flask mantida, sem JWT, Redis ou outro serviço externo.
- Revogação por conta, usando um inteiro persistente, na mesma transação que altera seu estado de segurança.
- Logout revoga **todas as sessões da conta**, inclusive cópia de cookie anterior e outros dispositivos. Essa escolha evita acrescentar armazenamento de sessões por dispositivo nesta etapa.
- Não reutilizar IDs de contas manualmente. A geração normal pelo ORM usa AUTOINCREMENT no SQLite e sequência SERIAL no PostgreSQL; a proteção de replay foi testada para os fluxos suportados.
- Nenhuma alteração na autorização territorial, seleção de propriedade ou regras agrícolas.

## C. Segurança das sessões

### C.1. Validação em cada requisição

O login salva apenas `user_id` e `auth_version` como dados de identidade. Metadados do Flask (`_permanent`, token CSRF e flashes) podem existir; senha, hash, nome, e-mail e perfil não são copiados como fonte de autorização.

A autenticação verifica tipos estritos e intervalo dos números, recusando bool, texto, listas, valores não positivos e inteiros fora do intervalo suportado. Consulta o usuário com atualização explícita do estado ORM; exige existência, conta ativa, perfil oficial e versão igual à do cookie. Sessões legadas sem versão exigem novo login. Uma sessão inválida é limpa e uma rota protegida redireciona para o login com mensagem apropriada.

`usuario_atual()` mantém o contrato de dict usado pelos módulos, mas os valores vêm do modelo validado. Um `user_perfil=admin` acrescentado ao cookie de um gerente não concede permissão administrativa. Perfil desconhecido no banco impede login e invalida sessão anterior.

O cache fica em `flask.g`, associado à identidade do objeto request: não é reaproveitado entre requisições, mesmo quando um teste mantém o app context aberto. A regressão correspondente comprovou uma busca de validação do usuário por request em chamadas repetidas sem commit intermediário; isso não significa que todas as demais consultas ORM do produto foram eliminadas.

### C.2. Revogação persistente

`Usuario.revogar_sessoes()` define incremento SQL `auth_version = auth_version + 1`, sem commit próprio. Alterações ORM de `senha_hash`, `perfil` ou `ativo` acionam esse incremento em `before_update`. O commit confirma alteração e revogação juntos; rollback desfaz ambas. Assim estão cobertos:

- edição administrativa, incluindo mudança de senha/perfil/status;
- inativação e reativação;
- reset de senha e definição inicial por convite;
- script de atualização de credenciais e atribuições ORM dos helpers administrativos;
- revogação administrativa explícita, chamando o método e confirmando a transação;
- logout de um usuário ainda validado.

Ao reativar uma conta, suas sessões antigas continuam inválidas. Mudança de perfil também revoga, exigindo novo login com permissões atuais. Não há renovação automática da sessão anterior pelo painel.

Um cookie antigo já revogado não pode ser usado para derrubar uma sessão nova pelo endpoint de logout: ele não passa pela validação que autoriza o incremento. Falha no commit de logout não é tratada como revogação bem-sucedida.

Foi testado o caso de duas sessões ORM carregando versão antiga, com commits sucessivos de revogação: resultado final 3, sem perder incremento. Isso demonstra o comportamento com leituras antigas; não foi executado teste de carga com transações paralelas em múltiplos processos.

**Contrato administrativo:** SQL direto ou UPDATE em massa não dispara eventos de mapper. Alterações de senha/perfil/ativação devem usar objetos ORM ou incrementar a versão explicitamente na mesma transação. Não se deve repor uma versão antiga ou reciclar IDs manualmente. Os caminhos atuais examinados usam o ORM para essas alterações; o script destrutivo não é um fluxo autorizado de operação desta etapa.

### C.3. Logout, prazo e recuperação

GET `/auth/logout` retorna **405** e não encerra a sessão. POST sem CSRF retorna **400** quando a proteção está ativa. O formulário “Sair” envia POST com token, revoga a conta e remove os dados locais. POST de usuário já desconectado continua seguro/idempotente.

As sessões são permanentes, com `PERMANENT_SESSION_LIFETIME` de **8 horas** e `SESSION_REFRESH_EACH_REQUEST=False`. A assinatura expirada foi testada e recusada. O Flask pode emitir novo cookie quando o conteúdo da sessão é modificado; esse limite não foi apresentado como expiração absoluta de uma conta independente de todas as escritas de sessão. A versão persistente continua sendo o mecanismo de revogação.

Recuperação/convite mantêm token aleatório, hash SHA-256 no banco, expiração e marca de uso único. Casos existentes de expiração, uso repetido, usuário inativo e mensagem genérica continuaram cobertos. Novas regressões verificam que reset e convite invalidam dois clientes previamente conectados. Em produção, o link demonstrativo permanece oculto. O link de e-mail usa a origem canônica configurada; em dev/test há fallback absoluto para o host da requisição.

Tokens não foram impressos neste relatório. As descrições de auditoria são verificadas quanto à ausência de token puro, e o diagnóstico SMTP é forçado a falso em produção. Logs de acesso de reverse proxy/servidor de produção não foram inspecionados: a implantação também deve impedir que URLs tokenizadas sejam retidas sem proteção nesses logs.

## D. Segurança em produção

Validação executada a cada criação da aplicação, antes de ativar as extensões:

1. Somente `development`, `testing` e `production` são aceitos. Nome vazio/desconhecido não cai silenciosamente em desenvolvimento.
2. `SECRET_KEY` deve vir explicitamente do ambiente. São recusados ausência, vazio, chave curta, exemplos conhecidos e padrões repetitivos ou claramente fracos cobertos pelos testes. O mínimo é 32 caracteres; essas verificações não substituem geração criptográfica e armazenamento seguro pelo operador. A aplicação não gera uma chave nova a cada inicialização; duas criações com a mesma configuração mantêm a chave.
3. `DATABASE_URL` é obrigatória e a URL resolvida é validada; não há fallback implícito em produção. SQLite explicitamente configurado continua suportado, inclusive para os ensaios locais. `DIRECT_URL` permanece opcional e é normalizada/validada.
4. `APP_BASE_URL` é obrigatória e deve ser HTTPS canônica, sem credenciais, query, fragmento, espaços ou barra invertida. Isso evita confiar no Host arbitrário do solicitante para links de reset/convite.
5. `DEBUG=False`, `WTF_CSRF_ENABLED=True`, `PASSWORD_RESET_SHOW_DEV_LINK=False`, `MAIL_DEBUG=False`; variáveis que tentem enfraquecer CSRF ou links de desenvolvimento não alteram essas garantias. Valores de `FLASK_DEBUG` que o CLI interpretaria como ativos — inclusive desconhecidos ou `off` — são recusados.
6. Cookies: `HttpOnly=True`, `Secure=True`, `SameSite=Lax`. O header real `Set-Cookie` foi verificado em requisição HTTPS simulada. Desenvolvimento/testes continuam aceitando HTTP local, sem serviço externo.
7. `seed-users` é bloqueado em produção antes de consulta/escrita. Um teste com observação de SQL comprovou zero comandos e ausência de criação do arquivo SQLite. Em development/testing, o comando continua explícito e idempotente.

Erros de configuração não incluem os valores de chave, DSN ou URL. Nenhuma conta preexistente foi apagada nem senha real alterada. Não houve inspeção de bases de produção para procurar contas demo; se o operador as identificar, deve revisar acessos e credenciais em procedimento administrativo próprio.

## E. Testes e evidências

### E.1. Execuções

Todas as verificações usaram `.venv` com Python 3.12.14, dependências preservadas e bancos descartáveis. Comando de baseline: os sete arquivos indicados em A, com `-q --junitxml=/tmp/connectagro-stage2/baseline.xml`.

```bash
# Na raiz, com DATABASE_URL e DIRECT_URL explicitamente temporárias:
.venv/bin/python -m pytest -q tests/test_session_security.py \
  tests/test_production_security.py tests/test_session_migration.py \
  tests/test_auth.py tests/test_permissions.py tests/test_password_reset.py \
  tests/test_csrf.py tests/test_usuarios_painel.py \
  tests/test_config_database.py tests/test_convite_usuarios.py
.venv/bin/python -m pytest -q
.venv/bin/python -m compileall -q src tests
```

| Execução | Resultado observado |
| --- | --- |
| Baseline anterior às alterações | 129 aprovados; 40,53 s |
| Segurança após as correções fundamentais e regressões | 191 aprovados; 47,65 s; quatro avisos legados de migration |
| Convites/auditoria após mascaramento | 14 aprovados; 6,46 s |
| Configuração de produção final | 35 aprovados; 0,54 s |
| Suíte completa final, após todas as alterações | **590 aprovados, zero falhas, erros, skipped ou casos coletados não executados; 154,88 s**; quatro avisos |
| `compileall -q src tests` | Código de saída 0 |
| Script administrativo em SQLite descartável | Backup real, usuário preservado, versão 1 → 2 e sessão anterior recusada |
| Navegador Chromium / HTTP real | Login, dashboard, permissões, logout POST/CSRF e rejeição do cookie copiado, nos três perfis |

A diferença para os 521 casos da Etapa 01 corresponde a **69 novos casos parametrizados**, sem remoção de testes anteriores. Artefatos desta instância: `/tmp/connectagro-stage2/full-final.xml`, `security-final.xml`, `production-final.xml`, `postgres.json` e roteiros temporários de validação. Esses auxiliares podem desaparecer ao descartar a máquina; os testes novos versionáveis e a migration são a base permanente de reprodução.

Execuções intermediárias não foram escondidas: um novo teste de remoção de conta inicialmente encontrou a restrição do relacionamento de propriedade, e passou a simular a remoção externa somente na fixture descartável, mantendo a assertiva de rejeição da sessão. Outro teste CSRF antigo proibia a string `csrf_token` em todo o HTML; com o novo formulário legítimo de logout, a assertiva passou a examinar o conteúdo da mensagem de erro, preservando rejeição 400 e ausência de detalhes técnicos. Nenhuma verificação de acesso foi removida para produzir um resultado positivo.

Os quatro avisos são `DeprecationWarning` do `get_engine()` legado em `migrations/env.py:21`, emitidos pelo teste novo que executa migrations reais. Não são falhas nem foram silenciados; a atualização desse helper pode ser feita separadamente, sem alterar dependências nesta etapa.

### E.2. Casos obrigatórios

| Caso | Cobertura executada |
| --- | --- |
| T01 / T02 | `test_auth.py`: usuário ativo autentica; inativo recebe 403. |
| T03 | `test_inativacao_revoga_dois_clientes_e_reativacao_nao_ressuscita`. |
| T04 | `test_usuario_excluido_nao_autentica_cookie_anterior` e proteção contra reutilização automática de ID. |
| T05 | Rebaixamento e edição administrativa reais: sessão antiga redirecionada, novo login aplica perfil atual. |
| T06 | `test_perfil_falso_no_cookie_nao_concede_privilegio`. |
| T07 | Perfil desconhecido no banco não autentica; matriz desconhecida não recebe permissões. |
| T08 / T09 / T10 | Logout POST, GET 405, POST sem CSRF 400, formulário com CSRF e acesso posterior bloqueado. |
| T11 | Reset e definição de senha invalidam clientes anteriores. |
| T12 | `test_get_redefinir_token_expirado_retorna_erro` e convite expirado. |
| T13 | `test_token_usado_nao_pode_ser_reutilizado` e regressões de reset/convite. |
| T14 | Produção recusa as chaves inseguras parametrizadas. |
| T15 | Flags de cookies/CSRF/debug e header HTTPS `Set-Cookie` verificados. |
| T16 | Seed em produção bloqueado antes de qualquer SQL. |
| T17 | HTTP local em development e seed idempotente preservados. |
| T18 | Suíte anterior preservada; resultado completo final registrado nesta seção. |
| T19 | Inativação seguida de reativação não ressuscita o cookie antigo. |
| T20 | Dois clientes simultaneamente autenticados são invalidados após reset. |

## F. Compatibilidade, migração e implantação

Migration **`c2a83e4f9b10`**, dependente de `b4f2c9d8a1e7`. Não foram editadas migrations históricas. A coluna nova é inteira não anulável, com default Python/SQL 1; usuários antigos mantêm IDs, nome, e-mail, hash, perfil e estado. No SQLite, o batch recria a estrutura de `usuario`, copia as linhas e ativa AUTOINCREMENT; no PostgreSQL, adiciona a coluna e mantém a sequência existente. Não há limpeza de usuários ou outros registros.

Teste automatizado SQLite: upgrade desde o head antigo com usuário preexistente, preservação dos dados, default 1 para INSERT sem a coluna nova, schema compatível com metadata e confirmação de AUTOINCREMENT no DDL.

Ensaio PostgreSQL **16.15** em contêiner oficial local descartável: upgrade antigo, inserção de usuário legado, upgrade para o novo head e `db check` sem diferenças. Usuário preservado; inativação/reativação produziram versões **1 → 2 → 3**. Também passaram carga/repetição de catálogo e seed, login/CSRF, gleba, cultura, aplicação, colheita, financeiro, polígono, dashboard e PDF via `Flask.test_client` (WSGI). A suíte oficial não foi convertida para PostgreSQL; esse foi um ensaio representativo separado. Contêiner encerrado/removido ao terminar.

O script original `scripts/update_admin_credentials.py` foi executado integralmente sobre um SQLite novo de teste, com credenciais sintéticas geradas em memória. Somente a raiz do diretório de backup foi redirecionada para `/tmp`; a rotina de backup e a alteração ORM foram reais. O backup reteve versão 1, o registro atualizado passou à versão 2, e o cliente autenticado anteriormente perdeu acesso. Nenhuma base ou credencial preexistente foi alterada.

Inicialização real pelo entrypoint `src/run.py` via Flask CLI, porta 5002, em outro SQLite temporário migrado, sem debugger/reloader e com CSRF ativo. Playwright/Chromium verificou `admin`, `tecnico` e `trabalhador`: login/dashboard; permissões admin versus demais perfis; JSON do mapa; GET logout 405 sem desconectar; POST sem CSRF 400; botão “Sair” com POST válido; rota privada bloqueada depois do logout; cookie copiado antes do logout recusado ao ser reapresentado. O servidor temporário foi encerrado após os ensaios. O aviso de servidor de desenvolvimento do Werkzeug foi esperado; não houve erro de startup.

**Ordem necessária em ambientes existentes:** fazer backup adequado, aplicar `flask --app src/run.py db upgrade` em ambiente autorizado antes de iniciar o novo código, e então reiniciar os processos. Esta etapa não aplicou migrations em bancos reais/preexistentes do operador. Cookies antigos sem versão perderão autenticação e exigirão novo login; dados e senhas não são alterados por essa expiração de sessão. Não executar `seed-users` em produção, nem usar scripts de reset para instalar a migration.

Produção passa a exigir configuração válida de chave estável, banco e `APP_BASE_URL` HTTPS. Falhar na inicialização diante de configuração insegura é intencional. Aplicar mudanças durante janela sem escritas concorrentes; não rebaixar a migration nem restaurar versões de autenticação antigas mantendo cookies de usuários, pois isso desfaria garantias de revogação.

Dashboard, usuários/convites, contexto de propriedades, glebas, mapa backend, culturas, aplicações, colheitas, equipe, financeiro, catálogo, relatórios, arquivos, auditoria e assistente foram mantidos. Não houve alteração de suas regras agrícolas ou de permissões territoriais; o controle “Sair” foi a única adaptação visual necessária.

## G. Pendências e conclusão de escopo

Permanecem da Etapa 01, sem correção funcional nesta etapa: números não finitos (AUD-003), datas (AUD-004), payloads GeoJSON (AUD-005), FKs SQLite desativadas (AUD-006), fórmulas CSV (AUD-009), regra específica do assistente (AUD-012) e documentação geral antiga (AUD-013). O mapa visual ainda depende de `unpkg.com` e dos tiles OpenStreetMap; salvar permissões em rascunho não comprova aplicação da rede. A suspeita de troca de camada visual do mapa continua pendente de reprodução com a CDN disponível.

Não foram executados SMTP real, Supabase/PgBouncer, HTTPS/reverse proxy de produção, carga concorrente ou toda a interação visual do mapa. Há necessidade futura de avaliar limitação de tentativas de login/reset, consumo concorrente de tokens, política de logs de acesso e eventual logout por dispositivo. Essas limitações não foram apresentadas como verificadas. Novas descrições de auditoria foram mascaradas; logs históricos não foram reescritos.

A seleção/gerência de múltiplas propriedades e a matriz por Área de Plantio ficam para a **Etapa 03** e a etapa territorial correspondente. O resolvedor atual de contexto foi preservado; não foi criada uma interface nova de revogação ou de escolha de propriedade.

Os critérios desta etapa foram atendidos: autenticação autoritativa, inativação/perfil com efeito na próxima requisição, revogação persistente, logout protegido, produção recusando configuração insegura, seed bloqueado e recuperação/convites preservados. A suíte integral, migrations e ensaios funcionais passaram nos limites descritos.

O projeto está preparado para avançar à **Etapa 03: gerenciamento e seleção de múltiplas propriedades**. Isso não constitui liberação para produção enquanto os demais achados e requisitos de implantação permanecerem abertos. O Git permanece na branch `work`, sem commit, push ou merge; o relatório da Etapa 01 permanece preservado.
