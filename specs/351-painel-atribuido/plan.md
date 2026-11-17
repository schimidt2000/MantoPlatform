<!-- ADAPTADO PARA A MANTO (2026-09-08) — reaplicar após qualquer atualização do Spec Kit; para este
     arquivo o hash em .specify/integrations/speckit.manifest.json deixa de conferir de propósito. -->
# Plano de implementação: Feature 351 — Painel atribuído

**Branch**: `351-painel-atribuido` | **Data**: 2026-11-17 | **Spec**: [spec.md](./spec.md)

**Input**: `/specs/351-painel-atribuido/spec.md`

**Nota**: preenchido pelo `/speckit-plan`. A constituição (`.specify/memory/constitution.md`, v3.2.0) é lida em tempo
de execução — o Constitution Check abaixo é o que ela cobra.

## Resumo

O painel de marketing passa a mostrar quanto custa a venda que o anúncio trouxe, ao lado do custo misto da 345. Uma
função só (`atribuicao_ops.atribuir_vendas`) decide, para cada venda, o último contato pago até 45 dias antes, com o
evento criado depois do contato e venda de jun/2026 em diante — a partir do que a `main` já grava (conversa do CRM,
anúncio de origem/recente da ficha, `utm_source` pago). Em volta dela: custo atribuído com desconto de 50% por frente,
lista das vendas atribuídas, funil por frente/anúncio/peça/conceito com custo (o dinheiro fica no marketing; o funil
do Comercial ganha só as divisões), resultado real do card, meta/verba/calendário por frente, proposta com número e
aviso no sino, diário com teste estruturado, três telas ajustadas para 390 px e três defeitos. Migration aditiva
`a351b0c1d2e3` sobre `d334b2c4e6f8`. Decisões em [research.md](./research.md).

## Contexto técnico

**Linguagem/Versão**: Python 3.11 (Flask + SQLAlchemy) no backend; TypeScript + React 18 (Vite) no frontend

**Dependências principais**: Flask, SQLAlchemy, Alembic (migrations à mão); React, TanStack Query, Tailwind CSS,
shadcn/ui (`@manto/ui`), Framer Motion, `@manto/api-client`, `@manto/money`

**Armazenamento**: PostgreSQL — produção no Render; verificação contra o espelho próprio `manto_351` (ver
Rastreamento de complexidade)

**Verificação**: `specs/351-painel-atribuido/verify_351.py` contra `manto_351`; `cd frontend && npm run typecheck`;
telas no Browser pane (backend 5351, Vite 6351), em 390 × 844 e em tela larga

**Plataforma-alvo**: web — app interno, usado no celular como app instalado

**Tipo de projeto**: SPA desacoplada (API JSON + React)

**Metas de desempenho**: o Desempenho continua abrindo em até ~2 s no espelho com 12 semanas; a atribuição faz um
número fixo de consultas por período (vendas, contatos das fichas delas, campanhas), nunca uma por venda. A lista do
Kanban só calcula atribuição quando há card com anúncio, e só para as fichas tocadas por esses anúncios.

**Restrições**: não tocar `app/api/marketing_agent.py`, `scripts/marketing/*`, a skill `marketing-auditor`,
`app/api/marketing_read.py:176` nem `MarketingDesempenhoPage.tsx:65-83` (345b, em paralelo); não criar as colunas da
348; nada muda na Meta, no Google nem no WhatsApp; 390 px sem rolagem lateral; `useReducedMotion`.

**Escala/escopo**: 1 tabela nova (`marketing_calendario`), 19 colunas novas em 4 tabelas, 3 endpoints novos
(`GET /api/marketing/atribuicao`, `GET|PATCH /api/marketing/calendario`), 8 endpoints com campos novos, 1 módulo de
núcleo novo (`atribuicao_ops.py`), 7 telas/diálogos tocados.

## Constitution Check

*GATE: aprovado antes da Phase 0; reavaliado após a Phase 1 — sem violação nova.*

