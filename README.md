# ConnectAgro

Plataforma web de **gestão agrícola** para pequenos, médios e grandes produtores.
O ConnectAgro centraliza o controle de culturas, glebas, insumos, finanças,
equipe, colheita, upload de documentos e mapa, oferecendo ainda apoio por uma
camada de IA simulada, relatórios operacionais e um catálogo técnico de produtos
agrícolas para consulta rápida.

> **Status do projeto:** fundação Flask, **modelos SQLAlchemy** (17 tabelas),
> **migrations** (Flask-Migrate), **importação do catálogo técnico** (via CLI),
> **autenticação real** (login/logout), **recuperação de senha** (token seguro,
> sem e-mail real), **permissões finas por perfil**,
> **CSRF/Flask-WTF** nos formulários POST,
> **Painel de Usuários** interno por propriedade,
> **Dashboard Operacional** somente leitura, **Mapa real simplificado** somente
> leitura, **IA Simulada Operacional** baseada em regras locais, **CRUDs** de
> **Glebas**, **Culturas** (com associação cultura↔gleba), **Equipe**,
> **Financeiro** (com totais), **Colheita**, **Aplicações de Insumo** (registro
> histórico operacional) e **Upload de Arquivos** (armazenamento local com
> metadados), além da **consulta somente leitura** do catálogo de **Defensivos** e
> **Fertilizantes** e dos **Relatórios Operacionais HTML** (geral, financeiro,
> agrícola, aplicações e uploads), somente leitura. Não há CRUD de produtos;
> `produto_preco`/`produto_imagem` continuam **vazios** no MVP. O sistema **não
> vende produtos**, não recomenda produtos, não valida dose, não usa LLM/API
> externa, não faz OCR/IA/extração automática de arquivos, não gera PDF/exportação
> e não oferece recursos avançados de mapa; o banco populado e uploads reais
> **não** são versionados.
>
> **MVP base consolidado:** a Fase 6.5 conclui a revisão final do MVP base, com
> validação da suíte automatizada, limpeza dos avisos legados simples e checklist
> de entrega.
>
> **MVP ampliado (em andamento):** após decisão de produto, foi aberto o **MVP
> ampliado** (Fase 7). A Fase 7.0 registrou a decisão de escopo, a **Fase 7.1
> implementa o painel de usuários** interno da propriedade e a **Fase 7.2
> implementa a recuperação de senha** (token seguro/expirável, sem envio real de
> e-mail). Seguem no escopo do MVP ampliado: **auditoria/logs administrativos**,
> **PDF/exportações** e **mapa avançado**. Continuam **fora do MVP ampliado** IA real/LLM, validação regulatória real
> do catálogo, preço/imagem com fontes reais, OCR/leitura automática de uploads e
> deploy/produção completo. **Venda, carrinho, checkout e cotação nunca entram no
> produto.**

---

## Visão geral

O objetivo do ConnectAgro é dar ao produtor uma ferramenta simples e organizada
para acompanhar a operação da propriedade do plantio à colheita, com registro
financeiro, gestão de equipe, documentos, relatórios, apoio operacional por IA
simulada e visualização em mapa.

O sistema será desenvolvido inicialmente como **MVP** (Produto Mínimo Viável) e,
em etapas posteriores, evoluirá para a versão completa.

### O que o ConnectAgro **é**

- Uma plataforma de **gestão e consulta**.
- Um dashboard operacional somente leitura para resumir dados já cadastrados.
- Um catálogo técnico de produtos agrícolas usado como **base de consulta rápida**.
- Um sistema para registrar aplicações de insumo como **histórico operacional**.
- Um sistema para armazenar localmente documentos da propriedade no MVP.
- Uma visualização simples das glebas em mapa, baseada nas coordenadas cadastradas.
- Uma IA simulada por regras para apoiar a leitura operacional dos dados locais da propriedade.
- Um conjunto de relatórios HTML somente leitura, escopados pela propriedade atual.
- Um controle básico de acesso por perfil (`admin`, `tecnico`, `trabalhador`).
- Um painel interno para o `admin` gerenciar usuários vinculados à propriedade.

### O que o ConnectAgro **não é**

- O sistema **não vende** produtos.
- Os valores de produtos servem **apenas como consulta rápida**.
- O catálogo é uma **base técnica inicial**, não uma verdade regulatória definitiva.
- O registro de aplicação de insumo **não recomenda produtos** e **não valida dose**.
- A IA simulada **não** usa LLM/API externa, não substitui profissional habilitado,
  não recomenda produtos, não valida dose e não faz diagnóstico agronômico.
