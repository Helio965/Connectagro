# 05 — Dicionário de Dados

## Status do documento

**Dicionário de Dados — v0.4 (alinhado aos modelos SQLAlchemy implementados).**

Detalha as tabelas e campos derivados do [DER](./04-modelagem-banco-der.md) e está
**alinhado** a ele (mesmos nomes de tabelas e campos), servindo como **referência
documental dos modelos SQLAlchemy já implementados** em `src/app/models/`. O schema
real é criado por migrations (`flask --app src/run.py db upgrade`) ou, em uso
pontual de desenvolvimento, por `flask --app src/run.py init-db`. O banco real,
uploads e arquivos locais continuam fora do versionamento.

A Fase 6.3 não altera schema: as permissões finas usam o campo já existente
`usuario.perfil` e a matriz em código `PERMISSOES_POR_PERFIL` em
`src/app/utils/permissions.py`, sem tabela nova de roles/permissões e sem
migration.

A Fase 6.5 também não altera schema: a revisão final consolida documentação,
testes e checklist de entrega sem criar model, migration, tabela ou dependência.

A Fase 7.1 adiciona a tabela `usuario_propriedade`, usada pelo painel interno de
usuários para vincular contas à propriedade atual. O campo
`propriedade.usuario_id` permanece no schema para compatibilidade com bases
anteriores.

## Objetivo

Documentar, de forma padronizada, cada tabela do MVP e seus campos: nome, tipo,
obrigatoriedade, chave, descrição e observações.

## Convenções

- Tabelas e colunas em `snake_case`.
- Toda tabela principal possui `id` INTEGER, PK, autoincremento.
- Datas/horas em **ISO 8601**, armazenadas como `TEXT`.
- "Obrigatório = Não" indica campo que pode ser `NULL`.
- **Booleanos** documentados como `BOOLEAN`, armazenados como `0`/`1` no SQLite.
- Campos de **lista** podem ser `TEXT` com **JSON** no MVP, com normalização
  prevista para o futuro.
- Tipos referem-se às afinidades do SQLite (`INTEGER`, `TEXT`, `REAL`,
  `BOOLEAN`).

> **Pendências e limites importantes do MVP:**
> - **Preço** (`produto_preco`) e **imagem** (`produto_imagem`) ficam
>   **pendentes**: `valor`/`url` podem ser `NULL` e `status_validacao` indica
>   `pendente`/`nao_consolidado`. Nunca inventar valores.
> - A **validação diária do menor preço** fica para o **sistema final**.
> - **Não existe validação AGROFIT/MAPA presumida**; o catálogo é base técnica
>   inicial, não base regulatória definitiva.
> - O sistema **não vende** produtos e **não é marketplace**.
> - Uploads ficam fora de `static`; o Upload não faz OCR, IA ou extração
>   automática de conteúdo no MVP.

---

## Gestão e acesso

### Tabela: `usuario`
Usuários do sistema (autenticação e perfil de acesso).

| Campo         | Tipo    | Obrigatório | Chave | Descrição                       | Observações                       |
|---------------|---------|-------------|-------|---------------------------------|-----------------------------------|
| id            | INTEGER | Sim         | PK    | Identificador único             | Autoincremento                    |
| nome          | TEXT    | Sim         |       | Nome do usuário                 |                                   |
| email         | TEXT    | Sim         |       | E-mail de login                 | Único                             |
| senha_hash    | TEXT    | Sim         |       | Hash da senha                   | Nunca armazenar senha em texto puro |
| perfil        | TEXT    | Sim         |       | Perfil de acesso                | `admin`, `tecnico`, `trabalhador` |
| ativo         | BOOLEAN | Sim         |       | Usuário ativo                   | `0`/`1`; padrão `1`               |
| criado_em     | TEXT    | Sim         |       | Data/hora de criação            | ISO 8601                          |
| atualizado_em | TEXT    | Não         |       | Data/hora da última atualização | ISO 8601                          |

Observação: permissões por perfil são resolvidas em código, não por tabela de
permissões. A sessão guarda o perfil atual em `user_perfil` e os templates usam
`can(...)` como apoio visual; o bloqueio obrigatório acontece nas rotas com
`require_permission(...)`.

