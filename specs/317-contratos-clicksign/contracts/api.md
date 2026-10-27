# Contratos de interface — Feature 317

Erros no envelope de `json_error` (`app/api_utils.py:36`). Toda chave nova no JSON de leitura é **opcional** no TS
(armadilha 21: o bundle em cache não pode cair). `undefined` = servidor antigo (não desenha); `null` = falha do bloco
(`AvisoDeFalha`).

## Leitura

### `GET /api/events/<id>` — bloco `contrato` (dentro de `show_comercial`; COMERCIAL, FINANCEIRO, SUPERADMIN)

```jsonc
"contrato": {
  "integracao_ligada": true,
  "situacao": "aguardando",            // assinado | assinado_manual | aguardando | vencido | recusado | sem_contrato
  "rotulo": "Aguardando assinatura — vence em 3 dias",
  "cor": "amarelo",                     // vermelho | amarelo | cinza | verde
  "escopo": "evento",                   // evento | grupo_principal | grupo_outro (molde da cobrança)
  "documento": {                        // vigente; null em sem_contrato/assinado_manual
    "id": 12, "nome": "25102026 + (11) 98492-5407 + Hot Wheels",
    "status": "running", "prazo": "2026-10-26T14:42:00", "assinado_em": null,
    "canal": "whatsapp", "vinculo_origem": "auto"
  },
  "outros_documentos": [ { "id": 9, "nome": "…", "status": "canceled" } ],
  "pode_cobrar": true,                  // só COMERCIAL/SA, principal, aguardando, venda viva
  "motivo_bloqueio": null,              // texto pt-BR quando pode_cobrar=false
  "ultima_cobranca": { "por": "Thays", "em": "2026-10-22T14:05:00" },
  "pode_conferir": true,                // COMERCIAL/SA e venda viva
  "a_conferir": [                       // documentos a conferir parecidos com esta venda (data ±3 / telefone)
    { "id": 30, "nome": "…", "data_lida": "2026-10-25", "telefone_lido": "5511…", "motivo": "empate" }
  ]
}
```

`mensagens` ganha (opcionais): `contrato_canal`, `contrato_prazo` (`"26/10"`).

### `GET /api/dashboard` — `comercial.contratos` (COMERCIAL, FINANCEIRO, SUPERADMIN)

```jsonc
"contratos": {                          // null se o bloco falhar; ausente em servidor antigo
  "integracao_ligada": true,
  "para_cobrar": [Linha], "vencidos": [Linha], "sem_contrato": [Linha],
  "a_conferir": [LinhaConferir], "ja_aconteceu": [Linha],
  "resumo": { "por_cor": {"vermelho": 2, "amarelo": 1, "cinza": 4}, "para_agir": 3 },
  "pode_cobrar": true
}
// Linha
{ "event_id": 812, "titulo": "…", "cliente": "Ana", "data_evento": "2026-10-25", "dias_ate_o_evento": 3,
  "situacao": "aguardando", "severidade": "vermelho", "selo": "Vence amanhã",
  "documento_id": 12, "prazo": "2026-10-26T14:42:00", "canal": "whatsapp",
  "ultima_cobranca": { "por": "Thays", "em": "…" } | null,
  "mensagem": { "characters": "…", "date_line": "…", "location": "…" } }   // para o "Cobrar contrato" da Home
// LinhaConferir
{ "documento_id": 30, "nome": "…", "data_lida": "2026-10-25", "telefone_lido": "5511…", "motivo": "empate",
  "sugestoes": [ { "event_id": 812, "titulo": "…", "data_evento": "2026-10-25", "cliente": "Ana" } ] }
```

### `GET /api/contratos/a-conferir` (COMERCIAL, FINANCEIRO, SUPERADMIN)

Lista completa de `LinhaConferir` (a Home mostra 6 e "Mostrar todas"; o diálogo "Ligar contrato da ClickSign" do evento
usa esta lista).

## Escrita (sessão; 401 sem login; 403 fora do papel)

| Método e rota | Papéis | Corpo | Respostas |
|---|---|---|---|
| `POST /api/contratos/<doc_id>/cobranca` | COMERCIAL, SA | — | 201 `{ultima_cobranca}` · 404 doc · 409 `{codigo: "nao_cobravel", motivo}` (assinado, vencido, venda cancelada, satélite) |
| `POST /api/contratos/<doc_id>/ligar` | COMERCIAL, SA | `{event_id}` | 200 `contrato` do evento · 404 · 409 `cancelado` (trava 312) / `ja_ligado` / `tipo_fora` |
| `POST /api/contratos/<doc_id>/desligar` | COMERCIAL, SA | — | 200 · 404 · 409 `nao_ligado` |
| `POST /api/contratos/<doc_id>/descartar` | COMERCIAL, SA | — | 200 · 404 · 409 `ja_ligado` |

Ligar sempre resolve o **principal** do `event_id` recebido. Rotas sob `/api/contratos/` ficam fora de
`PREFIXOS_DA_TELA` do `verify_312`; a trava do cancelado é aplicada no núcleo (`recusar_se_cancelado_para_ligar`).

## Aviso da ClickSign

`POST /api/webhooks/clicksign` — sem sessão; `limiter 60/min`; corpo ≤ 64 KB.

- `Content-Hmac: sha256=<hex>` = HMAC-SHA256(`clicksign_webhook_secret`, corpo bruto) — confere o atual e o anterior
  (24 h) com `hmac.compare_digest`.
- Inválido ou sem segredo configurado → **404**, nada acontece.
- Válido → **200** `{"success": true}` imediato; dispara a sincronização incremental em thread (ou na hora com
  `CLICKSIGN_AVISO_SINCRONO=1`, costura do verify). O conteúdo do aviso **não** é interpretado.

## Comandos (Shell do Render, `MANTO_SEM_THREADS=1`)

- `flask clicksign-sincronizar [--desde AAAA-MM-DD] [--aplicar]` — sem `--aplicar` só conta (R-08).
- `flask clicksign-webhook --listar` · `--registrar <url> [--aplicar]` · `--remover <id> [--aplicar]` — cadastra o aviso
  na ClickSign e grava o segredo devolvido (R-09). Nunca roda sozinho na subida.

## Saída para a ClickSign (cliente HTTP `app/integracoes/clicksign_client.py`)

Só GET, mais `POST/DELETE /webhooks` pelo comando. Base `CLICKSIGN_API_BASE`, `Authorization: <token>`,
`Accept/Content-Type: application/vnd.api+json`, timeout `(10, 30)`, travado por padrão (`travada=True`); exceções
`ClicksignIndisponivel` (não sei: timeout, 5xx, 429, corpo inválido), `ClicksignRecusou` (4xx), `ClicksignTravada`
(subclasse de indisponível). Lê `X-Rate-Limit-Remaining` e dorme quando < 5.
