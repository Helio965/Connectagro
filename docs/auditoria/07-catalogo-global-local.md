# Etapa 07 — Catálogo global, local e governança

Data de referência: 09/11/2026, America/Sao_Paulo. Repositório oficial:
https://github.com/Helio965/Connectagro.

## A. Diagnóstico inicial

Base conferida: `34e7749fd5318e66aa358757f2527a2df0150f1d`, branch publicada
`codex/etapa-06-registros-operacionais`, descendente da Etapa 05
`20b3fad8cbc6398d8adb123655bdf66141fc62a4`. Status limpo, branches, log,
remoto oficial, fetch e refs remotos foram verificados antes de modificar código.
Branch criada: `codex/etapa-07-catalogo-global-local`, a partir dessa base.

Os seis relatórios anteriores foram lidos integralmente na auditoria distribuída.
Foi executada a suíte existente **antes de qualquer alteração**: **1.099 testes
aprovados**, sem falhas/erros/ignorados, em **287,20 s**, exit 0; 204 avisos de
depreciação de `get_engine`. Evidências:
`/tmp/connectagro-stage7/baseline.{xml,log}`, inventário e hashes da base.

O catálogo anterior continha `ProdutoBase` global, fichas técnicas, imagens e
preços de referência, sem escrita web. Defensivos/Fertilizantes já ofereciam
busca, categorias, detalhe por slug e acesso autenticado mesmo sem Propriedade.
O seed tinha 60 bases, 60 fichas e 60 imagens com fontes/licenças rastreadas,
sem preços. Aplicações e itens de atividade referenciavam os IDs globais.

## B. Problemas identificados

1. **Associação ao produto errado no seed, reproduzida:** base era reconhecida
   por slug, mas ficha/imagem continuavam usando o ID original do arquivo. Banco
   com slug do seed em outro ID e produto distinto no ID original recebia dados
   do produto errado. Corrigido por preflight completo ID↔slug, antes das
   alterações de produtos, com erro controlado e rollback integral do conflito.
   Não se remapeia ou troca ID histórico para fazer a importação passar.
2. **Imagem administrada sobrescrita:** reimportar atualizava uma imagem escolhida
   implicitamente por produto, sem prova de origem. Agora somente a imagem
   explicitamente gerenciada pelo seed e ainda igual ao último fingerprint pode
   ser atualizada. Divergências, legados incertos e imagens adicionais permanecem.
3. **Produto bloqueado importado:** bastava não constar da própria lista de
   exclusões para os status bloqueados passarem pelo validador. Ambos os status
   são verificados independentemente dessa lista; bloqueados não são importados.
4. IDs explícitos do seed podiam deixar a sequence PostgreSQL atrasada. O helper
   de sincronização avança somente quando necessário, sem recuar valores já
   alocados, sob a mesma trava da publicação global.
5. Não existiam permissões/modelos para cadastro local, complementos, solicitações
   ou autoridade global. Essas decisões foram solicitadas antes da implementação.
6. A revisão encontrou campos extras nas ações de estado/cancelamento gerando
   HTTP 500. Foi corrigido para validação 400 controlada, mantendo 403 para campos
   protegidos e rollback sem modificar estado ou histórico.

Não foram alterados os arquivos de imagem, manifestos ou conteúdo técnico dos
seeds. As 60 imagens foram conferidas contra o manifesto: IDs/slugs/caminhos,
bytes, dimensões 900×600 e referências de fonte/licença.

## C. Decisões de negócio

### Aprovadas expressamente pelo usuário nesta etapa

- Produtos locais e personalizações pertencem à **Propriedade ativa**,
  compartilhados pelos usuários com vínculo autorizado nela.
- **Todos os perfis criam** produtos locais, personalizações e solicitações.
  **Somente Administrador e Gerente editam**, incluindo inativação/reativação e
  cancelamento de solicitação. Trabalhador não ganha edição por ser criador.
- Revisão/publicação global é restrita a **Administradores explicitamente
  habilitados para catálogo global**, sem acesso operacional a outras origens.

### Escolhas mínimas de implementação

- Nome e classe são obrigatórios no novo produto local; demais campos são
  opcionais. Classes existentes são mantidas, sem novo catálogo regulatório.
