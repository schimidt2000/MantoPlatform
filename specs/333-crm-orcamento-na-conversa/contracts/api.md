# Contratos — 333 Orçamento e formulário pela conversa

Endpoints novos com `api_login_required` e `pode_conversas()` (COMERCIAL/SUPERADMIN, papel real) no início da view; erro
no envelope de `json_error` com `codigo` e `fields`.

## `POST /api/conversas/<id>/orcamento`

- **Corpo**: `{"orcamento_id": int, "chave_envio": str, "cliente"?: {"id": int} | {"nome": str, "telefone": str}}`.
- **201** (pedido novo) ou **200** (a mesma chave): `{"envio": {...}, "mensagens": [mensagem…], "conversa": {...}}`.
  - `mensagens`: as partes do texto e o PDF, no formato da conversa.
  - `conversa`: com a ficha ligada.
- **Recusas**:
  - 404 `nao_encontrada`: conversa ou orçamento inexistente;
  - 422 `invalido`: `fields.chave_envio`, `fields.orcamento` ("Este orçamento não tem a mensagem pronta. Use
    Recalcular e envie o novo orçamento.") ou `fields.cliente` ("Selecione a ficha da cliente ou informe nome e
    telefone.", ficha inexistente, telefone inválido);
  - 409 `janela_fechada` / `envio_travado` e 503 `nao_configurado`: as do envio comum. Nessas, nada é criado.

## `POST /api/conversas/<id>/ficha`

- **Corpo**: `{"client_id": int}` ou `{"nome": str, "telefone": str}`.
- **200**: `{"conversa": {...}, "reaproveitada": bool}`. `reaproveitada` é `true` quando o telefone informado já era de
  uma ficha.
- **Recusas**: 404 conversa; 422 `fields.cliente` (ficha inexistente), `fields.nome` e `fields.telefone`.

## `DELETE /api/conversas/<id>/ficha`

- **200**: `{"conversa": {...}}` sem ficha. A ligação automática não volta a agir nesta conversa.

## `GET /api/conversas/<id>/formularios`

- **200**: `{"formularios": [{"tipo": "comum", "titulo": "Pré-contrato", "link": "https://app.mantoproducoes.com.br/f/pre-contrato", "texto": "Oi, Ana! …"}, {"tipo": "corporativo", …}]}`.

## Alterados

- `GET /api/orcamento/historico`: cada linha ganha `enviado_em` (ISO UTC do último envio, ou `null`).
- `GET /api/orcamento/historico/<id>`:
  - ganha `cliente` (`{"id", "nome"}` ou `null`);
  - ganha `envios`: `[{"id", "conversa_id", "conversa_nome", "canal", "autor", "quando"}]`, do mais novo ao mais antigo.
- `GET /api/events/new/prefill?orcamento_id=`: ganha `cliente` (`{"id", "nome"}`), só com o orçamento ligado.
- `serializar_conversa` (lista e conversa): ganha `ficha_manual`.
