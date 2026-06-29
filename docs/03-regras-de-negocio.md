# 03 — Regras de Negócio

> Documento-base. As regras abaixo consolidam as restrições já definidas para o
> projeto e serão expandidas conforme o detalhamento dos módulos.

## Como ler este documento

- **RN** = Regra de Negócio.

---

## Regras gerais do produto

- RN-01 — O ConnectAgro é uma plataforma de **gestão e consulta**; **não vende**
  produtos e **não** possui carrinho/checkout.
- RN-02 — Os valores de produtos têm finalidade de **consulta rápida** e não
  constituem cotação ou oferta de venda.

## Regras do catálogo de produtos

- RN-03 — O catálogo cobre defensivos, fertilizantes, corretivos, inoculantes e
  biofertilizantes, servindo como **base técnica inicial**.
- RN-04 — O catálogo **não** é verdade regulatória definitiva.
- RN-05 — No MVP, **preço** deve ser tratado como **pendência / dado não
  consolidado** quando não houver fonte confiável. Nunca inventar valores.
- RN-06 — No MVP, **imagem** do produto também é tratada como **pendência**
  quando indisponível.
- RN-07 — A **validação diária do menor valor atualizado** é responsabilidade do
  **sistema final**, não do MVP.
- RN-08 — **Não** afirmar validação **AGROFIT/MAPA** nem dizer que um produto
  está "validado oficialmente" sem comprovação por **fonte real**.
- RN-09 — Dados de produto sem origem confiável devem ser sinalizados como
  **não consolidados**, e não exibidos como definitivos.
- RN-09a — Cada produto possui um **`status_regulatorio`** (enum oficial do MVP):
  `nao_validado_agrofit`, `atencao_regulatoria`,
  `sujeito_a_sipeagro_nao_validado`, `tipo_tecnico_generico`,
  `bloqueado_historico`. **Defensivos** começam como `nao_validado_agrofit` (ou
  `atencao_regulatoria`) — **nunca** "validado oficialmente" sem fonte real.
- RN-09b — **Fertilizantes, corretivos, inoculantes e biofertilizantes** usam
  `sujeito_a_sipeagro_nao_validado` ou `tipo_tecnico_generico` (este para
  genéricos como Ureia, MAP, DAP, Calcário Dolomítico, Esterco Bovino, Composto
  Orgânico), separáveis de produtos comerciais específicos no futuro.
- RN-09c — **Paraquate**, se citado, é tratado como `bloqueado_historico` (uso
  proibido no Brasil), não recomendado. **Oxamil** não entra como produto
  recomendado no seed inicial.
- RN-09d — Preço (`produto_preco`) e imagem (`produto_imagem`) possuem
  **`status_validacao`**; no MVP ficam `pendente`/`nao_consolidado`.
- RN-09e — No **sistema final**, a validação diária do menor preço será apenas
  referência informativa e cada preço deverá registrar **fonte, data, unidade e
  status de validação**.

## Regras de acesso e permissões

- RN-10 — O acesso aos módulos exige **usuário autenticado** (login com e-mail e
  senha; sessão Flask). Sem login, as rotas dos módulos redirecionam para
  `/auth/login`. Rotas públicas: `/auth/login`, `/auth/logout`, `/health` e
  arquivos estáticos.
- RN-10a — **Usuário inativo** (`ativo = 0`) **não** consegue autenticar.
- RN-10b — Senhas são armazenadas como **hash** (`werkzeug.security`); a sessão
  guarda apenas dados mínimos do usuário, **nunca** a senha.
- RN-11 — **Perfis oficiais do MVP:** `admin`, `tecnico`, `trabalhador`
  (`usuario.perfil`). A matriz de permissões fica em código no MVP, em
  `src/app/utils/permissions.py`, sem tabela de roles/permissões e sem
  dependência externa de RBAC.
- RN-11a — `admin` pode acessar todos os módulos e criar, editar e remover nos
  CRUDs da **sua propriedade atual**. Admin não acessa dados globais de outras
  propriedades.
- RN-11b — `tecnico` pode acessar dashboard, mapa, catálogo, relatórios, IA,
  equipe e financeiro em leitura; pode criar/editar glebas, culturas, colheitas e
  aplicações; pode enviar e baixar uploads. Não pode remover registros críticos,
  remover uploads ou criar/editar/remover equipe e financeiro.
