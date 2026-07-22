# Data Model — Leitura e Gestão de Talentos e Figurino (154)

Nenhum modelo novo. `Talent` e `FigurinoSheet` já existem em `app/models.py`. Nenhuma
migration é necessária.

## Talent (`talents`) — campos expostos no perfil (`GET /api/talents/<id>`)

| Grupo | Campos |
|---|---|
| Identidade | `id`, `full_name`, `artistic_name`, `gender`, `birth_date`, `race`, `languages`, `is_foreigner` |
| Status | `status` (`pending`\|`active`) |
| Contato | `phone`, `email_contact` |
| Aparência | `tags`, `skills`, `height_cm`, `clothing_size_top`, `clothing_size_bottom`, `shoe_size`, `passport_status` |
| Documentos/PIX | `rg`, `cpf` (só editável por SUPERADMIN), `pix_key`, `pix_key_secondary`, `pix_key_type` |
| Fotos/docs (só leitura nesta fatia) | `photo_face_path`, `photo_full_path`, `doc_photo_path`, `cnh_file_path`, `cnh_expiration` |
| Veículo | `car_brand`, `car_model`, `car_year`, `car_plate` |
| Outros | `worked_before`, `how_found_us` |
| Interno (CASTING/SUPERADMIN) | `notes`, `warning_level` (`None`\|`leve`\|`moderado`\|`grave`) |

**Fora do payload desta fatia**: `password_hash`/`must_change_password`/
`password_reset_token`/`terms_accepted_at` (portal do talento), `media_items` (portal),
`received_sub_ratings`/`given_ratings` (avaliações — fatia futura).

## Histórico de eventos (calculado, não é uma tabela nova)

A partir de `EventRole` filtrado por `talent_id` + `assigned_at is not None`, join
`CalendarEvent`:

```json
{
  "items": [{"event_id", "event_title", "character_name", "cache_value", "start_at"}],
  "total_events": int,
  "total_earned": number,
  "characters_done": [str]
}
```

## FigurinoSheet (`figurino_sheets`) — campos expostos (`GET /api/figurino`)

| Campo | Observação |
|---|---|
| `id`, `character_name` | |
| `pieces` | lista `[{"name", "qty"}]`, via `pieces_list` (já trata formato legado) |
| `notes` | |
| `photo_url` | leitura apenas — pode ser `/uploads/...` (nativo) ou URL absoluta do Drive (legado); ver plan.md Design Decision 5 |
| `updated_at`, `created_at` | |

**Fora do payload/ação desta fatia**: `drive_file_id`/`drive_url`/`thumbnail_url`/
`last_synced_at` (sync legado, continua Jinja-only), upload/rotação de foto.

## Estados e transições

- **Talent.status**: `pending → active` (aprovar, idempotente) ou `pending → (excluído)`
  (rejeitar, só permitido em `pending`). Não existe transição `active → pending`.
- **FigurinoSheet**: sem estado — criar/editar/excluir são as únicas transições; excluir
  desvincula (`EventRole.figurino_sheet_id = NULL`) qualquer cargo que apontava para a ficha.
