# Implementation Plan: "Valor antes do desconto" no evento

**Branch**: `032-valor-antes-desconto` (sobre `031`) | **Date**: 2026-06-09 | **Spec**: [spec.md](./spec.md)

## Summary

Adicionar o campo **"Valor antes do desconto"** (preço cheio) ao lado de "Valor de venda" no
formulário de criar evento, obrigatório, persistido em nova coluna do evento para relatórios futuros.
Remover o campo "Valor no contrato" do mesmo formulário. Reusar a validação por campo da 031 e a
máscara monetária (027). Migration manual para a coluna nova.

## Constitution Check

- **I. Reutilizar** ✅ — reusa máscara `.brl-input`, `parse_brl`, e o padrão de validação por campo
  (031). Espelha o campo `sale_value` existente.
- **IV. Não quebrar** ✅ — coluna nullable (eventos antigos intactos); remove só um campo do form.
  Verificação no app. Migration manual (autogenerate quebrado).
- **V. Feedback** ✅ — campo obrigatório com aviso por campo, dados preservados no erro.
- **VII. Valor BR** ✅ — novo campo usa a máscara e exibição padrão.

## Design Detalhado

### 1. Banco — nova coluna (migration manual)
- `CalendarEvent.sale_value_gross = db.Column(db.Numeric(12, 2), nullable=True)` (espelha
  `sale_value`). Comentário: "valor antes do desconto (preço cheio)".
- Migration `j6d7e8f9a0b1_sale_value_gross.py` (down_revision `i5c6d7e8f9a0`): adiciona a coluna em
  `calendar_events` (batch_alter_table). up/down.

### 2. Template — campo novo + remover contrato (event_create.html)
- Na seção Valores, **antes** de "Valor de venda" (à esquerda/ao lado), novo item:
  ```
  Valor antes do desconto (R$) *
  [ R$ <input name="sale_value_gross" id="sale-value-gross" class="brl-input" required-visual> ]
  ```
  Prefill: `old.get('sale_value_gross')` ou (se vem de orçamento) `prefill.total_1h | brl`.
- Remover o bloco "Valor no contrato (R$)" (input `contract_amount`) da seção Contrato.

### 3. JS (event_create.html)
- `selectDuracao(card)`: além de `sale-value`, setar `sale-value-gross` = `formatBRL(total)`
  (acompanha a duração).
- `applyDesconto()`: **não** mexe no gross (já só altera `sale-value`) — diferença = desconto. OK.
- Validação de submit (handler 031): adicionar `grossEl = #sale-value-gross` ao `invalid[]` quando
  vazio ou `parseBRL <= 0` (mesma lógica do valor de venda).

### 4. Servidor (create_event)
- Ler `sale_value_gross_raw = request.form.get("sale_value_gross", "").strip()`.
- Validar obrigatório (> 0): `if (parse_brl(sale_value_gross_raw) or 0) <= 0:
  errors.append("Informe o valor antes do desconto.")`.
- Persistir: `sale_value_gross = parse_brl(sale_value_gross_raw)` no `CalendarEvent(...)`.
- `contract_amount`: o campo saiu do form; manter a leitura tolerante (vira None) ou remover. Como
  não há mais input, `request.form.get("contract_amount","")` → "" → `parse_brl_int` → None. O
  `EventContract` continua sendo criado se houver arquivo, só sem amount. (Mínima mudança.)

### 5. Verificação (app real)
- Campo aparece ao lado de "Valor de venda", com `*`; "Valor no contrato" some.
- Vazio/zero → bloqueia (cliente + servidor), com destaque; dados preservados.
- De orçamento → prefilled; troca de duração acompanha; aplicar desconto reduz só o valor de venda.
- Criar com os dois → salva `sale_value_gross` no banco (conferir valor).
- boot + ruff + migration up/down.

## Project Structure
```text
migrations/versions/j6d7e8f9a0b1_sale_value_gross.py  # NOVO — coluna sale_value_gross
app/models.py                 # CalendarEvent.sale_value_gross
app/templates/event_create.html  # campo novo + remove "Valor no contrato" + JS (duração/validação)
app/calendar/routes.py        # ler/validar/persistir sale_value_gross
```

## Fora de escopo
- Painel/relatório de desconto (consumo do dado) — entrega futura.
- Mexer no "Valor no contrato" da tela de detalhe do evento (event_detail) — permanece.
- Reescrever a lógica do painel de desconto. Sem outras telas.
```
