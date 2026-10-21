# Contratos — Feature 313

Envelope de erro: `json_error` (`{error: {message, fields?}}`). Nenhum gate muda (RBAC na spec).

## `POST /api/orcamento/calcular`

**Entrada — chaves novas, opcionais** (ausentes, `0` ou vazias = sem desconto; o resultado é o de hoje, salvo as
exceções da regra do acréscimo, Q7):

```text
desconto_pct?: number                       # 0 < d < 100 (modo %)
desconto_valor?: number                     # o valor final de UMA duração (modo valor)
desconto_duracao?: "1h"|"2h"|"3h"|"4h"|"extra"
```

Com `desconto_valor` + `desconto_duracao`, o servidor acha o % (sem arredondar) e ignora `desconto_pct`.

**400 `fields`** (um campo por vez, como hoje): `desconto_pct` fora de `0 < d < 100` (ou não numérico) → `desconto_pct`;
`desconto_valor` sem `desconto_duracao` (ou o contrário), duração que o resultado não mostra (R6), valor ≤ 0 ou
maior que o cheio daquela duração → `desconto_valor`.

**Saída** — `quote` com as chaves do `data-model.md`; `snapshot` com `versao_conta`, `bases`, `brutos` e o desconto
digitado. Mensagem:

- sem desconto: a de hoje, palavra por palavra;
- com desconto, em cada duração (e no "Total da visita" do só-produto): `• *VALOR TOTAL: de R$ X por R$ Y*` e
  `  _(desconto de N% aplicado)_`; "Valor da Apresentação" / "Logística e Transporte" pelo cheio;
- "À Vista (PIX)": negociado < 5% → os valores com 5% e `_(desconto especial de 5% aplicado)_`; negociado ≥ 5% →
  `1️⃣ *À Vista (PIX):* o mesmo valor — o desconto de N% já está aplicado.`

## `POST /api/orcamento/salvar`

Nada muda: persiste `quote` e `snapshot`; as colunas `total_*` guardam o valor final.

## `GET /api/orcamento/historico`

Cada linha ganha `desconto_pct?: number` (o `desconto_aplicado` do `form_snapshot`, quando > 0), para o selo
"−N%".

## `GET /api/orcamento/historico/<id>`, `…/pdf`, `POST …/enviar-email`

O `quote` congelado traz as chaves novas quando existem; o PDF lê `pix_*` (legado: `total × 0,95`) e mostra "R$ Y
(de R$ X)" + uma linha "Desconto de N% aplicado" (R10).

## `GET /api/events/new/prefill?orcamento_id=`

Ganha, para orçamento `versao_conta = 2`: `bruto_1h..4h`, `bruto_custom`, `desconto_pct`, `extra_por_horas: {"5":
{bruto, total}, …, "12": {…}}` (a R1 sobre as bases congeladas; ausente no personalizado) e `total_custom`/
`bruto_custom` pela R1. Orçamento antigo: as chaves novas ausentes; `total_custom` como hoje. Sem `pix_*` (Q2 = C).
`acrescimos_do_orcamento.linhas[].valores_brl` continua o BV **cheio**.

## `POST /api/events` e o gêmeo pelo orçamento

Corpo igual; a tela manda `sale_value_gross` = cheio e `sale_value` = final. O BV gravado (305) usa o cheio como
denominador (R3).

## `PATCH /api/events/<id>/orcamento` (273)

`aplicar_valores_do_orcamento` grava `sale_value` = final e `sale_value_gross` = cheio; BV pela mesma conta (R3).
Recusas da 299/306/312 inalteradas.

## EducaManto (`/api/educamanto/...calcular`)

As chaves de desconto são descartadas antes da conta compartilhada (R8); a regra de acréscimo (Q7) vale na
contratação Manto.
