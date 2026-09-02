# Hotfix 267b — venda sem "Data da venda" some da Planilha de Pagamentos

**Branch**: `267b-hotfix-data-da-venda` · **Created**: 2026-09-02 · **Status**: Draft · **Migration**: nenhuma

## Sintoma

Comissão da Thays em setembro "300 e poucos reais", quando agosto foi o melhor mês dela.

Medido em produção em 02/09/2026:

| Onde | Comissões 08/2026 da Thays |
|---|---|
| Tela **Comissões** (`/financeiro/comissoes?mes=2026-08`) | 43 vendas · **R$ 5.466,20** `a_pagar` |
| **Planilha de Pagamentos**, item "Comissões 08/2026" datado 05/09 | 5 vendas · **R$ 303,94** |

As duas telas leem a mesma tabela. A diferença são 38 linhas (R$ 5.162,26) cujo `sale_date` é NULL.

## Causa

1. **A "Data da venda" parou de ser preenchida em 05/08/2026.** Até 04/08 o formulário de criação
   de evento era o Jinja, que prefilhava o campo com hoje (`event_create.html:505`,
   `value="{{ old.get('sale_date') or today_str }}"`). No deploy da 205+206 (04/08) o React virou
   a interface primária; o formulário React nasce com `sale_date: ""` (`eventFormSchema.ts:91`), o
   rótulo diz "Data da venda *" mas o schema é `z.string()` sem mínimo, e a página manda
   `sale_date: values.sale_date || null` (`EventCreatePage.tsx:294`). Quem preenche, preenche
   (Fatima); quem não preenche, grava venda sem data (Thays: todas as 44 vendas desde 05/08;
   R$ 206.490 em vendas de agosto).
2. **A Planilha ignora comissão sem data.** `_build_commission_items` (`financeiro/routes.py`)
   filtra pelo ciclo `coalesce(payable_from, sale_date)` (267); com os dois nulos a linha não cai
   em **mês nenhum** — nunca entra num lote de pagamento. A tela de Comissões não sofre porque
   `_month_scoped_query` tem fallback para `created_at`. As duas telas discordavam.

Colaterais do mesmo defeito: o deep-link do evento para Comissões (`ComercialSection.tsx:90`) só
existe com `sale_date`; e relatórios por mês de venda (Dashboard Comercial) perdem essas vendas.

## Solução

1. **A regra sai do formulário e vai para o servidor.** `event_ops.resolver_data_da_venda()`:
   data informada vale; sem venda, sem data; venda que já tinha data mantém (editar a aba
   Comercial não apaga a data); venda registrada **agora** sem data → hoje (relógio de São Paulo);
   venda antiga já sem data continua sem — o servidor não inventa data velha, o backfill resolve.
   Usada na criação (`_create_event_row`) e nas duas edições (`update_event_core`,
   `update_event_comercial`) — qualquer tela, hoje ou futura.
2. **O React volta a nascer com hoje** (`defaultValues: { ...DEFAULT, sale_date: hojeYmd() }`) —
   não por segurança (o servidor já garante), mas para a pessoa **ver** a data que vai valer.
3. **Cinto no ciclo**: `ciclo_de_pagamento_expr()` vira `coalesce(payable_from, sale_date,
   date(created_at))`. Comissão sem data cai no mês em que a linha nasceu (que é quando a venda foi
   gravada) — a mesma regra que a tela de Comissões já usava; as duas telas voltam a concordar, e
   `liquidar_periodo` (mesma expressão) liquida o que a planilha mostra.
4. **Backfill do legado** (`backfill_data_da_venda.py`, dry-run por padrão): 47 eventos com venda
   e sem data em produção ganham a data pela melhor evidência — `created_at` da linha de comissão
   (44 casos), do `EventLog` "Atualizou dados comerciais: venda" (evento 267, importado do Google,
   venda digitada em 02/07) ou do próprio evento — convertida para o dia em São Paulo; as linhas
   de comissão `a_pagar`/`no_banco` do evento recebem a mesma data.

## Decisões

1. **Servidor, não só formulário.** Foi um prefill de template que segurava a regra por dois anos;
   quando a tela mudou, a regra caiu junto. Regra de negócio ("venda tem data") mora no `*_ops`.
2. **Hoje só para venda NOVA.** Numa edição de venda antiga sem data, carimbar hoje seria mentir
   sobre o mês da comissão — pior que NULL, porque paga no mês errado sem ninguém notar.
3. **Fallback por `created_at` fica**, mesmo depois do backfill: é o que impede o próximo caso
   (importação, script, tela nova) de sumir da planilha. Ressalva documentada: `created_at` é UTC
   e uma venda gravada depois das 21h do último dia pode cair no mês seguinte por esse degrau.
4. **Backfill é script com dry-run e verify, não migration.** Corrige dado, não schema; roda uma
   vez; a saída (tabela com fonte de cada data) é o registro do que foi feito.

## Verificação

`verify_267b.py` contra `manto_local` (Google dublado — `insert_event`/`update_event` de
`app.calendar.service` e `app.calendar.routes` substituídos; nada chega à Agenda real):

1. `POST /api/events` com venda e sem `sale_date` → `sale_date` = hoje (SP); a linha de comissão
   nasce com a mesma data e aparece no item da Planilha do mês seguinte.
2. `POST /api/events` sem venda → `sale_date` NULL.
3. `PATCH /events/<id>/comercial` que **registra** a venda (antes não havia) sem data → hoje.
4. Evento com venda e data NULL (legado) + `PATCH` sem data → continua NULL (não inventa data).
5. `PATCH` com data explícita → a data informada; venda com data + `PATCH` sem data → mantém.
6. Comissão legada com `sale_date` NULL aparece em `_build_commission_items` do mês do `created_at`
   e `liquidar_periodo` a liquida (as duas usam a mesma expressão).
7. Backfill dry-run não escreve nada; `--execute` preenche evento e comissão pela fonte certa
   (comissão → log → criação).
8. Limpeza.

Em tela (`/events/new`): o campo "Data da venda" nasce preenchido com hoje. Portões: `npm run
typecheck`, `ruff` no baseline, `docs/03` (entrada 267b) e `docs/04` §2.

## Fora de escopo

Exigir `sale_date` no schema Zod quando há venda (o servidor já garante); `_month_scoped_query`
excluir `no_banco` enquanto a planilha inclui (assimetria antiga, docs/05); o evento 267 sem
vendedor (venda de R$ 2.280 sem comissão para ninguém — decisão do dono, não do código).
