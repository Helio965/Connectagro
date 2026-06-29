# 11 — Revisão Técnica Final Pós-MVP

> **Pós-MVP 0.1.** Revisão de **organização e manutenção** do repositório, sem
> mudança de escopo funcional. Não houve funcionalidade nova, schema novo,
> dependência nova nem cópia de código externo.

## 1. Objetivo da revisão

Fazer uma última passada técnica no projeto como um todo — com foco em código —
para deixar o repositório mais organizado, conciso e fácil de manter, **sem**
alterar comportamento, escopo ou regras de negócio. O objetivo é deixar a base
pronta para download, execução local e uma futura fase visual/frontend.

## 2. Estado do projeto antes da revisão

- MVP base e **MVP ampliado concluídos** (Fases 7.1 a 7.6, PR #40).
- Validação herdada da `main`:
  - `python -m pytest` → **475 passed**;
  - `flask --app src/run.py db upgrade` → OK (head `e5f0a1b2c3d4`);
  - `flask --app src/run.py seed-users` → OK.
- Schema com **18 tabelas**.

## 3. Escopo da revisão

**Permitido:** remover imports/comentários/código mortos, corrigir docstrings e
textos desatualizados, eliminar duplicação simples e segura, remover template
morto, atualizar documentação desalinhada e criar este documento.

**Proibido:** funcionalidade nova, rota/módulo/model/migration/tabela novos,
dependência nova, mudança de schema, permissões, CSRF, autenticação, recuperação
de senha, painel de usuários, auditoria, relatórios/exportações, mapa, catálogo,
IA simulada ou upload — e qualquer cópia de código externo (incl. NEXO).

## 4. O que foi analisado

- `README.md`, `requirements.txt`, `.env.example`, `.gitignore`.
- `src/run.py`, `src/app/__init__.py`, `config.py`, `extensions.py`, `commands.py`.
- `src/app/models/`, `blueprints/`, `services/`, `utils/`, `templates/`,
  `static/css/main.css`, `static/js/`.
- `docs/`, `tests/`, `migrations/versions/`.
- Análise estática de imports não usados (pyflakes, ferramenta local de análise —
  **não** adicionada às dependências do projeto).

## 5. Melhorias aplicadas

- **Imports não usados removidos** em `blueprints/colheita/routes.py`
  (`Gleba` e `iso_now` não eram utilizados). Os imports de efeito colateral com
  `# noqa: F401` (registro de modelos e de rotas dos blueprints) foram mantidos
  por serem intencionais.
- **Template morto removido:** `templates/placeholders/modulo.html` (e a pasta
  `templates/placeholders/`), remanescente da fase de placeholders e sem
  referência em nenhuma rota/template.
- **Debug removido:** `static/js/main.js` deixou de emitir `console.log` de
  carga; o arquivo ficou como base limpa e comentada.
- **Docstrings/comentários atualizados:**
  - `services/__init__.py` e `utils/__init__.py` não dizem mais "vazio nesta
    etapa" — descrevem os serviços/utilitários existentes.
  - `models/gleba.py`: o comentário do campo `poligono_geojson` deixou de citar
    "mapa real futuro" e passa a referir a edição pelo mapa avançado (Fase 7.5).
- **`tests/README.md`** e este documento atualizados/criados; link adicionado no
  README.

## 6. O que não foi alterado

- Nenhuma rota, model, migration, tabela, permissão, regra de negócio ou
  dependência.
- Comportamento de autenticação, recuperação de senha, painel de usuários,
  auditoria, relatórios/exportações, mapa, catálogo, IA simulada e upload.
- A classe CSS `.placeholder-tag` foi **mantida**: apesar do nome de origem, ela
  é hoje usada como estilo de "nota/aviso" em vários templates reais; renomeá-la
  exigiria tocar em muitos arquivos sem ganho funcional (ver recomendações).

## 7. Estrutura final do projeto

```text
src/app/
├── __init__.py        # Application Factory, context processors, handlers de erro
├── config.py          # configuração por ambiente
├── extensions.py      # db, migrate, csrf
├── commands.py        # CLI: init-db, validate/import-catalog-seed, seed-users
├── blueprints/        # auth, dashboard, usuarios, auditoria, glebas, culturas,
│                      # equipe, financeiro, colheita, aplicacoes, upload,
│                      # defensivos, fertilizantes, mapa, ia, relatorios
├── models/            # 18 tabelas de domínio
├── services/          # catalogo_seed, dashboard, ia_simulada, relatorios,
│                      # usuarios, password_reset, auditoria, exportacoes, mapa
├── utils/             # auth, permissions, contexto, catalogo, formatters
├── templates/         # base + um diretório por módulo + errors/
└── static/            # css/, js/
```

## 8. Comandos de validação

```bash
python -m pytest
flask --app src/run.py db upgrade
flask --app src/run.py seed-users
git diff --check
```

## 9. Resultado dos testes

- Antes da revisão: **475 passed**.
- Depois da revisão: **479 passed** (475 testes anteriores + 4 testes documentais
  da revisão Pós-MVP 0.1; comportamento funcional preservado).

## 10. Riscos evitados

- Não se renomeou a classe CSS `.placeholder-tag` em massa (risco de inconsistência
  visual sem ganho funcional).
- Não se renomearam arquivos de teste (risco de afetar a coleta do pytest).
- Não se removeram imports de efeito colateral (`# noqa: F401`), necessários para
  registrar modelos e rotas.
- Não se tocou em schema, migrations ou regras de negócio.

## 11. Recomendações para pós-MVP

- (Opcional) Renomear `.placeholder-tag` para algo como `.nota-aviso` em CSS e
  templates, de forma mecânica e coberta por revisão visual.
- (Opcional) Adicionar um linter/formatador (ex.: `ruff`/`black`) como
  dependência **de desenvolvimento**, fora de `requirements.txt` de execução.
- Manter a IA **simulada** como IA oficial até decisão de produto sobre IA real.

## 12. Observações para futura fase visual/frontend

- A fase visual deve preservar autenticação, permissões por perfil, CSRF e escopo
  por propriedade.
- Os templates já estão organizados por módulo e o `static/` separa `css/` e
  `js/`, o que facilita um redesenho incremental.
- **Limites permanentes do produto:** venda, carrinho, checkout e cotação **não**
  entram. **Fora do MVP ampliado** (avaliados depois): IA real/LLM, validação
  regulatória real do catálogo, preço/imagem com fontes reais, OCR/leitura
  automática de uploads e deploy/produção completo.

---

## Documentos relacionados

- [00 — Visão Geral](./00-visao-geral.md)
- [06.1 — Arquitetura Técnica do MVP](./06-1-arquitetura-tecnica-mvp.md)
- [07 — Roadmap do MVP](./07-roadmap-mvp.md)
- [10 — Checklist Final do MVP Ampliado](./10-checklist-final-mvp-ampliado.md)
