# Contratos de API — Feature 297

Sete endpoints: três alterados, quatro novos. Todos sob `/api`, que o `frontend/server.js` já
proxia — nada a acrescentar em `BACKEND_PREFIXES`. Erro sempre no envelope de `json_error`
(`{"error": {"message", "fields"}}`).

Papéis do ERP: `ARTISTA_3D` ou `SUPERADMIN`, pelo `require_3d_access()` que a 200 criou.

---

## 1. `GET /api/nfc/<code>` *(alterado)* — público, sem login

A resolução que a página da tag consome. **O shape continua o mesmo para código inexistente, tag
desativada e tag sem vídeo pronto** — é a invariante SC-006, herdada da 255, e a razão de a página
nunca mostrar erro.

Resposta, sempre `200`:

```jsonc
{
  "product":  { "name": "...", "photo_url": "..." } | null,
  "campaign": null,
  "deliveries": [                       // só entregas com processing_status = "pronto"
    { "kind": "video", "title": "...", "media_url": "/api/nfc/<code>/entregas/<id>/media",
      "width": 1080, "height": 1920 }   // NOVO: dimensões, para a página reservar o palco
  ],
  "instagram_url": "https://www.instagram.com/mantoproducoes",
  "spotify_url":   "https://open.spotify.com/intl-pt/artist/...",   // NOVO
  "intro_video_url": "/api/nfc/abertura/video?v=<marca>" | null,    // NOVO, null se não cadastrado
  "aceita_recado": true                                             // NOVO
}
```

**Regras que não mudam**: incrementa `access_count` uma vez por resolução; código inexistente e tag
inativa saem antes do incremento; `spotify_url`, `instagram_url` e `intro_video_url` viajam **também**
no shape vazio, porque o menu genérico precisa dos dois botões externos.

**Por que `width`/`height`**: hoje a página não reserva altura e o layout pula quando o vídeo carrega
os metadados. Com as dimensões no payload, o palco nasce do tamanho certo.

---

## 2. `GET /api/nfc/<code>/entregas/<id>/media` *(inalterado)* — público

Continua exatamente como está (`app/api/nfc_read.py:46-82`): `send_file(conditional=True,
max_age=86400)`, `206` com `Range`, 404 genérico para qualquer negativa. A única diferença de
comportamento é indireta: o arquivo passa a ser dez vezes menor.

Passa a devolver 404 também para entrega que não está `pronto`.

---

## 3. `GET /api/nfc/abertura/video` *(novo)* — público, sem login

Serve o vídeo de abertura do sistema. Um arquivo só, o mesmo para todas as tags.

- `200` com `send_file(conditional=True, max_age=3600)` e `video/mp4`.
- `404` no envelope se nenhuma abertura foi cadastrada.
- `@limiter.limit("120 per minute")`, o mesmo valor folgado da mídia da tag.
- Aceita `?v=<marca>` e ignora: o parâmetro existe só para furar cache do navegador quando o dono
  troca o arquivo.

Não conflita com `GET /api/nfc/<code>`: são três segmentos contra dois.

---

## 4. `POST /api/nfc/<code>/recados` *(novo)* — público, sem login

```jsonc
// requisição
{ "message": "texto obrigatório, até 1000 caracteres", "author_name": "opcional, até 120" }

// 201
{ "ok": true }
```

- `@limiter.limit("10 per hour")` — mesmo valor de `POST /api/cadastro` e dos formulários públicos.
- `400` com `fields` quando o texto está vazio ou passa de 1000 caracteres:
  `{"error": {"message": "...", "fields": {"message": "Escreva sua mensagem."}}}`.
- **Código inexistente ou tag desativada devolvem `201` também** — a mesma indistinguibilidade da
  resolução. Nada é gravado, e a cliente vê o agradecimento. Revelar "esse código não existe" a quem
  posta seria o mesmo vazamento que o SC-006 fecha na leitura.
- Grava `client_id` copiado da tag no instante do envio.
- Emite a notificação do sino em transação curta e à prova de falha: falhar o aviso **não** desfaz o
  recado (regime B de `app/api/formularios_write.py:73-87`).

---

## 5. `POST /api/3d/nfc/<tag_id>/entregas` *(alterado)* — ARTISTA_3D, SUPERADMIN

Multipart, como hoje, com dois campos a mais:

