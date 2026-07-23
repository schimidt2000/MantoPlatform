# Data Model: Portal do Artista — App React (fatia 1)

Nenhum modelo novo, nenhuma migration. Os campos usados já existem em `app/models.py`.

## Talent (linhas 91-171)

Identidade que faz login. Campos relevantes a esta fatia: `cpf`/`email_contact` (login),
`password_hash`/`must_change_password` (via `check_password()`), `terms_accepted_at` (gate de
redirecionamento à versão clássica), `photo_face_path`/`photo_full_path` (fotos, US5),
`cnh_file_path` (documento, US5).

## EventRole (linhas 411-447)

Escalação do talento num evento — núcleo da Agenda e dos Convites.

| Campo | Uso nesta fatia |
|---|---|
| `invite_status` | `None`/`"pending"` → Convites (US3); `"accepted"` → Agenda (US2) |
| `character_name` | nome do personagem, exibido na ficha de figurino (US4) |
| `cache_value`/`travel_cache` | soma = valor do cachê no histórico (US2) |
| `payment_status` | "pago" vs. outro → situação de pagamento no histórico (US2) |
| `event_changed_at`/`change_description` | aviso de alteração não reconhecida (US2, FR-006) |
| `figurino_sheet_id`/`figurino_sheet` | ficha de figurino do personagem (US4) |

Aceitar/recusar convite (US3) só altera `invite_status` — mesma regra do
`accept_invite`/`reject_invite` legados (`app/talent_portal/routes.py`).

## CalendarEvent (linhas 206+)

`title`, `start_at`/`end_at`, `location` — exibidos na Agenda/Convites/Ficha de figurino.

## FigurinoSheet (linhas 352-392)

`photo_filename` (foto de referência) + `notes`/`pieces_list` (observações) — exibidos na Ficha
de Figurino (US4). Resolução do sheet de um `EventRole` segue a mesma regra do
`event_figurino()` legado: usa `role.figurino_sheet` se setado, senão busca por
`character_name_norm` (via `app.figurino.drive_service.normalize_name`).

## Sem mudança de schema

Toda a superfície de dados desta fatia já existe. O trabalho é 100% de camada de apresentação
(API + React) e extração de núcleo de negócio (`portal_ops.py`) das views Jinja existentes.