### Tabela: `propriedade`
Propriedade rural gerida pelo usuário.

| Campo         | Tipo    | Obrigatório | Chave | Descrição                | Observações            |
|---------------|---------|-------------|-------|--------------------------|------------------------|
| id            | INTEGER | Sim         | PK    | Identificador único      | Autoincremento         |
| usuario_id    | INTEGER | Sim         | FK    | Usuário dono             | FK para `usuario(id)`  |
| nome          | TEXT    | Sim         |       | Nome da propriedade      |                        |
| municipio     | TEXT    | Não         |       | Município                |                        |
| uf            | TEXT    | Não         |       | Unidade federativa       | Sigla (ex.: `MT`)      |
| area_total_ha | REAL    | Não         |       | Área total em hectares   |                        |
| criado_em     | TEXT    | Sim         |       | Data/hora de criação     | ISO 8601               |
| atualizado_em | TEXT    | Não         |       | Data/hora de atualização | ISO 8601               |

Observação: `usuario_id` continua indicando o dono legado/original da propriedade.
O acesso operacional do painel de usuários usa a associação explícita em
`usuario_propriedade`.

### Tabela: `usuario_propriedade`
Associação entre usuários e propriedades no MVP ampliado.

| Campo          | Tipo    | Obrigatório | Chave | Descrição                         | Observações                                |
|----------------|---------|-------------|-------|-----------------------------------|--------------------------------------------|
| id             | INTEGER | Sim         | PK    | Identificador único               | Autoincremento                             |
| usuario_id     | INTEGER | Sim         | FK    | Usuário vinculado                 | FK para `usuario(id)`                      |
| propriedade_id | INTEGER | Sim         | FK    | Propriedade vinculada             | FK para `propriedade(id)`                  |
| ativo          | BOOLEAN | Sim         |       | Vínculo ativo                     | `0`/`1`; acompanha inativação pelo painel  |
| criado_por_id  | INTEGER | Não         | FK    | Usuário que criou o vínculo       | FK para `usuario(id)`                      |
| criado_em      | TEXT    | Sim         |       | Data/hora de criação              | ISO 8601                                   |
| atualizado_em  | TEXT    | Não         |       | Data/hora da última atualização   | ISO 8601                                   |

Restrições: o par (`usuario_id`, `propriedade_id`) é único. O painel não faz
remoção física de usuários; a inativação marca `usuario.ativo = 0` e
`usuario_propriedade.ativo = 0`.

### Tabela: `equipe_membro`
Membros da equipe vinculados a uma propriedade.

| Campo          | Tipo    | Obrigatório | Chave | Descrição                | Observações                  |
|----------------|---------|-------------|-------|--------------------------|------------------------------|
| id             | INTEGER | Sim         | PK    | Identificador único      | Autoincremento               |
| propriedade_id | INTEGER | Sim         | FK    | Propriedade do membro    | FK para `propriedade(id)`    |
| nome           | TEXT    | Sim         |       | Nome do membro           |                              |
| funcao         | TEXT    | Não         |       | Função/papel             | Pode refinar permissões futuramente |
| email          | TEXT    | Não         |       | E-mail de contato        |                              |
| telefone       | TEXT    | Não         |       | Telefone de contato      |                              |
| ativo          | BOOLEAN | Sim         |       | Membro ativo             | `0`/`1`; padrão `1`          |
| criado_em      | TEXT    | Sim         |       | Data/hora de criação     | ISO 8601                     |
| atualizado_em  | TEXT    | Não         |       | Data/hora de atualização | ISO 8601                     |

---

## Operação agrícola

### Tabela: `cultura`
Culturas cadastradas na propriedade.

