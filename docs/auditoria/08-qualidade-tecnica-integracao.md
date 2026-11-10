# Etapa 08 — Qualidade técnica e integração contínua

Data de referência: 10/11/2026, America/Sao_Paulo.
Repositório oficial: https://github.com/Helio965/Connectagro.

**Estado técnico:** Etapa 08 recuperada e validada. A suíte completa repetida
após a recuperação passou em **1.399 testes**, sem falhas, erros, ignorados ou
avisos, em **349,79 s**, exit 0, com depreciações tratadas como erro. Navegador
e PostgreSQL também foram revalidados. A publicação do commit final e seu
SHA são confirmados na entrega; este relatório registra a revisão técnica
anterior ao commit. A `main` não recebeu merge.

## A. Recuperação de contexto

A base foi recuperada do GitHub no checkout existente
`/workspace/Connectagro`, sem criar segunda cópia ou recomeçar funcionalidades.
O fetch inicial abrangia apenas `main`; a consulta de refs revelou as branches
publicadas das Etapas 01–07. Elas foram buscadas explicitamente antes da troca
de branch. A árvore inicial estava limpa.

| Etapa | Commit publicado |
| --- | --- |
| 01–03 | `70310c00b188af056528fc69b15dfdfca96cb4de` |
| 04 — permissões | `7cb745687af9431857cbe77a53fd3cc145cda0d1` |
| 05 — território | `20b3fad8cbc6398d8adb123655bdf66141fc62a4` |
| 06 — operações | `34e7749fd5318e66aa358757f2527a2df0150f1d` |
| 07 — catálogo | `3fdfaf06644b713ba76678f26d56baecabbf9d91` |

Foi criada `codex/etapa-08-qualidade-integracao` a partir de
`origin/codex/etapa-07-catalogo-global-local`, no último commit da tabela.
A `main`, em `92273e2b3a4bdb6db4dc0a3b74b003ec702777d8`,
não foi usada como base de desenvolvimento.

Os sete relatórios `docs/auditoria/01` a `07` foram lidos na auditoria
distribuída, junto com README, visão geral, regras de negócio, DER, dicionário,
arquitetura técnica, documentação do catálogo e dos testes. As afirmações
históricas foram comparadas com os modelos, serviços, rotas e testes atuais;
os números antigos não foram tratados como novas execuções.

O ambiente executado é Linux, Python 3.12.14 e ambiente virtual `.venv`.
As dependências foram instaladas a partir de `requirements.txt`; Shapely,
acrescentado na Etapa 05, continuou necessário. Não se recuperaram credenciais
do ambiente antigo nem se usaram Supabase, SMTP ou banco de produção.

### Interrupção e recuperação do executor

A plataforma retornou `No usable execution environment` durante a conclusão
da etapa. O estado de conexão da interface não foi usado como prova de
disponibilidade do terminal. Na retomada, comandos reais confirmaram novamente
o checkout, a branch e o HEAD da Etapa 07, bem como as alterações locais da
Etapa 08 e os artefatos temporários de validação.

Foram preservados o workflow, as correções Python, os novos testes, os ajustes
documentais, os logs/XML da linha de base e da suíte final e as evidências
PostgreSQL/navegador. Não se usaram reset destrutivo, limpeza de arquivos ou
reescrita dos commits anteriores. Não havia commit final da Etapa 08 a
substituir. Este relatório ainda não existia e foi escrito com os fatos
recuperados.

Para preservar imediatamente o trabalho, foi criado o commit intermediário
`e4a4991bc86f9c4f74ff2e694227ed0c88d0d910` e publicado na branch
`codex/recuperacao-etapa-08-em-validacao`. O SHA remoto coincidiu com o
local. A branch final também contém esse commit, sem reescrever a base da
Etapa 07; ele é uma preservação em validação, não a entrega final.

