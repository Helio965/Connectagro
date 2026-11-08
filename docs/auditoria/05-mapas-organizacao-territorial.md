# Etapa 05 — mapas e organização territorial

Data de referência: 08/11/2026, America/Sao_Paulo.

**Implementação validada para Propriedades e Áreas de Plantio vinculadas.**
A suíte final executou **807 testes, todos aprovados**, e o navegador executou
**230 assertivas, todas aprovadas**. Áreas independentes não foram implementadas
por falta de decisões de autorização/contexto. Cartografia externa e abertura
automática de PR permanecem limitadas pela rede, conforme a seção J.

## A. Estado inicial

Checkout `/workspace/Connectagro`, remoto oficial `Helio965/Connectagro`.
Foram conferidos branch, status, cinco commits recentes, remoto e `fetch`;
os relatórios 01–03 existiam e foram preservados. A Etapa 04 estava interrompida
por falha do executor e seu relatório ainda não existia na retomada. Suas
correções foram concluídas e verificadas antes da implementação territorial:
**687 testes aprovados**, zero falhas/erros/ignorados, e **115 assertivas de
navegador** com os três perfis. Seis corridas PostgreSQL reais preservaram o
último administrador ativo. O relatório 04 foi então criado e conferido.

A fonte atualizada depende de trabalho anterior que ainda não estava em
commits. Foi preservado um snapshot exato antes da Etapa 04 e feita separação
explícita, sem incluir a base anterior no commit exclusivo das permissões:

| Base | Commit | Branch publicada |
| --- | --- | --- |
| Etapas 01–03 identificadas | `70310c00b188af056528fc69b15dfdfca96cb4de` | `codex/base-etapas-01-03` |
| Somente Etapa 04 | `7cb745687af9431857cbe77a53fd3cc145cda0d1` | `codex/etapa-04-permissoes-usuarios` |

As duas referências foram confirmadas com `git ls-remote`. A `main` permanece
em `92273e2b3a4bdb6db4dc0a3b74b003ec702777d8`, sem merge automático. A Etapa 05
começou em `codex/etapa-05-mapas-territorio`, filha da Etapa 04, com fonte limpa.
Snapshot de hashes em `/tmp/connectagro-stage5/baseline-manifest.json`.

O mapa já usava Leaflet 1.9.4 e Leaflet.draw 1.0.4, exibia geometrias de Gleba,
permitia salvar/limpar e validava estrutura GeoJSON. Propriedade não tinha
geometria própria. A resposta JSON possuía `propriedade` e `glebas`, e as rotas
de edição usavam `mapa.edit` e o contexto autorizado. Não havia autorização por
Área de Plantio independente.

## B. Problemas identificados

| Problema | Impacto e tratamento nesta etapa |
| --- | --- |
| Propriedade sem contorno próprio | Campo opcional e rotas próprias, separados das geometrias de Gleba |
| Validação apenas estrutural | Shapely/GEOS para degeneração, autointerseção, furos e validade de MultiPolygon |
| `type` não textual, inteiro enorme e JSON profundo | Limites antes do parse/GEOS e respostas controladas em vez de 500 |
| Leitura legada superficial | Leitura segura, mantendo lista textual e bytes antigos sem atualização automática |
| Camada confirmada removida após salvar | Reconstrução da camada confirmada para permanecer visível ao trocar a seleção |
| Limpar apagava desenho antes da resposta | Manter o rascunho até a confirmação do servidor |
| Troca de entidade descartava desenho | Aviso de alterações não salvas e seleção estável durante requests |
| Serialização usava somente a última camada | Preservar partes e furos em delimitações compostas |
| Bibliotecas CDN bloqueadas | Distribuições oficiais locais, com versões/licenças/integridade registradas |
| Falhas de HTTP/tiles sem tratamento adequado | Mensagens específicas e preservação do acesso textual e às geometrias |
| Troca rápida durante animação mantinha o enquadramento anterior | Cancelar a animação e enquadrar imediatamente a nova entidade; regressão real no navegador |
| Leaflet.draw executava mesmo quando Leaflet falhava | Loader condicionado à dependência; falta de cada biblioteca validada sem erro JavaScript não tratado |

O nome técnico `Gleba` foi preservado; a interface apresenta **Área de Plantio**.
Nenhum relacionamento agrícola foi renomeado ou movido para corrigir aparência.

## C. Arquivos e responsabilidades