| Campo          | Tipo    | Obrigatório | Chave | Descrição                | Observações                                       |
|----------------|---------|-------------|-------|--------------------------|---------------------------------------------------|
| id             | INTEGER | Sim         | PK    | Identificador único      | Autoincremento                                    |
| propriedade_id | INTEGER | Sim         | FK    | Propriedade da cultura   | FK para `propriedade(id)`                         |
| nome           | TEXT    | Sim         |       | Nome da cultura          | Ex.: soja, milho                                  |
| variedade      | TEXT    | Não         |       | Variedade/cultivar       |                                                   |
| safra          | TEXT    | Não         |       | Identificação da safra   | Ex.: `2025/2026`                                  |
| data_inicio    | TEXT    | Não         |       | Início da cultura        | ISO 8601                                          |
| data_fim       | TEXT    | Não         |       | Fim da cultura           | ISO 8601                                          |
| status         | TEXT    | Sim         |       | Situação da cultura      | `planejada`, `em_andamento`, `colhida`, `cancelada` |
| criado_em      | TEXT    | Sim         |       | Data/hora de criação     | ISO 8601                                          |
| atualizado_em  | TEXT    | Não         |       | Data/hora de atualização | ISO 8601                                          |

### Tabela: `gleba`
Áreas/talhões da propriedade.

| Campo            | Tipo    | Obrigatório | Chave | Descrição                  | Observações                          |
|------------------|---------|-------------|-------|----------------------------|--------------------------------------|
| id               | INTEGER | Sim         | PK    | Identificador único        | Autoincremento                       |
| propriedade_id   | INTEGER | Sim         | FK    | Propriedade da gleba       | FK para `propriedade(id)`            |
| nome             | TEXT    | Sim         |       | Identificação da gleba     |                                      |
| area_ha          | REAL    | Não         |       | Área em hectares           |                                      |
| latitude         | REAL    | Não         |       | Latitude do ponto central  | Usada pelo mapa real simplificado    |
| longitude        | REAL    | Não         |       | Longitude do ponto central | Usada pelo mapa real simplificado    |
| poligono_geojson | TEXT    | Não         |       | Polígono da área (GeoJSON) | JSON em `TEXT`; somente leitura no mapa |
| tipo_solo        | TEXT    | Não         |       | Tipo de solo               |                                      |
| observacoes      | TEXT    | Não         |       | Texto livre                |                                      |
| criado_em        | TEXT    | Sim         |       | Data/hora de criação       | ISO 8601                             |
| atualizado_em    | TEXT    | Não         |       | Data/hora de atualização   | ISO 8601                             |

### Tabela: `cultura_gleba`
Associação N:N entre culturas e glebas.

| Campo       | Tipo    | Obrigatório | Chave | Descrição           | Observações               |
|-------------|---------|-------------|-------|---------------------|---------------------------|
| id          | INTEGER | Sim         | PK    | Identificador único | Autoincremento            |
| cultura_id  | INTEGER | Sim         | FK    | Cultura associada   | FK para `cultura(id)`     |
| gleba_id    | INTEGER | Sim         | FK    | Gleba associada     | FK para `gleba(id)`       |
| data_inicio | TEXT    | Não         |       | Início do uso       | ISO 8601                  |
| data_fim    | TEXT    | Não         |       | Fim do uso          | ISO 8601; `NULL` se ativo |
| observacoes | TEXT    | Não         |       | Texto livre         |                           |

### Tabela: `aplicacao_insumo`
Aplicação de um insumo do catálogo em uma cultura/gleba.

| Campo            | Tipo    | Obrigatório | Chave | Descrição                 | Observações                                  |
|------------------|---------|-------------|-------|---------------------------|----------------------------------------------|
| id               | INTEGER | Sim         | PK    | Identificador único       | Autoincremento                               |
| cultura_gleba_id | INTEGER | Sim         | FK    | Onde foi aplicado         | FK para `cultura_gleba(id)`                  |
| produto_base_id  | INTEGER | Sim         | FK    | Produto aplicado          | FK para `produto_base(id)`                   |
| data_aplicacao   | TEXT    | Sim         |       | Data da aplicação         | ISO 8601                                     |
| dose             | REAL    | Não         |       | Quantidade aplicada       | Histórica/informativa; não valida dose correta |
| unidade          | TEXT    | Não         |       | Unidade da dose           | Ex.: kg/ha, L/ha                             |
| responsavel      | TEXT    | Não         |       | Responsável pela aplicação|                                              |
| observacao       | TEXT    | Não         |       | Texto livre               | Registro não substitui orientação agronômica |
| criado_em        | TEXT    | Sim         |       | Data/hora de criação      | ISO 8601                                     |

