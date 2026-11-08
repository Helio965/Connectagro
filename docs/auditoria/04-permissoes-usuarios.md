# Etapa 04 — permissões de usuários

Data de referência: 08/11/2026, America/Sao_Paulo.

## 1. Estado anterior e preservação

Repositório oficial `Helio965/Connectagro`, checkout `/workspace/Connectagro`.
O trabalho começou na branch `work`, HEAD
`92273e2b3a4bdb6db4dc0a3b74b003ec702777d8`. `git fetch origin` confirmou
`origin/main` no mesmo commit, sem commits locais à frente/atrás ou conflitos.
Havia **76 arquivos modificados/novos das Etapas 01–03**, ainda sem commit.

Foram conferidos os relatórios 01, 02 e 03, o código e as regras de negócio.
As implementações de autenticação/sessões e múltiplas propriedades existem
localmente; não constam ainda no HEAD oficial. Nenhum arquivo anterior foi
descartado. Snapshot integral anterior à Etapa 04, com hashes dos arquivos,
em `/tmp/connectagro-stage4/baseline/` e `baseline-manifest.json`; diff inicial
em `before.diff`. Esses artefatos são auxiliares desta instância.

Baseline executado antes das correções: **171 testes aprovados**, zero falhas,
erros ou ignorados, em **65,44 s**, incluindo permissões, usuários, autenticação,
CSRF, auditoria, sessões, convites e propriedades. Evidência:
`/tmp/connectagro-stage4/baseline.xml`.

Branch exclusiva criada após verificar ausência local/remota:
`codex/etapa-04-permissoes-usuarios`. Não houve reset, limpeza, force push ou merge.
Uma falha de inicialização do executor interrompeu esta etapa; após o retorno,
os arquivos foram conferidos e os testes retomados, sem assumir conclusão.

## 2. Achados e decisões

| Achado | Evidência e tratamento |
| --- | --- |
| Detalhes financeiros acessíveis ao Trabalhador por relatórios | HTML/CSV/PDF do financeiro exigiam apenas `relatorios.view`; agora exigem também `financeiro.view`, com card correspondente oculto |
| Corrida na proteção do último administrador | Dois administradores podiam validar contagem 2 e inativar um ao outro simultaneamente; agora verificação e alteração compartilham lock/transação do contexto, com revalidação do ator após espera |
| Auditoria de permissão negada incompatível com PostgreSQL | Nome textual da permissão era passado a `LogAuditoria.entidade_id`, que é Integer; PostgreSQL rejeitava o log e o serviço tratava a falha silenciosamente. Agora esse ID fica NULL; o nome continua na descrição |
| RN-11m antiga dizia “apenas admin” | Código, testes e README já previam Gerente administrando Trabalhadores. Preservada essa funcionalidade limitada; documentação corrigida |
| “Visão global” do Administrador sem contrato definido | Mantido o isolamento aprovado por propriedade/vínculo; não foi concedido acesso global |
| Ausência de autorização por Área de Plantio | Não há relação usuário↔Gleba nem papel por área; limitação registrada, sem criar vínculos fictícios |
| Documentação de contexto e serviço de usuários desatualizada | Removidas afirmações de criação de vínculo em leitura, ausência de seleção múltipla e referência a `usuarios_service.py` inexistente |

**Decisão expressa do usuário nesta etapa:** o Trabalhador pode consultar
“**somente totais agregados, sem detalhes financeiros ou de equipe**”. Por isso,
relatório geral e IA continuam exibindo receitas/despesas/saldo e contagens
agregadas, sem abrir lançamentos individuais ou membros de equipe. Não foi
classificado como falha o acesso a agregados autorizado por essa decisão.

As decisões anteriores permanecem: Administrador e Gerente criam/editam
Propriedades autorizadas; conta compartilhada é inativada somente no vínculo
local; Administrador não tem acesso global. `tecnico` continua sendo o valor
interno de **Gerente de Plantio**. Não há nova tabela RBAC nem biblioteca de
autorização.

