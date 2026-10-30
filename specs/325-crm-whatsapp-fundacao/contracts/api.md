# Contratos — 325 Conversas

Erro sempre no envelope de `json_error`: `{"error": {"message": str, "fields": {…}, "codigo"?: str}}`.
Horários com sufixo `+00:00` (UTC). Todos os endpoints internos exigem login (`api_login_required`,
401 JSON) e o gate `_pode_conversas()` = **COMERCIAL ou SUPERADMIN** (função no início da view).

## Público — webhook da Meta (`app/api/whatsapp_webhook.py`)

### `GET /api/webhooks/whatsapp`

Desafio de verificação. Query: `hub.mode=subscribe`, `hub.verify_token`, `hub.challenge`.

- Configurado e `hub.verify_token` == `WHATSAPP_VERIFY_TOKEN` (`compare_digest`) → **200**, corpo =
  `hub.challenge` em `text/plain`.
- Não configurado, modo errado ou token errado → **404** (não confirma existência).

### `POST /api/webhooks/whatsapp`

Aviso da Meta. Cabeçalho `X-Hub-Signature-256: sha256=<hex>` = HMAC-SHA256 do **corpo cru** com
`WHATSAPP_APP_SECRET`.

- Não configurado, sem assinatura ou assinatura inválida → **404**, nada gravado.
- Corpo > 256 KB → **413**, nada gravado.
- Válido → grava `whatsapp_avisos` (`pendente`), commit, **200** `{"ok": true}` e o processamento
  segue fora da requisição (thread; `WHATSAPP_AVISO_SINCRONO=True` processa na hora — costura do
  verify). Limiter `300/min` por IP — mais folgado que os `60/min` da ClickSign, porque cada mensagem
  enviada gera até 3 avisos de status e a Meta manda rajadas de poucos IPs; um 429 não perde nada (a
  Meta reenvia), mas atrasa. Corpo que não é JSON válido → 200 e `descartado` (a Meta não deve
  reenviar lixo).
- **Troca do App Secret**: não há janela com dois segredos (ele é env, não `site_settings`). Trocar =
  atualizar a env no Render e fazer o deploy; durante o deploy os avisos falham e a Meta reenvia.

## Interno — leitura (`app/api/conversas_read.py`)

### `GET /api/conversas`

Query: `busca` (nome, telefone ou nome da ficha; ≥ 2 caracteres), `antes` (cursor = `ultima_mensagem_em`
ISO da última da página anterior). Página de 50, ordenada por `ultima_mensagem_em desc`.

```json
{
  "configurado": true,
  "envio_travado": false,
  "conversas": [
    {"id": 12, "canal": "whatsapp", "nome": "Ana Souza", "telefone": "5511987654321",
     "cliente": {"id": 345, "nome": "Ana Souza"} ,
     "ultima_previa": "Oi, queria um orçamento…", "ultima_mensagem_em": "2026-10-30T19:02:11+00:00",
     "nao_lidas": 2, "janela_aberta": true}
  ],
  "proximo": "2026-10-29T13:00:00+00:00"
}
```

`nome` = nome da ficha, senão `nome_perfil`, senão o telefone formatado. `cliente` é `null` sem vínculo.

### `GET /api/conversas/<id>`

Query: `antes=<mensagem_id>` (página anterior, 50 por vez; sem `antes`, as 50 últimas). 404 se não
existe.

```json
{
  "conversa": {"id": 12, "nome": "…", "telefone": "…", "cliente": {…} , "janela_aberta": true,
               "janela_fecha_em": "2026-10-31T19:02:11+00:00", "nao_lidas": 0},
  "mensagens": [
    {"id": 991, "direcao": "recebida", "tipo": "audio", "texto": null,
     "momento": "2026-10-30T19:02:11+00:00", "situacao": "recebida",
     "autor": null, "origem": "contato", "modelo_nome": null,
     "erro": null,
     "midia": {"id": 77, "estado": "guardada", "mime": "audio/ogg", "tamanho": 18234,
               "nome": null, "url": "/api/conversas/midia/77"}}
  ],
  "tem_mais": false
}
```

`autor` = `{"id", "nome"}` ou `null`; `erro` = `{"codigo", "motivo"}` ou `null`; `midia` = `null` sem
arquivo. Abrir a conversa **não** zera as não lidas (isso é o `POST …/lida`, para o polling não
marcar como lido o que ninguém viu).

### `GET /api/conversas/midia/<midia_id>`

