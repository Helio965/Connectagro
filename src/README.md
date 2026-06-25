# src/

Código-fonte da aplicação **ConnectAgro** (backend Flask + frontend).

## Estado atual

> ⚠️ **Ainda não há código funcional.** O sistema Flask será implementado nas
> próximas etapas do [roadmap](../docs/07-roadmap-mvp.md).

## Stack

- **Backend:** Python + Flask
- **Banco de dados:** SQLite
- **Frontend:** HTML, CSS, JavaScript

## Estrutura proposta

A organização concreta será definida no início da implementação. Proposta
inicial (ver [Arquitetura do Sistema](../docs/06-arquitetura-do-sistema.md)):

```txt
src/
├── app.py              # ponto de entrada da aplicação Flask
├── config.py           # configurações
├── models/             # modelos de dados
├── routes/             # rotas/blueprints por módulo
├── services/           # regras de negócio
├── templates/          # HTML
└── static/             # CSS, JS, imagens
```

## Módulos previstos

Login · Dashboard · Culturas · Glebas · Defensivos · Fertilizantes ·
Financeiro · Upload · Equipe · Colheita · Mapa real · IA simulada · Relatórios.

---

## Documentos relacionados

- [06 — Arquitetura do Sistema](../docs/06-arquitetura-do-sistema.md)
- [07 — Roadmap do MVP](../docs/07-roadmap-mvp.md)
