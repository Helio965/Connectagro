# 05 — Dicionário de Dados

## Status do documento

**Dicionário de Dados — v0.4 (alinhado aos modelos SQLAlchemy implementados).**

Este documento detalha as tabelas e campos do MVP do ConnectAgro e permanece
alinhado aos modelos em `src/app/models/`. A Fase 6.3 não altera schema: as
permissões finas usam o campo já existente `usuario.perfil` e uma matriz em
código (`src/app/utils/permissions.py`).

## Convenções

- Tabelas e colunas em `snake_case`.
- Toda tabela principal possui `id` INTEGER, PK, autoincremento.
- Datas/horas em ISO 8601, armazenadas como `TEXT`.
- Booleanos documentados como `BOOLEAN`, armazenados como `0`/`1` no SQLite.
- Campos de lista podem ser `TEXT` com JSON no MVP.

> Limites do MVP: o sistema não vende produtos; `produto_preco` e
> `produto_imagem` seguem pendentes/vazios; não há validação oficial AGROFIT/MAPA
> presumida; permissões finas não criam tabela nova nem migration.

---

## Gestão e acesso

### Tabela: `usuario`
Usuários do sistema.

| Campo | Tipo | Obrigatório | Chave | Descrição | Observações |
|---|---|---:|---|---|---|
| id | INTEGER | Sim | PK | Identificador único | Autoincremento |
| nome | TEXT | Sim | | Nome do usuário | |
| email | TEXT | Sim | | E-mail de login | Único |
| senha_hash | TEXT | Sim | | Hash da senha | Nunca armazenar senha em texto puro |
| perfil | TEXT | Sim | | Perfil de acesso | `admin`, `tecnico`, `trabalhador` |
| ativo | BOOLEAN | Sim | | Usuário ativo | `0`/`1`; padrão `1` |
| criado_em | TEXT | Sim | | Data/hora de criação | ISO 8601 |
| atualizado_em | TEXT | Não | | Data/hora da última atualização | ISO 8601 |

Observação: permissões por perfil são resolvidas em código, não por tabela de
permissões. A sessão guarda o perfil atual em `user_perfil`.

### Tabela: `propriedade`
Propriedade rural gerida pelo usuário.

| Campo | Tipo | Obrigatório | Chave | Descrição | Observações |
|---|---|---:|---|---|---|
| id | INTEGER | Sim | PK | Identificador único | Autoincremento |
| usuario_id | INTEGER | Sim | FK | Usuário dono | FK para `usuario(id)` |
| nome | TEXT | Sim | | Nome da propriedade | |
| municipio | TEXT | Não | | Município | |
| uf | TEXT | Não | | Unidade federativa | Sigla, ex.: `MT` |
| area_total_ha | REAL | Não | | Área total em hectares | |
| criado_em | TEXT | Sim | | Data/hora de criação | ISO 8601 |
| atualizado_em | TEXT | Não | | Data/hora de atualização | ISO 8601 |

### Tabela: `equipe_membro`
Membros da equipe vinculados a uma propriedade.

| Campo | Tipo | Obrigatório | Chave | Descrição | Observações |
|---|---|---:|---|---|---|
| id | INTEGER | Sim | PK | Identificador único | Autoincremento |
| propriedade_id | INTEGER | Sim | FK | Propriedade do membro | FK para `propriedade(id)` |
| nome | TEXT | Sim | | Nome do membro | |
| funcao | TEXT | Não | | Função/papel | Pode refinar permissões futuramente |
| email | TEXT | Não | | E-mail de contato | |
| telefone | TEXT | Não | | Telefone de contato | |
| ativo | BOOLEAN | Sim | | Membro ativo | `0`/`1`; padrão `1` |
| criado_em | TEXT | Sim | | Data/hora de criação | ISO 8601 |
| atualizado_em | TEXT | Não | | Data/hora de atualização | ISO 8601 |

---

## Operação agrícola

### Tabela: `cultura`
Culturas cadastradas na propriedade.

| Campo | Tipo | Obrigatório | Chave | Descrição | Observações |
|---|---|---:|---|---|---|
| id | INTEGER | Sim | PK | Identificador único | Autoincremento |
| propriedade_id | INTEGER | Sim | FK | Propriedade da cultura | FK para `propriedade(id)` |
| nome | TEXT | Sim | | Nome da cultura | Ex.: soja, milho |
| variedade | TEXT | Não | | Variedade/cultivar | |
| safra | TEXT | Não | | Identificação da safra | Ex.: `2025/2026` |
| data_inicio | TEXT | Não | | Início da cultura | ISO 8601 |
| data_fim | TEXT | Não | | Fim da cultura | ISO 8601 |
| status | TEXT | Sim | | Situação da cultura | `planejada`, `em_andamento`, `colhida`, `cancelada` |
| criado_em | TEXT | Sim | | Data/hora de criação | ISO 8601 |
| atualizado_em | TEXT | Não | | Data/hora de atualização | ISO 8601 |

