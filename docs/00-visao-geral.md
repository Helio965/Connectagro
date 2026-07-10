# 00 — Visão Geral

## O que é o ConnectAgro

O ConnectAgro é uma **plataforma web de gestão agrícola** voltada para
pequenos, médios e grandes produtores. Seu propósito é centralizar, em um único
lugar, o acompanhamento da operação da propriedade — do planejamento das
culturas e glebas até a colheita —, somando a isso o controle financeiro, a
gestão de equipe, a visualização em mapa avançado operacional, relatórios com
exportação e uma camada de apoio por IA simulada.

## Problema que resolve

A gestão agrícola costuma ficar dispersa entre planilhas, cadernos e sistemas
desconexos. O ConnectAgro propõe um ambiente organizado para:

- registrar e acompanhar **culturas** e **glebas**;
- consultar informações técnicas de **defensivos** e **fertilizantes**;
- controlar **receitas e despesas** da propriedade;
- gerenciar a **equipe** e o **fluxo de colheita**;
- visualizar as áreas em um **mapa** e editar polígonos operacionais das glebas;
- centralizar **documentos** via upload;
- gerar **relatórios** de apoio à decisão com exportação CSV/PDF operacional.

## Público-alvo

Produtores rurais de pequeno, médio e grande porte e suas equipes de gestão.

## Estado do produto

- **MVP base consolidado.** A base funcional está concluída e testada:
  autenticação, permissões por perfil, CSRF, dashboard, glebas, culturas,
  equipe, financeiro, colheita, catálogo em consulta, aplicações de insumo,
  upload seguro, mapa real simplificado, IA simulada e relatórios HTML.
- **MVP ampliado concluído.** Por decisão de produto, o MVP foi ampliado antes
  de ser encerrado em definitivo. As fases 7.x entregaram **painel de usuários**,
  **recuperação de senha**, **auditoria/logs administrativos**,
  **PDF/exportações** e **mapa avançado**.
- **Fora do MVP ampliado** (avaliados depois): IA real/LLM, validação
  regulatória real do catálogo, preço com atualização periódica, imagens
  oficiais/do fabricante, OCR/leitura automática de uploads e deploy/produção
  completo. A IA do produto continua **simulada** também no MVP ampliado.
- **Limite permanente do produto:** o ConnectAgro **não** terá venda, carrinho,
  checkout ou cotação. Ele é uma plataforma de **gestão e consulta técnica**, não
  um marketplace, salvo mudança radical de produto explicitamente aprovada.

## Princípios e limites do projeto

Estes princípios orientam todas as decisões de produto e devem ser respeitados
em todas as etapas:

1. **Não é uma loja.** O ConnectAgro não vende produtos. O catálogo serve para
   **consulta rápida** e referência técnica.
2. **Valores são consulta, não cotação oficial.** Os preços exibidos são
   referência. A validação diária do menor valor atualizado fica para o
   **sistema final**, não para o MVP.
3. **Preço continua pendente; imagens de referência estão disponíveis.** O
   catálogo possui imagens locais com fonte/licença rastreadas, ainda tratadas
   como **dado não consolidado** e não como imagem oficial do fabricante.
4. **Sem validação regulatória inventada.** Não se deve afirmar validação
   AGROFIT/MAPA nem dizer que um produto está "validado oficialmente" sem
   comprovação por fonte real.
5. **Catálogo é base técnica inicial.** Não é verdade regulatória definitiva.
6. **Mapa é apoio operacional.** A edição de polígonos não substitui medição
   técnica ou georreferenciamento oficial.
7. **Exportações são operacionais.** CSV/PDF de relatórios não são cotação, venda
   ou documento comercial.

## Stack do MVP

- **Backend:** Python + Flask
- **Banco de dados:** SQLite local ou PostgreSQL/Supabase por configuração, com
  Flask-SQLAlchemy + Flask-Migrate
- **Segurança:** sessão Flask, permissões por perfil e CSRF/Flask-WTF
- **Exportações:** CSV com biblioteca padrão e PDF com ReportLab
- **Mapa:** Leaflet + Leaflet.draw via CDN
- **Frontend:** HTML, CSS, JavaScript

## Documentos relacionados

- [01 — Escopo do Projeto](./01-escopo-do-projeto.md)
- [02 — Requisitos do Sistema](./02-requisitos-do-sistema.md)
- [03 — Regras de Negócio](./03-regras-de-negocio.md)
- [04 — Modelagem do Banco (DER)](./04-modelagem-banco-der.md)
- [05 — Dicionário de Dados](./05-dicionario-de-dados.md)
- [06 — Arquitetura do Sistema](./06-arquitetura-do-sistema.md)
- [06.1 — Arquitetura Técnica do MVP](./06-1-arquitetura-tecnica-mvp.md)
- [07 — Roadmap do MVP](./07-roadmap-mvp.md)
- [09 — Roadmap do MVP Ampliado](./09-roadmap-mvp-ampliado.md)
- [10 — Checklist Final do MVP Ampliado](./10-checklist-final-mvp-ampliado.md)
- [Catálogo de Produtos](./catalogo-produtos/README.md)
