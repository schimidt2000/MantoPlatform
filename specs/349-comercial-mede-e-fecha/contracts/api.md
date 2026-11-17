# Contrato da API — 349

Todas as rotas: `api_login_required` + `pode_conversas(current_user)` no início da view (COMERCIAL e SUPERADMIN, papel
real); sem papel → **403** `{"error": {"message": "Sem permissão"}}`. Recusas do núcleo no envelope de `json_error` com
`codigo` (`invalido` 422 com `fields`, `nao_encontrada` 404). Horários em ISO com `+00:00`.

## Objetos

```jsonc
// Pessoa
{ "id": 7, "nome": "Ana" }

// VendaResumo — em cada item de GET /api/conversas (campo `venda`, opcional no React)
{
  "anuncio": true,
  "etapa": "orcamento",            // chegou | orcamento | formulario | evento | pagou | avaliou
  "qualificada": true,
  "perdida": { "motivo": "preco", "rotulo": "Achou caro" } | null,
  "lembrete_em": "2026-11-18T12:00:00+00:00" | null
}

// Venda — GET /api/conversas/<id>/venda e respostas das escritas
{
  "conversa_id": 12,
  "etapa": { "chave": "orcamento", "rotulo": "Orçamento enviado" },
  "anuncio": true,
  "primeira_resposta": {
    "recebida_em": "…" | null,
    "resposta_em": "…" | null,
    "minutos": 12 | null,
    "autor": Pessoa | null,
    "origem": "plataforma" | "celular" | "outro" | null
  },
  "perda": { "motivo": "preco", "rotulo": "Achou caro", "frase": null, "em": "…", "por": Pessoa | null } | null,
  "qualificacao": {
    "qualificada": true,
    "pela": "regra" | "decisao",
    "decisao": "qualificada" | "nao_qualificada" | null,
    "decidida_por": Pessoa | null,
    "decidida_em": "…" | null,
    "pontos": 3,
    "corte": 3,
    "sinais": [ { "chave": "data_proxima", "rotulo": "Data do evento em até 90 dias", "pontos": 2 } ]
  },
  "lembrete": { "em": "…", "para": Pessoa | null } | null,
  "parado": { "orcamento_em": "…", "dias": 5 } | null,
  "fechamento": { "orcamento_id": 88 | null, "cliente": { "id": 3, "nome": "Ana Souza" } | null, "vendedor": Pessoa | null },
  "motivos_de_perda": [ { "codigo": "preco", "rotulo": "Achou caro", "pede_frase": false } ]
}
```

## Rotas novas (`app/api/conversas_venda.py`)

| Método e rota | Corpo | Sucesso | Recusas |
|---|---|---|---|
| `GET /api/conversas/<id>/venda` | — | 200 `Venda` | 404 |
| `POST /api/conversas/<id>/perdida` | `{ "motivo": "preco", "frase": "…" }` | 200 `{ "venda": Venda }` | 422 `motivo` / `frase`; 404 |
| `DELETE /api/conversas/<id>/perdida` | — | 200 `{ "venda": Venda }` (idempotente) | 404 |
| `POST /api/conversas/<id>/qualificacao` | `{ "decisao": "qualificada" \| "nao_qualificada" \| null }` | 200 `{ "venda": Venda }` | 422 `decisao`; 404 |
| `POST /api/conversas/<id>/lembrete` | `{}` (sempre "amanhã às 9h") | 200 `{ "venda": Venda }` | 404 |
| `DELETE /api/conversas/<id>/lembrete` | — | 200 `{ "venda": Venda }` (idempotente) | 404 |

## Rotas alteradas

### `GET /api/conversas`

- Parâmetros novos: `recorte` ∈ `esperando` · `orcamento_parado` · `anuncio` (outro → 422 `recorte`); `dias` ∈ 2 · 5 ·
  9 (só com `orcamento_parado`; padrão 2; outro → 422 `dias`).
- Cada item ganha `venda: VendaResumo`. O resto não muda.

### `GET /api/conversas/funil`

Campos novos (todos opcionais no React):

```jsonc
{
  "primeira_resposta": { "respondidas": 40, "sem_resposta": 5, "sem_autor": 6, "mediana_minutos": 14, "ate_15_min": 52.5 },
  "qualificadas": 21,
  "perdidas": 9,
  "motivos_de_perda": [ { "codigo": "preco", "rotulo": "Achou caro", "quantidade": 4 } ],
  "grupos": [ { /* …como antes… */ "qualificadas": 8, "perdidas": 3, "mediana_minutos": 11, "ate_15_min": 60.0 } ]
}
```

`ate_15_min` = % das respondidas com resposta em até 15 min; `mediana_minutos` = mediana das respondidas (`null` sem
base). Perdidas = perdidas da coorte que não chegaram a Evento fechado.

### `GET /api/conversas/funil/parados`

Cada conversa ganha: `perdida` (`{motivo, rotulo}` | null), `qualificada` (bool), `primeira_resposta_minutos`
(int | null), `primeira_resposta_sem_autor` (bool), `lembrete_em` (ISO | null).

### `POST /api/events` (feature 152)

- Campo novo opcional `conversa_id` (int). Gate de sempre (`_can_create_event`). Conversa inexistente ou valor não
  inteiro → **400** `fields.conversa_id` (no lote de 17/11 a validação da 348 recusa junto com os outros campos; era 422 aqui), **antes** do Google (nada criado).
- Depois do núcleo: `fechamento_ops.ligar_evento_a_conversa(evento, conversa)` — a ficha da conversa entre as clientes
  do evento (Contratante, se ainda não estiver) e a perda apagada. Ponto único em que a 348 grava a coluna
  `calendar_events.conversa_id`.

## Telas (endereço)

- `/conversas?recorte=orcamento_parado&dias=5` — recorte da lista; `?orcamento=<id>` abre o envio com esse orçamento
  (consumido e apagado).
- `/orcamento?conversa=<id>&cliente=<nome>` — calculadora vinda da conversa.
- `/events/new?orcamento_id=<id>&conversa=<id>` — criação vinda da conversa.
