# Implementation Plan: Resumo de comissões nos Pagamentos (dia 5)

**Branch**: `024-comissoes-pagamentos` | **Date**: 2026-06-04 | **Spec**: [spec.md](./spec.md)

## Summary

Adicionar à página de Pagamentos itens `type="commission"` — **um por vendedor** — somando as
comissões dos eventos **vendidos no mês anterior**, datados no **dia 5** do mês visualizado. A linha
é acionável (marcar pago) e sincroniza com `CommissionPayment` (mesma fonte da página de Comissões).
Sem migration (derivado dos registros existentes). As linhas da tabela já são genéricas (dict do
item), e o controle de status já posta `item_type`/`item_id`.

## Constitution Check
- **I. Reutilizar** ✅ — reusa `CommissionPayment`, a tabela genérica de pagamentos e o endpoint de
  status. Sem nova tela.
- **IV. Não quebrar** ✅ — adiciona um tipo de item; estados sincronizam com Comissões; verificação
  no app. Sem migration.
- **V. UI/UX** ✅ — linha por vendedor com PIX, datada no dia 5, "futuro" até lá.
- **VI. Planejar antes de codar** ✅ — este plano; 2 decisões confirmadas.

## Project Structure

```text
app/financeiro/routes.py            # _build_commission_items(); pagamentos() inclui as linhas;
                                    #   set_payment_status() trata item_type="commission"
app/templates/financeiro/pagamentos.html  # omitir checkbox de bulk só para type="commission"
```

## Design Detalhado

### 1. Construir itens de comissão (`_build_commission_items`)
- Período = mês anterior ao visualizado: `[prev_start, prev_end)`.
- Query `CommissionPayment` com `status in (a_pagar, pago)` e `sale_date` no período; agrupar por
  `seller_id`; somar `amount` (estornos negativos reduzem). Pular soma zero.
- Para cada vendedor, item dict (mesmas chaves dos demais): `type="commission"`,
  `id=f"{seller_id}:{prev_ano}-{prev_mes:02d}"`, `date=date(ano_visto, mes_visto, 5)`,
  `event_title="Comissões MM/AAAA"`, `person_name=vendedor`, `amount=soma`, `pix_key`/tipo do
  vendedor, `status="pago" if todas pagas else "nao_pago"`, `is_future=due_date>today`.

### 2. Incluir em `pagamentos()`
- Calcular mês anterior; `items += _build_commission_items(...)`; reordenar por data. Totais já
  somam todos os itens (comissão entra naturalmente).

### 3. Marcar pago (`set_payment_status`, novo ramo `commission`)
- `item_id = "sellerId:YYYY-MM"`. Parse seller + período. `target = "pago" if status=="pago" else
  "a_pagar"`. Atualiza todas as `CommissionPayment` do vendedor com `sale_date` no período e status
  in (a_pagar,pago): `status=target`, `paid_at = hoje/None`. Audita. Commit.
- O guard de status existente aceita nao_pago/pago/no_banco; mapeio "pago"→pago, demais→a_pagar.

### 4. Template
- Omitir o checkbox de seleção (bulk) **apenas** para `item.type == 'commission'` (evita o
  bulk-action tentar `int(item_id)` num id composto). O resto da linha (status, copiar, PIX) é
  genérico e já funciona.

### Verificação
- Vendas em maio → ao ver Pagamentos de junho, 1 linha por vendedor datada 05/06 com a soma certa.
- Marcar pago na linha → `CommissionPayment` do vendedor/período viram "pago" e a página de Comissões
  reflete; desfazer volta para "a pagar".
- Antes do dia 5 → linha como "futuro". Soma zero → sem linha. Bulk não quebra (sem checkbox).

### Fora de escopo
- Estornos com data de venda nula (seguem só na página de Comissões). Sem migration.
