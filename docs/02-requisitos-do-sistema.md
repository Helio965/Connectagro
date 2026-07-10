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
> 7.1 (painel de usuários), 7.2 (recuperação de senha), 7.3 (auditoria/logs),
> 7.4 (PDF/exportações), 7.5 (mapa avançado) e 7.6 (revisão final) já estão
> implementadas. Nenhum item inclui venda, carrinho, checkout ou cotação.

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
- RF-24 — Enviar o link por Flask-Mail/SMTP quando `MAIL_ATIVO` e as credenciais
  estiverem configurados. Sem envio ativo, exibi-lo somente em local/dev/teste
  quando `PASSWORD_RESET_SHOW_DEV_LINK=true`; em produção, nunca. Usuário
  inativo não recupera senha e não é reativado.

### Auditoria/logs (Fase 7.3) ✅
- RF-25 — Registrar eventos de **login/logout** (`auth.login.sucesso`,
  `auth.login.falha`, `auth.logout`) e de **recuperação de senha**
  (`auth.password_reset.solicitado/redefinido/token_invalido`).
- RF-26 — Registrar **criação/edição/remoção** nos CRUDs principais (glebas,
  culturas, equipe, financeiro, colheita, aplicações) e no painel de usuários
  (`usuarios.create/edit/deactivate`).
- RF-27 — Registrar **upload/download/remoção** de arquivos
  (`upload.create/download/delete`).
- RF-28 — Registrar tentativas de **acesso negado** (`permissao.negada`,
  resultado `negado`).
- RF-29 — Registrar acesso à central de relatórios (`relatorios.view`) e
  exportações (`exportacao.gerada`/`exportacao.falha`) quando CSV/PDF forem
  solicitados.
- RF-29a — Os logs são consultados em `/auditoria/` **apenas pelo `admin`**
  (`auditoria.view`), escopados pela propriedade atual, com filtros simples
  (ação, resultado, entidade, usuário). Logs **não** armazenam senha, token
  puro, hash, CSRF ou conteúdo de formulário/arquivo.

### PDF/exportações (Fase 7.4) ✅
- RF-30 — Exportar os relatórios operacionais (geral, financeiro, agrícola,
  aplicações, uploads) em **CSV** (biblioteca padrão) e **PDF** (ReportLab),
  gerados **em memória**.
- RF-31 — Exportações respeitam a **propriedade atual** (mesmas consultas dos
  relatórios HTML, via `relatorios_service`).
- RF-32 — Exportações respeitam as **permissões por perfil** (`relatorios.view`)
  e os **mesmos filtros** dos relatórios (período/tipo no financeiro, período/
  classe nas aplicações); filtro inválido retorna **400** sem gerar arquivo.
- RF-33 — Exportações **nunca** geram cotação/venda; são relatórios operacionais
  com aviso explícito e registram auditoria `exportacao.gerada`.

### Mapa avançado (Fase 7.5) ✅
- RF-34 — **Editar, salvar e limpar** o polígono da gleba (`poligono_geojson`)
  pelo mapa, com Leaflet + Leaflet.draw (CDN). Edição exige a permissão
  `mapa.edit` (admin e técnico); **trabalhador apenas visualiza**.
- RF-35 — Exibir e editar os polígonos no mapa (um polígono por gleba), com
  validação de GeoJSON no backend e auditoria das alterações.
- RF-36 — Cálculo de **área aproximada** **não** foi implementado nesta fase
  (evitar dependência/risco); o foco é desenhar/salvar/limpar o polígono.
- RF-37 — Sem **PostGIS**, sem **GPS em tempo real**, sem shapefile/KML e sem
  medição/georreferenciamento oficial.

---

## Requisitos Não Funcionais (RNF)

- RNF-01 — **Tecnologia:** backend em Python/Flask, SQLite como banco local
  padrão ou PostgreSQL/Supabase por configuração, frontend em HTML/CSS/JavaScript.
- RNF-02 — **Segurança:** senhas armazenadas de forma segura (hash); acesso
  protegido por autenticação.
- RNF-03 — **Usabilidade:** interface simples e adequada ao público produtor.
- RNF-04 — **Integridade de dados:** o catálogo não deve apresentar dados
  inventados nem validações regulatórias não comprovadas.
- RNF-05 — **Manutenibilidade:** código organizado por módulos, com documentação
  acompanhando a evolução.
- RNF-06 — **Portabilidade:** execução local simples para o MVP (SQLite, sem
  dependência de serviços externos obrigatórios).

### RNF — MVP ampliado concluído

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
- RNF-11 — **Limites pós-MVP:** IA real/LLM, OCR, deploy completo, validação
  regulatória real, preço atualizado e imagens oficiais/do fabricante
  permanecem fora do MVP ampliado.

---

## Documentos relacionados

- [01 — Escopo do Projeto](./01-escopo-do-projeto.md)
- [03 — Regras de Negócio](./03-regras-de-negocio.md)
- [06 — Arquitetura do Sistema](./06-arquitetura-do-sistema.md)
