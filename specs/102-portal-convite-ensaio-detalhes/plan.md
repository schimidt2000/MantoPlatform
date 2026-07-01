# Implementation Plan: Convite do portal — detalhes de evento e ensaio bem organizados

**Branch**: `102-portal-convite-ensaio-detalhes` | **Date**: 2026-07-01 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/102-portal-convite-ensaio-detalhes/spec.md`

## Summary

Melhorar a exibição no **portal do artista** (`portal/home.html`): (1) exibir o **fim do ensaio** (o
dado já existe), (2) organizar cada ensaio em linhas **rotuladas** (Data do ensaio / Horário do ensaio
início–fim / Local do ensaio), (3) rotular as linhas do **evento** como "do evento" e mostrar o **Local
com o endereço completo**. Aplicar o fim do ensaio também aos cartões de **próximos eventos**. Mudança
**apenas de template** — sem modelo/migração.

## Technical Context

**Language/Version**: Jinja2 (template) + CSS inline; sem Python novo.

**Primary Dependencies**: Nenhuma nova.

**Storage**: N/A (sem alteração de dados). O ensaio já tem `start_at`/`end_at`/`location`; o evento tem
`start_at`/`end_at`/`location`.

**Testing**: Render do `portal/home.html` (Jinja parse) + verificação visual/manual dos casos (com/sem
fim, com/sem local, vários ensaios).

**Constraints**: Não alterar o fluxo de aceitar/recusar nem outras seções. Manter observação/materiais
do ensaio. Omitir linhas vazias (local do evento/ensaio).

**Scale/Scope**: 1 arquivo de template (`app/templates/portal/home.html`) — bloco de convite pendente e
bloco de próximos eventos.

## Constitution Check

- **Sem duplicação**: reutiliza o padrão de `invite-detail-row` já usado pelo evento para o ensaio. ✅
- **Não quebrar**: só reorganiza exibição; dados intactos. ✅
- **Sem migração/segredos**. ✅

Resultado: PASS.

## Project Structure

```text
app/templates/portal/home.html   # bloco convite pendente + bloco próximos eventos
```

**Structure Decision**: Puramente apresentação. No convite pendente, rotular o evento como "Data do
evento / Horário do evento / Local do evento" e transformar o bloco do ensaio em linhas rotuladas (Data
do ensaio / Horário do ensaio início–fim / Local do ensaio) + observação/materiais. Nos próximos
eventos, incluir o fim do ensaio.

## Implementation Approach

1. **Convite pendente — evento**: renomear rótulos para "Data do evento", "Horário do evento", "Local do
   evento"; manter Local exibindo `ev.location` completo (omitido se vazio).
2. **Convite pendente — ensaio**: para cada ensaio, exibir linhas rotuladas:
   - "🎭 Ensaio" (cabeçalho do bloco),
   - Data do ensaio (`start_at` data),
   - Horário do ensaio (`start_at` – `end_at`, ou só início se sem fim),
   - Local do ensaio (`location`, omitido se vazio),
   - observação (`description`) e materiais, como hoje.
3. **Próximos eventos — ensaio**: incluir o fim do ensaio (início–fim) e manter o estilo compacto.
4. **Verificação** (Jinja parse + casos com/sem fim/local, vários ensaios).

## Complexity Tracking

> Sem violações de constituição. Mudança mínima de template.
