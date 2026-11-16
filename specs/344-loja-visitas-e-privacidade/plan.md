# Plano de implementação: 344 — A loja conta as visitas e pede licença

**Branch**: `344-loja-visitas-e-privacidade` | **Data**: 2026-11-16 | **Spec**: [spec.md](./spec.md)

**Input**: `/specs/344-loja-visitas-e-privacidade/spec.md`

## Resumo

Três peças sobre a Loja de Interações Virtuais, num deploy:
1. **Contagem anônima**: a landing manda um `POST …/visita` por aba (guard em `sessionStorage`) com a
   origem já reduzida no front (parâmetro → procedência → "direto") e normalizada de novo no servidor;
   o servidor soma numa linha por campanha + dia + origem (`INSERT … ON CONFLICT DO UPDATE`). O pedido
   guarda a origem. A tela da campanha ganha o card "Visitas e vendas" (funil por origem e por dia) e os
   links `alo.mantoproducoes.com.br/<slug>?origem=<canal>` com copiar.
2. **LGPD**: página `/v/privacidade` (pública, no `LojaLayout`), linha + caixinha no formulário, "Seu
   nome"; `reservar` grava `marketing_opt_in_at`/`_version`, `buyer_name`, `origem`; `_efetivar_no_banco`
   chama `_cliente_da_venda` num SAVEPOINT (falha não derruba a venda); a varredura ganha a rotina
   `dicas`, que apaga `behavior_notes` vencidas no pedido, no `CalendarEvent.description` e reescreve a
   descrição no Google; o CRM conta a origem "loja" e mostra o aceite na ficha.
3. **Pixel**: `SiteSetting.meta_pixel_id` editado nas Configurações; `GET /api/virtuais/rastreamento`;
   no `LojaLayout`, aviso de cookies + carregamento do `fbevents.js` só com aceite (`localStorage`);
   eventos `PageView`, `InitiateCheckout` (reserva criada) e `Purchase` (pedido pago, uma vez por token).

## Contexto técnico

**Linguagem/Versão**: Python 3.11 (Flask + SQLAlchemy) no backend; TypeScript + React 18 (Vite)
no frontend

**Dependências principais**: Flask, SQLAlchemy (`sqlalchemy.dialects.postgresql.insert` para o upsert),
Alembic (à mão); React, TanStack Query, `@manto/api-client`, `@manto/ui`. Nenhuma dependência nova: o
pixel é o snippet oficial carregado de `connect.facebook.net` só com aceite.

**Armazenamento**: PostgreSQL — 1 tabela nova, 8 colunas novas (ver `data-model.md`).

**Verificação**: `verify_344.py` contra `manto_344` (dump de 16/11 02h); regressão `verify_310`,
`verify_340`, `verify_341`, `verify_310b`, `verify_205`; typecheck; telas no Browser pane (loja em
375×812).

**Plataforma-alvo**: web — Render.

**Tipo de projeto**: SPA desacoplada (API JSON + React)

**Metas de desempenho**: a contagem é disparada depois do primeiro render e nunca bloqueia (fire and
forget); o upsert é uma instrução.

**Restrições**: sem cookie e sem IP na contagem; sem dado pessoal para a Meta; rota pública nova da SPA
fica sob `/catalogo/v` (já servida, sem mexer em `server.js`); API nova sob `/api` (já repassada).

**Escala/escopo**: 1 tabela, 8 colunas, 3 endpoints novos (+2 alterados), 1 página pública nova, 4 telas
alteradas (landing, pedido, campanha, configurações; ficha e lista de clientes).

## Constitution Check

