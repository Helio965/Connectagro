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

## Regras de acesso

- RN-10 — O acesso aos módulos exige **usuário autenticado** (login com e-mail e
  senha; sessão Flask). Sem login, as rotas dos módulos redirecionam para
  `/auth/login`. Rotas públicas: `/auth/login`, `/auth/logout`, `/health` e
  arquivos estáticos.
- RN-10a — **Usuário inativo** (`ativo = 0`) **não** consegue autenticar.
- RN-10b — Senhas são armazenadas como **hash** (`werkzeug.security`); a sessão
  guarda apenas dados mínimos do usuário, **nunca** a senha.
- RN-11 — **Perfis oficiais do MVP:** `admin`, `tecnico`, `trabalhador`
  (`usuario.perfil`). **Permissões finas por módulo** (o que cada perfil pode
  fazer) ficam para **etapa futura** — no MVP, todo usuário autenticado acessa os
  módulos. As **funções** de `equipe_membro` poderão refinar permissões depois.

## Regras operacionais

- RN-12 — Uma **cultura** está associada a uma ou mais **glebas** (relação a ser
  formalizada no DER).
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
  devem retornar **404**.
- RN-19 — Cada usuário só pode listar, baixar e remover arquivos de upload da
  própria propriedade. Tentativas de acessar arquivo de outra propriedade devem
  retornar **404**.
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

---

## Documentos relacionados

- [02 — Requisitos do Sistema](./02-requisitos-do-sistema.md)
- [04 — Modelagem do Banco (DER)](./04-modelagem-banco-der.md)
- [Catálogo de Produtos](./catalogo-produtos/README.md)