- RN-11c — `trabalhador` tem acesso operacional restrito: pode acessar dashboard,
  mapa, catálogo, relatórios e IA; visualiza glebas, culturas, colheitas e
  aplicações; cria colheitas, aplicações e uploads; baixa uploads. Não acessa
  equipe/financeiro e não cria/edita/remove glebas/culturas nem edita/remove
  colheitas, aplicações ou uploads.
- RN-11d — Dashboard, Mapa, IA simulada, Relatórios e Catálogo são acessíveis aos
  perfis autenticados conforme a matriz de permissões.
- RN-11e — Permissões por perfil **não substituem** o escopo por propriedade. As
  consultas e ações continuam filtradas pela propriedade atual.
- RN-11f — O backend deve validar permissões com `require_permission(...)` e
  retornar **403** em ações não autorizadas. Esconder botão no template não é
  suficiente.
- RN-11g — `can(...)` nos templates é apoio visual para esconder menus, atalhos e
  botões não permitidos, mas não é a fonte de segurança da autorização.
- RN-11h — As funções de `equipe_membro` poderão refinar permissões futuramente,
  mas não controlam autorização nesta fase.
- RN-11i — Todo formulário **POST** do MVP deve enviar token CSRF gerado por
  Flask-WTF/CSRFProtect.
- RN-11j — Requisições POST com CSRF ausente ou inválido devem retornar **400**
  com mensagem amigável, sem expor detalhes técnicos do token.
- RN-11k — CSRF não substitui autenticação, permissões por perfil nem escopo por
  propriedade. Com token válido, ações sem permissão continuam retornando **403**.
- RN-11l — Formulários multipart do Upload também exigem token CSRF.
- RN-11m — O painel `/usuarios/` é interno e exige permissões `usuarios.view`,
  `usuarios.create`, `usuarios.edit` e `usuarios.deactivate`, concedidas apenas
  ao perfil `admin`.
- RN-11n — O painel de usuários trabalha somente com usuários vinculados à
  propriedade atual por `usuario_propriedade`; usuários de outra propriedade não
  podem ser editados/inativados e retornam **404** quando o perfil tem permissão.
- RN-11o — Criar usuário pelo painel exige e-mail único, perfil oficial e senha
  temporária com hash. Não há cadastro público nem redefinição de senha nesta
  fase.
- RN-11p — Inativar usuário desativa o login e o vínculo com a propriedade, sem
  remoção física do registro. A propriedade deve manter pelo menos um `admin`
  ativo.

## Regras de recuperação de senha (Fase 7.2)

- RN-11q — A recuperação de senha usa **token seguro** (`secrets.token_urlsafe`)
  e **expirável** (validade configurável por `PASSWORD_RESET_TOKEN_MINUTES`).
- RN-11r — O **token puro nunca é armazenado**: o banco guarda apenas o **hash**
  (SHA-256) em `senha_reset_token`. Nenhuma senha é gravada nessa tabela.
- RN-11s — A senha **nunca** é armazenada em texto; a nova senha é gravada como
  **hash** (`werkzeug.security`), com mínimo de 6 caracteres e confirmação.
- RN-11t — A solicitação de redefinição responde com **mensagem genérica** e não
  revela se o e-mail existe (evita enumeração de e-mails).
- RN-11u — **Usuário inativo não recupera senha**: não recebe token válido, não
  redefine senha por token e **não é reativado** pela redefinição.
- RN-11v — O token é de **uso único** e, ao solicitar novo reset, os tokens
  abertos anteriores do usuário são invalidados. Token usado/expirado/inválido é
  recusado, e a redefinição **não** autentica o usuário automaticamente.
- RN-11w — Exibir o **link/token de redefinição em tela** só é permitido em
  ambiente **local/dev/teste** (`PASSWORD_RESET_SHOW_DEV_LINK`). Em produção,
  nunca. **Não há envio real de e-mail** nesta fase; SMTP/serviço de e-mail e
  deploy ficam fora do escopo.

## Regras de auditoria/logs (Fase 7.3)

- RN-11x — **Ações sensíveis devem ser auditadas**: autenticação (login/logout),
  recuperação de senha, criação/edição/remoção nos CRUDs principais, painel de
  usuários, upload/download/remoção e permissão negada.
