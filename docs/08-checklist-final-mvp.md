# 08 — Checklist Final do MVP

## 1. Status geral

O MVP do ConnectAgro está consolidado para apresentação e continuidade. A base
inclui autenticação, permissões por perfil, CSRF, CRUDs operacionais, catálogo em
consulta, upload seguro, dashboard, mapa simplificado, IA simulada e relatórios
HTML somente leitura.

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

- [x] SQLAlchemy com 15 tabelas de domínio.
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

## 12. Limitações conhecidas do MVP

- Sem venda.
- Sem carrinho.
- Sem checkout.
- Sem cotação oficial.
- Sem recomendação agronômica.
- Sem validação técnica de dose.
- Sem validação oficial automática AGROFIT/MAPA.
- Preço e imagem de produto pendentes.
- Sem OCR.
- Sem leitura automática de upload.
- Sem PDF/exportação.
- Sem painel de usuários.
- Sem recuperação de senha.
- Sem auditoria avançada.
- Sem deploy/produção.
- Sem LLM/API externa.
- Sem mapa avançado.

## 13. Pendências pós-MVP

- PDF/exportações.
- Melhorias visuais avançadas.
- Painel de usuários.
- Recuperação de senha.
- Auditoria/logs administrativos.
- Validação regulatória real do catálogo.
- Preço/imagem com fontes reais e atualização periódica.
- Mapa avançado.
- IA real/LLM, se futuramente aprovado.
- Deploy/produção.

## 14. Critério de aceite final

O MVP é considerado aceito quando a suíte `python -m pytest` passa, os comandos
de banco `db upgrade` e `seed-users` executam sem erro, os formulários POST
mantêm CSRF, as permissões continuam retornando 403 para ações proibidas, o
escopo por propriedade permanece preservado e nenhum recurso pós-MVP foi
incluído indevidamente.
