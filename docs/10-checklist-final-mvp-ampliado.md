# 10 — Checklist Final do MVP Ampliado

## 1. Status geral

O **MVP ampliado do ConnectAgro está concluído**. O MVP base permanece válido e
foi ampliado pelas Fases 7.1 a 7.6 com painel de usuários, recuperação de senha,
auditoria/logs, PDF/exportações, mapa avançado e revisão final.

## 2. Validação técnica

- [x] `python -m pytest` validado com **475 passed**.
- [x] `flask --app src/run.py db upgrade` validado.
- [x] `flask --app src/run.py seed-users` validado.
- [x] Nenhum erro funcional bloqueante encontrado na revisão final.

## 3. Módulos do MVP base preservados

- [x] Autenticação real.
- [x] Permissões por perfil.
- [x] CSRF/Flask-WTF.
- [x] Dashboard operacional.
- [x] CRUDs de Glebas, Culturas, Equipe, Financeiro, Colheita e Aplicações.
- [x] Catálogo técnico em consulta.
- [x] Upload seguro.
- [x] IA simulada.
- [x] Relatórios operacionais HTML.

## 4. Módulos adicionados no MVP ampliado

- [x] Painel de usuários.
- [x] Recuperação de senha.
- [x] Auditoria/logs administrativos.
- [x] PDF/exportações CSV/PDF.
- [x] Mapa avançado.
- [x] Revisão final do MVP ampliado.

## 5. Segurança

- [x] Senhas armazenadas apenas como hash.
- [x] Sessão Flask sem armazenar senha.
- [x] CSRF em formulários POST.
- [x] Upload fora de `static`.
- [x] Logs sem senha, token, hash, CSRF ou payload sensível.
- [x] Escopo por propriedade preservado.

## 6. Permissões por perfil

- [x] `admin` acessa e gerencia todos os módulos da propriedade.
- [x] `tecnico` tem acesso operacional conforme matriz de permissões.
- [x] `trabalhador` tem acesso limitado e não edita mapa.
- [x] Backend bloqueia ações proibidas com 403.
- [x] `can(...)` continua apenas como apoio visual.

## 7. Painel de usuários

- [x] Admin lista, cria, edita e inativa usuários da propriedade.
- [x] Sem cadastro público.
- [x] Sem remoção física de usuário.
- [x] Mantém vínculo por `usuario_propriedade`.

## 8. Recuperação de senha

- [x] Token seguro, expirável e de uso único.
- [x] Token armazenado somente como hash.
- [x] Mensagem genérica, sem enumeração de e-mail.
- [x] Usuário inativo não recupera senha nem é reativado.
- [x] Sem envio real na entrega original desta fase; Flask-Mail/SMTP foi
  incorporado posteriormente.

## 9. Auditoria/logs

- [x] Logs acessíveis apenas ao admin.
- [x] Logs escopados por propriedade.
- [x] Eventos sensíveis registrados.
- [x] Sem senha, token, hash, CSRF ou conteúdo de formulário/arquivo.
- [x] Falha de auditoria não quebra o fluxo principal.

## 10. PDF/exportações

- [x] CSV e PDF para relatórios geral, financeiro, agrícola, aplicações e uploads.
- [x] Geração em memória.
- [x] Filtros preservados.
- [x] Auditoria de exportação.
- [x] Sem Excel/XLSX, envio automático ou agendamento.
- [x] Exportações não são cotação, venda, checkout ou documento comercial.

## 11. Mapa avançado

- [x] Admin/técnico desenham, salvam e limpam polígonos.
- [x] Trabalhador apenas visualiza.
- [x] GeoJSON validado no backend.
- [x] CSRF nos POSTs do mapa.
- [x] Auditoria sem gravar GeoJSON.
- [x] Sem PostGIS, GPS em tempo real, shapefile/KML ou georreferenciamento oficial.
- [x] O mapa não substitui medição técnica profissional.

## 12. Dados e banco

- [x] Schema final do MVP ampliado com **18 tabelas**.
- [x] Migrations versionadas.
- [x] Sem migration/model/tabela nova na Fase 7.6.
- [x] Banco real e uploads não versionados.

## 13. Catálogo técnico

- [x] Catálogo segue como consulta técnica.
- [x] Sem CRUD de produto.
- [x] Na conclusão desta fase, `produto_preco` e `produto_imagem` estavam
  vazios/pendentes; `produto_imagem` foi populado posteriormente.
- [x] Sem validação oficial automática AGROFIT/MAPA/SIPEAGRO.
- [x] Sem venda, carrinho, checkout ou cotação.

## 14. Upload

- [x] Arquivos armazenados fora de `static`.
- [x] Download protegido por rota autenticada.
- [x] Escopo por propriedade.
- [x] Sem OCR, IA, leitura automática ou extração de conteúdo.

## 15. IA simulada

- [x] IA baseada em regras locais.
- [x] Sem LLM/API externa/internet.
- [x] Sem OCR ou leitura automática de uploads.
- [x] Sem recomendação de produto.
- [x] Sem validação de dose ou diagnóstico agronômico.

## 16. Relatórios

- [x] Relatórios HTML somente leitura.
- [x] Exportações CSV/PDF operacionais.
- [x] Escopo por propriedade.
- [x] Sem alteração de dados.
- [x] Sem cotação, venda ou documento comercial.

## 17. Testes automatizados

- [x] Testes de autenticação.
- [x] Testes de permissões.
- [x] Testes de CSRF.
- [x] Testes dos CRUDs.
- [x] Testes de dashboard, mapa, IA e relatórios.
- [x] Testes de usuários, recuperação de senha, auditoria, exportações e mapa avançado.
- [x] Suíte completa: **475 passed**.

## 18. Comandos de validação

```bash
python -m pytest
flask --app src/run.py db upgrade
flask --app src/run.py seed-users
```

## 19. Limitações conhecidas

- Sem IA real/LLM.
- Sem OCR/leitura automática de uploads.
- Sem deploy/produção completo.
- Sem validação regulatória real.
- Sem preço atualizado nem imagens oficiais/do fabricante.
- Sem Excel/XLSX.
- Sem PostGIS, GPS em tempo real, shapefile/KML ou georreferenciamento oficial.

## 20. Fora do MVP ampliado

- IA real/LLM.
- Validação regulatória real do catálogo.
- Preço com fontes e atualização periódica; imagens oficiais/do fabricante.
- OCR/leitura automática de uploads.
- Deploy/produção completo.

## 21. Fora do produto

- Venda.
- Carrinho.
- Checkout.
- Cotação.

O ConnectAgro permanece uma plataforma de **gestão agrícola e consulta técnica**,
não um marketplace e não um sistema de comércio.

## 22. Critério de aceite final

O MVP ampliado é considerado aceito quando a suíte completa passa, as migrations
sobem, `seed-users` funciona, a documentação não contradiz o estado implementado,
as permissões e o escopo por propriedade continuam preservados e nenhum recurso
fora do MVP ampliado ou fora do produto foi introduzido.
