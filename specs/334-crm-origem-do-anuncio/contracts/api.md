# Contratos — 334 De qual anúncio veio cada cliente

Nenhum endpoint novo. Campos novos, opcionais no front (o backend antigo não os manda).

## `GET /api/conversas/<id>` (gate `pode_conversas`)

- Ganha `anuncio`: `{"tipo": "anuncio" | "publicacao" | "outro", "titulo": str | null, "campanha": str | null, "quando":
  ISO UTC}` — o contato mais recente da conversa — ou `null`.

## `GET /api/clientes/<id>` (gate `_require_vendas` da base de clientes)

- Ganha `origem`:

```json
{
  "lead_origin": "Anúncio do WhatsApp",
  "campanha": "Festa infantil SP",
  "primeiro": {"anuncio_id": "120…", "titulo": "Festa com personagens", "campanha": "Festa infantil SP", "quando": "…"},
  "recente": {"anuncio_id": "…", "titulo": "…", "campanha": "…", "quando": "…"}
}
```

  `primeiro` e `recente` são `null` sem anúncio; `campanha` (do topo) é o `utm_campaign`.

## `GET /api/marketing/desempenho` (gate de hoje)

- Cada item de `campaigns` ganha `returns` (fichas que voltaram por anúncio da campanha no período) e `return_events`
  (os eventos fechados depois do retorno).
- `headline` e os `leads` contam também a ficha criada pela conversa (pela data em que entrou na base).

## Integração com a Meta

`GET https://graph.facebook.com/{versão}/{ad_id}?fields=name,campaign{id,name}`, com o `META_ANUNCIOS_TOKEN` (ou o
`WHATSAPP_ACCESS_TOKEN`), que precisa de `ads_read`. Pela mesma trava do envio.
