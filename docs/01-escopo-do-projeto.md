# 01 — Escopo do Projeto

> Documento-base. Será detalhado nas próximas etapas. O escopo aqui descrito
> reflete a intenção do MVP e está sujeito a refinamento.

## Objetivo do MVP

Entregar uma versão funcional do ConnectAgro que permita ao produtor gerenciar
culturas, glebas, finanças, equipe e colheita, consultar um catálogo técnico de
insumos, registrar documentos e aplicações, visualizar suas áreas em mapa, usar
IA simulada e gerar relatórios operacionais.

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

## Escopo do MVP ampliado

O **MVP base** está consolidado. Por decisão de produto, foi aberto e concluído
o **MVP ampliado** (Fase 7), que incorpora ao escopo do MVP:

- **Painel de usuários** — gestão interna dos usuários da propriedade pelo
  admin (listar, criar, editar perfil/status, inativar). **Não** é cadastro
  público. **Concluído na Fase 7.1.**
- **Recuperação de senha** — solicitação de redefinição com token seguro e
  expirável, sem expor senha e sem envio real de e-mail. **Concluída na Fase 7.2.**
- **Auditoria/logs administrativos** — registro de ações sensíveis (login/
  logout, criação/edição/remoção, upload/download, acesso negado e exportações).
  **Concluída na Fase 7.3.**
- **PDF/exportações** — exportar relatórios operacionais, respeitando
  propriedade atual e permissões. Exportação **não** é cotação/venda.
  **Concluída na Fase 7.4.**
- **Mapa avançado** — edição e salvamento do polígono da gleba e melhor
  visualização, sem PostGIS obrigatório nem GPS em tempo real obrigatório.
  **Concluída na Fase 7.5.**

## Fora do MVP ampliado

Itens reconhecidos, mas **não** incluídos no MVP ampliado (avaliados depois):

- IA real/LLM (a IA do produto permanece **simulada**).
- Validação regulatória real do catálogo (AGROFIT/MAPA/SIPEAGRO).
- Preço/imagem com fontes reais e atualização periódica.
- OCR/leitura automática de uploads.
- Deploy/produção completo.

## Fora do produto

Itens **proibidos** como regra permanente do produto, salvo mudança radical de
produto explicitamente aprovada:

- Venda.
- Carrinho.
- Checkout.
- Cotação.

O ConnectAgro é uma plataforma de gestão agrícola e consulta técnica, **não** um
marketplace e **não** um sistema de comércio.

## Premissas

- O desenvolvimento ocorre em etapas e o MVP ampliado foi concluído na Fase 7.6.
- O catálogo técnico é consulta inicial; preço/imagem reais e validação
  regulatória oficial seguem fora do MVP ampliado.

## Restrições

- Stack fixada para o MVP: Python, Flask, SQLite, HTML, CSS, JavaScript.
- Nenhum dado de produto deve ser inventado ou apresentado como oficial sem
  fonte real.

## Documentos relacionados

- [00 — Visão Geral](./00-visao-geral.md)
- [02 — Requisitos do Sistema](./02-requisitos-do-sistema.md)
- [07 — Roadmap do MVP](./07-roadmap-mvp.md)