## 3. Matriz final

Há **43 permissões distintas**: Administrador 43, Gerente 31, Trabalhador 16.
Nenhuma foi adicionada ou ampliada. Todas têm uso em autorização backend;
nenhuma referência usada em rota/template está sem declaração. O inventário
final identifica 76 regras de rota, 17 blueprints, 68 rotas privadas com ambos
os decorators e 93 usos de `can()` em templates. Métodos HEAD/OPTIONS implícitos
não são repetidos. As rotas públicas de autenticação, health e estáticos foram
preservadas; redefinição/convite dependem de token válido.

| Operação | Administrador | Gerente de Plantio | Trabalhador |
| --- | --- | --- | --- |
| Dashboard, catálogo, mapa, IA e relatórios operacionais | Consultar | Consultar | Consultar |
| Propriedade: listar/ver/selecionar | Vínculo ativo | Vínculo ativo | Vínculo ativo |
| Propriedade: criar/editar | Sim | Sim | Não |
| Propriedade: excluir/desativar | Bloqueado | Bloqueado | Bloqueado |
| Áreas de Plantio e culturas | Ler/criar/editar/remover, respeitando histórico | Ler/criar/editar | Ler |
| Aplicações e colheita | Ler/criar/editar/remover | Ler/criar/editar | Ler/criar |
| Equipe: membros e detalhes | CRUD | Ler | Não |
| Financeiro: lançamentos e relatório detalhado HTML/CSV/PDF | CRUD e exportar | Ler e exportar | Não |
| Totais agregados financeiros/equipe em relatório geral e IA | Sim | Sim | Sim, conforme decisão expressa |
| Uploads | Ler/enviar/baixar/remover | Ler/enviar/baixar | Ler/enviar/baixar |
| Editar/salvar/limpar polígono | Sim | Sim | Não |
| Usuários | Gerentes/Trabalhadores e proteções específicas para admin | Somente Trabalhadores autorizados | Não |
| Criar Administrador pelo painel | Não | Não | Não |
| Alterar o próprio perfil administrativo/inativar-se indevidamente | Bloqueado | Sem promoção | Sem acesso |
| Auditoria | Consultar no contexto atual | Não | Não |

Os três relatórios financeiros detalhados exigem **duas** permissões:
`relatorios.view` **e** `financeiro.view`. Relatórios gerais/agrícolas/aplicações/
uploads mantêm `relatorios.view`. Os agregados da IA não incluem descrições,
categorias ou nomes de lançamentos/membros. O contexto interno pode consultar
registros para calcular totais; isso não os torna parte da resposta HTTP.

`perfil_atual()`, `has_permission()`, `can()` e `require_permission()` recebem a
identidade validada no banco pela Etapa 02. Perfil desconhecido não autentica e
não recebe permissão; um perfil forjado no cookie ou formulário não amplia
acesso. A matriz é verificada integralmente por teste de contrato para detectar
concessões acidentais futuras.

## 4. Arquivos e correções

Raiz absoluta dos caminhos: `/workspace/Connectagro/`.

| Arquivo | Alteração |
| --- | --- |
| `src/app/blueprints/usuarios/routes.py` | `_serializar_alteracao_usuario`: lock comum por contexto, revalidação de conta/epoch/vínculo/permissão após espera, antes de editar/inativar; recarregamento dos alvos |
| `src/app/blueprints/relatorios/routes.py` | Exigir `financeiro.view` nas três rotas detalhadas; corrigir docstring que negava exportação existente |
| `src/app/utils/permissions.py` | Não atribuir string de permissão a `entidade_id` Integer na auditoria negada |
| `src/app/templates/relatorios/index.html` | Card de financeiro detalhado condicionado a `can('financeiro.view')` |
| `tests/test_admin_governance.py` | 11 casos: concorrência real SQLite, compartilhamento, revalidação após espera e ausência de commit antecipado |
| `tests/test_permissions_stage4.py` | 28 casos: matriz completa, detalhes negados/agregados preservados, exportações, UI, escalonamento e auditoria |
| `README.md` | Matriz e painel/contexto atuais, sem auto-vínculo em leitura |
| `docs/03-regras-de-negocio.md` | Regra expressa de agregados, correção RN-11m, exceção de auditoria atômica de Propriedade já implementada na Etapa 03 |
| `docs/06-1-arquitetura-tecnica-mvp.md` | Painel e fonte real das validações, contexto múltiplo, conta compartilhada e detalhes financeiros |
| `docs/09-roadmap-mvp-ampliado.md` | Atualizar descrição de gestão de Trabalhadores por Gerente |
| `tests/README.md` | Descrever matriz/novos testes, sem exclusividade administrativa incorreta |
| `docs/auditoria/04-permissoes-usuarios.md` | Este relatório e inventário de rotas |

