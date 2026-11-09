# Etapa 06 — Registros operacionais agrícolas

Implementação iniciada em 08/11/2026; recuperação e conclusão em 09/11/2026,
America/Sao_Paulo. Execução em Linux/Python 3.12.14, ambiente virtual existente.
Resultados finais são registrados na seção J.

## A. Diagnóstico inicial

A base efetivamente conferida foi a Etapa 05, commit
`20b3fad8cbc6398d8adb123655bdf66141fc62a4`, publicada em
`codex/etapa-05-mapas-territorio`. Seus ancestrais são
`70310c00b188af056528fc69b15dfdfca96cb4de` (Etapas 01–03) e
`7cb745687af9431857cbe77a53fd3cc145cda0d1` (Etapa 04). A árvore estava limpa.
Foram verificados status, branches, log, remoto e fetch, antes de criar
`codex/etapa-06-registros-operacionais` a partir desse HEAD. A `main` antiga
não foi usada como base, nem recebeu merge.

Os cinco relatórios anteriores foram lidos integralmente na auditoria distribuída
dos componentes. Permanecem autenticação validada no banco, epoch de sessão,
vínculos ativos, contexto selecionado, permissões, CSRF, auditoria e mapas.
Os 97 testes iniciais de aplicações, colheita, relatórios e permissões passaram
antes da implementação (23,74 s; `/tmp/connectagro-stage6/baseline.xml`).

| Componente | Funcionamento reaproveitado | Limitação comprovada e evolução |
| --- | --- | --- |
| `AplicacaoInsumo` e CRUD | Produto catalogado, Cultura↔Área, dose, data, texto de executor e observação | Sem autoria persistida, conta verificável, consumo ou custo; acrescentados campos opcionais |
| `ColheitaRegistro` e CRUD | Cultura↔Área e quantidade/unidade de colheita | Sem autoria/executor; acrescentada rastreabilidade sem converter quantidade antiga |
| `Gleba`, `Cultura`, `CulturaGleba` | Contexto territorial e bloqueios de exclusão com histórico | Bloqueios ampliados para atividades gerais, inclusive canceladas |
| `Usuario`, `UsuarioPropriedade` | Conta ativa e vínculo local como fonte de acesso | Reutilizados para validar executor; nenhuma conta criada automaticamente |
| `EquipeMembro` | Cadastro separado de equipe | Não equivale a uma conta nem concede autorização; não usado como FK de usuário |
| `ProdutoBase`, `ProdutoPreco` | Catálogo técnico e bloqueio por dois status | Preço de consulta não é custo; nenhum preço ou produto alterado pelo consumo |
| `FinanceiroLancamento` | Receitas/despesas locais | Não representa itens agrícolas; cálculos consolidados preservados sem lançamento automático |
| Relatórios/exportações | Consultas locais e arquivos em memória | Acrescentado histórico operacional com consumo e custos filtrados por permissão |
| IA local | Regras, consultas e agregados aprovados | Somente contagem/consumo novos; nenhum custo individual persistido em respostas |

Também foram comprovadas dose/colheita aceitando NaN/Infinity, datas apenas não
vazias, ID de produto sem limite antes do SQL e seleção ambígua após erro.
Esses caminhos foram corrigidos sem remover funcionalidades existentes.

## B. Decisões de modelagem

O usuário aprovou expressamente **atividades gerais**: Administrador gerencia
tudo, Gerente cria/edita, Trabalhador cria/visualiza. Isso resolveu a ausência de
permissões próprias na documentação anterior. A matriz em código acrescenta
`atividades.view/create/edit/delete` conforme essa decisão; nenhuma permissão
financeira foi ampliada.

`AplicacaoInsumo` e `ColheitaRegistro` são preservados: representam operações já
existentes, com dependências e permissões próprias. Não bastavam para registrar
uma atividade sem produto/cultura obrigatórios ou vários produtos na mesma
execução. Foram criadas apenas `AtividadeOperacional` e `AtividadeItem`.

O tipo/nome da atividade é texto livre de até 120 caracteres informado pelo
usuário. Não foi criado catálogo definitivo, classificação agronômica nem regra
de cultura obrigatória por nome. Atividades sem consumo podem ter zero itens;
quando há produtos, cada um é um item separado, até 20 itens ativos por formulário.

