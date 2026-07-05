# Data Model — Dispensar Tarefa de Casting (108)

## EventRole (estendido)

| Campo novo | Tipo | Regras |
|---|---|---|
| `dismissed_at` | DateTime | nullable — `NULL` = cargo pendente normal; preenchido = dispensado |
| `dismissed_by` | Integer FK → `users.id` | nullable — quem dispensou |

Relationship nova: `dismisser = db.relationship("User", lazy=True, foreign_keys=[dismissed_by])`.

### Estados

```text
pendente (dismissed_at=None, dismissed_by=None)
   └─ dispensar → dispensado (dismissed_at=<now>, dismissed_by=<user>)
dispensado
   └─ restaurar → pendente (limpa os dois campos)
```

### Invariantes

- Só é válido dispensar um cargo com `talent_id IS NULL` (spec FR-009) — a rota rejeita
  (sem efeito + flash) se o cargo já tiver talento atribuído.
- Restaurar sempre é permitido em um cargo dispensado, independentemente de outros estados.
- A sincronização com o Google Agenda (`app/calendar/routes.py`) **não lê nem escreve** esses
  dois campos — o cargo dispensado é tratado como qualquer cargo existente do ponto de vista
  do parsing de título (ver research.md R1).

## Migration (manual)

Arquivo: `migrations/versions/<hash>_event_role_dismiss.py`
(`down_revision = "a3b4c5d6e7f8"`).

```text
upgrade():
  add_column event_roles.dismissed_at  DATETIME NULL
  add_column event_roles.dismissed_by  INTEGER NULL FK users.id

downgrade():
  drop_column event_roles.dismissed_by
  drop_column event_roles.dismissed_at
```

Sem backfill — cargos existentes ficam `NULL` (comportamento atual preservado, FR-008 /
regra "não quebrar o que funciona").
