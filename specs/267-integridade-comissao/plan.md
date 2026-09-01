# Plano de implementação — Feature 267

**Spec**: `spec.md` · **Branch**: `267-integridade-comissao` (criada de `main` em `da9f711`)
**Migration**: nenhuma · **Endpoints novos**: 0 · **Componentes novos em `@manto/ui`**: 0

> Âncoras conferidas no código em 31/08/2026, **depois** dos merges da 265 e 266. Onde a análise
> original errou, o plano registra a correção.

---

## 1. O que a verificação mudou em relação à spec

| Premissa da análise | Realidade |
|---|---|
| 2 cópias do filtro por `sale_date` | **4** — os controles individuais da planilha têm o mesmo defeito do lote |
| 4 fórmulas de comissão divergentes | **3** — `comissoes_ops.py:183` é recorte de mês, não cálculo; `financeiro/routes.py:120` é `_is_permuta` |
| `update_event_comercial` também não sincroniza | Já sincroniza (a dívida é de 06/08 e está desatualizada); só `update_event_core` falta |

## 2. Ordem de implementação

Blocos independentes; o A é o de maior valor por linha.

```
 A. verify_267.py (Princípio VIII)
 ├─ B. ciclo de pagamento único (4 cópias → 1 fonte)      ← P0 docs/05 #1
 ├─ C. PATCH em bloco sincroniza comissão                  ← P1 docs/05 #6
 ├─ D. KPI do evento lê a comissão real (+ gêmeo Jinja)    ← P1 docs/05 #5
 ├─ E. invalidação completa do cache financeiro            ← P0 docs/05 #2
 ├─ F. núcleo único do vínculo evento↔resposta
 ├─ G. exclusão de evento limpa a resposta
 └─ H. deep-link evento → /financeiro/comissoes (herdado da 266)
```

## 3. Bloco B — o ciclo de pagamento vira fonte única

**O defeito.** A planilha monta o item por `coalesce(payable_from, sale_date)` (comissão EducaManto
entra pelo mês da **realização**) mas as quatro liquidações filtram só por `sale_date`. O item
aparece em maio, o clique procura a venda em maio, acha zero linhas — a tela mostra "pago" sobre um
lote que continua `a_pagar`. E o inverso: o mês da venda liquida uma comissão que ele nem exibe.

**As quatro cópias** (todas com o mesmo `filter` + o mesmo laço `for c in rows`):

| Arquivo | Linha | O que é |
|---|---|---|
| `app/api/financeiro_write.py` | 82-90 | controle **individual** (`api_set_payment_status`, ramo `commission`) |
| `app/api/financeiro_write.py` | 211-219 | liquidação em **lote** (`_bulk_set_commission_period`) |
| `app/financeiro/routes.py` | 1113-1121 | gêmeo Jinja do individual |
| `app/financeiro/routes.py` | 1300-1308 | gêmeo Jinja do lote |

**A extração**, em `app/financeiro/comissoes_ops.py` (funções puras, sem commit e sem `audit` —
esses ficam nas rotas, que é onde `current_user` existe):

```python
def ciclo_de_pagamento_expr():
    """Mês em que a comissão entra no repasse: realização (EducaManto) ou venda."""
    return db.func.coalesce(CommissionPayment.payable_from, CommissionPayment.sale_date)

def liquidar_periodo(seller_id, p_start, p_end, target) -> list[CommissionPayment]:
    """Aplica `status`/`paid_at` às comissões do vendedor no ciclo. Sem commit."""
```

As 4 rotas viram parse + chamada + `audit` + `commit`. `_build_commission_items`
(`financeiro/routes.py:899`) passa a usar `ciclo_de_pagamento_expr()` — fechando o ciclo: **a mesma
expressão que monta o item liquida o item**.

⚠️ **Preservar exatamente:** o `status.in_(["a_pagar", "no_banco", "pago"])` das 4 cópias (inclui
`no_banco`, diferente de `_month_scoped_query`) e a **ausência** do filtro de Loja Virtual — alinhar
as duas pontas na expressão de ciclo é o escopo; mexer no que o lote alcança não é.

⚠️ **Reescrever a docstring de `comissoes_ops.py:1-11`**, que hoje declara explicitamente que
`financeiro/routes.py` **não** importa deste módulo. A extração inverte isso; deixar o texto velho
é pior que a duplicação que ele descrevia.