Não há cópia/backfill de aplicações para atividades, geração de aplicações pelos
itens ou sincronização entre fontes. Associação futura com aplicação existente
precisa definir fonte única, reconciliação e tratamento dos históricos antes de
ser implementada. O relatório identifica a origem e não fabrica registros.
Uma duplicação manual intencional entre módulos não é reconciliada automaticamente.

## C. Atividades operacionais

`/atividades/` lista o contexto autorizado; `/nova` registra;
`/<id>/editar` altera; `/<id>/cancelar` cancela logicamente. A atividade pertence
a `gleba_id` obrigatório. `cultura_gleba_id` é opcional e, quando informado, os
dois lados da associação precisam estar na Propriedade ativa e na mesma área.

IDs são limitados antes do SQL. Área/associação/item de outro ambiente não
podem ser vinculados por campos ocultos. Consultas também excluem associações
inconsistentes caso existam dados externos às rotas. Uma edição não transfere o
registro para outra Propriedade. Não se inventa uma Propriedade para área avulsa.

Toda validação é feita antes de modificar a atividade ou seus itens; a transação
persiste todos ou nenhum. Chave UUID única e comparação de conteúdo/contexto/autor
tornam reenvio idêntico idempotente. Reuso da chave com conteúdo/autor diferente
retorna 409. Os formulários legados passaram a enviar chave, mantendo compatibilidade
com clientes antigos sem esse campo; nesses clientes antigos a garantia de
idempotência não existe. Editar/cancelar depois pode tornar um reenvio antigo conflitante.

Cancelar atividade ou retirar item mantém linha, produto, quantidades e custos
históricos. Registros cancelados não voltam a ser editados/reativados pelas rotas.
Área/cultura/associação com atividades, mesmo canceladas, não pode ser apagada
ou desassociada. Exclusão administrativa anterior de aplicação/colheita foi
preservada, com auditoria atômica; não se introduziu cascade operacional.

## D. Responsáveis

`responsavel_usuario_id` é FK opcional para conta existente; `responsavel` guarda
a identificação histórica. Conta escolhida precisa estar globalmente ativa e
com vínculo ativo na Propriedade. Administrador/Gerente, com `equipe.view`,
selecionam contas locais; Trabalhador pode selecionar apenas a própria conta ou
usar texto, preservando o comportamento textual já aprovado. A interface não
expõe um diretório de contas/equipe ao Trabalhador.

O nome de uma conta escolhida é obtido do banco, não do texto forjado no POST.
Se uma conta histórica for inativada, manter o mesmo executor preserva FK/nome
existentes, sem revelar dados atuais de outra conta/contexto nem reativar acesso.
O sistema não reconcilia nomes antigos nem inventa executores para históricos.

`criado_por_id` vem exclusivamente da sessão validada. `criado_em` é preservado;
`data_execucao`/`data_aplicacao`/`data_colheita` representam execução, não cadastro.
Edição informa `atualizado_por_id`/`atualizado_em`, sem substituir o autor original.
Registros antigos continuam com autoria desconhecida quando não há evidência.

## E. Produtos e recursos

Cada item referencia `ProdutoBase`, sem copiar ou alterar sua ficha técnica.
Qualquer status `bloqueado_historico`, sistêmico ou regulatório, impede novo uso.
Item de atividade posteriormente bloqueado pode ser preservado integralmente
inalterado; não autoriza criar outro item nem aumentar consumo. A política
anterior de validação de produto nas aplicações continua vigente.

Não há recurso textual convertido em produto global, catálogo de recursos
externos, recomendação de produto, sugestão de dose ou validação agronômica.
Um mesmo produto em unidades distintas continua representado por itens distintos.

## F. Quantidades

Dose e unidade históricas da aplicação são preservadas. `quantidade_utilizada`
e `unidade_quantidade` registram separadamente o consumo efetivo conhecido.
Itens gerais também têm `dose`/`unidade_dose` opcionais. Não se calcula consumo
por hectares, dose ou área supostamente tratada.

Vírgula ou ponto decimal são aceitos sem separador de milhares. Valores novos
são positivos, finitos, até 12 dígitos inteiros e seis casas decimais; excesso
de precisão é recusado, sem arredondamento silencioso. Unidade é exigida quando
há quantidade. Ausência permanece NULL. A quantidade Float antiga de colheita
não foi convertida, mas novos envios não podem conter NaN/Infinity.

