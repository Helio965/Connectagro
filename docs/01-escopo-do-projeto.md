# 01 — Escopo do Projeto

> Documento-base. Será detalhado nas próximas etapas. O escopo aqui descrito
> reflete a intenção do MVP e está sujeito a refinamento.

## Objetivo do MVP

Entregar uma versão funcional mínima do ConnectAgro que permita ao produtor
gerenciar culturas, glebas, finanças, equipe e colheita, consultar um catálogo
técnico de insumos e visualizar suas áreas em mapa, com apoio de uma camada de
IA simulada e geração de relatórios.

## Escopo incluído (MVP)

Os módulos previstos para o MVP são:

| #  | Módulo        | Resumo do escopo                                              |
| -- | ------------- | ------------------------------------------------------------ |
| 1  | Login         | Autenticação de usuários e controle de acesso                |
| 2  | Dashboard     | Painel consolidado com indicadores principais                |
| 3  | Culturas      | Cadastro e acompanhamento das culturas da propriedade        |
| 4  | Glebas        | Cadastro e gestão de áreas/talhões                           |
| 5  | Defensivos    | Consulta de defensivos a partir do catálogo técnico          |
| 6  | Fertilizantes | Consulta de fertilizantes a partir do catálogo técnico       |
| 7  | Financeiro    | Registro de receitas e despesas                              |
| 8  | Upload        | Envio e armazenamento de documentos/arquivos                 |
| 9  | Equipe        | Cadastro de membros e atribuição de funções                  |
| 10 | Colheita      | Registro e acompanhamento do processo de colheita            |
| 11 | Mapa real     | Visualização geográfica das glebas                           |
| 12 | IA simulada   | Camada de apoio por IA com respostas simuladas               |
| 13 | Relatórios    | Geração de relatórios operacionais e financeiros             |

## Catálogo de produtos (escopo)

- Base técnica de produtos: defensivos, fertilizantes, corretivos, inoculantes
  e biofertilizantes.
- Uso exclusivo de **consulta rápida**.
- **Preço e imagem** entram como pendência / dado não consolidado.
- Sem validação oficial AGROFIT/MAPA no MVP.

## Fora de escopo (MVP)

Os itens abaixo **não** fazem parte do MVP e ficam para o sistema final ou
etapas futuras:

- Venda ou checkout de produtos.
- Validação diária e automatizada do menor valor de produtos.
- Validação regulatória oficial (AGROFIT/MAPA) integrada.
- IA real conectada a modelos de linguagem em produção (no MVP é **simulada**).
- Integrações externas com ERPs, bancos ou marketplaces.
- Aplicativo mobile nativo.

## Premissas

- O desenvolvimento ocorre em etapas; este repositório está na etapa de
  organização e documentação.
- O catálogo de produtos será fornecido **corrigido** em etapa posterior, sem
  dados inventados.

## Restrições

- Stack fixada para o MVP: Python, Flask, SQLite, HTML, CSS, JavaScript.
- Nenhum dado de produto deve ser inventado ou apresentado como oficial sem
  fonte real.

## Documentos relacionados

- [00 — Visão Geral](./00-visao-geral.md)
- [02 — Requisitos do Sistema](./02-requisitos-do-sistema.md)
- [07 — Roadmap do MVP](./07-roadmap-mvp.md)
