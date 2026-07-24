# Data Model: Reestruturação do Banco de Figurinos

## FigurinoSheet (existente, `app/models.py`) — alteração

Nova coluna:

| Campo | Tipo | Nullable | Descrição |
|-------|------|----------|-----------|
| `tags` | `Text` (JSON serializado: `list[str]`) | Sim | Tags/categorias livres da ficha, mesmo padrão de serialização já usado por `pieces`. `[]`/`None` quando sem tags. |

Nova property (paridade com `pieces_list`):

```python
@property
def tags_list(self) -> list[str]:
    """Lista de tags normalizadas (strip, sem vazias, sem duplicatas, preserva ordem de inserção)."""
```

Regras de validação (aplicadas em `_clean_tags()` no ops, mesma camada de `_clean_pieces()`):
- Cada tag: `strip()`; descarta vazias.
- Deduplicação case-insensitive (mantém a primeira grafia usada).
- Sem limite rígido de quantidade (uso interno, baixo volume esperado).

## FigurinoMissingDismissal (novo modelo, `app/models.py`)

Representa o descarte de um alerta de "personagem sem ficha" para as ocorrências (`EventRole`)
existentes no momento do descarte.

| Campo | Tipo | Nullable | Descrição |
|-------|------|----------|-----------|
| `id` | `Integer` (PK) | Não | — |
| `character_name_norm` | `String(200)`, indexado | Não | Nome do personagem normalizado (mesma função `normalize_name` já usada em `figurino_sheets.character_name_norm`). |
| `event_role_ids` | `Text` (JSON serializado: `list[int]`) | Não | IDs de `EventRole` cobertos por este descarte no momento em que ele foi feito. |
| `dismissed_at` | `DateTime` | Não (default `utcnow`) | Quando o descarte (mais recente, se atualizado) ocorreu. |
| `dismissed_by` | `Integer` (FK `users.id`) | Sim | Quem descartou. |

Restrição lógica (não é `UNIQUE` de banco, aplicada em código): no máximo um registro por
`character_name_norm` — descartes repetidos do mesmo nome fazem `UPDATE` (união dos
`event_role_ids`), nunca `INSERT` duplicado.

**Regra de reaparecimento (FR-011)**: um personagem sem ficha só permanece oculto enquanto todo
`EventRole.id` atualmente sem cobertura para aquele nome estiver contido em
`event_role_ids` do descarte. Um `EventRole` novo (id não presente no descarte) faz o personagem
reaparecer na lista.

## EventRole (existente, sem alteração de schema)

`figurino_sheet_id` (já existente desde a feature 154/155) passa a ser **escrito** por um novo
fluxo: a associação de um personagem faltante a uma ficha (`associate_missing_character`), além do
fluxo já existente (seleção manual na criação do evento). Nenhuma coluna nova.

## Forma de resposta da API — `GET /api/figurino` (contrato alterado)

Antes:
```json
{ "items": [...], "chars_without_sheet": ["Anjo Gabriel", "Duende 3"] }
```

Depois:
```json
{
  "items": [
    {
      "id": 1,
      "character_name": "Anjo Gabriel",
      "pieces": [{"name": "Blazer azul", "qty": 1}],
      "tags": ["anjo", "natal"],
      "notes": null,
      "photo_url": "/uploads/figurino_photos/1.jpg",
      "updated_at": "2026-07-20T10:00:00",
      "created_at": "2026-06-01T09:00:00"
    }
  ],
  "chars_without_sheet": [
    { "character_name": "Duende 3", "character_name_norm": "duende 3" }
  ]
}
```

Consumidor único deste formato: `frontend/apps/internal/src/lib/figurino.ts` /
`FigurinoListPage.tsx` (reescritos nesta mesma feature — ver nota do Constitution Check em
`plan.md`). A view Jinja legada (`app/figurino/routes.py`) tem sua própria query independente e
não é afetada.
