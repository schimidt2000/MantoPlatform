# Implementation Plan: Avaliar evento só depois que ele ACABOU

**Branch**: `039-avaliar-so-apos-fim` | **Date**: 2026-06-12 | **Spec**: [spec.md](./spec.md)

## Summary

Causa raiz: `app/talent_portal/routes.py` compara horários de evento (gravados **naïve em
Brasília**) com `datetime.utcnow()` (**UTC, +3h**) — o portal "vê" o futuro com 3h de antecedência,
e por isso o evento apareceu para avaliar antes de começar. Correção: helper `_now_sp()` (agora em
Brasília, naïve) usado em TODAS as comparações com horários de evento do portal + trava no servidor
nas rotas de avaliação (GET/POST) para evento não terminado. Sem migration.

## Constitution Check
- **I. Reutilizar** ✅ — mesmo padrão `ZoneInfo("America/Sao_Paulo")` já usado em financeiro (034),
  calendar e talents (038).
- **IV. Não quebrar** ✅ — janelas de 7/30 dias preservadas; carimbos internos (UTC) intactos.
- **V. UI/UX** ✅ — recusa com flash amigável e redirect (sem tela de erro).

## Design Detalhado

### 1. Helper
- `_now_sp() -> datetime` em `app/talent_portal/routes.py`:
  `datetime.now(ZoneInfo("America/Sao_Paulo")).replace(tzinfo=None)`.

### 2. Trocas de relógio (só comparações com horários de evento)
| Local | Linha (aprox.) | Hoje | Passa a |
|---|---|---|---|
| `_rateable_event_ids` | 222/229 | `utcnow()` | `_now_sp()` |
| `_editable_rating_event_ids` | 240/248 | `utcnow()` | `_now_sp()` |
| `home()` — `today` | 313 | `utcnow().date()` | `_now_sp().date()` |
| `home()` — upcoming | 329 | `utcnow()` | `_now_sp()` |
| `home()` — history | 350 | `utcnow()` | `_now_sp()` |
| `home()` — all_past | 361 | `utcnow()` | `_now_sp()` |
| `historico()` | 568 | `utcnow()` | `_now_sp()` |

**NÃO mudam** (carimbos internos, consistentes em UTC): `terms_accepted_at`, `replaced_at`,
`edited_at`, `detail_submitted_at`, reset de senha (linhas 113, 300, 303, 811, 853, 882).

### 3. Trava no servidor
- Helper `_event_ended(event) -> bool`: `(event.end_at or event.start_at) < _now_sp()`
  (False se sem datas).
- `rate_event` (GET), `submit_rating` (POST) e `rate_event_detail` (GET/POST): se não terminou →
  `flash("A avaliação abre depois que o evento terminar.", "error")` + redirect ao portal home.

### 4. Verificação
- `ruff check` no arquivo; boot.
- Test client (sessão do portal): evento terminando em +2h → não listado em "avaliar", GET da tela →
  redirect com aviso, POST → nada gravado; evento terminado há 1h → listado, POST grava; evento
  começando em +2h continua em próximos; janela de 7/30 dias inalterada (evento de 10 dias atrás não
  avaliável; avaliado há 10 dias ainda editável).

## Project Structure
```text
app/talent_portal/routes.py   # _now_sp, _event_ended, trocas de utcnow, travas nas rotas de rating
```

## Fora de escopo
- Mudar carimbos internos para Brasília (consistência UTC mantida).
- Outras telas fora do portal (calendar/financeiro já usam Brasília).