Agregação nova agrupa **produto + unidade exatamente informada**, sem converter
kg/L ou igualar grafias. `DecimalExato` mantém `Decimal` no Python, `NUMERIC`
no PostgreSQL e texto decimal canônico no SQLite, evitando conversão para REAL.
Não usar `SUM`/`CAST` numérico nas colunas textuais SQLite.

## G. Custos

`custo_unitario` e `custo_total` são opcionais e não negativos, com precisão
18/6 e 18/2. A moeda disponível é BRL, compatível com o financeiro existente.
Origem é `informado_usuario` ou `calculado_quantidade_unitario`, definida no
servidor. Não é aceito um preço de referência como custo automático.

O custo unitário refere-se à mesma unidade informada para consumo; não há
conversão. Com quantidade e custo unitário conhecidos, total é produto decimal
arredondado em centavos com `ROUND_HALF_UP`. Total explícito divergente é
recusado. Sem quantidade suficiente, custo unitário conhecido não fabrica total;
um total manual conhecido pode ser informado sem custo unitário. Zero é conhecido,
NULL é desconhecido. Moeda/origem também ficam NULL se não há custo.

Escrita exige `financeiro.create/edit` além da permissão operacional; leitura
individual exige `financeiro.view`. Gerente preserva custos ao editar dados
operacionais e não pode mudar sua base (produto, quantidade/unidade), nem retirar
item custeado. POST financeiro forjado é 403. Campos omitidos preservam dados;
campo explicitamente vazio pode ser limpo por quem possui autorização.

Não são criados lançamentos financeiros/contábeis, estoque ou operação comercial.
O relatório apresenta custos conhecidos separados dos totais de
`FinanceiroLancamento`; desconhecidos não viram zero nem despesa presumida.

## H. Segurança

| Ação | Administrador | Gerente | Trabalhador |
| --- | --- | --- | --- |
| Ver/criar atividade | Sim | Sim | Sim |
| Editar atividade | Sim | Sim | Não |
| Cancelar atividade | Sim | Não | Não |
| Ver custo individual | Sim | Sim | Não |
| Criar/alterar custo | Sim | Não | Não |
| Selecionar conta de executor | Ativa/local | Ativa/local | Apenas própria conta |

Login, epoch de sessão, vínculo ativo, contexto, CSRF e permissões continuam no
backend. O novo blueprint participa da exigência de contexto do app. Falta de
contexto não cria propriedades/vínculos. Trocar contexto invalida formulários
anteriores. IDs externos/ausentes não produzem enumeração entre ambientes.

Operação e auditoria são confirmadas na mesma transação, inclusive aplicações
e colheitas evoluídas. Logs guardam ação/IDs e nomes de campos alterados, sem
valores financeiros, corpo do formulário, senha, token ou coordenadas. Falha de
auditoria desfaz o registro operacional; auxiliares independentes anteriores
continuam com seus contratos nos demais módulos.

A revisão reproduziu uma falha concorrente: Gerente carregava item sem custo,
Administrador registrava custo, e a edição do Gerente podia usar o snapshot antigo
para alterar a quantidade sem proteger o total recém-gravado. Foi acrescentada
serialização pela mesma linha de Propriedade **antes** de carregar/validar dados:
PostgreSQL usa `FOR UPDATE`; SQLite reserva escrita com `BEGIN IMMEDIATE` ou
no-op UPDATE quando já existe transação física. Snapshot obsoleto/ocupação é
recusado com 409. Depois da espera, objetos e caches são atualizados e conta,
epoch, perfil e vínculo são revalidados. A trava termina com commit/rollback.

Atividades, aplicações, colheitas e escritas de áreas/culturas usam a mesma
estratégia, protegendo custo concorrente, cancelamento/edição e criação/exclusão
de pais. FKs continuam como integridade adicional nos bancos que as impõem;
SQL/CLI externo às rotas não participa desse protocolo. Não foi alterada a política
global de PRAGMA SQLite nem o contrato das migrations antigas.

DTOs, HTML, CSV e PDF do Trabalhador não incluem campos de custo individuais.
Totais financeiros/equipe gerais aprovados na Etapa 04 continuam disponíveis.
IA local integra apenas contagem e consumo; não grava custos individuais novos
nas respostas persistidas. CSV novo neutraliza fórmulas; HTML/PDF escapam texto.

## I. Banco de dados

