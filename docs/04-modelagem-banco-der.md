# 04 — Modelagem do Banco (DER)

> **Documento-base / placeholder.** O Diagrama Entidade-Relacionamento (DER)
> definitivo será fornecido e detalhado em etapa posterior. Este arquivo reserva
> o espaço e registra as entidades candidatas, sem fixar ainda chaves,
> cardinalidades ou tipos.

## Objetivo

Descrever a estrutura de dados do ConnectAgro: entidades, atributos e
relacionamentos, servindo de base para a criação do schema SQLite.

## Entidades candidatas (preliminar)

A lista abaixo é uma primeira aproximação derivada dos módulos do MVP e **não**
é definitiva:

- **Usuario** — usuários do sistema (login/acesso).
- **Membro de Equipe** — pessoas da operação e suas funções.
- **Cultura** — culturas cadastradas.
- **Gleba** — áreas/talhões da propriedade.
- **Produto** — itens do catálogo técnico (defensivos, fertilizantes,
  corretivos, inoculantes, biofertilizantes).
- **Categoria de Produto** — classificação dos produtos do catálogo.
- **Lançamento Financeiro** — receitas e despesas.
- **Colheita** — registros de colheita.
- **Documento/Upload** — arquivos enviados.

## Relacionamentos candidatos (preliminar)

- Cultura ↔ Gleba (a definir cardinalidade).
- Colheita → Cultura/Gleba.
- Produto → Categoria de Produto.
- Lançamento Financeiro → (origem a definir: cultura, gleba, etc.).

> ⚠️ As cardinalidades, chaves primárias/estrangeiras e atributos serão
> definidos no DER oficial. **Nada aqui deve ser tratado como esquema final.**

## Diagrama

O diagrama (imagem e/ou versão textual, ex.: Mermaid/dbml) será adicionado nesta
seção na etapa de modelagem.

```text
[ DER a ser inserido ]
```

---

## Documentos relacionados

- [03 — Regras de Negócio](./03-regras-de-negocio.md)
- [05 — Dicionário de Dados](./05-dicionario-de-dados.md)
- [06 — Arquitetura do Sistema](./06-arquitetura-do-sistema.md)
