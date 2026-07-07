# Implementation Plan: Botão "Editar no Google Agenda" (117)

**Branch**: `117-editar-evento-google` | **Date**: 2026-07-07 | **Spec**: [spec.md](./spec.md)

## Summary

Toda resposta da API do Google Calendar já vem com `htmlLink` — link direto pro evento no
site do Google Calendar — mas o sistema descarta esse campo hoje. `CalendarEvent` ganha
`google_html_link` (String, nullable), capturado em `sync_events()` (tanto ao criar quanto ao
atualizar um evento) a partir de `item.get("htmlLink")`. A página do evento ganha o botão
"Editar no Google Agenda" (`<a target="_blank">`), visível só para COMERCIAL/SUPERADMIN e só
quando `event.google_html_link` está preenchido. Nenhuma escrita nova para o Google — só
leitura de um campo que a API já devolve.

## Technical Context

**Stack**: o existente. **Storage**: 1 migration manual (1 coluna em `calendar_events`).

**Arquivos**: `app/models.py` (coluna nova), migration nova, `app/calendar/routes.py`
(captura de `htmlLink` nos dois branches de `sync_events()`), `app/templates/
event_detail.html` (botão condicional por papel + presença do link).

**Testing**: chamar `sync_events()` com um item simulando `htmlLink` do Google e conferir
que o campo é persistido (criação e atualização); RBAC do botão (visível pra COMERCIAL/
SUPERADMIN, oculto pros demais); botão ausente quando `google_html_link` é `None`.

## Constitution Check

| Princípio | Avaliação |
|---|---|
| I. Reutilizar | ✅ Usa o mesmo payload que a API do Google já devolve em `sync_events()` — nenhuma chamada nova à API, nenhuma lib nova. |
| II. Padrões Python | ✅ Coluna com comentário explicando a origem do dado. |
| III. Camadas | ✅ Captura no único ponto que já processa o payload do Google; template só lê o campo. |
| IV. Não quebrar | ✅ Coluna nova nullable; nenhuma mudança em campos/comportamento existentes de `sync_events()`; sem escrita nova ao Google (mantém a decisão de "Google é fonte da verdade"). |
| V. UI/UX | ✅ Botão só aparece quando o link existe — sem link quebrado; abre em nova aba (não perde o contexto do Manto). |
| VI. Planejar | ✅ Este plano + decisão discutida em conversa antes do spec. |
| VII. Moeda BR | N/A. |

**Gate: PASS.**

## Decisões

1. **Persistir `htmlLink`, não construir a URL na mão**: o formato do link do Google usa um
   `eid` codificado que não é documentado como estável para construção manual — usar
   exatamente o que a API devolve evita link quebrado.
2. **Botão oculto sem o link, não desabilitado**: mais simples e sem exigir texto de
   explicação; o link aparece sozinho após a próxima sincronização (automática ou manual).
3. **RBAC igual ao dos outros botões comerciais da página** (COMERCIAL/SUPERADMIN) — mesmo
   grupo que já vê "Confirmar dados do evento" e o botão de confirmar evento (116).
4. **Zero escrita nova para o Google**: mantém a política discutida — o Manto não passa a
   editar data/hora/local; só facilita o caminho até onde isso já deveria ser feito.
