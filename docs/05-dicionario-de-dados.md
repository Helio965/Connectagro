# 05 — Dicionário de Dados

## Status do documento

**Dicionário de dados preliminar — v0.1 (MVP).**

Detalha as tabelas e campos derivados do [DER preliminar](./04-modelagem-banco-der.md).
Acompanha a v0.1 e está sujeito a refinamento. Nenhum banco, migration ou seed é
criado nesta etapa.

## Objetivo

Documentar, de forma padronizada, cada tabela do MVP e seus campos: nome, tipo,
obrigatoriedade, descrição e observações — garantindo clareza para a futura
implementação em **SQLite**.

## Convenções

- Tabelas e colunas em `snake_case`.
- Toda tabela principal possui `id` INTEGER, PK, autoincremento.
- Datas/horas em **ISO 8601**.
- "Obrigatório = Não" indica campo que pode ser `NULL`.
- Tipos referem-se às classes de afinidade do SQLite (`INTEGER`, `TEXT`, `REAL`,
  `NUMERIC`/`BOOLEAN`). `BOOLEAN` é armazenado como `0`/`1`.
- **Preço e imagem de produtos são pendências no MVP**: ficam `NULL` e
  `consolidado = 0` enquanto não houver fonte confiável. Nunca preencher com
  valores inventados.
- A **validação diária do menor preço** fica para o **sistema final**.
- **Validação regulatória AGROFIT/MAPA não é presumida**; o catálogo é base
  técnica inicial, não verdade regulatória definitiva.

---

## Gestão e acesso

### Tabela: `usuario`
Usuários do sistema (autenticação).

| Campo         | Tipo     | Obrigatório | Descrição                          | Observações                  |
| ------------- | -------- | ----------- | ---------------------------------- | ---------------------------- |
| id            | INTEGER  | Sim         | Identificador único (PK)           | Autoincremento               |
| nome          | TEXT     | Sim         | Nome do usuário                    |                              |
| email         | TEXT     | Sim         | E-mail de login                    | Único                        |
| senha_hash    | TEXT     | Sim         | Hash da senha                      | Nunca armazenar em texto puro|
| ativo         | BOOLEAN  | Sim         | Usuário ativo                      | Padrão `1`                   |
| criado_em     | TEXT     | Sim         | Data/hora de criação               | ISO 8601                     |
| atualizado_em | TEXT     | Não         | Data/hora da última atualização    | ISO 8601                     |

### Tabela: `propriedade`
Propriedade rural gerida pelo usuário.

| Campo         | Tipo     | Obrigatório | Descrição                          | Observações                  |
| ------------- | -------- | ----------- | ---------------------------------- | ---------------------------- |
| id            | INTEGER  | Sim         | Identificador único (PK)           | Autoincremento               |
| usuario_id    | INTEGER  | Sim         | Dono/responsável                   | FK → `usuario(id)`           |
| nome          | TEXT     | Sim         | Nome da propriedade                |                              |
| municipio     | TEXT     | Não         | Município                          |                              |
| uf            | TEXT     | Não         | Unidade federativa                 | Sigla (ex.: `MT`)            |
| area_total_ha | REAL     | Não         | Área total em hectares             |                              |
| criado_em     | TEXT     | Sim         | Data/hora de criação               | ISO 8601                     |

### Tabela: `equipe_membro`
Membros da equipe vinculados a uma propriedade.

| Campo          | Tipo     | Obrigatório | Descrição                         | Observações                 |
| -------------- | -------- | ----------- | --------------------------------- | --------------------------- |
| id             | INTEGER  | Sim         | Identificador único (PK)          | Autoincremento              |
| propriedade_id | INTEGER  | Sim         | Propriedade do membro             | FK → `propriedade(id)`      |
| nome           | TEXT     | Sim         | Nome do membro                    |                             |
| funcao         | TEXT     | Não         | Função/papel                      | Pode condicionar permissões |
| email          | TEXT     | Não         | E-mail de contato                 |                             |
| telefone       | TEXT     | Não         | Telefone de contato               |                             |
| ativo          | BOOLEAN  | Sim         | Membro ativo                      | Padrão `1`                  |
| criado_em      | TEXT     | Sim         | Data/hora de criação              | ISO 8601                    |

---

## Operação agrícola

### Tabela: `cultura`
Culturas cadastradas na propriedade.

| Campo          | Tipo     | Obrigatório | Descrição                         | Observações                 |
| -------------- | -------- | ----------- | --------------------------------- | --------------------------- |
| id             | INTEGER  | Sim         | Identificador único (PK)          | Autoincremento              |
| propriedade_id | INTEGER  | Sim         | Propriedade da cultura            | FK → `propriedade(id)`      |
| nome           | TEXT     | Sim         | Nome da cultura                   | Ex.: soja, milho            |
| variedade      | TEXT     | Não         | Variedade/cultivar                |                             |
| safra          | TEXT     | Não         | Identificação da safra            | Ex.: `2025/2026`            |
| criado_em      | TEXT     | Sim         | Data/hora de criação              | ISO 8601                    |