| Princípio / seção | Como o plano cumpre (ou por que não se aplica) |
|---|---|
| I. Reutilizar antes de criar | `frente_venda_sql`, `frente_da_campanha`, `_effective_campaign_rows`, `normalize_campaign_name`, `platform_from_utm_source`, `_entrada_na_base`, `funil_ops._etapas`, `notificacoes_ops.emitir`, `require_marketing_access`/`eh_superadmin`, `MoneyInput`/`formatBRL`, `useRestaurarRolagem` |
| II. Padrões de código | type hints/docstrings; funções ≤ ~30 linhas; constantes em `app/constants.py`; TS estrito; `ruff check` nos tocados; `ruff format` só em `atribuicao_ops.py` e na migration |
| III. Camadas / API First | núcleo em `app/marketing/atribuicao_ops.py` e `comando_ops.py` (puros); endpoints em `marketing_comando_read/_write.py` (já importados em `app/api/__init__.py`); sem rota pública |
| IV. Não quebrar o que funciona | tudo aditivo; campos antigos dos payloads intactos; o custo misto continua; funil do Comercial sem dinheiro; mutação otimista do Kanban preservada (filtro na tela) |
| V. UI/UX com feedback | TanStack Query; botões com "Salvando…"; erro no campo (`ApiRequestError.fields`); estados vazios |
| VI. Esteira (Nível 1) | specify → clarify → plan → checklist → tasks → analyze → implement → converge |
| VII. Living Spec | spec atualizada antes do código (linha 23 do verify ajustada no plano) |
| VIII. Verify antes do núcleo | `verify_351.py` na fase Foundational, falhando pelos motivos certos; cenários 15 e 26 devem falhar (403) |
| IX. Dinheiro BRL | `Numeric(12,2)`/`Decimal` no servidor; `formatBRL` e `MoneyInput` de `@manto/money` |
| X. Mobile-first público | não toca superfície pública; o interno segue a regra da casa de 390 px |
| XI. Framer Motion | listas novas com `AnimatePresence`/`motion` e `useReducedMotion` |
| XII. Combobox / Maps | selects com ≤ 6 opções (frente, tipo, divisão, métrica, alvo); nenhum com > 10 |
| XIII. RBAC declarado | gate por endpoint na spec e no contrato; linhas em `docs/01` §4.3 |
| XIV. Config / efeito externo | nenhuma env nova; nenhuma escrita fora (o sino é interno) |
| XV. Texto por superfície | interno, operacional; "Situação"; estados vazios "Nenhum/Nenhuma … ainda."; premissa da atribuição escrita como fato ("é premissa até existir teste") |
| Stack | migration à mão `a351b0c1d2e3`, `down_revision = d334b2c4e6f8`; sem Jinja; sem segredo |
| Operação e Deploy | não toca `startCommand`; migration aditiva (sem ensaio destrutivo); o backend vai em lote com 348–350 |

## Estrutura do projeto

### Documentação (esta feature)

```text
specs/351-painel-atribuido/
├── spec.md · plan.md · research.md · data-model.md · quickstart.md
├── contracts/api-351.md
├── checklists/requirements.md · checklists/<tema>.md
├── tasks.md
└── verify_351.py
```

### Código

```text
migrations/versions/a351b0c1d2e3_painel_atribuido.py  # nova (aditiva)
app/models.py                                  # MarketingFrente, MarketingCalendario (nova), MarketingPost,
                                               # MarketingProposta, MarketingDiario
app/constants.py                               # ATRIBUICAO_*, INCREMENTALIDADE_PREMISSA, METRICAS_DO_TESTE, …
app/marketing/atribuicao_ops.py                # NOVO: toques pagos, atribuir_vendas, funil_com_custo,
                                               # vendas_por_anuncio, clientes_novos
app/marketing/comando_ops.py                   # resumo_frentes/painel_frentes, metas/calendário, proposta,
                                               # diário, fila da rotina, contexto da rotina, temas paginados
app/marketing/marketing_ops.py                 # conceito, resultado real do card, "no ar"
app/marketing/desempenho_ops.py                # _cac (cliente novo de anúncio)
app/conversas/funil_ops.py, constantes.py      # divisões frente/anúncio/peça/conceito (sem dinheiro)
app/notificacoes/notificacoes_ops.py           # KIND_MARKETING_PROPOSTA + produtor
app/api/marketing_comando_read.py / _write.py  # atribuição, calendário, frentes (meta/verba), temas (página)
app/api/marketing_write.py                     # conceito no POST/PATCH do card
frontend/apps/internal/src/lib/marketing.ts, lib/funil.ts
frontend/apps/internal/src/components/marketing/{PainelFrentes,FrentesConfigDialog}.tsx,
  marketing/{AtribuicaoPainel,CalendarioDialog}.tsx (novos)
frontend/apps/internal/src/components/{MarketingPostDialog,MarketingKanban}.tsx
frontend/apps/internal/src/components/notificacoes/NotificacaoItem.tsx
frontend/apps/internal/src/pages/{MarketingDesempenhoPage,MarketingDecisoesPage,MarketingTemasPage,
  MarketingPainelPage,FunilPage}.tsx
```

**Decisão de estrutura**: a regra da atribuição mora num módulo próprio do marketing para ser a porta única que a 348
troca (R1). O funil das conversas ganha só divisões; o dinheiro do funil é somado no marketing (R6), preservando a
invariante 39 do `docs/04`. Metas, calendário, proposta e diário ficam no `comando_ops` (o núcleo da 345). Em
`marketing_read.py` só muda a rota de posts (nada perto da linha 176); o resto dos campos novos do Desempenho chega
pelo `comando_ops.painel_frentes`, que o endpoint já mescla.

## Rastreamento de complexidade

| Violação | Por que é necessária | Alternativa mais simples rejeitada porque |
|---|---|---|
| Verify contra `manto_351`, não `manto_local` (Princípio VIII) | o `manto_local` é compartilhado com as sessões 348–350, que aplicam migrations de outras branches na mesma head | refazer o `manto_local` apagaria o esquema das outras sessões; o `manto_351` é o mesmo dump noturno de produção (17/11 02h), só em outro nome |
| Import tardio de `comando_ops` dentro de `funil_ops` e de `atribuicao_ops` dentro de `marketing_ops` | a regra da frente da campanha e a atribuição são únicas; o import no topo fecharia ciclo de carga (`atribuicao_ops → comando_ops → marketing_ops`) | copiar a regra da frente para o domínio das conversas criaria a segunda fonte que a 348 teria de trocar |
