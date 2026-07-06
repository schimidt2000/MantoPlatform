# Contracts — Comissão EducaManto (109)

Nenhuma rota nova. Contratos das regras/rotas alteradas:

## Regra: beneficiário da comissão

`_commission_beneficiary(event, settings) -> User | None` (app/financeiro/routes.py)

| Caso | Retorno |
|---|---|
| Evento EDU (`title` começa com "(EDU", case-insensitive) e `settings.educamanto_seller_id` definido | usuário responsável EducaManto |
| Evento EDU sem responsável configurado | `event.seller` (regra atual) |
| Evento comum | `event.seller` (regra atual) |

`_event_commission` retorna 0 se o beneficiário não existir ou `receives_commission=False`.
Valor (feature 109, ajuste): evento EDU com responsável → **5% sobre o lucro**
(`sale_value − BV − cachês`, floor 0), override `event.commission_rate` substitui os 5%;
evento comum → % sobre a venda (regra atual, inalterada).
`_sync_commission_payment` cria/atualiza a linha com `seller_id = beneficiário.id` e
`payable_from = data do evento` (EDU) / `NULL` (comum). Exigência de `event.seller_id` cai
apenas no caso EDU-com-responsável.

## GET /vendas/ (pipeline) — alterada

| Usuário | Comportamento |
|---|---|
| COMERCIAL / FINANCEIRO / SUPERADMIN | inalterado (todos os eventos) |
| Responsável EducaManto (sem os papéis acima) | 200; lista APENAS eventos `title ilike "(EDU%"` |
| Demais | 403 (inalterado) |

## GET /financeiro/comissoes — alterada

| Usuário | Comportamento |
|---|---|
| FINANCEIRO / SUPERADMIN | inalterado (gerencia tudo) |
| COMERCIAL | inalterado (vê as próprias, leitura) |
| Responsável EducaManto | 200; vê apenas `seller_id == current_user.id`, leitura |
| Demais | 403 (inalterado) |

## GET/POST /admin/settings — alterada

POST aceita campo novo `educamanto_seller_id` (int vazio ⇒ NULL). Só SUPERADMIN (guard
existente da rota). GET passa lista de usuários para o select.

## GET /educamanto/historico — alterada

Parâmetros novos (opcionais): `date_from`, `date_to` (filtram `created_at`; formato ISO),
`user_id` (só aplicado se superadmin). Template ganha coluna "Gerado por" e filtro por
usuário visíveis apenas para superadmin (regra idêntica ao histórico da calculadora); busca
`q` existente inalterada.

## Planilha de pagamentos (GET /financeiro/pagamentos) — comportamento

Linha agregada de comissões do mês M lista comissões cujo
`COALESCE(payable_from, sale_date)` cai no mês M−1 (vencimento dia 5 de M). Comissões EDU de
eventos ainda não realizados só aparecem nos meses da realização em diante.