**De graça na mesma edição:** `c.paid_at = date.today()` → `now_sp().date()` nas 4 (produção roda
UTC; depois das 21h de SP o pagamento é carimbado no dia seguinte).

## 4. Bloco C — PATCH em bloco sincroniza comissão

`update_event_core` (`app/calendar/event_ops.py`) ganha o mesmo parâmetro keyword-only do gêmeo:
`sincronizar_comissao: Any = None`, **por injeção** — `event_ops` não pode importar
`app.financeiro.*` (regra documentada em `:846-847`; import direto seria regressão de arquitetura
e ciclo na prática).

A chamada entra **imediatamente antes do `db.session.add(EventLog(...))`**, ou seja depois de
`_reconcile_characters`, das atribuições de venda/vendedor, do `_create_client_links` e do vínculo
do pré-contrato — e antes do commit. A ordem importa: `_sync_commission_payment` lê `sale_value`,
`seller_id`, `title` (de onde sai `is_educamanto`), `start_at` e, para EducaManto, `_event_cost`.

⚠️ **`db.session.flush()` antes da chamada.** `_reconcile_characters` faz `add`/`delete` de
`EventRole` **sem flush**; para EducaManto a comissão incide sobre o **lucro**, que lê `event.roles`.
Sem o flush a coleção volta do cache sem os cachês novos e a comissão sai errada nessa gravação.

**Chamada incondicional**, como os dois gêmeos. Guardar por "campo mudou" reintroduz metade do bug:
a venda que nunca gerou linha precisa de sync **mesmo quando nada mudou nesta gravação** — é
exatamente o buraco que `_resync_pending_commissions` não cobre (ele só percorre linhas existentes).

⚠️ **Comportamento novo a registrar:** `api_update_event` **não** recusa satélite (o `/comercial`
recusa com 409). Com o sync ligado, um PATCH em bloco sobre satélite passa a mexer na linha dele —
na prática `should_have` dá `False` (venda zerada) e a linha `a_pagar` é cancelada, que é o certo e
o que `group_ops.agrupar` já faz. Fica registrado, não bloqueado.

## 5. Bloco D — o KPI do evento lê a comissão real

`_compute_kpi` (`app/api/agenda_read.py`) hoje recalcula com 2% flat sobre venda−BV, ignorando
EducaManto (5% sobre lucro), Loja Virtual (que não comissiona) e `receives_commission`. Passa a:

1. **Linha real** — soma `amount` das `commission_payments` do evento com status em
   `a_pagar`/`no_banco`/`pago`. Estornos não entram (nascem com `event_id` nulo).
2. **Fallback** — sem nenhuma linha, chama a regra **canônica** `_event_commission`, nunca a fórmula
   flat. Isso resolve sozinho os casos delicados: Loja Virtual devolve 0 por design, beneficiário
   sem `receives_commission` devolve 0, EducaManto usa a base de lucro.
3. **Guarda de cancelado** — `is_cancelled` → 0. O cancelamento **esvazia o backref**, então sem
   esta guarda o fallback voltaria a inventar número exatamente onde o financeiro já estornou.
   `_event_commission` sozinho **não** protege: quem checa cancelamento é a sincronização.

O miolo vai para `comissoes_ops` como `comissao_exibida_do_evento(event, settings) -> tuple[Decimal, str]`
(valor + origem), para o **gêmeo Jinja** (`app/calendar/routes.py:1711-1753`, que calcula com o mesmo
2% flat) chamar a mesma função. Deixá-lo de fora produziria duas telas do mesmo evento com dois
números — o problema que esta feature existe para acabar.

**Contrato de API:** o payload do KPI ganha `commission_source` (`"linha"` | `"estimativa"`). Quando
o valor vem da linha real ele **não é derivável de um percentual único** (EducaManto incide sobre
lucro), então a tela diz "estimativa" enquanto a linha não existe em vez de estampar um percentual
que não corresponde à conta.

**O `lucro` continua sem descontar comissão** — a tela declara "venda − cachês − gastos" e é isso
que ela mostra. Mudar é decisão de negócio, não correção.

## 6. Bloco E — invalidação completa do cache financeiro

`useSetPaymentStatus`/`useBulkPaymentAction` (`lib/financeiro.ts`) e `usePagarMesComissao` invalidam
só `["financeiro-pagamentos", mês]`. Mas o endpoint é **poliforme**: escreve em `CommissionPayment`
**e** `RecurringExpenseEntry`. Comissões, Gastos Recorrentes e Dashboard Financeiro nunca são
invalidados — e com `staleTime: 30_000` + `refetchOnWindowFocus: false` o dado errado **persiste em
tela**. Extrair `invalidarFinanceiro(queryClient)` e chamá-lo nas três mutações.

