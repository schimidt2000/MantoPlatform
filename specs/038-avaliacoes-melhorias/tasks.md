# Tasks: Avaliações robustas (filtros, navegação e insights)

**Input**: `specs/038-avaliacoes-melhorias/`
**Tests**: boot + ruff + test client (combinações de filtros). Sem migration.

## Phase 1: Backend (rota)
- [x] T001 `app/talents/routes.py`: helper `_parse_period()` + leitura/validação de `cat`, `period`,
      `from`, `to` (inválidos → fallback); base de ratings com join em CalendarEvent por período.
- [x] T002 Recorte por categoria: scores/dist/comentários de `EventSubRating` quando `cat` ativo;
      manter visão geral atual quando não.
- [x] T003 Seletor agrupado por mês (`event_groups`); comentários unificados (geral + categoria, com
      `cat_label` e `subject_name`); ranking best/worst; pontos de atenção (≤2, limite 10); tendência
      mensal (média + contagem).

## Phase 2: Template
- [x] T004 `avaliacoes.html`: barra de filtros (período com atalhos + personalizado, categoria,
      evento com optgroup por mês, limpar filtros), auto-submit, filtros preservados na URL.
- [x] T005 Painéis novos: tendência (barras CSS), ranking melhores/piores (links preservando `cat`),
      pontos de atenção (estado positivo quando vazio); chips de categoria nos comentários; KPIs com
      rótulo do recorte; estados vazios com limpar filtros.

## Phase 3: Verificação
- [x] T006 `ruff check` + boot + test client: sem filtros; `cat=figurino`; `period=30d`; custom
      de/até; `event_id`+`cat`; inválidos (200, fallback); sem permissão → 403. Conferir optgroup,
      etiquetas e painéis no HTML.

## Dependencies
- T001 → T002 → T003 → T004/T005 → T006.

## Notes
- Sem migration; tudo agregação em leitura. URL antiga `?event_id=` continua válida.
- Visão por evento ignora `period`; `cat` vale em todas as visões.