Antes da falha já estavam validados a linha de base, os cenários de navegador
e PostgreSQL e as correções específicas. A suíte final havia sido iniciada,
mas seu resultado ainda não era conhecido na comunicação de interrupção.
O log/XML recuperado comprovou posteriormente sua conclusão: 1.399 aprovados,
zero avisos, exit 0. Essa é uma execução iniciada antes da falha,
**não** uma repetição feita após a recuperação. A nova rodada completa
pós-recuperação passou em 1.399 testes, zero falhas/erros/ignorados/avisos,
em 349,79 s, exit 0. O navegador foi repetido
após a retomada: 85 checks aprovados, zero pageerrors e os mesmos 237 hashes de
fontes verificados. A nova evidência está em
`/tmp/connectagro-stage8-browser/run-lt0fwale/`.

## B. Diagnóstico inicial

A linha de base foi executada antes das alterações:

```bash
.venv/bin/python -m compileall -q src tests
.venv/bin/python -m pytest -q --junitxml=/tmp/connectagro-etapa08-baseline.xml
```

Resultado: **1.362 aprovados**, zero falhas, erros ou ignorados, **364 avisos**,
**361,56 s**, exit 0. Os avisos apontavam para
`migrations/env.py`, no uso depreciado de `get_engine()`.
A instalação não impediu estabelecer a situação real do projeto.

| Problema comprovado | Severidade e efeito |
| --- | --- |
| API depreciada do engine nas migrations | Média, compatibilidade: 364 avisos na suíte; API marcada para remoção |
| Uso concorrente do mesmo token de senha/convite | Alta, segurança: duas transações podiam aceitar a leitura inicial e disputar a senha; uso único precisava ser garantido na escrita |
| Relações carregadas individualmente no relatório operacional | Média, desempenho: dez atividades distintas exigiam 43 SELECTs durante a montagem do relatório |
| Datas civis impossíveis nos relatórios financeiro/aplicações | Média, correção: `2026-02-30` gerava HTML, CSV e PDF com status 200 |
| Ordem de persistência/remoção de uploads | Alta, integridade: falha SQL podia deixar arquivo sem registro ou remover o conteúdo de um registro cujo delete fosse desfeito |

Não houve reescrita geral, novo módulo agrícola ou alteração dos IDs internos
dos perfis `admin`, `tecnico` e `trabalhador`.

## C. Arquitetura

A aplicação permanece um monólito Flask com Application Factory,
renderização Jinja2, 20 blueprints, 103 regras de rota e 25 tabelas de domínio.
O metadata declara 52 chaves estrangeiras. Não foi introduzido framework,
serviço externo ou arquitetura alternativa.

As responsabilidades continuam separadas entre rotas, serviços, modelos,
helpers de identidade/contexto/permissão, templates e JavaScript local:

- Autenticação valida a conta e a versão de sessão no banco; contexto deriva
  de vínculo ativo e seleção autorizada.
- Propriedade é o ambiente administrativo; Gleba é Área de Plantio vinculada.
  Culturas e associações mantêm seus relacionamentos históricos.
- Aplicações e colheitas continuam distintas de atividades gerais e seus itens.
  Dose, consumo efetivo, autoria, responsável e custo têm semânticas próprias.
- Catálogo global é independente das propriedades; produtos locais,
  personalizações, revisões e solicitações preservam contexto e histórico.
  A autoridade global optativa não concede acesso operacional à origem.
- Mapas usam GeoJSON e Shapely/GEOS no backend e Leaflet/Draw locais no frontend.
- Relatórios e exportações consultam os mesmos serviços; a IA permanece
  simulada e não inclui custos individuais nos registros acessíveis ao Trabalhador.

Foram analisadas validações repetidas, relações ORM, tratamento de erros,
fronteiras transacionais e dependências. A refatoração ficou restrita aos
problemas reproduzidos. Listagens sem paginação e agregações que carregam o
conjunto completo foram registradas como limite de escala; não se alterou o
contrato de totais/exportações nem se criaram índices especulativos.

## D. Refatorações e correções

| Arquivo | Alteração e garantia |
| --- | --- |
| `migrations/env.py` | Usa `.engine`, API compatível com o Flask-SQLAlchemy >=3.1 declarado; mantém roteamento e escaping das URLs |
| `src/app/services/password_reset_service.py` | Consumo condicional de token ainda não usado, lock da conta no PostgreSQL, nova leitura de estado e commit conjunto de token/senha/epoch |
| `src/app/services/relatorios_service.py` | Validação civil ISO compartilhada e eager loading das relações escalares consumidas pelo DTO |
| `src/app/blueprints/upload/routes.py` | Limpeza do arquivo após falha de criação SQL; delete físico somente após confirmação SQL; falhas de armazenamento/limpeza com resposta controlada |

