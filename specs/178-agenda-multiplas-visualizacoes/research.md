# Phase 0 Research: Agenda com múltiplas visualizações

Nenhum `NEEDS CLARIFICATION` restou no Technical Context — as decisões abaixo documentam as
escolhas feitas durante a exploração do código existente, não incertezas em aberto.

## 1. Fonte de dados para a visão Dia

- **Decision**: usar o hook já existente `useAgendaDia(date)` (`frontend/apps/internal/src/lib/agenda.ts:38`), que chama `GET /api/agenda/day/<YYYY-MM-DD>`.
- **Rationale**: o endpoint já existe no backend (`app/api/agenda.py:api_agenda_day`) e devolve exatamente `EventoResumo[]` do dia, já ordenado por `start_at`. Nenhum consumidor React usava esse hook até agora — é reuso puro, sem trabalho de backend.
- **Alternatives considered**: filtrar no cliente os eventos já carregados pela visão Mês (`useAgenda(ym)`). Rejeitado porque a visão Dia precisa poder navegar para fora do mês corrente (ex.: dia 1 do mês seguinte a partir do calendário) sem depender do estado de outro hook, e porque manter uma única fonte por visão é mais simples de cachear via TanStack Query (chave `["agenda-dia", date]` já definida).

## 2. Fonte de dados para a visão Lista

- **Decision**: reusar `useAgenda(ym)` (o mesmo hook já usado pela visão Mês), agrupando o array `events` por dia no cliente.
- **Rationale**: não existe endpoint de range arbitrário de datas (confirmado em `app/api/agenda.py` — só `?ym=` mensal e `/day/<date>` diário); a spec já assume (ver Assumptions do spec.md) que "o período" da Lista é o mês corrente. Reaproveitar o mesmo fetch evita uma segunda chamada de rede ao trocar entre Mês e Lista no mesmo período.
- **Alternatives considered**: criar um novo endpoint de range. Rejeitado — fora do escopo definido na spec (FR-019: reusar dados já existentes) e desnecessário, já que o mês inteiro já vem em uma única resposta.

## 3. Cálculo de posicionamento e sobreposição na linha do tempo (estilo Google Agenda)

- **Decision**: função pura em `lib/agendaLayout.ts` que recebe `EventoResumo[]` de um dia e devolve, para cada evento, `{ top: number; height: number; column: number; columnCount: number }` (percentuais relativos a 00:00–24:00), usando o algoritmo clássico de "cluster de intervalos sobrepostos" (agrupar eventos em clusters transitivamente conectados por sobreposição de horário, atribuir coluna sequencial dentro do cluster, `columnCount` = nº de colunas do cluster).
- **Rationale**: é o mesmo algoritmo usado por Google Agenda/Outlook para layout de colunas; é determinístico, testável isoladamente (função pura, sem DOM) e barato (O(n log n) por dia, poucas dezenas de eventos no pior caso real do sistema).
- **Alternatives considered**: CSS Grid com `grid-column` fixo por "faixa de horário" pré-definida. Rejeitado por ser mais rígido para overlaps parciais (ex. 14:00–16:00 e 15:00–17:00 não ocupam a mesma faixa inteira) e mais difícil de generalizar para 3+ eventos simultâneos.

## 4. Estado de visão e data de referência (Mês/Dia/Lista + navegação)

- **Decision**: manter o estado (`view`: "month"|"day"|"list", `date`/`ym` de referência) sincronizado com a query string da URL (`/agenda?view=day&date=2026-07-25`), com `useState` inicializado a partir dela e `useSearchParams` do React Router para atualizar.
- **Rationale**: satisfaz FR-005 (trocar de visão preserva a data de referência) de forma robusta a re-render/navegação do browser (voltar/avançar), e permite futuramente linkar direto para um dia específico. Consistente com o padrão já usado pelo restante do app (React Router é a lib de navegação padrão do projeto).
- **Alternatives considered**: estado local (`useState`) sem URL. Rejeitado — mais simples, mas perde o estado ao navegar para o detalhe do evento e voltar (o botão "voltar" do navegador retornaria à visão Mês em vez da visão Dia que o usuário estava vendo), o que quebraria a expectativa natural de navegação.

## 5. Clique no dia da grade mensal vs. clique no evento (FR-006/FR-007)

- **Decision**: em `CalendarGrid.tsx`, o clique no número do dia e na área vazia da célula (`DayCell`) chama um callback `onDayClick(dateKey)` fornecido pelo pai; os badges de evento continuam sendo `<Link to={/events/:id}>` como hoje, com `stopPropagation` implícito por já serem elementos de foco/clique próprios dentro da célula.
- **Rationale**: menor mudança possível no componente já existente (Princípio I) — hoje a célula inteira (`DayCell`) já é uma `div`; basta adicionar `onClick`/`role="button"` na própria `div` (fora dos links de evento) sem alterar a estrutura visual.
- **Alternatives considered**: envolver a célula inteira num `<Link>` e os badges de evento com `stopPropagation`. Rejeitado — `<Link>` teria que envolver outros elementos clicáveis (`<button>` de "+N"), gerando aninhamento inválido de elementos interativos em HTML.

## 6. Largura do container (FR-016)

- **Decision**: trocar `max-w-5xl` por `w-full` (sem `max-w-*`) no container raiz de `AgendaPage.tsx`, mantendo o padding responsivo já existente (`p-4 sm:p-6`).
- **Rationale**: atende diretamente FR-016/SC-003; `AppLayout` já não impõe limite de largura no `<main>` (confirmado na exploração) — quem limitava era só o `max-w-5xl` da própria página.
- **Alternatives considered**: `max-w-6xl`/`max-w-7xl` (limite generoso, mas ainda finito). Rejeitado porque a spec pede explicitamente "ocupar toda a largura" em monitores widescreen (SC-003 exige ≥90% da largura disponível), o que um `max-w` fixo não garante em telas muito grandes.
