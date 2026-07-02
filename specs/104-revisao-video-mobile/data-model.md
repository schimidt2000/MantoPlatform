# Data Model — Revisão de Vídeo Profissional Mobile-First (104)

## Entidades

### ReviewAssetVersion (NOVA) — tabela `review_asset_versions`

Snapshot de uma versão **anterior** de um material, criado no momento da substituição do
arquivo. A versão atual continua vivendo em `ReviewAsset`.

| Campo | Tipo | Regras |
|---|---|---|
| `id` | Integer PK | |
| `asset_id` | Integer FK → `review_assets.id` | NOT NULL, index `ix_review_asset_versions_asset_id`; cascade delete via relationship |
| `version_number` | Integer | NOT NULL — número que a versão tinha quando era atual (1, 2, ...) |
| `file_path` | String(400) | NOT NULL — URL/caminho no armazenamento |
| `original_name` | String(300) | nullable |
| `uploaded_by` | Integer FK → `users.id` | nullable — quem enviou aquela versão (desconhecido para snapshots de dados antigos) |
| `created_at` | DateTime | NOT NULL — quando a versão foi enviada (herdado de quando era atual, se conhecido; senão o momento do snapshot) |
| `expires_at` | DateTime | nullable — herdado do asset no momento do snapshot (NÃO renova) |
| `file_removed` | Boolean | NOT NULL default False server_default "0" — True quando o cleanup/finalize removeu o arquivo |

Relationships: `ReviewAsset.versions` (backref `asset`, cascade `all, delete-orphan`,
order_by `version_number`).

Propriedade `is_available` (espelha a do asset): `not self.file_removed`.

### ReviewComment (ESTENDIDA) — tabela `review_comments`

| Campo novo | Tipo | Regras |
|---|---|---|
| `version_number` | Integer | NOT NULL, server_default "1" — versão do material vigente quando o comentário foi criado; carimbado com `asset.version` no INSERT |
| `resolved_by` | Integer FK → `users.id` | nullable — quem concluiu |
| `resolved_at` | DateTime | nullable — quando concluiu |

Relationship: `resolver = db.relationship("User", foreign_keys=[resolved_by])`.

Estados do comentário:

```text
pendente (resolved=False, resolved_by=None, resolved_at=None)
   └─ concluir → concluído (resolved=True, resolved_by=<user>, resolved_at=<now>)
concluído
   └─ reabrir → pendente (limpa os três campos)
```

### ReviewAsset (1 coluna nova)

| Campo novo | Tipo | Regras |
|---|---|---|
| `uploaded_by` | Integer FK → `users.id` | nullable — quem enviou a versão ATUAL do arquivo; preenchido no upload/substituição e copiado para o snapshot ao substituir (necessário para FR-012: "autor do envio" no histórico) |

Ganha também relationship `versions` e helpers Python:

- `history` (property): lista de snapshots ordenada por `version_number` desc.
- Ao **substituir** (`replace_asset`): antes de sobrescrever, cria
  `ReviewAssetVersion(asset_id, version_number=asset.version, file_path=asset.file_path,
  original_name=asset.original_name, uploaded_by=<desconhecido→None>, created_at=<data do
  envio anterior se rastreada, senão utcnow>, expires_at=asset.expires_at,
  file_removed=asset.file_removed)` — e NÃO chama mais `delete_file` no arquivo antigo.
- Ao **finalizar** / **excluir**: remove também os arquivos dos snapshots com
  `file_removed=False`.

### ReviewSpace / ReviewReviewer (INALTERADAS)

## Validação e integridade

- `version_number` do comentário sempre ≥ 1; novos comentários recebem `asset.version` no
  servidor (nunca confiar no client).
- Comentar exige que a versão exibida seja a atual — POST de comentário rejeita quando o
  request referencia versão antiga (composer nem aparece, mas a API valida).
- Concluir/reabrir: permitido a criador do espaço, super admin ou autor do comentário.
- Excluir comentário: permitido apenas ao autor ou super admin.

## Migration (manual)

Arquivo: `migrations/versions/a3b4c5d6e7f8_review_versions_resolution.py`
(`down_revision = "e7b8c9d0f1a2"`).

```text
upgrade():
  1. create_table review_asset_versions (colunas acima + FKs + index asset_id)
  2. add_column review_comments.version_number  INTEGER NOT NULL server_default "1"
  3. add_column review_comments.resolved_by     INTEGER NULL FK users.id
  4. add_column review_comments.resolved_at     DATETIME NULL
  5. backfill: UPDATE review_comments SET version_number = (
       SELECT version FROM review_assets WHERE review_assets.id = review_comments.asset_id)
     (sintaxe de subquery correlacionada — funciona em SQLite e Postgres)

downgrade(): drop das 3 colunas + drop da tabela.
```

Materiais existentes NÃO ganham snapshots retroativos (os arquivos antigos já foram
apagados pela lógica anterior); o histórico começa a acumular a partir da primeira
substituição pós-deploy. Comentários existentes ficam todos na versão atual do seu material
(comportamento idêntico ao de hoje — FR-017).