Raiz absoluta: `/workspace/Connectagro/`. Os caminhos completos da entrega estão
no inventário ao final deste relatório.

| Arquivos | Responsabilidade / alteração |
| --- | --- |
| `src/app/models/propriedade.py` | Contorno próprio opcional, sem mudar áreas informadas ou relacionamentos |
| `migrations/versions/e4ca60b1d732_add_propriedade_poligono.py` | ADD COLUMN nullable; downgrade bloqueado quando existe conteúdo |
| `src/app/services/mapa_service.py` | Validação de estrutura/topologia, limites de recurso, leitura legada segura, comparação informativa e setters separados |
| `src/app/blueprints/mapa/routes.py` | JSON compatível ampliado, novos POSTs de Propriedade, bytes limitados antes do parse, contexto/IDs e auditoria |
| `src/app/blueprints/glebas/routes.py` | Rejeitar áreas informadas não finitas antes de persistir |
| `src/app/templates/mapa/index.html` | Dois tipos de entidade, identificação visível, legenda, estados textuais e controles por permissão |
| `src/app/static/js/mapa.js` | Camadas confirmadas e desenho local separados, partes/furos, dirty/busy, enquadramento estável e erros sem perda silenciosa |
| `src/app/static/js/mapa-loader.js` | Carregar Draw somente após Leaflet; fallback de leitura/texto quando há falha parcial |
| `src/app/static/css/main.css` | Cores/camadas, controles, avisos e tamanhos menores, preservando navegação e identidade visual |
| `src/app/static/vendor/` | 19 arquivos oficiais de Leaflet/Draw, incluindo licenças, e manifesto de origem/integridade |
| `.gitattributes` | Preservar os bytes e finais de linha oficiais do vendor em Linux/Windows, mantendo a verificação de whitespace |
| `requirements.txt` | Shapely `>=2.2,<3`, necessário para topologia confiável |
| `tests/test_mapa_geometria.py` | 83 casos novos de geometria, limites, legado e contenção |
| `tests/test_mapa_territorio.py` | 32 casos novos de API, preservação, segurança, hectares e persistência |
| `tests/test_mapa_migration.py` | Cinco casos de migration SQLite real e proteção contra reversão com perda |
| `README.md`, `docs/03-regras-de-negocio.md`, `docs/04-modelagem-banco-der.md`, `docs/05-dicionario-de-dados.md`, `docs/06-1-arquitetura-tecnica-mvp.md`, `tests/README.md` | Contratos atuais; remoção de coordenadas obsoletas da documentação e distinção entre dados informados e geometria |
| `docs/auditoria/05-mapas-organizacao-territorial.md` | Este relatório |

## D. Modelagem territorial

Propriedade continua sendo o ambiente administrativo autorizado por
`UsuarioPropriedade`; Gleba continua sendo a Área de Plantio com FK obrigatória
à Propriedade. Cada entidade possui seu próprio `poligono_geojson` opcional.
Não há cópia automática de polígonos das áreas para o contorno da Propriedade.

Os valores `area_total_ha` e `area_ha` são áreas **informadas pelo usuário**.
Salvar/editar/limpar uma delimitação não substitui esses valores. Não foi
introduzido cálculo de hectares em graus ou medição geodésica nesta etapa.

### Áreas de Plantio independentes

**Não implementadas.** A FK atual foi preservada. Não se criou Propriedade
fictícia nem se tornou a FK nullable sem autorização. Faltam decisões sobre:

1. Quem cria e administra uma área independente e como se define o responsável.
2. Como conceder/revogar usuários e aplicar os três perfis nesse ambiente.
3. Como selecionar o contexto e distinguir IDs de propriedade e área.
4. Como culturas, aplicações/colheitas, financeiro, documentos, equipe e histórico
   pertencem ao ambiente independente.
5. Como vincular/desvincular futuramente sem mover registros ou ampliar acessos.

Os testes T31–T34 condicionais não foram executados como validação de uma
funcionalidade inexistente. O restante do módulo trabalha com Propriedades e
Áreas de Plantio vinculadas, usando o isolamento já aprovado.

## E. Polígonos e validação

O contrato de escrita mantém Polygon, MultiPolygon ou Feature poligonal. A
leitura também aceita FeatureCollection poligonal legada válida, sem migrar ou
reescrever o texto salvo. Entrada antiga inválida continua preservada no banco
e é sinalizada como não exibível, sem interromper o restante do mapa.

