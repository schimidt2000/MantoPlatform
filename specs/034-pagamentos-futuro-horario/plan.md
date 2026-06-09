# Implementation Plan: "Futuro" pelo horário de término do evento (Pagamentos)

**Branch**: `034-pagamentos-futuro-horario` | **Date**: 2026-06-09 | **Spec**: [spec.md](./spec.md)

## Summary

Trocar a classificação Futuro/Pendente dos **cachês de evento** para usar o **horário de término** do
evento comparado ao **agora em Brasília** (em vez de data de início vs `date.today()` no fuso do
servidor). Salário/gasto/comissão seguem por data de vencimento. Sem migration.

## Constitution Check
- **I. Reutilizar** ✅ — usa o `end_at`/`start_at` já existentes; mesma estrutura de itens.
- **IV. Não quebrar** ✅ — só muda o cálculo de `is_future` dos cachês; demais itens intactos.
- **VII / Padrão Brasília** ✅ — "agora" em America/Sao_Paulo, como o resto do sistema.

## Estado atual
- `_build_payment_items`: cachê → `ev_date = event.start_at.date()`; `is_future = ev_date > today`.
- `pagamentos()`: `today = date.today()` (fuso do servidor — UTC em produção).
- Eventos são guardados como datetime **naïve em horário de São Paulo** (parse_event_datetime).

## Design Detalhado
1. `app/financeiro/routes.py`: importar `ZoneInfo`; constante `TZ_SP = ZoneInfo("America/Sao_Paulo")`.
2. `pagamentos()`:
   - `now_sp = datetime.now(TZ_SP).replace(tzinfo=None)` (naïve SP, igual ao armazenado).
   - `today = now_sp.date()` (data de Brasília, no lugar de `date.today()`).
   - Passar `now_sp` para `_build_payment_items`.
3. `_build_payment_items(..., now_dt)`:
   - Cachê: `ev_end = r.event.end_at or r.event.start_at` (se houver evento);
     `is_future = bool(ev_end and ev_end > now_dt)`.
   - `date` (coluna) continua sendo a data de início (exibição/ordenação).
   - Salário/gasto: `is_future` por `due_date/expense_date > today` (inalterado).
4. Verificação: evento terminando no futuro hoje → Futuro; terminado hoje → Pendente; salário/gasto
   inalterados; boot + ruff.

## Project Structure
```text
app/financeiro/routes.py   # TZ_SP; now_sp em pagamentos(); is_future por end_at em _build_payment_items
```

## Fora de escopo
- Classificação de salário/gasto/comissão (mantida). Outras telas. Sem migration.
```
