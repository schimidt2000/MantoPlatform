# Modelo de dados — Feature 339

Uma migration à mão, aditiva, `down_revision = "d323b5a1c0e7"` (ver `research.md` R8). Nenhuma
coluna existente muda de tipo; nenhuma tabela nova.

## `event_roles` (`EventRole`, `app/models.py:583`)

| Coluna nova | Tipo | Nulo | Significado |
|---|---|---|---|
| `teto_autorizado` | `Numeric(10,2)` | sim | Valor que o Superadmin autorizou acima do teto do orçamento **para a vaga** (sobrevive à troca de pessoa e aos recálculos de teto). NULL = sem autorização |
| `teto_autorizado_por` | `Integer` FK `users.id` `ON DELETE SET NULL` | sim | Quem autorizou. NULL com valor preenchido = autorização anterior à 339 (preenchimento da migration) |
| `teto_autorizado_em` | `DateTime` (hora de SP, `now_sp()`) | sim | Quando |
| `sobrando_desde` | `DateTime` (hora de SP) | sim | A vaga é de um personagem que o título passou a pedir menos vezes, e todas as vagas dele estavam ocupadas (FR-020). Limpa quando título e vagas voltam a bater (FR-017) |

Relação nova: `autorizador = db.relationship("User", foreign_keys=[teto_autorizado_por])`
(`EventRole` já tem outro FK para `users`, `dismissed_by` — sem `foreign_keys` o mapper quebra no boot,
como no caso do `CatalogItem`, `docs/00` §6 item 14).

### Regras

- **Teto efetivo** (fonte única, função nova `teto_ops.teto_efetivo(role, parcela)`, usada por
  `casting_ops.assign_role` e por `agenda_read._serialize_role`):
  `None` se `cache_cap is None`; senão `max(cache_cap + parcela, teto_autorizado or 0, cache_value or 0)`.
- **Teto para a nota do log** ("acima do cap — autorizado pelo admin"): o mesmo sem o `cache_value`.
- **Escrita do teto autorizado** (só em `assign_role`, só Superadmin, só com talento e cachê > 0):
  cachê > `cache_cap + parcela` → grava valor, autor, data; senão → NULL nos três.
- **Recálculo** (troca de tipo, vínculo novo) reescreve `cache_cap`/`cache_cap_note`; **nunca** toca
  `teto_autorizado`.
- **Preenchimento**: `teto_autorizado = cache_value` onde `cache_cap IS NOT NULL AND cache_value >
  cache_cap AND does_transport IS NOT TRUE`.

### Transições de `sobrando_desde`

```text
NULL ──(título perde ocorrência; vagas ocupadas > pedido)──▶ marcado
marcado ──(Casting tira a pessoa: vaga vazia sai; ou remove a vaga; ou o título volta a pedir)──▶ NULL
```

A resolução recalcula por nome: `vagas_do_nome ≤ contar_personagens(event.title)[nome]` → limpa a
marca de todas as vagas daquele nome e dá "Ciente" automático nos avisos daquela sobra.

## `notifications` (`Notification`, `app/models.py:685`)

| Coluna nova | Tipo | Nulo | Significado |
|---|---|---|---|
| `ciente_em` | `DateTime` (hora de SP, como `created_at`) | sim | A pessoa (`user_id` da linha) clicou "Ciente" na faixa do evento, ou a situação se resolveu (vaga a mais). Independe de `read_at` |

Sem índice novo: a faixa filtra por `entity_type/entity_id` (`ix_notifications_entity`, já existe) e
`user_id`.

### Catálogo (`app/notificacoes/notificacoes_ops.py`)

| `kind` | Destinatários (`DESTINATARIOS_POR_KIND`) | `dedupe_key` | Tem "Ciente" |
|---|---|---|---|
| `evento.tipo_show` | CASTING, ENSAIO, SUPERADMIN, menos o autor | `evento.tipo_show:{event_id}:{entrou\|saiu}:{AAAAMMDDHHMMSSffffff}` | sim |
| `evento.vaga_sobrando` | CASTING, SUPERADMIN, menos o autor | `evento.vaga_sobrando:{event_id}:{nome}:{pedido}:{vagas}` | sim |

`KINDS_COM_CIENTE = {evento.tipo_show, evento.vaga_sobrando}`. Retenção: linha desses `kind` com
`ciente_em IS NULL` segue a regra de "não lida" (180 dias).

## `event_logs` (sem mudança de esquema)

Entradas novas, todas com `actor_role` coerente com a porta: tetos recalculados (antigo → novo, por
vaga), teto autorizado gravado/limpo, vaga vazia removida pelo título, vaga marcada como sobrando,
título ajustado (remoção/inclusão de vaga), título não ajustado (nome não encontrado), título do ensaio
atualizado, falha do Google ao gravar título.
