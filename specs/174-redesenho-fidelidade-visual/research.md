# Research: Redesenho e Fidelidade Visual das Telas Principais

## R1 — Donuts: CSS puro vs. Recharts

**Decision**: CSS puro (`conic-gradient` via custom property), replicando a técnica já usada em
`app/templates/home.html` (`.donut { --p: Xdeg; background: conic-gradient(...) }`).

**Rationale**: os únicos donuts pedidos (Casting %, Figurino %) são gráficos de 1 série cada
(percentual concluído/pendente) — exatamente o caso de uso onde CSS puro é suficiente e mais
leve. Adicionar Recharts como dependência nova ao `apps/internal/package.json` custaria ~90kb
(gzip) para 2 elementos visuais simples, sem ganho de interatividade real pedido pela spec
(sem tooltip/múltiplas séries no requisito). Manteria menos superfície de manutenção (sem SVG
runtime, sem re-render de biblioteca externa) e paridade 1:1 com o visual clássico.

**Alternatives considered**:
- **Recharts `<PieChart>` com `innerRadius`**: rejeitado por ora — custo de dependência não
  compensa para 2 séries simples; reavaliar se uma fase futura pedir donuts multi-série (ex.:
  distribuição de vendas por categoria) onde CSS puro não escala.
- **SVG manual (`<circle stroke-dasharray>`)**: equivalente em peso ao CSS puro, mas exige mais
  código para animar o traço; `conic-gradient` já anima suavemente via `transition` no custom
  property com suporte a `@property` ou via Framer Motion controlando o valor numérico.

## R2 — "Distribuição financeira/status" do pedido original

**Decision**: interpretar como o painel "Performance" do Jinja clássico (SUPERADMIN-only):
seletor de período (7/30/customizado) + Casting done/total + Figurino done/total + "Entrada
total" (soma de cachês no período).

**Rationale**: leitura de `app/templates/home.html` (linhas ~673–708) e `app/__init__.py`
(linhas ~528–576) confirma que não existe, no sistema clássico, um gráfico de "distribuição
financeira" na home — a única peça financeira ali é esse painel de KPIs textuais. Fidelidade
visual (o objetivo desta FASE B) significa restaurar o que existia, não inventar uma métrica
nova. "Status" mapeia para os donuts de Casting/Figurino (R1); "financeira" mapeia para
"Entrada total" do Performance.

**Alternatives considered**:
- **Gráfico de pizza com receita/despesa/lucro**: rejeitado — essa visão já existe, completa e
  correta, no Dashboard financeiro (`/financeiro`, feature 157/`FinanceiroDashboardPage.tsx`);
  duplicá-la na home criaria duas fontes da mesma métrica (viola Princípio I).

## R3 — Extensão do contrato de `/api/dashboard`

**Decision**: extensão aditiva — `GET /api/dashboard?perf_range=7|30|custom&perf_start=...&
perf_end=...`, resposta ganha `"performance": {...} | null`. Nenhum campo existente muda de
formato.

**Rationale**: `build_dashboard_summary()` já é a fonte única usada por `home()` (Jinja, via
migração futura) e pela API — mas hoje o `perf_*` só existe inline em `app/__init__.py`,
duplicando (em espírito) o padrão que `dashboard_service.py` já resolveu para
casting/figurino/financeiro. Extrair para `compute_performance(cutoff, start_dt, end_dt)` e
`compute_comercial_pending(cutoff)` fecha essa lacuna, seguindo o mesmo padrão do resto do
arquivo.

**Alternatives considered**:
- **Endpoint novo `/api/dashboard/performance`**: rejeitado — o Performance é parte do mesmo
  agregado de tela (mesma call site, mesmo ciclo de vida de query), não um recurso
  independente; um segundo endpoint obrigaria 2 round-trips onde 1 com parâmetro basta.
- **Calcular client-side a partir de dados já existentes**: inviável — `/api/dashboard` hoje
  não retorna `EventRole`/`CalendarEvent` cru (só resumos serializados), e trazer todos os
  registros do período para o cliente agregar seria pior (payload maior, lógica de negócio no
  front). A agregação deve continuar no backend.

## R4 — Cor de categoria de evento na Agenda

**Decision**: mapear `event_type` para cor seguindo `app/templates/event_detail.html`:
`R&I`/`RI` → azul, `SHOW` → dourado, `CORP` → cinza, `VM` → azul, `SOCIAL` → verde, `ENSAIO` →
laranja (paridade com o prefixo visual "🟧 ENSAIO" usado em títulos), qualquer outro valor →
cinza neutro (fallback, nunca quebra o bloco).

**Rationale**: é o único mapeamento cor↔categoria que já existe no sistema; replicá-lo garante
que o time reconheça as mesmas cores que já associa a cada tipo de evento.

**Alternatives considered**: gerar uma paleta nova por categoria — rejeitado, quebraria a
associação mental já treinada pelo uso diário do Jinja.

## R5 — Estrutura de dados para a grade de calendário

**Decision**: `CalendarGrid` recebe `events: EventoResumo[]` e `ym: string` (já buscados por
`useAgenda`) e monta a grade internamente (semanas completas, incluindo dias adjacentes
esmaecidos), indexando eventos por `start_at.slice(0,10)` — o mesmo agrupamento por dia que
`AgendaPage.tsx` já faz hoje (`groups` via `useMemo`), só que alimentando células de uma grade
em vez de seções de lista.

**Rationale**: `AgendaMes.by_day: Record<string, number[]>` já existe no tipo, mas mapeia para
IDs — reindexar os próprios objetos `EventoResumo` (já carregados) evita um segundo lookup;
mais simples manter a mesma técnica de agrupamento já usada na página, só trocando o
componente de apresentação.

**Alternatives considered**: usar uma lib de calendário (`react-big-calendar`, `FullCalendar`)
— rejeitada por peso de dependência e customização de tema mais difícil que uma grade CSS
própria para o caso (visão de mês única, sem drag-and-drop pedido).

## R6 — Mosaico de Talentos

**Decision**: novo componente `TalentMosaic` recebe a mesma lista `TalentSummary[]` já retornada
por `useTalentDirectory`, sem mudança de hook/endpoint; troca apenas a apresentação por card
(foto grande em vez de avatar 64px, badges de medida sempre visíveis).

**Rationale**: `TalentSummary` já tem todos os campos necessários (`photo_face_path`,
`height_cm`, `clothing_size_top`, `shoe_size`, `warning_level`) — nenhuma extensão de contrato
necessária.

**Alternatives considered**: nenhuma — a spec já pede explicitamente reaproveitar o endpoint.
