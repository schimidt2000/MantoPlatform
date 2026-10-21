# Contratos — Feature 313

Envelope de erro: `json_error` (`{error: {message, fields?}}`). Nenhum gate muda (RBAC na spec).

## `POST /api/orcamento/calcular`

**Entrada — chaves novas, opcionais** (ausentes, `0` ou vazias = sem desconto; o resultado é o de hoje, salvo as
exceções da regra do acréscimo, Q7). O 400 vale para `desconto_pct` < 0, ≥ 100 ou não numérico:

```text
desconto_pct?: number                       # 0 < d < 100 (modo %)
desconto_valor?: number                     # o valor final de UMA duração (modo valor)
desconto_duracao?: "1h"|"2h"|"3h"|"4h"|"extra"
```

Com `desconto_valor` + `desconto_duracao`, o servidor acha o % (sem arredondar) e ignora `desconto_pct`. Valor final
igual ao cheio (± R$ 0,005) = sem desconto.

**400 `fields`** (um campo por vez, como hoje): `desconto_pct` < 0, ≥ 100 ou não numérico → `desconto_pct`;
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
"−N%". Custo: um `json.loads` por linha (até 300 por listagem, `orcamento_read.py:209`) — aceito; o
`form_snapshot` já vem na consulta.

## `GET /api/orcamento/historico/<id>`, `…/pdf`, `POST …/enviar-email`

O `quote` congelado traz as chaves novas quando existem; o PDF lê `pix_*` (legado: `total × 0,95`) e mostra "R$ Y
(de R$ X)" + uma linha "Desconto de N% aplicado" (R10).

## `GET /api/events/new/prefill?orcamento_id=`

Ganha, para orçamento `versao_conta = 2`: `bruto_1h..4h`, `bruto_custom`, `desconto_pct` (o `desconto_aplicado`),
`extra_por_horas: {"5": {bruto, total}, …, "24": {…}}` (a R1 sobre as bases congeladas; ausente no personalizado;
o "Outra (h)" passa a aceitar de 5 a 24 h) e `total_custom`/`bruto_custom` pela R1; cada
`acrescimos_do_orcamento.linhas[]` ganha `valores_final` (o que a linha vale com o desconto, por duração — o
servidor faz a conta; o navegador só mostra, analyze A7). Orçamento antigo: as chaves novas ausentes; `total_custom` como hoje. Sem `pix_*` (Q2 = C).
`acrescimos_do_orcamento.linhas[].valores_brl` continua o BV **cheio**.

## `POST /api/events` e o gêmeo pelo orçamento

Corpo igual; a tela manda `sale_value_gross` = cheio e `sale_value` = final. O BV gravado (305) usa o cheio como
denominador (R3).

## `PATCH /api/events/<id>/orcamento` (273)

`aplicar_valores_do_orcamento` grava `sale_value` = final e `sale_value_gross` = cheio (`bruto_{d}h ?? total_{d}h`,
o legado sem a chave); BV pela mesma conta (R3). A tela do vínculo (`ComercialSection.tsx:786-797`) mostra o BV pelo
`valores_final` do prefill, não o `valores_brl` cheio (analyze B3).
Recusas da 299/306/312 inalteradas.

## EducaManto (`/api/educamanto/...calcular`)

As chaves de desconto são descartadas antes da conta compartilhada (R8); a regra de acréscimo (Q7) vale na
contratação Manto.