O arquivo (`send_file`, `Content-Type` = `mime`, `Content-Disposition: inline`, `nome_original`).
Sem o papel, mídia inexistente ou `estado != guardada` → **404** (Princípio XIII: não confirma
existência).

### `GET /api/conversas/modelos`

Modelos **aprovados** da conta, lidos da Meta (cache de 5 min por processo).

```json
{"modelos": [{"nome": "retomar_orcamento", "idioma": "pt_BR", "categoria": "MARKETING",
              "texto": "Oi, {{1}}! Ainda pensando na festa…", "variaveis": 1}]}
```

Meta fora / não configurado → 503 `{"error": {"message": "Não foi possível carregar os modelos. Tente novamente."}}`.

## Interno — escrita (`app/api/conversas_write.py`)

Toda escrita leva `chave_envio` (string de 8–64 caracteres gerada pelo navegador por clique). A
mesma chave de novo → **200** com a mensagem já gravada (não envia de novo — FR-018).

### `POST /api/conversas/<id>/mensagens`

- JSON `{"texto": "…", "chave_envio": "…"}` → texto (≤ 4096 caracteres).
- `multipart/form-data` `arquivo`, `legenda?`, `chave_envio` → imagem, documento, áudio ou vídeo
  pelo MIME (teto de tamanho em `plan.md`).

Respostas:
- **201** `{"mensagem": {…}}` (mesmo formato da leitura; `situacao` `enviada` ou `falhou`).
- **409** `codigo: "janela_fechada"` — "A janela de 24 horas desta conversa fechou. Envie um modelo
  aprovado para retomar o contato."
- **409** `codigo: "envio_travado"` — "O envio pelo WhatsApp está travado neste ambiente." (banco
  local sem `WHATSAPP_ALLOW_LOCAL_SEND`).
- **503** `codigo: "nao_configurado"` — "O WhatsApp ainda não foi configurado."
- **422** `fields` — texto vazio, arquivo de tipo não aceito, arquivo acima do teto.
- Falha da Meta no envio **não** é 5xx: a mensagem é gravada `falhou` com o motivo e volta 201 (a
  tela mostra "não entregue" e o "Tentar novamente").

### `POST /api/conversas/<id>/modelo`

JSON `{"nome": "retomar_orcamento", "idioma": "pt_BR", "variaveis": ["Ana"], "chave_envio": "…"}`.
Permitido com a janela fechada. 422 se o modelo não está entre os aprovados ou o número de
variáveis não confere. Mesmos 409/503 de travado e não configurado. 201 com a mensagem
(`tipo: "modelo"`, `texto` = texto final com as variáveis).

### `POST /api/conversas/<id>/lida`

Zera `nao_lidas` e, se houver mensagem recebida e o envio não estiver travado, marca a última como
lida na Meta (melhor esforço: falha só vai para o log). **204**.

## Configuração (`app/config.py`)

| Chave | Default | Observação |
|---|---|---|
| `WHATSAPP_ACCESS_TOKEN` | `""` | segredo, só env (`render.yaml` `sync: false`); token de System User |
| `WHATSAPP_APP_SECRET` | `""` | segredo, só env; assina o webhook |
| `WHATSAPP_VERIFY_TOKEN` | `""` | segredo, só env; desafio do GET |
| `WHATSAPP_PHONE_NUMBER_ID` | `""` | não secreto, mas por ambiente; só env |
| `WHATSAPP_WABA_ID` | `""` | para listar modelos |
| `WHATSAPP_GRAPH_VERSION` | versão fixada em `research.md` | default real |
| `WHATSAPP_GRAPH_BASE` | `https://graph.facebook.com` | default real |
| `WHATSAPP_SUPPRESS_SEND` | `_suppress_whatsapp()` | banco local = travado |
| `WHATSAPP_ALLOW_LOCAL_SEND` | `false` | escape explícito para testar no número de teste |
| `WHATSAPP_AVISO_SINCRONO` | `False` | costura do verify |
| `WHATSAPP_POLL_SEGUNDOS` | `5` | devolvido à tela no `GET /api/conversas` |
| `CONVERSAS_MEDIA_FOLDER` | `instance/conversas_midia` (em `create_app`) | pasta irmã de `uploads`; nunca bucket público |

"Configurado" = `ACCESS_TOKEN`, `APP_SECRET`, `VERIFY_TOKEN` e `PHONE_NUMBER_ID` preenchidos. Sem
isso, `create_app` avisa no log da subida (Princípio XIV) e o módulo some (404/503, menu oculto).
