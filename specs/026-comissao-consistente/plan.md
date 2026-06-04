# Implementation Plan: Comissão consistente entre as telas

**Branch**: `026-comissao-consistente` | **Date**: 2026-06-04 | **Spec**: [spec.md](./spec.md)

## Summary

Reconciliar as comissões **a pagar** com o cálculo ao vivo do evento (mesma base da aba comercial),
para que a página de Comissões e o resumo nos Pagamentos parem de mostrar a taxa antiga. Reaproveita
`_sync_commission_payment(event)` (já atualiza só `a_pagar` e preserva `pago`). Chamado ao abrir as
telas de Comissões e Pagamentos. Sem migration.

## Constitution Check
- **I. Reutilizar** ✅ — reusa `_sync_commission_payment` (fonte única do cálculo da comissão).
- **IV. Não quebrar** ✅ — só atualiza `a_pagar`; pagas preservadas; estornos intactos; verificação
  no app. Sem migration.
- **VI. Planejar antes de codar** ✅ — causa raiz identificada.

## Project Structure

```text
app/financeiro/routes.py   # _resync_pending_commissions(); chamado em comissoes() e pagamentos()
```

## Design Detalhado

### Causa raiz
`CommissionPayment.amount` é gravado por `_sync_commission_payment` no momento da venda (taxa de
então = 2%). A aba comercial calcula ao vivo (2,5% atual). A página de Comissões/Pagamentos lê o
valor gravado → divergência.

### Correção
- `_resync_pending_commissions()`: para cada evento com comissão **a pagar** (positiva), chamar
  `_sync_commission_payment(ev)` (recalcula `amount`/`sale_date` só para `a_pagar`; cancela se
  inelegível) e `commit`.
- Chamar `_resync_pending_commissions()` no início de `comissoes()` e de `pagamentos()` (antes de
  montar o resumo de comissões da 024).

Pseudocódigo:
```text
def _resync_pending_commissions():
    pend = CommissionPayment.query.filter(status=='a_pagar', event_id != None, amount >= 0).all()
    for eid in {p.event_id for p in pend}:
        ev = CalendarEvent.get(eid)
        if ev: _sync_commission_payment(ev)
    commit()
```

### Verificação (app real)
- Evento com venda; gravar comissão a 2% (simular) → página de Comissões mostra 2%.
- Rodar a reconciliação (abrir Comissões/Pagamentos) → comissão a pagar vira 2,5% (= aba comercial).
- Comissão marcada como paga não muda. Estorno (negativo) não muda.

### Fora de escopo
- Refactor maior de "fonte única de cálculo" (REVIEW da 019) — aqui só reconciliamos a pagar.
- Sem migration.
