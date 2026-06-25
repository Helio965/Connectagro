# 05 — Dicionário de Dados

> **Documento-base / placeholder.** O dicionário de dados definitivo será
> preenchido após a consolidação do [DER](./04-modelagem-banco-der.md). Este
> arquivo estabelece o formato que será usado para descrever cada tabela e
> campo.

## Objetivo

Documentar, de forma padronizada, cada tabela do banco e seus campos: nome,
tipo, obrigatoriedade, descrição e observações. Isso garante clareza para a
implementação e manutenção.

## Formato padrão por tabela

Cada tabela será documentada no seguinte formato:

### Tabela: `nome_da_tabela`

Descrição: _objetivo da tabela._

| Campo        | Tipo      | Obrigatório | Descrição                         | Observações                 |
| ------------ | --------- | ----------- | --------------------------------- | --------------------------- |
| id           | INTEGER   | Sim         | Identificador único (PK)          | Autoincremento              |
| ...          | ...       | ...         | ...                               | ...                         |

## Convenções (preliminares)

- Nomes de tabelas e colunas em **snake_case**.
- Toda tabela possui chave primária `id`.
- Datas/horas em formato ISO 8601.
- Campos de produto sem fonte confiável (ex.: preço, imagem) são marcados como
  **não consolidados**, conforme as [Regras de Negócio](./03-regras-de-negocio.md).

> As tabelas concretas serão adicionadas aqui assim que o DER for fechado.

---

## Documentos relacionados

- [04 — Modelagem do Banco (DER)](./04-modelagem-banco-der.md)
- [03 — Regras de Negócio](./03-regras-de-negocio.md)
