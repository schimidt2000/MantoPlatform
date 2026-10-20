# Contratos — Feature 312

Envelope de erro: `json_error` (`{error, fields?, codigo?}`). Toda recusa por cancelado leva `codigo: "cancelado"`
(`CODIGO_EVENTO_CANCELADO`). Todo campo novo é opcional no TypeScript. "Papel real" = `current_user.roles` (o
"Ver como" não conta); "flag" = `_role_flags` (segue o "Ver como").

## Leitura — o cancelado deixa de vir

| Endpoint | Mudança | RBAC |
|---|---|---|
| `GET /api/agenda?ym=` | inalterado (já não traz); `incluir_cancelados` não existe | inalterado |
| `GET /api/agenda/day/<data>` | **passa a esconder** o cancelado, sempre | inalterado |
| `GET /api/agenda/search?q=` | **passa a esconder**, filtro antes do limite | inalterado |
| `GET /api/events/<id>/grupo/candidatos` | o cancelado some (pela busca) | inalterado |
| `GET /api/gastos/eventos?date=` | **deixa de trazer** o cancelado | inalterado (`api_login_required`) |
| `GET /api/talents/<id>` | `history.items` e `total_events`, `total_earned`, `characters_done`, `last_event` sem o cancelado | inalterado |
| `GET /api/clientes/<id>` | `events[]` e `event_count` sem o cancelado; sai `events[].cancelado`; **novo** `cancelamentos: {quantidade: int, retido: str}` (zero sem cancelado); `form_history[].event_situacao?` | inalterado (`_require_vendas`) |
| Fila 3D e pendências de presente (`impressoes3d_read`) | sem o cancelado | inalterados |
| `GET /api/events/<id>` (principal vivo) | `group.satellites[]` sem o dia cancelado; `group_label` conta os vivos; `ensaios[]` sem ensaio cancelado | inalterado |
| `GET /api/vendas/pipeline`, `GET /api/financeiro/dashboard` | `eventos[].group_label` "(N eventos)" só com os dias vivos | inalterados |

## Página de Cancelamentos

`GET /api/events/cancelamentos[?mes=AAAA-MM][&devolucao=nao_pago|no_banco|pago|sem]`

- **RBAC**: SUPERADMIN ou FINANCEIRO pelo papel real (`_can_read_cancelamentos`); demais **403**; anônimo **401**.
  `_can_delete` intocado (excluir, cancelar e alterar devolução continuam só do Superadmin).
- **Erros**: `mes` fora de `AAAA-MM` (ou mês inexistente) → **400** `fields.mes`; `devolucao` fora do
  vocabulário → **400** `fields.devolucao`.
- **Resposta**: `pendentes[]` (inalterado, agora também ao FINANCEIRO); `cancelados[]` com o `resumo` da 306
  (inalterado) e sem o objeto `devolucao` legado; **novos** `total_retido: str`, `total_retido_escopo: "periodo" |
  "listados"`, `filtros: {mes: str | null, devolucao: str | null}`. Com `mes`, sem limite; sem `mes`, 200 mais
  recentes por `cancelled_at`. `devolucao` filtra por `EXISTS` (o evento aparece em cada estado que tem); `sem` =
  `NOT EXISTS`. `total_retido` soma por evento.

## Card "Cancelamentos do período"

Forma única (`painel_de_cancelamentos`), igual nas duas telas:

```text
{ quantidade: int, pago: str, devolvido: str, devolucao_a_pagar: str, retido: str, comissao_retido: str,
  bv_retido: str, imposto?: str, efeito_resultado?: str,
  itens: [{ event_id, titulo, event_date, cancelado_em, seller_name, pago, devolvido, devolucao_a_pagar,
            retido, comissao_retido, status: "cancelado" }] }
```

| Endpoint | Mudança | RBAC |
|---|---|---|
| `GET /api/vendas/pipeline` | **novo** `cancelamentos` (sempre presente; `quantidade: 0` sem cancelado), do mês do cancelamento, no escopo do vendedor de `_resolve_vendas_scope`; comissão pela regra do KPI | inalterado; `imposto` e `efeito_resultado` só para SUPERADMIN e FINANCEIRO (flag) |
| `GET /api/financeiro/dashboard` | `paineis.cancelamentos` passa a sair da mesma função; os itens ganham `event_date, seller_name, pago, devolvido, devolucao_a_pagar, comissao_retido` | inalterado (FINANCEIRO/SUPERADMIN) |

## A tela do cancelado

`GET /api/events/<id>` do cancelado:
- `flags.somente_consulta: true` (ausente no vivo); `can_edit_event`, `can_edit_core`, `can_confirm`,
  `can_group`, `can_manage_3d`, `can_request_delete` falsas; `flags.desfazer?: {presente_3d: bool, formulario: bool}`
  com o que `can_manage_3d` e `can_edit_core` seriam (o soltar e o desligar); `can_edit_venda_cancelado` e `can_edit_motivo_cancelado` (306/306b)
  inalteradas.
- `cancellation_reason` e `cancelled_by` só com `show_comercial` (COMERCIAL, FINANCEIRO, SUPERADMIN, pela flag);
  os outros recebem `null`; `cancelled_at` para todos.

