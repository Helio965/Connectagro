# 08 — Checklist Final do MVP

> **Nota (Fase 7.0):** este checklist registra o **MVP base consolidado**. Após
> nova decisão de produto, foi aberto o **MVP ampliado** na **Fase 7**. Os itens
> antes listados como pós-MVP — painel de usuários, recuperação de senha,
> auditoria/logs, PDF/exportações e mapa avançado — passaram a integrar o MVP
> ampliado (ver a seção “Escopo do MVP ampliado” e o
> [09 — Roadmap do MVP Ampliado](./09-roadmap-mvp-ampliado.md)).
>
> **Nota (Fase 7.6):** este arquivo permanece como checklist histórico do
> **MVP base**. O checklist final do MVP ampliado está em
> [10 — Checklist Final do MVP Ampliado](./10-checklist-final-mvp-ampliado.md).

## 1. Status geral

O MVP **base** do ConnectAgro está consolidado para apresentação e continuidade.
A base inclui autenticação, permissões por perfil, CSRF, CRUDs operacionais,
catálogo em consulta, upload seguro, dashboard, mapa simplificado, IA simulada e
relatórios HTML somente leitura. A partir daqui o projeto segue no **MVP
ampliado** (Fase 7).

## 2. Módulos concluídos

- [x] Autenticação real com login/logout e usuários de teste.
- [x] Dashboard operacional somente leitura.
- [x] Glebas e Culturas, incluindo associação cultura↔gleba.
- [x] Equipe.
- [x] Financeiro.
- [x] Colheita.
- [x] Consulta de Defensivos e Fertilizantes.
- [x] Aplicações de Insumo como histórico operacional.
- [x] Upload de arquivos com metadados.
- [x] Mapa real simplificado.
- [x] IA simulada operacional.
- [x] Relatórios operacionais HTML.

## 3. Segurança

- [x] Senhas armazenadas com hash.
- [x] Sessão Flask sem armazenar senha.
- [x] Rotas sensíveis protegidas por autenticação.
- [x] Permissões por perfil com `require_permission(...)`.
- [x] Templates usando `can(...)` para ocultar ações indisponíveis.
- [x] Handler/template 403 para acesso negado.
- [x] CSRF ativo por padrão no app real.
- [x] `csrf_token()` em formulários POST.
- [x] Upload multipart com token CSRF.
- [x] Handler/template 400 amigável para falha de CSRF.
- [x] Escopo por propriedade preservado nas consultas e ações.

## 4. Dados e banco

- [x] SQLAlchemy com 15 tabelas no MVP base; schema atual do MVP ampliado com
  18 tabelas após `usuario_propriedade`, `senha_reset_token` e `log_auditoria`.
- [x] Flask-Migrate/Alembic configurado.
- [x] Migration inicial versionada.
- [x] SQLite como banco padrão do MVP.
- [x] Banco real não versionado.
- [x] Uploads reais não versionados.
- [x] Seeds técnicos versionados em `data/seeds/`.

## 5. Catálogo

- [x] Catálogo técnico inicial importável por CLI.
- [x] Defensivos e Fertilizantes em consulta somente leitura.
- [x] Busca e filtros por classe.
- [x] Detalhe por slug.
- [x] Produtos bloqueados históricos tratados como não aplicáveis.
- [x] Sem CRUD de produto no MVP.
- [x] Sem venda, carrinho, checkout ou cotação.
- [x] Sem validação oficial automática AGROFIT/MAPA.
- [x] `produto_preco` e `produto_imagem` permanecem vazios/pendentes no MVP.

## 6. Upload

- [x] Upload salvo fora de `static`.
- [x] Nome de arquivo tratado com `secure_filename`.
- [x] Nome físico único com UUID.
- [x] Extensões permitidas controladas.
- [x] Download por rota protegida.
- [x] Remoção respeita permissão por perfil.
- [x] Escopo por propriedade.
- [x] Sem OCR, leitura automática, IA ou extração de conteúdo.

## 7. IA simulada

- [x] Respostas por regras locais.
- [x] Histórico salvo em `ia_interacao`.
- [x] Escopo por usuário e propriedade.
- [x] Sem LLM, API externa, internet, OCR ou machine learning.
- [x] Sem recomendação agronômica.
- [x] Sem validação de dose.
- [x] Sem leitura de uploads.

