# Research — Feature 317

Fontes: exploração multi-agente de 22/10/2026 (código da `main` 5781993c, `manto_local` de ~30/09, docs oficiais da
ClickSign em developers.clicksign.com), painel da conta ClickSign (só leitura, Claude in Chrome) e o **Portão 0** contra
a API de produção (só GET, token em variável de ambiente local, nada escrito na ClickSign).

## Portão 0 — a API enxerga os contratos dos fluxos? **Sim.**

Pré-condição descoberta: a API v3 devolve 403 "E-mail do usuário da API não configurado" enquanto o campo de mesmo nome
estiver vazio em Configurações › API. Configurado em 22/10 com o administrador da conta (joao@primedreams.com.br), a
pedido do dono. O token "Plataforma Manto" foi **regerado** no mesmo dia (o anterior apareceu num print do chat).

| Pergunta | Resposta medida |
|---|---|
| Envelopes dos fluxos com formulário aparecem em `GET /api/v3/envelopes`? | Sim: 765 na conta, desde jun/2025; o nome é o mesmo do painel |
| Filtros | `filter[status]=running|closed|canceled|draft`, `filter[created]=AAAA-MM-DD,AAAA-MM-DD`, `filter[modified]=…` (intervalo com vírgula) funcionam |
| Página | `page[size]` máximo **50** (acima → 400 código 118); `page[number]`; `meta.record_count` |
| Signatário | `GET /envelopes/{id}/signers`: `name`, `phone_number`, `email`, `communicate_events = {signature_request: "whatsapp", signature_reminder: "none", document_signed: "whatsapp"}` → o **canal** sai daqui |
| Situação | `attributes.status` do envelope (`running`, `closed` = todos assinaram, `canceled`), `deadline_at`, `created`, `modified` |
| Quando assinou | `GET /envelopes/{id}/events`: `sign` (com `data.signer`), `auto_close`, `document_closed`, `add_signer`, `upload` |
| PDF assinado | `GET /envelopes/{id}/documents/{doc}` → `links.files.signed` (também `original`, `ziped`) |
| Webhooks já cadastrados | Nenhum |
| Limite | `X-Rate-Limit-Remaining` começa em 49–50 por janela de 10 s |

**Volume desde 01/06/2026** (235 envelopes): festa 209 (134 fechados, 70 cancelados, 5 em processo), corporativo 12,
festa com e-mail no lugar do telefone 1, outros 13 (artista, "AF_…", "Declaração…", um sem nome, um com quatro datas,
um só com razão social). Datas: `DDMMAAAA` 150, `DD-MM-AAAA` 57, sem zero 2. O leitor de nome da pesquisa leu 222/235.

## Decisões

### R-01 — Fonte da verdade: API v3 da ClickSign; o aviso é só um "algo mudou"

- **Decisão**: a situação do contrato vem sempre de uma consulta à API. O aviso (webhook) da ClickSign não é
  interpretado: ele só dispara uma **sincronização incremental** por `filter[modified]` desde o último marco (1–2
  requisições). A mesma sincronização roda periodicamente (a cada 30 min, atrás de `MANTO_SEM_THREADS`) e pelo comando
  retroativo.
- **Por quê**: (1) a documentação não garante que `document.key` do aviso seja o id v3 nem traz o id do envelope; (2)
  não há reentrega documentada — um aviso perdido no deploy viraria "a cobrar" para sempre; (3) "o corpo nunca decide
  sozinho" (molde R-11 da 310) — um segredo vazado do espelho não consegue marcar contrato como assinado; (4) 1
  requisição a cada 30 min não é o polling que a ClickSign veta (que é consultar documento a documento em laço).
- **Alternativas**: interpretar o payload (rejeitada: formato não confirmado e forjável); só periódico sem aviso
  (rejeitada: atraso de até 30 min, SC-003 pede 5 min); polling por documento (vetado pela ClickSign).

### R-02 — Chave de vínculo: data + telefone do nome, conferidos pelo signatário

- **Decisão**: normalizar o nome (Unicode NFC — a ClickSign devolve acento decomposto, ex. `Ç` = `C` + U+0327; tirar
  `.pdf`, sufixo ` (N)`, espaços), ler data (`D?D[-]MM[-]AAAA`), telefone `(DD) 9NNNN-NNNN` e tema/razão. O telefone do
  **signatário** (`phone_number` da API) tem precedência sobre o do nome quando os dois existem e divergem → "a conferir".
  Candidatos: vendas vivas cuja data do grupo **ou de qualquer dia do grupo** é a data lida e cujo telefone normalizado
  está em {cliente do evento, contratantes `EventClient`, `FormResponse.contact_phone` ligado}. Único → liga; vários →
  tema contra `tema_evento` do formulário / título (normalizado, sem acento, contém) → único liga, senão "a conferir";
  zero → sugestões (mesmo telefone ±3 dias; mesma data com telefone de outra pessoa do evento) e "a conferir".
- **Por quê**: medido no `manto_local` (52 anexos no padrão): data = evento em 51/52; telefone bate em 40/49; data +
  telefone dá vínculo único e certo em 37/52, 3 empates resolvidos pelo tema, 11 sem candidato (signatário ≠ titular,
  dígito trocado, anexo no evento errado). O "a conferir" captura exatamente esses.
