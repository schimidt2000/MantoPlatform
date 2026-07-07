# Implementation Plan: Marcar Evento como Confirmado (116)

**Branch**: `116-confirmar-evento` | **Date**: 2026-07-07 | **Spec**: [spec.md](./spec.md)

## Summary

`CalendarEvent` ganha `confirmed_at` (DateTime, nullable) e `confirmed_by_id` (FK users,
nullable) — mesmo padrão de `dismissed_at`/`dismissed_by` (feature 108). Botão único e
simples na página do evento, ao lado de "✅ Confirmar dados do evento": alterna entre
"Marcar evento como confirmado" e "✓ Confirmado por X em DD/MM — desfazer", via
`POST /events/<id>/toggle-confirmado`, restrito a COMERCIAL/SUPERADMIN, com `EventLog` de
auditoria (padrão de `_handle_toggle_contract_signed`).

## Technical Context

**Stack**: o existente. **Storage**: 1 migration manual (2 colunas em `calendar_events`).

**Arquivos**: `app/models.py` (2 colunas + relationship), migration nova,
`app/calendar/routes.py` (rota toggle), `app/templates/event_detail.html` (botão +
indicador ao lado do "Confirmar dados do evento").

**Testing**: test client vs manto_local — marcar liga com autor/data; desfazer limpa;
persiste após reload; RBAC (403 fora de COMERCIAL/SUPERADMIN); log de auditoria criado.

## Constitution Check

| Princípio | Avaliação |
|---|---|
| I. Reutilizar | ✅ Segue exatamente o padrão de `dismissed_at`/`dismissed_by` (108) e do toggle de contrato assinado (`_handle_toggle_contract_signed`) — RBAC, EventLog, redirect de volta ao evento. |
| II. Padrões Python | ✅ Type hints/docstring na rota nova. |
| III. Camadas | ✅ Rota só orquestra; nada de regra de negócio nova fora do padrão do módulo. |
| IV. Não quebrar | ✅ Coluna nova nullable, sem tocar em nada existente; botão "Confirmar dados" (cópia de mensagem) intocado. |
| V. UI/UX | ✅ Botão muda de rótulo/cor conforme o estado; ação simples sem modal (mesmo padrão do toggle de contrato); flash de sucesso. |
| VI. Planejar | ✅ Este plano. |
| VII. Moeda BR | N/A. |

**Gate: PASS.**

## Decisões

1. **Toggle único, não dismiss/restore separado**: ação simples e reversível — uma rota
   `POST /events/<id>/toggle-confirmado` alterna o estado, como o toggle de contrato
   assinado já existente (mesmo módulo, mesmo padrão).
2. **RBAC = COMERCIAL/SUPERADMIN**: igual ao bloco onde o botão "Confirmar dados" já vive
   (FR-004).
3. **Sem indicador na agenda**: fora do pedido explícito ("em cada evento" = página do
   evento); registrado como assumption, não implementado.