Migration `f6a28d9c104e_registros_operacionais.py`, revisão anterior
`e4ca60b1d732`. Cria duas tabelas e acrescenta 11 campos em aplicação e seis em
colheita, todos opcionais, sem default/backfill nos históricos. Nenhuma
geometria, hectare, dose antiga, quantidade de colheita ou valor financeiro
é transformado. Nenhuma dependência de pacote nova foi introduzida.

SQLite usa batch apenas nas tabelas folha aplicação/colheita para adicionar FKs
e unicidade, sem recriar os pais. PostgreSQL utiliza ALTER e NUMERIC. FKs não
têm cascade destrutivo. Downgrade faz preflight antes de DDL: qualquer atividade
ou item, inclusive cancelado, ou campo novo legado não NULL, inclusive zero ou
texto vazio, bloqueia a reversão. Planejar backup/reconciliação em manutenção;
não forçar downgrade destrutivo.

Todos os exercícios de banco usam SQLite temporário/in-memory ou PostgreSQL
descartável. Não se executou migration ou seed no banco real/default anterior,
nem se substituiu migration por `create_all()` em base existente. Testes de
CRUD podem criar schema novo em memória; testes de migration aplicam revisões reais.

## J. Testes

**Resultado final após recuperação: 1.099 testes executados e aprovados,
zero falhas, zero erros e zero ignorados; exit 0, em 282,82 s.** A contagem foi
obtida da execução completa, e não presumida pela soma das rodadas. Os seis
arquivos novos de teste totalizam 292 casos; os demais casos foram preservados.

| Validação | Resultado comprovado |
| --- | --- |
| Suíte completa recuperada/final | 1.099 aprovados, 0 falhas/erros/ignorados; 282,82 s |
| Navegador após recuperação | 96 assertivas aprovadas, 0 falhas e 0 pageerror; desktop 1440px, tablet 820px, celular 390px e três perfis |
| PostgreSQL 16.15 pós-lock | 64 verificações aprovadas, 41 payloads negativos rejeitados atomicamente e 17 guardas de downgrade |
| Concorrência PostgreSQL | Oito corridas reais: custo/quantidade em atividade/aplicação, cancelamento/edição, exclusão/edição, criação/exclusão de pai em duas ordens, perfil e vínculo revogados durante espera |
| Concorrência SQLite | Dez testes reais em arquivo/WAL, incluindo snapshot antigo, custo concorrente, revogação e exclusão/criação sem órfãos |
| Migrations | SQLite e4→f6 populado, FKs, dados preservados, schema sem drift e downgrade protegido; PostgreSQL real com 18 tabelas anteriores preservadas |
| Verificações adicionais | compileall src/tests, node --check atividades.js, pip check e git diff --check aprovados |

Há 204 avisos de depreciação do `get_engine` em `migrations/env.py`,
sem falhas. Não foram convertidos em mudanças de arquitetura fora desta etapa.

Evidências finais: `/tmp/connectagro-stage6/full-final.{xml,log}`;
`ui-summary.md`, `ui-recovery-final.log` e `ui-zny3lut0/` (resultado,
persistência e nove screenshots); `pg-summary.md` e `pg-validation.{py,json,log}`.
Os hashes de aplicação/migrations coincidem com as evidências anteriores; a UI
recuperada repetiu a execução integral com fonte invariável e todos os booleanos
de persistência aprovados. Servidor e container PostgreSQL foram encerrados.
Nenhum banco real/default foi modificado.


Evidências preliminares: `/tmp/connectagro-stage6/baseline.xml` (97),
`atividades.xml` (100), `reports-final.xml` (51),
`/tmp/connectagro-stage6-legacy-final.xml` (119: 71 novos + 48 existentes),
testes de decimal/migration (60 novos). UI e PostgreSQL têm resumos próprios
em `/tmp/connectagro-stage6/`.

O teste histórico de mapas foi atualizado para comparar explicitamente suas
colunas antigas no upgrade até o head, que agora acrescenta campos opcionais,
e exercer a proteção de downgrade da própria revisão e4. A comparação integral
de metadata no head e os testes específicos e4→f6 continuam obrigatórios. Nenhuma
assertiva de integridade foi removida para mascarar erro de produção.

O teste de igualdade exata da matriz de permissões da Etapa 04 recebeu apenas
as quatro permissões de atividades aprovadas expressamente nesta etapa:
Trabalhador cria/visualiza, Gerente também edita, Administrador também cancela.
A igualdade exata e todas as permissões anteriores continuam verificadas;
nenhuma restrição financeira foi retirada.

### Interrupção e recuperação do ambiente

