# Contrato: campos de valor em reais (059)

Define o comportamento único que **todo** campo de entrada de R$ deve respeitar.

## 1. Marcação no template (front)

Um campo de R$ MUST ser:

```html
<input type="text" inputmode="decimal" class="brl-input" name="..." placeholder="0,00">
```

- `type="text"` (nunca `number`) + `inputmode="decimal"` (teclado numérico no mobile).
- `class="brl-input"` → `money-mask.js` aplica a máscara automaticamente.
- **Não** usar `step`/`min`/`max` (são de `type=number`).
- Valor inicial vindo do servidor: renderizar com o filtro `| brl` (ex.:
  `value="{{ x | brl if x is not none else '' }}"`).

## 2. Comportamento da máscara (já implementado em money-mask.js)

- Preenche da direita para a esquerda; centavos sempre com 2 casas.
- `.` separa milhar, `,` separa centavos. Ex.: digitar `150000` → `1.500,00`.
- Campo vazio = sem valor (não força `0,00`).
- Nós inseridos dinamicamente: chamar `MoneyMask.init(novoElemento)`.

## 3. API JS (MoneyMask)

| Função | Entrada | Saída | Uso |
|---|---|---|---|
| `MoneyMask.init(root?)` | elemento/doc | — | (re)liga a máscara a `.brl-input` |
| `MoneyMask.applyMask(input)` | input | — | normaliza o valor do input |
| `MoneyMask.format(cents)` | inteiro (centavos) | `"1.500,00"` | formatar p/ exibição |
| **`MoneyMask.parseNumber(valueOrInput)`** (novo) | string ou input | `Number` (ex.: `1500`) ou `0` | **ler valor em calculadoras ao vivo** |

> `parseNumber` substitui `parseFloat(el.value)` onde o JS precisa do número de um campo
> mascarado (Orçamento: `acrescimo_valor`, `cust_valor_*`; evento: `desc-val`).

## 4. Leitura no backend (já implementado em money.py)

- Valor de R$ recebido de formulário MUST ser lido com `parse_brl(...)` (retorna `Decimal` ou
  `None`) ou `parse_brl_int(...)` (retorna `int` ou `None`).
- `parse_brl` aceita mascarado (`"1.500,00"`), cru (`"1500"`/`"1500.00"`) e americano
  (`"1,500.00"`) → **retrocompatível**: converter o input não quebra dados/fluxos antigos.
- Proibido `float(request.form[...])`/`int(...)` direto em campo de R$.

## 5. Critérios de aceite do contrato

- [ ] Todo input de R$ usa `class="brl-input"` (nenhum `type="number"` para R$).
- [ ] Calculadoras ao vivo leem via `MoneyMask.parseNumber` (resultado idêntico ao anterior).
- [ ] Toda rota que recebe campo de R$ usa `parse_brl`/`parse_brl_int`.
- [ ] Campos não-monetários (%, contagem, markup, dimensão, tempo) permanecem inalterados.