Não foram alterados os valores de perfil, modelos ou migrations nesta etapa.
Migrations c2/d3 das etapas anteriores continuam sendo pré-requisitos de uma
instalação atualizada. Não houve execução de migration em banco real.

## 5. Isolamento e proteção de governança

Todas as operações operacionais usam a propriedade selecionada validada por
vínculo ativo. Identificadores de URL/formulário não substituem o contexto.
Permissão ausente retorna 403; recurso fora do contexto retorna 404 quando
adequado. CSRF é verificado independentemente do perfil; ocultar botões é
somente apoio visual. Seleção revogada e formulários antigos mantêm as proteções
da Etapa 03.

Gerente não cria Administrador/Gerente, não altera conta administrativa nem
administra usuários exclusivos de outro contexto. Contas compartilhadas
preservam os outros vínculos. Não se adotou `criado_por_id` como uma nova regra
de isolamento entre Gerentes da mesma propriedade, pois não há tal autorização
documental.

Para editar/inativar, o PostgreSQL bloqueia a linha comum da Propriedade com
`SELECT FOR UPDATE` na transação. No SQLite, `BEGIN IMMEDIATE` reserva a escrita;
se já houver transação física, UPDATE sem mudança de valores obtém o lock.
Conflito de upgrade SQLite é recusado com 409, sem repetir decisão baseada em
estado antigo. Não há commit antecipado. Conta, versão de sessão, vínculo e
permissão do ator são revalidados após obter o lock; o alvo é recarregado.
Assim, dois administradores não conseguem confirmar simultaneamente a
inativação um do outro. A proteção cobre o endpoint de inativação e o checkbox
da edição, inclusive para contas compartilhadas.

Foram mantidos convite por e-mail/definição de senha, hash de senhas, revogação
persistente e auditoria sensível sem senha/token/GeoJSON. Novos eventos de
permissão negada têm `entidade_id=NULL` e o nome da permissão na descrição;
eventos antigos não foram apagados ou reescritos.

## 6. Testes e evidências

Comandos na raiz, com `.venv` e bancos exclusivamente descartáveis:

```bash
.venv/bin/python -m pytest -q tests/test_permissions_stage4.py \
  tests/test_admin_governance.py tests/test_exportacoes.py \
  tests/test_permissions.py tests/test_usuarios_painel.py \
  tests/test_session_security.py tests/test_propriedades.py \
  tests/test_convite_usuarios.py tests/test_auditoria.py
.venv/bin/python -m compileall -q src tests
.venv/bin/python -m pytest -q
git diff --check
```

| Execução | Resultado real |
| --- | --- |
| Baseline pré-correção | 171 aprovados; 65,44 s |
| Testes diretamente relacionados, após todas as correções | 232 aprovados, zero falhas/erros/ignorados; 87,45 s |
| Suíte completa | **687 aprovados, zero falhas/erros/ignorados; 193,08 s; exit 0** |
| Compilação | Código de saída 0 |
| PostgreSQL 16.15 descartável, migrations reais até d3 | Seis corridas reais aprovadas; auditoria negada persistida; financeiro worker403 e agregados200 |
| Navegador com três perfis | **115 assertivas aprovadas**, zero falhas/erros JavaScript; desktop e celular; servidor encerrado |