Limites técnicos de recurso: 100 KiB de GeoJSON UTF-8; profundidade 32;
20.000 nós JSON; 5.000 posições; 256 anéis e 128 partes. Não são regras de
negócio territorial. JSON não finito, estruturas circulares internas, tipos
incorretos, vértices insuficientes, anéis abertos, coordenadas fora de faixa e
geometrias inválidas são rejeitados. O backend lê no máximo limite+1 bytes
antes de interpretar JSON, evitando parse recursivo fora desse controle.

Shapely verifica a topologia completa. Não se usa `make_valid`, `buffer(0)`,
simplificação, arredondamento ou reparo automático. Uma entrada inválida não
substitui a delimitação válida anterior.

### Comparação entre contorno e Área de Plantio

`comparar_limites` usa `covers`, incluindo toque na fronteira. Retorna
`contida`, `fora_do_limite`, `sem_delimitacao` ou `nao_verificavel`, com mensagem
informativa. Na ausência de uma regra de bloqueio aprovada, **não bloqueia o salvamento
nem recorta ou move geometrias**. Alterar o contorno reavalia os avisos das áreas.
Ausência de geometria não impede os outros módulos.

A comparação é topológica/operacional, não medição cadastral. Travessias do
antimeridiano exigem tratamento geográfico específico e são classificadas como
não verificáveis pela comparação planar. Não há PostGIS, GPS em tempo real,
shapefile/KML ou integração oficial cadastral.

## F. Segurança e auditoria

São preservados login, validação de usuário/epoch, vínculo ativo, propriedade
selecionada e CSRF. As rotas usam as permissões existentes `mapa.view` e
`mapa.edit`: Administrador/Gerente podem editar somente no ambiente autorizado;
Trabalhador consulta. Não foi criada regra local de perfil que contorne a matriz.

O ID de Propriedade em uma rota de alteração deve corresponder ao contexto
**ativo**, mesmo que o usuário tenha outro vínculo legítimo. IDs de Gleba são
consultados junto à propriedade. Identificadores manipulados/fora da faixa são
recusados antes de binds SQL incompatíveis.

Os eventos diferenciam `propriedade` e `gleba`, ator, operação e contexto, sem
GeoJSON ou coordenadas nos logs. Validação e tentativas indevidas são auditadas
pelos fluxos correspondentes. Falha de auditoria mantém o contrato independente
das operações de mapa; não apaga a delimitação já confirmada.

## G. Banco de dados e dependências

Migration criada e validada nesta implementação:
`e4ca60b1d732_add_propriedade_poligono.py`, posterior a `d3b94f5a0c21`.
Acrescenta somente TEXT nullable na Propriedade, sem default/backfill, sem alterar
IDs, responsáveis, polígonos de Gleba ou campos de hectares. Instalações antigas
não precisam fornecer contorno. O downgrade verifica o conteúdo antes de DDL e
recusa a remoção da coluna se houver qualquer valor não NULL, inclusive conteúdo
legado vazio/inválido, para evitar perda silenciosa.
Antes de aplicar ou reverter, faça backup verificável, valide uma cópia e
suspenda as escritas em janela de manutenção. Nenhuma base real foi migrada
durante esta etapa.

Shapely `>=2.2,<3` foi escolhido porque topologia de anéis, autointerseção,
MultiPolygon e contenção exigiriam algoritmos complexos manuais. Usa GEOS no
processo, sem serviço novo e sem depender do banco. Ambiente executado:
Shapely 2.2.0, NumPy 2.5.4, Python 3.12.14; `pip check` passou. Distribuições
oficiais CPython 3.12 Linux e Windows amd64 foram verificadas. Isso confirma
disponibilidade de instalação Windows, **não** execução da suíte em Windows.
A versão usa Python >=3.11, compatível com a versão documentada do projeto.

Leaflet 1.9.4 e Leaflet.draw 1.0.4 são as mesmas bibliotecas anteriores. Seus
arquivos locais são obtidos das distribuições oficiais npm com SHA-512 do
arquivo de distribuição verificado, hashes individuais e licenças preservadas.
O manifesto de proveniência permite conferir versões e integridade. Não se
desativou TLS nem se usaram mocks para substituir a biblioteca nos testes.

## H. Compatibilidade

