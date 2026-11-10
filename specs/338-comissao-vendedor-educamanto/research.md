# Pesquisa — Feature 338

Fontes lidas em `main` (`96837811`): `app/financeiro/comissoes_ops.py`, `app/calendar/cancel_ops.py`,
`app/calendar/group_ops.py`, `app/calendar/event_ops.py`, `app/api/agenda_write.py`,
`app/api/agenda_read.py`, `app/financeiro/routes.py`, `app/financeiro/vendas_ops.py`; mapa de consumidores
feito por um agente de leitura (lista abaixo, R8). Dados conferidos na produção (leitura) em 06/11.

## R1 — Onde mora a comissão do vendedor: coluna no evento

- **Decisão**: `calendar_events.educamanto_seller_commission NUMERIC(12,2) NULL`, campo de venda (entra em
  `group_ops.SATELLITE_FIELDS_CLEARED`, logo some do satélite ao agrupar e passa na passagem da venda).
- **Por quê**: o orçamento da calculadora (`educamanto_quotes`) não tem vínculo com o evento; o valor
  precisa estar onde a comissão é calculada e onde o cancelamento congela.
- **Rejeitado**: ler do `EducaMantoQuote` (sem vínculo; snapshot congelado por design, `docs/00` §6 item
  12); acréscimo BV (`event_acrescimos.is_bv`) — o BV paga terceiro pela Planilha com PIX, não entra na
  comissão da pessoa, e o dono pediu "comissão de uma fonte diferente".

## R2 — Duas linhas por evento: uma coluna `source` e duas trilhas

- **Decisão**: `commission_payments.source VARCHAR(30) NULL`. `NULL` = a comissão do evento (a de sempre,
  "trilha principal"); `vendedor_educamanto` = a do vendedor ("trilha do vendedor"). Toda consulta que hoje
  procura "a linha do evento" passa a filtrar a trilha principal; a reconciliação da 306 ganha o
  parâmetro `fonte` e trabalha numa trilha por vez.
- **Por quê**: `_comissao_existente` pega a linha viva mais recente do evento — sem o corte, a
  sincronização (que roda a cada abertura de Comissões/Planilha via `_resync_pending_commissions`)
  sobrescreveria a linha do vendedor. A reconciliação da 306 dá alvo 0 a todo beneficiário com linha viva
  que não está em `alvos`: sem trilhas, o corte de um dia e a correção do cancelado zerariam o vendedor.
  Com trilhas, nenhum chamador da 306 muda (todas as linhas de hoje têm `source NULL`).
- **Rejeitado**: marca nas notas (padrão `NOTA_COMISSAO_PROPRIA_DO_DIA`) — as notas são reescritas pela
  reconciliação e já carregam três marcas; uma coluna é consultável e indexável, e a migration existe de
  qualquer jeito (R1). Linha sem `event_id` — confundiria com o estorno órfão (`filtro_estorno_orfao`).

## R3 — A base do responsável

- **Decisão**: `custo_da_base_educamanto(event, settings, *, sem_o_dia=None)` = cachês dos dias vivos
  (`_event_cost`, a régua da 239) + gastos extras **aprovados** dos dias vivos, fora a devolução
  (`cancel_ops.filtro_devolucao`) + comissão do vendedor (só com quem receba). O imposto sai à parte, em
  `_base_da_comissao`: `venda × alíquota ÷ 100` quando há nota, com `com_nota` sobreponível para o
  cancelado (`event_cancellations.with_invoice`). A alíquota é a da DRE (`_get_tax_rate`, `SiteSetting.tax_rate`
  ou 16%), que muda de `routes.py` para `comissoes_ops.py` (routes reexporta o nome).
- **Por quê**: o imposto depende da venda, que a correção do cancelado pode mudar; o custo não. O
  `commission_cost` congelado no ato passa a guardar cachês + gastos + vendedor (o que a base usa), e a
  correção da venda do cancelado refaz o imposto pela venda nova.
- **Devolução fora**: no cancelado ela já está descontada no retido; contar também no custo seria duas
  vezes. No vivo, devolução parcial é rara e fica registrada como premissa.
