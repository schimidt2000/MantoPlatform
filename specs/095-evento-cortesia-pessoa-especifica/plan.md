# Implementation Plan: Evento cortesia/permuta e pessoa específica na criação

**Branch**: `095-evento-cortesia-pessoa-especifica` | **Date**: 2026-06-30 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/095-evento-cortesia-pessoa-especifica/spec.md`

## Summary

Duas adições à **tela de criação de evento** (`/events/new`), sem novo modelo nem migração:

1. **Cortesia/permuta**: expor na criação a marcação `is_cortesia_permuta` (campo já existente no
   `CalendarEvent`). Quando marcada, relaxar as validações que hoje exigem valor (>0) e salvar com
   `sale_value = 0` + `is_cortesia_permuta = True` — espelhando o que `_handle_update_comercial` já faz
   na página do evento.
2. **Pré-escala de pessoa específica** (do Banco de Talentos): por personagem e para o Coordenador, o
   vendedor pode escolher um talento; a vaga (`EventRole`) nasce **com `talent_id` atribuído** (+
   `assigned_at`), **sem** convite automático. Conflitos de agenda são **sinalizados** (flash), não
   bloqueiam.

204 talentos (todos `active`) → o seletor é um **autocomplete embutido** no form (JSON pequeno), sem
endpoint novo.

## Technical Context

**Language/Version**: Python 3.x (Flask), Jinja2, JS vanilla

**Primary Dependencies**: Flask, SQLAlchemy (nenhuma nova)

**Storage**: PostgreSQL (prod) / SQLite (dev). **Sem migração** — reusa `CalendarEvent.is_cortesia_permuta`
e `EventRole.talent_id`/`assigned_at`. Testar contra `manto_local`.

**Testing**: pytest/scripts contra `manto_local`. Casos: criação cortesia sem valor (venda=0); venda
normal ainda exige valor; vaga nasce atribuída quando talento escolhido e aberta quando não; conflito
sinalizado.

**Target Platform**: Web (área comercial)

**Project Type**: Web app (monolito Flask + templates Jinja2)

**Constraints**: Não enviar convite automático na pré-escala (casting controla). Conflito é informativo.
Reaproveitar a lógica de conflito existente (extrair helper). Manter o fluxo de orçamento intacto.

**Scale/Scope**: Mudanças em `app/calendar/routes.py` (rota `create_event` + 1 helper de conflito) e
`app/templates/event_create.html` (checkbox cortesia + seletor de talento por linha + coordenador).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Sem duplicação**: cortesia reusa a lógica/campo já existentes; pré-escala reusa `talent_id`/
  `assigned_at` e o fluxo de convite; conflito extrai helper a partir do bloco já existente. ✅
- **Separação de responsabilidades**: validação/montagem na rota; seleção no template. ✅
- **Sem migração/segredos novos**. ✅
- **Não quebrar o que funciona**: validações de venda normal preservadas; vaga sem seleção continua
  aberta; orçamento intacto. ✅

Resultado: PASS.

## Project Structure

### Documentation (this feature)

```text
specs/095-evento-cortesia-pessoa-especifica/
├── spec.md
├── plan.md
├── tasks.md
└── checklists/requirements.md
```

### Source Code (repository root)

```text
app/
├── calendar/routes.py        # EDIT create_event: cortesia (validação+save), char_talent_id[],
│                             #   coordinator_talent_id, pré-escala em EventRole, flash de conflito;
│                             #   ADD helper _talent_time_conflict(...)
└── templates/
    └── event_create.html     # EDIT: checkbox cortesia/permuta + JS toggle de obrigatoriedade;
                              #   seletor de talento por personagem; seletor de coordenador específico
```

**Structure Decision**: Tudo dentro do fluxo de criação existente. Sem novo blueprint/modelo. O seletor
de talento é alimentado por uma lista `talents` (id+nome) já passada ao template (ou adicionada ao
contexto do GET), renderizada como autocomplete embutido.

## Implementation Approach

1. **Cortesia/permuta (US1)**
   - Template: checkbox `is_cortesia_permuta` na seção de venda; JS marca os campos de valor como não
     obrigatórios e dá feedback visual quando ligado.
   - Rota: ler `is_cortesia_permuta`; se ligado, **pular** os erros "informe o valor antes do desconto/
     valor de venda" e setar `sale_value=0`, `is_cortesia_permuta=True` (e `sale_value_gross` 0/None).
2. **Pré-escala de artista (US2)**
   - Template: por linha de personagem, um seletor de talento (autocomplete da lista embutida) que
     preenche `char_talent_id[]` alinhado a `character_names[]`.
   - Rota: ao criar cada `EventRole`, se houver `char_talent_id[i]` válido → `talent_id` + `assigned_at`
     (invite_status fica None).
3. **Pré-escala de coordenador (US3)**
   - Template: seletor "Coordenador específico".
   - Rota: ao garantir o coordenador, se `coordinator_talent_id` válido → criar a vaga "Coordenador"
     (extra) já com `talent_id` + `assigned_at` (ajustar `_ensure_coordinator` ou criar antes dele).
4. **Conflito (FR-010)**: extrair `_talent_time_conflict(talent_id, start, end, exclude_event_id)` a
   partir do bloco existente (linhas ~1352-1363) e, após criar, **flash** de aviso listando talentos
   pré-escalados com conflito. Não bloqueia.

## Complexity Tracking

> Sem violações de constituição. Nenhuma complexidade extra a justificar.
