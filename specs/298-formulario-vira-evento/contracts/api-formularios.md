# Contrato — endpoints de formulário (feature 298)

Todos devolvem JSON. Erro no envelope `json_error` (`{"error": {"message", "fields"}}`). Os gates são
funções chamadas no início da view (Princípio XIII). As linhas entram na tabela de `docs/01` §4.3, e
cada módulo tocado **ganha** um comentário `RBAC:` no topo, que hoje não existe.

- `_require_vendas` = COMERCIAL, FINANCEIRO e SUPERADMIN (`formularios_admin_read.py:26-29`).
- `_can_create_event` = COMERCIAL e SUPERADMIN (`_CAN_CREATE`, `calendar/routes.py:60`).

**Mensagens de conflito (409):**
- ação sobre formulário cujo destino mudou → "Este formulário já tem destino.";
- reabrir o que já foi reaberto → "Este formulário não está mais encerrado.".

**Campos novos são opcionais no React** até o servidor e o site estarem na mesma versão (portão da
constituição).

## Novos

### `POST /api/formularios/respostas/<id>/encerrar` — `_require_vendas`
```json
{ "motivo": "<codigo de motivos_encerramento>", "frase": "obrigatória se motivo=outro, até 300" }
```
- **200** → `{ "response": <resumo> }`
- **400** → motivo inválido, ou `outro` sem frase (`fields.motivo` / `fields.frase`)
- **404** → formulário inexistente
- **409** → o formulário já tem evento, ou já está encerrado
- **422** → formulário do histórico, que chegou antes do corte e não se encerra

Efeitos: grava as 4 colunas, `audit("formulario.encerrado", …)` e marca como lidos, para todos, os
avisos do sino desse formulário.

### `POST /api/formularios/respostas/<id>/reabrir` — `_require_vendas`
- **200** → `{ "response": <resumo> }`
- **409** → "Este formulário não está mais encerrado."

Efeitos: limpa as 4 colunas e grava `audit("formulario.reaberto", …)`. Não reemite aviso.

### `POST /api/formularios/respostas/<id>/manter-entre-repetidos` — `_require_vendas`
Mantém `<id>` e encerra como `repetido` os demais formulários **sem destino**, desde o corte, com o
mesmo `contact_phone`. É uma transação só, com as linhas bloqueadas, e uma `audit()` por formulário
encerrado.
- **200** → `{ "response": <resumo>, "encerrados": [ids] }`
- **409** → `<id>` já não está sem destino
- **422** → `<id>` não tem telefone

### `POST /api/formularios/respostas/<id>/sugestao/<event_id>/confirmar` — `_require_vendas`
Liga pelo núcleo (`source="manual"`, `decisao_humana=True`).
- **200** → `{ "response": <resumo>, "divergencia_cliente": null | {"formulario": {id, nome}, "evento": {id, nome}} }`
- **404** → par inexistente, ou evento cancelado
- **409** → o formulário já tem destino, ou o evento já tem formulário

### `POST /api/formularios/respostas/<id>/sugestao/<event_id>/descartar` — `_require_vendas`
Grava o par em `form_response_dismissed_events` com `INSERT … ON CONFLICT DO NOTHING`.
- É idempotente: responde **200** `{ "ok": true }` também na segunda vez.
- É definitivo: não há rota para desfazer (decisão do dono, 11/09). A tela pede confirmação antes. A
  ligação à mão pela tela Formulários continua possível.

### `POST /api/formularios/respostas/<id>/usar-cliente-do-evento` — `_require_vendas`
Resolve a divergência de cliente (FR-015). O formulário passa a ter a cliente do evento, pela mesma
escolha do núcleo, com `client_link_source='evento'`. O evento não é alterado.
- **200** → `{ "response": <resumo> }`
- **409** → o formulário não tem evento, ou o evento não tem cliente

