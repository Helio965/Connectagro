# 06 — Arquitetura do Sistema

> Documento-base. A arquitetura definitiva será detalhada conforme a
> implementação avança. Esta versão registra a direção pretendida para o MVP.

## Visão geral

O ConnectAgro (MVP) será uma aplicação web monolítica baseada em **Flask**, com
banco **SQLite** e frontend renderizado em **HTML/CSS/JavaScript**. A
organização favorece a separação por módulos para facilitar evolução futura.

## Camadas

- **Apresentação (frontend):** páginas HTML com CSS e JavaScript; templates
  servidos pelo Flask.
- **Aplicação (backend):** rotas/controladores Flask por módulo, contendo a
  lógica de cada funcionalidade.
- **Domínio / regras:** regras de negócio aplicadas no backend (ver
  [03 — Regras de Negócio](./03-regras-de-negocio.md)).
- **Dados:** camada de acesso ao SQLite.

## Organização de código (proposta)

A estrutura concreta de `src/` será definida na implementação. Uma proposta
inicial, sujeita a ajuste:

```txt
src/
├── app.py              # ponto de entrada da aplicação Flask
├── config.py           # configurações
├── models/             # modelos de dados
├── routes/ (ou blueprints/) # rotas por módulo
├── services/           # regras de negócio / serviços
├── templates/          # HTML
└── static/             # CSS, JS, imagens
```

> O uso de **Blueprints** do Flask é a abordagem pretendida para separar os
> módulos (login, culturas, glebas, financeiro, etc.).

## Decisões e restrições

- **Stack fixa no MVP:** Python/Flask, SQLite, HTML/CSS/JS.
- **IA simulada:** no MVP, o módulo de IA retorna respostas simuladas; não há
  integração com modelos em produção.
- **Catálogo como consulta:** sem venda; preço/imagem como pendência quando não
  consolidados.
- **Sem serviços externos obrigatórios:** o MVP deve rodar localmente de forma
  simples.

## Evolução futura

- Possível migração de SQLite para um SGBD mais robusto no sistema final.
- Integração de IA real e da validação diária de menor valor de produtos.

---

## Documentos relacionados

- [02 — Requisitos do Sistema](./02-requisitos-do-sistema.md)
- [04 — Modelagem do Banco (DER)](./04-modelagem-banco-der.md)
- [07 — Roadmap do MVP](./07-roadmap-mvp.md)
