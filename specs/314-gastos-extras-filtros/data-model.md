# Modelo de dados — Feature 314

**Sem mudança de esquema.** Nenhuma coluna, nenhuma migration. A feature lê `special_expenses`
(`SpecialExpense`, `app/models.py`) e deriva um valor.

## Campos lidos

| Campo | Valores | Quem escreve |
|---|---|---|
| `status` | `pendente` · `aprovado` · `rejeitado` | criar / aprovar / rejeitar (`gastos_ops`) |
| `payment_status` | `nao_pago` (default) · `no_banco` · `pago` | Planilha de Pagamentos (`set-status`, `bulk-action`) |
| `paid_at_creation` | bool | criar ("já pago", feature 128) |
| `disbursement_type` | `reembolso` · `fornecedor` · `cliente` · `NULL` | criar / editar; `cliente` só pelo cancelamento (306) |
| `expense_date` | data pura | criar / editar |
| `category` | `SpecialExpense.CATEGORIES` | criar / editar |

## Valor derivado: `situacao`

`gastos_ops.situacao_do_gasto(expense) -> str`. Regra e ordem em `research.md` D2.

| `situacao` | Rótulo na tela | Grupo na abertura | Tom |
|---|---|---|---|
| `aguardando_aprovacao` | Aguardando aprovação | lista principal | `gold` |
| `a_pagar` | A pagar | lista principal | `red` (o "Pendentes" de Pagamentos) |
| `no_banco` | No banco | lista principal | `blue` |
| `pago` | Pago (cartão "Pagos") | recolhido "Pagos" | `green` |
| `rejeitado` | Rejeitado (cartão "Rejeitados") | recolhido "Rejeitados" | neutro |

Invariante (SC-003): todo gasto tem exatamente uma situação, então cai em exatamente um grupo. A soma dos grupos é
igual ao total da lista.

## Transições que mudam a situação (todas já existem; nenhuma é nova)

```text
aguardando_aprovacao ──aprovar──▶ a_pagar          (com desembolso, sem "já pago")
                     ──aprovar──▶ pago             (sem desembolso, ou "já pago")
                     ──rejeitar─▶ rejeitado
a_pagar ──planilha "no banco"──▶ no_banco ──planilha "pago"──▶ pago
pago ──planilha "não pago"──▶ a_pagar   (a planilha desfaz; esta tela só lê)
qualquer ──editar desembolso──▶ recalculada no próximo GET
```

## Estado da tela (não persiste no servidor)

| Estado | Onde vive | Valores |
|---|---|---|
| busca | URL `busca` | texto livre |
| categoria | URL `categoria` | uma de `categories` do payload |
| desembolso | URL `desembolso` | `reembolso` · `fornecedor` · `cliente` · `nenhum` |
| mês | URL `mes` | `AAAA-MM` |
| situação | URL `situacao` | as 5 acima |
| grupo aberto | estado do `AccordionRow` | aberto/fechado, por grupo |