O hash da nova senha é calculado antes do lock; a validade, o estado da conta
e o token são revalidados depois da espera. O UPDATE de consumo exige
`usado=False`; somente uma transação pode confirmar o uso do mesmo token.
O mapper de `Usuario` continua responsável pela revogação de sessões.
Falhas posteriores desfazem consumo, senha e epoch juntos.

No upload, rollback de exclusão preserva o documento original. Falha na
limpeza posterior ao commit deixa um resíduo privado e gera indicação ao
administrador, sem reconstruir um registro já removido ou expor caminhos
no log. Erro de gravação é tratado sem criar metadados de sucesso.

Não foram modificados modelos, revisões históricas, contratos válidos de
relatório, fichas técnicas, seeds ou IDs para obter aprovação nos testes.

## E. Banco de dados, migrations e relacionamentos

Há uma cadeia única, sem novo head ou nova migration nesta etapa:

```text
97642b24c238 → e3e72eacc334 → b4f2c9d8a1e7 → c2a83e4f9b10
→ d3b94f5a0c21 → e4ca60b1d732 → f6a28d9c104e → g7c53b8e19a2
```

O upgrade de banco vazio, o upgrade de bases populadas, as FKs, as projeções
históricas e a comparação schema/metadata foram exercitados em bases
descartáveis. Os testes antigos de migrations continuam ativos. Testes novos
executam upgrade/check reais com `DeprecationWarning` convertido em erro.

SQLite mantém o engine da aplicação mesmo com `DIRECT_URL` diferente.
PostgreSQL real validou uma URL direta distinta: somente o banco destinado
às migrations foi atualizado e o banco da aplicação permaneceu intacto.
O teste PostgreSQL offline cobre geração de SQL/escaping, e é identificado
como offline; não substitui a validação PostgreSQL online.

A validação PostgreSQL preservou as 20 tabelas históricas, os valores decimais,
o default falso da capacidade global e as restrições de FK. Verificou
idempotência de upgrade, ausência de drift e bloqueios de downgrade com
capacidade/proveniência preenchidas e histórico local inativo. Não se
reescreveram migrations publicadas nem se executaram operações em banco real.

As proteções recentes contra perda em downgrade permanecem. Revisões legadas
não possuem todas as guardas introduzidas nas etapas novas; isso não foi
convertido em revisão retroativa de arquivos publicados. Backup verificável,
cópia de validação e janela de manutenção continuam necessários antes de
mudanças estruturais.

## F. Segurança, transações e concorrência

Foram revalidados login/logout, recuperação/convite, revogação de sessão,
contas inativas, os três perfis, contexto, vínculos, CSRF, dados financeiros,
uploads/downloads e governança global. Os testes mantêm negativas por perfil,
IDs externos, estado e tentativas de forjar autoridade.

Os locks operacionais continuam por Propriedade, antes de carregar e validar
os objetos de escrita. PostgreSQL usa `FOR UPDATE`; SQLite reserva a escrita.
Após esperar, a identidade, epoch, perfil e vínculo são relidos. As operações
e a auditoria transacional dos módulos novos permanecem atômicas.

Governança mantém a ordem catálogo → Propriedade de origem → conta do revisor.
Seed e publicação usam a mesma coordenação global; nenhum caminho inverso
confirmado foi introduzido. As cinco corridas PostgreSQL observaram waiters
reais e cobriram aprovação repetida, revogação do aprovador, revogação do
vínculo local, custo concorrente e seed/publicação. As 16 verificações dessas
corridas passaram.

Uma regressão SQLite versionada confirmou que revogar a capacidade global
durante a espera impede publicação: 403, solicitação ainda pendente e nenhum
produto global novo. A autoridade de publicação não criou vínculo nem acesso
à Propriedade da solicitação.

