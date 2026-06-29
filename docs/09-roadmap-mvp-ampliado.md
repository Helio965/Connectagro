# 09 — Roadmap do MVP Ampliado

> Este documento guia a evolução do ConnectAgro após a consolidação do **MVP
> base**. Ele define o escopo do **MVP ampliado** (Fase 7), o que fica de fora e o
> que **nunca** entra no produto. A **Fase 7.0** foi somente documental, a
> **Fase 7.1** implementa o painel interno de usuários, a **Fase 7.2** implementa
> a recuperação de senha (token seguro, sem envio real de e-mail), a **Fase 7.3**
> implementa a auditoria/logs administrativos (somente admin, sem dados sensíveis)
> e a **Fase 7.4** implementa as exportações CSV/PDF dos relatórios (operacionais,
> nunca cotação/venda).

## 1. Decisão de produto

O MVP base foi concluído e validado (Fase 6.5). Antes de encerrar o produto em
definitivo, houve uma **decisão de produto** para **ampliar o MVP**: incorporar
ao escopo do MVP cinco frentes antes tratadas como pós-MVP — painel de usuários,
recuperação de senha, auditoria/logs, PDF/exportações e mapa avançado.

Esta decisão **não desfaz** o MVP base: ele continua válido, testado e
consolidado. O MVP ampliado é uma **continuação** organizada em fases 7.x.

## 2. MVP base consolidado

O MVP base entrega, já testado:

- autenticação real (login/logout, sessão, hash de senha);
- permissões finas por perfil (`admin`, `tecnico`, `trabalhador`) com 403 no backend;
- CSRF/Flask-WTF nos formulários POST;
- dashboard operacional somente leitura;
- CRUDs de glebas, culturas (com associação cultura↔gleba), equipe, financeiro e colheita;
- catálogo de defensivos/fertilizantes em consulta somente leitura;
- aplicações de insumo (histórico operacional);
- upload seguro escopado por propriedade;
- mapa real simplificado (somente leitura);
- IA simulada operacional;
- relatórios operacionais HTML;
- documentação e checklist final do MVP base.

Validação registrada na Fase 6.5:

```bash
python -m pytest          # 302 passed
flask --app src/run.py db upgrade
flask --app src/run.py seed-users
```

## 3. Escopo incluído no MVP ampliado

| Fase | Item | Resumo |
| ---- | ---- | ------ |
| 7.1 | Painel de usuários | **Concluído:** admin lista, cria, edita perfil/status e inativa usuários da propriedade. **Sem cadastro público.** |
| 7.2 | Recuperação de senha | **Concluído:** token seguro/expirável, armazenado só como hash, uso único; mensagem genérica; sem envio real de e-mail (link dev em local/teste). |
| 7.3 | Auditoria/logs | **Concluído:** tabela `log_auditoria`, serviço central, eventos sensíveis (auth, reset, CRUDs, usuários, upload, permissão negada); tela `/auditoria/` só admin, escopo por propriedade, sem dados sensíveis. |
| 7.4 | PDF/exportações | **Concluído:** CSV (lib padrão) + PDF (ReportLab) dos 5 relatórios, em memória; escopo por propriedade/permissão; filtros preservados; auditoria `exportacao.gerada`; nunca cotação/venda. |
| 7.5 | Mapa avançado | Edição/salvamento de polígono da gleba e melhor visualização; sem PostGIS obrigatório. |

## 4. Fora do MVP ampliado

Reconhecidos, mas **não** incluídos no MVP ampliado (avaliados depois):

- IA real/LLM (a IA do produto permanece **simulada**);
- validação regulatória real do catálogo (AGROFIT/MAPA/SIPEAGRO);
- preço/imagem com fontes reais e atualização periódica;
- OCR/leitura automática de uploads;
- deploy/produção completo.

## 5. Fora do produto

Proibidos como **regra permanente** do produto, salvo mudança radical de produto
explicitamente aprovada:

- venda;
- carrinho;
- checkout;
- cotação.

