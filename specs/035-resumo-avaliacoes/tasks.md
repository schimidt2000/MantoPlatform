# Tasks: Página de resumo das avaliações

**Input**: `specs/035-resumo-avaliacoes/`
**Tests**: boot + ruff + render do template + verificação no app. Sem migration.

## Phase 1: Rota/agregação
- [x] T001 `app/talents/routes.py`: `avaliacoes()` em `GET /talents/avaliacoes?event_id=` — acesso
      SUPERADMIN/CASTING; lista de eventos avaliados; agrega total, média geral, eventos avaliados,
      distribuição 1..5, média por categoria, comentários (geral ou por evento).

## Phase 2: Template
- [x] T002 `app/templates/talents/avaliacoes.html` (novo): seletor de evento; cards; distribuição em
      barras; médias por categoria em barras + estrelas; lista de comentários; estado vazio; macro de
      estrelas. Paleta via variáveis CSS.

## Phase 3: Navegação
- [x] T003 `app/templates/base.html`: item "Avaliações" no menu (ativo em /talents/avaliacoes).

## Phase 4: Verificação
- [x] T004 boot + `ruff check` + render do template. Cenários: visão geral (métricas/categorias);
      por evento (médias + comentários); estado vazio; acesso negado a papel sem permissão.

## Dependencies
- T001 → T002 → T003 → T004.

## Notes
- Só leitura/agregação de EventRating + EventSubRating. Sem migration.