### Tabela: `colheita_registro`
Registros de colheita por cultura/gleba.

| Campo            | Tipo    | Obrigatório | Chave | Descrição            | Observações                |
|------------------|---------|-------------|-------|----------------------|----------------------------|
| id               | INTEGER | Sim         | PK    | Identificador único  | Autoincremento             |
| cultura_gleba_id | INTEGER | Sim         | FK    | Cultura/gleba colhida| FK para `cultura_gleba(id)` |
| data_colheita    | TEXT    | Sim         |       | Data da colheita     | ISO 8601                   |
| quantidade       | REAL    | Não         |       | Quantidade colhida   |                            |
| unidade          | TEXT    | Não         |       | Unidade              | Ex.: sacas, ton            |
| qualidade        | TEXT    | Não         |       | Classificação/qualidade |                         |
| observacao       | TEXT    | Não         |       | Texto livre          |                            |
| criado_em        | TEXT    | Sim         |       | Data/hora de criação | ISO 8601                   |

---

## Catálogo de produtos

> Base técnica inicial de consulta rápida. **Preço e imagem são pendências no
> MVP.** Sem validação AGROFIT/MAPA presumida.

### Tabela: `produto_base`
Tabela central do catálogo.

| Campo              | Tipo    | Obrigatório | Chave | Descrição                  | Observações                                                                 |
|--------------------|---------|-------------|-------|----------------------------|-----------------------------------------------------------------------------|
| id                 | INTEGER | Sim         | PK    | Identificador único        | Autoincremento                                                              |
| nome               | TEXT    | Sim         |       | Nome principal do item     |                                                                             |
| slug               | TEXT    | Sim         |       | Versão amigável (URL/busca)| Único. Ex.: `glifosato`, `npk-04-14-08`, `calcario-dolomitico`              |
| classe             | TEXT    | Sim         |       | Grupo amplo                | Ex.: `defensivo`, `fertilizante`                                            |
| categoria          | TEXT    | Sim         |       | Categoria específica       | Ex.: `herbicida`, `inseticida`, `fungicida`, `mineral`, `organico`, `corretivo`, `inoculante` |
| descricao_curta    | TEXT    | Não         |       | Resumo                     |                                                                             |
| descricao_completa | TEXT    | Não         |       | Descrição detalhada        |                                                                             |
| status_sistema     | TEXT    | Sim         |       | Status interno do sistema  | `pre_cadastrado`, `cadastrado_usuario`, `definitivo`, `bloqueado_historico`  |
| status_regulatorio | TEXT    | Sim         |       | Status regulatório         | Enum MVP: `nao_validado_agrofit`, `atencao_regulatoria`, `sujeito_a_sipeagro_nao_validado`, `tipo_tecnico_generico`, `bloqueado_historico` |
| criado_em          | TEXT    | Sim         |       | Data/hora de criação       | ISO 8601                                                                    |
| atualizado_em      | TEXT    | Não         |       | Data/hora de atualização   | ISO 8601                                                                    |

**Regras (MVP):**

- **Defensivos** começam como `nao_validado_agrofit`, exceto itens de atenção,
  que usam `atencao_regulatoria` — nunca "validado oficialmente".
- **Fertilizantes, corretivos, inoculantes e biofertilizantes** usam
  `sujeito_a_sipeagro_nao_validado` ou `tipo_tecnico_generico` (este para
  genéricos como Ureia, MAP, DAP, Calcário Dolomítico, Esterco Bovino, Composto
  Orgânico).
- **Paraquate** permanece como `bloqueado_historico`; **Oxamil** não entra como
  recomendado no seed.
- **Nenhum item** deve ser marcado como validado oficialmente sem fonte real.
  Valores como `validado_agrofit`/`validado_sipeagro` só existirão após validação
  comprovada (não no MVP).
