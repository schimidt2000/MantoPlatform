# Contratos — Feature 305

Tudo o que é novo é **opcional** no TypeScript e neutro quando ausente (bundle novo × backend velho).
Erros no envelope de `json_error`: `{"error": {"message": str, "fields"?: {campo: msg}}}`. Nenhuma rota
nova; a tabela de gates de `docs/01` §4.3 não muda.

## `GET /api/events/new/prefill?orcamento=<id>` — Comercial, Superadmin

Chave nova `acrescimos_do_orcamento` (a antiga `acrescimos`, lista crua, continua):

```json
"acrescimos_do_orcamento": {
  "personalizado": false,
  "linhas": [
    { "tipo": "BV", "descricao": "", "is_bv": true, "percentual": 10.0,
      "valores_brl": { "1": 44.0, "2": 100.0, "3": 147.5, "4": 196.0, "custom": null } }
  ]
}
```

`valores_brl` = o BV **cheio** por duração (R1); `custom` só com a duração extra do orçamento.
Personalizado → `linhas: []` e `personalizado: true`.

## `POST /api/events` — Comercial, Superadmin

Corpo ganha `bv_recipient?: string`, `bv_pix?: string`. A lista `acrescimos` do corpo é **ignorada**
(em toda criação). Ordem: 403 → validação (400) → guarda 1:1 do formulário (409) → **B8 (400)** → Google
→ linha → B3 → sync → commit.

```json
400 { "error": { "message": "Este evento tem BV: informe quem recebe e o PIX, para o repasse ir à Planilha de Pagamentos.",
                 "fields": { "bv_recipient": "Informe quem recebe o BV.", "bv_pix": "Informe o PIX de quem recebe o BV." } } }
```

Também 400 em `fields.bv_pix` com mais de 140 caracteres, `fields.bv_recipient` com mais de 200, ou
qualquer dos dois que não seja texto. Sem BV no orçamento (ou cortesia, "Valor a definir",
personalizado): os campos são ignorados.

## `PATCH /api/events/<id>/orcamento` — Comercial, Financeiro, Superadmin

Corpo ganha `bv_recipient?`, `bv_pix?` (usados só com `aplicar_valores_duracao`). Ordem: 404 → 403 →
409 satélite → autoria 301 (409 `orcamento_de_outro` / 404) → **B8 (400, mesmo formato)** →
`set_event_orcamento`. `relatorio_orcamento` ganha:

```json
"acrescimos_criados": 1, "bv_total": 147.5,
"acrescimos_ignorados": "evento já tem venda" | "evento já tem acréscimos" | "orçamento personalizado" | "duração não identificada" | "evento cancelado"
```

e a frase: "… BV de R$ 147,50 para <quem recebe> — entra na Planilha de 08/2026; a comissão passa a ser
sobre a venda menos o BV." / "O BV do orçamento não entra sozinho: lance-o em Acréscimos, com quem
recebe e o PIX, e confira se o valor de venda é o total com o BV." (só se o vínculo é depois do corte).

## `PUT /api/events/<id>/acrescimos` — Comercial, Financeiro, Superadmin

Item ganha `id?: number` (o recebido no GET) e `descricao?: string` (**ausente** = mantém; `""` =
apaga). `value` aceita número ou texto pt-BR ("1.309,52"). Ordem: 404 → 403 → 401 → 409 satélite →
**B8/régua (400 sem apagar nada)** → grava → sync da comissão → commit.

```json
400 { "error": { "message": "Corrija os acréscimos destacados",
                 "fields": { "items.2.bv_pix": "Informe o PIX de quem recebe o BV.",
                             "items.0.value": "Valor inválido." } } }
```

Índice = posição **na requisição**. Linha BV nova em % com a venda sem valor → 400 na linha.

## `GET /api/events/<id>` — bloco `acrescimos` e `venda` só para `show_comercial`

- Item de `acrescimos` ganha `descricao` e `bv_pix` (o `id` já vem).
- `venda.orcamento.bv`: `{"percentual": 10.0}` | `{"valor": 10.0}` | `null`.
- `venda.bv_do_orcamento_pendente`: `{"valor": 140.13 | null, "percentual": 10.0 | null, "duracao": 2 | null}` | `null` (R8).

## `PATCH /api/events/<id>/comercial` — Comercial, Superadmin (215b antes)

Resposta (o evento) ganha `aviso_bv?: string` — "O BV acompanhou a venda: de R$ 200,00 para R$ 180,00.
Confira o BV e o valor total com BV." ou "Confira o BV: o valor de venda voltou."

## `PATCH /api/events/<id>` (edição completa) — Comercial, Superadmin (215b antes)

Os avisos da B10 e o do alerta aceso entram em `warnings` (já existe).

## Planilha e comissão — sem mudança de contrato

O BV novo aparece pelas consultas de hoje (`_build_bv_items`, `financeiro_read.py:706-715`) com
recebedor, PIX e `missing_data: false`; marcar pago segue Financeiro/Superadmin (Comercial 403).
