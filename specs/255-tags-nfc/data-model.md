# Data Model — Feature 255: Tags NFC

## Tabela nova: `nfc_tags`

Modelo `NfcTag` em `app/models.py` (seção Impressões e Acervo 3D).

| Coluna | Tipo | Regras |
|---|---|---|
| `id` | Integer PK | |
| `code` | String(20) NOT NULL UNIQUE (índice) | Imutável após criação. Formato `<prefixo>-<sufixo 6 chars>` em MAIÚSCULAS, sufixo do alfabeto `23456789ABCDEFGHJKMNPQRSTUVWXYZ` via `secrets.choice` |
| `sequence` | Integer NOT NULL | Numeração humana por item (1, 2, 3…). Imutável. Constraint única `(item_id, sequence)` |
| `item_id` | Integer FK → `acervo_3d_items.id` NOT NULL (índice) | Produto da tag. Sem cascade de delete: `delete_acervo_item` já recusa apagar item com vínculos (tags contam como vínculo) |
| `event_id` | Integer FK → `calendar_events.id` NULLABLE, `ondelete="SET NULL"` (índice) | Evento do show. Alterável pelo admin; evento apagado → tag fica sem evento, nunca quebra |
| `is_active` | Boolean NOT NULL default `true` | Desativação lógica; página pública de tag inativa responde payload genérico |
| `notes` | Text NULLABLE | Observações da equipe |
| `access_count` | Integer NOT NULL default `0` | Total de acessos públicos resolvidos (FR-012) |
| `last_accessed_at` | DateTime NULLABLE | Último acesso público |
| `created_at` | DateTime NOT NULL default utcnow | |

**Relationships**: `item` (joinedload na lista/resolução — nome+foto), `event` (lazy; a lista admin usa joinedload de `event.event_clients` para o contratante via `client_of_event`).

**Invariantes**:
- Tag **nunca é apagada** — nenhum endpoint/op de delete existe.
- `code` e `sequence` nunca mudam após a criação.
- `event_id` é o único vínculo mutável (+ `is_active`, `notes`).

## Coluna nova: `acervo_3d_items.nfc_prefix`

| Coluna | Tipo | Regras |
|---|---|---|
| `nfc_prefix` | String(10) NULLABLE | Não-nulo = item habilitado para NFC; valor é o prefixo do código (ex.: `01`). Normalizado (trim, maiúsculas, sem `-`). Alterável — vale só para tags futuras (códigos existentes imutáveis) |

## Migration

Arquivo manual em `migrations/versions/`, `down_revision = "f3a9c15d8b42"` (head atual):
1. `op.add_column("acervo_3d_items", sa.Column("nfc_prefix", sa.String(10), nullable=True))`
2. `op.create_table("nfc_tags", ...)` com índices (`code` unique, `item_id`, `event_id`) e `UniqueConstraint("item_id", "sequence", name="uq_nfc_tags_item_sequence")`
3. Downgrade: drop table, drop column.

Sem backfill: não existem tags físicas gravadas ainda; a luminária v1 recebe o prefixo pelo ERP após o deploy.

## Regras de negócio (em `app/impressoes3d/nfc_ops.py`, puro)

- **Geração de código**: sorteia sufixo até código inédito (máx. 20 tentativas; espaço de 31⁶ por prefixo).
- **Sequence**: `max(sequence) + 1` por item, na mesma transação da criação.
- **`sync_event_gift_tags(event, item)`** (chamada por `add_event_gift`/`update_event_gift` antes do commit): alvo = `sum(quantity)` dos presentes do item no evento; existentes = `count` de tags `(event_id, item_id)`; cria `max(0, alvo - existentes)` tags associadas ao evento. Nunca remove. Item sem `nfc_prefix` → no-op.
- **Lote manual**: cria N tags do item sem evento (`event_id = NULL`). Exige item com `nfc_prefix`.
- **Resolução pública**: normaliza código para maiúsculas; tag ativa → payload com produto + contadores atualizados (commit tolerante a falha); inexistente/inativa → payload genérico idêntico em shape.
- **Auditoria**: criação (lote e automática), associação/troca de evento e ativar/desativar geram `audit(...)` como o restante do módulo 3D.

## Estados

`is_active`: `true` ⇄ `false` (reversível, sem outros estados). Associação: `event_id NULL` ⇄ `event_id set` (reversível/alterável). Não há máquina de estados adicional — o ciclo de vida físico (gravada/travada/entregue) é procedimento operacional fora do software (assumption da spec).