A plataforma interrompeu o acesso ao executor com
`failed to query executor configuration capabilities`. O terminal passou a
responder `No usable execution environment is available`; a espera retornou
falha explícita. Não era possível verificar arquivos, resultado final, commit ou
push. O ponto de retomada foi salvo no rascunho de configuração, sem apresentar
o desenvolvimento local como publicado.

Na recuperação, foram confirmados a mesma branch/HEAD da Etapa 05, todos os
**49 arquivos locais** inventariados antes da queda e os logs/XML/artefatos de
UI/PostgreSQL. O inventário recuperado coincidiu exatamente; não foi identificada
perda de trabalho. Os hashes de 226 arquivos de aplicação/migrations coincidiram
com a validação PostgreSQL final anterior. Nenhum módulo foi reconstruído.

O log completo recuperado mostrou que a primeira suíte havia terminado:
**1.099 executados, 1.096 aprovados e três falhas**, em 286,27 s. As três falhas
eram a expectativa anterior da matriz, ainda sem as novas permissões aprovadas;
nenhum teste foi omitido. Essa execução foi preservada em
`/tmp/connectagro-stage6/full-before-recovery.{xml,log}`. O estado antes da queda
era desconhecido, e não foi apresentado como suíte aprovada.

Após atualizar a expectativa documentada da matriz, foram repetidos compileall,
a suíte completa e o navegador real em outro SQLite descartável. Os resultados
finais desta seção são os das execuções efetivas, sem somar rodadas repetidas. A
validação PostgreSQL foi reaproveitada por evidências e hashes idênticos;
as migrations SQLite também integram a suíte completa reexecutada.

### Rastreabilidade dos cenários solicitados

| Cenários | Verificação efetiva |
| --- | --- |
| T01–T04 | Área/associação locais, IDs externos e executores ativos, autoria de sessão preservada nos CRUDs |
| T05–T07 | Produto catalogado, bloqueio pelos dois status, dois itens separados e rejeição atômica de item inválido |
| T08–T10 | Dose/consumo independentes, positivos/finitos/precisos, soma por produto e unidade sem conversões |
| T11–T14 | NULL versus zero, multiplicação decimal/arredondamento, preço não inferido e nenhum lançamento automático |
| T15–T18 | Migration populada, outros ambientes intactos, cancelamento lógico/bloqueio de exclusões e auditoria atômica |
| T19–T21 | Matriz dos três perfis, custos omitidos do Trabalhador, POST forjado/CSRF e acesso revogado durante espera |
| T22–T24 | Atividade sem itens/cultura, históricos incompletos, totais separados e unidades/ACL nas exportações CSV/PDF |
| T25–T26 | SQLite real com FKs na migration e corridas WAL; PostgreSQL 16.15 real, persistência e concorrência |
| T27–T30 | Suíte completa, incluindo dashboard, mapas, sessões, permissões e todos os módulos anteriores |

## K. Pendências

- Áreas de Plantio independentes: autorização/contexto continuam fora desta etapa.
- Recursos não catalogados e catálogo definitivo de tipos de atividade aguardam
  regra. Texto livre da atividade não é um catálogo publicado de classificações.
- Associação reconciliada entre atividade e aplicação histórica, com fonte única,
  migração verificável e prevenção de dupla entrada manual, não foi implementada.
- Integração automática com financeiro/estoque não foi autorizada e não existe.
- Outras moedas, conversões de unidade, recomendação agronômica e cálculo de dose
  não foram implementados.
- Testes Windows nativos não foram executados; o ambiente validado é Linux.
- Publicação/PR e disponibilidade externa dependem das condições de rede; ver L.

## L. Conclusão

Branch de entrega: `codex/etapa-06-registros-operacionais`, com base de revisão
`codex/etapa-05-mapas-territorio`. O hash completo e a confirmação do push são
registrados na entrega final e no histórico Git; este documento não inclui seu
próprio hash futuro. Etapas anteriores não são apresentadas como delta exclusivo
desta etapa. A `main` não recebe merge automático e permaneceu na referência
`92273e2b3a4bdb6db4dc0a3b74b003ec702777d8` na consulta remota de recuperação.

A chamada REST `gh api repos/Helio965/Connectagro` continuou retornando
`Forbidden` para `api.github.com` na política aplicada, enquanto o Git nativo
conseguiu consultar os refs. Não foi criado PR nem inventado número/link de PR.
A comparação para revisão/abertura manual, após o envio da branch, é:
https://github.com/Helio965/Connectagro/compare/codex/etapa-05-mapas-territorio...codex/etapa-06-registros-operacionais?expand=1

