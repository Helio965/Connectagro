# src/

Código-fonte da aplicação **ConnectAgro** (backend Flask + frontend).

## Estado atual

> ⚠️ **Ainda não há código funcional.** A implementação só deve começar **após a
> aprovação da arquitetura técnica** descrita em
> [06.1 — Arquitetura Técnica do MVP](../docs/06-1-arquitetura-tecnica-mvp.md)
> (ver checklist de prontidão naquele documento e a Etapa 4 do
> [roadmap](../docs/07-roadmap-mvp.md)).

## Stack

- **Backend:** Python + Flask
- **Banco de dados:** SQLite local ou PostgreSQL/Supabase por configuração
- **Frontend:** HTML, CSS, JavaScript

## Estrutura profissional planejada

Estrutura **planejada** (package Flask com Application Factory + Blueprints) — a
ser criada quando a implementação começar:

```text
src/
├── run.py                       # ponto de entrada (chama create_app)
├── app/
│   ├── __init__.py              # create_app / Application Factory
│   ├── config.py                # configurações por ambiente
│   ├── extensions.py            # instâncias de extensões (db, csrf, etc.)
│   ├── models/                  # modelos de dados (espelham o DER)
│   ├── blueprints/              # um pacote por módulo do MVP
│   ├── services/                # regras de negócio
│   ├── templates/               # HTML (Jinja2)
│   ├── static/                  # css/, js/, uploads/
│   └── utils/                   # helpers
├── instance/                    # banco SQLite e config de instância (não versionado)
└── tests/                       # testes com pytest
```

Detalhes completos (estrutura expandida, blueprints, decisão de ORM, segurança e
fluxos) estão em
[06.1 — Arquitetura Técnica do MVP](../docs/06-1-arquitetura-tecnica-mvp.md).

## Módulos previstos

Login · Dashboard · Culturas · Glebas · Defensivos · Fertilizantes ·
Financeiro · Upload · Equipe · Colheita · Mapa real · IA simulada · Relatórios.

---

## Documentos relacionados

- [06 — Arquitetura do Sistema](../docs/06-arquitetura-do-sistema.md)
- [06.1 — Arquitetura Técnica do MVP](../docs/06-1-arquitetura-tecnica-mvp.md)
- [07 — Roadmap do MVP](../docs/07-roadmap-mvp.md)
