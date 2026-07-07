# Implementation Plan: Atualizar "Já Trabalhou com a Manto" Automaticamente (115)

**Branch**: `115-atualizar-ja-trabalhou` | **Date**: 2026-07-07 | **Spec**: [spec.md](./spec.md)

## Summary

`sync_events()` (função central de sincronização — usada pelo botão "Sincronizar agora", pela
thread automática de calendário e pelo sync de um evento individual) ganha um passo final:
`_mark_talents_worked()`. A função busca `talent_id` distintos de `EventRole` cujo evento não
é Ensaio, já passou (`end_at` ou, na falta, `start_at`), e cujo convite não foi recusado, e
liga `Talent.worked_before = True` para quem ainda não estava marcado. Nenhuma coluna nova,
nenhuma thread nova — reaproveita o ciclo de sync já existente (~600s).

## Technical Context

**Stack**: o existente. **Storage**: zero migration (usa a coluna `worked_before` já
existente em `Talent`).

**Arquivos**: `app/calendar/routes.py` (`_mark_talents_worked()`, chamada ao fim de
`sync_events()`).

**Testing**: script test client vs manto_local — talento com evento passado e convite não
recusado liga automaticamente; evento futuro não liga; convite recusado não liga; Ensaio não
liga; talento já `True` permanece `True` (idempotência/não regressão); edição manual
continua funcionando.

## Constitution Check

| Princípio | Avaliação |
|---|---|
| I. Reutilizar | ✅ Hook dentro da função de sync já existente — sem thread, migration ou tela novas. |
| II. Padrões Python | ✅ Função com docstring explicando a regra de "realizou". |
| III. Camadas | ✅ Lógica de negócio centralizada num único helper, chamado de um único ponto. |
| IV. Não quebrar | ✅ `sync_events()` continua com o mesmo comportamento para roles/eventos; a marcação só ADICIONA um efeito colateral aditivo (liga, nunca desliga). |
| V. UI/UX | N/A — automação silenciosa, sem tela nova; filtro existente já lê o campo. |
| VI. Planejar | ✅ Este plano. |
| VII. Moeda BR | N/A. |

**Gate: PASS.**

## Decisões

1. **Hook em `sync_events()`, não thread nova**: essa função já é chamada por todo caminho
   que toca a agenda (manual, automático, por evento) — um único ponto cobre os três.
2. **`end_at` com fallback em `start_at`**: eventos sem hora de término registrada ainda
   contam como "passados" pelo início, evitando falso negativo por dado incompleto.
3. **Convite `NULL` conta como trabalhado**: fluxos antigos sem registro de convite não
   podem ficar de fora; só `"rejected"` explicitamente exclui.
4. **UPDATE em massa com `.isnot(True)`**: idempotente e nunca desliga uma marcação (FR-002),
   inclusive preservando correções manuais para "Sim".