Permanece o contrato superior `/mapa/dados` com exatamente `propriedade` e
`glebas`. Seus objetos internos são ampliados. Rotas antigas de Gleba e seus
eventos de atualização/remoção permanecem; rotas novas tratam apenas o contorno
da Propriedade. Nenhuma leitura altera geometrias legadas.

As regras de criação/edição de propriedade, contas compartilhadas e acesso do
Trabalhador a apenas agregados financeiros/equipe foram preservadas. Registros
agrícolas continuam vinculados às mesmas Glebas/CulturaGleba.

## I. Testes

Todos os testes utilizaram dados sintéticos e bancos descartáveis. Comandos
finais na raiz do projeto:

```bash
.venv/bin/python -m compileall -q src tests
.venv/bin/python -m pytest -q --junitxml=/tmp/connectagro-stage5/full-final.xml
node --check src/app/static/js/mapa.js
node --check src/app/static/js/mapa-loader.js
.venv/bin/python -m pip check
git diff --check
```

**Resultado final: 807 executados, 807 aprovados, zero falhas, zero erros e zero
ignorados, em 209,98 s; exit 0.** São 120 novos casos de mapa/território/migration,
sem remover casos anteriores. Há 60 avisos de depreciação de `get_engine()` em
`migrations/env.py`, sem impedir migrations. Compilação, sintaxe JavaScript,
integridade dos 19 arquivos oficiais locais e dependências foram verificadas.

| Execução concluída | Resultado |
| --- | --- |
| Suíte completa no código final | **807 aprovados**, zero falhas/erros/ignorados; **209,98 s** |
| Navegador real no código final | **230 assertivas aprovadas**, zero falhas e zero erros JavaScript não tratados |
| Interface/contratos após fase C | 102 testes aprovados; 44,87 s |
| Inicialização reutilizável do ambiente | Script testado com SQLite/uploads novos: migrations e4, catálogo, seed explícito, health, login/CSRF e mapa vazio aprovados; servidor encerrado |
| Base Etapa 04 antes da evolução territorial | 687 testes aprovados; 115 assertivas UI; PostgreSQL aprovado |
| Fase A: validação e leitura geométrica + mapa avançado existente | 138 aprovados, zero falhas; 83 casos novos + 55 existentes; 23,91 s |
| Fase B: território, migrations, geometria e regressões de mapas/áreas | 201 aprovados, zero falhas; 48,26 s |
| PostgreSQL 16.15 descartável | Upgrade d3→e4, snapshot de 13 tabelas históricas e das colunas antigas da Propriedade, persistência e proteção de downgrade aprovados; 16 payloads inválidos400, 16 acessos cruzados404 e quatro escritas de Trabalhador403 |

Evidência da fase A: `/tmp/connectagro-stage5/geometria-fase-a.xml` e `.log`.
Não foram executados testes em banco real. A fase B inclui cinco testes de
migration real SQLite, snapshot de 13 tabelas históricas e das colunas antigas da Propriedade e reinicialização de aplicativo/
engine. O PostgreSQL repetiu upgrade/idempotência/db check e downgrade seguro;
três tentativas de downgrade com contorno não NULL abortaram sem alterar dados
ou revisão. Os 16 payloads inválidos preservaram os bytes exatos da delimitação
anterior. Logs de negativas persistiram com tipos compatíveis, sem GeoJSON.
Evidências: `/tmp/connectagro-stage5/territorio-fase-b.xml`, `.log`,
`postgres.py`, `postgres.json` e `postgres.log`. O container PostgreSQL foi
removido ao final, com código de saída 0.

As instruções `start_skill` do ambiente foram atualizadas no rascunho com o
startup descartável testado em `/tmp/connectagro-stage5/start-cloud.sh` e seu
log, preservando o script de instalação existente. O teste não usou nem migrou
o banco de desenvolvimento anterior. Salvar essas instruções não aplica a rede,
não publica o ambiente e não comprova restauração em nova tarefa; revisão,
salvamento e publicação pelo produto continuam separados.

## J. Pendências

- Modelagem/autorização de Áreas de Plantio independentes, detalhada na seção D.
- Regra funcional de bloqueio/aceitação de área fora do contorno; por enquanto
  a detecção informa e não bloqueia.
- Cálculo geodésico de área em hectares não foi implementado; valores informados
  permanecem distintos de qualquer estimativa futura.
