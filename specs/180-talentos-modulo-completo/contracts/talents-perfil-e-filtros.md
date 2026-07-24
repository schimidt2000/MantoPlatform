# Contrato — Talentos: filtros, perfil e avaliações (feature 180)

Segue as convenções gerais de `specs/144-migracao-react-spa/contracts/api-conventions.md` e o
contrato já existente de `specs/154-talentos-figurino-leitura/contracts/talents-figurino-endpoints.md`.
Este documento cobre só o que muda ou é adicionado por esta feature.

## `GET /api/talents/directory` (existente — extensão de parâmetro)

Novo valor aceito em `height_op`: `"eq"` (além de `"gte"`/`"lte"` já existentes). Nenhuma outra
mudança de contrato — request/response inalterados fora disso.

```
GET /api/talents/directory?status=active&height_op=eq&height_value=180
```

## `GET /api/talents/<id>` (existente — extensão de resposta)

Novo campo `history.last_event`:

```json
{
  "talent": { "...": "inalterado" },
  "history": {
    "items": ["..."],
    "total_events": 12,
    "total_earned": 4500.0,
    "characters_done": ["..."],
    "last_event": {
      "event_id": 812,
      "event_title": "Aniversário Infantil — Buffet X",
      "character_name": "Homem-Aranha",
      "start_at": "2026-06-14T15:00:00"
    }
  },
  "can_edit": true
}
```

`last_event` é `null` quando `history.items` está vazio.

## `GET /api/talents/<id>/ratings` (NOVO)

Leitura aberta (`@api_login_required`, sem gate de papel — paridade com o restante da leitura de
talentos). 404 se o talento não existir.

```
GET /api/talents/42/ratings
```

```json
{
  "received": [
    {
      "category": "artista",
      "category_label": "Artista",
      "score": 5,
      "comment": "Muito profissional, chegou no horário.",
      "author": "Maria Produção",
      "event_id": 812,
      "event_title": "Aniversário Infantil — Buffet X",
      "event_date": "2026-06-14T15:00:00"
    }
  ],
  "given": [
    {
      "score": 4,
      "comment": "Organização boa, atraso na saída.",
      "event_id": 812,
      "event_title": "Aniversário Infantil — Buffet X",
      "event_date": "2026-06-14T15:00:00",
      "submitted_at": "2026-06-15T09:12:00",
      "edited": true,
      "edit_count": 1
    }
  ],
  "show_authors": true
}
```

Quando o modo anônimo total (`SiteSetting.ratings_fully_anonymous`) está ativo, ou o usuário
requisitante não é SUPERADMIN, `author` em cada item de `received` vem como `"Anônimo"` e
`show_authors` vem `false` — mesma regra já aplicada em `GET /api/ratings` (avaliações gerais).

Erros: `404` (`{"error": {"message": "Talento não encontrado"}}`) — sem outros códigos de erro
específicos (leitura sempre permitida a usuário autenticado).

## `GET /api/talents/character-suggestions` (NOVO — espelho do endpoint Jinja)

Leitura aberta. Mesma resposta do endpoint Jinja `/talents/character-suggestions` (não afetado):

```
GET /api/talents/character-suggestions?q=hom
```

```json
[
  { "name": "Homem-Aranha", "count": 14 },
  { "name": "Homem de Ferro", "count": 6 }
]
```

`q` com menos de 2 caracteres retorna `[]` (paridade com o comportamento Jinja atual).

## Sem mudanças

- `PATCH /api/talents/<id>` — inalterado (o modo de edição unificado consome o mesmo endpoint já
  existente; nenhum campo novo de escrita).
- `POST /api/talents/<id>/notes`, `/approve`, `/reject`, `/photo`, `DELETE /photo` — inalterados.