### Tabela: `gleba`
Áreas/talhões da propriedade.

| Campo          | Tipo     | Obrigatório | Descrição                         | Observações                  |
| -------------- | -------- | ----------- | --------------------------------- | ---------------------------- |
| id             | INTEGER  | Sim         | Identificador único (PK)          | Autoincremento               |
| propriedade_id | INTEGER  | Sim         | Propriedade da gleba              | FK → `propriedade(id)`       |
| nome           | TEXT     | Sim         | Identificação da gleba/talhão     |                              |
| area_ha        | REAL     | Não         | Área em hectares                  |                              |
| geometria      | TEXT     | Não         | Dados geográficos (mapa)          | Formato a definir (ex.: GeoJSON)|
| criado_em      | TEXT     | Sim         | Data/hora de criação              | ISO 8601                     |

### Tabela: `cultura_gleba`
Associação N:N entre culturas e glebas.

| Campo       | Tipo     | Obrigatório | Descrição                          | Observações                 |
| ----------- | -------- | ----------- | ---------------------------------- | --------------------------- |
| id          | INTEGER  | Sim         | Identificador único (PK)           | Autoincremento              |
| cultura_id  | INTEGER  | Sim         | Cultura associada                  | FK → `cultura(id)`          |
| gleba_id    | INTEGER  | Sim         | Gleba associada                    | FK → `gleba(id)`            |
| data_inicio | TEXT     | Não         | Início do plantio/uso              | ISO 8601                    |
| data_fim    | TEXT     | Não         | Fim do ciclo                       | ISO 8601; `NULL` se ativo   |

### Tabela: `aplicacao_insumo`
Aplicação de um insumo do catálogo em uma cultura/gleba.

| Campo            | Tipo     | Obrigatório | Descrição                       | Observações                  |
| ---------------- | -------- | ----------- | ------------------------------- | ---------------------------- |
| id               | INTEGER  | Sim         | Identificador único (PK)        | Autoincremento               |
| cultura_gleba_id | INTEGER  | Sim         | Onde foi aplicado               | FK → `cultura_gleba(id)`     |
| produto_base_id  | INTEGER  | Sim         | Produto aplicado                | FK → `produto_base(id)`      |
| data_aplicacao   | TEXT     | Sim         | Data da aplicação               | ISO 8601                     |
| dose             | REAL     | Não         | Quantidade aplicada             |                              |
| unidade          | TEXT     | Não         | Unidade da dose                 | Ex.: kg/ha, L/ha             |
| observacao       | TEXT     | Não         | Texto livre                     |                              |
| criado_em        | TEXT     | Sim         | Data/hora de criação            | ISO 8601                     |

### Tabela: `colheita_registro`
Registros de colheita por cultura/gleba.

| Campo            | Tipo     | Obrigatório | Descrição                       | Observações                  |
| ---------------- | -------- | ----------- | ------------------------------- | ---------------------------- |
| id               | INTEGER  | Sim         | Identificador único (PK)        | Autoincremento               |
| cultura_gleba_id | INTEGER  | Sim         | Cultura/gleba colhida           | FK → `cultura_gleba(id)`     |
| data_colheita    | TEXT     | Sim         | Data da colheita                | ISO 8601                     |
| quantidade       | REAL     | Não         | Quantidade colhida              |                              |
| unidade          | TEXT     | Não         | Unidade                         | Ex.: sacas, ton              |
| observacao       | TEXT     | Não         | Texto livre                     |                              |
| criado_em        | TEXT     | Sim         | Data/hora de criação            | ISO 8601                     |

---

## Catálogo de produtos

> Base técnica inicial de consulta rápida. **Preço e imagem são pendências no
> MVP.** Sem validação AGROFIT/MAPA presumida.

### Tabela: `produto_base`
Linha central do produto no catálogo.

| Campo              | Tipo     | Obrigatório | Descrição                       | Observações                                  |
| ------------------ | -------- | ----------- | ------------------------------- | -------------------------------------------- |
| id                 | INTEGER  | Sim         | Identificador único (PK)        | Autoincremento                               |
| categoria          | TEXT     | Sim         | Categoria do produto            | `defensivo`, `fertilizante`, `corretivo`, `inoculante`, `biofertilizante` (expansível) |
| nome               | TEXT     | Sim         | Nome do produto/insumo          |                                              |
| produto_tecnico_id | INTEGER  | Não         | Tipo técnico associado          | FK → `produto_tecnico(id)`                   |
| fabricante         | TEXT     | Não         | Fabricante                      | `NULL` para itens genéricos no MVP           |
| tipo_registro      | TEXT     | Sim         | Natureza do registro            | `tecnico_generico` (padrão MVP) ou `comercial` (futuro) |
| descricao          | TEXT     | Não         | Descrição técnica               |                                              |
| criado_em          | TEXT     | Sim         | Data/hora de criação            | ISO 8601                                     |

