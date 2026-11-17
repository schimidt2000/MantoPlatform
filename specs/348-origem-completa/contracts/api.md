# Contratos de API — 348

Envelope de erro: `json_error` (`{"error": {"message", "fields"}}`).

## `POST /api/origem/codigo` (novo, público)

Sem login. Limite `20 per hour` por endereço (Flask-Limiter). Módulo `app/api/origem_public.py`.

Corpo (JSON, todos opcionais, texto):

```json
{
  "gclid": "…", "gbraid": "…", "wbraid": "…", "fbclid": "…",
  "gad_campaignid": "123", "utm_id": "456",
  "utm_source": "google", "utm_medium": "cpc", "utm_campaign": "FESTA_…", "utm_content": "…", "utm_term": "…",
  "pagina": "/catalogo/f/pre-contrato", "procedencia": "www.google.com"
}
```

- **201** `{"codigo": "A7K2Q", "linha": "Código do site: #A7K2Q", "validade_dias": 90}`. A `linha` é o texto que
  vai no fim da mensagem pronta: o servidor é a fonte única dele (a lista de desejos usa a que veio aqui; o
  formulário público, a do `codigo_ops.anexar_a_mensagem`).
- **400** `{"error": {"message": "Nenhum marcador de campanha."}}` quando não há `gclid`, `gbraid`, `wbraid`,
  `fbclid`, `gad_campaignid`, `utm_id` nem `utm_*`.
- Valores não-texto são ignorados; textos são cortados no tamanho da coluna.

## `POST /api/formularios/<tipo>` (público, como hoje)

Campo novo opcional no multipart: `origem_codigo` (texto). Código válido (existe e tem ≤ 90 dias) → a mensagem do
`wa_link` ganha, no fim, uma linha em branco e `Código do site: #A7K2Q`, e a resposta fica ligada ao código
(`origem_codigos.form_response_id`, só se ainda vazio). Código inválido ou ausente → a resposta de hoje.

## `POST /api/events` (Comercial, Superadmin — como hoje)

Campos novos opcionais no JSON:

- `frente`: um slug de `marketing_frentes` (`corporativo`, `social`, `educamanto`, `festas`, `loja`) ou `null`.
  Fora da lista → **400** `fields.frente = "Selecione uma frente da lista."`. Ausente/nulo → grava só a sugestão certa.
- `conversa_id`: inteiro de uma conversa existente. Inexistente ou não inteiro → **400**
  `fields.conversa_id = "Conversa não encontrada."`, antes da chamada ao Google. Presente → o evento guarda a conversa
  e o contato de origem (regra R7). Ausente → herda do orçamento (`orcamento_history_id`), se houver.

## `PATCH /api/events/<id>/comercial` (Comercial, Superadmin — como hoje, com a regra do cancelado)

Campo novo opcional: `frente`.

- Chave ausente (bundle antigo): a frente não muda e não é exigida.
- Chave presente com slug válido: grava.
- Chave presente, `null` ou vazia: não apaga a gravada.
- Slug fora da lista → **400** `fields.frente = "Selecione uma frente da lista."`.
- Chave presente, nenhuma frente (nem no corpo nem gravada), venda > 0 e sem cortesia → **400**
  `fields.frente = "Selecione a frente da venda."`.

## `GET /api/events/<id>` (detalhe — como hoje)

Dentro de `venda` (bloco só de quem tem `show_comercial`), duas chaves novas, opcionais no React:

```json
"frente": {
  "frente": "social", "rotulo": "Social (15 anos e casamento)", "definida": true,
  "sugestao": "festas", "sugestao_certa": false,
  "opcoes": [{"slug": "corporativo", "rotulo": "Corporativo"}, "…"]
},
"origem": {
  "conversa_id": 12, "conversa_nome": "Ana Souza", "canal": "whatsapp", "pode_abrir": true,
  "contato": {
    "tipo": "anuncio", "titulo": "Festa com a Elsa", "anuncio_id": "120…", "campanha": "FESTA_…",
    "campanha_id": "238…", "conjunto": "Mães SP", "codigo": null, "quando": "2026-11-12T14:03:00+00:00"
  }
}
```

`origem` é `null` quando a venda não tem conversa; `contato` é `null` quando a conversa não tem contato de origem na
janela (venda orgânica). `pode_abrir` diz se quem lê tem acesso às Conversas (`acesso.pode_conversas`).
