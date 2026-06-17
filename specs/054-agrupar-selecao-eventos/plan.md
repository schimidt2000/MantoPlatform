# Implementation Plan: Seleção de eventos no agrupamento (busca + multi-seleção)

**Branch**: `054-agrupar-selecao-eventos` | **Date**: 2026-06-16 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/054-agrupar-selecao-eventos/spec.md`

## Summary

Melhorar **apenas a etapa de seleção** do agrupamento de eventos (feature 053). Hoje o
seletor mostra só eventos em uma janela de ±3 dias e agrupa um por vez. Esta feature:
remove a janela de data, carrega todos os eventos elegíveis, adiciona uma **busca em tempo
real no cliente** (reaproveitando o padrão de `pagamentos.html` da feature 045) e permite
marcar **vários eventos por checkbox** e agrupá-los numa só confirmação, escolhendo qual é
o principal. O modelo de dados, as regras de negócio e os efeitos do agrupamento
permanecem os da 053 — sem migration, sem nova entidade.

## Technical Context

**Language/Version**: Python 3.11, Flask + SQLAlchemy (Jinja2 + HTML/CSS/JS vanilla)

**Primary Dependencies**: Flask, SQLAlchemy, Flask-Login (RBAC). Nenhuma dependência nova.

**Storage**: SQLite (dev) / PostgreSQL (prod). **Sem mudança de schema** — reutiliza
`CalendarEvent.group_leader_id` e o relacionamento `satellites`/`group_leader` da 053.

**Testing**: Sem suíte automatizada no projeto (`pytest`/`conftest.py` inexistentes) —
verificação manual via `quickstart.md`, como nas features 051/052/053.

**Target Platform**: App web (Railway/produção), mobile-first.

**Project Type**: Web application (Flask monolito: `app/calendar/routes.py` +
`app/templates/event_detail.html`).

**Performance Goals**: Busca filtra a lista em <1s (percepção de tempo real) com centenas
de eventos — viável no cliente sem requisição ao servidor.

**Constraints**: Mobile-first; busca acento-insensível; prevenir envio duplicado; não
perder a seleção do usuário em erro; textos pt-BR.

**Scale/Scope**: Ordem de centenas de eventos cadastrados; 1 rota tocada, 1 handler
estendido, 1 template editado, 0 migrations.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **I. Reutilizar antes de criar (NÃO-NEGOCIÁVEL)**: ✅ Estende o handler
  `_handle_group_events` e `_apply_satellite` já existentes (053); reaproveita o padrão de
  busca client-side acento-insensível de `app/templates/financeiro/pagamentos.html`
  (feature 045) e o `EventLog` para auditoria. Nenhuma lógica nova paralela.
- **II. Padrões Python**: ✅ Type hints + docstrings; handler estendido mantém-se pequeno,
  extraindo a validação por evento em helper se necessário (≤30 linhas/função, ≤3 níveis).
- **III. Arquitetura em camadas**: ✅ A rota `event_detail` só monta a lista de candidatos
  e renderiza; a regra (validar e agrupar) fica no handler `_handle_group_events`.
- **IV. Não quebrar o que funciona (NÃO-NEGOCIÁVEL)**: ✅ O resultado final é idêntico ao
  da 053 (FR-012). O caminho de 1 evento continua funcionando como caso particular de N=1.
  Verificação no app real prevista no quickstart.
- **V. UI/UX com feedback (pt-BR)**: ✅ Botão de agrupar desabilita ao enviar (anti-duplo
  envio); validação client-side (≥1 marcado + principal escolhido) com destaque, sem
  bloquear em silêncio; eventos já agrupados aparecem desabilitados (não selecionáveis),
  evitando erro de servidor e perda de seleção (FR-010); confirmação destrutiva mantida.
  Cores via variáveis CSS.
- **VI. Planejar antes de codar**: ✅ Este plano.
- **VII. Valores monetários BR (NÃO-NEGOCIÁVEL)**: ✅ Não há novo valor monetário exibido
  na lista de candidatos (só título + data/horário). Sem impacto.

**Resultado**: PASS — nenhuma violação. Complexidade adicional: nenhuma.

## Project Structure

### Documentation (this feature)

```text
specs/054-agrupar-selecao-eventos/
├── plan.md              # Este arquivo
├── spec.md              # Especificação (já criada)
├── research.md          # Fase 0 — decisões técnicas
├── data-model.md        # Fase 1 — confirma "sem mudança de modelo"
├── quickstart.md        # Fase 1 — roteiro de verificação manual
├── contracts/
│   └── group-events.md  # Fase 1 — contrato da ação group_events (multi-seleção)
└── checklists/
    └── requirements.md  # Checklist de qualidade do spec (já criado)
```

### Source Code (repository root)

```text
app/
├── calendar/
│   └── routes.py                 # event_detail: lista de candidatos (remove janela ±3d);
│                                 # _handle_group_events: aceita N eventos (target_event_ids[])
└── templates/
    └── event_detail.html         # seção "Agrupar": busca + checkbox list + escolha do principal
```

**Structure Decision**: Monolito Flask existente. A feature toca exatamente 2 arquivos
(`app/calendar/routes.py` e `app/templates/event_detail.html`). Sem novos módulos, sem
migration, sem mudança em `app/models.py` nem em `app/financeiro/routes.py` (o painel
financeiro já trata o grupo corretamente desde a 053).

## Complexity Tracking

> Sem violações de constituição — seção não aplicável.