Duas corridas adicionais PostgreSQL, separadas do total de 82 verificações,
confirmaram uso único do mesmo token de reset e do mesmo token de convite.
Em cada corrida houve exatamente um sucesso, senha correspondente ao vencedor,
epoch incrementado e replay recusado. SQLite possui regressões equivalentes,
além de inativação/expiração durante o cálculo do hash e rollback de falha.

## G. Desempenho

O N+1 foi medido em SQLite em memória com sessões limpas e listener SQLAlchemy
apenas durante `montar_relatorio_operacional`. Cada atividade usava uma Área,
Cultura/associação e produto distintos, evitando que o identity map ocultasse
o problema.

| Carga | Antes | Depois |
| --- | --- | --- |
| Uma atividade | 7 SELECTs | 3 SELECTs |
| Dez atividades | 43 SELECTs | 3 SELECTs |

A correção antecipa somente as relações escalares usadas na montagem do DTO.
Não altera escopo, precisão, unidades, totalização, campos financeiros ou
permissões. A regressão compara crescimento de consultas para atividades e
aplicações, com e sem custos, e verifica conteúdo/valores retornados.

No PostgreSQL descartável, dez atividades com autoria exigiram quatro
SELECTs e mantiveram quantidades/custos exatos. Não se apresenta redução
de tempo ou carga de produção sem medição correspondente.

## H. Dependências e instalação

O arquivo `requirements.txt` não foi alterado. Não houve atualização geral
de bibliotecas. Versões observadas neste ambiente:

| Componente | Versão |
| --- | --- |
| Python | 3.12.14 |
| Flask | 3.1.3 |
| Flask-SQLAlchemy / SQLAlchemy | 3.1.1 / 2.1.8 |
| Flask-Migrate / Alembic | 4.1.0 / 1.20.1 |
| Shapely | 2.2.0 |
| psycopg2-binary | 2.9.13 |
| pytest | 9.2.0 |

Shapely requer Python compatível; o projeto documenta Python 3.11+ e o fluxo
verificado nesta etapa usa 3.12. O driver PostgreSQL, Pillow/ReportLab e as
bibliotecas de mapa foram mantidos. `pip check` verifica consistência das
dependências instaladas, sem representar auditoria de vulnerabilidades.

Não há lockfile; uma instalação limpa futura pode resolver versões novas
dentro das faixas declaradas. Esse limite é documentado, sem inventar
reprodutibilidade binária. Windows não foi executado; disponibilidade de wheel
não é resultado de teste nativo nesse sistema.

## I. Frontend e documentação

O navegador real usou Flask, SQLite descartável, CSRF e Leaflet/Leaflet.draw
locais, sem substituir as bibliotecas por mocks. Foram verificadas navegação,
formulários, desenho/salvamento de polígono, atividade/custos, catálogo local e
proposta, publicação global, uploads/downloads, relatórios e exportações.

As seis telas verificadas em celular — dashboard, mapa, atividades, catálogo
local, relatório operacional e usuários — não apresentaram overflow horizontal,
e o menu abriu/fechou. Os perfis e o aprovador global foram exercitados. Houve
zero `pageerror` não tratado nos 85 checks aprovados.

As imagens cartográficas OpenStreetMap continuaram bloqueadas pelo proxy.
O teste comprovou o editor e os vetores com os assets locais, e o fallback
para falha cartográfica; não comprovou disponibilidade dos tiles externos.

README, visão geral, DER, dicionário e guia de testes foram ajustados para
distinguir o MVP histórico das Etapas 01–07, documentar instalação/CI e corrigir
afirmações obsoletas sobre contagem de tabelas, contexto, seed e mapa. Não se
transformaram entregas acadêmicas do Projeto Integrador I em funcionalidades
novas do produto. A arquitetura e as regras aprovadas foram preservadas.

## J. Integração contínua

Foi criado `.github/workflows/tests.yml`, inexistente na base recuperada.
Ele executa em Pull Requests e pushes para `main` e `codex/**`, com:

- Ubuntu, Python 3.12 e Node.js 22 para verificação de sintaxe;
- permissões `contents: read`, checkout sem persistência de credenciais,
  actions fixadas por SHA e timeout de 15 minutos;
- instalação de `requirements.txt` e `pip check`;
- `compileall`, `node --check` nos cinco scripts de produto e conferência
  de tamanho/SHA-256 dos 19 assets oficiais Leaflet/Draw;