O rascunho de rede contém proposta para a API, mas salvar rascunho não aplica
rede nem publica ambiente. Configuração reutilizável deve ser revisada/salva e
publicada pelo produto. Nenhum token adicional foi solicitado ou extraído.

A Etapa 06 foi validada no escopo implementado, com as pendências funcionais
explicitadas em K. A base está organizada para a Etapa 07, catálogo local/global e aprovação
administrativa, sem implementar antecipadamente cadastro global automático nem
fluxo de aprovação. A evolução deverá preservar IDs de produtos já referenciados
em aplicações/itens, os bloqueios regulatórios e o isolamento territorial.

## Inventário absoluto da Etapa 06

50 arquivos exclusivos em relação ao commit da Etapa 05. Os 49 arquivos recuperados foram preservados; a atualização explícita do contrato de permissões acrescentou o 50º arquivo.

```text
/workspace/Connectagro/README.md
/workspace/Connectagro/docs/03-regras-de-negocio.md
/workspace/Connectagro/docs/04-modelagem-banco-der.md
/workspace/Connectagro/docs/05-dicionario-de-dados.md
/workspace/Connectagro/docs/auditoria/06-registros-operacionais.md
/workspace/Connectagro/migrations/versions/f6a28d9c104e_registros_operacionais.py
/workspace/Connectagro/src/app/__init__.py
/workspace/Connectagro/src/app/blueprints/__init__.py
/workspace/Connectagro/src/app/blueprints/aplicacoes/routes.py
/workspace/Connectagro/src/app/blueprints/atividades/__init__.py
/workspace/Connectagro/src/app/blueprints/atividades/routes.py
/workspace/Connectagro/src/app/blueprints/colheita/routes.py
/workspace/Connectagro/src/app/blueprints/culturas/routes.py
/workspace/Connectagro/src/app/blueprints/glebas/routes.py
/workspace/Connectagro/src/app/blueprints/relatorios/routes.py
/workspace/Connectagro/src/app/models/__init__.py
/workspace/Connectagro/src/app/models/aplicacao.py
/workspace/Connectagro/src/app/models/atividade.py
/workspace/Connectagro/src/app/models/colheita.py
/workspace/Connectagro/src/app/models/cultura.py
/workspace/Connectagro/src/app/models/gleba.py
/workspace/Connectagro/src/app/services/exportacoes_service.py
/workspace/Connectagro/src/app/services/ia_simulada_service.py
/workspace/Connectagro/src/app/services/operacionais_lock.py
/workspace/Connectagro/src/app/services/operacionais_service.py
/workspace/Connectagro/src/app/services/relatorios_service.py
/workspace/Connectagro/src/app/static/css/atividades.css
/workspace/Connectagro/src/app/static/js/atividades.js
/workspace/Connectagro/src/app/templates/aplicacoes/form.html
/workspace/Connectagro/src/app/templates/aplicacoes/list.html
/workspace/Connectagro/src/app/templates/atividades/_item.html
/workspace/Connectagro/src/app/templates/atividades/_macros.html
/workspace/Connectagro/src/app/templates/atividades/form.html
/workspace/Connectagro/src/app/templates/atividades/list.html
/workspace/Connectagro/src/app/templates/base.html
/workspace/Connectagro/src/app/templates/colheita/form.html
/workspace/Connectagro/src/app/templates/colheita/list.html
/workspace/Connectagro/src/app/templates/relatorios/index.html
/workspace/Connectagro/src/app/templates/relatorios/operacionais.html
/workspace/Connectagro/src/app/utils/decimal_exato.py
/workspace/Connectagro/src/app/utils/permissions.py
/workspace/Connectagro/tests/README.md
/workspace/Connectagro/tests/test_atividades_operacionais.py
/workspace/Connectagro/tests/test_decimal_exato.py
/workspace/Connectagro/tests/test_mapa_migration.py
/workspace/Connectagro/tests/test_operacionais_concorrencia.py
/workspace/Connectagro/tests/test_operacionais_legado.py
/workspace/Connectagro/tests/test_operacionais_migration.py
/workspace/Connectagro/tests/test_permissions_stage4.py
/workspace/Connectagro/tests/test_relatorios_etapa6.py
```
