# Contrato de API — Formulários Dinâmicos Públicos (163)

Estende `specs/144-migracao-react-spa/contracts/api-conventions.md`. Todas as rotas são
públicas (sem `@login_required`, sem RBAC) — mesma acessibilidade das rotas `/f/pre-contrato` e
`/f/corporativo` hoje. `<form_type>` é `comum` ou `corporativo`; qualquer outro valor → 404.

## `GET /api/formularios/<form_type>/schema`

- Público, sem rate limit (só leitura, mesmo padrão de `/api/catalogo/*`).
- 404 se `form_type` não for `comum`/`corporativo`: `{"error": {"message": "Formulário não encontrado"}}`.
- 200: `{"title", "header", "sections": [{"secao", "campos": [{"key","type","label","help_text","placeholder","required","options"}]}]}` — ver `data-model.md`.

## `POST /api/formularios/<form_type>`

- Público. Rate limit: `10 per hour` por IP (mesmo limite do Jinja).
- `Content-Type: multipart/form-data` (ou `application/x-www-form-urlencoded` — o backend só lê
  `request.form`, ambos funcionam; o frontend usa `FormData`).
- Campos: um por `field_key` do schema vigente daquele `form_type`, mais `website` (honeypot).
  Campo tipo `telefone` envia `{key}_ddi` e `{key}_national`. Campo tipo `sim_nao` só é enviado
  quando marcado (valor `"Sim"`); omitido quando desmarcado.
- **Honeypot**: se `website` vier preenchido, responde **201** com
  `{"wa_link": null, "contact_name": null}` — não salva nenhuma resposta, paridade com o
  comportamento silencioso do Jinja.
- **400** — validação (mesma ordem/mensagens de `_validate_dynamic`):
  `{"error": {"message": "Alguns campos precisam de atenção. Corrija os campos destacados e envie novamente.", "fields": {"<field_key ou field_key_national>": "<mensagem>", ...}}}`.
  Pode haver múltiplos campos inválidos na mesma resposta (diferente da 162, que retorna só o
  primeiro erro encontrado) — `_validate_dynamic` já coleta todos de uma vez.
- **201** — sucesso: `{"wa_link": "https://api.whatsapp.com/send?...", "contact_name": "Nome"}`.

## Notas de paridade

- A resposta é salva (`_save_response`) e o vínculo automático de evento é tentado
  (`_attempt_auto_link`, best-effort — nunca impede o 201) exatamente como no Jinja, antes do
  link de WhatsApp ser retornado — mesma ordem de operações (SC-002 da spec 118).
- `_build_message`/`_whatsapp_link` são as mesmas funções do Jinja — a mensagem de WhatsApp
  produzida pela API é byte-a-byte igual à do Jinja para os mesmos dados.