- Complementos locais não substituem classe, categoria, status, preços, dose ou
  ficha técnica global. Nome local aparece identificado separadamente.
- Aprovação de inclusão cria nova referência global, ou associa explicitamente
  o resultado a uma existente escolhida pelo revisor. Não há fusão automática.
- Alteração global pelo fluxo se limita a descrições. Nome, slug, classe,
  categoria, status, preço e ficha técnica existentes não são sobrescritos. Isso
  preserva também a identificação que relatórios históricos consultam atualmente.
- Dados apresentados em uma solicitação são revisados explicitamente no
  formulário; observações privadas e arquivos locais não são copiados ao envio.
- Imagens privadas e uso de produtos locais em operações não foram presumidos
  como autorizados. Sua integração permanece declarada na seção M.

## D. Modelagem

`ProdutoBase` continua **exclusivamente global**, com seus IDs e slugs. Nenhuma
FK de `AplicacaoInsumo` ou `AtividadeItem` foi substituída, tornada polimórfica ou
preenchida com ID local/de solicitação.

| Estrutura | Responsabilidade |
| --- | --- |
| `ProdutoLocal` | Cadastro particular da Propriedade, autoria, campos informados, estado, versão e chave única de envio |
| `ProdutoPersonalizacao` | Complemento local de uma base global, único por Propriedade/produto |
| `CatalogoRevisao` | Snapshot imutável de cada versão de cadastro/personalização, com autor/data/ação |
| `SolicitacaoCatalogo` | Origem explícita, versão, proposta imutável, estado, decisão e referência global resultante |
| `CatalogoControle` | Linha única de coordenação transacional para seed/publicação, sem dados operacionais |
| `Usuario.catalogo_global_aprovador` | Capacidade restrita e optativa; falso por padrão para todas as contas |
| `ProdutoImagem.origem_seed/seed_fingerprint` | Proveniência explícita e prova do último conteúdo aplicado pelo seed |

Revisão/solicitação tem exatamente uma origem: produto local **ou**
personalização. Constraints XOR, versões positivas e unicidades protegem os
vínculos. Não há cascata destrutiva de históricos.

Foram descartados: inserir locais em `ProdutoBase` (vazaria nos leitores e
seletores globais), copiar a ficha global por Propriedade (duplicaria dados
técnicos), interpretar IDs locais como globais (misturaria identidades) e aplicar
apelidos ao histórico operacional vivo (alteraria a apresentação de registros
antigos). O uso operacional futuro requer relacionamento tipado e política de
snapshot/reconciliação própria.

## E. Cadastros

O módulo `/catalogo/local/` exige contexto e vínculo ativos. Nome/classe/categoria,
descrições, unidade de referência, observações e fonte são validados no backend.
Somente nome/classe são obrigatórios. Identificação territorial, autor, status e
capacidade global não vêm de campos ocultos. Campos protegidos forjados são 403;
campos extras ou repetidos são recusados com 400 controlado.

Reenvio idêntico com a mesma UUID não duplica cadastro ou autoria. Reuso em outro
contexto/autor/conteúdo é conflito. Edição exige a versão carregada; conflitos
retornam 409. Possíveis correspondências por nome normalizado/slug são avisos
para confirmação de registro distinto, sem união automática. Slugs globais
mantêm unicidade; locais não reutilizam o domínio de IDs globais.

Nomes/identificadores coincidentes exatamente com bloqueios globais ou exclusões
documentadas do seed não podem ser usados para fabricar referência operacional
liberada. Esse controle não afirma validação externa nem deduz equivalência de
nomes apenas semelhantes.

## F. Personalizações

Campos permitidos: nome local, descrição complementar, unidade de referência,
observações e fonte. São apresentados como complemento da Propriedade, sem
trocar o nome/slug/status/ficha do produto global. Uma personalização não
desbloqueia produto e não altera outra Propriedade.

Criação e edição são autorizadas separadamente: Trabalhador pode criar quando
ainda não existe complemento, mas não editar ou reativar o já existente.
Cada alteração efetiva gera versão/revisão; estado também é rastreado. Versão,
autoria e data anteriores são preservadas. Leituras não criam cadastros/vínculos.

