# Tasks: Botões de mensagem no evento (083)

**Feature**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)

Sem testes automatizados solicitados — verificação manual contra `manto_local`.

## Phase 1: Setup

- [X] T001 Confirmar dados disponíveis em `event_detail()` (título, start/end, location, installments,
  payment_due_date, sale_value, received_total) em `app/calendar/routes.py`.

## Phase 2: User Story 1 — Confirmar dados do evento (P1) 🎯 MVP

- [X] T002 [US1] Adicionar helper `_format_event_date_ptbr(start_at, end_at) -> str` (dia da semana e
  mês por extenso pt-BR + faixa de horário) em `app/calendar/routes.py`.
- [X] T003 [US1] Em `event_detail()`, computar e passar ao template: `confirm_characters`
  (`" + ".join(parse_characters(event.title))`), `confirm_date_line`
  (`_format_event_date_ptbr(...)`), `confirm_location` (`event.location`) em `app/calendar/routes.py`.
- [X] T004 [US1] Adicionar botão "Confirmar dados do evento" no bloco `page_actions` (só COMERCIAL/
  SUPERADMIN) e o `<script>` que monta a mensagem com saudação por horário e copia para a área de
  transferência com feedback "✅ Copiado!" em `app/templates/event_detail.html`.

## Phase 3: User Story 2 — Cobrança no vencimento/atraso (P2)

- [X] T005 [US2] Em `event_detail()`, computar `cobranca_enabled` (bool), `cobranca_amount`
  (formatado pt-BR "R$ x.xxx,xx") e `cobranca_due_line` (data limite formatada), via parcelas em
  aberto ou `payment_due_date`+`sale_value`−`received_total`, em `app/calendar/routes.py`.
- [X] T006 [US2] Adicionar botão "Cobrança" no `page_actions` (só COMERCIAL/SUPERADMIN): desabilitado e
  translúcido quando `not cobranca_enabled` (com tooltip), e, quando habilitado, montar/copiar a
  mensagem de cobrança com o valor em aberto em `app/templates/event_detail.html`.

## Phase 4: Polish & Verificação

- [X] T007 Verificar contra `manto_local`: saudação nos 3 períodos, personagens sem prefixo, data
  pt-BR, local omitido quando vazio; cobrança habilitada só com vencimento/atraso + saldo e valor
  correto. Rodar `ruff` (sem erros novos).

## Dependencies

- T002 → T003 → T004 (US1, sequencial; mesmo arquivo/route).
- T005 → T006 (US2).
- US1 e US2 tocam os mesmos dois arquivos → executar em sequência, não em paralelo.
- T007 por último.

## MVP

User Story 1 (botão de confirmação) é o MVP entregável isolado.
