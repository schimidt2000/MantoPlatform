# Modelo de dados — Feature 312

**Nenhuma entidade, coluna, tabela ou migration nova.** A entrega lê o que já existe.

## O que se lê

| Fato | Onde mora | Uso aqui |
|---|---|---|
| O evento está cancelado | `CalendarEvent.cancelled_at` (`models.py:298`); `is_cancelled`; `situacao` (`:427-449`, cancelado > sumiu > exclusão) | todo filtro e toda recusa; `event_situacao` das coisas ligadas |
| Motivo e autor | `cancellation_reason`, `cancelled_by_id` | Q9: só com `show_comercial` |
| Dinheiro do cancelado | `cancel_ops.resumos_cancelados(ids)` → `ResumoCancelado` (regimes `venda`, `satelite`, `dia`, `virtual`, `legado`) | página, card, ficha da cliente |
| Cancelados do período | `cancel_ops.cancelados_do_periodo(inicio, fim, *, seller_id, educamanto_only)` (só `venda` e `legado` com dinheiro) | card |
| Estado de cada devolução | `filtro_devolucao` sobre `SpecialExpense` (categoria devolução) | filtro `devolucao` da página |
| Grupo vivo | `group_ops.dias_vivos(event)` | painel do grupo e `group_label` |
| Quem o ato avisou | `event_cancellation_elenco`; `elenco_do_ato` | régua de "a avisar" da pendência |
| Pedido ao Casting | `Notification` `kind = evento.cancelado_escala`, `entidade = ("calendar_event", dia.id)` | marcar lida quando a escala esvazia |

## Regras derivadas (sem estado novo)

- **Visível em lista** ⇔ `cancelled_at IS NULL`. Nada olha `deletion_requested_at` nem `google_missing_since`.
- **A avisar** (pendência do Casting) ⇔ vaga de hoje com talento, em evento cancelado com `start_at >=
  dashboard_cutoff`, pela régua de `elenco_do_ato` (fora presença e quem recusou). Some sozinha quando a vaga
  esvazia.
- **Somente consulta** ⇔ `cancelled_at IS NOT NULL`, para qualquer papel; as portas de venda e o motivo seguem as
  regras próprias da 306/306b.
- **Card**: o universo de `cancelados_do_periodo` (mês do cancelamento, São Paulo); com tudo devolvido, retido 0 e
  conta na quantidade; cancelado sem dinheiro fica fora (e aparece só na página).
- **Total retido da página**: soma por evento dos `resumo.retido` listados.

## Formas dos payloads

As formas exatas estão em `contracts/api.md` (página, card, detalhe, Home, coisas ligadas).