## 8. Relatórios

- [x] Central `/relatorios/`.
- [x] Relatório geral.
- [x] Relatório financeiro.
- [x] Relatório agrícola.
- [x] Relatório de aplicações.
- [x] Relatório de uploads.
- [x] Filtros operacionais.
- [x] Botão de impressão pelo navegador.
- [x] Somente leitura.
- [x] Sem PDF, CSV, Excel ou exportação automática.

## 9. Mapa

- [x] Página `/mapa/`.
- [x] Endpoint GET `/mapa/dados`.
- [x] Glebas com coordenadas exibidas.
- [x] Glebas sem coordenadas tratadas como estado informativo.
- [x] GeoJSON inválido ignorado sem quebrar resposta.
- [x] Escopo por propriedade.
- [x] Sem desenho de polígonos, edição de coordenadas, medição de área, PostGIS ou GPS em tempo real.

## 10. Testes

- [x] Testes de app factory e rotas.
- [x] Testes de schema/modelos.
- [x] Testes de autenticação.
- [x] Testes de permissões.
- [x] Testes de CSRF.
- [x] Testes dos CRUDs operacionais.
- [x] Testes de catálogo.
- [x] Testes de upload.
- [x] Testes de dashboard.
- [x] Testes de mapa.
- [x] Testes de IA simulada.
- [x] Testes de relatórios.

## 11. Comandos de validação

```bash
python -m pytest
flask --app src/run.py db upgrade
flask --app src/run.py seed-users
```

## 12. Limitações conhecidas do MVP base

Recursos **ainda não implementados** no MVP base. Os itens marcados com
**(MVP ampliado)** foram movidos para a Fase 7 e serão entregues em fases 7.x:

- Painel de usuários fora do MVP base, entregue depois no MVP ampliado
  **(Fase 7.1 concluída)**.
- Sem recuperação de senha. **(MVP ampliado — Fase 7.2)**
- Sem auditoria/logs administrativos. **(MVP ampliado — Fase 7.3)**
- Sem PDF/exportação. **(MVP ampliado — Fase 7.4)**
- Sem mapa avançado. **(MVP ampliado — Fase 7.5)**
- Sem validação oficial automática AGROFIT/MAPA. **(fora do MVP ampliado)**
- Preço e imagem de produto pendentes. **(fora do MVP ampliado)**
- Sem OCR / leitura automática de upload. **(fora do MVP ampliado)**
- Sem LLM/API externa (IA permanece simulada). **(fora do MVP ampliado)**
- Sem deploy/produção completo. **(fora do MVP ampliado)**
- Sem recomendação agronômica. **(limite permanente)**
- Sem validação técnica de dose. **(limite permanente)**
- Sem venda, carrinho, checkout ou cotação. **(fora do produto — permanente)**

## 13. Escopo do MVP ampliado

Itens que **passaram a integrar o MVP** (Fase 7), antes tratados como pós-MVP:

- Painel de usuários (Fase 7.1 concluída).
- Recuperação de senha (Fase 7.2).
- Auditoria/logs administrativos (Fase 7.3).
- PDF/exportações (Fase 7.4).
- Mapa avançado (Fase 7.5).
- Revisão final do MVP ampliado (Fase 7.6 concluída; ver checklist próprio).

**Fora do MVP ampliado** (pós-MVP, avaliados depois):

- IA real/LLM, se futuramente aprovado.
- Validação regulatória real do catálogo.
- Preço/imagem com fontes reais e atualização periódica.
- OCR/leitura automática de uploads.
- Deploy/produção completo.
- Melhorias avançadas que não entrarem na Fase 7.

**Fora do produto** (regra permanente, salvo mudança radical aprovada):

- Venda, carrinho, checkout e cotação.

## 14. Critério de aceite final

O MVP é considerado aceito quando a suíte `python -m pytest` passa, os comandos
de banco `db upgrade` e `seed-users` executam sem erro, os formulários POST
mantêm CSRF, as permissões continuam retornando 403 para ações proibidas, o
escopo por propriedade permanece preservado e nenhum recurso pós-MVP foi
incluído indevidamente.
