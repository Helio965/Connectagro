# ConnectAgro

Plataforma web de **gestão agrícola** para pequenos, médios e grandes produtores.
O ConnectAgro centraliza o controle de culturas, glebas, insumos, finanças,
equipe, colheita e mapa, oferecendo ainda apoio por uma camada de IA e um
catálogo técnico de produtos agrícolas para consulta rápida.

> **Status do projeto:** início do desenvolvimento — fase de organização do
> repositório e documentação. O sistema Flask ainda **não** foi implementado.

---

## Visão geral

O objetivo do ConnectAgro é dar ao produtor uma ferramenta simples e organizada
para acompanhar a operação da propriedade do plantio à colheita, com registro
financeiro, gestão de equipe e visualização em mapa.

O sistema será desenvolvido inicialmente como **MVP** (Produto Mínimo Viável) e,
em etapas posteriores, evoluirá para a versão completa.

### O que o ConnectAgro **é**

- Uma plataforma de **gestão e consulta**.
- Um catálogo técnico de produtos agrícolas usado como **base de consulta rápida**.

### O que o ConnectAgro **não é**

- O sistema **não vende** produtos.
- Os valores de produtos servem **apenas como consulta rápida**.
- O catálogo é uma **base técnica inicial**, não uma verdade regulatória definitiva.

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
| Dashboard      | Visão consolidada da propriedade                                |
| Culturas       | Cadastro e acompanhamento das culturas                          |
| Glebas         | Cadastro e gestão das áreas/talhões                             |
| Defensivos     | Consulta de defensivos a partir do catálogo                     |
| Fertilizantes  | Consulta de fertilizantes a partir do catálogo                  |
| Financeiro     | Registro de receitas e despesas                                 |
| Upload         | Envio e armazenamento de documentos/arquivos                    |
| Equipe         | Gestão de membros e funções                                     |
| Colheita       | Registro e acompanhamento de colheita                           |
| Mapa real      | Visualização das glebas em mapa                                 |
| IA simulada    | Camada de apoio por IA (respostas simuladas no MVP)             |
| Relatórios     | Geração de relatórios operacionais e financeiros                |

---

## Stack tecnológica (MVP)

- **Backend:** Python + Flask
- **Banco de dados:** SQLite
- **Frontend:** HTML, CSS, JavaScript

---

## Estrutura do repositório

```txt
.
├── docs/                  # Documentação do projeto (visão, escopo, requisitos, DER...)
│   └── catalogo-produtos/ # Documentação e especificação do catálogo de produtos
├── data/                  # Dados de apoio do projeto
│   └── seeds/             # Dados de carga inicial (seeds) — ainda não definitivos
├── src/                   # Código-fonte da aplicação Flask (a ser implementado)
└── tests/                 # Testes automatizados (a serem implementados)
```

A documentação detalhada está em [`docs/`](./docs). Comece pela
[Visão Geral](./docs/00-visao-geral.md).

### Documentação principal

- [00 — Visão Geral](./docs/00-visao-geral.md)
- [01 — Escopo do Projeto](./docs/01-escopo-do-projeto.md)
- [04 — Modelagem do Banco (DER)](./docs/04-modelagem-banco-der.md)
- [05 — Dicionário de Dados](./docs/05-dicionario-de-dados.md)
- [06 — Arquitetura do Sistema](./docs/06-arquitetura-do-sistema.md) — **visão conceitual**
- [06.1 — Arquitetura Técnica do MVP](./docs/06-1-arquitetura-tecnica-mvp.md) — **guia técnico para futura implementação**
- [07 — Roadmap do MVP](./docs/07-roadmap-mvp.md)
- [Catálogo de Produtos](./docs/catalogo-produtos/README.md)

---

## Próximos passos

Este repositório está em fase de organização. Os próximos passos previstos são:

1. Consolidar **escopo**, **requisitos** e **regras de negócio**.
2. Definir a **modelagem do banco (DER)** e o **dicionário de dados**.
3. Receber o **catálogo de produtos corrigido** (sem dados inventados).
4. Implementar o código Flask do MVP, módulo a módulo.

Consulte o [Roadmap do MVP](./docs/07-roadmap-mvp.md) para o detalhamento.

---

## Licença

A definir.
