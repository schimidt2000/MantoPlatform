# Contratos da API — 352

Erros no envelope de `json_error`: `{"error": {"message": str, "fields": {campo: msg}}}`.

## Objeto `fornecedor`

```json
{
  "id": 12,
  "nome": "Thunder Print 3D",
  "pix": "64.731.999/0001-21",
  "categoria_padrao": "Marketing",
  "ativo": true,
  "gastos": 3,
  "total_aprovado": 1850.0,
  "ultimo_gasto": "2026-11-06"
}
```

`gastos`, `total_aprovado` e `ultimo_gasto` só vão para Financeiro/Superadmin (`null` no objeto
devolvido pelas escritas quando não calculado). `ultimo_gasto` é a maior `expense_date` dos gastos
ligados (`null` sem gastos); `total_aprovado` soma os ligados com `status = "aprovado"`.

## `GET /api/gastos/fornecedores`

RBAC: qualquer usuário logado. Não gestor recebe só `ativo = true`, sem os três totais.

```json
{
  "fornecedores": [ /* fornecedor, ordem alfabética sem acento */ ],
  "categorias": ["Figurino", "Escritório", "Marketing", "Manutenção", "Outros"],
  "can_manage": true
}
```

## `POST /api/gastos/fornecedores`

RBAC: Financeiro, Superadmin (403 `"Sem permissão"`).
Corpo: `{"nome": str, "pix": str?, "categoria_padrao": str?}` → **201** `fornecedor`.
400: `fields.nome` ("Informe o nome do fornecedor." | "Já existe um fornecedor com este nome."),
`fields.categoria_padrao` ("Selecione uma categoria da lista.").

## `PATCH /api/gastos/fornecedores/<id>`

RBAC: Financeiro, Superadmin. Corpo parcial: `nome`, `pix`, `categoria_padrao` (`""`/`null` limpa),
`ativo` (bool). → **200** `fornecedor`. Renomear reescreve `supplier_name` dos gastos ligados.
404 `"Fornecedor não encontrado"`; 400 como no `POST`.

## `POST /api/gastos/fornecedores/<id>/juntar`

RBAC: Financeiro, Superadmin. Corpo: `{"destino_id": int}`. `<id>` é o que deixa de existir.
→ **200** `{"fornecedor": fornecedor_destino, "gastos_movidos": int}`.
404 se `<id>` não existe; 400 `fields.destino_id` ("Selecione outro fornecedor.") se o destino é o
próprio ou não existe.

## Alterados

- `POST /api/gastos` (multipart) e `PATCH /api/gastos/<id>` (JSON): campo opcional `fornecedor_id`
  (int). Só vale com `disbursement_type = "fornecedor"`; id inexistente é ignorado (cai no nome).
- Objeto de gasto (`_expense_dict`): ganha `fornecedor_id` (int | null). No React é `fornecedor_id?:`
  (opcional — `docs/00` §6.21).
