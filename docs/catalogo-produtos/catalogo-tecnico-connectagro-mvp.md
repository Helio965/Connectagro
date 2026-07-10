# Catálogo Técnico — ConnectAgro (MVP)

> **Documento humano principal do catálogo de produtos.** Base **técnica e
> documental** para cadastro e consulta no ConnectAgro. **Não é receituário
> agronômico** nem fonte regulatória oficial.

## Introdução

Este catálogo reúne uma lista inicial de **defensivos**, **fertilizantes**,
**corretivos**, **inoculantes** e **biofertilizantes** que servirá como base
técnica para o cadastro do MVP e como fonte futura do seed do banco. Ele está
alinhado à modelagem definida no [DER](../04-modelagem-banco-der.md) e no
[dicionário de dados](../05-dicionario-de-dados.md), com as tabelas
`produto_base`, `produto_tecnico`, `produto_preco` e `produto_imagem`.

O ConnectAgro **não vende produtos**. O catálogo existe para **consulta rápida**,
organização de insumos, apoio ao registro futuro de aplicação e documentação
técnica.

## Critérios de seleção

- Cobertura dos **ingredientes ativos / tipos de insumo** mais comuns na
  agricultura brasileira de grãos e culturas associadas.
- Representatividade por **categoria** (inseticida, fungicida, herbicida,
  acaricida, moluscicida; mineral, orgânico, organomineral, biofertilizante,
  inoculante, corretivo).
- Fertilizantes tratados como **tipos técnicos/genéricos** (não produtos
  comerciais específicos).
- Itens de **uso proibido/restrito** são mantidos apenas como histórico/bloqueado.

## Fontes consideradas

- Conhecimento técnico geral e literatura agronômica de domínio público
  (classes químicas, nutrientes, formas de aplicação).
- **Nenhuma** consulta automatizada a AGROFIT/MAPA ou SIPEAGRO/MAPA foi feita
  dentro do repositório. O campo `fonte_tecnica` está marcado como **pendente de
  validação por fonte oficial**.

## Limitações

- As informações **não substituem** a bula do produto, o cadastro oficial nem a
  orientação de um **engenheiro agrônomo**.
- **Culturas, alvos e doses** indicados são genéricos e exigem validação na bula
  e no AGROFIT antes de qualquer uso real.
- **Preço** e **imagem** **não** são consolidados no MVP (ver
  [pendências de validação](./pendencias-validacao.md)).
- O `status_regulatorio` é **informativo**: nenhum item está "validado
  oficialmente".

---

## Tabela de defensivos (pré-cadastrados)

> Todos com `status_sistema = pre_cadastrado`. `status_regulatorio` informativo —
> nenhum validado no AGROFIT.

| id | slug | nome | categoria | grupo químico | status_regulatorio |
|----|------|------|-----------|---------------|--------------------|
| 1 | `imidacloprido` | Imidacloprido | inseticida | Neonicotinoide | `nao_validado_agrofit` |
| 2 | `lambda-cialotrina` | Lambda-cialotrina | inseticida | Piretroide | `nao_validado_agrofit` |
| 3 | `clorpirifos` | Clorpirifós | inseticida | Organofosforado | `atencao_regulatoria` |
| 4 | `espinetoram` | Espinetoram | inseticida | Espinosina | `nao_validado_agrofit` |
| 5 | `metomil` | Metomil | inseticida | Carbamato (metilcarbamato de oxima) | `nao_validado_agrofit` |
| 6 | `abamectina` | Abamectina | acaricida | Avermectina | `nao_validado_agrofit` |
| 7 | `acefato` | Acefato | inseticida | Organofosforado | `nao_validado_agrofit` |
| 8 | `clorantraniliprole` | Clorantraniliprole | inseticida | Diamida antranílica | `nao_validado_agrofit` |
| 9 | `fipronil` | Fipronil | inseticida | Fenilpirazol | `nao_validado_agrofit` |
| 10 | `deltametrina` | Deltametrina | inseticida | Piretroide | `nao_validado_agrofit` |
| 11 | `mancozebe` | Mancozebe | fungicida | Ditiocarbamato | `nao_validado_agrofit` |
| 12 | `tebuconazol` | Tebuconazol | fungicida | Triazol | `nao_validado_agrofit` |
| 13 | `azoxistrobina` | Azoxistrobina | fungicida | Estrobilurina | `nao_validado_agrofit` |
| 14 | `ciproconazol` | Ciproconazol | fungicida | Triazol | `nao_validado_agrofit` |
| 15 | `captana` | Captana | fungicida | Ftalimida | `nao_validado_agrofit` |
| 16 | `difenoconazol` | Difenoconazol | fungicida | Triazol | `nao_validado_agrofit` |
| 17 | `clorotalonil` | Clorotalonil | fungicida | Isoftalonitrila | `nao_validado_agrofit` |
| 18 | `fluxapiroxade` | Fluxapiroxade | fungicida | Carboxamida (SDHI) | `nao_validado_agrofit` |
| 19 | `glifosato` | Glifosato | herbicida | Glicina substituída (aminoácido fosfonado) | `nao_validado_agrofit` |
| 20 | `atrazina` | Atrazina | herbicida | Triazina | `nao_validado_agrofit` |
| 21 | `2-4-d` | 2,4-D | herbicida | Ácido fenoxiacético (ariloxialcanoico) | `nao_validado_agrofit` |
| 22 | `s-metolacloro` | S-metolacloro | herbicida | Cloroacetamida | `nao_validado_agrofit` |
| 23 | `dicamba` | Dicamba | herbicida | Ácido benzoico | `nao_validado_agrofit` |
| 24 | `cletodim` | Cletodim | herbicida | Ciclohexanodiona (DIM) | `nao_validado_agrofit` |
| 25 | `clomazona` | Clomazona | herbicida | Isoxazolidinona | `nao_validado_agrofit` |
| 26 | `sulfentrazona` | Sulfentrazona | herbicida | Triazolinona | `nao_validado_agrofit` |
| 27 | `fluopiram` | Fluopiram | fungicida | Piridiniletil-benzamida (SDHI) | `nao_validado_agrofit` |
| 28 | `propargito` | Propargito | acaricida | Sulfito de organoenxofre | `nao_validado_agrofit` |
| 29 | `metaldeido` | Metaldeído | moluscicida | Aldeído (polímero do acetaldeído) | `nao_validado_agrofit` |
| 30 | `fosfato-ferrico` | Fosfato férrico | moluscicida | Composto inorgânico (fosfato de ferro) | `nao_validado_agrofit` |