## 7. Bloco F — núcleo único do vínculo evento↔resposta

Extrair em `formularios_ops.py`, acima de `link_event`, **sem commit**:
`apply_event_link(response, event, *, source="manual")` (grava `event_id`, `event_link_source`,
`ambiguous=False`, `locked=True` e chama `ensure_event_client`) e `clear_event_link(response)`.

`link_event`/`unlink_event` viram cascas finas (validação + núcleo + commit), preservando a
assinatura e o `FormValidationError` que a rota já espera.

⚠️ **Delegar no NÚCLEO, nunca no wrapper.** `link_event` **rouba** uma resposta presa a outro evento;
`set_event_form_response` **recusa** com 409. Delegar no wrapper mudaria o contrato da API.

⚠️ **O núcleo não commita.** `unlink_event` commita; usá-la dentro do laço de desvínculo daria um
commit por resposta e quebraria a transação única do request.

Import no **topo** de `event_ops.py`: `formularios_ops` é folha (importa só `app`, `app.clientes.importer`,
`app.models`, `app.utils` — nenhum toca `app.calendar`), então não há ciclo. O ciclo real é
`routes → event_ops`, e é por isso que `event_ops` importa `routes` dentro de função.

⚠️ **Comportamento novo:** vincular um pré-contrato pela tela do evento passa a inserir a cliente em
`event_clients` — e, se o evento não tinha cliente, ela entra como **Contratante**. Hoje nada é
criado. É o objetivo, mas é escrita a partir de uma tela que não pediu isso.

## 8. Bloco G — exclusão de evento limpa a resposta

Dentro de `_clear_event_side_tables`, como última instrução (cobre de uma vez os três chamadores):
`FormResponse.query.filter_by(event_id=event_id).update({...})` zerando `event_id`,
`event_link_source` e `ambiguous`. A função **não commita** — a linha nova segue a mesma regra.

**Não tocar `event_link_locked`**: quem estava travado por decisão humana continua travado; quem
veio de vínculo automático volta destravado para a fila, que é o certo quando o evento é recriado no
mesmo dia (o caso clássico do sync que apaga e o Google devolve com id novo).

**Desvincula, nunca apaga**: o pré-contrato é o registro da festa e a fonte do histórico pré-2026.

## 9. Bloco H — deep-link do evento para as telas financeiras

As rotas são `/financeiro/comissoes` e `/financeiro/pagamentos` (**não** `/comissoes`), e nenhuma
lê parâmetro de URL hoje — o deep-link precisa ser construído nas duas.

⚠️ **Mês diferente em cada tela:** comissão é escopada por `sale_date`; pagamento por
`CalendarEvent.start_at`. Um evento vendido em maio e realizado em agosto tem os dois links em meses
diferentes — usar o mesmo mês entrega tela vazia. Extrair o mês por `.slice(0, 7)`, **nunca**
`new Date()` (horário de parede).

⚠️ O filtro de vendedor **é privilegiado**: o servidor força o próprio usuário para `COMERCIAL`. O
`KpiGrid` só aparece para FINANCEIRO/SUPERADMIN, então o link nasce no público certo.

⚠️ `ComissoesPage` precisa abrir na aba **Detalhamento** quando vier `?evento=`, senão o filtro fica
invisível.

## 10. Verificação

`verify_267.py` contra `manto_local`, escrito antes do código, conferindo **por conexão separada**.
Casos na spec §Verificação. Ensaio obrigatório antes do merge: contar por mês quantas linhas o
filtro velho pega e quantas o novo pega — a diferença tem de ser **exatamente** as linhas com
`payable_from` preenchido.

## 11. Riscos

| Risco | Mitigação |
|---|---|
| A liquidação passar a alcançar linhas que antes não alcançava | É o objetivo; o ensaio no dump mede exatamente quais |
| Evento que não comissiona por design ganhar número no KPI | Fallback é `_event_commission`, que já devolve 0 nesses casos |
| Evento cancelado voltar a exibir comissão estornada | Guarda `is_cancelled` explícita (o backref fica vazio) |
| EducaManto com comissão errada no PATCH em bloco | `flush()` antes do sync |
| Comissão paga deixar de "acompanhar" a venda na tela | É o comportamento correto — comissão paga é histórico congelado |