- a suíte pytest completa, que inclui migrations e concorrência SQLite reais.

Não há deploy, segredo de produção, SMTP ou conexão Supabase. PostgreSQL e
navegador foram validados separadamente nesta etapa e não são jobs automáticos
desse workflow. A configuração e os comandos foram revisados localmente.
As actions v6 fixadas usam runtime Node 24; o Node 22 selecionado no job é o
interpretador dos checks JavaScript do projeto. Foram conferidos tags/SHAs e
`action.yml` oficiais de checkout 6.1.0, setup-python 6.3.0 e setup-node 6.5.0.
O workflow passou no actionlint 1.7.7, obtido de release oficial com checksum
verificado. Os checks locais foram repetidos após recuperar o executor.

Após a publicação da branch intermediária, a página pública do GitHub Actions
respondeu HTTP 200 e exibiu a execução real
[`42914165448`](https://github.com/Helio965/Connectagro/actions/runs/42914165448),
acionada pelo push e ainda **In progress** no momento da consulta.
Isso confirma o acionamento remoto, mas **não** um resultado remoto aprovado.
A API continuou bloqueada; a confirmação foi feita pela página pública.

## K. Testes e evidências

Os totais abaixo descrevem execuções distintas; verificações de navegador e
PostgreSQL não são somadas à contagem pytest.

| Execução | Resultado efetivamente confirmado |
| --- | --- |
| Linha de base antes das alterações | 1.362 aprovados; zero falhas/erros/ignorados; 364 avisos; 361,56 s; exit 0 |
| Suíte completa iniciada antes da interrupção, resultado recuperado | 1.399 aprovados; zero falhas/erros/ignorados/avisos; 376,66 s; exit 0 |
| Repetição completa após recuperação | **1.399 aprovados; zero falhas/erros/ignorados/avisos; 349,79 s; exit 0**, com `-W error::DeprecationWarning` |
| Relatórios novos + suites de relatório/exportações existentes | 155 aprovados; 59,49 s; exit 0 |
| Corrida versionada de autoridade global SQLite | 1 aprovado; 0,34 s; exit 0 |
| Navegador real | 85 verificações aprovadas; zero pageerrors |
| Navegador repetido após recuperação | 85 verificações aprovadas; zero pageerrors; 237 hashes de fontes conferidos |
| PostgreSQL 16.15 real descartável | 82 verificações: 51 migrations + 16 concorrência em cinco corridas + 15 relatórios/uploads |
| PostgreSQL repetido após recuperação | 82 verificações aprovadas e duas corridas de token aprovadas; contêiner, volumes e bancos descartáveis removidos |
| Consumo concorrente de tokens PostgreSQL | Duas corridas adicionais: reset e convite; um vencedor em cada |
| Compilação, sintaxe JS e integridade de dependências/assets | Repetidas após recuperação: compileall, cinco scripts JS, pip check, 19 assets e actionlint passaram |

A suíte final contém 37 casos adicionais em relação à linha de base, sem
remoção de testes anteriores para obter sucesso. As coberturas novas estão em
`test_migrations_runtime.py`, `test_password_reset_concorrencia.py`,
`test_relatorios_qualidade.py`, `test_catalogo_concorrencia.py` e nos casos
acrescentados a `test_upload_crud.py`.

Rastreabilidade dos requisitos de teste solicitados, sem afirmar que cada
rótulo corresponde a um único teste:

| Cenários | Evidência |
| --- | --- |
| T01–T02 | Factory, registro dos blueprints, health e inicialização real |
| T03–T07 | Suites de migrations SQLite, runtime sem depreciação e PostgreSQL online/offline distinguidos |
| T08–T14 | Autenticação, epoch, perfis, vínculos, contexto e CSRF nas suites e no navegador |
| T15–T16 | Geometria/território, APIs e editor real com Leaflet/Draw locais |
| T17–T19 | Atividades, responsáveis, dose/consumo/custos e preservação de aplicações/colheitas |
| T20–T24 | Catálogo global/local, autoridade explícita, seed e históricos |
| T25–T26 | Corridas SQLite versionadas e cinco corridas PostgreSQL de operações/catálogo |
| T27–T30 | Relatórios, CSV/PDF, auditoria e uploads/downloads, com negativas e falhas transacionais |
| T31–T34 | Compileall, node --check, pip check, manifesto dos assets e revisão do workflow |
| T35 | Suíte final completa e repetição pós-recuperação aprovadas, com 1.399 testes em cada rodada |

Comandos da raiz do checkout:

```bash
.venv/bin/python -m compileall -q src tests
.venv/bin/python -m pip check
for script in src/app/static/js/*.js; do node --check "$script"; done
.venv/bin/python -m pytest -q -W error::DeprecationWarning --junitxml=/tmp/connectagro-etapa08-recovery-final.xml
git diff --check
```

Evidências locais recuperadas, mantidas fora do commit:

- `/tmp/connectagro-etapa08-baseline.{xml,log}`;
- `/tmp/connectagro-etapa08-final.{xml,log}`;
- `/tmp/connectagro-stage8-browser/run-0x52gpr3/result.json`, logs e screenshots;
- `/tmp/connectagro-stage8-browser/run-lt0fwale/result.json`, da repetição após recuperação;
- `/tmp/connectagro-stage8-pg/summary.json`, `migration-results.json`,
  `concurrency-results.json`, `report-results.json` e `token-races-fixed.json`;
- `/tmp/connectagro-stage8-pg-recovery-20261110T222513Z/*results.json`,
  evidências da repetição PostgreSQL após a recuperação;
- `/tmp/connectagro-etapa08-recovery-final.{xml,log}`, da repetição completa após recuperação.

O PostgreSQL e seus bancos descartáveis da primeira rodada foram removidos
após a validação, conforme `summary.json`. A repetição PostgreSQL
pós-recuperação também passou; contêiner, volumes e bancos temporários foram removidos.
Não se executaram migrations ou testes em banco
de produção. Arquivos temporários, SQLite, uploads, logs e credenciais não
integram o delta de código.

## L. Compatibilidade preservada

Continuam implementadas as Etapas 01–07: autenticação e revogação,
gerenciamento/seleção de Propriedades, permissões, território/polígonos,
operações com autoria/quantidade/custo/histórico, catálogo local/global e sua
governança. As APIs válidas e os identificadores históricos não foram migrados.

Não se renomeou `tecnico`; a interface mantém Gerente de Plantio. O
Trabalhador não recebe detalhe financeiro/equipe nem autorização de editar
polígono ou publicar globalmente. A publicação global não amplia vínculos
territoriais. Produtos locais continuam fora das FKs globais operacionais.

O catálogo não afirma validação regulatória oficial, recomendação agronômica,
venda ou preço consolidado. A IA continua simulada, sem serviço externo.
As regras de áreas informadas e geometrias independentes permanecem distintas.

## M. Pendências e limites

- Áreas de Plantio independentes dependem de decisões de modelagem, contexto e
  autorização; não foram implementadas nesta etapa.
- Uso operacional de produtos locais, fotos privadas específicas, revisão
  regulatória externa, preços consolidados e alterações globais de
  identidade/status/ficha técnica continuam fora do fluxo implementado.
- A política global de FKs SQLite continua a anterior. Testes específicos
  ativam/verificam FKs quando necessário; não se afirma que toda conexão
  SQLite da aplicação passou a impor essas restrições.
- A correção de tokens garante consumo único do **mesmo token**. A emissão
  concorrente de tokens distintos para uma conta não foi serializada nesta
  etapa e permanece como análise específica futura.
- Não existe transação distribuída entre filesystem e banco. Compensações
  tratam falhas observadas no fluxo normal; crash abrupto entre gravação SQL
  e limpeza de arquivo ainda pode deixar resíduos privados, exigindo
  reconciliação operacional.
- Revisões legadas de downgrade não receberam todas as guardas recentes;
  não se deve interpretar os testes como autorização para reversão destrutiva.
- Listagens e relatórios completos continuam sujeitos a limites de escala;
  paginação e mudanças de contrato precisam de avaliação própria.
- Tiles OpenStreetMap permanecem bloqueados. Leaflet/Draw locais funcionam;
  cartografia externa disponível não foi validada.
- A API GitHub retornou Forbidden no ambiente observado. Git nativo publicou
  a preservação intermediária; as páginas públicas permitiram confirmar
  Actions em andamento e zero PRs abertos (50 fechados) na consulta. O
  resultado final remoto e eventual PR ainda dependem de confirmação.
- Windows nativo, Supabase e SMTP real não foram testados. Não foram usados
  bancos ou contas de produção.

## N. Preparação para integração

O histórico confirma commits consecutivos das Etapas 01–07; a `main`
observada é ancestral da Etapa 07. O delta da Etapa 08 deve ser revisado contra
`codex/etapa-07-catalogo-global-local`, e não apresentado como se os commits
anteriores fossem exclusivos desta etapa.

A estratégia recomendada é revisar a cadeia base01–03 → 04 → 05 → 06 → 07 →
08, preservando seus commits e migrations. A integração futura com a `main`
deve ocorrer somente após aprovação específica, estado remoto atualizado e
CI concluída. Não é necessário reexecutar cherry-picks de commits que já
fazem parte da mesma cadeia; isso duplicaria o histórico.

A relação ancestral demonstra compatibilidade do histórico observado, mas
não substitui uma nova análise se `main` ou a base remota avançarem. A
simulação `git merge-tree origin/main HEAD` terminou com exit 0, sem conflitos,
sem atualizar refs ou fazer merge. As consultas remotas mantiveram `main` no
SHA `92273e2b3a4bdb6db4dc0a3b74b003ec702777d8` e Etapa 07 no
SHA `3fdfaf06644b713ba76678f26d56baecabbf9d91`. A comparação e eventual PR
desta etapa usam Etapa 07 como base e Etapa 08 como
head. Não houve merge automático nem atualização da `main`.

O commit intermediário publicado em A preserva as 15 alterações de código,
testes, CI e documentação revisadas. O commit final acrescenta este relatório,
com a mensagem `refactor: concluir auditoria tecnica e integracao continua - etapa 08`.
Não se reescreve o commit intermediário. A entrega informa o SHA final e a
confirmação de `git ls-remote`; um relatório não pode incluir seu próprio
hash futuro antes de ser commitado.

Comparação exclusiva da Etapa 08, para revisão e eventual abertura de PR:
https://github.com/Helio965/Connectagro/compare/codex/etapa-07-catalogo-global-local...codex/etapa-08-qualidade-integracao?expand=1

Depois de aprovada a revisão desta etapa, a branch acumulada pode ser proposta
à `main`, preservando a cadeia original e revalidando seu estado remoto. A
aprovação da Etapa 08 não autoriza executar esse merge.

## O. Conclusão

O trabalho da Etapa 08 foi recuperado e preservado em controle de versão.
Cinco problemas comprovados receberam correções localizadas. A repetição
integral após a recuperação confirmou 1.399 testes aprovados e zero avisos;
navegador e PostgreSQL também passaram novamente. O CI está configurado,
validado localmente e seu acionamento remoto foi observado.

O código está preparado para a revisão da Etapa 09, mantendo as pendências
de produto e os limites descritos em M. O resultado remoto final de Actions
deve ser conferido na entrega e no GitHub antes de integrar a `main`.
A publicação da branch final é confirmada separadamente na entrega, sem
confundi-la com merge ou publicação do ambiente na nuvem.

## Inventário exclusivo da Etapa 08

16 arquivos em relação à Etapa 07 publicada; bancos, logs, uploads, credenciais
e harnesses temporários de diagnóstico não integram os commits:

```text
.github/workflows/tests.yml
README.md
docs/00-visao-geral.md
docs/04-modelagem-banco-der.md
docs/05-dicionario-de-dados.md
docs/auditoria/08-qualidade-tecnica-integracao.md
migrations/env.py
src/app/blueprints/upload/routes.py
src/app/services/password_reset_service.py
src/app/services/relatorios_service.py
tests/README.md
tests/test_catalogo_concorrencia.py
tests/test_migrations_runtime.py
tests/test_password_reset_concorrencia.py
tests/test_relatorios_qualidade.py
tests/test_upload_crud.py
```
