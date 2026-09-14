# Contrato — "Valor a definir" no cadastro e na edição (feature 299)

## `POST /api/events` e `PATCH /api/events/<id>`

**Gate inalterado**: `_can_create_event()` = COMERCIAL ou SUPERADMIN (`agenda_write.py:84-88, 743-744,
891-892`). FINANCEIRO recebe 403 exato (cenário 16).

**Corpo** — uma chave nova, opcional e **não gravada**:

```json
{ "valor_a_definir": true, "sale_value": null, "sale_value_gross": null, "seller_id": 2, "...": "..." }
```

| Situação | O que o servidor faz |
|---|---|
| `valor_a_definir: true`, sem cortesia | grava `sale_value` e `sale_value_gross` como `NULL`, ignora números que venham e **não** gera os erros de valor |
| `is_cortesia_permuta: true` | a cortesia vence a marca: venda gravada como hoje (0 na criação e na edição) |
| sem a marca, sem cortesia e sem valor (nulo, 0 ou ausente) | **400**, com `{"error": {"message": "...", "fields": {"sale_value_gross": "Informe o valor de venda ou marque “Valor a definir”.", "sale_value": "Informe o valor de venda ou marque “Valor a definir”."}}}` |
| vendedor ausente | 400 em `seller_id`, como hoje (FR-016), **exceto** no outro evento de um grupo |
| `PATCH` num outro evento de grupo (satélite) | `update_event_core` **não grava** nenhum campo comercial (valores, vendedor, pagamento, cortesia, data da venda, taxa, NF, transporte, acréscimo). `_validate_event_core` pula valor e vendedor. O resto (título, data, local...) salva normalmente |

A validação roda **antes** do Google e de qualquer escrita (`agenda_write.py:761` antes de `:792`;
`:899` antes de `:922`). Um 400 não deixa evento órfão na Agenda.

**Data da venda** (FR-017, `resolver_data_da_venda(..., a_definir)`):
- **Criação** com a marca e sem `sale_date`: hoje em São Paulo.
- **Criação** com `sale_date`: a informada.
- **Edição** com `sale_date` vazio: mantém a data que o evento já tinha.

**Comissão** (FR-031, `_sync_commission_payment`):
- **Sem valor**: não nasce linha, e a linha `a_pagar` existente vira `cancelado`. Isso já é assim
  hoje.
- **Linha nova de comissão comum**, com `sale_date` num mês anterior ao mês corrente de São Paulo:
  `payable_from = hoje`. O ciclo de pagamento (`coalesce(payable_from, sale_date, created_at)`) cai
  no mês em que o valor entrou.
- **Sincronizações seguintes**: não trocam esse `payable_from` de volta para `NULL`.
- **EducaManto**: continua com `payable_from = data da realização`.
- **Linha já paga**: não muda.

**Compatibilidade na janela de deploy**:
- **Bundle antigo, servidor novo**: a chave não chega, e vale a regra de hoje. O Zod antigo já exige
  valor maior que 0.
- **Bundle novo, servidor antigo**: os adaptadores antigos descartam a chave. O 400 volta em
  `sale_value`/`sale_value_gross` antes do Google. É falha segura: basta salvar de novo depois do
  deploy.

**Sem mudança**:
- A criação Jinja (`calendar/routes.py:4008`) e o `PATCH /api/events/<id>/basico` não mandam a chave
  e ficam como estão.
- O `PATCH /api/events/<id>/comercial` já aceita valor nulo e continua recusando satélite com 409.

## Tela (`ValoresBlock`, `EventCreatePage`, `EventEditPage`)

- **Marca.** Botão de alternar "Valor a definir" (`aria-pressed`), no padrão da cortesia e excludente
  com ela. Quando marcada:
  - esconde os dois valores com o mesmo `AnimatePresence`;
  - mostra "O evento fica em “Evento sem valor de venda” até alguém pôr o valor.".

  Vendedor, data da venda, transporte e acréscimo continuam à mostra.
- **Aviso.** Marcar num evento que tinha valor mostra, no lugar, "O valor de R$ X será apagado e a
  comissão a pagar, cancelada.".
- **Hidratação da edição.** A marca abre marcada quando `sale_value` é `null` ou 0 e não há
  cortesia. O R$ 0,01 abre **desmarcado**. No satélite, a marca abre marcada e travada, com o link
  para o principal.
- **Foco.** Os dois `MoneyInput` passam por `Controller`, com `id` e `ref`. No envio bloqueado e no
  400 do servidor, a tela foca e rola até o primeiro campo de `error.fields`, na ordem de
  `FIELD_ORDER`. O Salvar nunca fica desabilitado.

## RBAC — linhas para `docs/01` §4.3

| Rota | Gate | Papéis | Muda na 299 |
|---|---|---|---|
| `GET /api/dashboard` | `show_comercial` (papel efetivo, "Ver como") para os blocos `comercial` e `formularios` | COMERCIAL, FINANCEIRO, SUPERADMIN | linha **nova** na tabela (hoje não existe); o conteúdo do bloco muda |
| `GET /api/events/<id>` | `show_comercial` para `cobranca`, `venda`, `pagamentos` e `mensagens` | COMERCIAL, FINANCEIRO, SUPERADMIN | conteúdo da cobrança (grupo) |
| `POST /api/events` | `_can_create_event` | COMERCIAL, SUPERADMIN | `valor_a_definir` |
| `PATCH /api/events/<id>` | `_can_create_event` | COMERCIAL, SUPERADMIN | `valor_a_definir`; satélite sem campos comerciais |
| `PATCH /api/events/<id>/orcamento` | `_can_manage_sale` | COMERCIAL, FINANCEIRO, SUPERADMIN | valor simbólico conta como sem venda |
| `PATCH /api/events/<id>/comercial` | `_can_create_event` | COMERCIAL, SUPERADMIN | nenhuma (já aceita nulo) |