- **Alternativas**: e-mail/CPF (o fluxo de WhatsApp não pede e-mail; só 17 de 46 clientes futuros têm e-mail);
  `metadata` do envelope (os fluxos não preenchem); gerar o contrato pela API com o id da Manto (fora de escopo,
  decisão 4 do dono).

### R-03 — Classificação

`artista` = nome contém "PRESTAÇÃO DE SERVIÇOS ARTÍSTICOS" (após NFC); `cliente` = leu data + (telefone ou e-mail) ;
`outro` = o resto. Só `cliente` entra em venda; `outro` com data legível mas sem telefone vai para "a conferir" com
sugestões pela data (pode ser corporativo só com razão social).

### R-04 — Documento vigente e situação da venda

Vigente = o documento `cliente` ligado à venda com o `created` mais recente, **exceto** que um `closed` vence qualquer
`canceled` criado antes dele (reenvio `(1)` assinado + original cancelado depois pelo prazo). Situação: `closed` →
Assinado; `running` → Aguardando (prazo = `deadline_at`); `canceled` com evento `refusal` → Recusado; `canceled` → Venceu
sem assinatura; nenhum → marca manual do Superadmin (`EventContract.is_signed`) → "Assinado (marcado à mão)"; senão "Sem
contrato na ClickSign".

### R-05 — Onde moram os segredos

- **Token da API**: só env `CLICKSIGN_ACCESS_TOKEN` (`render.yaml` `sync: false`, default `""`), com
  `CLICKSIGN_API_BASE` default `https://app.clicksign.com/api/v3`. Nunca no banco: o `pg_dump` inteiro vai ao Drive, aos
  `backups/` e ao `manto_local` (o espelho já traz `infinitepay_webhook_token` e `google_token` reais). A coluna
  `SiteSetting.clicksign_token` continua inerte (dívida no `docs/05`).
- **Segredo do aviso**: coluna nova `SiteSetting.clicksign_webhook_secret` (+ `_anterior` 24 h, molde 310), gravada pelo
  próprio app quando ele cadastra o aviso pela API (`POST /api/v3/webhooks` devolve `secret`). Aceitável no banco porque
  o aviso não decide nada (R-01).
- **Trava**: `_suppress_clicksign()` no molde de `_suppress_infinitepay` (310): suprime quando o banco não é o de
  produção, salvo `CLICKSIGN_ALLOW_LOCAL_CALLS=1`; `CLICKSIGN_SUPPRESS_CALLS=1` força. Entra no mesmo commit do cliente.

### R-06 — Aviso (webhook) de entrada

`POST /api/webhooks/clicksign`: corpo bruto ≤ 64 KB, `Content-Hmac: sha256=<hex>` = HMAC-SHA256(segredo, corpo bruto),
`hmac.compare_digest` (o primeiro HMAC do repositório: não há `hmac.new` em `app/`); inválido → 404 sem efeito. Válido →
responde 200 na hora e dispara a sincronização incremental fora da requisição (thread curta no molde
`virtuais_webhook.py` da 310, com claim atômico de janela curta para várias rajadas virarem uma passada). **Sem caixa de
entrada**: o aviso não carrega decisão, e a sincronização é idempotente (UNIQUE pelo id do envelope; anexo só se
`contrato_anexo_id` vazio). Limite `60 per minute` no limiter. Sem redirect (a ClickSign trata 301 como falha). A
`virtuais_webhook.py` da `main` usa `==` e processa dentro da requisição — o molde é o da 310, não o da main.

### R-07 — Cobrar contrato

Só copia a mensagem (decisão 1). O texto sai do frontend com fragmentos do servidor (molde `buildCobrancaMsg`/
`_serialize_mensagens`); canal pelo `communicate_events.signature_request` do signatário (`whatsapp` | `email` |
`sms`). O clique chama `POST /api/contratos/<id>/cobranca` que grava quem/quando; a Home e o evento mostram a última.

### R-08 — Retroativo

`flask clicksign-sincronizar [--desde 2026-06-01] [--aplicar]`: sem `--aplicar` só conta (ligaria / a conferir /
artista / outros / PDFs a anexar / anexos antigos que passam a assinado). Idempotente por UNIQUE do id do documento.
Roda no Shell do Render com `MANTO_SEM_THREADS=1` depois do deploy.

### R-09 — Cadastro do aviso

`flask clicksign-webhook --registrar <url>` (e na subida, se houver token e não houver segredo? **não** — cadastro só
pelo comando, para nunca registrar a URL de uma cópia local). Eventos: `sign`, `close`, `auto_close`,
`document_closed`, `deadline`, `cancel`, `refusal`, `add_signer`, `upload`.

## Riscos registrados

- `X-Rate-Limit` 50/10 s: o retroativo pagina a 50 e dorme entre páginas.
- O link do PDF assinado é pré-assinado e curto (~5 min): baixar na mesma passada; falha → reintenta na próxima.
- Mudança do nome no fluxo da ClickSign quebra o vínculo automático sem aviso: tudo cai em "a conferir" (visível), não
  em vínculo errado. Registrar no `docs/04`.
- Número americano / e-mail no lugar do telefone: lê, não liga sozinho por telefone; liga por e-mail do formulário se
  houver, senão "a conferir".