---

## Tabela de fertilizantes / corretivos / inoculantes

> Tratados como **tipos técnicos/genéricos** no MVP. Minerais e comerciais como
> `sujeito_a_sipeagro_nao_validado`; orgânicos genéricos como
> `tipo_tecnico_generico`.

| id | slug | nome | categoria | nutrientes | status_regulatorio |
|----|------|------|-----------|------------|--------------------|
| 40 | `npk-04-14-08` | NPK 04-14-08 | mineral | N, P, K | `sujeito_a_sipeagro_nao_validado` |
| 41 | `npk-20-05-20` | NPK 20-05-20 | mineral | N, P, K | `sujeito_a_sipeagro_nao_validado` |
| 42 | `npk-10-10-10` | NPK 10-10-10 | mineral | N, P, K | `sujeito_a_sipeagro_nao_validado` |
| 43 | `ureia` | Ureia | mineral | N | `sujeito_a_sipeagro_nao_validado` |
| 44 | `sulfato-de-amonio` | Sulfato de amônio | mineral | N, S | `sujeito_a_sipeagro_nao_validado` |
| 45 | `nitrato-de-calcio` | Nitrato de cálcio | mineral | N, Ca | `sujeito_a_sipeagro_nao_validado` |
| 46 | `map` | MAP | mineral | N, P | `sujeito_a_sipeagro_nao_validado` |
| 47 | `dap` | DAP | mineral | N, P | `sujeito_a_sipeagro_nao_validado` |
| 48 | `superfosfato-simples` | Superfosfato simples | mineral | P, Ca, S | `sujeito_a_sipeagro_nao_validado` |
| 49 | `superfosfato-triplo` | Superfosfato triplo | mineral | P | `sujeito_a_sipeagro_nao_validado` |
| 50 | `cloreto-de-potassio` | Cloreto de potássio | mineral | K | `sujeito_a_sipeagro_nao_validado` |
| 51 | `fosfato-monopotassico-mkp` | Fosfato monopotássico MKP | mineral | P, K | `sujeito_a_sipeagro_nao_validado` |
| 52 | `nitrato-de-potassio` | Nitrato de potássio | mineral | N, K | `sujeito_a_sipeagro_nao_validado` |
| 53 | `sulfato-de-magnesio` | Sulfato de magnésio | mineral | Mg, S | `sujeito_a_sipeagro_nao_validado` |
| 54 | `enxofre-bentonita` | Enxofre bentonita | mineral | S | `sujeito_a_sipeagro_nao_validado` |
| 55 | `boro-granubor` | Fonte de boro (Granubor) | mineral | B | `sujeito_a_sipeagro_nao_validado` |
| 56 | `fosfato-natural-reativo` | Fosfato natural reativo | mineral | P | `sujeito_a_sipeagro_nao_validado` |
| 57 | `npk-s-granulado` | NPK+S granulado | mineral | N, P, K, S | `sujeito_a_sipeagro_nao_validado` |
| 58 | `esterco-bovino-curtido` | Esterco bovino curtido | organico | N, P, K, matéria orgânica | `tipo_tecnico_generico` |
| 59 | `cama-de-frango-curtida` | Cama de frango curtida | organico | N, P, K, matéria orgânica | `tipo_tecnico_generico` |
| 60 | `composto-organico` | Composto orgânico | organico | matéria orgânica, N, P, K | `tipo_tecnico_generico` |
| 61 | `humus-de-minhoca` | Húmus de minhoca | organico | matéria orgânica, N | `tipo_tecnico_generico` |
| 62 | `torta-de-mamona` | Torta de mamona | organico | N, matéria orgânica | `tipo_tecnico_generico` |
| 63 | `organomineral-npk-granulado` | Organomineral NPK granulado | organomineral | N, P, K, matéria orgânica | `sujeito_a_sipeagro_nao_validado` |
| 64 | `biofertilizante-liquido-fermentado` | Biofertilizante líquido fermentado | biofertilizante | nutrientes diversos, matéria orgânica | `sujeito_a_sipeagro_nao_validado` |
| 65 | `extrato-de-algas` | Extrato de algas | biofertilizante | nutrientes diversos, bioativos | `sujeito_a_sipeagro_nao_validado` |
| 66 | `inoculante-bradyrhizobium-soja` | Inoculante Bradyrhizobium para soja | inoculante | N (biológico) | `sujeito_a_sipeagro_nao_validado` |
| 67 | `inoculante-azospirillum-milho` | Inoculante Azospirillum para milho | inoculante | N (biológico) | `sujeito_a_sipeagro_nao_validado` |
| 68 | `calcario-dolomitico` | Calcário dolomítico | corretivo | Ca, Mg | `sujeito_a_sipeagro_nao_validado` |
| 69 | `gesso-agricola` | Gesso agrícola | corretivo | Ca, S | `sujeito_a_sipeagro_nao_validado` |