### Tabela: `gleba`
Áreas/talhões da propriedade.

| Campo | Tipo | Obrigatório | Chave | Descrição | Observações |
|---|---|---:|---|---|---|
| id | INTEGER | Sim | PK | Identificador único | Autoincremento |
| propriedade_id | INTEGER | Sim | FK | Propriedade da gleba | FK para `propriedade(id)` |
| nome | TEXT | Sim | | Identificação da gleba | |
| area_ha | REAL | Não | | Área em hectares | |
| latitude | REAL | Não | | Latitude do ponto central | |
| longitude | REAL | Não | | Longitude do ponto central | |
| poligono_geojson | TEXT | Não | | Polígono da área | GeoJSON em `TEXT` |
| tipo_solo | TEXT | Não | | Tipo de solo | |
| observacoes | TEXT | Não | | Texto livre | |
| criado_em | TEXT | Sim | | Data/hora de criação | ISO 8601 |
| atualizado_em | TEXT | Não | | Data/hora de atualização | ISO 8601 |

### Tabela: `cultura_gleba`
Associação N:N entre culturas e glebas.

| Campo | Tipo | Obrigatório | Chave | Descrição | Observações |
|---|---|---:|---|---|---|
| id | INTEGER | Sim | PK | Identificador único | Autoincremento |
| cultura_id | INTEGER | Sim | FK | Cultura associada | FK para `cultura(id)` |
| gleba_id | INTEGER | Sim | FK | Gleba associada | FK para `gleba(id)` |
| data_inicio | TEXT | Não | | Início do uso | ISO 8601 |
| data_fim | TEXT | Não | | Fim do uso | ISO 8601; `NULL` se ativo |
| observacoes | TEXT | Não | | Texto livre | |

### Tabela: `aplicacao_insumo`
Aplicação de um insumo do catálogo em uma cultura/gleba.

| Campo | Tipo | Obrigatório | Chave | Descrição | Observações |
|---|---|---:|---|---|---|
| id | INTEGER | Sim | PK | Identificador único | Autoincremento |
| cultura_gleba_id | INTEGER | Sim | FK | Onde foi aplicado | FK para `cultura_gleba(id)` |
| produto_base_id | INTEGER | Sim | FK | Produto aplicado | FK para `produto_base(id)` |
| data_aplicacao | TEXT | Sim | | Data da aplicação | ISO 8601 |
| dose | REAL | Não | | Quantidade aplicada | Histórica/informativa |
| unidade | TEXT | Não | | Unidade da dose | Ex.: kg/ha, L/ha |
| responsavel | TEXT | Não | | Responsável pela aplicação | |
| observacao | TEXT | Não | | Texto livre | Não substitui orientação agronômica |
| criado_em | TEXT | Sim | | Data/hora de criação | ISO 8601 |

### Tabela: `colheita_registro`
Registros de colheita por cultura/gleba.

| Campo | Tipo | Obrigatório | Chave | Descrição | Observações |
|---|---|---:|---|---|---|
| id | INTEGER | Sim | PK | Identificador único | Autoincremento |
| cultura_gleba_id | INTEGER | Sim | FK | Cultura/gleba colhida | FK para `cultura_gleba(id)` |
| data_colheita | TEXT | Sim | | Data da colheita | ISO 8601 |
| quantidade | REAL | Não | | Quantidade colhida | |
| unidade | TEXT | Não | | Unidade | Ex.: sacas, ton |
| qualidade | TEXT | Não | | Classificação/qualidade | |
| observacao | TEXT | Não | | Texto livre | |
| criado_em | TEXT | Sim | | Data/hora de criação | ISO 8601 |

---

## Catálogo de produtos

### Tabela: `produto_base`
Tabela central do catálogo.

| Campo | Tipo | Obrigatório | Chave | Descrição | Observações |
|---|---|---:|---|---|---|
| id | INTEGER | Sim | PK | Identificador único | Autoincremento |
| nome | TEXT | Sim | | Nome principal do item | |
| slug | TEXT | Sim | | Versão amigável | Único |
| classe | TEXT | Sim | | Grupo amplo | Ex.: `defensivo`, `fertilizante` |
| categoria | TEXT | Sim | | Categoria específica | Ex.: herbicida, mineral |
| descricao_curta | TEXT | Não | | Resumo | |
| descricao_completa | TEXT | Não | | Descrição detalhada | |
| status_sistema | TEXT | Sim | | Status interno | `pre_cadastrado`, `cadastrado_usuario`, `definitivo`, `bloqueado_historico` |
| status_regulatorio | TEXT | Sim | | Status regulatório | Enum MVP documentado nas regras de negócio |
| criado_em | TEXT | Sim | | Data/hora de criação | ISO 8601 |
| atualizado_em | TEXT | Não | | Data/hora de atualização | ISO 8601 |