- O upload **não** faz OCR, IA, extração automática ou validação documental avançada.
- O mapa do MVP **não** mede área, não desenha polígonos e não usa GPS em tempo real.
- Os relatórios do MVP **não** geram PDF, CSV, Excel ou exportação automática.

> **Importante sobre dados de produtos:** no MVP, **preço e imagem** devem ser
> tratados como **pendência / dado não consolidado**. A validação diária do menor
> valor atualizado fica para o sistema final. Não há, neste momento, validação
> oficial AGROFIT/MAPA — nenhum produto deve ser apresentado como "validado
> oficialmente" sem fonte real comprovada.

---

## Módulos do MVP

| Módulo         | Descrição resumida                                              |
| -------------- | --------------------------------------------------------------- |
| Login          | Autenticação e controle de acesso                               |
| Recuperar senha| Redefinição por token seguro/expirável, sem e-mail real         |
| Permissões     | Matriz por perfil (`admin`, `tecnico`, `trabalhador`)           |
| CSRF           | Token CSRF em formulários POST com Flask-WTF                    |
| Usuários       | Painel interno de usuários da propriedade, sem cadastro público |
| Dashboard      | Resumo operacional somente leitura da propriedade atual         |
| Culturas       | Cadastro e acompanhamento das culturas                          |
| Glebas         | Cadastro e gestão das áreas/talhões                             |
| Defensivos     | Consulta de defensivos a partir do catálogo                     |
| Fertilizantes  | Consulta de fertilizantes a partir do catálogo                  |
| Aplicações     | Registro histórico operacional de aplicações de insumo          |
| Financeiro     | Registro de receitas e despesas                                 |
| Upload         | Envio, listagem, download e remoção de arquivos da propriedade  |
| Equipe         | Gestão de membros e funções                                     |
| Colheita       | Registro e acompanhamento de colheita                           |
| Mapa real      | Visualização das glebas em mapa                                 |
| IA simulada    | Apoio operacional por regras, com histórico por propriedade     |
| Relatórios     | Relatórios operacionais HTML somente leitura                    |

---

## Stack tecnológica (MVP)

- **Backend:** Python + Flask
- **Banco de dados:** SQLite + Flask-SQLAlchemy + Flask-Migrate
- **Segurança de formulários:** Flask-WTF / CSRFProtect
- **Frontend:** HTML, CSS, JavaScript, Jinja2
- **Testes:** pytest

---

## Estrutura do repositório

```txt
.
├── docs/                  # Documentação do projeto (visão, escopo, requisitos, DER...)
│   └── catalogo-produtos/ # Documentação e especificação do catálogo de produtos
├── data/                  # Dados de apoio do projeto
│   └── seeds/             # Seed técnico do catálogo (JSON/CSV) — importável via CLI
├── migrations/            # Flask-Migrate/Alembic (schema inicial + evoluções)
├── instance/              # Banco SQLite e uploads locais em execução — não versionado
├── src/                   # Código-fonte da aplicação Flask
│   ├── run.py             # ponto de entrada
│   └── app/               # package Flask (Application Factory)
│       ├── __init__.py    # create_app
│       ├── config.py      # configuração por ambiente
│       ├── extensions.py  # extensões (Flask-SQLAlchemy, Flask-Migrate)
│       ├── blueprints/    # auth + CRUDs + catálogo + módulos protegidos
│       ├── models/        # modelos SQLAlchemy de domínio (16 tabelas)
│       ├── commands.py    # CLI: init-db, validate/import-catalog-seed, seed-users
│       ├── services/      # regras de negócio e agregações (dashboard, IA, relatórios)
│       ├── utils/         # auth.py, contexto.py, formatters.py, permissions.py
│       ├── templates/     # HTML (Jinja2)
│       └── static/        # css/, js/ (arquivos públicos)
├── tests/                 # testes (pytest)
├── requirements.txt       # dependências
└── .env.example           # exemplo de variáveis de ambiente
```

A documentação detalhada está em [`docs/`](./docs). Comece pela
[Visão Geral](./docs/00-visao-geral.md).

## Como executar (MVP)

Fluxo recomendado, a partir da raiz do projeto:

```bash
# 1. Ambiente virtual
python -m venv .venv
# ative o ambiente conforme seu SO (ex.: source .venv/bin/activate)

# 2. Dependências
pip install -r requirements.txt

# 3. Schema do banco (migrations — Flask-Migrate/Alembic)
flask --app src/run.py db upgrade

# 4. Importar o catálogo técnico (opcional; idempotente)
flask --app src/run.py validate-catalog-seed
flask --app src/run.py import-catalog-seed

# 5. Criar os usuários de teste (idempotente)
flask --app src/run.py seed-users

# 6. Subir a aplicação
python src/run.py

# 7. Acessar /auth/login e entrar com um usuário de teste

# 8. Rodar os testes
pytest
```

O acesso exige **login** (sessão Flask + `werkzeug.security`): a rota `/` e os
módulos são protegidos e redirecionam para `/auth/login`; `/health` é público. O
arquivo de banco gerado **não** é versionado.

### Dashboard operacional

O Dashboard em `/` é protegido por login e mostra um resumo somente leitura da
propriedade atual. Ele agrega dados já existentes de Glebas, Culturas,
Financeiro, Equipe, Colheita, Aplicações de Insumo, Upload e Catálogo.

Indicadores principais:

- total de glebas, área somada e glebas sem área informada;
- culturas por status e associações cultura↔gleba;
- receitas, despesas, saldo e últimos lançamentos financeiros;
- membros de equipe ativos/inativos;
- registros e somas de colheita por unidade;
- aplicações recentes como histórico operacional;
- total e tamanho aproximado dos uploads;
- totais globais do catálogo técnico por classe e produtos bloqueados/históricos.

O Dashboard não cria dados, não altera schema e não implementa gráficos externos.

### Mapa real simplificado

O módulo Mapa em `/mapa/` é protegido por login e mostra uma visualização somente
leitura das glebas da propriedade atual usando as coordenadas já cadastradas em
`Gleba.latitude` e `Gleba.longitude`. A rota `/mapa/dados` entrega JSON escopado
pela propriedade atual, sem dados de usuário/e-mail e separando glebas sem
coordenadas válidas.

O frontend usa Leaflet via CDN e renderiza marcadores. Quando `poligono_geojson`
contém GeoJSON válido, ele pode ser exibido em modo somente leitura; conteúdo
inválido é ignorado com segurança. A página continua renderizando mesmo sem
internet, embora o mapa visual dependa da biblioteca externa.

O módulo não cria, edita ou remove glebas, não altera schema, não usa PostGIS,
não mede área, não desenha polígonos, não importa/exporta GeoJSON e não usa GPS
em tempo real.

### IA simulada operacional

O módulo IA em `/ia/` é protegido por login e oferece apoio operacional por regras
simples. Ele usa dados locais já cadastrados na propriedade atual para responder
sobre resumo geral, financeiro, glebas, culturas, colheita, aplicações de insumo,
documentos e catálogo.

Cada pergunta/resposta válida é registrada em `ia_interacao` com `usuario_id`,
`propriedade_id`, `pergunta`, `resposta` e `tipo="simulada"`. O histórico exibido
mostra apenas as últimas interações do usuário e da propriedade atual.

A IA simulada não usa LLM, OpenAI, Claude, Gemini, API externa, internet ou
machine learning. Ela não recomenda produtos, não valida dose, não faz diagnóstico
agronômico, não consulta fontes oficiais em tempo real e não lê o conteúdo dos
arquivos enviados.

### Upload de arquivos

O módulo Upload armazena arquivos localmente no MVP usando
`UPLOAD_FOLDER` (`instance/uploads` por padrão), em subpastas por propriedade
(`propriedade_<id>/`). Essa pasta padrão fica fora de `src/app/static`, então os
arquivos enviados não são servidos diretamente por `/static/uploads`; o acesso
continua passando pela rota protegida de download, com validação da propriedade.

O banco guarda apenas metadados e caminho relativo seguro; arquivos reais
enviados por usuários são ignorados pelo Git.

Extensões permitidas no MVP: `pdf`, `png`, `jpg`, `jpeg`, `csv`, `xlsx`, `txt` e
`docx`. Executáveis, scripts, compactados e HTML/PHP/Python são bloqueados pela
allowlist. O módulo não faz OCR, IA, leitura automática, classificação ou
extração de dados.

### Relatórios operacionais