| Campo | Valor | Observação |
|---|---|---|
| `file` | o vídeo | Mesmas extensões e teto de 250 MB de hoje |
| `kind` | `"video"` | Inalterado |
| `title` | texto opcional | Inalterado |
| `com_moldura` | `"true"` / `"false"` | **NOVO**. Ausente equivale a `true`, para que a caixinha marcada seja também o default do servidor |

A resposta continua sendo `{tag: ...}` no shape de `GET /api/3d/nfc`, agora com a entrega em
`processing_status: "pendente"`. **A requisição retorna assim que o arquivo está no disco** — a
conversão acontece depois, na thread de fundo. É isso que cumpre o SC-003.

`400` com `fields` nos mesmos casos de hoje (sem arquivo, extensão fora da allowlist, acima de
250 MB).

---

## 6. `POST /api/3d/nfc/<tag_id>/entregas/<id>/reprocessar` *(novo)* — ARTISTA_3D, SUPERADMIN

```jsonc
{ "com_moldura": true }     // opcional; omitido mantém a escolha atual da entrega
```

Devolve `{tag: ...}` com a entrega em `pendente`. Parte do **mestre**; se a entrega não tiver mestre
(as dez antigas, antes da primeira conversão), parte do arquivo entregue.

`409` no envelope se a entrega já está `pendente` ou `processando` — evita duas filas para o mesmo
vídeo.

---

## 7. `PUT /api/3d/nfc/moldura` e `PUT /api/3d/nfc/abertura` *(novos)* — ARTISTA_3D, SUPERADMIN

Multipart com um campo `file`. Guardam com nome fixo em `nfc_media/sistema/` e escrevem o caminho em
`site_settings`.

| Rota | Aceita | Recusa com `400` + `fields` |
|---|---|---|
| `.../moldura` | `.png` | Extensão diferente; PNG **sem transparência real** (`imaging.tem_transparencia_real`) — uma moldura opaca cobriria o vídeo inteiro |
| `.../abertura` | `.mp4`, `.mov`, `.webm`, `.m4v`, até 250 MB | Mesmas regras do vídeo da tag |

Resposta: `{ "moldura_url": "...", "atualizada_em": "..." }` e o equivalente para a abertura.

**Não existe GET em JSON deste estado, de propósito.** `GET /api/3d/nfc/moldura` devolve o PNG (ou
404) e `GET /api/nfc/abertura/video` devolve o vídeo (ou 404). O diálogo do ERP precisa carregar a
prévia de qualquer maneira, então é o próprio `onLoad`/`onError` dessa prévia que responde se o
arquivo existe — uma requisição em vez de duas. Depois do primeiro `PUT`/`DELETE` da sessão, a
resposta do servidor passa a mandar.

**A abertura passa pela mesma conversão** dos vídeos de tag, sem moldura: é um arquivo público
servido a todo mundo que encosta o celular numa luminária, então tem de ser leve pelo mesmo motivo.

`DELETE` nas duas rotas remove o arquivo e volta a coluna para `NULL`. Sem moldura cadastrada, todo
envio sai sem moldura, com aviso. Sem abertura cadastrada, a página abre direto no menu.

---

## 8. `GET /api/3d/nfc/<tag_id>/recados` *(novo)* — ARTISTA_3D, SUPERADMIN

```jsonc
{ "items": [ { "id": 1, "message": "...", "author_name": "..." | null,
               "created_at": "2026-09-10T21:03:00", "read_at": null } ],
  "unread_count": 1 }
```

`POST /api/3d/nfc/<tag_id>/recados/lidos` marca todos como lidos e devolve quantos mudaram.

O `GET /api/3d/nfc` (lista de gestão) ganha, por tag, `messages_count` e `messages_unread`, para o
card mostrar o selo sem uma requisição por tag.

---

## 9. Envelope do 429 *(mudança global, pequena)*

Hoje não existe `@app.errorhandler(429)` (`app/__init__.py:782-801` registra só 404, 500, 403 e
413), então o `flask-limiter` devolve HTML cru e o front mostra "Ocorreu um erro inesperado"
(`packages/api-client/src/client.ts:115-124`).

Passa a existir um handler que devolve, para qualquer rota sob `/api`:

```jsonc
{ "error": { "message": "Muitas tentativas. Aguarde um instante e tente de novo." } }
```

Corrige de uma vez as treze rotas públicas que já têm limite de taxa e hoje falham em silêncio.
