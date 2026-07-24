# Contrato: Status de aprovação do material de revisão

## `PATCH /api/revisao/asset/<int:asset_id>/status`

Endpoint novo em `app/api/revisao_write.py`, seguindo exatamente o padrão dos endpoints vizinhos
(`api_revisao_finalize_asset`, `api_revisao_replace_asset`): busca o asset, valida RBAC via
`review_ops.can_manage`, delega a regra de negócio a `review_ops.set_asset_status`.

### Autenticação/RBAC

- Requer sessão autenticada (`@api_login_required`, igual aos demais endpoints do blueprint).
- Só quem passa em `review_ops.can_manage(asset.space, current_user)` (criador do espaço ou super
  admin) pode alterar — mesma regra já usada para excluir/substituir material. Sem RBAC novo.

### Request

```
PATCH /api/revisao/asset/42/status
Content-Type: application/json

{ "status": "aprovado" }
```

Valores aceitos para `status`: `"em_revisao"`, `"aprovado"`, `"precisa_ajustes"`, `"rejeitado"`.

### Responses

| Status HTTP | Quando | Corpo |
|---|---|---|
| 200 | Sucesso | `{ "status": "aprovado" }` |
| 400 | `status` ausente ou fora dos 4 valores válidos | `json_error("Status inválido.", 400, fields={"status": "..."})` |
| 403 | Usuário autenticado mas sem `can_manage` no espaço | `json_error("Sem permissão", 403)` |
| 404 | `asset_id` não existe | `json_error("Material não encontrado", 404)` |

### Efeito colateral

Nenhum — só atualiza `ReviewAsset.status`. Não afeta comentários, versões nem o arquivo.

## Alteração em payloads existentes (sem endpoint novo)

`GET /api/revisao/<space_id>` , `GET /api/revisao/<space_id>/asset/<asset_id>` e o corpo de resposta
de `POST /api/revisao/<space_id>/upload` — em qualquer lugar onde `_asset_summary()` já serializa um
`ReviewAsset` — passam a incluir o campo `"status"` (string, um dos 4 valores) no objeto do asset,
sem quebrar consumidores existentes (campo aditivo).

```jsonc
{
  "id": 42,
  "media_type": "video",
  "original_name": "spot_v2.mp4",
  "position": 0,
  "version": 2,
  "is_available": true,
  "days_left": 5,
  "finalized_at": null,
  "file_url": "https://.../review/spot_v2.mp4",
  "status": "em_revisao"   // NOVO
}
```
