# Implementation Plan: Página de resumo das avaliações

**Branch**: `035-resumo-avaliacoes` | **Date**: 2026-06-09 | **Spec**: [spec.md](./spec.md)

## Summary

Nova página `/talents/avaliacoes` (somente leitura/agregação) com visão **Geral** e **Por evento**
(via `?event_id=`), apresentando médias, distribuição de notas e médias por categoria de forma visual
(estrelas + barras). Acesso SUPERADMIN/CASTING. Link no menu. Sem migration.

## Constitution Check
- **I. Reutilizar** ✅ — lê `EventRating`/`EventSubRating` existentes; reusa layout/estilos do sistema.
- **III. Camadas** ✅ — agregação na rota; template só apresenta.
- **V. UI/UX** ✅ — estrelas, barras, estado vazio, paleta via variáveis CSS.

## Design Detalhado

### Rota — `app/talents/routes.py`: `avaliacoes()`
- `GET /talents/avaliacoes?event_id=<opcional>`. Acesso: SUPERADMIN ou CASTING (senão 403).
- Lista de eventos avaliados: distinct de `EventRating.event_id` (id, título, data), ordenada por data.
- Base de avaliações: todas (geral) ou filtradas por `event_id` (por evento).
- Agregar em Python:
  - `total` = nº de avaliações; `avg_overall` = média das notas (1 casa); `events_rated` = nº de
    eventos distintos; `dist` = contagem por nota 1..5.
  - `by_category` = para cada categoria (figurino/som/texto/artista/coordenacao/maquiagem): média e nº
    a partir de `EventSubRating` (filtrado por evento quando aplicável).
  - `comments` = avaliações com comentário (nota, comentário, avaliador, data) — destaque na visão por
    evento; também disponível na geral (mais recentes).
- Render `talents/avaliacoes.html` com `mode` ("geral"/"evento"), `selected_event`, listas e métricas.

### Template — `app/templates/talents/avaliacoes.html` (novo)
- Seletor de evento (`<select onchange="location=...">`: "Geral" + eventos avaliados).
- Cards: Total de avaliações · Nota média (estrelas) · Eventos avaliados.
- Distribuição de notas (5→1) em barras com contagem.
- Médias por categoria em barras proporcionais (0–5) + estrelas + nº de avaliações.
- Lista de comentários (estrelas + texto + autor + evento/data).
- Estado vazio claro quando não há avaliações.
- Macro/parcial de estrelas (cheia/meia/vazia) reutilizável no template.

### Navegação — `app/templates/base.html`
- Item "Avaliações" no menu (próximo a Banco de Talentos), ativo quando em `/talents/avaliacoes`.

### Verificação
- Boot + ruff + render do template; com dados de avaliação (se houver no dev) conferir números;
  estados vazios; acesso negado p/ papel sem permissão.

## Project Structure
```text
app/talents/routes.py                     # avaliacoes() (agregação)
app/templates/talents/avaliacoes.html     # NOVO — página visual
app/templates/base.html                   # link de navegação
```

## Fora de escopo
- Filtro por período / exportação (follow-up). Edição de avaliações por aqui. Sem migration.
```
