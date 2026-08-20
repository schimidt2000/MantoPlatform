# Contracts — Feature 255: Tags NFC

Todos os endpoints são JSON no blueprint `api_bp` (`/api/*`), servidos em produção pelo proxy do `frontend/server.js` (prefixo `/api` já listado em `BACKEND_PREFIXES` — nada a fazer no proxy).

## Público (sem login)

### `GET /api/nfc/<code>`

Resolve o código de uma tag. **Sempre 200**, mesmo shape — código inexistente é indistinguível de tag desativada (SC-006).

```jsonc
// código válido e ativo
{
  "product": { "name": "Luminária Manto v1", "photo_url": "/uploads/acervo_3d_photos/<uuid>.jpg" },
  "campaign": null,            // gancho v2 — hoje SEMPRE null
  "instagram_url": "https://instagram.com/<handle oficial>"
}

// código inexistente OU tag desativada
{
  "product": null,
  "campaign": null,
  "instagram_url": "https://instagram.com/<handle oficial>"
}
```

- Lookup case-insensitive (normaliza para maiúsculas).
- Efeito colateral (só tag válida/ativa): `access_count += 1`, `last_accessed_at = now` — falha na métrica não afeta a resposta.
- **Proibido** no payload v1: qualquer dado do evento/cliente (FR-009).
- `photo_url` é caminho relativo — o front usa `assetUrl()`.

## Admin (RBAC: `ARTISTA_3D` ou `SUPERADMIN`, via `require_3d_access`)

### `GET /api/3d/nfc`

Lista completa (sem paginação — dezenas de linhas), ordenada por item e `sequence`.

```jsonc
{
  "tags": [
    {
      "id": 1,
      "code": "01-K7M3QF",
      "sequence": 14,                       // nº humano por produto — destaque na UI
      "item": { "id": 3, "name": "Luminária Manto v1", "photo_url": "/uploads/...", "nfc_prefix": "01" },
      "event": { "id": 210, "title": "Show Maria 15 anos", "start_at": "2026-09-12T19:00:00" } , // ou null
      "client_name": "Maria Silva",         // client_of_event(event) — ou null
      "is_active": true,
      "notes": null,
      "access_count": 0,
      "last_accessed_at": null,             // ISO ou null
      "created_at": "2026-08-20T14:00:00"
    }
  ]
}
```

### `POST /api/3d/nfc/lote`

Gera tags avulsas (estoque). Body: `{ "item_id": 3, "quantity": 5 }`.
- 400 `json_error` com `fields` se: item inexistente, item sem `nfc_prefix`, quantidade fora de 1–999.
- 200: `{ "tags": [ ...mesmo shape da lista... ] }` (as recém-criadas).

### `PATCH /api/3d/nfc/<id>`

Edita **apenas** os mutáveis: `{ "event_id": 210 | null, "is_active": true|false, "notes": "..." }` (todos opcionais; ausente = não altera).
- 400 se `event_id` não existe; 404 se tag não existe.
- 200: `{ "tag": { ...shape da lista... } }`.
- Não existe DELETE — por contrato.

## Alterações em endpoints existentes

- `PATCH`/`POST` do Acervo 3D (`app/api/impressoes3d_write.py`): aceitam campo opcional `nfc_prefix` (string vazia = remover habilitação). `serialize_acervo_item` passa a incluir `nfc_prefix`.
- `add_event_gift`/`update_event_gift` (ops): passam a disparar `sync_event_gift_tags` — sem mudança de contrato HTTP; o payload do presente não muda.

## Superfícies (URLs de navegador)

- **Pública**: `/nfc/<code>` na raiz do domínio (`app.mantoproducoes.com.br`) — servida pelo bundle `apps/public` via entrada nova `NFC_PREFIX` no `frontend/server.js` (mecanismo idêntico a `CADASTRO_PREFIX`; sem reescrita de URL). Sem login, mobile-first.
- **Admin**: `/3d/tags` no ERP (`apps/internal`), rota irmã de `/3d/acervo` e `/3d/fila`, entrada "Tags NFC" na navegação da seção 3D.
