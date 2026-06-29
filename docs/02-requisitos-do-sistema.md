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

## Requisitos Funcionais — MVP ampliado

> Os requisitos abaixo descrevem o **escopo do MVP ampliado** (Fase 7). As Fases
> 7.1 (painel de usuários) e 7.2 (recuperação de senha) já estão implementadas;
> os demais itens seguem planejados para fases 7.x. Nenhum deles inclui venda,
> carrinho, checkout ou cotação.

### Painel de usuários (Fase 7.1)
- RF-17 — Permitir que o **admin** liste os usuários da sua propriedade.
- RF-18 — Permitir que o **admin** crie usuário (sem cadastro público).
- RF-19 — Permitir que o **admin** edite perfil e status do usuário.
- RF-20 — Permitir que o **admin** inative um usuário.
- RF-20a — Vincular usuários à propriedade por `usuario_propriedade`, preservando
  `propriedade.usuario_id` para compatibilidade com bases anteriores.
- RF-20b — Impedir que o painel deixe a propriedade sem nenhum `admin` ativo.

### Recuperação de senha (Fase 7.2) ✅
- RF-21 — Permitir que o usuário solicite redefinição de senha em
  `/auth/esqueci-senha`, com **mensagem genérica** (sem enumeração de e-mails).
- RF-22 — Gerar **token seguro** (`secrets.token_urlsafe`) de redefinição, com
  **expiração** configurável; armazenar apenas o **hash** do token.
- RF-23 — Permitir redefinir a senha mediante token válido em
  `/auth/redefinir-senha/<token>`, sem expor a senha; token de **uso único**.
- RF-24 — **Sem envio real de e-mail** nesta fase: em ambiente local/dev/teste o
  link de redefinição é exibido na tela (`PASSWORD_RESET_SHOW_DEV_LINK`); em
  produção, nunca. Usuário inativo não recupera senha e não é reativado.

### Auditoria/logs (Fase 7.3)
- RF-25 — Registrar eventos de **login/logout**.
- RF-26 — Registrar **criação/edição/remoção** de registros.
- RF-27 — Registrar **upload/download** de arquivos.
- RF-28 — Registrar tentativas de **acesso negado**.
- RF-29 — Registrar **exportações** quando o recurso existir.

### PDF/exportações (Fase 7.4)
- RF-30 — Exportar relatórios operacionais (ex.: PDF/CSV).
- RF-31 — Exportações respeitam a **propriedade atual**.
- RF-32 — Exportações respeitam as **permissões por perfil**.
- RF-33 — Exportações **nunca** geram cotação/venda; são relatórios operacionais.

### Mapa avançado (Fase 7.5)
- RF-34 — Editar e **salvar o polígono** da gleba (`poligono_geojson`).
- RF-35 — Melhorar a visualização dos polígonos no mapa.
- RF-36 — Calcular **área aproximada**, se implementado.
- RF-37 — Sem **PostGIS** obrigatório e sem **GPS em tempo real** obrigatório.

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

### RNF planejados — MVP ampliado

- RNF-07 — **Segurança da recuperação de senha:** tokens devem ser
  armazenados/comparados com segurança (sem expor senha ou token em claro) e
  devem **expirar**.
- RNF-08 — **Rastreabilidade:** a auditoria deve registrar ações sensíveis com
  data/hora, usuário e propriedade, **sem** armazenar senha ou dados sensíveis
  desnecessários.
- RNF-09 — **Escopo por propriedade:** painel de usuários, exportações e mapa
  avançado continuam restritos à propriedade atual e às permissões por perfil.
- RNF-10 — **Integridade das exportações:** PDF/exportações são relatórios
  operacionais e **não** podem ser apresentados como cotação ou documento
  comercial.

---

## Documentos relacionados

- [01 — Escopo do Projeto](./01-escopo-do-projeto.md)
- [03 — Regras de Negócio](./03-regras-de-negocio.md)
- [06 — Arquitetura do Sistema](./06-arquitetura-do-sistema.md)