Em `/relatorios/` há uma central com cinco relatórios **HTML somente leitura**,
escopados pela propriedade atual: **geral**, **financeiro** (com filtros de
período e tipo), **agrícola**, **aplicações** (com filtros de período e classe) e
**uploads**. Os relatórios apenas consultam dados já existentes — não criam,
alteram ou removem nada. Não há geração de PDF nem exportação CSV/Excel nesta
fase; a impressão usa o recurso do próprio navegador (`window.print()`). Os
relatórios não recomendam produtos, não validam dose e não leem o conteúdo dos
uploads.

### Permissões por perfil

A Fase 6.3 adicionou permissões finas usando `src/app/utils/permissions.py`.
A autorização usa o campo `usuario.perfil`, sem tabela de roles/permissões e sem
dependência externa de RBAC. A Fase 7.1 acrescentou permissões `usuarios.*`,
liberadas apenas para `admin`.

Elementos principais:

- `PERMISSOES_POR_PERFIL` define a matriz dos perfis `admin`, `tecnico` e
  `trabalhador`.
- `require_permission(...)` protege rotas sensíveis no backend e retorna **403**
  para ação não autorizada.
- `can(...)` fica disponível nos templates para esconder menus, atalhos e botões
  que o perfil não pode usar.
- O handler 403 renderiza `templates/errors/403.html`.
- As permissões não substituem o escopo por propriedade: cada usuário continua
  acessando apenas os dados da sua propriedade atual.

Resumo dos perfis:

| Perfil | Permissões principais |
| ------ | --------------------- |
| admin | Acessa todos os módulos e pode criar, editar e remover registros nos CRUDs da sua propriedade atual; pode enviar, baixar e remover uploads. |
| tecnico | Acessa dashboard, mapa, catálogo, relatórios, IA, equipe e financeiro em leitura; cria/edita glebas, culturas, colheitas e aplicações; envia e baixa uploads; não remove registros críticos nem gerencia equipe/financeiro. |
| trabalhador | Acessa dashboard, mapa, catálogo, relatórios e IA; visualiza glebas, culturas, colheitas e aplicações; cria colheitas, aplicações e uploads; baixa upload; não acessa equipe/financeiro e não edita/remove registros críticos. |

### Proteção CSRF

A Fase 6.4 adicionou proteção CSRF real com Flask-WTF/CSRFProtect.
Todos os formulários POST do MVP renderizam `csrf_token()`, incluindo login,
CRUDs, formulários de remoção, Upload multipart e IA simulada. Requisições POST
sem token válido retornam **400** com mensagem amigável.

O ambiente de testes (`TestingConfig`) mantém `WTF_CSRF_ENABLED = False` por
padrão para preservar a suíte existente. Os testes específicos de CSRF ativam a
proteção explicitamente em `tests/test_csrf.py`.

CSRF não substitui autenticação, permissões por perfil nem escopo por
propriedade.

### Painel de usuários

A Fase 7.1 adiciona o módulo `/usuarios/`, disponível somente para `admin`.
Ele permite listar usuários vinculados à propriedade atual, criar usuário com
senha temporária, editar nome/perfil/status e inativar acesso. Não há cadastro
público, remoção física de usuário, recuperação de senha, auditoria ou painel de
roles nesta fase.

O vínculo entre conta e propriedade passa pela tabela `usuario_propriedade`.
`propriedade.usuario_id` continua preservado para compatibilidade; quando uma
base antiga ainda não tem vínculo, `propriedade_atual()` cria a associação ativa
automaticamente. O comando `seed-users` também cria uma propriedade demo e
vincula os três usuários de teste de forma idempotente.

### Recuperação de senha

A Fase 7.2 adiciona um fluxo seguro de redefinição de senha, **sem envio real de
e-mail** nesta etapa. No login há o link **"Esqueci minha senha"**
(`/auth/esqueci-senha`): o usuário informa o e-mail e o sistema responde sempre
com a **mesma mensagem genérica**, evitando revelar se o e-mail existe.

Se o usuário existir e estiver **ativo**, é gerado um **token seguro**
(`secrets.token_urlsafe`), **expirável** (`PASSWORD_RESET_TOKEN_MINUTES`, padrão
30) e de **uso único**. O banco (`senha_reset_token`) guarda apenas o **hash**
(SHA-256) do token — o token puro nunca é persistido e nenhuma senha é gravada
nessa tabela. Solicitar um novo reset invalida os tokens abertos anteriores.

