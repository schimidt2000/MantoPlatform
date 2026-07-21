# Contrato de API — escrita de casting (146, US1)

Herda as convenções gerais (144): erro `{"error":{"message","fields"}}`; sessão obrigatória
(`api_login_required`). Ações de escrita retornam o recurso atualizado (o evento serializado).

## `POST /api/roles/<role_id>/assign`

- Escala/atualiza/desescala o talento de um cargo. Body: ver data-model.md.
- **RBAC**: CASTING ou SUPERADMIN (mesmo gate de casting do Jinja). Teto de cachê
  (`cache_cap`) só ultrapassável por SUPERADMIN — aplicado no servidor.
- **200**: `serialize_event_detail(event, user, impersonate)` — evento atualizado.
- **403**: `{"error":{"message":"Sem permissão"}}` (papel sem casting).
- **404**: role inexistente.
- Efeitos colaterais (e-mails) idênticos ao handler Jinja.

## Fora de escopo desta fatia (US2/US3 e fatias futuras)

`POST /api/events/<id>/roles` (adicionar cargo), `DELETE /api/roles/<id>` (remover),
`POST /api/roles/<id>/invite`, `.../dismiss`, `.../restore`, `.../figurino-done` — US2/US3.
Venda/pagamentos/contrato/logística/agrupamento/criar-evento/ensaio/sync/excluir — fatias
seguintes.
