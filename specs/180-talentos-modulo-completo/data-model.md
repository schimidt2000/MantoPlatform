# Data Model — Reestruturação do Módulo de Talentos

Nenhuma tabela ou coluna nova. Todos os dados já existem em `app/models.py`; esta feature apenas
expõe/deriva mais informação a partir deles. Nenhuma migration é necessária.

## Entidades existentes reutilizadas

### `Talent` (tabela `talents`)
Sem mudança de schema. Campos relevantes já mapeados no `spec.md`/`plan.md` — ver seção 3.1 do
levantamento inicial. `race`, `clothing_size_top`, `clothing_size_bottom`, `shoe_size`,
`passport_status` continuam texto livre/enums já existentes; o filtro de Raça no frontend passa a
oferecer 5 opções fixas (Amarela, Branca, Indígena, Parda, Preta) que são comparadas por
igualdade exata contra `Talent.race` — mesma comparação `.in_()` já usada hoje, sem mudança no
backend.

### `EventRole` (tabela `event_roles`)
Sem mudança. Fonte do histórico de eventos (`character_name`, `cache_value`, `assigned_at`,
join com `CalendarEvent.start_at`). Agora também usado para derivar `last_event` (primeiro item
da lista já ordenada por data decrescente).

### `EventRating` (tabela `event_ratings`)
Sem mudança. Passa a ser consultado por talento (`talent_id == talent.id`) para o bloco
"avaliações dadas" do perfil — antes só era consultado agregado (por evento/categoria) em
`rating_ops.py::build_overview`.

### `EventSubRating` (tabela `event_sub_ratings`)
Sem mudança. Passa a ser consultado por `subject_talent_id == talent.id` para o bloco
"avaliações recebidas" do perfil.

### `EventRatingVersion` (tabela `event_rating_versions`)
Sem mudança. Não é lido nesta fatia (o indicador "editada"/`edit_count` já basta para o requisito
do usuário; o histórico completo de versões do Jinja — expandir cada edição anterior — fica fora
de escopo, ver Assumptions do spec.md: a spec pede "estrelas e depoimentos", não o drill-down de
histórico de edição, que é uma funcionalidade adicional do Jinja não mencionada no pedido).

## Formas de dados novas (somente en route, não persistidas)

### `TalentHistory.last_event` (novo campo no payload de `GET /api/talents/<id>`)
```
{
  "event_id": int,
  "event_title": str | null,
  "character_name": str,
  "start_at": str (ISO 8601) | null
} | null
```
Deriva de `history[0]` (já ordenado desc por `CalendarEvent.start_at`) dentro de
`get_talent_profile()`. `null` quando o talento não tem histórico.

### `TalentRatingsOverview` (payload de `GET /api/talents/<id>/ratings`, novo)
```
{
  "received": [
    {
      "category": str,           // som | figurino | texto | coordenacao | maquiagem | artista
      "category_label": str,     // rótulo em pt-BR
      "score": int,               // 1-5
      "comment": str | null,
      "author": str,               // nome de quem avaliou, ou "Anônimo"
      "event_id": int,
      "event_title": str | null,
      "event_date": str (ISO) | null
    }
  ],
  "given": [
    {
      "score": int,
      "comment": str | null,
      "event_id": int,
      "event_title": str | null,
      "event_date": str (ISO) | null,
      "submitted_at": str (ISO) | null,
      "edited": bool,             // edit_count > 0
      "edit_count": int
    }
  ],
  "show_authors": bool            // paridade com build_overview — front usa para decidir se
                                   // exibe algum aviso de "avaliações anônimas" quando false
}
```

## Estado de UI (frontend, não persistido no backend)

### Modo da tela de perfil
`"read" | "edit"` — refletido em `?edit=1` na URL de `/talents/:id`. Não é uma entidade de dados,
é estado de navegação (React Router `useSearchParams`).

### Filtros pendentes vs. aplicados (listagem)
Dois conjuntos de estado local no `TalentsListPage`/`TalentFilterPanel`:
- **Pendente**: o que o usuário está selecionando dentro dos dropdowns, antes de clicar
  "Filtrar".
- **Aplicado**: o que efetivamente vai para `useTalentDirectory` (query params). Só é atualizado
  no clique de "Filtrar" — busca por nome (`q`) e abas continuam aplicando na hora, por serem
  interações diretas de resultado imediato, não parte do painel avançado.