| Princípio / seção | Como o plano cumpre |
|---|---|
| I. Reutilizar antes de criar | `normalize_phone` do importador de clientes; `formularios_ops.ensure_event_client` para ligar evento↔cliente; varredura existente (`ciclo_de_varredura`) em vez de thread nova; `update_event` do calendário; `config_ops.update_settings` para o pixel; `require_virtuais_access` |
| II. Padrões de código | type hints/docstrings pt-BR; constantes em `app/constants.py` (origens, versão do aceite, dias de retenção); `ruff check` |
| III. Camadas / API First | regras em `virtuais_ops.py` (`registrar_visita`, `funil_da_campanha`, `_cliente_da_venda`, `apagar_dicas_vencidas`); endpoints só RBAC + serialização (`virtuais_public.py`, `virtuais_read.py`) |
| IV. Não quebrar o que funciona | tudo aditivo; `buyer_name`/`marketing_opt_in`/`origem` opcionais no `reservar`; CRM em SAVEPOINT; regressão das cinco verifies da loja |
| V. UI/UX com feedback | botão copiar com "Copiado"; caixinha acessível (44px); erros no campo |
| VI. Esteira (Nível 1) | esteira completa nesta pasta |
| VII. Living Spec | spec com Clarifications antes do código |
| VIII. Verify antes do núcleo | `verify_344.py` na Fase 2, falhando por falta de tabela/colunas/rotas |
| IX. Dinheiro BRL | valor da compra para o pixel vem do `total_value` (string) → `apiMoneyToNumber` |
| X. Mobile-first público | landing, aviso de privacidade e aviso de cookies em 375px, alvos ≥ 44px |
| XI. Framer Motion | aviso de cookies entra com `useReducedMotion` respeitado |
| XII. Combobox / Maps | não se aplica |
| XIII. RBAC declarado | tabela na spec; linhas novas em `docs/01` §4.3 |
| XIV. Config / efeito externo | `LOJA_PUBLIC_BASE_URL` com default real; escrita no Google na limpeza respeita `CALENDAR_SUPPRESS_EVENT_WRITES`; pixel desligado por padrão (ID vazio) |
| XV. Texto por superfície | público (loja): lúdico e claro, sem juridiquês no formulário; o aviso de privacidade em linguagem simples; interno: operacional ("Visitas", "Reservas", "Vendas", "Conversão") |
| Stack | migration à mão, `down_revision = f310b2a4c6e8`; sem Jinja; sem segredo |
| Operação e Deploy | migration aditiva (sem ensaio destrutivo); deploy de backend à noite; não toca `startCommand` |

## Estrutura do projeto

```text
app/models.py                                  # VirtualCampaignVisit; colunas em VirtualOrder, Client, SiteSetting
migrations/versions/e344a1b2c3d4_loja_visitas_e_privacidade.py
app/constants.py                               # VIRTUAL_ORIGENS, VIRTUAL_ACEITE_VERSAO, VIRTUAL_DICAS_RETENCAO_DIAS
app/config.py                                  # LOJA_PUBLIC_BASE_URL (default real)
app/marketing/virtuais_ops.py                  # registrar_visita, funil_da_campanha, _cliente_da_venda, apagar_dicas_vencidas
app/api/virtuais_public.py                     # POST visita, GET rastreamento; reservar aceita campos novos
app/api/virtuais_read.py                       # GET funil
app/admin/config_ops.py, app/api/admin_config_read.py   # meta_pixel_id
app/clientes/client_ops.py, app/api/clientes_read.py    # origem "loja" no gráfico; aceite na ficha
frontend/apps/public/src/lib/virtuais.ts       # origem da visita, useRegistrarVisita, useRastreamento, tipos
frontend/apps/public/src/lib/pixel.ts          # consentimento + fbq (novo)
frontend/apps/public/src/components/loja/AvisoCookies.tsx  # (novo)
frontend/apps/public/src/components/loja/LojaLayout.tsx    # monta o aviso e o PageView
frontend/apps/public/src/pages/CampanhaVirtualPage.tsx     # visita, nome, caixinha, linha de privacidade
frontend/apps/public/src/pages/PedidoVirtualPage.tsx       # Purchase quando pago
frontend/apps/public/src/pages/PrivacidadeLojaPage.tsx     # aviso de privacidade (novo)
frontend/apps/public/src/App.tsx                           # rota /v/privacidade
frontend/apps/internal/src/pages/VirtuaisCampanhaFormPage.tsx  # card Visitas e vendas + links
frontend/apps/internal/src/lib/virtuais*.ts                # hook do funil
frontend/apps/internal/src/pages/AdminSettingsPage.tsx + lib/adminConfig.ts  # campo do pixel
frontend/apps/internal/src/pages/ClientDetailPage.tsx, ClientsListPage.tsx + lib  # aceite; Loja no gráfico
```

**Decisão de estrutura**: tudo no domínio da loja (`virtuais_ops`); o CRM só ganha leitura (contagem e
ficha) — a escrita do cliente nasce da venda, dentro do `_ops` da loja, reaproveitando a regra de
telefone do CRM. `/v/privacidade` fica dentro do `LojaLayout` para herdar tema e aviso de cookies.

## Rastreamento de complexidade

| Violação | Por que é necessária | Alternativa mais simples rejeitada porque |
|---|---|---|
| Verify contra `manto_344`, não `manto_local` | o `manto_local` está na migration do CRM 334 (sem push) | refazer o `manto_local` apagaria o esquema das branches do CRM |
| `virtuais_ops` importa `formularios_ops.ensure_event_client` | ligar evento↔cliente tem regra (Contratante × Outros, `event.client_id`) | copiar a regra criaria uma segunda fonte |
