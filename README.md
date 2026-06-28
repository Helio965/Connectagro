# ConnectAgro

Plataforma web de **gestão agrícola** para pequenos, médios e grandes produtores.
O ConnectAgro centraliza culturas, glebas, insumos, finanças, equipe, colheita,
uploads, mapa, relatórios e apoio operacional por IA simulada.

> **Status do projeto:** MVP Flask com modelos SQLAlchemy, migrations,
> importação de catálogo técnico, autenticação real, permissões finas por perfil,
> Dashboard Operacional, Mapa real simplificado, IA Simulada Operacional, CRUDs de
> Glebas, Culturas, Equipe, Financeiro, Colheita, Aplicações de Insumo e Upload de
> Arquivos, consulta de Defensivos/Fertilizantes e Relatórios Operacionais HTML.
> O sistema não vende produtos, não recomenda produtos, não valida dose, não usa
> LLM/API externa, não faz OCR e não gera PDF/exportação nesta fase.

---

## Visão geral

O objetivo do ConnectAgro é dar ao produtor uma ferramenta simples para acompanhar
a operação da propriedade do plantio à colheita, com registro financeiro, equipe,
documentos, mapa, relatórios e consulta técnica de produtos agrícolas.

### O que o ConnectAgro é

- Uma plataforma de **gestão e consulta**.
- Um dashboard operacional da propriedade atual.
- Um catálogo técnico de produtos agrícolas para consulta rápida.
- Um sistema para registrar aplicações de insumo como histórico operacional.
- Um repositório local de documentos da propriedade no MVP.
- Uma visualização simples das glebas em mapa.
- Uma IA simulada por regras para leitura operacional dos dados locais.
- Relatórios HTML somente leitura.

### O que o ConnectAgro não é

- Não vende produtos.
- Não possui carrinho, checkout ou cotação.
- Não recomenda produtos nem valida dose.
- Não substitui profissional habilitado.
- Não usa LLM/API externa, OCR ou leitura automática de arquivos.
- Não afirma validação oficial AGROFIT/MAPA sem fonte real.

---

## Módulos do MVP

| Módulo | Descrição resumida |
|---|---|
| Login | Autenticação por sessão Flask |
| Permissões | Matriz por perfil (`admin`, `tecnico`, `trabalhador`) |
| Dashboard | Resumo operacional da propriedade atual |
| Culturas | Cadastro e acompanhamento das culturas |
| Glebas | Cadastro e gestão das áreas/talhões |
| Defensivos | Consulta de defensivos do catálogo |
| Fertilizantes | Consulta de fertilizantes do catálogo |
| Aplicações | Registro histórico operacional de aplicações de insumo |
| Financeiro | Registro de receitas e despesas |
| Upload | Envio, listagem, download e remoção de arquivos |
| Equipe | Gestão de membros e funções |
| Colheita | Registro e acompanhamento de colheita |
| Mapa real | Visualização das glebas em mapa |
| IA simulada | Apoio operacional por regras |
| Relatórios | Relatórios operacionais HTML |

---

## Stack tecnológica

- **Backend:** Python + Flask
- **Banco de dados:** SQLite + Flask-SQLAlchemy + Flask-Migrate
- **Frontend:** HTML, CSS, JavaScript, Jinja2
- **Testes:** pytest

---

## Estrutura do repositório

```txt
.
├── docs/
├── data/seeds/
├── migrations/
├── instance/              # banco e uploads locais; não versionado
├── src/
│   ├── run.py
│   └── app/
│       ├── __init__.py
│       ├── blueprints/
│       ├── models/
│       ├── services/
│       ├── utils/         # auth.py, contexto.py, permissions.py etc.
│       ├── templates/
│       └── static/
├── tests/
├── requirements.txt
└── .env.example
```

---

## Como executar

```bash
python -m venv .venv
# ative o ambiente conforme seu sistema operacional
pip install -r requirements.txt
flask --app src/run.py db upgrade
flask --app src/run.py validate-catalog-seed
flask --app src/run.py import-catalog-seed
flask --app src/run.py seed-users
python src/run.py
pytest
```

Rotas públicas: `/auth/login` e `/health`. Os módulos exigem login.

---

## Usuários de teste

| Perfil | E-mail | Senha |
|---|---|---|
| admin | admin@connectagro.com | admin123 |
| tecnico | tecnico@connectagro.com | tecnico123 |
| trabalhador | trabalhador@connectagro.com | trabalhador123 |

Não há cadastro público, convite de usuários, recuperação de senha ou painel de
administração de usuários nesta fase.

---

## Permissões por perfil

As permissões finas estão em `src/app/utils/permissions.py`. Elas usam o campo já
existente `usuario.perfil`, sem migration, sem tabela de permissões e sem RBAC
externo.

### Admin

Pode acessar todos os módulos e criar, editar e remover registros nos CRUDs da
sua propriedade atual, além de enviar, baixar e remover uploads.

### Técnico

Pode acessar dashboard, mapa, catálogo, relatórios, IA, equipe e financeiro em
leitura. Pode criar/editar glebas, culturas, colheitas e aplicações. Pode enviar
e baixar uploads. Não pode remover registros críticos, remover upload ou gerenciar
equipe/financeiro.

### Trabalhador

Pode acessar dashboard, mapa, catálogo, relatórios e IA; visualizar glebas,
culturas, colheitas e aplicações; criar colheitas, aplicações e uploads; e baixar
uploads. Não acessa equipe/financeiro e não edita/remove registros críticos.

O backend valida permissões e retorna **403** para ações não autorizadas. Os
templates usam `can(...)` para esconder menus, atalhos e botões indisponíveis.
Permissões não alteram o escopo por propriedade: cada usuário continua vendo
apenas dados da propriedade atual.

---

## Observações de segurança e escopo

- Senhas são armazenadas como hash.
- A sessão guarda apenas dados mínimos do usuário.
- Uploads ficam fora de `static` e são servidos por rota protegida.
- Registros operacionais são filtrados por propriedade.
- Catálogo e relatórios são somente leitura.
- CSRF/Flask-WTF ainda está pendente.

---

## Documentação principal

- [00 — Visão Geral](./docs/00-visao-geral.md)
- [01 — Escopo do Projeto](./docs/01-escopo-do-projeto.md)
- [03 — Regras de Negócio](./docs/03-regras-de-negocio.md)
- [04 — Modelagem do Banco (DER)](./docs/04-modelagem-banco-der.md)
- [05 — Dicionário de Dados](./docs/05-dicionario-de-dados.md)
- [06 — Arquitetura do Sistema](./docs/06-arquitetura-do-sistema.md)
- [06.1 — Arquitetura Técnica do MVP](./docs/06-1-arquitetura-tecnica-mvp.md)
- [07 — Roadmap do MVP](./docs/07-roadmap-mvp.md)
- [Catálogo de Produtos](./docs/catalogo-produtos/README.md)

---

## Próximos passos

Concluídos: fundação Flask, modelos/migrations, catálogo, autenticação,
permissões finas, dashboard, mapa, IA simulada, relatórios HTML e CRUDs
operacionais.

Próximo passo recomendado: **CSRF/Flask-WTF**, seguido da revisão final do MVP.

---

## Licença

A definir.
