# Implementation Plan: Cliente na Criação de Evento + Busca sem Acentos (114)

**Branch**: `114-cliente-criar-evento-busca-sem-acento` | **Date**: 2026-07-06 | **Spec**: [spec.md](./spec.md)

## Summary

O editor de clientes do evento (features 094/100, hoje um script inline em
`event_detail.html`) vira componente compartilhado `app/static/js/client_picker.js`
(mesmo IIFE keyed em `#clients-block`, com a exigência de cliente controlada por
`data-required` em vez de Jinja). `event_create.html` ganha o mesmo bloco no começo do
formulário; o POST de criação passa a persistir `client_id[]`/`client_relation[]` via helper
compartilhado `_parse_client_pairs()` (extraído de `_handle_update_sale`), incluindo o
`client_id` denormalizado; erro de validação re-renderiza com os clientes preservados
(`old_clients`). Busca sem acentos: helpers `strip_accents_lower()` (Python) e
`unaccent_lower_sql()` (SQL `translate(lower(col), …)`, sem extensão) em `app/utils.py`,
aplicados em `/clientes/search` e na busca da lista `/clientes/`.

## Technical Context

**Stack**: o existente; **Storage**: zero migration (translate SQL dispensa a extensão
`unaccent` — funciona em qualquer Postgres).

**Arquivos**: `app/static/js/client_picker.js` (novo, extraído), `app/templates/
event_detail.html` (script inline → include + `data-required`), `app/templates/
event_create.html` (bloco no topo + include + `old_clients`), `app/calendar/routes.py`
(`_parse_client_pairs()` compartilhado; POST/GET/erros do create), `app/utils.py`
(helpers de acento), `app/clientes/routes.py` (search + lista).

**Testing**: test client vs manto_local — busca com/sem acento (2 sentidos + telefone),
criar evento com clientes (EventClient + client_id primário; `insert_event` do Google
monkeypatched no teste), erro de validação preserva seleção, página do evento continua com
o bloco/script (regressão FR-006).

## Constitution Check

| Princípio | Avaliação |
|---|---|
| I. Reutilizar | ✅ Componente único (JS extraído, não copiado); parsing de clientes vira helper usado pelos dois fluxos; busca corrigida na fonte única `/clientes/search`. |
| II. Padrões Python | ✅ Helpers com docstring/type hints em `utils.py`. |
| III. Camadas | ✅ Normalização de acento em utils; rotas só aplicam. |
| IV. Não quebrar | ✅ `_handle_update_sale` mantém o mesmo comportamento (só extrai o parsing); busca continua aceitando telefone; verificação cobre a página do evento. |
| V. UI/UX | ✅ Mesma UI já conhecida; seleção preservada em erro de validação. |
| VI. Planejar | ✅ Este plano. |
| VII. Moeda BR | ✅ N/A. |

**Gate: PASS.**

## Decisões

1. **`translate(lower(col))` em vez da extensão `unaccent`**: zero migration, funciona em
   qualquer Postgres (local e Railway); tabela de acentos espelhada no Python
   (`strip_accents_lower` via NFD) para normalizar o termo digitado.
2. **`data-required` no lugar do Jinja `client_required`**: o JS vira arquivo estático
   compartilhável; `event_detail` seta o atributo quando a exigência vale; criação não seta
   (campo opcional — FR-005).
3. **Cliente opcional na criação**: não trava a criação de eventos operacionais; a exigência
   da feature 094 continua no save da venda.
4. **`old_clients` no re-render de erro**: POST com erro busca os clientes selecionados e
   devolve ao template (linhas pré-montadas no bloco) — FR-003.
