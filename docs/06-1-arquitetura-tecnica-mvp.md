# 06.1 — Arquitetura Técnica do MVP

## Status do documento

**Arquitetura técnica — v0.11 (CRUDs + catálogo + aplicação de insumo).**

Este documento **complementa** o [06 — Arquitetura do Sistema](./06-arquitetura-do-sistema.md):

- O documento **06** é a **visão conceitual/geral** (camadas em alto nível).
- O documento **06.1** (este) é o **guia técnico detalhado** da implementação do
  MVP em Flask.

> **Estado atual:** estão prontos a **fundação Flask** (`src/run.py` + `src/app/`
> com Application Factory, layout base, `/health`), os **modelos SQLAlchemy** (15
> tabelas), as **migrations** (Flask-Migrate, pasta `migrations/` versionada), a
> **importação do catálogo técnico** via CLI (`validate-catalog-seed` /
> `import-catalog-seed`) e a **autenticação real** (login/logout com sessão Flask
> + `werkzeug.security`; rotas dos módulos protegidas por `@login_required`;
> usuários de teste via `seed-users`).
>
> **CRUDs entregues:** Glebas, Culturas (+ associação cultura↔gleba), Equipe,
> Financeiro (com totais), Colheita e **Aplicações de Insumo**. A consulta
> somente leitura do catálogo (**Defensivos**/**Fertilizantes**) usa `ProdutoBase`
> + `ProdutoTecnico` (busca, filtros e detalhe); `ProdutoPreco`/`ProdutoImagem`
> seguem **vazios** no MVP.
>
> **Aplicações de Insumo:** o módulo liga `CulturaGleba` a `ProdutoBase`, registra
> histórico operacional e bloqueia produtos com status histórico/bloqueado. Ele
> **não** é recomendação agronômica, **não** valida dose tecnicamente e **não**
> cria preço, imagem, venda, carrinho ou cotação.
>
> **Próximo passo oficial:** implementar o **Upload**. Dashboard, Mapa real, IA
> simulada e Relatórios seguem pendentes.

## Objetivo

Definir **como** o MVP é construído tecnicamente, oferecendo um guia claro e
consistente para a implementação incremental.

---

## 1. Visão técnica geral

O MVP é uma **aplicação web monolítica** em **Flask**, renderizada no servidor
(Server-Side Rendering com Jinja2), com banco **SQLite** e frontend em
**HTML/CSS/JavaScript**. A organização segue separação por camadas e por módulos
(blueprints), favorecendo manutenção, testes e evolução futura.

```text
Navegador (HTML/CSS/JS)
        │  HTTP
        ▼
Flask (rotas/blueprints)  ──►  Serviços/helpers  ──►  Modelos/Acesso a dados
        │                                                       │
        ▼                                                       ▼
   Templates Jinja2                                         SQLite (instance/)
```

### Princípios técnicos

- **Application Factory** (`create_app`) para criar a aplicação de forma
  configurável e testável.
- **Blueprints** para isolar cada módulo do MVP.
- **Separação de responsabilidades:** rotas simples, helpers locais para CRUDs e
  serviços quando houver regra compartilhada.
- **Configuração por ambiente** via variáveis de ambiente (`.env`), sem segredos
  versionados.
- Alinhamento total com os nomes de tabelas/campos do
  [dicionário de dados](./05-dicionario-de-dados.md).

---

## 2. Stack planejada

| Camada           | Tecnologia planejada                         | Observações                                    |
|------------------|----------------------------------------------|------------------------------------------------|
| Linguagem        | Python 3.11+                                 | Versão a confirmar no ambiente local           |
| Framework web    | Flask                                        | Monólito com blueprints                        |
| Templates        | Jinja2 (incluído no Flask)                   | SSR                                            |
| Banco de dados   | SQLite                                       | Arquivo local em `instance/`                   |
| Acesso a dados   | Flask-SQLAlchemy                             | ORM adotado                                    |
| Migrations       | Flask-Migrate (Alembic)                      | Pasta `migrations/` versionada                 |
| Autenticação     | Sessão Flask + hash de senha (Werkzeug)      | Helpers em `utils/auth.py`                     |
| Formulários/CSRF | Sem Flask-WTF nesta etapa                    | CSRF dedicado permanece pendente               |
| Frontend         | HTML, CSS, JavaScript                        | Sem framework JS obrigatório no MVP            |
| Testes           | pytest                                       | SQLite em memória                              |

> **Flask**, **Flask-SQLAlchemy**, **Flask-Migrate**, **python-dotenv** e
> **pytest** estão declarados no [`requirements.txt`](../requirements.txt).

---

## 3. Estrutura Flask

```text
src/
├── run.py
└── app/
    ├── __init__.py              # create_app / Application Factory
    ├── config.py                # configuração por ambiente
    ├── extensions.py            # db, migrate
    ├── commands.py              # init-db, validate/import-catalog-seed, seed-users
    ├── blueprints/
    │   ├── __init__.py          # registro central dos blueprints
    │   ├── auth/  dashboard/  culturas/  glebas/
    │   ├── defensivos/  fertilizantes/  aplicacoes/
    │   ├── financeiro/  upload/  equipe/  colheita/
    │   └── mapa/  ia/  relatorios/
    ├── models/                  # modelos SQLAlchemy de domínio (15 tabelas)
    ├── services/                # regras compartilhadas quando necessário
    ├── utils/                   # auth.py, contexto.py, catalogo.py
    ├── templates/               # base.html, módulos, erros
    └── static/                  # css/, js/, uploads/
```

> O banco SQLite fica em `instance/` e arquivos `.db` não são versionados.

---

## 4. Application Factory + Blueprints

- `create_app(config_name)` em `app/__init__.py` instancia o Flask, carrega a
  configuração, inicializa `db`/`migrate`, registra modelos, blueprints,
  comandos CLI, context processors e handlers de erro.
- `src/app/blueprints/__init__.py` centraliza `ALL_BLUEPRINTS`.
- Cada módulo do MVP tem `__init__.py` com `Blueprint` e `routes.py` com as rotas.

---

## 5. Mapeamento de módulos → blueprints

| Módulo (MVP)       | Blueprint        | Prefixo        | Entidades principais                              |
|--------------------|------------------|----------------|---------------------------------------------------|
| Login              | `auth`           | `/auth`        | `usuario`                                         |
| Dashboard          | `dashboard`      | `/`            | agregações                                        |
| Culturas           | `culturas`       | `/culturas`    | `cultura`, `cultura_gleba`                        |
| Glebas             | `glebas`         | `/glebas`      | `gleba`, `cultura_gleba`                          |
| Defensivos         | `defensivos`     | `/defensivos`  | `produto_base`, `produto_tecnico`                 |
| Fertilizantes      | `fertilizantes`  | `/fertilizantes` | `produto_base`, `produto_tecnico`               |
| Aplicações         | `aplicacoes`     | `/aplicacoes`  | `aplicacao_insumo`, `cultura_gleba`, `produto_base` |
| Financeiro         | `financeiro`     | `/financeiro`  | `financeiro_lancamento`                           |
| Upload             | `upload`         | `/upload`      | `upload_arquivo`                                  |
| Equipe             | `equipe`         | `/equipe`      | `equipe_membro`                                   |
| Colheita           | `colheita`       | `/colheita`    | `colheita_registro`, `cultura_gleba`              |
| Mapa real          | `mapa`           | `/mapa`        | `gleba`                                           |
| IA simulada        | `ia`             | `/ia`          | `ia_interacao`                                    |
| Relatórios         | `relatorios`     | `/relatorios`  | leitura de múltiplas entidades                    |

---

## 6. Acesso a dados e banco SQLite

- **Banco:** arquivo SQLite em `instance/` ou caminho configurado por ambiente.
- **ORM:** `Flask-SQLAlchemy`, com instância `db` em `src/app/extensions.py`.
- **Migrations:** `Flask-Migrate/Alembic`, com migration inicial das 15 tabelas.
- **Seeds:** `flask --app src/run.py import-catalog-seed` popula apenas
  `produto_base` + `produto_tecnico`. `produto_preco`/`produto_imagem` continuam
  vazios no MVP.
- **Aplicações de Insumo:** não exigem migration nova porque a tabela
  `aplicacao_insumo` já existe no schema inicial.

---

## 7. Fluxo principal do MVP

1. Usuário acessa o sistema.
2. Faz **login**.
3. Entra no **dashboard**.
4. Cadastra ou consulta **propriedade / glebas / culturas**.
5. Consulta o **catálogo** de defensivos/fertilizantes.
6. Registra **aplicações de insumos** em associações cultura↔gleba.
7. Registra **despesas/receitas** no financeiro.
8. Registra **colheita**.
9. Futuramente consulta mapa, relatórios e IA simulada.

> **IA simulada:** quando implementada, não deve emitir recomendação agronômica
> definitiva. Funcionará apenas como apoio textual/informativo e organizacional.

---

## 8. Fluxo do catálogo de produtos

- O catálogo **não vende** produtos — serve para consulta rápida, organização da
  propriedade e registro histórico de aplicações.
- Produtos ficam em **`produto_base`**; dados técnicos em **`produto_tecnico`**;
  preços em **`produto_preco`**; imagens em **`produto_imagem`**.
- No MVP, **preço e imagem são pendentes / não consolidados**.
- O MVP **não** busca preços automaticamente e **não** afirma validação oficial
  AGROFIT/MAPA ou SIPEAGRO/MAPA sem fonte real.
- `status_regulatorio` é informativo.
- Itens **bloqueados/históricos**, como Paraquate, não devem ser recomendados e
  **não** podem ser registrados como aplicação válida.

---

## 9. Detalhamento dos módulos do MVP

### Login ✅
- Autenticação real com sessão Flask e hash de senha.
- Rotas protegidas por `@login_required`.

### Dashboard
- Visão consolidada da propriedade após login.
- Permanece pendente nesta etapa.

### Culturas ✅
- CRUD com `status` (`planejada`, `em_andamento`, `colhida`, `cancelada`).
- Associação a glebas sincronizada no formulário.

### Glebas ✅
- CRUD de áreas/talhões.
- Futuro: `poligono_geojson` para mapa real.

### Defensivos ✅
- Consulta somente leitura de `ProdutoBase` com classe `defensivo`.
- Busca, filtros e detalhe técnico.
- Sem CRUD de produto.

### Fertilizantes ✅
- Consulta somente leitura de `ProdutoBase` com classe `fertilizante`.
- Busca, filtros e detalhe técnico.
- Sem CRUD de produto.

### Aplicações de Insumo ✅
- **Objetivo:** registrar histórico operacional de uso de insumos do catálogo.
- **Dados principais:** `aplicacao_insumo`, `cultura_gleba`, `produto_base`.
- **Blueprint:** `aplicacoes` (`/aplicacoes`).
- **Implementado:** CRUD de `AplicacaoInsumo` com listagem, criação, edição e
  remoção, protegido por login e escopado à propriedade atual.
- **Vínculo:** cada registro liga uma associação **Cultura↔Gleba** (`cultura_gleba_id`)
  a um produto do catálogo (`produto_base_id`).
- **Bloqueio:** produtos com `status_sistema == "bloqueado_historico"` ou
  `status_regulatorio == "bloqueado_historico"` não aparecem no select e são
  recusados na validação do POST.
- **Dose:** aceita vírgula ou ponto e, quando informada, deve ser maior que zero.
  Essa validação é apenas numérica; não há regra de dose correta, segura, ideal
  ou recomendada.
- **Avisos de tela:** o módulo reforça que é histórico operacional, não recomenda
  produto, não valida dose, não substitui profissional habilitado e não vende
  produtos.
- **Sem efeitos colaterais:** não cria `ProdutoPreco`, não cria `ProdutoImagem`,
  não cria venda, carrinho, cotação ou orçamento.

### Financeiro ✅
- CRUD de receitas/despesas com validação de tipo, valor positivo e data.
- Listagem com totais de receitas, despesas e saldo.

### Upload
- Envio e armazenamento de documentos/arquivos.
- Permanece pendente.

### Equipe ✅
- CRUD de membros e funções, escopado por propriedade.
- `funcao` poderá condicionar permissões finas futuramente.

### Colheita ✅
- CRUD vinculado a associação cultura↔gleba.
- Validação numérica simples de quantidade opcional.

### Mapa real
- Visualização das glebas em mapa.
- Permanece pendente.

### IA simulada
- Apoio informativo por IA simulada.
- Permanece pendente e não deve gerar recomendação agronômica definitiva.

### Relatórios
- Relatórios operacionais e financeiros.
- Permanece pendente.

---

## 10. Configuração, autenticação e segurança

- Configuração por ambiente em `app/config.py`.
- Sessão Flask assinada por `SECRET_KEY`, guardando dados mínimos do usuário.
- Senhas com `werkzeug.security`.
- Sem permissões finas por perfil no MVP atual.
- Sem Flask-WTF/CSRF dedicado nesta etapa.
- Templates Jinja com escaping padrão.
- Banco real, `.env`, uploads de usuário e arquivos sensíveis não são versionados.

---

## 11. Testes

- `pytest` é a ferramenta oficial.
- O app de teste é criado por `create_app("testing")` com SQLite em memória.
- Testes existentes cobrem: app factory, rotas protegidas, schema/modelos, seed,
  autenticação, CRUDs de Glebas/Culturas, Equipe/Financeiro, Colheita, consulta
  do catálogo e Aplicações de Insumo.
- O arquivo `tests/test_aplicacoes_crud.py` cobre login obrigatório, criação,
  validações, produto bloqueado, dose numérica, edição, remoção, escopo por
  propriedade, orientações de tela, ausência de termos de venda e garantia de que
  `ProdutoPreco`/`ProdutoImagem` não são criados.

---

## 12. Regras para implementação

- **Não** criar funcionalidades fora do escopo do MVP sem atualizar a documentação.
- **Não** inventar dados de produtos.
- **Não** afirmar validação AGROFIT/MAPA ou SIPEAGRO/MAPA sem fonte real.
- **Não** transformar o sistema em loja ou marketplace.
- **Não** vender produtos.
- **Não** exibir preço como cotação oficial.
- **Não** criar CRUD de produto no MVP atual.
- **Não** recomendar produto nem validar dose tecnicamente no módulo de aplicações.
- No MVP, **preço e imagem** devem aparecer como pendentes / não consolidados.
- A **validação diária do menor preço** pertence ao sistema final.
- Usar nomes de tabelas e campos compatíveis com o DER e o dicionário de dados.
- Priorizar código simples, modular e testável.
- Usar Application Factory e Blueprints.
- Nunca versionar `.env`, banco SQLite real, uploads de usuário ou arquivos sensíveis.

---

## 13. Checklist de fechamento e prontidão

**Concluído:**

- [x] Escopo consolidado
- [x] Requisitos revisados
- [x] Regras de negócio revisadas
- [x] DER revisado
- [x] Dicionário de dados revisado
- [x] Catálogo de produtos corrigido com IDs, slugs e classe
- [x] Estratégia de seed definida (`produto_base` + `produto_tecnico`; preço/imagem vazios no MVP)
- [x] Decisão final sobre ORM: Flask-SQLAlchemy
- [x] Fundação Flask criada (`src/run.py` + `src/app/`)
- [x] Blueprints placeholders criados
- [x] Modelos SQLAlchemy de domínio criados (15 tabelas em `src/app/models/`)
- [x] Schema validável por `db.create_all()` e comando `flask init-db`
- [x] Flask-Migrate/Alembic configurado e migration inicial versionada
- [x] Validação do seed técnico (`flask validate-catalog-seed`)
- [x] Importação idempotente do catálogo (`flask import-catalog-seed`)
- [x] Autenticação real (login/logout, sessão, `login_required`, `seed-users`)
- [x] CRUD de Glebas e Culturas (+ associação cultura↔gleba)
- [x] CRUD de Equipe e Financeiro (com totais receitas/despesas/saldo)
- [x] CRUD de Colheita (vinculada a cultura↔gleba)
- [x] Consulta do catálogo (Defensivos/Fertilizantes, somente leitura)
- [x] CRUD de Aplicações de Insumo (histórico operacional, sem recomendação)
- [x] Testes de fundação, schema, seed, autenticação, CRUDs e consulta do catálogo

**Pendente:**

- [ ] Upload
- [ ] Dashboard
- [ ] Mapa real
- [ ] IA simulada
- [ ] Relatórios
- [ ] Permissões finas por perfil/módulo
- [ ] Revisão e ajustes do MVP

---

## Documentos relacionados

- [00 — Visão Geral](./00-visao-geral.md)
- [02 — Requisitos do Sistema](./02-requisitos-do-sistema.md)
- [04 — Modelagem do Banco (DER)](./04-modelagem-banco-der.md)
- [05 — Dicionário de Dados](./05-dicionario-de-dados.md)
- [06 — Arquitetura do Sistema (visão conceitual)](./06-arquitetura-do-sistema.md)
- [07 — Roadmap do MVP](./07-roadmap-mvp.md)
- [Catálogo de Produtos](./catalogo-produtos/README.md)
