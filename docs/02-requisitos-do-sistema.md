# 02 — Requisitos do Sistema

> Documento-base. Os requisitos abaixo são uma primeira versão e serão
> detalhados, numerados e priorizados nas próximas etapas.

## Como ler este documento

- **RF** = Requisito Funcional (o que o sistema deve fazer).
- **RNF** = Requisito Não Funcional (como o sistema deve se comportar).

---

## Requisitos Funcionais (RF)

### Login e acesso
- RF-01 — Permitir que usuários autentiquem-se com credenciais.
- RF-02 — Restringir o acesso aos módulos a usuários autenticados.

### Dashboard
- RF-03 — Exibir uma visão consolidada com indicadores da propriedade.

### Culturas
- RF-04 — Cadastrar, editar, listar e remover culturas.

### Glebas
- RF-05 — Cadastrar, editar, listar e remover glebas/talhões.

### Defensivos e Fertilizantes (catálogo)
- RF-06 — Consultar defensivos a partir do catálogo técnico.
- RF-07 — Consultar fertilizantes a partir do catálogo técnico.
- RF-08 — Exibir, quando indisponível, **preço e imagem como pendência**
  (dado não consolidado), sem inventar valores.

### Financeiro
- RF-09 — Registrar receitas e despesas.
- RF-10 — Listar e filtrar lançamentos financeiros.

### Upload
- RF-11 — Permitir envio e armazenamento de documentos/arquivos.

### Equipe
- RF-12 — Cadastrar membros da equipe e atribuir funções.

### Colheita
- RF-13 — Registrar e acompanhar o processo de colheita.

### Mapa real
- RF-14 — Visualizar as glebas em um mapa.

### IA simulada
- RF-15 — Oferecer apoio por IA com **respostas simuladas** no MVP.

### Relatórios
- RF-16 — Gerar relatórios operacionais e financeiros.

---

## Requisitos Não Funcionais (RNF)

- RNF-01 — **Tecnologia:** backend em Python/Flask, banco SQLite, frontend em
  HTML/CSS/JavaScript.
- RNF-02 — **Segurança:** senhas armazenadas de forma segura (hash); acesso
  protegido por autenticação.
- RNF-03 — **Usabilidade:** interface simples e adequada ao público produtor.
- RNF-04 — **Integridade de dados:** o catálogo não deve apresentar dados
  inventados nem validações regulatórias não comprovadas.
- RNF-05 — **Manutenibilidade:** código organizado por módulos, com documentação
  acompanhando a evolução.
- RNF-06 — **Portabilidade:** execução local simples para o MVP (SQLite, sem
  dependência de serviços externos obrigatórios).

---

## Documentos relacionados

- [01 — Escopo do Projeto](./01-escopo-do-projeto.md)
- [03 — Regras de Negócio](./03-regras-de-negocio.md)
- [06 — Arquitetura do Sistema](./06-arquitetura-do-sistema.md)
