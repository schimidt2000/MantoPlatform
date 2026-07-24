# Data Model: Reconstrução do Formulário de Cadastro/Edição de Eventos

Nenhum modelo novo é criado nesta feature — todas as entidades já existem (`app/models.py`). O
que muda é como `CalendarEvent` e `EventRole`/`EventClient` são atualizados em bloco (novo), e um
campo booleano passa a ser aceito na criação de `EventContract` (extensão aditiva).

## CalendarEvent (existente) — campos tocados pela edição em bloco

Nenhuma coluna nova. O novo `PATCH /api/events/<id>` passa a poder alterar, de uma vez:
`title`, `event_type`, `start_at`/`end_at` (derivados de `date`+`start`+`end`), `location`,
`description`, `needs_rehearsal`, `sale_value`, `sale_value_gross`, `transport_value`,
`acrescimo_value`, `with_invoice`, `is_cortesia_permuta`, `seller_id`, `sale_date`,
`payment_method`, `payment_installments`, `payment_due_date`.

Campos que **não** são tocados por este endpoint (permanecem só editáveis pelas ações pontuais já
existentes): `confirmed_at`/`confirmed_by_id` (endpoint de confirmar), `commission_rate` (tela de
detalhe, restrito a superadmin), `makeup_time`/`makeup_location`/`departure_time`/
`departure_location` (endpoint de logística), `group_leader_id`/`group_name`/`parent_event_id`
(agrupamento/ensaio, fora de escopo), `feedback_token`, `google_event_id`/`google_html_link`.

## EventRole (existente) — reconciliação por identidade na edição

Campos lidos/escritos pela edição em bloco (só `role_type="character"`): `character_name`,
`figurino_sheet_id`, `cache_value`, `needs_makeup`, `is_singer`, `talent_id`.

Regra de reconciliação (ver `research.md` §4):

| Situação da linha enviada | Ação |
|---|---|
| Tem `role_id` que existe e é `role_type="character"` | `UPDATE` dos campos acima |
| Não tem `role_id` (nova linha) | `INSERT` novo `EventRole(role_type="character")`, mesma auto-detecção de figurino por nome já usada na criação |
| `role_id` existente não aparece mais no conjunto enviado, sem convite aceito | `DELETE` |
| `role_id` existente não aparece mais no conjunto enviado, **com convite aceito**, ator não é SUPERADMIN | Operação inteira recusada (nada é salvo) |

Vagas `role_type="extra"` (Coordenador, Técnico de Som) não entram nesse conjunto — o
coordenador continua sendo tratado como campo dedicado (`coordinator_talent_id`), mesma lógica de
`_apply_default_roles`/`_ensure_coordinator` já usada na criação (procura a vaga "Coordenador"
existente e atualiza o `talent_id`, ou cria uma nova se não houver).

## EventClient (existente) — substituição completa na edição

Corpo do `PATCH`: `clients: {client_id, relation}[]`. Sem estado próprio a preservar — o núcleo
apaga todos os `EventClient` do evento e recria a partir da lista enviada, mesma lógica de
`_create_client_links` já usada na criação. `CalendarEvent.client_id` (denormalizado, "cliente
primário") é recalculado com a mesma regra da criação: o `relation == "Contratante"` (ou o
primeiro da lista, se nenhum for Contratante).

## EventContract (existente) — novo campo aceito na criação do registro

`is_signed` (já existe na coluna, default `False`) passa a poder ser setado no momento da criação
via `POST /events/<id>/contracts` (multipart, campo opcional `is_signed`), além de continuar
alterável depois via `POST /contracts/<id>/toggle-signed` (inalterado, SUPERADMIN apenas).

## Forma do corpo — `PATCH /api/events/<id>` (novo)

```json
{
  "title": "string",
  "event_type": "SHOW | CORP | R&I | VM | \"\"",
  "date": "YYYY-MM-DD",
  "start": "HH:MM",
  "end": "HH:MM",
  "location": "string",
  "description": "string",
  "needs_rehearsal": true,
  "sale_value": 0,
  "sale_value_gross": 0,
  "transport_value": 0,
  "acrescimo_value": 0,
  "with_invoice": false,
  "is_cortesia_permuta": false,
  "seller_id": 1,
  "sale_date": "YYYY-MM-DD",
  "payment_method": "avista | pix_parcelado | faturado | cartao | \"\"",
  "payment_installments": 2,
  "payment_due_date": "YYYY-MM-DD",
  "coordinator_talent_id": 1,
  "form_response_id": 1,
  "characters": [
    { "role_id": 42, "name": "Mickey", "figurino_sheet_id": 3, "cache_value": 300,
      "needs_makeup": true, "is_singer": false, "talent_id": 7 },
    { "role_id": null, "name": "Minnie", "figurino_sheet_id": null, "cache_value": null,
      "needs_makeup": true, "is_singer": false, "talent_id": null }
  ],
  "clients": [{ "client_id": 10, "relation": "Contratante" }]
}
```

Resposta: mesmo formato de "full event detail" (`serialize_event_detail`) já usado por todos os
outros endpoints de evento — nenhum formato de resposta novo.

Erros:
- `400` — mesma validação de `_validate_event_core` (título/data/horários/valores/vendedor/
  parcelas), reaproveitada da criação.
- `409` — remoção de personagem com convite aceito, ator não-SUPERADMIN (ver §4 acima).
- `403` — ator sem papel COMERCIAL/SUPERADMIN.
- `404` — evento não encontrado.

## Consumidor único deste formato

`frontend/apps/internal/src/pages/EventEditPage.tsx` (novo) via
`frontend/apps/internal/src/lib/eventCreate.ts::useUpdateEvent()` (novo hook). Nenhuma view Jinja
legada é afetada — `app/calendar/routes.py` e os templates continuam com sua própria lógica de
edição pontual, intocada.
