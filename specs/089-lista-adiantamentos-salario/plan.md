# Implementation Plan: Lista de adiantamentos de salário (089)

**Branch**: `089-lista-adiantamentos-salario` | **Date**: 2026-06-26 | **Spec**: [spec.md](spec.md)

## Summary

Transforma o adiantamento único (`SalaryPayment.advance_amount/advance_proof`) numa **lista** via novo
modelo `SalaryAdvance` (1 SalaryPayment → N adiantamentos). Total adiantado = soma; valor a pagar =
salário − total. Add (append, sem sobrescrever) + remover item. Migração cria a tabela e **importa** os
adiantamentos únicos existentes. Sem mudança no custo de salário do balanço.

## Technical Context

**Modelo** (`app/models.py`):
- `SalaryAdvance`: id, salary_payment_id(FK), amount(Numeric 12,2), proof(String 300), created_at.
- `SalaryPayment`: relação `advances` (cascade delete, order_by created_at) + property
  `advance_total` (Decimal). Colunas legadas `advance_amount/advance_proof` ficam (não mais usadas).

**Migração** (down_revision `x0a1b2c3d4e5`): cria `salary_advances`; copia linhas de `salary_payments`
com `advance_amount` não nulo para `salary_advances` (amount, proof, created_at).

**Rotas** (`app/financeiro/routes.py`):
- `salary_advance` (POST `.../salary/<sp_id>/advance`): passa a **adicionar** um `SalaryAdvance`
  (não sobrescrever). Valida valor > 0, comprovante obrigatório, e `advance_total + novo ≤ salário`.
- Nova `salary_advance_delete` (POST `.../salary/advance/<adv_id>/delete`): remove um item + o arquivo.
- `_build_payment_items`: `_adv = sp.advance_total`; adiciona `advances` (lista de
  `{id, amount(str), date(str), proof}`) ao item; `amount = salário − total`.
- `_regenerate...` (feature 068): trocar o filtro `advance_amount.is_(None)` por "sem adiantamentos"
  (`~SalaryPayment.id.in_(subquery dos salary_payment_id em salary_advances)`).

**Template** (`app/templates/financeiro/pagamentos.html`):
- Linha: "adiantado R$ <total>".
- Modal: salário + **lista** de adiantamentos (valor · data · 📎 · Remover) + **total** + **líquido**, e
  um form para **adicionar** (valor + comprovante). Lista renderizada no cliente a partir de um data-
  attribute JSON (`item.advances | tojson`); "Remover" e "Adicionar" são forms que postam e recarregam.

**Storage**: comprovante segue em `UPLOAD_PAYMENTS` (`/uploads/payments/...`), 10 MB, PDF/imagem.

## Constitution Check

- **II. Migration manual** (autogenerate quebrado): escrita à mão + import dos existentes.
- **IV. Não quebrar**: balanço/custo de salário inalterado; colunas legadas mantidas; preservação na
  regeneração ajustada para a lista.

**Resultado**: PASS (migração de 1 tabela + import).

## Testing

Contra **`manto_local`**: aplicar migração (existentes migram); adicionar 2 adiantamentos ao mesmo
salário (ambos persistem; total e líquido corretos); soma > salário bloqueada; remover um item mantém os
demais e o arquivo é descartado; regenerar a tela preserva os salários com adiantamentos. `ruff` sem
erros novos. Limpar dados de teste.

## Project Structure

```text
app/models.py                              — SalaryAdvance + advances/advance_total
migrations/versions/y1b2c3d4e5f6_*.py       — cria salary_advances + importa existentes
app/financeiro/routes.py                    — add/delete advance; preservação; _build_payment_items
app/templates/financeiro/pagamentos.html    — linha + modal com lista
```

## Complexity Tracking

> Sem violações. Maior atenção: preservação na regeneração e a renderização da lista no modal.