### Tabela: `produto_tecnico`
Informações técnicas do produto.

| Campo | Tipo | Obrigatório | Chave | Descrição | Observações |
|---|---|---:|---|---|---|
| id | INTEGER | Sim | PK | Identificador único | Autoincremento |
| produto_id | INTEGER | Sim | FK | Produto associado | FK para `produto_base(id)` |
| grupo_quimico | TEXT | Não | | Grupo químico | Principalmente defensivos |
| composicao | TEXT | Não | | Composição | Principalmente fertilizantes |
| nutrientes_principais | TEXT | Não | | Nutrientes | JSON em `TEXT` no MVP |
| culturas_comuns | TEXT | Não | | Culturas usuais | JSON em `TEXT` no MVP |
| alvos_controle | TEXT | Não | | Alvos de controle | Defensivos; JSON em `TEXT` |
| uso_principal | TEXT | Não | | Uso principal | |
| modo_aplicacao | TEXT | Não | | Modo de aplicação | |
| tipo_liberacao | TEXT | Não | | Tipo de liberação | Fertilizantes |
| fonte_tecnica | TEXT | Não | | Origem da informação | Não inventar |
| observacoes | TEXT | Não | | Texto livre | |

### Tabelas: `produto_preco` e `produto_imagem`
Existem no schema, mas ficam vazias/pendentes no MVP. Não são populadas pelo seed
nem pelos CRUDs operacionais.

---

## Financeiro, upload e IA

### Tabela: `financeiro_lancamento`
Lançamentos financeiros.

| Campo | Tipo | Obrigatório | Chave | Descrição | Observações |
|---|---|---:|---|---|---|
| id | INTEGER | Sim | PK | Identificador único | Autoincremento |
| propriedade_id | INTEGER | Sim | FK | Propriedade do lançamento | FK para `propriedade(id)` |
| tipo | TEXT | Sim | | Tipo | `receita` ou `despesa` |
| categoria | TEXT | Não | | Categoria | |
| descricao | TEXT | Não | | Descrição | |
| valor | REAL | Sim | | Valor | Maior que zero nas rotas |
| data | TEXT | Sim | | Data | ISO 8601 |
| criado_em | TEXT | Sim | | Data/hora de criação | ISO 8601 |
| atualizado_em | TEXT | Não | | Data/hora de atualização | ISO 8601 |

### Tabela: `upload_arquivo`
Documentos/arquivos enviados.

| Campo | Tipo | Obrigatório | Chave | Descrição | Observações |
|---|---|---:|---|---|---|
| id | INTEGER | Sim | PK | Identificador único | Autoincremento |
| propriedade_id | INTEGER | Sim | FK | Propriedade do arquivo | FK para `propriedade(id)` |
| nome_original | TEXT | Sim | | Nome do arquivo enviado | |
| caminho | TEXT | Sim | | Caminho relativo | Fora de `static` |
| tipo_mime | TEXT | Não | | Tipo do arquivo | Ex.: `application/pdf` |
| tamanho | INTEGER | Não | | Tamanho em bytes | |
| descricao | TEXT | Não | | Descrição | |
| enviado_em | TEXT | Sim | | Data/hora do upload | ISO 8601 |

### Tabela: `ia_interacao`
Interações com a IA simulada.

| Campo | Tipo | Obrigatório | Chave | Descrição | Observações |
|---|---|---:|---|---|---|
| id | INTEGER | Sim | PK | Identificador único | Autoincremento |
| usuario_id | INTEGER | Sim | FK | Usuário da interação | FK para `usuario(id)` |
| propriedade_id | INTEGER | Não | FK | Propriedade de contexto | FK para `propriedade(id)` |
| pergunta | TEXT | Sim | | Entrada do usuário | |
| resposta | TEXT | Não | | Resposta gerada | Apoio informativo |
| tipo | TEXT | Sim | | Tipo da interação | `simulada`, `apoio`, `relatorio`, `duvida` |
| criado_em | TEXT | Sim | | Data/hora de criação | ISO 8601 |

---

## Documentos relacionados

- [04 — Modelagem do Banco (DER)](./04-modelagem-banco-der.md)
- [03 — Regras de Negócio](./03-regras-de-negocio.md)
- [Catálogo de Produtos](./catalogo-produtos/README.md)