- **Números (produção, 06/11)**: Jundiaí 44.800 − 24.550 − 3.313,65 − 1.500 = 15.436,35 → R$ 771,82;
  Santo Américo 12.000 − 1.920 − 8.200 − 659,87 = 1.220,13 → R$ 61,01.

## R4 — A linha do vendedor no vivo

- **Decisão**: `_sync_commission_payment` vira a casca das duas trilhas: o corpo de hoje passa a
  `_sync_comissao_do_evento` e, depois dele, `_sync_comissao_do_vendedor_edu`. Valor = comissão do vendedor
  (teto na venda), `seller_id` = vendedor do evento, `sale_date` = data da venda, `payable_from` = dia do
  evento (decisão do dono: mês do evento, como a do responsável).
- **Por quê**: os 8 chamadores de `_sync_commission_payment` (PATCH em bloco, `/comercial`, `/orcamento`,
  acréscimos, agrupar, Jinja comercial e agrupar, criação) passam a cuidar das duas linhas sem mudar.

## R5 — O cancelado

- **Decisão**: `event_cancellations.educamanto_seller_id` + `educamanto_seller_commission` congelam quem e
  quanto no ato (regime `venda`). Alvo do vendedor = `comissao_do_retido(valor, retido, venda)` (a mesma
  proporção do responsável e do BV, com teto no valor). Pontos: execução do ato e prévia (a prévia soma o
  plano da trilha do vendedor ao da principal), `reaplicar_cancelado` (correção do retido), troca de
  vendedor em `recongelar_do_comercial`, resumo (`ResumoCancelado.comissao_vendedor_retido`) e totais da DRE.
- **Corte de um dia e passagem**: a trilha do vendedor não muda (o valor fica no principal vivo); a base
  do responsável perde cachês e gastos do dia (`custo_da_base_educamanto(…, sem_o_dia=dia)`).
- **Alterar o valor no cancelado**: 409 `cancelado` para todos (a porta não recongela o valor — regra única
  da 306, `docs/00` §4).

## R6 — DRE e Dashboard Comercial

- **Decisão**: `_compute_drg` soma a comissão do vendedor às comissões dos eventos normais;
  `vendas_ops.build_kpis` soma na `comissao_prevista` (para "Minhas vendas", só quando a pessoa é o
  vendedor). Os outros leitores de `_event_commission` (tabela por evento do dashboard Jinja/API, pipeline
  Jinja) ficam como estão — mostram a comissão do responsável por evento.

## R7 — Telas

- **Decisão**: `venda.educamanto_seller_commission` + `venda.mostra_comissao_do_vendedor` no detalhe; campo
  "Comissão do vendedor" no `VendaForm` (só EducaManto com responsável); `kpi.commission` passa a ser só a
  trilha principal e `kpi.seller_commission` traz a do vendedor; `CommissionEntry.origem` e
  `commission_lines[].origem` rotulam a linha em Comissões e na Planilha. Campo novo opcional no React
  (`docs/00` §6 item 21).

## R8 — Consumidores conferidos (agente de leitura)

`comissao_exibida_do_evento` somava toda linha viva → passa a trilha principal; `sale_count` do resumo por
vendedor contava a linha do vendedor como venda → conta eventos distintos; `aplicar_estorno_comissao`
(exclusão) trata todas as linhas → o estorno leva o `source` da linha; `liquidar_*`, `pay_seller_month`,
`_build_commission_items`, `financeiro_write` e `user_ops` trabalham por vendedor e ciclo — corretos sem
mudança. `scripts/auditor/collect.py` lê `paid_at` (correto); a skill `financeiro` documenta a tabela.

## R9 — Banco de verificação

`manto_local` está em `d334b2c4e6f8` (migration do CRM, branch não publicada) e parado em 20/10. Para não
desfazer o esquema das outras sessões, a 338 usa `manto_338`, restaurado do dump de produção de
06/11 02:00 (`backups/manto_2026-11-06_0200.dump`, revisão `d323b5a1c0e7` = head da `main`), com a URL em
`C:\tmp\mp338\.local-db-url` (ignorado pelo git).