- RN-11y — Os **logs são acessíveis apenas ao `admin`** (`auditoria.view`), na
  tela `/auditoria/`; técnico e trabalhador **não** acessam.
- RN-11z — Os logs são **escopados pela propriedade atual**; um admin não vê
  logs de outra propriedade.
- RN-11aa — Os logs **não** guardam senha, nova senha, `senha_hash`, token puro,
  `token_hash`, `csrf_token`, conteúdo de arquivo, corpo completo de formulário
  nem dados sensíveis desnecessários. E-mails, quando úteis, são **mascarados**.
- RN-11ab — A auditoria **nunca** quebra o fluxo principal: falha ao gravar log
  não impede a ação do usuário.
- RN-11ac — A auditoria **não** substitui backup, segurança de infraestrutura
  nem monitoramento de produção (SIEM); é um registro interno simples.

## Regras de PDF/exportações (Fase 7.4)

- RN-11ad — Os relatórios operacionais (geral, financeiro, agrícola, aplicações,
  uploads) podem ser **exportados em CSV e PDF**, gerados em memória.
- RN-11ae — As exportações **respeitam a propriedade atual** e usam as mesmas
  consultas somente leitura dos relatórios HTML; não criam, alteram ou removem
  dados.
- RN-11af — As exportações **respeitam as permissões** (`relatorios.view`) e os
  mesmos **filtros** dos relatórios; filtro inválido retorna **400** e **não**
  gera arquivo nem registra exportação como sucesso.
- RN-11ag — Toda exportação bem-sucedida registra auditoria `exportacao.gerada`
  (entidade `relatorio`), sem armazenar o conteúdo do relatório.
- RN-11ah — As exportações são **relatórios operacionais**: **não** são cotação,
  venda, checkout nem documento comercial, e **não** validam dose ou recomendação
  agronômica. Cada PDF/CSV traz aviso explícito nesse sentido.

## Regras operacionais

- RN-12 — Uma **cultura** está associada a uma ou mais **glebas**.
- RN-13 — Lançamentos **financeiros** classificam-se em **receita** ou
  **despesa**.
- RN-14 — Registros de **colheita** referenciam a cultura/gleba correspondente.
- RN-15 — A **aplicação de insumo** é um **registro histórico operacional** do
  que foi aplicado em uma associação cultura↔gleba. Ela **não** representa
  recomendação agronômica.
- RN-16 — Produtos com `status_sistema == "bloqueado_historico"` ou
  `status_regulatorio == "bloqueado_historico"` **não** podem ser registrados
  como aplicação válida.
- RN-17 — A dose informada em uma aplicação é **histórica/informativa**; o
  ConnectAgro apenas registra o valor digitado e **não** valida dose correta,
  segura, ideal ou recomendada.
- RN-18 — Cada usuário só acessa aplicações vinculadas à sua própria
  propriedade. Tentativas de editar ou remover aplicação de outra propriedade
  devem retornar **404** quando a ação é permitida ao perfil.
- RN-19 — Cada usuário só pode listar, baixar e remover arquivos de upload da
  própria propriedade. Tentativas de acessar arquivo de outra propriedade devem
  retornar **404** quando a ação é permitida ao perfil.
- RN-20 — O Upload do MVP aceita apenas extensões de documentos/imagens simples:
  `pdf`, `png`, `jpg`, `jpeg`, `csv`, `xlsx`, `txt` e `docx`.
- RN-21 — Executáveis, scripts, compactados e arquivos web executáveis devem ser
  bloqueados no Upload. Exemplos proibidos: `exe`, `bat`, `cmd`, `sh`, `ps1`,
  `js`, `html`, `php`, `py`, `zip`, `rar`, `7z`, `dll`, `msi` e `jar`.
- RN-22 — Arquivos enviados são armazenados localmente no MVP, fora da pasta
  `static` pública, com nome seguro, sem versionar o conteúdo no Git e com acesso
  apenas pelas rotas protegidas do módulo Upload.
- RN-23 — O Upload não faz OCR, IA, leitura automática, classificação,
  validação documental avançada ou extração automática de conteúdo nesta etapa.
- RN-24 — A IA do MVP é **simulada**, baseada em regras simples e dados locais já
  cadastrados no sistema.
