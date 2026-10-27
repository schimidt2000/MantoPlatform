# Modelo de dados — Feature 313

Nenhuma tabela nem coluna nova (sem migration). O que muda é o conteúdo dos JSONs do orçamento.

## `OrcamentoHistory.form_snapshot` (o `snapshot` do cálculo)

Chaves novas, todas opcionais; ausentes = orçamento de antes, lido pelo caminho de hoje (020).

| Chave | Tipo | O que é |
|---|---|---|
| `versao_conta` | `2` | a marca da regra desta entrega (R2). Ausente = regra antiga (R$ × h ÷ 4 acima de 4h; BV sobre a base sem os outros acréscimos) |
| `bases` | `[float × 4]` | a base pré-acréscimos de cada coluna 1–4h (apresentação + transporte + produto) |
| `brutos` | `{"1h","2h","3h","4h": float, "custom"?: float}` | o preço antes do desconto (a extra é `"custom"`,
como `bruto_custom` no `quote`; a entrada `desconto_duracao` chama a mesma coluna de `"extra"`) |
| `desconto_pct_digitado` | `float \| null` | o % como a comercial digitou (modo %); `null` no modo valor |
| `desconto_valor` | `float \| null` | o valor final digitado (modo valor) |
| `desconto_duracao` | `"1h" \| "2h" \| "3h" \| "4h" \| "extra" \| null` | a duração do valor digitado |
| `desconto_aplicado` | `float` | o % exato aplicado (o digitado, ou o achado pelo valor); `0` sem desconto — **é
esta** que o prefill, o histórico e o evento leem (analyze A5) |

`acrescimos[i].valores_brl` continua (305): o que a linha somou ao preço **cheio**, pela regra nova quando
`versao_conta = 2`. `produtos`, `produtos_total` (309) não mudam.

**Validação ao ler** (`/salvar` devolve o snapshot do navegador): `bases` com 4 números finitos ≥ 0; `brutos[d]` ≥
`total_{d}` gravado; `desconto_aplicado` em `[0, 100)`. Inválido → caminho de hoje.

## `OrcamentoHistory.total_1h..total_4h`

Passam a guardar o **valor final** (com o desconto). Sem desconto, o de hoje.

## `OrcamentoHistory.result_snapshot` (o `quote`)

| Chave | Tipo | O que é |
|---|---|---|
| `total_1h..4h`, `total_custom` | float | o valor final (com o desconto) |
| `bruto_1h..4h`, `bruto_custom` | float | o preço antes do desconto (= total sem desconto) |
| `base_4h` | float | a base de 4h, para o "Outra (h)" |
| `desconto_pct` | `float \| null` | o % exato aplicado; `null` sem desconto |
| `desconto_pct_texto` | `string \| null` | o % como a proposta mostra ("8,3", "10") |
| `desconto_modo` | `"pct" \| "valor" \| null` | como foi digitado |
| `pix_pct` | float | `max(5, desconto exato)` |
| `pix_1h..4h`, `pix_custom` | float | `round(bruto × (1 − pix_pct ÷ 100), 2)` |
| `bv_1h..4h`, `bv_custom` | `float \| null` | o BV a repassar com o desconto (`bv_que_acompanha`); `null` sem BV |
| `bv_pix_1h..4h`, `bv_pix_custom` | `float \| null` | o mesmo, no PIX à vista |

A memória ganha, **só com desconto**, "Desconto (N%)" (tipo `pos`, negativa, depois da nota) e, com BV, "BV a
repassar a quem indicou" (tipo `subtotal`, depois do total). Sem desconto a memória é a de hoje (paridade;
analyze A4) — o BV a repassar sem desconto é o próprio BV da linha de acréscimo.

## `CalendarEvent`

Nenhuma coluna. `sale_value_gross` passa a nascer com o cheio do orçamento e `sale_value` com o final (Novo evento e
vínculo 273). O BV gravado (`event_acrescimos`, 305) é `bv_que_acompanha(cheio da linha, venda, cheio da duração)`.