O ConnectAgro permanece uma plataforma de **gestão agrícola e consulta técnica**,
**não** um marketplace e **não** um sistema de comércio.

## 6. Fases planejadas

- **Fase 7.0 — Redefinição oficial do MVP ampliado** ✅ (concluída): apenas
  documentação/roadmap/regras/checklist; sem código funcional novo.
- **Fase 7.1 — Painel de usuários** ✅
- **Fase 7.2 — Recuperação de senha** ✅
- **Fase 7.3 — Auditoria/logs** ✅
- **Fase 7.4 — PDF/exportações** ✅
- **Fase 7.5 — Mapa avançado** ⏳
- **Fase 7.6 — Revisão final do MVP ampliado** ⏳

## 7. Critérios de aceite por fase

Critérios gerais (valem para todas as fases 7.x):

- toda a suíte existente continua passando e a fase **adiciona seus próprios testes**;
- autenticação, permissões por perfil, CSRF e escopo por propriedade preservados;
- nenhum recurso fora do escopo é introduzido sem atualizar a documentação.

Por fase:

- **7.1 Painel de usuários:** admin lista/cria/edita/inativa usuários da
  propriedade; não há cadastro público; ações exigem perfil `admin` e respeitam o
  escopo por propriedade. Implementado com `usuario_propriedade`,
  `usuarios_bp`, permissões `usuarios.*` e testes próprios.
- **7.2 Recuperação de senha:** token seguro e expirável; senha/token nunca
  expostos; redefinição válida apenas com token válido e não expirado.
- **7.3 Auditoria/logs:** eventos sensíveis registrados com data/hora, usuário e
  propriedade; sem senha nem dados sensíveis desnecessários.
- **7.4 PDF/exportações:** exportações escopadas por propriedade e permissão;
  nunca apresentadas como cotação/venda.
- **7.5 Mapa avançado:** edição/validação de `poligono_geojson`; sem PostGIS
  obrigatório nem GPS em tempo real obrigatório.
- **7.6 Revisão final:** suíte completa validada; documentação e checklist do MVP
  ampliado atualizados.

## 8. Riscos técnicos

- **Vínculo usuário↔propriedade:** a Fase 7.1 criou `usuario_propriedade` e
  adaptou `utils/contexto.py` para priorizar vínculos ativos, mantendo backfill
  de bases legadas por `propriedade.usuario_id`.
- **Tokens e segurança:** recuperação de senha exige geração/armazenamento
  seguros de token e expiração; erro aqui é risco de segurança.
- **Volume de auditoria:** logs podem crescer; definir o que registrar sem
  guardar dados sensíveis e sem comprometer desempenho.
- **Dependência de PDF:** PDF pode exigir nova dependência **controlada**; CSV
  pode usar biblioteca padrão. Avaliar custo/manutenção na fase 7.4.
- **Edição de GeoJSON:** o mapa avançado precisa validar a entrada para não
  gravar GeoJSON inválido em `gleba.poligono_geojson`.

## 9. Ordem recomendada

1. Fase 7.1 — Painel de usuários (concluída).
2. Fase 7.2 — Recuperação de senha (concluída).
3. Fase 7.3 — Auditoria/logs (concluída).
4. Fase 7.4 — PDF/exportações (concluída).
5. Fase 7.5 — Mapa avançado.
6. Fase 7.6 — Revisão final do MVP ampliado.

## 10. Próximo passo

**Fase 7.5 — Mapa avançado.**

---

## Documentos relacionados

- [01 — Escopo do Projeto](./01-escopo-do-projeto.md)
- [02 — Requisitos do Sistema](./02-requisitos-do-sistema.md)
- [03 — Regras de Negócio](./03-regras-de-negocio.md)
- [06.1 — Arquitetura Técnica do MVP](./06-1-arquitetura-tecnica-mvp.md)
- [07 — Roadmap do MVP](./07-roadmap-mvp.md)
- [08 — Checklist Final do MVP](./08-checklist-final-mvp.md)