---

## Itens bloqueados / históricos

> **Não** entram como itens ativos recomendados e **não** são aplicáveis ao
> registro de aplicação de insumos (`aplicacao_insumo`). Constam apenas em
> `itens_bloqueados_ou_excluidos` no seed.

| id | slug | nome | classe | status_sistema | motivo |
|----|------|------|--------|----------------|--------|
| 90 | `paraquate` | Paraquate | defensivo | `bloqueado_historico` | Uso proibido no Brasil (banido pela Anvisa). Mantido apenas como item histórico/bloqueado. Não recomendado e não aplicável ao registro de aplicação de insumos. |
| 91 | `oxamil` | Oxamil | defensivo | `excluido_do_seed` | Não incluído como item ativo recomendado no seed do MVP. Mantido apenas como registro de exclusão. |

---

## Pendências de validação

Resumo (detalhes em [pendencias-validacao.md](./pendencias-validacao.md)):

- **Defensivos:** validação AGROFIT/MAPA **pendente**.
- **Fertilizantes:** validação SIPEAGRO/MAPA **pendente**.
- **Preço:** pendente / não consolidado (tabela `produto_preco` vazia).
- **Imagem:** uma referência local por produto, com fonte/licença rastreadas e
  status não consolidado; imagens oficiais/do fabricante seguem pendentes.
- **Fabricante / produto comercial:** pendente (itens são genéricos).
- **Fonte técnica:** pendente de validação oficial.

---

## Regras para uso futuro no banco

- O seed deve popular **`produto_base`** + **`produto_tecnico`** +
  **`produto_imagem`**; `produto_preco` permanece vazio no MVP.
- Usar os **mesmos `id`/`slug`/`classe`** definidos aqui e no seed JSON/CSV.
- `slug` é **único**, minúsculo, sem acentos, separado por hífen.
- Itens **bloqueados/excluídos** (Paraquate, Oxamil) **não** devem ser
  oferecidos para registro de aplicação.
- Nenhum **preço** nem **imagem** deve ser inserido como definitivo sem fonte/
  licença rastreável.
- A **validação diária do menor preço** é funcionalidade do **sistema final**.

---

## Documentos relacionados

- [Catálogo de Produtos — README](./README.md)
- [Pendências de Validação](./pendencias-validacao.md)
- [04 — Modelagem do Banco (DER)](../04-modelagem-banco-der.md)
- [05 — Dicionário de Dados](../05-dicionario-de-dados.md)
- [Seeds](../../data/seeds/README.md)