Evidências locais: `/tmp/connectagro-stage4/baseline.xml`, `focused-final.xml`,
`full-final.xml`, respectivos logs e `postgres.py/.json/.log`. As seis corridas
PostgreSQL combinaram inativação/edição/misto e conta global/compartilhada, com
dois requests autenticados por CSRF real e barreira antes do lock. Sempre houve
um sucesso, uma autorização revogada após espera, exatamente um administrador
ativo e um log de inativação. Em contas compartilhadas, os dois administradores
globais e os vínculos do outro contexto foram preservados. O container foi
removido no `finally`.

Os três acessos negados a relatórios financeiros detalhados no PostgreSQL
produziram três logs `permissao.negada` com ID NULL e ator/contexto corretos.
Relatório geral HTML/CSV e IA GET/POST mantiveram agregados sem marcadores
individuais. Gerente continuou consultando o financeiro detalhado.

Uma rodada inicial dos novos testes encontrou falha no parser auxiliar de PDF
do teste, que não decodificava parênteses escapados. Foi corrigido somente o
parser, mantendo todas as assertivas sobre totais e ausência de segredos.
Nenhum teste antigo foi enfraquecido para obter aprovação.

Os cenários T01–T30 do pedido são cobertos pela matriz completa, novos testes de
permissões/governança e suítes existentes de usuários, convites, CSRF, sessões,
propriedades, integridade, exportação, upload e mapas. T21 inclui concorrência
real em dois bancos; T29/T30 verificam o conjunto exato das 43 permissões.

## 7. Compatibilidade

Preservados: arquitetura Flask/SQLAlchemy/Alembic, perfis internos, vínculos e
responsáveis, seleção de contexto, módulos agrícolas, histórico, proteção de
exclusão, catálogos, arquivos, convite/recuperação, sessões e CSRF. Nenhuma senha,
conta, registro agrícola ou log anterior foi excluído. Relatórios operacionais e
IA mantêm o acesso aprovado; somente as três vias de detalhes financeiros foram
restringidas ao contrato confirmado.

## 8. Pendências e publicação

- Definição de eventual visão administrativa global: não autorizada nesta
  implementação; permanece acesso somente por vínculo ativo.
- Autorização por Área de Plantio e segmentação entre Gerentes da mesma
  propriedade: relações não modeladas, sem funcionalidade alegada como pronta.
- Política de retenção/desativação de Propriedade e novo fluxo para vincular
  conta já existente a outro ambiente permanecem pendentes da Etapa 03.
- A publicação exclusiva da Etapa 04 depende da base anterior não commitada.
  O HEAD oficial não tem `auth_version`, c2/d3, seleção/contexto ou as fixtures
  usadas na versão validada. Incluir arquivos completos misturaria etapas;
  publicar só o delta sobre o HEAD antigo não reproduziria o sistema testado.
  A solução revisável é um commit-base separado das Etapas 01–03, seguido do
  commit exclusivo da Etapa 04, mantendo a dependência explícita e sem merge.
  A estratégia de dependências solicitada na Etapa 05 será aplicada: a base
  identificada terá um commit e uma branch próprios, sem ser incorporada ao
  commit exclusivo da Etapa 04. Cada PR declarará sua base e escopo, sem merge
  automático. Não há alterações anteriores desconhecidas sendo incluídas.
- SMTP externo, Supabase e restauração em nova tarefa não foram validados.
  Persistem os achados de números/datas/CSV e mapa externo registrados nos
  relatórios anteriores, fora do escopo desta etapa.

## 9. Conclusão

**Etapa 04 tecnicamente concluída:** matriz coerente com as decisões
aprovadas, sem falhas críticas de autorização remanescentes nos cenários
verificados. A suíte completa executou 687 testes com todos aprovados, e o
navegador executou 115 assertivas com os três perfis. O sistema pode servir
como base para a Etapa 05 de mapas, mantendo as limitações funcionais da seção
8. Nenhuma permissão por Área de Plantio foi apresentada como implementada.

