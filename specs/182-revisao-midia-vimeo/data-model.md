# Phase 1 Data Model: Revisão de Mídia estilo Vimeo

Todas as entidades já existem em `app/models.py` (linha ~1369). Esta feature altera apenas
`ReviewAsset` (campo novo) — as demais entidades ficam listadas para referência de relacionamento.

## ReviewAsset (alterado)

| Campo | Tipo | Notas |
|---|---|---|
| `status` | `String(20)`, `NOT NULL`, default `"em_revisao"` | **NOVO**. Valores válidos: `em_revisao`, `aprovado`, `precisa_ajustes`, `rejeitado`. Validado em `review_ops.py` (não como `db.Enum` do Postgres — string simples + validação em Python, para migration mais simples e reversível sem `ALTER TYPE`). |

**Regras de transição**:
- Criação de material (`save_assets`): `status` nasce `"em_revisao"` (via `server_default`, sem
  mudança de código em `save_assets`).
- Substituição de arquivo (`replace_asset`): `status` volta para `"em_revisao"` incondicionalmente
  (FR-017), mesmo que já estivesse `"em_revisao"`.
- Mudança manual (`set_asset_status`, novo): só quem passa em `review_ops.can_manage(space, user)`
  pode chamar; qualquer um dos 4 valores é aceito como destino (inclusive voltar manualmente para
  `"em_revisao"`, ex.: reabrir uma revisão rejeitada por engano).

**Sem migração de dados**: materiais existentes recebem `"em_revisao"` via `server_default` da
migration (sem necessidade de `UPDATE` em massa).

## ReviewSpace, ReviewAssetVersion, ReviewReviewer, ReviewComment (inalterados)

Mantidos exatamente como estão hoje — ver `app/models.py:1369-1514`. Relacionamentos relevantes para
esta feature:

- `ReviewAsset.versions` (`ReviewAssetVersion`, ordenado por `version_number`) alimenta o
  `VersionSelector.tsx` novo (já existia como lista simples via `asset.history` — vira seletor de UI,
  sem mudança de dado).
- `ReviewAsset.comments` (`ReviewComment`, filtrado por `version_number == versão atual`) alimenta os
  marcadores do `VideoScrubber.tsx` e o `CommentFeed.tsx` — sem mudança de estrutura, só nova forma de
  consumo (ordenação por `timecode` em vez de `created_at`, ver FR-007).

## Contrato de serialização (API) — `_asset_summary()`

`app/api/revisao_read.py::_asset_summary()` e `app/api/revisao_write.py::_space_summary()` (o dict do
asset embutido nas respostas de escrita) passam a incluir `"status": asset.status` no payload, ao
lado dos campos já existentes (`id`, `media_type`, `original_name`, `position`, `version`,
`is_available`, `days_left`, `finalized_at`, `file_url`). Ver `contracts/revisao-status.md` para o
contrato completo do payload e do endpoint novo de escrita.