**Trava** — toda escrita abaixo, num evento cancelado, para **todo** papel, depois do 404 e do 403 da rota:
**409** `{error: "Este evento foi cancelado — a tela fica só para consulta.", codigo: "cancelado"}`, nada gravado.

- `PATCH /api/events/<id>`, `…/basico`, `POST …/confirm`, `PATCH …/logistics`, observações (`POST …/observations`,
  `DELETE /observations/<id>`), `PUT …/clients`, contratos (as três rotas), `…/travel-estimate`, materiais (as
  rotas), `…/presenca`, `PATCH …/grupo` (renomear), `POST …/sync`, `POST …/roles` com ou sem talento, `PATCH`/`DELETE
  /ensaios/<id>` de ensaio cancelado, `POST`/`DELETE …/3d-dismissal`, `DELETE /clientes/avaliacoes/<id>` de avaliação
  de cancelado;
- vagas: `DELETE /roles/<id>`, `…/transporte` (as duas), figurino feito e ficha, dismiss/restore, `…/payment-status`,
  `POST /roles/<id>/assign` com talento, cachê ou transporte;
- `PATCH /api/events/<id>/3d-gifts/<gift>` (editar presente);
- Jinja: toda ação do despachante `POST /events/<id>` e as rotas fora dele que escrevem no evento (observações,
  materiais, dismiss/restore, `create-ensaio`, `link-parent`, `edit-ensaio`, `delete-ensaio`, `sync`) → `flash` com a
  frase e `redirect`; `GET /figurinos/print-event/<id>` idem; no cancelado, o "Log de atividades" do Jinja só vai
  ao template com a `show_comercial` (Q9).

**Livre** (regra própria, intocada): dados de venda (`pode_editar_venda_do_cancelado`, 306), `PATCH
…/motivo-cancelamento` (306b), `PATCH …/devolucao`, `POST …/multas`; desfazer: `PATCH …/form-response` com
`null`, soltar presente 3D e tag NFC (`event_id: null`), tirar da escala (abaixo).

**Recusas de vínculo** (Q2, Q5):

| Rota | Recusa |
|---|---|
| `POST /api/ensaios/<id>/vincular` com pai cancelado | **400** `fields.parent_event_id` |
| `PATCH /api/3d/nfc/<id>` com `event_id` cancelado diferente do atual | **400** `fields.event_id` (o mesmo id → 200) |
| `POST`/`PATCH /api/figurino/producoes` com `event_id` cancelado novo; `solicitar-ficha` | **400** `fields.event_id` (editar sem trocar → 200) |
| `POST /api/events/<id>/ensaios` (e Jinja `create-ensaio`) | **409**, antes do Google |
| `POST /api/events/<id>/3d-gifts` | **409** |
| `PATCH /api/events/<id>/form-response` com id; `POST /api/formularios/respostas/<id>/vincular-evento`; edição em bloco | **409** (com `null` → 200) |
| `POST /api/events/<id>/roles` com talento; `POST /roles/<id>/assign` com talento; `POST /roles/<id>/invite` | **409**, sem e-mail |
| `POST /api/events/<id>/feedback-link` | **409** |
| `GET`/`POST /api/avaliar/<token>` (público) | **410** "Este evento foi cancelado — não há avaliação a fazer."; nada gravado |
| `GET /api/portal/events/<id>/figurino` (portal) | depois do 403 "não escalado" e do 404: **400** "Este evento foi cancelado." |
| `POST /api/portal/invites/<role_id>/accept` (portal) | **400** "Este evento foi cancelado." (recusar e "Ciente" ficam livres) |

Evento com pedido de exclusão pendente ou marcado pela 303: nenhuma das recusas acima.

## Tirar da escala no cancelado (Q10)

`POST /api/roles/<id>/assign` em vaga de evento cancelado:
- **RBAC**: `_can_casting` (CASTING, SUPERADMIN pelo papel real); FIGURINO, COMERCIAL, FINANCEIRO → **403**
  "Evento cancelado: quem tira da escala é o Casting." (no vivo, inalterado: `_can_edit_event`).
- Só `{talent_id: null}` sem cachê nem transporte → 200 com o detalhe; a vaga fica; nenhum e-mail de remoção.
  Com talento, cachê ou transporte → 409 da trava.
- Quando não sobra ninguém a avisar naquele dia, a notificação `evento.cancelado_escala` do dia fica lida para
  todos, na mesma transação.

## Home

`GET /api/dashboard` → `casting.cancelados_a_avisar?: [{role_id, event_id, event_title, event_date, cancelled_at,
character_name, talent_id, talent_name, whatsapp}]` — opcional; `[]` sem pendência; só no painel de casting
(CASTING e SUPERADMIN, como hoje).

## Coisas ligadas

`event_situacao?: "cancelado" | "sumiu_do_google" | "exclusao_solicitada" | null` em: tags NFC (`serialize_tag`),
lista de formulários (`formularios_admin_read`), `form_history` da ficha da cliente, pedidos de figurino. Gastos
Extras: o `event_cancelled` da 306, inalterado. `PATCH` de gasto com o mesmo `event_id` → 200; gasto novo ligado a
cancelado por chamada direta → 200.
