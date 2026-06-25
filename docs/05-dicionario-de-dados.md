# 05 — Dicionário de Dados

## Status do documento

**Dicionário de dados preliminar — v0.2 (MVP).**

Detalha as tabelas e campos derivados do [DER preliminar](./04-modelagem-banco-der.md)
e está **alinhado** a ele (mesmos nomes de tabelas e campos). Serve de fonte
confiável para a futura implementação em **SQLite**. **Nenhum banco, migration ou
seed definitivo é criado nesta etapa.**

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

---

## Gestão e acesso

### Tabela: `usuario`
Usuários do sistema (autenticação).

| Campo         | Tipo    | Obrigatório | Chave | Descrição                       | Observações                       |
|---------------|---------|-------------|-------|---------------------------------|-----------------------------------|
| id            | INTEGER | Sim         | PK    | Identificador único             | Autoincremento                    |
| nome          | TEXT    | Sim         |       | Nome do usuário                 |                                   |
| email         | TEXT    | Sim         |       | E-mail de login                 | Único                             |
| senha_hash    | TEXT    | Sim         |       | Hash da senha                   | Nunca armazenar senha em texto puro|
| perfil        | TEXT    | Sim         |       | Perfil de acesso                | `admin`, `produtor`, `membro`     |
| ativo         | BOOLEAN | Sim         |       | Usuário ativo                   | `0`/`1`; padrão `1`               |
| criado_em     | TEXT    | Sim         |       | Data/hora de criação            | ISO 8601                          |
| atualizado_em | TEXT    | Não         |       | Data/hora da última atualização | ISO 8601                          |

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

### Tabela: `equipe_membro`
Membros da equipe vinculados a uma propriedade.

| Campo          | Tipo    | Obrigatório | Chave | Descrição                | Observações                  |
|----------------|---------|-------------|-------|--------------------------|------------------------------|
| id             | INTEGER | Sim         | PK    | Identificador único      | Autoincremento               |
| propriedade_id | INTEGER | Sim         | FK    | Propriedade do membro    | FK para `propriedade(id)`    |
| nome           | TEXT    | Sim         |       | Nome do membro           |                              |
| funcao         | TEXT    | Não         |       | Função/papel             | Pode condicionar permissões  |
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
| status         | TEXT    | Sim         |       | Situação da cultura      | `planejada`, `em_andamento`, `colhida`, `cancelada`|
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
| latitude         | REAL    | Não         |       | Latitude do ponto central  |                                      |
| longitude        | REAL    | Não         |       | Longitude do ponto central |                                      |
| poligono_geojson | TEXT    | Não         |       | Polígono da área (GeoJSON) | Mapa real futuro; JSON em `TEXT`     |
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

| Campo            | Tipo    | Obrigatório | Chave | Descrição                | Observações                                  |
|------------------|---------|-------------|-------|--------------------------|----------------------------------------------|
| id               | INTEGER | Sim         | PK    | Identificador único      | Autoincremento                               |
| cultura_gleba_id | INTEGER | Sim         | FK    | Onde foi aplicado        | FK para `cultura_gleba(id)`                  |
| produto_base_id  | INTEGER | Sim         | FK    | Produto aplicado         | FK para `produto_base(id)`                   |
| data_aplicacao   | TEXT    | Sim         |       | Data da aplicação        | ISO 8601                                     |
| dose             | REAL    | Não         |       | Quantidade aplicada      |                                              |
| unidade          | TEXT    | Não         |       | Unidade da dose          | Ex.: kg/ha, L/ha                             |
| responsavel      | TEXT    | Não         |       | Responsável pela aplicação|                                             |
| observacao       | TEXT    | Não         |       | Texto livre              | Registro não substitui orientação agronômica |
| criado_em        | TEXT    | Sim         |       | Data/hora de criação     | ISO 8601                                     |

### Tabela: `colheita_registro`
Registros de colheita por cultura/gleba.

| Campo            | Tipo    | Obrigatório | Chave | Descrição           | Observações                 |
|------------------|---------|-------------|-------|---------------------|-----------------------------|
| id               | INTEGER | Sim         | PK    | Identificador único | Autoincremento              |
| cultura_gleba_id | INTEGER | Sim         | FK    | Cultura/gleba colhida| FK para `cultura_gleba(id)`|
| data_colheita    | TEXT    | Sim         |       | Data da colheita    | ISO 8601                    |
| quantidade       | REAL    | Não         |       | Quantidade colhida  |                             |
| unidade          | TEXT    | Não         |       | Unidade             | Ex.: sacas, ton             |
| qualidade        | TEXT    | Não         |       | Classificação/qualidade|                          |
| observacao       | TEXT    | Não         |       | Texto livre         |                             |
| criado_em        | TEXT    | Sim         |       | Data/hora de criação| ISO 8601                    |

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
| status_regulatorio | TEXT    | Sim         |       | Status regulatório         | `nao_validado`, `autorizado_sujeito_a_verificacao`, `sujeito_a_sipeagro`, `bloqueado`, `nao_se_aplica` |
| criado_em          | TEXT    | Sim         |       | Data/hora de criação       | ISO 8601                                                                    |
| atualizado_em      | TEXT    | Não         |       | Data/hora de atualização   | ISO 8601                                                                    |

**Regras (MVP):** defensivos começam como `nao_validado` ou
`autorizado_sujeito_a_verificacao`, nunca "validado oficialmente"; fertilizantes
genéricos usam `nao_se_aplica` ou `sujeito_a_sipeagro`; Paraquate, se citado, é
`bloqueado_historico` (não recomendado); Oxamil não entra como recomendado no
seed inicial.

### Tabela: `produto_tecnico`
Informações técnicas do produto.

