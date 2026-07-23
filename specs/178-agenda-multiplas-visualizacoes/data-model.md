# Phase 1 Data Model: Agenda com múltiplas visualizações

Nenhuma entidade de banco de dados nova ou alterada — esta feature é somente de apresentação
(frontend), sobre dados já servidos pela API existente. As "entidades" abaixo são os tipos de
dado que fluem entre os componentes React novos, alguns já existentes e reutilizados.

## Entidades existentes (reutilizadas, sem alteração)

### `EventoResumo` (`frontend/apps/internal/src/lib/agenda.ts`)

Já existente — fonte única do resumo de evento consumido pelas 3 visões.

| Campo | Tipo | Uso nas novas visões |
|---|---|---|
| `id` | `number` | chave de navegação (`/events/:id`) |
| `title` | `string` | nome do evento (Dia e Lista) |
| `event_type` | `string` | categoria → `eventCategory()` (cor/rótulo do badge) |
| `start_at` | `string \| null` (ISO) | posicionamento vertical na linha do tempo; ordenação na Lista |
| `end_at` | `string \| null` (ISO) | altura do bloco na linha do tempo |
| `location` | `string \| null` | exibido no bloco (Dia) e no item (Lista) |
| `characters`, `is_satellite`, `group_name`, `confirmed` | diversos | não usados diretamente nas novas visões (já existentes, sem novo uso aqui) |

### `AgendaMes` / `AgendaDia` (`frontend/apps/internal/src/lib/agenda.ts`)

Já existentes — respostas de `useAgenda(ym)` e `useAgendaDia(date)`. Sem alteração de forma.

## Entidades novas (somente estado de UI, não persistidas)

### `AgendaViewMode`

```ts
type AgendaViewMode = "month" | "day" | "list";
```

Controla qual dos 3 componentes de visão é renderizado. Vive na query string da URL (`?view=`).

### `AgendaLayoutBlock` (saída de `lib/agendaLayout.ts`)

Resultado do cálculo de posicionamento/overlap para um evento dentro da linha do tempo de um dia.

| Campo | Tipo | Descrição |
|---|---|---|
| `event` | `EventoResumo` | evento original |
| `topPct` | `number` (0–100) | posição vertical, % do dia (00:00–24:00) |
| `heightPct` | `number` (0–100) | altura do bloco, % do dia; mínimo aplicado para eventos muito curtos ou sem `end_at` |
| `column` | `number` (0-indexed) | coluna atribuída dentro do cluster de eventos sobrepostos |
| `columnCount` | `number` | nº total de colunas do cluster ao qual este evento pertence (define a largura: `100% / columnCount`) |

Eventos sem `start_at` não entram nesta lista — são tratados separadamente como "sem horário"
(FR-012) numa seção à parte da grade.

### Regras de derivação/validação

- Um evento entra no cálculo de overlap da visão Dia somente se `start_at` estiver definido; `end_at` ausente assume duração mínima padrão de 1 hora para fins de altura visual (evento "pontual").
- Overlap é calculado por transitividade: dois eventos A e B estão no mesmo cluster se seus intervalos `[start_at, end_at)` se interceptam, direta ou indiretamente através de um terceiro evento C.
- Evento cujo `end_at` ultrapassa 23:59 do dia de `start_at` tem `heightPct` truncado ao final da grade (ver Edge Case "evento que atravessa a meia-noite" no spec.md) — não é redistribuído para o dia seguinte.
- Agrupamento por dia na visão Lista usa a data (`YYYY-MM-DD`) de `start_at`; eventos sem `start_at` caem na mesma seção "Sem data" já existente na visão Mês (paridade, FR-019 — não inventar novo comportamento para esse caso).