- A importação do catálogo é feita via CLI e popula `produto_base` e
  `produto_tecnico`; não cria preços, imagens, venda, carrinho, checkout ou
  cotação.

### Tabela: `produto_tecnico`
Informações técnicas do produto.

| Campo                 | Tipo    | Obrigatório | Chave | Descrição                  | Observações                                  |
|-----------------------|---------|-------------|-------|----------------------------|----------------------------------------------|
| id                    | INTEGER | Sim         | PK    | Identificador único        | Autoincremento. **No seed JSON pode ser omitido** (gerado no banco) |
| produto_id            | INTEGER | Sim         | FK    | Produto associado          | FK para `produto_base(id)`; vínculo usado no seed |
| grupo_quimico         | TEXT    | Não         |       | Grupo químico              | Principalmente defensivos                    |
| composicao            | TEXT    | Não         |       | Composição                 | Principalmente fertilizantes                 |
| nutrientes_principais | TEXT    | Não         |       | Nutrientes (ex.: NPK)      | Lista; JSON em `TEXT`; normalizar no futuro  |
| culturas_comuns       | TEXT    | Não         |       | Culturas usuais            | Lista; JSON em `TEXT`; normalizar no futuro  |
| alvos_controle        | TEXT    | Não         |       | Alvos de controle          | Defensivos; JSON em `TEXT`                   |
| uso_principal         | TEXT    | Não         |       | Uso principal              | Ex.: inseticida, fertilizante mineral        |
| modo_aplicacao        | TEXT    | Não         |       | Modo de aplicação          | `forma_aplicacao` do seed é mapeada para cá  |
| tipo_liberacao        | TEXT    | Não         |       | Tipo de liberação          | Fertilizantes (ex.: convencional, lenta)     |
| fonte_tecnica         | TEXT    | Não         |       | Origem da informação técnica | Não inventar; validar depois se ausente    |
| observacoes           | TEXT    | Não         |       | Texto livre                |                                              |

> **Seed técnico:** no arquivo JSON de seed, o campo `id` de `produto_tecnico`
> pode ser omitido. Na importação para o SQLite/ORM, o banco gera esse
> identificador automaticamente. O vínculo com `produto_base` é feito pelo campo
> `produto_id`.

### Tabela: `produto_preco`
Preços de **referência** (consulta rápida). **Pendência no MVP.**

| Campo            | Tipo    | Obrigatório | Chave | Descrição                | Observações                              |
|------------------|---------|-------------|-------|--------------------------|------------------------------------------|
| id               | INTEGER | Sim         | PK    | Identificador único      | Autoincremento                           |
| produto_id       | INTEGER | Sim         | FK    | Produto do preço         | FK para `produto_base(id)`               |
| valor            | REAL    | Não         |       | Valor de referência      | **Pendência**: `NULL` no MVP             |
| moeda            | TEXT    | Não         |       | Moeda                    | Ex.: `BRL`                               |
| unidade          | TEXT    | Não         |       | Unidade do preço         | Ex.: kg, L, ton                          |
| data_coleta      | TEXT    | Não         |       | Data da coleta           | ISO 8601                                 |
| fonte            | TEXT    | Não         |       | Origem do dado           |                                          |
| status_validacao | TEXT    | Sim         |       | Situação do dado         | MVP: `pendente`/`nao_consolidado`        |
| observacoes      | TEXT    | Não         |       | Texto livre              |                                          |
| criado_em        | TEXT    | Sim         |       | Data/hora de criação     | ISO 8601                                 |

> No sistema final, guardará o menor preço atualizado diariamente — sempre
> informativo, nunca venda, cotação oficial, oferta comercial, carrinho ou
> checkout.

### Tabela: `produto_imagem`
Imagem do produto. **Pendência no MVP.**