| Campo                 | Tipo    | Obrigatório | Chave | Descrição                  | Observações                                  |
|-----------------------|---------|-------------|-------|----------------------------|----------------------------------------------|
| id                    | INTEGER | Sim         | PK    | Identificador único        | Autoincremento                               |
| produto_id            | INTEGER | Sim         | FK    | Produto associado          | FK para `produto_base(id)`                   |
| grupo_quimico         | TEXT    | Não         |       | Grupo químico              | Principalmente defensivos                    |
| composicao            | TEXT    | Não         |       | Composição                 | Principalmente fertilizantes                 |
| nutrientes_principais | TEXT    | Não         |       | Nutrientes (ex.: NPK)      | Lista; JSON em `TEXT`; normalizar no futuro  |
| culturas_comuns       | TEXT    | Não         |       | Culturas usuais            | Lista; JSON em `TEXT`; normalizar no futuro  |
| alvos_controle        | TEXT    | Não         |       | Alvos de controle          | Defensivos; JSON em `TEXT`                    |
| modo_aplicacao        | TEXT    | Não         |       | Modo de aplicação          |                                              |
| fonte_tecnica         | TEXT    | Não         |       | Origem da informação técnica| Não inventar; validar depois se ausente      |
| observacoes           | TEXT    | Não         |       | Texto livre                |                                              |

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
> informativo, nunca venda/cotação oficial.

### Tabela: `produto_imagem`
Imagem do produto. **Pendência no MVP.**

| Campo            | Tipo    | Obrigatório | Chave | Descrição            | Observações                       |
|------------------|---------|-------------|-------|----------------------|-----------------------------------|
| id               | INTEGER | Sim         | PK    | Identificador único  | Autoincremento                    |
| produto_id       | INTEGER | Sim         | FK    | Produto da imagem    | FK para `produto_base(id)`        |
| url              | TEXT    | Não         |       | Caminho/URL da imagem| **Pendência**: `NULL` no MVP      |
| fonte            | TEXT    | Não         |       | Origem da imagem     | Não usar imagem sem fonte         |
| status_validacao | TEXT    | Sim         |       | Situação do dado     | MVP: `pendente`/`nao_consolidado` |
| observacoes      | TEXT    | Não         |       | Texto livre          |                                   |
| criado_em        | TEXT    | Sim         |       | Data/hora de criação | ISO 8601                          |

---

## Financeiro, upload e IA

### Tabela: `financeiro_lancamento`
Lançamentos financeiros (receita/despesa).

| Campo          | Tipo    | Obrigatório | Chave | Descrição                | Observações               |
|----------------|---------|-------------|-------|--------------------------|---------------------------|
| id             | INTEGER | Sim         | PK    | Identificador único      | Autoincremento            |
| propriedade_id | INTEGER | Sim         | FK    | Propriedade do lançamento| FK para `propriedade(id)` |
| tipo           | TEXT    | Sim         |       | Tipo do lançamento       | `receita` ou `despesa`    |
| categoria      | TEXT    | Não         |       | Categoria do lançamento  |                           |
| descricao      | TEXT    | Não         |       | Descrição                |                           |
| valor          | REAL    | Sim         |       | Valor do lançamento      |                           |
| data           | TEXT    | Sim         |       | Data do lançamento       | ISO 8601                  |
| criado_em      | TEXT    | Sim         |       | Data/hora de criação     | ISO 8601                  |
| atualizado_em  | TEXT    | Não         |       | Data/hora de atualização | ISO 8601                  |

### Tabela: `upload_arquivo`
Documentos/arquivos enviados.

| Campo          | Tipo    | Obrigatório | Chave | Descrição               | Observações               |
|----------------|---------|-------------|-------|-------------------------|---------------------------|
| id             | INTEGER | Sim         | PK    | Identificador único     | Autoincremento            |
| propriedade_id | INTEGER | Sim         | FK    | Propriedade do arquivo  | FK para `propriedade(id)` |
| nome_original  | TEXT    | Sim         |       | Nome do arquivo enviado |                           |
| caminho        | TEXT    | Sim         |       | Caminho de armazenamento|                           |
| tipo_mime      | TEXT    | Não         |       | Tipo do arquivo         | Ex.: `application/pdf`    |
| tamanho        | INTEGER | Não         |       | Tamanho em bytes        |                           |
| descricao      | TEXT    | Não         |       | Descrição               |                           |
| enviado_em     | TEXT    | Sim         |       | Data/hora do upload     | ISO 8601                  |

### Tabela: `ia_interacao`
Interações com a camada de IA. **No MVP a IA é simulada.**

| Campo          | Tipo    | Obrigatório | Chave | Descrição              | Observações                            |
|----------------|---------|-------------|-------|------------------------|----------------------------------------|
| id             | INTEGER | Sim         | PK    | Identificador único    | Autoincremento                         |
| usuario_id     | INTEGER | Sim         | FK    | Usuário da interação   | FK para `usuario(id)`                  |
| propriedade_id | INTEGER | Não         | FK    | Propriedade de contexto| FK para `propriedade(id)`              |
| pergunta       | TEXT    | Sim         |       | Entrada do usuário     |                                        |
| resposta       | TEXT    | Não         |       | Resposta gerada        | Apoio informativo, não recomendação definitiva |
| tipo           | TEXT    | Sim         |       | Tipo da interação      | `simulada`, `apoio`, `relatorio`, `duvida` |
| criado_em      | TEXT    | Sim         |       | Data/hora de criação   | ISO 8601                               |

---

## Documentos relacionados

- [04 — Modelagem do Banco (DER)](./04-modelagem-banco-der.md)
- [03 — Regras de Negócio](./03-regras-de-negocio.md)
- [Catálogo de Produtos](./catalogo-produtos/README.md)
