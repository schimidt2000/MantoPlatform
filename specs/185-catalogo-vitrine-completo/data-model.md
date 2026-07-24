# Data Model: Catálogo Vitrine Completo

Toda mudança é **aditiva** — nenhuma coluna/tabela existente de `CatalogItem`, `CatalogCategory`,
`CatalogItemImage` ou `FigurinoSheet` é alterada ou removida (FR-015).

## Entidades alteradas

### `CatalogItem` (`catalog_items`) — Tema

Coluna nova:

| Coluna       | Tipo         | Null | Descrição                                                        |
|--------------|--------------|------|--------------------------------------------------------------------|
| `video_url`  | `VARCHAR(500)` | sim  | URL externa de vídeo do Tema (Drive/MP4/Vimeo). `NULL` = sem vídeo. |

Propriedade nova (não persistida): `video_kind` → `classify_video_url(video_url)` (`"mp4"|"drive"|"vimeo"|None`).

Relacionamento novo: `characters` (`CatalogCharacter`, `lazy=True`, `cascade="all, delete-orphan"`,
`order_by="CatalogCharacter.position"`) — mesma forma do relacionamento `images` já existente.

## Entidades novas

### `CatalogCharacter` (`catalog_characters`) — Personagem filho

| Coluna              | Tipo            | Null | Descrição                                                                 |
|---------------------|-----------------|------|------------------------------------------------------------------------------|
| `id`                | `INTEGER PK`    | não  |                                                                              |
| `catalog_item_id`   | `INTEGER FK`    | não  | `catalog_items.id`, `ON DELETE CASCADE` — índice (`ix_catalog_characters_catalog_item_id`) |
| `name`               | `VARCHAR(200)`  | não  | Nome do personagem                                                          |
| `slug`               | `VARCHAR(240)`  | não  | Único globalmente (`<slug-tema>-<slug-nome>` + desambiguação `-2`, `-3`…)   |
| `photo_url`          | `VARCHAR(500)`  | sim  | Uma foto (upload local, mesmo `app/storage.py` das fotos do Tema)           |
| `video_url`          | `VARCHAR(500)`  | sim  | URL externa de vídeo (Drive/MP4/Vimeo)                                     |
| `figurino_sheet_id`  | `INTEGER FK`    | sim  | `figurino_sheets.id`, `ON DELETE SET NULL`                                 |
| `position`           | `INTEGER`       | não  | Default `0` — ordem de exibição dentro do Tema                             |
| `is_active`          | `BOOLEAN`       | não  | Default `true` — Personagens inativos não aparecem na vitrine pública      |
| `created_at`         | `DATETIME`      | não  | `default=utcnow`                                                           |

Propriedade não persistida: `video_kind` (mesma função `classify_video_url`).

**Validação (camada `*_ops`, não no banco)**:
- `name` obrigatório, não-vazio após `strip()`.
- `video_url`, se preenchida, precisa ser classificável (`mp4`/`drive`/`vimeo`) — senão `CatalogValidationError("video_url", ...)`.
- Pelo menos uma mídia (foto OU vídeo) recomendada, mas não bloqueante — Personagem sem nenhuma mídia é permitido (ex.: cadastro incompleto salvo como rascunho) e a vitrine trata como card sem preview.

**Cascata de exclusão**: excluir um `CatalogItem` (Tema) exclui seus `CatalogCharacter` em cascata (mesmo padrão de `images`), com confirmação explícita no gerenciador interno (Assumption da spec). Excluir um `CatalogCharacter` individualmente não afeta o Tema nem outros Personagens.

**Degradação segura de figurino excluído**: excluir uma `FigurinoSheet` referenciada por um `CatalogCharacter` não é bloqueado — `ON DELETE SET NULL` limpa o vínculo automaticamente (Edge Case da spec).

## Relação com entidades existentes (sem alteração de schema)

- **`FigurinoSheet`** (`app/models.py:352`): referenciada por `CatalogCharacter.figurino_sheet_id`; nenhuma coluna nova nela.
- **`EventRole`** (`app/models.py:447`, já tem `character_name` + `figurino_sheet_id`): recebe o auto-preenchimento de `figurino_sheet_id` a partir do Personagem escolhido no formulário de Novo Evento — é um *prefill* de formulário, não um vínculo de banco novo (ver `research.md` §6). Nenhuma migration necessária para `EventRole`.
- **Lista de Interesse (`localStorage`, frontend)**: não é uma entidade de banco. `WishlistItem` (TypeScript, `frontend/apps/public/src/lib/wishlist.ts`) ganha `kind?: "tema" | "personagem"` e `parentSlug?: string` (research.md §5) — mudança de tipo, sem migration de dado (itens antigos sem `kind` continuam válidos, tratados como `"tema"`).

## Migration Alembic

- Arquivo novo em `migrations/versions/`, `down_revision = "4e6f8a1c2d5b"` (head atual — `figurino_sheet_tags`).
- `upgrade()`: `op.add_column("catalog_items", sa.Column("video_url", sa.String(500), nullable=True))` +
  `op.create_table("catalog_characters", ...)` com os campos acima, FK `catalog_item_id` com `ondelete="CASCADE"`, FK `figurino_sheet_id` com `ondelete="SET NULL"`, índice em `catalog_item_id`, `unique=True` em `slug`.
- `downgrade()`: `op.drop_table("catalog_characters")` + `op.drop_column("catalog_items", "video_url")` — completo e reversível, sem perda de dado de tabelas pré-existentes.