Em ambiente **local/dev/teste** (`PASSWORD_RESET_SHOW_DEV_LINK`), o link de
redefinição é exibido na própria tela para teste manual; em **produção, nunca**.
A redefinição (`/auth/redefinir-senha/<token>`) valida o token, exige nova senha
(mínimo 6 caracteres) e confirmação, grava o hash, marca o token como usado,
**não reativa** usuário inativo e **não** faz login automático — redireciona ao
login. Não há SMTP/Flask-Mail, fila, agendador ou deploy nesta fase.

### Usuários de teste (`seed-users`)

| Perfil      | E-mail                       | Senha           |
| ----------- | ---------------------------- | --------------- |
| admin       | admin@connectagro.com        | admin123        |
| tecnico     | tecnico@connectagro.com      | tecnico123      |
| trabalhador | trabalhador@connectagro.com  | trabalhador123  |

> `seed-users` cria/garante também uma propriedade demo e vínculos ativos em
> `usuario_propriedade` para os três usuários, sem sobrescrever senhas existentes.
>
> A importação do catálogo popula apenas `produto_base` + `produto_tecnico`;
> `produto_preco`/`produto_imagem` permanecem vazios no MVP e itens bloqueados
> (Paraquate/Oxamil) não são importados. Alternativa pontual ao passo 3 (sem
> migrations): `flask --app src/run.py init-db`.

### Documentação principal

- [00 — Visão Geral](./docs/00-visao-geral.md)
- [01 — Escopo do Projeto](./docs/01-escopo-do-projeto.md)
- [04 — Modelagem do Banco (DER)](./docs/04-modelagem-banco-der.md)
- [05 — Dicionário de Dados](./docs/05-dicionario-de-dados.md)
- [06 — Arquitetura do Sistema](./docs/06-arquitetura-do-sistema.md) — **visão conceitual**
- [06.1 — Arquitetura Técnica do MVP](./docs/06-1-arquitetura-tecnica-mvp.md) — **guia técnico detalhado do MVP**
- [07 — Roadmap do MVP](./docs/07-roadmap-mvp.md)
- [08 — Checklist Final do MVP](./docs/08-checklist-final-mvp.md)
- [09 — Roadmap do MVP Ampliado](./docs/09-roadmap-mvp-ampliado.md)
- [Catálogo de Produtos](./docs/catalogo-produtos/README.md) — inclui o [catálogo técnico](./docs/catalogo-produtos/catalogo-tecnico-connectagro-mvp.md) e o **seed técnico** ([`data/seeds/`](./data/seeds/README.md))

---

## Próximos passos

Concluídos: documentação de produto, modelagem (DER + dicionário), catálogo
técnico/seed, a **fundação Flask**, os **modelos SQLAlchemy de domínio** (17
tabelas), migrations, autenticação real, recuperação de senha, permissões finas
por perfil, CSRF/Flask-WTF nos formulários POST, Dashboard
Operacional, Mapa real simplificado, IA Simulada Operacional, Relatórios
Operacionais HTML, CRUDs de glebas/culturas/equipe/financeiro/colheita/aplicações
de insumo/upload, Painel de Usuários interno e consulta somente leitura de
Defensivos/Fertilizantes.

O **MVP base está consolidado** e o projeto segue na fase de **MVP ampliado**
(Fase 7). As Fases **7.1 — Painel de usuários** e **7.2 — Recuperação de senha**
estão implementadas. O MVP ampliado ainda incorporará, em fases 7.x:

- auditoria/logs administrativos;
- PDF/exportações dos relatórios operacionais;
- mapa avançado (edição/salvamento de polígono da gleba).

Continuam **fora do MVP ampliado** (avaliados depois): IA real/LLM, validação
regulatória real do catálogo, preço/imagem com fontes reais e atualização
periódica, OCR/leitura automática de uploads e deploy/produção completo. A IA
**simulada** continua sendo a IA oficial também no MVP ampliado.

**Nunca entram no produto** (regra permanente, salvo mudança radical de produto
explicitamente aprovada): **venda, carrinho, checkout e cotação**. O ConnectAgro
permanece uma plataforma de gestão agrícola e consulta técnica, **sem
marketplace e sem comércio**.

O **próximo passo técnico** é a **Fase 7.3 — Auditoria/logs**. Consulte o
[Roadmap do MVP](./docs/07-roadmap-mvp.md) e o
[Roadmap do MVP Ampliado](./docs/09-roadmap-mvp-ampliado.md) para o detalhamento.

---

## Licença

A definir.