- API GitHub retornou `Forbidden` nas chamadas GraphQL e REST, enquanto pushes
  Git nativos funcionaram. `api.github.com` foi acrescentado ao rascunho de rede,
  preservando os domínios anteriores. Salvar o rascunho não aplica a política;
  review/salvamento/publicação pelo produto são separados.
- A cartografia externa OpenStreetMap **não foi validada como disponível**:
  uma sonda com proxy/CA herdados para `a.tile.openstreetmap.org` recebeu CONNECT
  403 (curl exit 56, HTTP 000). Os vetores/editor/texto foram validados com
  Leaflet e Draw reais locais. O aviso de indisponibilidade também foi exercitado
  por falha controlada de tiles. Não se usou mock para substituir a biblioteca.

## K. Conclusão e GitHub

O sistema diferencia e edita contornos de Propriedade e Áreas de Plantio
vinculadas, com validação geométrica, persistência, permissões e isolamento
verificados. **Está preparado para a Etapa 06 no modelo de ambientes já
aprovado**, preservando os relacionamentos operacionais. Áreas independentes
continuam pendentes das decisões da seção D; não são apresentadas como prontas.

Branch de entrega: `codex/etapa-05-mapas-territorio`. A base de revisão é
`codex/etapa-04-permissoes-usuarios`, commit
`7cb745687af9431857cbe77a53fd3cc145cda0d1`. O commit exclusivo desta etapa e sua
confirmação remota são apresentados na entrega final e no histórico Git. O
conjunto de arquivos foi revisado sem incluir bancos, logs, backups, credenciais
reais ou auxiliares de teste em /tmp. As etapas anteriores estão em commits
separados, com a dependência explícita; este delta não é apresentado como
alterações isoladas sobre uma main antiga.

O PR automático ficou impedido pelo acesso à API, e nenhum número/link de PR foi
inventado. A comparação de revisão deve usar Etapa 04 como base e Etapa 05 como
head. Não houve merge automático na `main`.


### Evidências de interface e rastreabilidade dos cenários

Resumo: `/tmp/connectagro-stage5/ui-summary.md`; runner e interações:
`/tmp/stage5-ui-driver.py` e `/tmp/stage5-ui.js`. Resultado, persistência e nove
screenshots em `/tmp/connectagro-stage5-ui-08w2yfnv/`; log
`/tmp/connectagro-stage5/ui-final.log`. Servidor encerrado no finally, exit 0.
Desktop 1440px, tablet 820px e celular 390px foram verificados sem overflow nas
telas testadas. Os três perfis usaram login/CSRF reais. Desenho por cliques e
edição por arraste alteraram de fato o SVG antes dos salvamentos reais HTTP.

Foram usados HTTP400/403 e falha de rede simulados para verificar retenção de
rascunho; sucessos, permissões, armazenamento e recarregamento usaram o aplicativo
e banco reais. O contexto vazio não tinha contorno nem qualquer Área de Plantio;
texto, mapa e editor autorizado continuaram utilizáveis. Coleção legada foi
convertida somente após confirmação, mantendo todas as partes/furos. Feature
simples preservou suas properties. Os snapshots confirmam hectares/IDs/histórico,
outros ambientes e conteúdo legado inválido intactos.

A UI encontrou dois defeitos de produto durante a validação: enquadramento
incorreto na troca rápida durante animação e execução de Draw quando Leaflet
falhava. Ambos foram corrigidos e receberam regressão na rodada final. Também
houve ajustes no harness (debounce dos cliques, vértice encoberto, seleção de
locators e espera de reload cancelado); nenhuma assertiva de autorização ou
integridade foi removida. Uma rodada completa anterior passou em 807 testes;
a rodada final foi repetida após as correções do navegador. Execuções parciais
interrompidas para corrigir essas falhas não foram contadas como suíte concluída.

| Cenários solicitados | Cobertura efetivamente executada |
| --- | --- |
| T01–T05 | API territorial, SQLite/PostgreSQL, reinicialização e navegador: contorno opcional, salvar/editar/limpar sem excluir Propriedade |
| T06–T10 | Geometrias distintas por área, parte/furo preservados e snapshots de CulturaGleba/Aplicação/Colheita sem mover histórico |
| T11–T18 | 83 testes de geometria e negativas HTTP reais: tipos, anéis, topologia, coordenadas, tamanho/complexidade e preservação anterior |
| T19–T24 | Login, worker403, gerente autorizado, IDs cruzados404, contexto ativo e CSRF em SQLite/PostgreSQL/navegador |
| T25–T30 | Legado válido exibido, inválido preservado sem erro, migration segura, contexto totalmente vazio e suíte anterior mantida |
| T31–T34 | **Condicionais não implementados/não executados para áreas independentes**; impedimentos da seção D, sem FK opcional ou Propriedade fictícia |
| T35–T38 | Eventos distinguem Propriedade/Gleba, falhas e negativas registradas, sem GeoJSON/coordenadas nos logs |
| T39–T44 | 230 assertivas UI reais: várias áreas, seleção, troca A/B, rascunho/erros, leitura por Trabalhador e três tamanhos de tela |