Defensivos/Fertilizantes preservam endpoints, classes, busca/categorias e detalhe
por slug. Busca também pode encontrar o complemento da Propriedade ativa,
mantendo os filtros globais. Sem contexto selecionado, somente globais aparecem.
Categorias e produtos locais não atravessam Propriedades por query string.

## G. Solicitações

Todos os perfis podem enviar proposta de inclusão de produto local ou alteração
de descrição a partir de personalização. A solicitação guarda origem, versão,
autor/data e campos explicitamente propostos; não publica ao receber o POST.
Não inclui automaticamente observações privadas ou imagens.

Existe uma solicitação por origem/versão, protegida por unicidade. Reenvio
idêntico preserva a primeira autoria; conteúdo diferente na mesma versão é
conflito. Alterar a origem não reescreve o snapshot enviado. Cancelamento local
é restrito a Administrador/Gerente e preserva a proposta. Não há e-mail,
notificação externa ou usuário criado automaticamente.

## H. Aprovação

`/catalogo/revisao/` exige capacidade dinâmica de banco, além do perfil Admin.
Ser Administrador comum, enviar campo/cookie forjado ou ser Gerente com flag
indevida não concede essa autoridade. Nenhuma conta real foi habilitada.

O operador de infraestrutura pode provisionar explicitamente uma conta Admin
ativa com `flask --app src/run.py catalogo-global-permissao --usuario-id ID
--habilitar` ou revogar com `--revogar`. O comando é auditado e não existe rota
de autoconcessão. Não foi executado em conta real nesta tarefa.

O revisor vê somente a proposta e a decisão do catálogo; não seleciona a
Propriedade de origem na sessão nem obtém operações, equipe, arquivos ou dados
financeiros de terceiros. Pode trabalhar sem vínculo à origem ou Propriedade
ativa. Os demais módulos continuam exigindo seus próprios vínculos.

Decisão é serializada na ordem catálogo → Propriedade de origem → conta do
revisor, com refresh e revalidação de sessão/epoch/perfil/capacidade depois da
espera. Edições locais usam a mesma trava de Propriedade das operações anteriores.
Seed e publicação compartilham a linha de controle global.

Aprovação pendente exige origem ativa e mesma versão; alteração descritiva exige
também o fingerprint da ficha global no momento do envio. Conteúdo obsoleto é
conflito. Rejeição não modifica a base. Decisão repetida é idempotente; decisão
oposta após encerramento não substitui a anterior.

Inclusão nova usa ID automático, slug único e estados existentes de cadastro de
usuário/não validado por classe. Não cria preço ou imagem. Referência existente
pode ser escolhida explicitamente como resultado, sem alterar sua ficha ou
remapear local/históricos. Referências bloqueadas e exclusões documentadas não
podem ser liberadas quando a proposta coincide com seus nomes/identificadores,
mesmo com slug distinto, confirmação de duplicata ou associação explícita.
Nomes apenas semelhantes não são prova de identidade.

**Aprovação administrativa no ConnectAgro não é aprovação regulatória oficial,
recomendação de uso, registro, venda ou comercialização.**

## I. Integração operacional

Aplicações e atividades permanecem com `produto_base_id` global. Seus seletores,
bloqueios pelos dois status, dose, consumo, unidades e custos não foram alterados.
Não entram locais/solicitações pendentes como produtos globais aprovados.
Personalizações não mudam retrospectivamente nomes dos registros operacionais.

A publicação não transfere IDs históricos, não reaplica doses e não usa preço
de referência como custo. Relatórios/exportações/IA continuam respeitando
contexto e a política financeira da Etapa 06. Novo global aprovado pode ser
selecionado como qualquer referência global, com os bloqueios vigentes.

## J. Segurança

- Login, sessão validada no banco, epoch, permissões e CSRF preservados.
- Operações locais exigem vínculo/contexto e consultas por Propriedade; IDs
  externos retornam 404 para ações permitidas ao perfil. Trabalhador não edita.
- Autor/contexto/status/capacidade global são determinados no servidor.
- Textos têm tamanho limitado; NUL/controles inválidos são recusados. Propostas
  JSON têm leitura limitada/controlada e não viram HTML não escapado.
