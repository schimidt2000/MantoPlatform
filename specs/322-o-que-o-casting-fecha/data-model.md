# Modelo de dados — Feature 322

## `event_roles` (modelo `EventRole`, `app/models.py`)

Três colunas novas, todas nulas, sem backfill (migration `c322a7e1b9d4`, `down_revision =
"e8b4a1c7d310"`):

| Coluna | Tipo | Significado | Quem escreve |
|---|---|---|---|
| `perfil_vendido` | `String(200)`, nula | O tipo que o orçamento vendeu, pronto para ler ("Cantor · show · com maquiagem"). `NULL` = vaga sem orçamento. | criação do orçamento (`_create_roles_from_input`); vínculo 273 só onde é `NULL` |
| `criada_pelo_sistema` | `Boolean`, nula | `True` = a vaga nasceu de uma regra do sistema (coordenador/técnico/presença garantidos, extras do orçamento, maquiador da 322). `NULL` = criada por pessoa ou antes do deploy. | `_ensure_coordinator`, `_ensure_sound_technician`, `_create_extra_roles_from_orcamento`, `aplicar_equipe_do_orcamento`, `garantir_vaga_de_maquiador` |
| `escalado_pelo_comercial` | `Boolean`, nula | `True` = o talento ATUAL entrou pelo formulário do evento. Acompanha o talento: sai quando o casting troca ou tira. | `_create_roles_from_input`, `_apply_default_roles`, `update_event_core` (liga); `assign_role` (desliga) |

Marcadores puros, como `needs_makeup`/`is_singer`/`does_transport`: `True | NULL`.

## Invariantes

- **I-1**: evento não cancelado com ao menos um personagem `needs_makeup` tem, depois de criado,
  editado ou ligado a orçamento pós-deploy, ao menos uma vaga cujo nome contém "maquiad".
- **I-2**: `perfil_vendido` nunca é apagado nem trocado por vínculo ou edição.
- **I-3**: depois que o evento existe, `needs_makeup` só muda por superadmin (edição) ou pelo
  orçamento (vínculo 273).
- **I-4**: `escalado_pelo_comercial = True` só com `talent_id` preenchido.

## Payload (`_serialize_role`)

Ver [contracts/evento-elenco.md](./contracts/evento-elenco.md).