A publicação será confirmada pelo Git/GitHub e registrada na entrega, sem
inventar commit ou link. A base das Etapas 01–03, o commit exclusivo da Etapa
04 e a evolução da Etapa 05 serão identificados separadamente.

## Anexo — inventário de todas as rotas

Permissões separadas por `+` são cumulativas. As classificações são para auditoria, sem criar novas permissões.

| Rota | Métodos explícitos | Endpoint | Permissão | Login decorator | Classificação | Perfis com permissão | Origem |
|---|---|---|---|---|---|---|---|
| /aplicacoes/ | GET | aplicacoes.index | aplicacoes.view | sim | operacional / leitura | admin, tecnico, trabalhador | src/app/blueprints/aplicacoes/routes.py:128 |
| /aplicacoes/nova | GET,POST | aplicacoes.nova | aplicacoes.create | sim | criação | admin, tecnico, trabalhador | src/app/blueprints/aplicacoes/routes.py:144 |
| /aplicacoes/<int:aplicacao_id>/editar | GET,POST | aplicacoes.editar | aplicacoes.edit | sim | edição | admin, tecnico | src/app/blueprints/aplicacoes/routes.py:176 |
| /aplicacoes/<int:aplicacao_id>/remover | POST | aplicacoes.remover | aplicacoes.delete | sim | exclusão | admin | src/app/blueprints/aplicacoes/routes.py:215 |
| /auditoria/ | GET | auditoria.index | auditoria.view | sim | administrativa / leitura | admin | src/app/blueprints/auditoria/routes.py:196 |
| /auth/ | GET | auth.index | — | não | pública / autenticação | todos/publica | src/app/blueprints/auth/routes.py:46 |
| /auth/login | GET,POST | auth.login | — | não | pública / autenticação | todos/publica | src/app/blueprints/auth/routes.py:52 |
| /auth/logout | POST | auth.logout | — | não | pública / autenticação | todos/publica | src/app/blueprints/auth/routes.py:106 |
| /auth/esqueci-senha | GET,POST | auth.esqueci_senha | — | não | pública / autenticação | todos/publica | src/app/blueprints/auth/routes.py:124 |
| /auth/redefinir-senha/<token> | GET,POST | auth.redefinir_senha | — | não | pública / autenticação | todos/publica | src/app/blueprints/auth/routes.py:230 |
| /auth/definir-senha/<token> | GET,POST | auth.definir_senha | — | não | pública / autenticação | todos/publica | src/app/blueprints/auth/routes.py:236 |
| /colheita/ | GET | colheita.index | colheita.view | sim | operacional / leitura | admin, tecnico, trabalhador | src/app/blueprints/colheita/routes.py:86 |
| /colheita/nova | GET,POST | colheita.nova | colheita.create | sim | criação | admin, tecnico, trabalhador | src/app/blueprints/colheita/routes.py:108 |
| /colheita/<int:colheita_id>/editar | GET,POST | colheita.editar | colheita.edit | sim | edição | admin, tecnico | src/app/blueprints/colheita/routes.py:133 |
| /colheita/<int:colheita_id>/remover | POST | colheita.remover | colheita.delete | sim | exclusão | admin | src/app/blueprints/colheita/routes.py:163 |
| /culturas/ | GET | culturas.index | culturas.view | sim | operacional / leitura | admin, tecnico, trabalhador | src/app/blueprints/culturas/routes.py:80 |
| /culturas/nova | GET,POST | culturas.nova | culturas.create | sim | criação | admin, tecnico | src/app/blueprints/culturas/routes.py:94 |
| /culturas/<int:cultura_id>/editar | GET,POST | culturas.editar | culturas.edit | sim | edição | admin, tecnico | src/app/blueprints/culturas/routes.py:133 |
| /culturas/<int:cultura_id>/remover | POST | culturas.remover | culturas.delete | sim | exclusão | admin | src/app/blueprints/culturas/routes.py:189 |
| / | GET | dashboard.index | dashboard.view | sim | operacional / leitura | admin, tecnico, trabalhador | src/app/blueprints/dashboard/routes.py:15 |
| /defensivos/ | GET | defensivos.index | catalogo.view | sim | operacional / leitura | admin, tecnico, trabalhador | src/app/blueprints/defensivos/routes.py:23 |
| /defensivos/<slug> | GET | defensivos.detalhe | catalogo.view | sim | operacional / leitura | admin, tecnico, trabalhador | src/app/blueprints/defensivos/routes.py:38 |
| /equipe/ | GET | equipe.index | equipe.view | sim | operacional / leitura | admin, tecnico | src/app/blueprints/equipe/routes.py:30 |
| /equipe/novo | GET,POST | equipe.novo | equipe.create | sim | criação | admin | src/app/blueprints/equipe/routes.py:42 |
| /equipe/<int:membro_id>/editar | GET,POST | equipe.editar | equipe.edit | sim | edição | admin | src/app/blueprints/equipe/routes.py:72 |
| /equipe/<int:membro_id>/remover | POST | equipe.remover | equipe.delete | sim | exclusão | admin | src/app/blueprints/equipe/routes.py:99 |
| /fertilizantes/ | GET | fertilizantes.index | catalogo.view | sim | operacional / leitura | admin, tecnico, trabalhador | src/app/blueprints/fertilizantes/routes.py:23 |
| /fertilizantes/<slug> | GET | fertilizantes.detalhe | catalogo.view | sim | operacional / leitura | admin, tecnico, trabalhador | src/app/blueprints/fertilizantes/routes.py:38 |
| /financeiro/ | GET | financeiro.index | financeiro.view | sim | operacional / leitura | admin, tecnico | src/app/blueprints/financeiro/routes.py:46 |
| /financeiro/novo | GET,POST | financeiro.novo | financeiro.create | sim | criação | admin | src/app/blueprints/financeiro/routes.py:63 |
| /financeiro/<int:lancamento_id>/editar | GET,POST | financeiro.editar | financeiro.edit | sim | edição | admin | src/app/blueprints/financeiro/routes.py:86 |
| /financeiro/<int:lancamento_id>/remover | POST | financeiro.remover | financeiro.delete | sim | exclusão | admin | src/app/blueprints/financeiro/routes.py:114 |
| /glebas/ | GET | glebas.index | glebas.view | sim | operacional / leitura | admin, tecnico, trabalhador | src/app/blueprints/glebas/routes.py:65 |
| /glebas/nova | GET,POST | glebas.nova | glebas.create | sim | criação | admin, tecnico | src/app/blueprints/glebas/routes.py:77 |
| /glebas/<int:gleba_id>/editar | GET,POST | glebas.editar | glebas.edit | sim | edição | admin, tecnico | src/app/blueprints/glebas/routes.py:104 |
| /glebas/<int:gleba_id>/remover | POST | glebas.remover | glebas.delete | sim | exclusão | admin | src/app/blueprints/glebas/routes.py:133 |
| /ia/ | GET,POST | ia.index | ia.view | sim | operacional / leitura e criação de interação (POST) | admin, tecnico, trabalhador | src/app/blueprints/ia/routes.py:35 |
| /mapa/ | GET | mapa.index | mapa.view | sim | operacional / leitura | admin, tecnico, trabalhador | src/app/blueprints/mapa/routes.py:66 |
| /mapa/dados | GET | mapa.dados | mapa.view | sim | operacional / leitura | admin, tecnico, trabalhador | src/app/blueprints/mapa/routes.py:81 |
| /mapa/glebas/<int:gleba_id>/poligono | POST | mapa.salvar_poligono | mapa.edit | sim | operacional / edição polígono | admin, tecnico | src/app/blueprints/mapa/routes.py:100 |
| /mapa/glebas/<int:gleba_id>/poligono/limpar | POST | mapa.limpar_poligono | mapa.edit | sim | operacional / edição polígono | admin, tecnico | src/app/blueprints/mapa/routes.py:130 |
| /propriedades/ | GET | propriedades.index | propriedades.view | sim | operacional / leitura | admin, tecnico, trabalhador | src/app/blueprints/propriedades/routes.py:46 |
| /propriedades/selecionar | GET,POST | propriedades.selecionar | propriedades.select | sim | seleção / sessão | admin, tecnico, trabalhador | src/app/blueprints/propriedades/routes.py:53 |
| /propriedades/nova | GET,POST | propriedades.nova | propriedades.create | sim | criação | admin, tecnico | src/app/blueprints/propriedades/routes.py:76 |
| /propriedades/<int:propriedade_id> | GET | propriedades.detalhe | propriedades.view | sim | operacional / leitura | admin, tecnico, trabalhador | src/app/blueprints/propriedades/routes.py:105 |
| /propriedades/<int:propriedade_id>/editar | GET,POST | propriedades.editar | propriedades.edit | sim | edição | admin, tecnico | src/app/blueprints/propriedades/routes.py:112 |
| /propriedades/<int:propriedade_id>/remover | POST | propriedades.remover | propriedades.edit | sim | exclusão bloqueada (409) | admin, tecnico | src/app/blueprints/propriedades/routes.py:140 |
| /relatorios/ | GET | relatorios.index | relatorios.view | sim | operacional / leitura | admin, tecnico, trabalhador | src/app/blueprints/relatorios/routes.py:76 |
| /relatorios/geral | GET | relatorios.geral | relatorios.view | sim | operacional / leitura | admin, tecnico, trabalhador | src/app/blueprints/relatorios/routes.py:89 |
| /relatorios/financeiro | GET | relatorios.financeiro | relatorios.view + financeiro.view | sim | operacional / leitura | admin, tecnico | src/app/blueprints/relatorios/routes.py:99 |
| /relatorios/agricola | GET | relatorios.agricola | relatorios.view | sim | operacional / leitura | admin, tecnico, trabalhador | src/app/blueprints/relatorios/routes.py:119 |
| /relatorios/aplicacoes | GET | relatorios.aplicacoes | relatorios.view | sim | operacional / leitura | admin, tecnico, trabalhador | src/app/blueprints/relatorios/routes.py:128 |
| /relatorios/uploads | GET | relatorios.uploads | relatorios.view | sim | operacional / leitura | admin, tecnico, trabalhador | src/app/blueprints/relatorios/routes.py:148 |
| /relatorios/geral/exportar.csv | GET | relatorios.geral_exportar_csv | relatorios.view | sim | exportação / leitura | admin, tecnico, trabalhador | src/app/blueprints/relatorios/routes.py:175 |
| /relatorios/geral/exportar.pdf | GET | relatorios.geral_exportar_pdf | relatorios.view | sim | exportação / leitura | admin, tecnico, trabalhador | src/app/blueprints/relatorios/routes.py:185 |
| /relatorios/financeiro/exportar.csv | GET | relatorios.financeiro_exportar_csv | relatorios.view + financeiro.view | sim | exportação / leitura | admin, tecnico | src/app/blueprints/relatorios/routes.py:196 |
| /relatorios/financeiro/exportar.pdf | GET | relatorios.financeiro_exportar_pdf | relatorios.view + financeiro.view | sim | exportação / leitura | admin, tecnico | src/app/blueprints/relatorios/routes.py:212 |
| /relatorios/agricola/exportar.csv | GET | relatorios.agricola_exportar_csv | relatorios.view | sim | exportação / leitura | admin, tecnico, trabalhador | src/app/blueprints/relatorios/routes.py:227 |
| /relatorios/agricola/exportar.pdf | GET | relatorios.agricola_exportar_pdf | relatorios.view | sim | exportação / leitura | admin, tecnico, trabalhador | src/app/blueprints/relatorios/routes.py:237 |
| /relatorios/aplicacoes/exportar.csv | GET | relatorios.aplicacoes_exportar_csv | relatorios.view | sim | exportação / leitura | admin, tecnico, trabalhador | src/app/blueprints/relatorios/routes.py:247 |
| /relatorios/aplicacoes/exportar.pdf | GET | relatorios.aplicacoes_exportar_pdf | relatorios.view | sim | exportação / leitura | admin, tecnico, trabalhador | src/app/blueprints/relatorios/routes.py:262 |
| /relatorios/uploads/exportar.csv | GET | relatorios.uploads_exportar_csv | relatorios.view | sim | exportação / leitura | admin, tecnico, trabalhador | src/app/blueprints/relatorios/routes.py:277 |
| /relatorios/uploads/exportar.pdf | GET | relatorios.uploads_exportar_pdf | relatorios.view | sim | exportação / leitura | admin, tecnico, trabalhador | src/app/blueprints/relatorios/routes.py:287 |
| /upload/ | GET | upload.index | upload.view | sim | operacional / leitura | admin, tecnico, trabalhador | src/app/blueprints/upload/routes.py:151 |
| /upload/novo | GET,POST | upload.novo | upload.create | sim | criação | admin, tecnico, trabalhador | src/app/blueprints/upload/routes.py:164 |
| /upload/<int:arquivo_id>/download | GET | upload.download | upload.download | sim | download / leitura | admin, tecnico, trabalhador | src/app/blueprints/upload/routes.py:206 |
| /upload/<int:arquivo_id>/remover | POST | upload.remover | upload.delete | sim | exclusão | admin | src/app/blueprints/upload/routes.py:226 |
| /usuarios/ | GET | usuarios.index | usuarios.view | sim | administrativa / leitura | admin, tecnico | src/app/blueprints/usuarios/routes.py:296 |
| /usuarios/novo | GET,POST | usuarios.novo | usuarios.create | sim | administrativa / gestão | admin, tecnico | src/app/blueprints/usuarios/routes.py:350 |
| /usuarios/novo/gerente | GET,POST | usuarios.novo_gerente | usuarios.create | sim | administrativa / gestão | admin, tecnico | src/app/blueprints/usuarios/routes.py:358 |
| /usuarios/novo/trabalhador | GET,POST | usuarios.novo_trabalhador | usuarios.create | sim | administrativa / gestão | admin, tecnico | src/app/blueprints/usuarios/routes.py:366 |
| /usuarios/<int:usuario_id>/reenviar-convite | POST | usuarios.reenviar_convite | usuarios.edit | sim | administrativa / gestão | admin, tecnico | src/app/blueprints/usuarios/routes.py:508 |
| /usuarios/<int:usuario_id>/editar | GET,POST | usuarios.editar | usuarios.edit | sim | administrativa / gestão | admin, tecnico | src/app/blueprints/usuarios/routes.py:537 |
| /usuarios/<int:usuario_id>/inativar | POST | usuarios.inativar | usuarios.deactivate | sim | administrativa / gestão | admin, tecnico | src/app/blueprints/usuarios/routes.py:626 |
| /health | GET | health | — | não | pública / health | todos/publica | src/app/__init__.py:78 |
| /static/<path:filename> | GET | static | — | não | pública / recurso estático Flask | todos/publica | Flask static:0 |


### Evidência complementar de interface

Resumo em `/tmp/connectagro-stage4/ui-summary.md`; resultados, persistência e
screenshots em `/tmp/connectagro-stage4-ui-zzib_ksg/`. Foram validados login e
navegação reais dos três perfis, detalhes financeiros negados para Trabalhador,
agregados preservados em HTML/CSV/PDF e IA/histórico, convite/reenvio por Gerente
com CSRF e envio SMTP suprimido, CRUD de equipe e auditoria por Administrador.
Sem overflow nas telas verificadas em desktop 1440px e celular 390px. Tokens e
e-mails integrais não foram impressos nem encontrados nas descrições dos logs.