### Tabela: `produto_tecnico`
Tipos técnicos/genéricos (ex.: Ureia, MAP, DAP, Calcário Dolomítico).

| Campo        | Tipo     | Obrigatório | Descrição                       | Observações                  |
| ------------ | -------- | ----------- | ------------------------------- | ---------------------------- |
| id           | INTEGER  | Sim         | Identificador único (PK)        | Autoincremento               |
| categoria    | TEXT     | Sim         | Categoria                       | Mesma classificação de `produto_base` |
| nome_tecnico | TEXT     | Sim         | Nome do tipo técnico/genérico   | Ex.: Ureia, MAP, DAP         |
| composicao   | TEXT     | Não         | Composição/descrição técnica    | Ex.: teores NPK              |
| descricao    | TEXT     | Não         | Observações                     |                              |

### Tabela: `produto_preco`
Preço de **referência** (consulta rápida). **Pendência no MVP.**

| Campo           | Tipo     | Obrigatório | Descrição                       | Observações                          |
| --------------- | -------- | ----------- | ------------------------------- | ------------------------------------ |
| id              | INTEGER  | Sim         | Identificador único (PK)        | Autoincremento                       |
| produto_base_id | INTEGER  | Sim         | Produto do preço                | FK → `produto_base(id)`              |
| valor           | REAL     | Não         | Valor de referência             | **Pendência**: `NULL` se não consolidado |
| moeda           | TEXT     | Não         | Moeda                           | Ex.: `BRL`                           |
| fonte           | TEXT     | Não         | Origem do dado                  | Necessária para considerar consolidado |
| data_referencia | TEXT     | Não         | Data de referência do valor     | ISO 8601                             |
| consolidado     | BOOLEAN  | Sim         | Dado consolidado?               | Padrão `0` (pendência) no MVP        |

> A validação diária do menor valor entre fontes fica para o **sistema final**.

### Tabela: `produto_imagem`
Imagem do produto. **Pendência no MVP.**

| Campo           | Tipo     | Obrigatório | Descrição                       | Observações                          |
| --------------- | -------- | ----------- | ------------------------------- | ------------------------------------ |
| id              | INTEGER  | Sim         | Identificador único (PK)        | Autoincremento                       |
| produto_base_id | INTEGER  | Sim         | Produto da imagem               | FK → `produto_base(id)`              |
| caminho         | TEXT     | Não         | Caminho/URL da imagem           | **Pendência**: `NULL` se indisponível |
| fonte           | TEXT     | Não         | Origem da imagem                |                                      |
| consolidado     | BOOLEAN  | Sim         | Dado consolidado?               | Padrão `0` (pendência) no MVP        |

---

## Financeiro, arquivos e apoio

### Tabela: `financeiro_lancamento`
Lançamentos financeiros (receita/despesa).

| Campo          | Tipo     | Obrigatório | Descrição                       | Observações                  |
| -------------- | -------- | ----------- | ------------------------------- | ---------------------------- |
| id             | INTEGER  | Sim         | Identificador único (PK)        | Autoincremento               |
| propriedade_id | INTEGER  | Sim         | Propriedade do lançamento       | FK → `propriedade(id)`       |
| tipo           | TEXT     | Sim         | Tipo do lançamento              | `receita` ou `despesa`       |
| categoria      | TEXT     | Não         | Categoria do lançamento         |                              |
| descricao      | TEXT     | Não         | Descrição                       |                              |
| valor          | REAL     | Sim         | Valor do lançamento             |                              |
| data           | TEXT     | Sim         | Data do lançamento              | ISO 8601                     |
| criado_em      | TEXT     | Sim         | Data/hora de criação            | ISO 8601                     |

### Tabela: `upload_arquivo`
Documentos/arquivos enviados.

| Campo          | Tipo     | Obrigatório | Descrição                       | Observações                  |
| -------------- | -------- | ----------- | ------------------------------- | ---------------------------- |
| id             | INTEGER  | Sim         | Identificador único (PK)        | Autoincremento               |
| propriedade_id | INTEGER  | Sim         | Propriedade do arquivo          | FK → `propriedade(id)`       |
| nome_original  | TEXT     | Sim         | Nome do arquivo enviado         |                              |
| caminho        | TEXT     | Sim         | Caminho de armazenamento        |                              |
| tipo_mime      | TEXT     | Não         | Tipo do arquivo                 | Ex.: `application/pdf`       |
| tamanho        | INTEGER  | Não         | Tamanho em bytes                |                              |
| enviado_em     | TEXT     | Sim         | Data/hora do upload             | ISO 8601                     |

---

## Documentos relacionados

- [04 — Modelagem do Banco (DER)](./04-modelagem-banco-der.md)
- [03 — Regras de Negócio](./03-regras-de-negocio.md)
- [Catálogo de Produtos](./catalogo-produtos/README.md)