- Validação precede alterações; estado e auditoria são confirmados atomicamente.
  Logs têm ação/IDs/campos/decisão, sem corpo técnico completo, senha ou token.
- Fontes globais/imagens/licenças existentes foram preservadas. Nenhum upload
  privado foi exposto em `static` ou promovido automaticamente ao catálogo.
- A autoridade global não libera dados de outra Propriedade nas rotas anteriores.

## K. Banco de dados

Migration `g7c53b8e19a2_catalogo_global_local.py`, após `f6a28d9c104e`.
Acrescenta cinco tabelas, uma capacidade falsa por padrão e dois campos opcionais
de proveniência de imagens. Não altera migrations antigas nem IDs, slugs,
campos técnicos, aplicações, itens, quantidades, custos, hectares ou geometrias.
Proveniência desconhecida permanece NULL; não é inferida por semelhança.

Upgrade e downgrade foram exercitados em bases temporárias. Downgrade faz
preflight antes de qualquer DDL: bloqueia qualquer domínio novo, inclusive
inativo/rejeitado, capacidade global habilitada ou proveniência preenchida.
Controle singleton só pode ser removido após verificar ausência dos dados.
Não houve alteração/seed em banco real/default e não se usou `create_all()` para
atualizar base existente. Fixtures novas em memória podem criar schema vazio;
testes de migration usam revisões reais e histórico populado.

As fixtures antigas de migrations foram ajustadas para inserir no schema
histórico refletido, evitando defaults novos do ORM em colunas ainda inexistentes.
Testes que consultam o ORM atual/schema completo usam o head vigente; proteções
de downgrade continuam exercitando revisões específicas. A projeção mantém todas
as colunas históricas e as novas ficam cobertas nos testes próprios. A matriz
exata também recebeu somente as permissões locais expressamente aprovadas;
nenhuma igualdade ou restrição antiga foi removida.

## L. Testes

**Suíte final: 1.362 testes executados e aprovados, zero falhas, zero erros e
zero ignorados, em 344,81 s; exit 0.** A contagem foi medida pelo pytest/XML:
263 casos novos em quatro arquivos, dentro do total, sem somar rodadas repetidas.
Há 364 avisos de depreciação de `get_engine` em `migrations/env.py`; o ajuste
estrutural solicitado pertence à Etapa 08 e não foi misturado neste commit.

| Validação | Resultado real |
| --- | --- |
| Baseline da Etapa 06, antes de alterações | 1.099 aprovados; 287,20 s |
| Suíte completa final | 1.362 aprovados; 344,81 s; sem falhas/erros/ignorados |
| Workflows locais/globais e CLI | 132 aprovados, incluindo corpos extras/duplicados e atomicidade |
| Seed novo + anterior | 119 aprovados na integração inicial; casos adicionais também na suíte completa |
| Migration g7 | 32 aprovados em SQLite populado/FKs ativas; sem drift |
| Compatibilidade das migrations anteriores + g7 | 68 aprovados; sem perda de assertivas históricas |
| Navegador real final | 160 assertivas, zero falhas/pageerror, todos os snapshots aprovados; servidor encerrado |
| PostgreSQL 16.15 real final | 106 verificações, 12 payloads negativos inventariados, sete guardas de downgrade e oito corridas reais aprovados; container removido |
| Verificações adicionais | compileall src/tests, sintaxe JS, pip check, git diff --check e hashes de fontes/imagens/migrations publicados aprovados |

Evidências finais: `/tmp/connectagro-stage7/full-final.{xml,log}`;
`workflow-tests-final.{xml,log}`; `ui-summary.md`, `ui-final.log` e
`ui-c4z8xhvp/` com resultados/persistência/nove screenshots; `pg-summary.md`,
`pg-validation.{py,json,log}` e `pg-api-phase.py`. Fontes do produto e migrations
permaneceram idênticos às evidências finais de UI/PostgreSQL. Não foi alterado
banco real/default nem habilitada conta real para publicação global.