## Inventário absoluto da Etapa 05

Delta exclusivo em relação à Etapa 04; não inclui o commit-base anterior.

```text
/workspace/Connectagro/.gitattributes
/workspace/Connectagro/README.md
/workspace/Connectagro/docs/03-regras-de-negocio.md
/workspace/Connectagro/docs/04-modelagem-banco-der.md
/workspace/Connectagro/docs/05-dicionario-de-dados.md
/workspace/Connectagro/docs/06-1-arquitetura-tecnica-mvp.md
/workspace/Connectagro/docs/auditoria/05-mapas-organizacao-territorial.md
/workspace/Connectagro/migrations/versions/e4ca60b1d732_add_propriedade_poligono.py
/workspace/Connectagro/requirements.txt
/workspace/Connectagro/src/app/blueprints/glebas/routes.py
/workspace/Connectagro/src/app/blueprints/mapa/routes.py
/workspace/Connectagro/src/app/models/propriedade.py
/workspace/Connectagro/src/app/services/mapa_service.py
/workspace/Connectagro/src/app/static/css/main.css
/workspace/Connectagro/src/app/static/js/mapa-loader.js
/workspace/Connectagro/src/app/static/js/mapa.js
/workspace/Connectagro/src/app/static/vendor/README.md
/workspace/Connectagro/src/app/static/vendor/leaflet-1.9.4/LICENSE
/workspace/Connectagro/src/app/static/vendor/leaflet-1.9.4/images/layers-2x.png
/workspace/Connectagro/src/app/static/vendor/leaflet-1.9.4/images/layers.png
/workspace/Connectagro/src/app/static/vendor/leaflet-1.9.4/images/marker-icon-2x.png
/workspace/Connectagro/src/app/static/vendor/leaflet-1.9.4/images/marker-icon.png
/workspace/Connectagro/src/app/static/vendor/leaflet-1.9.4/images/marker-shadow.png
/workspace/Connectagro/src/app/static/vendor/leaflet-1.9.4/leaflet.css
/workspace/Connectagro/src/app/static/vendor/leaflet-1.9.4/leaflet.js
/workspace/Connectagro/src/app/static/vendor/leaflet-draw-1.0.4/LICENSE
/workspace/Connectagro/src/app/static/vendor/leaflet-draw-1.0.4/images/layers-2x.png
/workspace/Connectagro/src/app/static/vendor/leaflet-draw-1.0.4/images/layers.png
/workspace/Connectagro/src/app/static/vendor/leaflet-draw-1.0.4/images/marker-icon-2x.png
/workspace/Connectagro/src/app/static/vendor/leaflet-draw-1.0.4/images/marker-icon.png
/workspace/Connectagro/src/app/static/vendor/leaflet-draw-1.0.4/images/marker-shadow.png
/workspace/Connectagro/src/app/static/vendor/leaflet-draw-1.0.4/images/spritesheet-2x.png
/workspace/Connectagro/src/app/static/vendor/leaflet-draw-1.0.4/images/spritesheet.png
/workspace/Connectagro/src/app/static/vendor/leaflet-draw-1.0.4/images/spritesheet.svg
/workspace/Connectagro/src/app/static/vendor/leaflet-draw-1.0.4/leaflet.draw.css
/workspace/Connectagro/src/app/static/vendor/leaflet-draw-1.0.4/leaflet.draw.js
/workspace/Connectagro/src/app/static/vendor/mapa-dependencias.json
/workspace/Connectagro/src/app/templates/mapa/index.html
/workspace/Connectagro/tests/README.md
/workspace/Connectagro/tests/test_mapa_geometria.py
/workspace/Connectagro/tests/test_mapa_migration.py
/workspace/Connectagro/tests/test_mapa_territorio.py
```
