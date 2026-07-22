# Data Model: Revisão de Mídia (170)

Nenhuma tabela/campo novo.

| Entidade             | Uso                                                                 |
|----------------------|------------------------------------------------------------------------|
| `ReviewSpace`        | espaço — título, descrição, criador, materiais, revisores            |
| `ReviewAsset`        | material — arquivo, tipo, posição, versão, expiração, finalizado     |
| `ReviewAssetVersion` | snapshot de versão substituída                                       |
| `ReviewReviewer`     | vínculo usuário↔espaço                                              |
| `ReviewComment`      | comentário — corpo, âncora (timecode/página/pos_x,y), versão, resolvido |

## Valores computados (movidos para `review_ops.py`, sem duplicar regra)

- `can_create()` — Marketing ou Superadmin.
- `can_view(space, user)` — Superadmin, criador, ou revisor selecionado.
- `can_manage(space, user)` — Superadmin ou criador.
- `can_resolve(comment, user)` — Superadmin, criador do espaço do material, ou autor do
  comentário.
- `can_delete_comment(comment, user)` — Superadmin ou autor do comentário.
- `detect_media_type(filename)` — mapeia extensão → `video`/`audio`/`image`/`pdf`.
- `save_assets(space, files, uploader_id)` — valida tipo/tamanho (512MB), salva no
  armazenamento, cria `ReviewAsset` com posição incremental e expiração de 7 dias; erros por
  arquivo não impedem os demais.
- `snapshot_current_version(asset)` — preserva a versão vigente como `ReviewAssetVersion` antes
  de sobrescrever (chamado por `replace_asset`).
- `delete_version_files(asset)` — remove do armazenamento os arquivos de snapshots ainda
  disponíveis.
- `replace_asset(asset, file, uploader_id)` — exige mesmo tipo de mídia; snapshot + nova versão
  + reinício do prazo.
- `finalize_asset(asset)` — remove arquivo atual e de versões antigas do armazenamento; marca
  `file_removed`/`finalized_at`.
- `add_comment(...)` — recusa (`ReviewCommentVersionError`) se a versão informada não for a
  atual.
- `ReviewValidationError(field, message)` — erro de validação de negócio (arquivo inválido/
  incompatível).