| Campo            | Tipo    | Obrigatório | Chave | Descrição             | Observações                       |
|------------------|---------|-------------|-------|-----------------------|-----------------------------------|
| id               | INTEGER | Sim         | PK    | Identificador único   | Autoincremento                    |
| produto_id       | INTEGER | Sim         | FK    | Produto da imagem     | FK para `produto_base(id)`        |
| url              | TEXT    | Não         |       | Caminho/URL da imagem | **Pendência**: `NULL` no MVP      |
| fonte            | TEXT    | Não         |       | Origem da imagem      | Não usar imagem sem fonte         |
| status_validacao | TEXT    | Sim         |       | Situação do dado      | MVP: `pendente`/`nao_consolidado` |
| observacoes      | TEXT    | Não         |       | Texto livre           |                                   |
| criado_em        | TEXT    | Sim         |       | Data/hora de criação  | ISO 8601                          |

---

## Financeiro, upload e IA

### Tabela: `financeiro_lancamento`
Lançamentos financeiros (receita/despesa).

| Campo          | Tipo    | Obrigatório | Chave | Descrição                 | Observações               |
|----------------|---------|-------------|-------|---------------------------|---------------------------|
| id             | INTEGER | Sim         | PK    | Identificador único       | Autoincremento            |
| propriedade_id | INTEGER | Sim         | FK    | Propriedade do lançamento | FK para `propriedade(id)` |
| tipo           | TEXT    | Sim         |       | Tipo do lançamento        | `receita` ou `despesa`    |
| categoria      | TEXT    | Não         |       | Categoria do lançamento   |                           |
| descricao      | TEXT    | Não         |       | Descrição                 |                           |
| valor          | REAL    | Sim         |       | Valor do lançamento       | Maior que zero nas rotas  |
| data           | TEXT    | Sim         |       | Data do lançamento        | ISO 8601                  |
| criado_em      | TEXT    | Sim         |       | Data/hora de criação      | ISO 8601                  |
| atualizado_em  | TEXT    | Não         |       | Data/hora de atualização  | ISO 8601                  |

### Tabela: `upload_arquivo`
Documentos/arquivos enviados.

| Campo          | Tipo    | Obrigatório | Chave | Descrição               | Observações               |
|----------------|---------|-------------|-------|-------------------------|---------------------------|
| id             | INTEGER | Sim         | PK    | Identificador único     | Autoincremento            |
| propriedade_id | INTEGER | Sim         | FK    | Propriedade do arquivo  | FK para `propriedade(id)` |
| nome_original  | TEXT    | Sim         |       | Nome do arquivo enviado |                           |
| caminho        | TEXT    | Sim         |       | Caminho relativo seguro | Fora de `static`; nunca absoluto |
| tipo_mime      | TEXT    | Não         |       | Tipo do arquivo         | Ex.: `application/pdf`    |
| tamanho        | INTEGER | Não         |       | Tamanho em bytes        |                           |
| descricao      | TEXT    | Não         |       | Descrição               |                           |
| enviado_em     | TEXT    | Sim         |       | Data/hora do upload     | ISO 8601                  |

### Tabela: `ia_interacao`
Interações com a camada de IA. **No MVP a IA é simulada.**

| Campo          | Tipo    | Obrigatório | Chave | Descrição               | Observações                            |
|----------------|---------|-------------|-------|-------------------------|----------------------------------------|
| id             | INTEGER | Sim         | PK    | Identificador único     | Autoincremento                         |
| usuario_id     | INTEGER | Sim         | FK    | Usuário da interação    | FK para `usuario(id)`                  |
| propriedade_id | INTEGER | Não         | FK    | Propriedade de contexto | FK para `propriedade(id)`              |
| pergunta       | TEXT    | Sim         |       | Entrada do usuário      |                                        |
| resposta       | TEXT    | Não         |       | Resposta gerada         | Apoio informativo, não recomendação definitiva |
| tipo           | TEXT    | Sim         |       | Tipo da interação       | `simulada`, `apoio`, `relatorio`, `duvida` |
| criado_em      | TEXT    | Sim         |       | Data/hora de criação    | ISO 8601                               |

---

## Documentos relacionados

- [04 — Modelagem do Banco (DER)](./04-modelagem-banco-der.md)
- [03 — Regras de Negócio](./03-regras-de-negocio.md)
- [08 — Checklist Final do MVP](./08-checklist-final-mvp.md)
- [Catálogo de Produtos](./catalogo-produtos/README.md)
