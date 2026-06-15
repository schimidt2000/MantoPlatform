# Implementation Plan: Cobranças comerciais incluindo o passado

**Branch**: `046-cobrancas-passado` | **Date**: 2026-06-15 | **Spec**: [spec.md](./spec.md)

## Summary

Sem migration. O painel de cobranças (`app/__init__.py`, rota `/`) já filtra por `task_cutoff`
(= `release_date` ou hoje). Mudanças:

1. **Cobranças usa a data de início como lookback real** — o filtro `start_at >= task_cutoff` já
   inclui passado quando `release_date` está no passado; só falta o usuário configurar 01/05/2026.
   Garantir que o cálculo de severidade trate eventos passados.
2. **Severidade "atrasado"/"vencido"** para eventos passados/com data combinada vencida, no topo.
3. **Admin**: atualizar o texto de ajuda do campo `release_date` para citar as cobranças.

## Constitution Check
- **I. Reutilizar** ✅ — reusa `release_date` e o painel da 040; mesma convenção de Brasília.
- **IV. Não quebrar** ✅ — tarefas seguem usando `task_cutoff`; quitados/anteriores continuam fora.
- **V. UI/UX** ✅ — destaque "Atrasado" vermelho, ordenado primeiro.

## Design Detalhado

### 1. `app/__init__.py` — loop de `pending_payments`
- `ev_date = ev.start_at.date()`; `is_past = ev_date < today_sp`.
- Severidade:
  - futuro/faturado com `payment_due_date`: `vencido` se due ≤ hoje, senão `info`.
  - senão, `is_past` → `atrasado`.
  - senão (futuro): `urgent` se faltam ≤ 2 dias; `warn` se recebido < 50%; senão pula.
- `pending_payments` ganha `is_past`.
- `_SEVERITY_ORDER = {"atrasado":0, "vencido":1, "urgent":2, "warn":3, "info":4}`; desempate por
  `start_at` ascendente (mais antigo primeiro).

### 2. `app/templates/home.html` — painel Comercial
- Vermelho de fundo para `atrasado|vencido|urgent`; dourado para `warn`.
- Badge: `atrasado`→"ATRASADO", `vencido`→"VENCIDO", `urgent`→"URGENTE", `warn`→"SINAL PENDENTE".

### 3. `app/templates/admin_settings.html`
- Ajuda do campo "Data de início do sistema": citar que controla também as cobranças do comercial.

## Verificação
- ruff (sem novos) + boot.
- Test client: com `release_date` no passado, evento passado em aberto aparece como "atrasado" e
  no topo; evento anterior à data não aparece; quitado não aparece; futuro segue urgent/warn;
  alterar release_date muda o recorte. Seeds temporários, limpos no finally.

## Project Structure
```text
app/__init__.py                       # severidade atrasado/vencido + is_past + ordenação
app/templates/home.html               # badges/realce no painel Comercial
app/templates/admin_settings.html     # texto de ajuda do release_date
```

## Fora de escopo
- Novo campo/migration (reusa release_date).
- Mudar recorte das tarefas de casting/figurino (seguem como hoje).