PostgreSQL preservou as 20 tabelas anteriores; validou sequência após seed e
após ID manual 2000 sem colisão. As oito corridas ordenadas com waiters PG reais
abrangem aprovação repetida, disputa de slug por solicitações diferentes,
edição antes da aprovação e aprovação antes da edição, flag revogada, perfil
rebaixado, seed antes da publicação e vínculo local revogado durante espera. Nenhuma proposta criou acesso operacional
à origem. Consultar o resumo/harness para os pares de resposta de cada cenário.


Evidências parciais: `/tmp/connectagro-stage7/`: baseline, models-migration,
seed-integration, workflow-first e migrations-compatible (XML/log).

| Cenários solicitados | Cobertura efetivamente executada |
| --- | --- |
| T01–T04 | Globais, IDs/slugs/seed idempotente e referências de aplicação/item preservados em SQLite/PostgreSQL e regressões |
| T05–T09 | Cadastro/overlay por contexto, IDs externos recusados, global inalterado, revisões e inativação sem exclusão |
| T10–T15 | Snapshot privado/versionado, rejeição sem publicação, aprovação idempotente, conflitos/duplicatas e auditoria atômica |
| T16–T20 | Login, três perfis, capacidade global optativa, CSRF, contexto e tentativas de manipular IDs/autoridade |
| T21–T26 | Bloqueios e exclusões documentadas, status/custos/preços imutáveis, FKs de aplicações/itens antigos intactos |
| T27–T28 | SQLite populado/FKs/migrations e PostgreSQL 16.15 real, sequence e corridas concorrentes |
| T29–T33 | Busca/filtros globais e por alias local, estados/roles e navegador real desktop/tablet/celular |
| T34–T38 | Suíte completa e regressões de autenticação, Propriedades, mapas e operações anteriores |

As rodadas de navegador usaram Flask/migrations/Chromium/CSRF reais, sem mocks
do produto. Na primeira tentativa, as 160 assertivas de interação passaram,
mas o snapshot final do harness comparava todas as fichas, incluindo as novas
fontes explicitamente propostas. O harness foi corrigido para exigir preservação
exata das fichas antigas por ID **e** verificar separadamente que as novas
contêm somente a fonte informada, sem composição/dados inventados. A rodada
completa foi repetida e passou com todos os snapshots verdadeiros. Nenhum código
de produção ou controle de acesso foi alterado para esconder esse resultado.

O cancelamento manual por botão não foi exercitado nessa rodada de navegador;
o backend possui testes reais para cancelamento, papéis e corpos inválidos.
Resultados da rodada PostgreSQL ampliada substituem, sem somar, a preliminar.

## M. Pendências

- Uso operacional tipado de produtos locais, com FK própria e snapshot adequado;
  locais não entram nos campos globais existentes nesta etapa.
- Fotos privadas locais: ainda precisam de regra e validação real de conteúdo,
  vínculo/armazenamento privado e política de publicação. Upload atual por
  extensão não foi apresentado como solução inline de imagem.
- Revisão regulatória externa, preço consolidado, novas unidades/moedas e dados
  técnicos oficiais permanecem fora da implementação.
- Alterações globais de identidade/status/ficha técnica precisam de fluxo próprio
  e análise dos históricos; somente descrições foram liberadas neste fluxo.
- Habilitação de contas reais é responsabilidade explícita do operador, sem
  concessão automática pelo seed ou painel de usuários.
- Restauração em nova tarefa e testes Windows nativos não são presumidos.

## N. Conclusão

A implementação está validada no escopo descrito, com as funcionalidades
condicionais explicitadas em M. Branch de entrega:
`codex/etapa-07-catalogo-global-local`, baseada em
`34e7749fd5318e66aa358757f2527a2df0150f1d`. O hash completo/resultado de push
constam da entrega e do histórico Git, sem incluir o próprio hash futuro aqui.
A comparação de revisão usa Etapa 06 como base; commits anteriores não são
apresentados como delta exclusivo da Etapa 07.

A API REST GitHub retornou `Forbidden` para `api.github.com`, enquanto o Git
nativo permaneceu disponível. Nenhum PR foi criado/numerado automaticamente.
Comparação para revisão/abertura manual após o envio:
https://github.com/Helio965/Connectagro/compare/codex/etapa-06-registros-operacionais...codex/etapa-07-catalogo-global-local?expand=1

