# Implementation Plan: Arquivos temporários na Revisão (090)

**Branch**: `090-revisao-arquivos-temporarios` | **Date**: 2026-06-26 | **Spec**: [spec.md](spec.md)

## Summary

Materiais de revisão (feature 088) passam a ser **temporários**: `expires_at = envio + 7 dias`. Uma
limpeza diária remove o **arquivo** dos vencidos não finalizados (mantendo registro + comentários). O
criador pode **substituir** (nova versão, reinicia prazo, remove o antigo) e **finalizar** (remove o
arquivo na hora). Aviso de 7 dias na criação. Sem perda de comentários.

## Technical Context

**Modelo** (`app/models.py` — `ReviewAsset`): novas colunas
- `expires_at` (DateTime), `finalized_at` (DateTime), `file_removed` (Boolean, default False),
  `version` (Integer, default 1).
- Propriedades auxiliares: `is_available` (tem arquivo: `not file_removed`), `days_left`.

**Migração** (down_revision `y1b2c3d4e5f6`): adiciona as 4 colunas; para os existentes,
`expires_at = created_at + interval '7 days'`, `version = 1`, `file_removed = false`.

**Limpeza** (`app/revisao/cleanup.py`): `cleanup_expired_review_files()` — apaga via `delete_file()` o
arquivo de assets `expires_at < now AND finalized_at IS NULL AND file_removed = false`, marca
`file_removed = true`. Idempotente. Retorna nº removidos.
- Thread diária em `app/__init__.py` (`_start_review_cleanup`, mesma guarda de dev; intervalo 24h, sleep
  inicial). Reuso opcional via CLI `flask cleanup-review-files` (em `app/cli.py`).

**Rotas** (`app/revisao/routes.py`):
- `_save_assets`: define `expires_at = utcnow + 7d` ao criar.
- `POST /revisao/asset/<aid>/replace` (criador): valida mesmo tipo de mídia + tamanho; `delete_file`
  do antigo; `save_file` do novo; `file_path` novo, `version += 1`, `expires_at = utcnow+7d`,
  `file_removed=False`, `finalized_at=None`. Mantém comentários.
- `POST /revisao/asset/<aid>/finalize` (criador): `delete_file` do arquivo; `finalized_at=utcnow`,
  `file_removed=True`. Mantém registro/comentários.
- `asset_view`/`space_detail`: já passam o asset; templates leem `file_removed`/`finalized_at`/
  `expires_at`/`version`.

**Templates**:
- `revisao/new.html`: aviso "arquivos ficam ~7 dias e depois são removidos".
- `revisao/space.html`: por material, selo de **expira em N dias** / **Finalizado** / **Expirado**.
- `revisao/asset.html`: se `file_removed` → bloco "arquivo removido (expirado/finalizado)" no lugar do
  player, mantendo o painel de comentários; se `can_manage` e há arquivo → form **Substituir arquivo** +
  botão **Finalizar** (com confirmação); mostrar "expira em N dias" e "versão N".

**Storage**: `delete_file()` (já existe) remove do volume/S3.

## Constitution Check

- **II. Migração manual** (autogenerate quebrado): colunas adicionadas à mão; existentes recebem prazo.
- **IV. Não quebrar**: registros/comentários preservados; só o arquivo é removido. Thread isolada com
  guarda de dev, não afeta o fluxo normal.

**Resultado**: PASS.

## Testing

Contra **`manto_local`**: migração aplica (existentes com expires_at); criar material define expires_at;
substituir remove antigo + versão+1 + reinicia prazo (comentários mantidos); finalizar remove arquivo +
marca finalizado; `cleanup_expired_review_files()` remove arquivo de vencido não finalizado e marca
file_removed (sem apagar comentários); permissões (revisor não substitui/finaliza). Viewer mostra estado
removido. `ruff` sem erros novos. Limpar dados de teste.

## Project Structure

```text
app/models.py                         — ReviewAsset: expires_at/finalized_at/file_removed/version
migrations/versions/z2c3d4e5f6a7_*.py  — adiciona colunas + prazo nos existentes
app/revisao/cleanup.py                 — cleanup_expired_review_files()
app/__init__.py                        — _start_review_cleanup (thread diária)
app/cli.py                             — comando cleanup-review-files
app/revisao/routes.py                  — expires no upload; replace; finalize
app/templates/revisao/{new,space,asset}.html — aviso, selos, controles, estado removido
```

## Complexity Tracking

> Sem violações. Atenção: limpeza idempotente e remoção do arquivo sem perder comentários.