- RN-25 — A IA simulada não usa LLM, API externa, internet, machine learning,
  OCR, leitura automática de uploads ou consulta a fontes oficiais em tempo real.
- RN-26 — A IA simulada não recomenda produtos, não valida dose e não faz
  diagnóstico agronômico.
- RN-27 — As respostas da IA são apoio operacional e devem ser escopadas pela
  propriedade atual.
- RN-28 — O histórico da IA deve ser visível apenas ao usuário e à propriedade
  correspondentes.
- RN-29 — A IA simulada não substitui orientação técnica profissional ou
  profissional habilitado.
- RN-30 — Os **relatórios são somente leitura**: não criam, alteram ou removem
  dados.
- RN-31 — Os relatórios são **escopados pela propriedade atual**; nenhuma rota de
  relatório aceita `propriedade_id` por parâmetro.
- RN-32 — O relatório de **aplicações** não recomenda produtos e não valida dose;
  apresenta apenas o histórico operacional registrado.
- RN-33 — O relatório de **uploads** não lê o conteúdo dos arquivos (sem OCR/IA/
  extração); apenas lista metadados e oferece download por rota protegida.
- RN-34 — Os relatórios **financeiros** são informativos e **não substituem
  contabilidade formal**.

## Regras de fechamento do MVP

- RN-35 — A revisão final consolida o **MVP base** sem transformar limitações
  conhecidas em funcionalidades. No fechamento do MVP base ficaram fora: venda,
  carrinho, checkout, cotação oficial, recomendação agronômica, validação técnica
  de dose, validação oficial automática AGROFIT/MAPA, OCR, leitura automática de
  uploads, PDF/exportação, painel de usuários, recuperação de senha, auditoria
  avançada, deploy/produção, LLM/API externa e mapa avançado. **Parte desses
  itens foi posteriormente movida para o MVP ampliado** (ver “Regras de escopo do
  MVP ampliado”, RN-37 a RN-45).
- RN-36 — Qualquer evolução pós-MVP base deve preservar autenticação, permissões
  por perfil, CSRF, escopo por propriedade e os avisos de limites técnicos já
  documentados.

## Regras de escopo do MVP ampliado

- RN-37 — O **MVP base** continua válido e testado; a abertura do **MVP ampliado**
  (Fase 7) é uma **nova decisão de escopo** e **não** desfaz o MVP base.
- RN-38 — O **MVP ampliado** inclui **painel de usuários**, **recuperação de
  senha**, **auditoria/logs**, **PDF/exportações** e **mapa avançado**.
- RN-39 — Ficam **fora do MVP ampliado** (avaliados depois): **IA real/LLM**,
  **validação regulatória real** do catálogo, **preço/imagem real** com
  atualização periódica, **OCR/leitura automática** de uploads e
  **deploy/produção completo**. A IA do produto continua **simulada**.
- RN-40 — **Venda, carrinho, checkout e cotação** são **proibidos** como regra
  permanente do produto, salvo mudança radical de produto explicitamente
  aprovada.
- RN-41 — **Exportações não podem ser usadas como cotação oficial**: PDF/
  exportações são relatórios operacionais, **não** documentos comerciais.
- RN-42 — **Painel de usuários não é cadastro público**: a criação de usuários é
  uma ação administrativa interna, escopada à propriedade.
- RN-42a — O vínculo `usuario_propriedade` é a fonte do painel de usuários no
  MVP ampliado. `propriedade.usuario_id` permanece para compatibilidade e pode
  gerar associação ativa automaticamente quando uma base antiga não possui
  vínculo explícito.
- RN-43 — A **recuperação de senha** deve respeitar a segurança e **não** expor
  senha nem token; o token deve ser seguro e expirável.
- RN-44 — A **auditoria** deve registrar ações sensíveis **sem** armazenar senha
  ou dados sensíveis desnecessários.
- RN-45 — O **mapa avançado** apoia a gestão operacional e **não** substitui
  medição profissional ou georreferenciamento oficial.

---

## Documentos relacionados

- [02 — Requisitos do Sistema](./02-requisitos-do-sistema.md)
- [04 — Modelagem do Banco (DER)](./04-modelagem-banco-der.md)
- [08 — Checklist Final do MVP](./08-checklist-final-mvp.md)
- [Catálogo de Produtos](./catalogo-produtos/README.md)
