# Data Model: Resumo das Avaliações — fidelidade visual e RBAC

Nenhuma tabela ou coluna nova. Este documento apenas mapeia as entidades já existentes
(`app/models.py`) que o panorama de avaliações consome, e a forma serializada (`RatingsOverview`)
que a tela React consome — sem nenhuma mudança de schema/contrato além do valor `"7d"` passar a
ser aceito como `period`.

## Entidades existentes (sem alteração)

- **`EventRating`**: avaliação geral que um `Talent` dá a um `CalendarEvent` em que participou —
  `score` (1-5), `comment`, `submitted_at`, `edit_count`, FKs `event_id`/`talent_id`.
- **`EventSubRating`**: sub-nota de categoria dentro de uma `EventRating` — `category` (uma de
  `RATING_CATEGORIES`: artista/som/figurino/texto/coordenacao/maquiagem), `score`, `comment`,
  `subject_talent_id` (colega avaliado, opcional).
- **`SiteSetting` (id=1)**: configuração global singleton — campo `ratings_fully_anonymous`
  (bool) controla o "modo anônimo total".
- **`CalendarEvent`**: evento — `title`, `start_at`; usado para agrupar/ordenar o panorama.
- **`EventRole`**: papel de um talento num evento — usado só para resolver `author_funcao`
  (personagem) quando `show_authors` é verdadeiro.

## Contrato serializado — `RatingsOverview` (sem mudança de forma, só de valores aceitos)

Já definido em `frontend/apps/internal/src/lib/ratings.ts` e produzido por
`rating_ops.serialize_overview()`. Nenhum campo novo — a única mudança é que o campo `period` da
requisição (`RatingsFilters.period`) passa a aceitar `"7d"` além de `"30d" | "90d" | "365d" |
"custom" | "all"`, e a resposta pode ecoar `period: "7d"` com `recorte_label` contendo "última
semana" (via `PERIOD_LABELS["7d"]`).

Campos relevantes já existentes que esta feature passa a **renderizar** (hoje calculados pelo
backend mas ignorados pela tela React atual):

| Campo               | Tipo                    | Uso na tela                                   |
|---------------------|-------------------------|------------------------------------------------|
| `dist`               | `Record<string, number>`| Painel "Distribuição das notas" (barras 5★–1★) |
| `dist_max`           | `number`                 | Normaliza a largura das barras de distribuição |
| `by_category`        | `CategoryAverage[]`      | Painel "Média por categoria"                   |
| `best_events`        | `RankedEvent[]`          | Painel "Melhores eventos"                      |
| `worst_events`       | `RankedEvent[]`          | Painel "Pontos a melhorar"                     |
| `trend`              | `TrendPoint[]`           | Painel "Tendência mensal"                      |
| `recorte_label`      | `string`                 | Legenda do recorte ativo nos KPIs              |
| `has_filters`        | `boolean`                | Habilita a ação "Limpar filtros"                |
| `date_mode`          | `string`                 | Estado ativo do toggle "Data do evento/avaliação" |
| `selected_event`     | `EventOption \| null`    | Suprime período/ranking quando visão por evento |

## Regra de exibição derivada (client-side, sem estado próprio)

- `showAnonToggle = data.is_superadmin` (já correto no código atual — mantido).
- `authorText = comment.author` (renderizado literalmente — o backend já resolve para "Anônimo"
  quando aplicável; o frontend nunca decide esse valor).
