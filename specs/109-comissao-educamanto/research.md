# Research — Comissão EducaManto + Padronização (109)

## R1. Como detectar um evento EducaManto

Convenção do usuário: título começa com "(EDU)". Já existe em produção um evento com prefixo
"(EDUCAMANTO)" — um prefixo estrito "(EDU)" o deixaria de fora.

**Decision**: prefixo `"(EDU"` case-insensitive. Constante `EDUCAMANTO_TITLE_PREFIX = "(EDU"`
em `app/constants.py` + property `CalendarEvent.is_educamanto` em `app/models.py` (Python) e
filtro SQL `CalendarEvent.title.ilike("(EDU%")` onde precisar de query (pipeline). Nenhuma
coluna nova — classificação deriva do título, igual ao padrão já usado para "🟧 ENSAIO".

**Alternatives considered**: coluna booleana `is_educamanto` preenchida na sync — rejeitado:
estado duplicado do título (dessincroniza em edição manual) e exige mexer na sync (Princípio
IV; lição da feature 108: campo de estado só quando o título NÃO é a fonte da verdade — aqui
o título É a fonte da verdade da classificação).

## R2. Quem recebe a comissão EducaManto

Gabriel Lara (user 10, papel ENSAIO, `receives_commission=True`) não pode ser hardcoded.

**Decision**: coluna `educamanto_seller_id` (FK `users.id`, nullable) em `site_settings`,
editável na tela de configurações do admin (`admin_settings.html`, mesma tela da taxa de
comissão padrão) via `<select>` de usuários. Migration faz backfill:
`UPDATE site_settings SET educamanto_seller_id = (SELECT id FROM users WHERE email =
'gabriel@mantoproducoes.com.br')` — idempotente e no-op se o usuário não existir.

## R3. Redirecionamento da comissão

Hoje `_sync_commission_payment` exige `event.seller_id` + `seller.receives_commission` e cria
`CommissionPayment(seller_id=event.seller_id)`. Eventos EDU em produção têm `seller_id=None`
— nenhuma comissão é gerada.

**Decision**: helper `_commission_beneficiary(event, settings) -> User | None` em
`app/financeiro/routes.py`: para evento EDU com responsável configurado retorna o
responsável; senão retorna `event.seller`. `_event_commission` e `_sync_commission_payment`
passam a usar o helper (elegibilidade `receives_commission` avaliada no beneficiário). Para
EDU com responsável, `event.seller_id` deixa de ser exigido (a venda pode ser registrada por
FINANCEIRO/SUPERADMIN sem vendedor). Linhas pendentes (`a_pagar`) são reconciliadas pelo
`_resync_pending_commissions` existente (beneficiário/valor/data acompanham o estado atual);
linhas pagas nunca mudam — mesmo contrato de hoje.

## R4. "Comissão só após a realização do evento"

Ciclo atual: `_build_commission_items` agrega por `sale_date` no mês anterior ao visto, com
vencimento dia 5. Para EDU o ciclo deve ser o mês da REALIZAÇÃO.

**Decision**: coluna `payable_from` (Date, nullable) em `commission_payments` — data da
realização (data de `event.start_at`); `NULL` = comissão comum (ciclo pela venda). A janela
do `_build_commission_items` passa a filtrar por
`func.coalesce(CommissionPayment.payable_from, CommissionPayment.sale_date)` — 1 linha
mudada, zero efeito em linhas com `payable_from IS NULL` (100% das existentes). Evento
remarcado: o resync atualiza `payable_from` junto (segue a data atual do evento). Estorno em
`_delete_event` copia `payable_from` do original (simetria).

**Alternatives considered**: gravar `sale_date = data do evento` para EDU — rejeitado: mente
sobre o dado (a tela de Comissões exibe `sale_date` como data da venda) e quebra auditoria.

## R5. Acesso do responsável (US2)

`require_vendas` de `app/financeiro/routes.py` guarda exatamente 2 rotas: `/vendas/`
(pipeline) e `/financeiro/comissoes`. (O `require_vendas` de `app/clientes/routes.py` é
outra função — não é tocado.)

**Decision**: helper `_is_educamanto_responsavel()` (settings.educamanto_seller_id ==
current_user.id); `require_vendas` passa a aceitar também esse caso. No `pipeline()`, quando
o usuário só entra por ser responsável (sem COMERCIAL/FINANCEIRO/SUPERADMIN), a query filtra
`CalendarEvent.title.ilike("(EDU%")`. Em `comissoes()`, `can_manage` continua False para ele
→ já cai no filtro `seller_id == current_user.id` existente. Sidebar (`base.html`): links
Pipeline/Comissões ganham `or is_educamanto_responsavel` (context processor novo em
`app/__init__.py`, padrão de `inject_revendedor_flag`); o link Clientes mantém o guard atual.

## R6. Padronização do histórico EducaManto (US3)

Histórico da calculadora (`orcamento/historico`): coluna Vendedor + filtro por usuário (só
superadmin), filtros de período, busca. Histórico EducaManto: só busca, sem autor.

**Decision**: elevar `educamanto/historico` ao mesmo padrão — coluna "Gerado por" e filtro
por usuário visíveis só para superadmin (mesma regra da calculadora), filtros `date_from`/
`date_to` (sobre `created_at`) para todos. `EducaMantoQuote.user` já existe — zero migração.
Calculadora não muda.

## R7. Taxa da comissão EDU

Usuário não pediu taxa própria. `EducaMantoPackage.commission_rate` existe mas serve ao
acréscimo de revendedor no PDF (feature 078) — outra coisa.

**Decision**: mesmas regras de hoje — `event.commission_rate` (override por evento, editável
pelo superadmin em Dados de Venda) senão `default_commission_rate` (2,5%). Padronização de
verdade: EDU e comum diferem só em beneficiário e ciclo.
