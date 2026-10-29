# Contratos — 323

Todo campo novo de resposta é **opcional** no React (`campo?:`, sai com `null`): backend e bundle
ficam em versões diferentes durante o deploy (`docs/00` §6, item 21).

## 1. Corpo das portas da venda — chave nova `nota` (opcional)

`POST /api/events`, `PATCH /api/events/<id>`, `PATCH /api/events/<id>/comercial`. Gates de hoje,
sem mudança (`_can_create_event`).

```json
"nota": {
  "tomador_doc": "61.006.839/0001-21",
  "iss_retido": true,
  "municipio": "Jundiaí - SP",
  "referencia": "AF 618/2026",
  "observacoes": "Cliente pede o número do pedido na nota."
}
```

- Ausente → os dados gravados não mudam. Presente → substitui os cinco (vazio = nulo).
- `tomador_doc` aceita máscara; grava só dígitos.
- Erros (400, envelope `json_error`, mensagem "Corrija os campos destacados"):
  - `fields.nota_tomador_doc`: "Informe o CNPJ com 14 dígitos ou o CPF com 11."
  - `fields.nota_municipio`: "Informe o município onde o serviço é prestado." (ISS retido sem município)
- Na criação, a validação roda **antes** de criar o evento no Google.
- No PATCH em bloco do cancelado, `nota` diferente do gravado conta como "venda mudaria" (409 de hoje).

## 2. Detalhe do evento — `venda.nota` (novo, em `GET /api/events/<id>` e respostas de escrita)

Só dentro de `venda` (já restrito a `show_comercial`).

```json
"nota": {
  "tomador_doc": "61006839000121" | null,
  "doc_do_cliente": "61006839000121" | null,
  "iss_retido": false,
  "municipio": null,
  "referencia": null,
  "observacoes": null
}
```

`notas_fiscais[]` ganha `pedida_por` (nome ou `null`) e `pedida_em` (ISO SP ou `null`).

## 3. Tela inicial — bloco `notas_a_emitir` em `GET /api/dashboard`

Só Superadmin real sem "Ver como"; outros papéis recebem `null` (ou a chave ausente em servidor
antigo — os dois significam "não desenhe").

```json
"notas_a_emitir": {
  "itens": [
    {
      "id": 812,
      "event_id": 1290,
      "event_title": "(SHOW) Sereia + Pirata",
      "event_start_at": "2026-11-14T15:00:00",
      "amount": 2127.98,
      "issue_date": null,
      "tomador": {"nome": "Esporte Clube Sírio", "doc": "61006839000121", "email": "…", "endereco": "…"},
      "iss_retido": false,
      "municipio": null,
      "referencia": null,
      "observacoes": null,
      "pedida_por": "Thaís",
      "pedida_em": "2026-10-28T14:02:11",
      "vencimento": "2026-11-20",
      "discriminacao": "Personagens para evento 14/11\nVencimento: 20/11\nEsses são os dados…",
      "cancelado": false
    }
  ]
}
```

Ordem: `pedida_em` mais antiga primeiro; legado (sem `pedida_em`) por último, pela data do evento.

## 4. Inserir o PDF — porta existente, sem mudança

`PATCH /api/events/<event_id>/invoices/<id>` (multipart: `file`, `amount`, `issue_date`), gate
`_can_manage_sale`. A Home manda o `amount` atual e `issue_date` = a da nota ou hoje (SP); sem eles o
PATCH apagaria o valor (R7).

## 5. E-mail — `send_nota_pedida_email(nota, users)`

- Assunto: `Nota R$ 2.127,98 · Esporte Clube Sírio · pedida por Thaís` (tomador cortado em 40 com
  "…"; sem valor: `Nota (valor a definir) · …`; sem cliente: "cliente não informado").
- Prévia: `<evento> — dd/mm · ISS retido (Jundiaí - SP) · vencimento dd/mm` (só o que existir) +
  enchimento invisível.
- Corpo: "A <nome> pediu a emissão de uma nota fiscal." + caixa (Valor, Tomador, CNPJ/CPF ou "Não
  informado", E-mail, Endereço, ISS, Referência, Observações, Evento) + discriminação em bloco
  pré-formatado + botão **Emitir nota →** para `<plataforma>/` (tela inicial).
