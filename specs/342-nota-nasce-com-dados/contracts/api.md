# Contratos — 342

Nenhum endpoint novo. Tudo abaixo é **aditivo e opcional** para o cliente (armadilha 21).

## 1. `GET /api/formularios/<tipo>/schema` (público)

Cada campo ganha:

```json
{ "key": "nota_doc", "type": "cpf_cnpj", "...": "...",
  "show_if": { "key": "precisa_nota", "value": "Sim" },
  "only_for_cnpj_of": null }
```

- `show_if`: `null` quando o campo aparece sempre.
- `only_for_cnpj_of`: `"nota_doc"` só em `nota_iss`; `null` nos demais.
- `type` novo: `"cpf_cnpj"`.

## 2. `POST /api/formularios/<tipo>` (público, multipart)

- Campo escondido pela condição: não é exigido; valor enviado é descartado (a seção salva traz `""`).
- Erros novos em `fields`: `nota_doc` ("Confira o CNPJ ou CPF: o número não parece válido." /
  obrigatório), `nota_email`, `nota_iss`.
- Corpo sem `precisa_nota` (bundle antigo) = não precisa de nota.

## 3. Editor (`POST /api/formularios/editor/<tipo>/campo`, `PATCH …/campo/<id>`) — Superadmin

Corpo aceita `show_if_key` e `show_if_value` (os dois vazios = sempre aparece). Resposta do campo
traz `show_if_key`, `show_if_value`. 400 `fields.show_if_key` quando a chave não existe no
formulário, é o próprio campo ou não é `selecao`/`sim_nao`; `fields.show_if_value` quando a chave
veio sem valor. Campo do sistema: a condição enviada é ignorada.

## 4. Chave `nota` das três portas da venda

`POST /api/events`, `PATCH /api/events/<id>`, `PATCH /api/events/<id>/comercial`.

```json
"nota": { "tomador_doc": "", "email": "", "iss_retido": false,
          "municipio": "Sorocaba - SP", "referencia": "", "observacoes": "" }
```

- `email`: novo, opcional. **Ausente = não mexe**; presente grava (vazio apaga). 400
  `fields.nota_email` se inválido.
- `municipio`: gravado com ou sem `iss_retido`; obrigatório só com `iss_retido`.
- 400 `fields.nota_tomador_doc`:
  - "CNPJ ou CPF inválido. Confira os números." — dígito verificador;
  - "Informe o CNPJ ou CPF de quem recebe a nota." — `with_invoice` ligado, sem documento na venda
    nem no cadastro da contratante da gravação, e o pedido nasce agora ou a gravação apagaria o
    documento que existia.

## 5. `GET /api/events/<id>` — `venda.nota`

```json
"nota": { "tomador_doc": "…", "doc_do_cliente": "…", "iss_retido": false,
          "municipio": null, "referencia": null, "observacoes": null,
          "email": null,
          "municipio_sugerido": "Sorocaba - SP",
          "do_formulario": { "response_id": 812, "doc": "12345678000195", "email": "nf@x.com",
                             "iss": "Não sei", "referencia": "OC 4411" } }
```

`do_formulario` é `null` sem formulário ligado que tenha pedido nota. `iss` é o texto da resposta
(`"Sim"`, `"Não"`, `"Não sei"`) ou `null` (CPF).

## 6. Painel "Notas a emitir" (`GET /api/dashboard`, bloco das notas)

Cada item ganha `municipio_sugerido` (string ou `null`); `tomador.email` passa a ser o e-mail da nota
e, sem ele, o do cadastro.

## 7. Pré-preenchimento da criação (`GET` do formulário para o cadastro de evento)

`valores` pode trazer `with_invoice: true` e `nota: {tomador_doc, email, iss_retido, referencia}`,
com `origem` marcando os dois como vindos do formulário.