A `main` não recebe merge automático. A referência observada foi
`92273e2b3a4bdb6db4dc0a3b74b003ec702777d8`; a confirmação remota final é
registrada na entrega. Rascunho de configuração não significa rede aplicada ou
ambiente publicado: revisão/salvamento e publicação pelo produto são separados.

A Etapa 08 foi recebida durante o desenvolvimento e exige validar/publicar a
Etapa 07 primeiro. Não foram misturadas refatorações/CI da Etapa 08 neste delta.
A auditoria estrutural seguinte deverá usar o commit efetivamente validado da
Etapa 07 e preservar os controles de identidade, contexto e publicação descritos.

## Inventário absoluto da Etapa 07

49 arquivos exclusivos em relação ao commit validado da Etapa 06; nenhum arquivo da Etapa 08 está incluído.

```text
/workspace/Connectagro/README.md
/workspace/Connectagro/data/seeds/README.md
/workspace/Connectagro/docs/03-regras-de-negocio.md
/workspace/Connectagro/docs/04-modelagem-banco-der.md
/workspace/Connectagro/docs/05-dicionario-de-dados.md
/workspace/Connectagro/docs/auditoria/07-catalogo-global-local.md
/workspace/Connectagro/docs/catalogo-produtos/README.md
/workspace/Connectagro/migrations/versions/g7c53b8e19a2_catalogo_global_local.py
/workspace/Connectagro/src/app/__init__.py
/workspace/Connectagro/src/app/blueprints/__init__.py
/workspace/Connectagro/src/app/blueprints/catalogo_admin/__init__.py
/workspace/Connectagro/src/app/blueprints/catalogo_admin/routes.py
/workspace/Connectagro/src/app/blueprints/catalogo_local/__init__.py
/workspace/Connectagro/src/app/blueprints/catalogo_local/routes.py
/workspace/Connectagro/src/app/blueprints/defensivos/routes.py
/workspace/Connectagro/src/app/blueprints/fertilizantes/routes.py
/workspace/Connectagro/src/app/commands.py
/workspace/Connectagro/src/app/models/__init__.py
/workspace/Connectagro/src/app/models/catalogo_local.py
/workspace/Connectagro/src/app/models/produto.py
/workspace/Connectagro/src/app/models/usuario.py
/workspace/Connectagro/src/app/services/catalogo_governanca_service.py
/workspace/Connectagro/src/app/services/catalogo_local_service.py
/workspace/Connectagro/src/app/services/catalogo_seed.py
/workspace/Connectagro/src/app/static/css/catalogo-local.css
/workspace/Connectagro/src/app/static/js/catalogo-local.js
/workspace/Connectagro/src/app/templates/base.html
/workspace/Connectagro/src/app/templates/catalogo/detail.html
/workspace/Connectagro/src/app/templates/catalogo/list.html
/workspace/Connectagro/src/app/templates/catalogo_admin/detail.html
/workspace/Connectagro/src/app/templates/catalogo_admin/index.html
/workspace/Connectagro/src/app/templates/catalogo_local/_macros.html
/workspace/Connectagro/src/app/templates/catalogo_local/detail.html
/workspace/Connectagro/src/app/templates/catalogo_local/form.html
/workspace/Connectagro/src/app/templates/catalogo_local/historico.html
/workspace/Connectagro/src/app/templates/catalogo_local/index.html
/workspace/Connectagro/src/app/templates/catalogo_local/solicitacao.html
/workspace/Connectagro/src/app/templates/catalogo_local/solicitacoes.html
/workspace/Connectagro/src/app/templates/catalogo_local/solicitar.html
/workspace/Connectagro/src/app/utils/catalogo.py
/workspace/Connectagro/src/app/utils/permissions.py
/workspace/Connectagro/tests/README.md
/workspace/Connectagro/tests/test_catalogo_global_workflow.py
/workspace/Connectagro/tests/test_catalogo_local_migration.py
/workspace/Connectagro/tests/test_catalogo_local_workflow.py
/workspace/Connectagro/tests/test_catalogo_seed_stage7.py
/workspace/Connectagro/tests/test_mapa_migration.py
/workspace/Connectagro/tests/test_operacionais_migration.py
/workspace/Connectagro/tests/test_permissions_stage4.py
```
