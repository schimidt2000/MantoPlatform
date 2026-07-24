# Contrato de API — Figurino (feature 183)

Todas as rotas herdam `@api_login_required`. Auth por cookie de sessão HttpOnly (Flask-Login).
Erros seguem `json_error(msg, status, fields=...)` já padrão do repo.

## `GET /api/figurino` (alterado)

Sem mudança de parâmetros. Resposta: ver `data-model.md` (novo formato de `chars_without_sheet`
com objetos, novo campo `tags` por item).

## `POST /api/figurino` (alterado)

Body adiciona campo opcional `tags: string[]`.

```json
{ "character_name": "Anjo Gabriel", "pieces": [...], "notes": "...", "tags": ["anjo", "natal"] }
```

RBAC: FIGURINO ou SUPERADMIN (sem mudança).

## `PATCH /api/figurino/<id>` (alterado)

Mesmo body de create + `tags`. RBAC: FIGURINO ou SUPERADMIN (sem mudança).

## `POST /api/figurino/faltantes/dispensar` (novo)

Descarta o alerta de um personagem sem ficha para as ocorrências atuais.

**RBAC**: SUPERADMIN apenas (403 para qualquer outro papel, inclusive FIGURINO).

Request:
```json
{ "character_name_norm": "duende 3" }
```

Response `200`:
```json
{ "ok": true, "dismissed_role_ids": [101, 102] }
```

Response `400` se `character_name_norm` não corresponder a nenhum personagem atualmente sem
ficha (nada a descartar):
```json
{ "error": "Nenhum cargo pendente encontrado para esse personagem.", "fields": {} }
```

## `POST /api/figurino/faltantes/associar` (novo)

Vincula todos os cargos de evento atualmente sem ficha daquele personagem à ficha escolhida.

**RBAC**: SUPERADMIN apenas.

Request:
```json
{ "character_name_norm": "duende 3", "sheet_id": 7 }
```

Response `200`:
```json
{ "ok": true, "updated_role_count": 2, "sheet_id": 7 }
```

Response `404` se `sheet_id` não existir:
```json
{ "error": "Ficha não encontrada", "fields": {} }
```

Response `400` se `character_name_norm` não corresponder a nenhum cargo pendente:
```json
{ "error": "Nenhum cargo pendente encontrado para esse personagem.", "fields": {} }
```

## Fluxo de impressão (sem endpoint novo)

O botão "Imprimir" do card abre `/figurinos/<id>/print` (rota Jinja legada existente,
`app/figurino/routes.py`) em nova aba — mesma sessão de cookie, sem mudança de backend.