### `GET /api/formularios/respostas/<id>/para-evento` — `_can_create_event`
Só leitura: **não** marca aviso como lido. O formato está em `contracts/pre-evento.md`.
- **200** → `{ "form_response": <resumo>, "valores": {...}, "origem": [...], "observacoes": [...], "alertas": [...], "eventos_da_cliente": [...] }`
- **403** → papel sem permissão (FINANCEIRO, CASTING…)
- **409** → "Este formulário já tem destino."

## Alterados

### `GET /api/formularios/respostas?filtro=` — `_require_vendas`
- **`filtro`**: aceita `sem_destino`, `com_evento`, `encerrados` e `historico`. Vazio lista todos.
  Valores antigos, como `sem_evento`, caem em "todos", sem erro.
- **`counts`**: `{ total, sem_destino, com_evento, encerrados, historico, corte }`, onde `corte` é
  AAAA-MM-DD, dia em SP.
- **`truncado`**: `true` quando o filtro tem mais que o limite (200).
- **Carregamento**: `joinedload(client, closed_by)`; o corte é calculado uma vez por requisição.

### `GET /api/formularios/respostas/search` — `_require_vendas`
Mesmo resumo novo.

### Resumo da resposta (`_response_summary`, `formularios_admin_read.py:38`)
Acrescenta:
- `destino`, calculado por `formularios_ops.destino_de(response, corte)`, nunca no serializador:
  `"sem_destino" | "com_evento" | "encerrados" | "historico"`;
- `tipo_rotulo` ("Festa" / "Corporativo");
- `closed_reason`, `closed_reason_label`, `closed_note`, `closed_by_name` e `closed_at`.

`created_at` e `closed_at` passam a sair com `+00:00`.

### Detalhe `GET /api/formularios/respostas/<id>` — `_require_vendas`
Acrescenta:
- `sugestao`, no mesmo formato da linha da Home;
- `divergencia_cliente` (`null` ou `{formulario: {id, nome}, evento: {id, nome}}`), recalculada a cada
  leitura;
- `motivos_encerramento: [{codigo, rotulo}]`;
- `flags: { pode_encerrar, pode_reabrir, pode_criar_evento }`, ao lado de `can_edit_structure`.

O efeito de marcar lido para quem abre continua.

### `POST /api/formularios/respostas/<id>/vincular-evento` — `_require_vendas`
- Deixa de sobrescrever. **409** quando o formulário já tem evento.
- Liga pelo núcleo.
- A resposta muda de `{event_id, event_title}` para `{ "response": <resumo>, "divergencia_cliente": … }`.
  O hook `useLinkEvent` do front muda junto.

### `POST /api/events` — `_can_create_event`
Com `form_response_id`, o formulário é bloqueado (`FOR UPDATE`) **antes** de inserir no Google e fica
bloqueado até o commit. Se ele já tem evento → **409**, sem tocar o Google. O vínculo passa pelo
núcleo: traz a cliente, limpa o encerramento e apaga o sino.

### `PATCH /api/events/<id>` e `PATCH /api/events/<id>/form-response` — `_can_create_event`
- Com um formulário ligado a **outro** evento → **409** "Este formulário já tem destino.".
- Hoje o primeiro ignora em silêncio e o segundo responde com outra mensagem.
- O vínculo passa pelo núcleo.

### `POST /api/formularios/<tipo>` (envio público)
Sem mudança para a cliente.
- **Ordem**: `attempt_auto_link_client` roda antes de `_attempt_auto_link` (preserva `auto_phone` e o
  preenchimento da ficha).
- **Aviso**: o sino **não** é emitido quando o formulário já chega ligado a um evento.

## CLI (correções únicas; sem `--execute` só contam; rodam com `MANTO_SEM_THREADS=1`)

- **`flask formularios-avisos-resolvidos [--execute]`** (FR-019): marca como lidos, num UPDATE em lote,
  os avisos `KIND_FORM_RESPONSE` não lidos de formulários com evento ou encerrados.
- **`flask formularios-cliente-do-evento [--execute]`** (FR-020): dá a cliente do evento aos
  formulários desde o corte que já estão ligados a evento com cliente e continuam sem cliente, pela
  mesma escolha do núcleo.
