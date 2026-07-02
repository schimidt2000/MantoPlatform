# Contrato de Rotas — Revisão 104

Blueprint existente `revisao_bp` (`/revisao`). Autenticação: `@login_required` em tudo;
leitura exige `_can_view(space)`; gestão exige `_can_manage(space)`.

## Rotas modificadas

### `GET /revisao/<space_id>/asset/<asset_id>` — asset_view

Novo query param opcional `v` (int):

- ausente ou `v == asset.version` → modo normal (versão atual, pode comentar).
- `v` < atual e existe snapshot → modo somente leitura: renderiza o arquivo do snapshot
  (ou aviso de expirado se `file_removed`), banner "versão antiga", composer oculto.
- `v` inexistente → 404.

Template recebe: `asset`, `space`, `can_manage`, `viewing_version` (int|None — None = atual),
`version_file` (dados do snapshot quando antiga), `history` (lista para o seletor).

### `GET /revisao/asset/<asset_id>/comments` — list_comments

Novo query param opcional `v` (int, default = versão atual). Retorna JSON **filtrado pela
versão** e enriquecido:

```json
[
  {
    "id": 12,
    "body": "Cortar 2s dessa cena",
    "author": "Maria",
    "author_id": 3,
    "timecode": 42.5,
    "page": null,
    "pos_x": null,
    "pos_y": null,
    "version_number": 2,
    "resolved": true,
    "resolved_by_name": "Erika",
    "resolved_at": "01/07/2026 14:30",
    "created_at": "30/06/2026 09:12",
    "can_resolve": true,
    "can_delete": false
  }
]
```

Campos novos: `version_number`, `resolved_by_name` (string|null), `resolved_at`
(string dd/mm/yyyy HH:MM | null), `can_resolve` (bool). `can_delete` muda de regra
(autor ou super admin — criador do espaço não excluí mais comentário alheio).

### `POST /revisao/asset/<asset_id>/comment` — add_comment

- Carimba `version_number = asset.version` no servidor.
- Rejeita com `409 {"error": "Comentários só na versão atual."}` se o body/query indicar
  versão antiga (`v` presente e != atual).
- Response 201 com o JSON do comentário (formato acima).

### `POST /revisao/comment/<comment_id>/resolve` — resolve_comment

- Permissão nova `_can_resolve`: criador do espaço, super admin ou autor do comentário;
  outros → 403.
- Concluir: `resolved=True, resolved_by=current_user.id, resolved_at=utcnow()`.
- Reabrir (toggle quando já resolvido): limpa os três campos.
- Response 200 com JSON do comentário.

### `POST /revisao/comment/<comment_id>/delete` — delete_comment

- Permissão restringida: autor do comentário ou super admin (criador do espaço removido).
- Response 200 `{"ok": true}`.

### `POST /revisao/asset/<asset_id>/replace` — replace_asset

Antes de sobrescrever o asset, cria snapshot `ReviewAssetVersion` com os dados atuais e
**não apaga** o arquivo antigo do armazenamento. Restante igual (valida tipo, 512 MB,
incrementa `version`, renova `expires_at`, zera `finalized_at`/`file_removed`).

### `POST /revisao/asset/<asset_id>/finalize` — finalize_asset

Além do arquivo atual, remove os arquivos de snapshots com `file_removed=False`
(marcando-os).

### `POST /revisao/asset/<asset_id>/delete` e `POST /revisao/<space_id>/delete`

Passam a apagar também os arquivos dos snapshots do(s) material(is).

## Rotas inalteradas

`GET /revisao/`, `GET|POST /revisao/novo`, `GET /revisao/<space_id>`,
`POST /revisao/<space_id>/upload`, `POST /revisao/<space_id>/reviewers`.

## Cleanup (não-HTTP)

`cleanup_expired_review_files()` passa a varrer também `review_asset_versions`
(`file_removed=False AND expires_at < now`) — mesmo contrato: retorna total removido,
idempotente.
