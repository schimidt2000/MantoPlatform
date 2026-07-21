# Data Model — escrita de casting (146, US1)

Sem entidade/coluna nova. Escrita sobre `EventRole` existente. Descreve o contrato de entrada
e o efeito no banco (que deve espelhar o handler Jinja atual).

## Entrada — `POST /api/roles/<id>/assign`

Body JSON:

| Campo | Tipo | Nota |
|---|---|---|
| `talent_id` | int \| null | null = desescalar (remove o talento do cargo) |
| `cache_value` | string \| number \| null | valor cru (pt-BR ou número); parseado no back via `parse_brl` |
| `travel_cache` | string \| number \| null | adicional de transporte fora de SP |

## Efeito no `EventRole` (mesmo do handler Jinja)

- `talent_id` ← novo (ou null).
- `cache_value` ← parseado; **limitado ao `cache_cap`** se quem salva não é superadmin.
- `travel_cache` ← parseado.
- `assigned_at` ← agora (se tem talento) ou null.
- Ao TROCAR de talento: `figurino_done_at` ← null; `invite_status` ← null → depois `pending`.
- Com talento: `payment_status` ← `nao_pago`.
- `EventLog` criado (autor = usuário, papel "Casting", mensagem espelhando a do Jinja).

## Efeitos colaterais (preservados do Jinja)

- Talento novo escalado → e-mail de convite (`send_invite_email`), `invite_status=pending`.
- Talento trocado que não recusou → e-mail de remoção ao antigo (`send_removal_email`).
- Talento já `accepted` com cachê/transporte alterado → e-mail de mudança
  (`send_event_changed_email`) + `event_changed_at`/`change_description`.

## Saída

`serialize_event_detail(event, current_user, impersonate)` (feature 145) — o evento atualizado,
com os blocos conforme o papel. A tela React re-renderiza a partir daí.
