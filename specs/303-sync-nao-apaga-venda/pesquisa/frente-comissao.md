# Frente comissao

Comissão do retido e desconto no repasse (FR-016, FR-017, FR-018, FR-020 e o risco do resync) — feature 303

Tamanho: M — sem endpoint novo e sem tela nova nesta frente. Em app/financeiro/comissoes_ops.py: 5 funções novas e 6 pontos alterados. Em app/calendar/cancel_ops.py: 1 troca de chamada e o congelamento. Em app/financeiro/routes.py: 2 toques aditivos no builder compartilhado. Em app/api/financeiro_read.py: 1 campo serializado. 2 colunas de congelamento na migration da feature (down_revision e5a1c7d93b20). Campos opcionais em 2 payloads, com ajustes pequenos em ComissoesPage e nos tipos TS. 1 script avulso. O peso está no verify: matriz de datas da função pura, comparação linha a linha entre as duas telas e regressão main × branch das comissões do espelho.

## C1 — (a) Como ficam as linhas CommissionPayment depois do cancelamento, para cada estado inicial (a_pagar, no_banco, pago, sem linha)? O event_id continua sendo anulado?

**Decisão.** O cancelamento deixa de chamar `aplicar_estorno_comissao` e passa a chamar uma reconciliação única e idempotente, `reconciliar_comissao_do_cancelado(event, alvo)`, que serve ao cancelamento e ao recálculo da FR-015a. Invariante: a soma das linhas vivas do evento (a_pagar + no_banco + pago) é igual à comissão do retido (alvo). O `event_id` é MANTIDO em todas as linhas; nada é desvinculado.

Por estado inicial (exemplo: cheia 100, alvo 20):
- **a_pagar**: a própria linha é reescrita para o alvo (100 → 20). Mantém `event_id`, `seller_id`, `sale_date` e `payable_from` (o ciclo dela está aberto por definição). Alvo 0 → `status='cancelado'` com nota, sem anular `event_id`.
- **pago**: linha intacta. Nasce uma linha de ajuste: `amount = alvo − liquidado` (−80), `status='a_pagar'`, `event_id = evento`, `original_id =` id da linha liquidada mais recente, `seller_id =` o da linha paga (quem recebeu), `sale_date = payable_from =` data do primeiro repasse aberto (C2), `event_title` copiado, nota legível. Diferença 0 → não cria linha.
- **no_banco**: idêntico a pago (conta como liquidado).
- **sem linha** (os eventos 69, 62 e 203 da PARADA são assim): alvo > 0 → cria linha `a_pagar` com o alvo, `original_id NULL`, `seller_id = _commission_beneficiary`, `sale_date = payable_from =` data do primeiro repasse aberto. Alvo 0 → nada.

Regra geral (cobre recálculo e estados mistos): `liquidado = Σ(pago + no_banco)`; `falta = alvo − liquidado`. Havendo linha a_pagar, a mais antiga recebe `falta` e as demais abertas viram `cancelado`. Não havendo, e `falta ≠ 0`, cria a linha de ajuste. Linha criada pela reconciliação sempre nasce com `sale_date = payable_from`; linha atualizada no lugar mantém as datas (exceção EducaManto, C6).

**Porquê.** - Hoje o cancelamento anula o `event_id` (cancel_ops.py:142, 155) e não tem ramo para `no_banco` (cancel_ops.py:140-155). O evento perde as próprias comissões, e a FR-015a e a FR-020 ficam sem chave.
- Manter o `event_id` só é seguro porque a C4 tira o evento cancelado do alcance de `_sync_commission_payment`.
- Uma função só para cancelar e recalcular reproduz os cenários 19 a 23a: 100 → 20; pago 100 → −80; depois 20 → 10; depois, com a de 10 paga, +15.
- O invariante sobrevive ao 'desfazer pago' da Planilha: `liquidar_periodo` só troca status, não valor (comissoes_ops.py:246-250).
- Evento cancelado com valor retido nunca é apagável (`pode_excluir` recusa venda ou recebido > 0, cancel_ops.py:64-67), então o FK mantido não esbarra em exclusão.

**Alternativas rejeitadas.** 1. Manter `event_id = None` e ligar só por `original_id`: rejeitada. A linha a_pagar reduzida não tem `original_id`, o link `?evento=` continua vazio (ComissoesPage.tsx:221) e o recálculo não acha as linhas.
2. Sempre cancelar a linha a_pagar e criar outra com o alvo: rejeitada. A FR-017 diz 'ajustada', e mover a linha de ciclo sem motivo muda o repasse em que o vendedor a esperava.
3. Estornar inteiro (−100) e criar +20: rejeitada. Duas linhas para um efeito, e o −100 no ciclo antigo é o defeito de hoje.

**Contrato.** Em `app/financeiro/comissoes_ops.py`:

```python
@dataclass(frozen=True)
class ReconciliacaoComissao:
    alvo: Decimal
    liquidado: Decimal          # Σ pago + no_banco
    em_aberto_antes: Decimal    # Σ a_pagar antes
    ajuste: Decimal             # alvo − liquidado
    ciclo: date | None          # data do repasse em que uma linha NOVA entra
    beneficiario_id: int | None
    linha_ids: list[int]

def reconciliar_comissao_do_cancelado(
    event: CalendarEvent, alvo: Decimal, *,
    hoje: date | None = None, simular: bool = False,
) -> ReconciliacaoComissao
```

- Não commita; `simular=True` não escreve (prévia da FR-015).
- Lê as linhas do evento com `with_for_update()` (precedente: `pay_seller_month`, comissoes_ops.py:521-528).
- Notas (constantes em `app/constants.py`): `NOTA_AJUSTE_CANCELAMENTO = 'Ajuste de cancelamento'`, seguida de 'retido R$ X de R$ Y; comissão R$ F → R$ CR'; e '| Cancelado: evento cancelado sem valor retido'.
- Nenhuma coluna nova em `commission_payments`.
- Tipo derivado, sem coluna: `original_id IS NULL` → comissão; `original_id` e `event_id` preenchidos → ajuste de cancelamento; `original_id` preenchido e `event_id NULL` → estorno órfão (legado ou exclusão).

**Pontos de toque.**
- app/calendar/cancel_ops.py:273 (troca a chamada a aplicar_estorno_comissao pela reconciliação; pula satélite e venda virtual)
- app/calendar/cancel_ops.py:128-155 (aplicar_estorno_comissao fica só para _delete_event; docstring reescrita — FR-025)
- app/calendar/routes.py:325-327 (_delete_event continua chamando aplicar_estorno_comissao — não tocar)
- app/financeiro/comissoes_ops.py (função nova reconciliar_comissao_do_cancelado, depois de _comissao_existente :776-801)
- app/models.py:897-904 e :917-925 (docstring de CommissionPayment: linha de ajuste, significado de sale_date/payable_from/original_id nela)
- app/constants.py:466 (constante de nota nova ao lado de NOTA_CICLO_VALOR_TARDIO)

**Riscos.**
- Linha paga desatualizada em relação à regra (venda aumentada depois do pagamento; `_sync` nunca reescreve paga, comissoes_ops.py:865): o ajuste traz o total para cheia-pela-regra × proporção e pode nascer POSITIVO num cancelamento sem devolução. É a letra da FR-016; registrar no docs/04.
- Corrida com a liquidação na Planilha no mesmo instante: o `with_for_update` cobre só as linhas do evento, não as outras linhas do ciclo de destino.
- `set_commission_status` do Jinja (financeiro/routes.py:1549-1568) troca o status de qualquer linha individualmente e quebra o invariante. Já existe hoje e só responde pelo domínio direto do backend; vira dívida no docs/05.

**Verify.** Cenários 19, 20, 21, 22 e 23a, conferindo por conexão separada: `event_id` preenchido em todas as linhas, `original_id` só no ajuste, e Σ vivas = alvo em cada passo.

Cobrir também:
- o caso 'sem linha' (evento com venda e nenhuma CommissionPayment);
- o estado misto depois de 'desfazer pago' na Planilha (base a_pagar 100 + ajuste a_pagar −80; recálculo consolida em uma linha);
- idempotência: chamar o recálculo duas vezes não cria segunda linha.

**Revisão adversarial: parcial.** O desenho central se sustenta (event_id mantido + reconciliação única e idempotente + invariante Σ vivas = alvo). Reproduzi os cenários 19–23a à mão e fecham. Quatro furos de contrato:

1. A regra geral não diz o que fazer quando falta == 0 e existe linha a_pagar (ex.: a linha do retido foi paga e sobrou um ajuste aberto). A regra do estado 'a_pagar' diz 'alvo 0 → cancelado'; a geral diz 'a mais antiga recebe falta'. Uma linha a_pagar de R$ 0,00 e uma linha cancelada não são equivalentes para a C2 (ciclo 'aberto') nem para a C10.

2. A reconciliação reescreve valor de comissão e cria linha de dinheiro sem audit() nem EventLog. Toda liquidação audita (comissoes_ops.py:540-548; financeiro_write.py:89-95) e a FR-023 pede rastro. A nota textual, anexada a cada recálculo, cresce sem limite: 'idempotente' vale para linhas, não para notes (o precedente _com_marca_do_ciclo, comissoes_ops.py:732-738, evita repetição).

3. simular=True com with_for_update() dentro de um GET (impacto-exclusao) trava linhas de comissão durante a leitura da prévia.

4. 'Sem linha viva' no recálculo (FR-015a): depois de 'Tudo' devolvido a linha a_pagar vira 'cancelado'; se a devolução baixar, a linha nova usa _commission_beneficiary(event) lido NA HORA, e a aba Comercial do cancelado continua editável. O vendedor trocado depois do cancelamento recebe a comissão do retido. A própria C6 rejeita isso para o ajuste ('beneficiário sai da linha, não do evento').

Ressalva de consumidor: a justificativa 'FK mantido não esbarra em exclusão' só cobre retido > 0. Cancelado com venda 0, sem comprovante, contrato nem escalado (ex-satélite com linha paga, o caso 287 da PARADA) passa em pode_excluir, e DELETE /api/events/<id> não olha is_cancelled. _delete_event roda aplicar_estorno_comissao sobre as linhas ligadas: o ajuste a_pagar vira 'cancelado' e nasce um estorno órfão no ciclo ANTIGO da venda — o defeito que a 303 quer eliminar. Hoje só pela API direta: a tela não oferece o botão para cancelado.

**Emenda.** 1. Regra geral explícita: falta == 0 → toda linha a_pagar do evento vira 'cancelado' (nunca a_pagar de R$ 0,00); falta ≠ 0 → a mais antiga recebe falta e as demais são canceladas.

2. A reconciliação chama audit('payment','commission', …) por linha alterada ou criada e o chamador grava EventLog. A nota é substituída por prefixo (helper no molde de _com_marca_do_ciclo), não anexada.

3. with_for_update() só quando simular=False.

4. Beneficiário de linha nova: seller_id da linha mais recente do evento em QUALQUER status (inclusive 'cancelado'); só na falta de qualquer linha, _beneficiario_comissionado(event).

5. Ordem fixa em cancelar_evento: congelar → _registrar_devolucao → flush → calcular alvo → reconciliar → cancelled_at. O touchpoint ':273 troca a chamada' fica antes da devolução (:274) e não serve como está.

6. api_delete_event recusa evento cancelado com 409 — uma linha, fecha o caminho do estorno órfão.

**Evidência da revisão.** app/calendar/cancel_ops.py:64-74 (pode_excluir), :139-155 (aplicar_estorno_comissao sem ramo no_banco), :272-274 (ordem atual); app/api/agenda_write.py:504-538 (DELETE sem checar cancelado); app/calendar/routes.py:320-337; frontend/apps/internal/src/components/EventDetail/EventHeader.tsx:306 (botão só se !cancelado); app/financeiro/comissoes_ops.py:540-548, 732-738; docs/PARADA_REMOCAO_JINJA.md:112-116

## C2 — (b) Como 'primeiro repasse do beneficiário ainda não liquidado' vira sale_date/payable_from, de modo que Planilha e Comissões mostrem a mesma coisa sem reabrir repasse pago?

**Decisão.** Função pura `primeiro_repasse_aberto(seller_id, hoje) -> date`, sobre `ciclo_de_pagamento_expr()` e os status a_pagar/no_banco/pago. Candidatos em ordem:
1. o ciclo M−1, só se `hoje.day <= 5` E houver linha a_pagar do beneficiário nele (o repasse do dia 5 ainda não saiu);
2. o ciclo corrente M, se não tem linha do beneficiário ou tem alguma a_pagar;
3. M+1, M+2… pela mesma regra de M.

Ciclo cujas linhas são todas pago/no_banco está liquidado e é pulado. A data devolvida é `hoje` presa ao intervalo do ciclo escolhido (clamp).

Toda linha CRIADA pela reconciliação recebe `sale_date = payable_from =` essa data. Com isso ela se comporta como comissão comum do ciclo C nas duas telas sem mudar consulta nenhuma: a Planilha do mês C+1 a soma no item do vendedor, e a tela de Comissões a mostra no mês C, onde o 'Pagar Mês' de C a liquida.

**Porquê.** - A Planilha monta e liquida por `coalesce(payable_from, sale_date, created_at)` (comissoes_ops.py:212-216; routes.py:918-925), e o mês M mostra o ciclo M−1 (financeiro_read.py:717-720).
- A tela de Comissões recorta só por `sale_date` (comissoes_ops.py:299-311).
- Se o ajuste herdasse o `sale_date` da venda, como o estorno de hoje (cancel_ops.py:148-149), reabriria o mês da venda na tela de Comissões, e o 'Pagar Mês' desse mês antigo o liquidaria fora de qualquer repasse.
- Igualar as duas datas é o único arranjo em que as duas telas concordam sem tocar `_month_scoped_query`, suas duas cópias e o gêmeo Jinja.
- O limite no dia 5 atende à resposta do dono (cancelamento em 02/10 sai no repasse de 05/10). Também evita abater de um repasse que já saiu do banco e só não foi marcado.

**Alternativas rejeitadas.** 1. `payable_from = hoje` e `sale_date` herdado: rejeitada. Certa na Planilha, errada em Comissões (mês da venda reaberto, saldo zerado).
2. Mudar `_month_scoped_query` para o ciclo: rejeitada. Troca o eixo da tela para EducaManto e para a regra da 299 ('mês da comissão = mês da venda', ComissoesPage.tsx:301-302) e obriga a mexer em três consultas e no Jinja.
3. Procurar para trás o primeiro ciclo não liquidado, sem limite: rejeitada. Cairia em ciclos antigos nunca marcados, numa Planilha que ninguém abre.
4. Sempre o ciclo do mês do cancelamento: rejeitada. Contraria a FR-018 entre os dias 1 e 5 e reabre o ciclo corrente quando ele foi pago adiantado.

**Contrato.** ```python
DIA_DO_REPASSE = 5  # topo de comissoes_ops.py; mesmo dia do due_date da Planilha

def primeiro_repasse_aberto(seller_id: int, hoje: date) -> date
    # data dentro do ciclo de destino; no máximo 24 ciclos à frente,
    # com fallback no ciclo corrente
```

- 'Liquidado' = existe linha do beneficiário no ciclo e nenhuma está a_pagar.
- Linha de ajuste ou criada: `sale_date = payable_from = primeiro_repasse_aberto(seller_id, hoje)`.
- Na linha de ajuste, a coluna 'Data da venda' da tela mostra a data do ajuste; documentar em models.py:917-920.

**Pontos de toque.**
- app/financeiro/comissoes_ops.py:188-216 (ciclo_de_pagamento_expr — reusada, não alterada)
- app/financeiro/comissoes_ops.py:219-251 (liquidar_periodo — não muda; passa a liquidar o ajuste junto com o ciclo)
- app/financeiro/comissoes_ops.py:296-316 (_month_scoped_query — eixo não muda)
- app/financeiro/routes.py:904-961 (_build_commission_items — ciclo não muda)
- app/api/financeiro_read.py:717-720 e app/financeiro/routes.py:1054-1058 (o dia 5 já é literal aqui)

**Riscos.**
- Entre os dias 1 e 5, se o financeiro já pagou o ciclo anterior e não marcou, o desconto abate de um item que já saiu. A janela cai de 'o mês inteiro' para cinco dias, mas não some.
- Ciclo corrente pago adiantado pelo 'Pagar Mês' no meio do mês: o desconto vai para M+1 mesmo que entrem vendas novas em M depois. É conservador de propósito.
- Vendedor com linhas EducaManto ou da 299 (`payable_from` diferente do mês de `sale_date`): o mês C pode parecer 'Pago' em Comissões e estar aberto na Planilha. A divergência de eixo já existe e não é corrigida aqui.
- Desconto maior que o repasse: o item fica negativo. A spec já aceita isso nos Casos de borda.

**Verify.** **Matriz da função pura, com `hoje` injetado e vendedor descartável:**
1. dia 3, M−1 com a_pagar → M−1;
2. dia 3, M−1 todo pago → M;
3. dia 3, M−1 sem linha → M;
4. dia 20, M−1 com a_pagar → M;
5. M todo pago ou no_banco → M+1.

**Cenário HTTP (20 e 21):** linha paga com `sale_date` de três meses atrás e vendedor sem outras linhas. O ciclo esperado é o mês corrente em qualquer dia do mês — calcular o esperado pelo estado semeado, não chamando a função (seria tautologia).

**Provar 'não reabre':**
- o item `seller:ciclo-antigo` da Planilha continua 'pago' com o mesmo valor;
- o mês antigo em Comissões continua `month_status='pago'` com pendente 0;
- o ajuste NÃO aparece no mês da venda.

**Revisão adversarial: parcial.** Igualar sale_date e payable_from é de fato o único arranjo que faz as duas telas concordarem sem tocar _month_scoped_query. Conferi os eixos (comissoes_ops.py:212-216 × 299-311) e o ciclo M−1 na Planilha do mês M (financeiro_read.py:717-720). Três problemas:

1. 'Aberto = tem alguma a_pagar' conta linha de R$ 0,00 e estorno órfão. A 299 cria linha a_pagar de R$ 0,00 para venda simbólica; se ela nasce depois de o ciclo M−1 ter sido pago, o item fica 'nao_pago' sem mudar de valor (routes.py:939-944). Entre os dias 1 e 5 a regra 1 poria o desconto nesse ciclo já pago — o que a FR-018 proíbe. Um estorno órfão a_pagar em M−1 ou M tem o mesmo efeito.

2. O clamp gera data que a tela mostra errada. formatDate faz new Date('AAAA-MM-DD').toLocaleDateString (ComissoesPage.tsx:40-43): data sem hora é lida como UTC e exibida em −3h, um dia antes. Defeito pré-existente, mas o clamp produz exatamente os casos de borda: ajuste posto em 01/10 (ciclo M+1) aparece na lista de outubro como '30/09/2026'. Não rodei a tela; a afirmação vem da semântica do Date.

3. Com M pré-pago, a linha nasce com sale_date no futuro (primeiro dia de M+1) numa coluna chamada 'Data da venda'. Sem o campo 'tipo' da C9 o bundle em cache mostra isso como venda.

Menores: a função consulta o banco, então não é 'pura' (a matriz do verify precisa de linhas semeadas); DIA_DO_REPASSE vira a terceira cópia do 5 (financeiro_read.py:720; routes.py:1058).

**Emenda.** 1. Definição única de aberto/liquidado, compartilhada com a C10: o ciclo está aberto para o beneficiário quando não tem linha, ou tem linha a_pagar com amount ≠ 0 e event_id preenchido (ou original_id nulo). Linha de R$ 0,00 e estorno órfão não abrem ciclo.

2. Registrar no plano o defeito de formatDate e conferir na tela com data no dia 1º. Ou o clamp evita o dia 1º, ou a 303 corrige formatDate nas três tabelas de ComissoesPage (mudança de uma função).

3. Documentar em models.py:917-920 que sale_date de linha criada pela reconciliação é data de ciclo; a tela rotula pelo campo tipo.

4. Comentário nos dois literais apontando para DIA_DO_REPASSE, sem refatorar. Trocar 'função pura' por 'função de leitura' no contrato.

**Evidência da revisão.** app/financeiro/comissoes_ops.py:212-216, 237-251, 299-311, 755-773; app/financeiro/routes.py:939-944, 1054-1058; app/api/financeiro_read.py:717-720; frontend/apps/internal/src/pages/ComissoesPage.tsx:40-43, 59, 254, 265

## C3 — (c) Ajuste positivo (FR-015a): `_pending_reversals_query` só pega negativo — estende para positivo?

**Decisão.** Não estende; estreita. `_pending_reversals_query` ganha o filtro `CommissionPayment.event_id.is_(None)` e passa a trazer só o estorno ÓRFÃO (evento apagado ou legado da 224). O ajuste da 303, positivo ou negativo, tem `event_id` e ciclo próprio (C2) e entra nas duas telas pela via normal: `_month_scoped_query` em Comissões e o ciclo na Planilha. O mesmo filtro entra na cópia inline `reversal_ids` de `get_month_summary_by_seller`.

Efeito: o 'Pagar Mês' de um mês qualquer deixa de liquidar desconto de outro ciclo, e o desconto não aparece duas vezes (mês do ciclo + mês corrente).

**Porquê.** - `_estornos_do_mes` existe para resgatar estorno preso num `sale_date` antigo (comissoes_ops.py:358-372). O ajuste da 303 não fica preso, porque nasce no ciclo aberto.
- Se continuasse passando por ali, um desconto posto em M−1 ou M+1 apareceria também no mês corrente, e `pay_seller_month` o pagaria em qualquer mês (comissoes_ops.py:517-518). É o defeito descrito na História 4.
- O positivo (+15) é só uma linha a_pagar do ciclo C: o 'Pagar Mês' de C e o item da Planilha o pagam como qualquer comissão.
- `event_id IS NULL` separa os dois casos sem coluna nova: o estorno legado nasce com `event_id=None` (cancel_ops.py:145).

**Alternativas rejeitadas.** 1. Tirar o `amount < 0` para pegar positivos: rejeitada. Todo a_pagar positivo do vendedor viraria 'estorno pendente' em todo mês.
2. Coluna `kind` em `commission_payments`: rejeitada. `original_id` + `event_id` já distinguem os três tipos (Princípio I), e a migration fica menor.
3. Distinguir por marca em `notes` (padrão da 299, comissoes_ops.py:713-729): rejeitada para filtro SQL de dinheiro.

**Contrato.** - `_pending_reversals_query(seller_id=None)`: filtros `status == 'a_pagar'`, `amount < 0` e `event_id IS NULL`.
- Assinaturas inalteradas.
- Sem campo novo por causa desta decisão.

**Pontos de toque.**
- app/financeiro/comissoes_ops.py:324-340 (_pending_reversals_query: + event_id IS NULL; docstring)
- app/financeiro/comissoes_ops.py:438-443 (reversal_ids inline: mesmo filtro)
- app/financeiro/comissoes_ops.py:358-372 (docstring de _estornos_do_mes)
- app/financeiro/comissoes_ops.py:516-518 (pay_seller_month herda o filtro)
- app/calendar/cancel_ops.py:128-138 e frontend/apps/internal/src/lib/eventOps.ts:125-128 (textos que prometem desconto via _seller_payable_rows — FR-025)

**Riscos.**
- O gêmeo Jinja `comissoes()` (financeiro/routes.py:1516-1523, 1532) NÃO recebe o filtro, porque a spec pôs o painel antigo fora de escopo. Lá o desconto da 303 aparece no painel 'Estornos pendentes' em todo mês e conta em dobro no total. Dívida no docs/05; a página só responde pelo domínio direto do backend.
- Estorno órfão já pendente em produção (o do 1244 e outros) segue a regra antiga: ciclo da venda na Planilha, mês corrente em Comissões. Ver C12 e a pergunta em aberto.

**Verify.** Cenário 23a, segunda metade (ajuste de +15):
- aparece uma vez em Comissões, no mês do ciclo, e uma vez na Planilha (item `seller:ciclo`);
- o 'Pagar Mês' desse mês o liquida.

Cenário que DEVE não acontecer: com um desconto da 303 posto num ciclo diferente do corrente (forçar com `hoje` injetado ou com o ciclo corrente pré-pago), o 'Pagar Mês' do mês corrente NÃO muda o status dele, e ele não aparece nas entries do mês corrente.

Regressão: um estorno órfão semeado (`event_id NULL`, negativo) continua aparecendo no mês corrente.

**Revisão adversarial: sim.** Não consegui refutar. O estorno de hoje sempre nasce com event_id=None (cancel_ops.py:145), então event_id IS NULL separa o órfão do ajuste da 303 sem coluna nova. Os dois pontos que precisam do filtro são os citados (comissoes_ops.py:333-336 e a cópia inline :438-443), e pay_seller_month herda em :518.

Resíduo: pay_seller_month continua liquidando órfão em QUALQUER mês (:517-518 não checa mês corrente). É comportamento antigo, mas o docstring novo não pode prometer o contrário.

Falta uma contagem: linha a_pagar negativa COM event_id em produção deixaria de ser resgatada no mês corrente.

**Emenda.** Acrescentar à lista de contagens pré-deploy (só leitura): status='a_pagar' AND amount<0 AND event_id IS NOT NULL — esperado 0. Se houver, o plano decide antes de aplicar o filtro.

No docstring de _pending_reversals_query e _estornos_do_mes, dizer que o órfão segue liquidável pelo 'Pagar Mês' de qualquer mês (dívida no docs/05, junto do painel Jinja).

**Evidência da revisão.** app/calendar/cancel_ops.py:144-155; app/financeiro/comissoes_ops.py:324-340, 358-372, 438-443, 516-518; app/financeiro/routes.py:1516-1532 (gêmeo Jinja fora de escopo, spec.md:759-760)

## C4 — (d) Como `_sync_commission_payment` e `_resync_pending_commissions` deixam de zerar a comissão do retido?

**Decisão.** Retorno antecipado no topo de `_sync_commission_payment`: `if event.is_cancelled: return`. As linhas de evento cancelado passam a ser propriedade exclusiva da reconciliação do cancelamento; a sincronização não cria, não reescreve e não cancela nada nelas. A cláusula `and not event.is_cancelled` de `should_have` sai, com o comentário reescrito.

`_resync_pending_commissions` não muda: continua selecionando a linha a_pagar do cancelado e a chamada vira no-op.

A elegibilidade hoje inline em `should_have` é extraída para `_beneficiario_comissionado(event, settings)`, reusada por `comissao_cheia_do_evento` (C11). A regra 'quem comissiona' fica com uma fonte só.

**Porquê.** - Hoje, para evento cancelado, `should_have` é falso e a linha a_pagar existente vira 'cancelado' (comissoes_ops.py:816-839).
- `_resync_pending_commissions` roda em todo GET de Comissões e da Planilha, API e Jinja (financeiro_read.py:566, 670; financeiro/routes.py:1010, 1483), sobre toda linha a_pagar com `event_id` e valor ≥ 0 (comissoes_ops.py:885-893). Com o `event_id` mantido (C1), a linha de 20 e o ajuste de +15 seriam zerados na primeira abertura.
- `_comissao_existente` pega a linha não cancelada mais recente (comissoes_ops.py:793-801), que pode ser o próprio ajuste.
- O retorno no topo cobre os nove chamadores de uma vez: resync; aba comercial, criação e orçamento (agenda_write.py:951-960, 1087-1098, 1203-1260, 2170-2219); Jinja (calendar/routes.py:974, 1536, 3794); grupo (group_ops.py:180-183).
- Não existe 'descancelar' evento (busca por `cancelled_at = None` só acha a produção de figurino), então a guarda não precisa de caminho de volta.

**Alternativas rejeitadas.** 1. Ensinar `_sync_commission_payment` a calcular a comissão do retido (`should_have` verdadeiro para cancelado): rejeitada. Ela não sabe tratar linha paga ou no banco, e recalcularia o que a FR-026 manda ler do que ficou gravado.
2. Filtrar o cancelado só na consulta do resync: rejeitada como única trava. A aba Comercial do cancelado continua editável e chama a sincronização direto.
3. Deixar `should_have` inline e duplicar as três condições na função da cheia: rejeitada (Princípio I; 'cortesia nunca comissiona' teria duas cópias).

**Contrato.** ```python
def _beneficiario_comissionado(event, settings) -> User | None
```

- Devolve o beneficiário quando a venda comissiona: `sale_value` preenchido, beneficiário com `receives_commission`, não é cortesia/permuta, não é Loja Virtual.
- NÃO olha cancelamento.
- `_sync_commission_payment(event) -> None`: mesma assinatura; primeira linha útil passa a ser o retorno para cancelado.

**Pontos de toque.**
- app/financeiro/comissoes_ops.py:804-839 (retorno antecipado; should_have passa a usar _beneficiario_comissionado; comentário de :820-822 reescrito)
- app/financeiro/comissoes_ops.py:879-901 (_resync_pending_commissions — sem mudança de código; docstring cita a 303)
- app/financeiro/routes.py:29-30 (o Jinja reimporta as duas daqui — nada a tocar)
- docs/04_GUIA_DE_DOMINIOS.md:206-230 (regra de comissão: ramo 'cancelado' muda)

**Riscos.**
- Extração em código de dinheiro: a PARADA (docs/PARADA_REMOCAO_JINJA.md:89-91) pede comparação main × branch. Sem ela, uma inversão de condição muda comissão em silêncio.
- Evento cancelado antes da 303 que ainda tenha linha a_pagar com `event_id` (não deveria existir, porque a 224 desvincula) deixaria de ser cancelada pelo resync. Contar no espelho antes do deploy: linhas a_pagar ligadas a evento com `cancelled_at`.

**Verify.** **Cenário 35, com prova por mutação:** depois do cancelamento, abrir `GET /api/financeiro/comissoes` e `GET /api/financeiro/pagamentos` DUAS vezes cada e conferir, por conexão separada, que a linha do retido continua a_pagar com 20,00 (18,00 com BV) e que o ajuste de +15 continua a_pagar. Sem o retorno antecipado, esse cenário tem de falhar.

Também: salvar a aba Comercial do evento cancelado (mudando venda e taxa) e conferir que nenhuma linha muda.

**Regressão de dinheiro:** dump de (id, amount, status, seller_id, payable_from, notes) de todas as `commission_payments` depois de um resync no espelho, main × branch — idêntico.

**Revisão adversarial: sim.** Conferi os chamadores: o retorno no topo cobre todos — resync (comissoes_ops.py:900), agenda_write.py:951/1087/1203/2170, calendar/routes.py:974/1536/3794, e os injetados em event_ops.py:946-956 e :1136, group_ops.py:180-183 e orcamento_evento_ops.py:406-408. Não existe 'descancelar': o único cancelled_at = None é de figurino (producao_ops.py:896, 906).

Hoje o ramo é inerte para cancelado, porque aplicar_estorno_comissao desvincula as linhas; a guarda passa a ser o que protege a linha do retido.

A extração de _beneficiario_comissionado é necessária, não lateral: _event_commission calcula comissão com beneficiário None (comissoes_ops.py:666-668 só barra quem existe e não comissiona) e não conhece cortesia. Sem a extração, a 'cheia' da C11 sairia errada para evento sem vendedor ou cortesia com valor.

Risco residual não listado: some a autocorreção. Hoje o resync conserta qualquer a_pagar divergente; para cancelado, nada mais conserta. Uma gravação concorrente da aba Comercial ou um resync em voo que emita UPDATE de amount depois do commit do cancelamento deixa a linha errada para sempre. A janela é pequena (só quando a regra mudou o valor).

**Emenda.** Manter. Dois acréscimos:

1. O retorno para Loja Virtual continua ANTES de should_have, como hoje (:810-811). Se _beneficiario_comissionado também checar virtual, o comportamento é idêntico só enquanto esse retorno ficar — comentar.

2. O verify cruzado (C8) checa o invariante Σ vivas = comissao_retido para TODO cancelado com congelamento no espelho, não só os semeados — é o que substitui a autocorreção perdida.

A comparação main × branch da PARADA é obrigatória para a extração, como a proposta já diz.

**Evidência da revisão.** app/financeiro/comissoes_ops.py:656-686, 804-839, 879-901; app/calendar/event_ops.py:946-956, 1136-1137; app/calendar/group_ops.py:180-183; app/calendar/orcamento_evento_ops.py:406-408; app/figurino/producao_ops.py:896, 906; docs/PARADA_REMOCAO_JINJA.md:89-91

## C5 — (e) O que `comissao_exibida_do_evento` devolve para evento cancelado?

**Decisão.** A camada 1 deixa de devolver 0 fixo. Para cancelado, devolve `(resumo_do_cancelado(event).comissao_retido, 'linha')` — o valor da função única da FR-026, calculado do que ficou congelado, não a soma das linhas nem `_event_commission`.

Evento cancelado antes da 303 (sem congelamento), satélite e venda virtual continuam em `(0, 'linha')`. A origem continua sendo 'linha': nenhum valor novo no enum.

**Porquê.** - A guarda de hoje (comissoes_ops.py:285-286) existe porque o cancelamento esvaziava o backref; com a C1 isso deixa de ser verdade, e a tela do evento mostraria 0 onde Planilha e Comissões mostram 20.
- Ler da função da FR-026 faz tela do evento, Cancelamentos e DRE mostrarem o mesmo número por construção (FR-020). O verify confere que Σ linhas = esse número.
- Manter 'linha' evita que o bundle em cache caia no `else` e estampe 'Comissão (5%)' sobre o valor do retido (ComercialSection.tsx:122-125; tipo em lib/agenda.ts:508).
- O Jinja `event_detail` chama a mesma função (calendar/routes.py:1779-1781) e herda o valor sem ser tocado.

**Alternativas rejeitadas.** 1. Somar as linhas vivas também para cancelado: rejeitada como fonte. Dá o mesmo número hoje, mas a FR-026 manda todas as telas lerem a função única, e um status trocado à mão no Jinja faria a tela do evento divergir da DRE.
2. Origem nova 'cancelamento': rejeitada. É valor novo num campo que já existe, e o bundle antigo o trataria como estimativa. O contexto do cancelamento vai no bloco 'Resultado do cancelamento' (FR-037), de outra frente.

**Contrato.** - `comissao_exibida_do_evento(event, settings) -> tuple[Decimal, str]`: assinatura e valores de origem inalterados ('linha' | 'estimativa').
- Para cancelado, o import de `app.calendar.cancel_ops.resumo_do_cancelado` é tardio, dentro do ramo (`cancel_ops` também importa `comissoes_ops` de forma tardia; sem ciclo no boot).
- Depende da frente do resumo (FR-026) expor `comissao_retido: Decimal` — ver C11.

**Pontos de toque.**
- app/financeiro/comissoes_ops.py:259-293 (ramo do cancelado e docstring das três camadas)
- app/api/agenda_read.py:395-412 (consumidor; sem mudança de contrato)
- app/calendar/routes.py:1779-1781 (consumidor Jinja; não tocar)
- frontend/apps/internal/src/lib/agenda.ts:504-508 (comentário do campo; tipo inalterado)

**Riscos.**
- Dependência cruzada financeiro → calendar por import tardio: renomear `resumo_do_cancelado` quebra a tela do evento em silêncio (docs/00 §7). Citar o nome no docstring dos dois lados.
- Num grupo, `_compute_kpi` passa o LÍDER (agenda_read.py:357-358, 397). Abrir um satélite cancelado de um líder vivo mostra a comissão do líder; correto, mas conferir no verify.

**Verify.** Cenário 40: `kpi.commission` do evento cancelado = 18,00 com `commission_source='linha'`. O mesmo valor em:
- (a) Σ linhas vivas do evento, por conexão separada;
- (b) página de Cancelamentos;
- (c) linha Comissões da DRE do mês do cancelamento.

Cancelado 'legado' (`cancelled_at` sem congelamento, semeado direto no banco): 0,00.

Depois de alterar a devolução (23a), o valor acompanha (10,00; depois 25,00).

**Revisão adversarial: parcial.** Ler de resumo_do_cancelado é o que a FR-026 manda, e manter a origem 'linha' protege o bundle em cache (ComercialSection.tsx:122). A guarda de :285-286 não pode simplesmente sair: com alvo 0 a linha vira 'cancelado', não sobra linha viva, e a camada 3 estamparia a comissão CHEIA como estimativa.

A frase 'mostram o mesmo número por construção' só vale entre as telas que leem a função. Planilha e Comissões leem LINHAS, e a linha só acompanha se a reconciliação rodar a cada mudança do retido. O retido = pago − devolvido é lido na hora, e o 'pago' de um cancelado continua editável: adicionar, corrigir e excluir comprovante não checam cancelamento (agenda_write.py:1540-1613; calendar/routes.py:1097-1134). Um comprovante lançado depois do cancelamento muda kpi.commission, Cancelamentos e DRE, e deixa Planilha e Comissões no valor antigo — FR-020 quebrada sem erro.

Segundo ponto: o link 'ver em comissões' da tela do evento leva a ?mes=<mês da venda>&vendedor=<seller do evento>&evento=<id> (ComercialSection.tsx:92-94). O ajuste mora em outro mês (C2) e, no EducaManto, em outro beneficiário. A tela do evento mostra 20 e o link abre uma lista só com a linha paga de 100.

**Emenda.** 1. Decidir no plano, junto da frente da devolução, uma de duas: (a) comprovante de evento cancelado fica travado nos três endpoints (409 com motivo) — mais simples e coerente com a FR-015a, que já trava a devolução; ou (b) os três chamam a reconciliação. Recomendo (a). Em qualquer caso, cenário no verify.

2. resumo_do_cancelado expõe o ciclo e o beneficiário de cada linha viva (saem da própria reconciliação). O bloco 'Resultado do cancelamento' linka para o mês e o vendedor do ajuste, não para o mês da venda.

3. Docstring das três camadas cita resumo_do_cancelado pelo nome nos dois lados, como a proposta já prevê.

**Evidência da revisão.** app/financeiro/comissoes_ops.py:285-293; app/api/agenda_read.py:357-358, 395-412; app/api/agenda_write.py:1540-1613; app/calendar/routes.py:1097-1134, 1779-1781; frontend/apps/internal/src/components/EventDetail/ComercialSection.tsx:92-94, 122

## C6 — (f) EducaManto (beneficiário = responsável; comissão cheia sobre o lucro) e grupo comercial (venda no líder): o que muda na regra?

**Decisão.** **EducaManto**
- A cheia congelada é a que `_event_commission` dá no momento do cancelamento: 5% (ou a taxa do evento) sobre venda − BV − cachês. A proporção `retido ÷ venda` se aplica a ela igual à comum.
- O beneficiário do ajuste é o `seller_id` da linha liquidada (o responsável que recebeu). Para linha nova sem nenhuma anterior, `_commission_beneficiary(event, settings)`.
- Ciclo: a linha a_pagar reduzida troca `payable_from` (que era o dia da realização) pela data do primeiro repasse aberto, porque a realização não vai acontecer. O `sale_date` fica. Reconhecimento da linha: `payable_from` preenchido sem a marca da 299. Ajustes seguem a C2.

**Grupo**
- Satélite cancelado não chama a reconciliação: nenhuma linha muda, mesmo que exista linha paga antiga nele.
- Líder só é cancelado depois de desagrupado (regra da 224, cancel_ops.py:267-270), então é reconciliado como evento avulso, com a venda do grupo que ficou nele.
- Venda zerada (ex-satélite) → cheia 0, alvo 0, sem divisão por zero.
- Venda virtual não entra (FR-021).

**Porquê.** - A FR-018 já diz 'para comissão comum e EducaManto'. Deixar `payable_from` = dia do evento seguraria a comissão do retido até o mês seguinte a uma data que não significa mais nada; se o evento for passado, cairia num ciclo já pago (comissoes_ops.py:845-846).
- O beneficiário sai da linha, e não do evento, porque a aba Comercial do cancelado continua editável e o vendedor pode ser trocado depois.
- Satélite tem venda zerada ao agrupar, e a sincronização já cancelou a linha a pagar dele (group_ops.py:173-183). A spec manda não mexer em comissão nem BV de satélite.

**Alternativas rejeitadas.** 1. EducaManto mantém `payable_from` = data do evento: rejeitada (paga meses depois, ou reabre ciclo pago em evento passado).
2. Beneficiário sempre recalculado do evento: rejeitada (um vendedor trocado depois do cancelamento receberia o desconto de comissão que não recebeu).
3. Reconciliar o líder ainda agrupado: rejeitada (a spec mantém a exigência de desagrupar).

**Contrato.** Dentro de `reconciliar_comissao_do_cancelado`:
- linha a_pagar com `payable_from IS NOT NULL` e sem `NOTA_CICLO_VALOR_TARDIO` em `notes` → `payable_from = primeiro_repasse_aberto(linha.seller_id, hoje)`, e a nota ganha '| Ciclo: evento cancelado';
- linha da 299 (com a marca) e linha comum mantêm o ciclo.

Em `cancelar_evento`: `if event.is_satellite or is_loja_virtual(event):` não congela, não reconcilia e não registra devolução.

**Pontos de toque.**
- app/financeiro/comissoes_ops.py:643-653 (_commission_beneficiary — reusada)
- app/financeiro/comissoes_ops.py:656-686 (_event_commission — reusada, não alterada)
- app/financeiro/comissoes_ops.py:713-729 (_ciclo_marcado_pela_299 — reusada para reconhecer payable_from de realização)
- app/calendar/cancel_ops.py:262-274 (guarda de satélite e de venda virtual antes de reconciliar)
- app/calendar/group_ops.py:173-183, 204-231 (só leitura: por que o satélite não tem linha e o ex-líder guarda a venda)

**Riscos.**
- EducaManto ex-líder de grupo: depois de desagrupar, `_event_commission` usa só os cachês do próprio evento (comissoes_ops.py:676), e a cheia congelada fica MAIOR do que era com o grupo montado. Consequência da regra 'desagrupe antes'; registrar no docs/05.
- Os cachês que entram na base EducaManto são os da escala no instante do cancelamento. Se a escala foi desmontada antes de cancelar, a cheia sobe. O congelamento impede só a mudança posterior.
- Na tela de Comissões a linha EducaManto continua no mês da venda (eixo da tela); na Planilha ela vai para o ciclo novo. Mês diferente é permitido pela FR-020, mas o verify tem de procurar nos dois meses.

**Verify.** **Variante EducaManto do cenário 19** (título '(EDU) …', responsável configurado no SiteSetting do espelho, evento futuro):
- comissão a pagar = 5% × (venda − BV − cachês) × retido ÷ venda;
- `seller_id` = responsável;
- `payable_from` sai do dia do evento para o ciclo aberto.

**Variante do cenário 20 para EducaManto:** o desconto vai para o repasse do responsável, não do vendedor do evento.

**Cenário 23c:** satélite cancelado não muda nenhuma CommissionPayment (contar linhas e somas antes e depois).

**Ex-satélite com venda 0 e linha paga antiga:** desconto da linha inteira, sem erro de divisão.

**Revisão adversarial: nao.** A regra de reconhecimento do contrato está errada e quebra a C2. 'Linha a_pagar com payable_from IS NOT NULL e sem NOTA_CICLO_VALOR_TARDIO' casa com a linha EducaManto, mas também com TODA linha criada pela reconciliação, que nasce com payable_from preenchido e sem a marca da 299.

No recálculo (FR-015a), a regra geral da C1 entrega a 'falta' à a_pagar mais antiga — que pode ser o ajuste. Ele é 'atualizado no lugar', cai nesta regra e tem payable_from regravado com sale_date mantido. A partir daí sale_date ≠ payable_from numa linha de ajuste: Comissões a mostra num mês e a Planilha em outro. É o defeito que a C2 existe para impedir, e atinge evento comum, não só EducaManto.

O mesmo vale para a própria linha EducaManto na segunda passada: é re-movida e ganha a nota de novo.

A justificativa também tem um erro: 'se o evento for passado, cairia num ciclo já pago' não se aplica a linha reduzida no lugar. Uma linha a_pagar nunca está num ciclo liquidado — o item só é 'pago' se todas forem (routes.py:939-944). O único argumento real é o evento FUTURO: o responsável receberia a comissão do retido só depois de uma data que não vai acontecer.

Isso é comportamento visível (quando o responsável recebe) que a spec não decide: a FR-018 fala do desconto e do ajuste, não da linha a_pagar.

O resto se sustenta: satélite sem reconciliação (spec.md:393-395; coerente com a pendência 2 da PARADA), líder só depois de desagrupar (cancel_ops.py:267-270), venda 0 → alvo 0, beneficiário vindo da linha.

Fora da alçada desta frente: 'não registra devolução' para venda virtual. É consequência de pago = 0, e pertence à frente da devolução.

**Emenda.** 1. Mover o ciclo da linha EducaManto UMA vez, só na chamada do cancelamento, reconhecendo pelo evento (event.is_educamanto com _educamanto_responsavel(settings) — a mesma condição de comissoes_ops.py:828), e só quando original_id IS NULL. No recálculo, nenhuma linha atualizada no lugar muda de data.

2. A nota do ciclo vira constante (NOTA_CICLO_CANCELAMENTO) e serve de guarda de idempotência.

3. Registrar no plano como decisão de plano, comunicada ao dono: 'comissão EducaManto a pagar de evento cancelado entra no primeiro repasse aberto, não espera a data do evento'. Se o dono preferir não mexer, a alternativa é zero código: a linha fica onde está.

4. Cenário novo no verify: depois do +15 do 23a ainda a_pagar, alterar a devolução de novo e exigir sale_date == payable_from no ajuste e o mesmo mês nas duas telas. Com a regra como proposta, tem de falhar.

5. Em cancelar_evento esta frente diz só 'satélite e venda virtual: não congela e não reconcilia'; a devolução fica com a outra frente.

**Evidência da revisão.** app/financeiro/comissoes_ops.py:713-729, 755-773, 828, 841-858; app/financeiro/routes.py:939-944; app/calendar/cancel_ops.py:267-270; app/calendar/group_ops.py:173-183, 204-231; docs/PARADA_REMOCAO_JINJA.md:115-116; specs/303-sync-nao-apaga-venda/spec.md:393-395, 508-510

## C7 — (g) Qual é o mínimo a tocar no Jinja legado de app/financeiro/routes.py?

**Decisão.** Nenhuma view e nenhum template. O único toque no arquivo é no builder compartilhado `_build_commission_items`, que a API e a Planilha Jinja já dividem:
1. cada item ganha a chave aditiva `linhas` (composição por linha), que `pagamentos.html` ignora;
2. a condição de pular o item muda de `total == 0` para 'total zero E nenhuma linha com valor' (C10).

`pagamentos()`, `comissoes()`, `set_commission_status`, `_bulk_set_commission_period` e `comissoes.html` não são tocados. A correção do resync (C4) chega ao Jinja sozinha, porque ele importa as duas funções de `comissoes_ops` (financeiro/routes.py:29-30). A comissão do retido chega ao `event_detail` Jinja pela C5.

**Porquê.** - A PARADA proíbe mover ou apagar funções de lá, e a spec põe fora de escopo o painel antigo 'Estornos pendentes' (spec, Fora de escopo).
- A Planilha Jinja precisa mostrar o mesmo que a nova (FR-019/FR-020 falam das duas telas) e consegue isso só porque o builder é comum. A consulta de BV duplicada nas duas views é da frente do BV.
- As liquidações Jinja já delegam a `liquidar_periodo` (financeiro/routes.py:1132-1134, 1314-1316) e passam a liquidar o ajuste junto com o ciclo, sem mudança.

**Alternativas rejeitadas.** 1. Acrescentar `event_id IS NULL` também no `estornos_q` do `comissoes()` Jinja (:1516-1523): rejeitada. É uma linha só, mas a spec declara o painel fora de escopo, e mexer ali convida a corrigir a dupla contagem de :1532.
2. Mover `_build_commission_items` para `comissoes_ops`: rejeitada (refatoração lateral com import tardio em dois consumidores).

**Contrato.** Item de comissão devolvido por `_build_commission_items` ganha:

```
'linhas': [{'id': int, 'event_id': int | None, 'event_title': str,
            'amount': Decimal, 'status': str, 'tipo': str}]
```

- `tipo` ∈ 'comissao' | 'ajuste_cancelamento' | 'estorno'.
- As demais chaves, o id 'sellerId:YYYY-MM' e a regra de status do item não mudam.

**Pontos de toque.**
- app/financeiro/routes.py:904-961 (_build_commission_items: chave `linhas` e condição de :935-937)
- app/financeiro/routes.py:1006-1089 (pagamentos — não tocar)
- app/financeiro/routes.py:1478-1568 (comissoes e set_commission_status — não tocar; dívida no docs/05)
- app/templates/financeiro/pagamentos.html:171 e app/templates/financeiro/comissoes.html:33-79 (não tocar)
- docs/05 (dívida nova: painel Jinja de estornos mostra o desconto da 303 em todo mês e o 'Marcar processado' o liquida fora do repasse)

**Riscos.**
- A página Jinja de Comissões (só pelo domínio direto do backend) mostra o desconto da 303 no painel de estornos em todos os meses e o soma duas vezes no total. Defeito antigo agravado; vai para o docs/05.
- Item de total zero passa a aparecer também na Planilha Jinja (C10).

**Verify.** Cenário 23/26, na parte 'tela antiga': `GET /financeiro/pagamentos?month=…` direto no backend, com o usuário FINANCEIRO do verify, mostra para o vendedor descartável o mesmo total do item que a API.

Não há assert sobre a página Jinja de Comissões (fora de escopo); o verify só registra que ela responde 200 depois do cancelamento.

**Revisão adversarial: sim.** Não consegui refutar. _build_commission_items é o único ponto comum às duas Planilhas (routes.py:1058; financeiro_read.py:720). A chave nova é aditiva: pagamentos.html só lê campos nomeados (o único tojson é em item.advances, :263) e _serialize_pagamento_item escolhe chave a chave (financeiro_read.py:608-622). As liquidações Jinja já delegam a liquidar_periodo (routes.py:1132-1134, 1314-1316). Nenhuma função é movida nem apagada, como a PARADA exige.

Dois detalhes:

1. 'tipo' seria derivado dentro de routes.py e de novo em _to_entry (C9) — duas cópias da regra original_id/event_id.

2. Na Planilha Jinja o item de total zero da C10 aparece SEM valor: o template só imprime se item.amount for verdadeiro (pagamentos.html:178). Inofensivo, mas o verify não pode esperar 'R$ 0,00' no HTML.

**Emenda.** Um helper único em comissoes_ops (tipo_da_linha(cp) -> str), importado de forma tardia pelo builder — como ele já faz com ciclo_de_pagamento_expr (routes.py:916) — e usado por _to_entry.

No verify da tela antiga, o assert do item zerado é pela presença da linha do vendedor, não pelo texto do valor.

**Evidência da revisão.** app/financeiro/routes.py:904-961, 1054-1058, 1132-1134, 1314-1316; app/api/financeiro_read.py:598-643, 720; app/templates/financeiro/pagamentos.html:120, 178-182, 263

## C8 — (h) Como o verify prova 'Planilha e Comissões batem por evento depois de reabertas'?

**Decisão.** Por identidade de linhas, com vendedor descartável. Para cada evento E cancelado no verify:
1. abrir as duas telas duas vezes (cada GET roda o resync);
2. ler por conexão separada as linhas de E (a_pagar, no_banco, pago) e o ciclo de cada uma;
3. para cada ciclo C tocado, buscar `GET /api/financeiro/comissoes?month=C&seller_id=S` (entries com `event_id == E`) e `GET /api/financeiro/pagamentos?month=C+1` (item `S:C`, campo `commission_lines` com `event_id == E`);
4. exigir: mesmo conjunto de ids, valores e status nas duas; cada linha exatamente uma vez em cada tela ao varrer os meses de [venda − 1, hoje + 2]; Σ = `comissao_retido` da FR-026 = `kpi.commission` do evento = linha Comissões da DRE; Σ dos ajustes (`tipo='ajuste_cancelamento'`) = desconto esperado, no mesmo ciclo nas duas telas.

A comparação exige que a Planilha exponha a composição do item (`commission_lines`, C9) e que Comissões mostre 'no banco' (C9).

**Porquê.** - Hoje a Planilha só tem um item agregado por vendedor e ciclo (financeiro/routes.py:928-961), e Comissões ignora no_banco (comissoes_ops.py:300). Não existe 'por evento' a comparar, e o cenário 21 ficaria sem par.
- Comparar linhas, e não totais, pega três defeitos de uma vez: a linha zerada pelo resync, a duplicada pelo estorno pendente e a posta em ciclos diferentes nas duas telas.
- Vendedor descartável torna o item da Planilha determinístico no espelho, que tem dados reais.

**Alternativas rejeitadas.** 1. Comparar só o total do item do vendedor descartável com a soma das entries: rejeitada. Passa mesmo com duas linhas trocadas de ciclo, e não prova nada em produção, onde o vendedor tem outras vendas.
2. Comparar as telas contra o banco, e não entre si: rejeitada como única prova. O aceite 5 da História 4 é tela × tela; o banco entra como terceiro vértice.

**Contrato.** Helper do verify:

```python
comparar_por_evento(event_id, seller_id) -> list[str]  # lista de divergências
```

Usa só HTTP (login por `POST /api/auth/login` como FINANCEIRO) mais uma conexão separada. Os estados iniciais são montados pelas próprias APIs:
- `POST /api/financeiro/pagamentos/set-status` com `{item_type: 'commission', item_id: 'S:YYYY-MM', status: 'pago' | 'no_banco'}`;
- `POST /api/financeiro/comissoes/pagar-mes` com `{seller_id, month}`.

**Pontos de toque.**
- specs/303-sync-nao-apaga-venda/verify_303.py (cenários 19-23a, 35 e o cruzado)
- app/api/financeiro_read.py:548-595 (GET comissoes — roda o resync em :566)
- app/api/financeiro_read.py:646-747 (GET pagamentos — roda o resync em :670)
- app/api/financeiro_write.py:54-97 e :329-360 (set-status e pagar-mes, usados para montar os estados 'pago' e 'no_banco')

**Riscos.**
- Os GETs do verify rodam `_resync_pending_commissions` sobre TODAS as linhas a_pagar do espelho e commitam (comissoes_ops.py:885-901). O efeito colateral já existe nos verifies 267 e 299 e não é desfeito na limpeza.
- O resultado depende do dia do mês em que o verify roda. Os cenários HTTP precisam de vendedor sem linha em M−1, e a matriz de datas vai na função pura (C2).
- Os eventos do verify precisam de `google_event_id` falso e único, e o Google tem de estar substituído (a spec já exige).

**Verify.** Rodar `comparar_por_evento` depois de cada transição:
- cancelar (19, 20, 21, 22);
- alterar a devolução (23a, 29);
- 'desfazer pago' do ciclo da base;
- pagar o ciclo do ajuste pela Planilha, e depois pelo 'Pagar Mês'.

Prova por mutação obrigatória para três asserts:
- sem a C4, a linha some na segunda abertura;
- sem a C3, o desconto aparece duas vezes em Comissões quando o ciclo não é o corrente;
- com `sale_date` herdado da venda, o mês da venda reabre.

**Revisão adversarial: sim.** Comparar por identidade de linhas é a prova certa: total × total passa com duas linhas trocadas de ciclo. Os endpoints citados existem e montam os estados (financeiro_write.py:54-97, 329-360), e o resync roda nos dois GETs (financeiro_read.py:566, 670).

Três lacunas:

1. 'Σ = linha Comissões da DRE' não é comparável por evento: a DRE é agregada e não lê CommissionPayment. O esperado tem de sair de outra forma.

2. Falta o cenário que pega o defeito da C6: recálculo com ajuste ainda a_pagar.

3. Os ramos dos dias 1 a 5 da C2 não são alcançáveis por HTTP — o cancelamento usa o relógio real. Isso fica só na matriz da função de leitura e precisa estar dito, para o verde de um dia 20 não ser lido como cobertura.

**Emenda.** 1. Na DRE, comparar por delta (mês do cancelamento antes × depois do cancelamento semeado, com vendedor descartável) ou pelo card 'Cancelamentos do período', que é por evento.

2. Acrescentar a transição 'alterar a devolução com ajuste a_pagar existente' e exigir sale_date == payable_from em toda linha com tipo ajuste_cancelamento.

3. Acrescentar a transição da C5: comprovante lançado ou excluído depois do cancelamento (recusado, ou reconciliado — conforme a decisão).

4. Checar o invariante Σ vivas = comissao_retido para todo cancelado com congelamento do espelho.

5. Registrar no quickstart que os ramos dos dias 1 a 5 só têm prova na matriz com hoje injetado.

**Evidência da revisão.** app/api/financeiro_read.py:548-595, 646-747; app/api/financeiro_write.py:54-97, 329-360; app/financeiro/comissoes_ops.py:885-901; specs/303-sync-nao-apaga-venda/spec.md:686-688, 700, 754-756

## C9 — Que campos de payload as duas telas precisam para mostrar (e o verify comparar) comissão e desconto por evento — e a comissão 'no banco' passa a aparecer na tela de Comissões?

**Decisão.** **1. 'No banco' aparece em Comissões.** `_month_scoped_query` e a cópia `month_ids` passam a incluir `no_banco`; `STATUS_LABELS` ganha 'No banco'.
- `pending_amount` continua somando só a_pagar.
- `total_paid` continua só pago.
- `total_month` passa a ser a soma de `total_amount` das linhas por vendedor (hoje é pago + pendente).

**2. `CommissionEntry` ganha campos opcionais:** `tipo`, `original_id`, `evento_cancelado` (consulta única dos eventos cancelados entre os `event_id` do mês, sem N+1) e `ciclo` ('AAAA-MM').

**3. O item de comissão da Planilha ganha `commission_lines`** (de `linhas`, C7), serializado só para `type == 'commission'`.

**4. `sale_count` conta só linhas com `original_id IS NULL`** — desconto não é venda.

**Porquê.** - Sem o item 1, o cenário 21 (base no banco + desconto) mostra Σ = 20 na Planilha e −80 em Comissões, e o aceite 5 da História 4 falha. A Planilha já inclui no_banco (financeiro/routes.py:922).
- Hoje, entre 'no banco' e 'pago', a comissão some da tela de Comissões; o item 1 corrige isso para toda comissão, não só a de cancelado.
- O `pay_seller_month` não muda o que paga, porque filtra `status == 'a_pagar'` depois de coletar os ids (comissoes_ops.py:521-525).
- Os itens 2 e 3 são o que permite à tela rotular 'Desconto — evento cancelado' e ao financeiro entender por que o item do vendedor caiu 80.
- Todos os campos são opcionais no TS, e o bundle em cache os ignora.

**Alternativas rejeitadas.** 1. Deixar no_banco invisível e comparar só a_pagar/pago: rejeitada (a Planilha inclui no_banco; o cenário 21 não fecha).
2. Novo `month_status` 'no_banco': rejeitada por ora. É valor novo de enum, o bundle antigo mostraria 'Pago' de qualquer forma, e o status por linha já diz 'No banco'.
3. Pôr o detalhe do desconto na string `sublabel`: rejeitada como contrato (dinheiro formatado no servidor; o verify precisa de dado estruturado).

**Contrato.** **`GET /api/financeiro/comissoes`** — `entries[]` e `by_seller[].entries[]`:
- `status` pode ser 'no_banco' (`status_label` 'No banco');
- `tipo?: 'comissao' | 'ajuste_cancelamento' | 'estorno'`;
- `original_id?: number | null`;
- `evento_cancelado?: boolean`;
- `ciclo?: string` ('AAAA-MM').
- `kpis.total_month` = soma de tudo que a tela lista.

**`GET /api/financeiro/pagamentos`** — item `type == 'commission'`:
- `commission_lines?: [{id, event_id, event_title, amount, status, tipo}]`.

Nenhum endpoint novo nesta frente. RBAC inalterado: Comissões por `_can_view_vendas`, com escopo do vendedor no servidor (financeiro_read.py:563-571); Planilha só para FINANCEIRO e SUPERADMIN (financeiro_read.py:667).

**Pontos de toque.**
- app/financeiro/comissoes_ops.py:31-35 (STATUS_LABELS + 'no_banco')
- app/financeiro/comissoes_ops.py:46-74 (CommissionEntry: campos novos com default; to_dict)
- app/financeiro/comissoes_ops.py:296-316 e :419-437 (status do recorte mensal)
- app/financeiro/comissoes_ops.py:343-355 (_to_entry), :460 (sale_count), :471-484 (get_month_kpis)
- app/financeiro/comissoes_ops.py:242-243 (comentário 'não unificar sem medir' — atualizar com a medição)
- app/api/financeiro_read.py:598-643 (_serialize_pagamento_item: commission_lines)
- frontend/apps/internal/src/lib/financeiro.ts:194-209 (CommissionStatus + 'no_banco'; campos opcionais)
- frontend/apps/internal/src/lib/pagamentos.ts (tipo do item: commission_lines opcional)
- frontend/apps/internal/src/pages/ComissoesPage.tsx:56-84, 144, 237-245 (rótulo do ajuste, selo 'Evento cancelado', opção 'No banco' no filtro)
- docs/01 (contrato dos dois payloads) e docs/02:1419 (texto 'estornos aparecem em qualquer mês')

**Riscos.**
- A tela de Comissões muda para TODO mês que tenha linha no banco: total por vendedor e KPI do mês sobem pelo valor que hoje fica escondido. Conferir com o dono na tela antes do merge e registrar no docs/03.
- Mês só com linhas no banco mostra o selo 'Pago' no resumo (`month_status` binário).
- `evento_cancelado` exige a consulta em lote; se for feita por linha, repete o N+1 que a 300 corrigiu.
- O CSV exportado (financeiro.ts:309-322) passa a contar menos 'vendas' quando há desconto.

**Verify.** Cenário 21:
- a linha base aparece em Comissões com `status='no_banco'`;
- o desconto aparece com `tipo='ajuste_cancelamento'` e `evento_cancelado=true`;
- `commission_lines` da Planilha traz as mesmas duas linhas.

Regressão em mês do espelho sem cancelamento, main × branch: as entries são as mesmas mais as linhas no_banco; `pending_amount` idêntico; o 'Pagar Mês' altera o mesmo conjunto de ids.

Cenário que DEVE falhar: COMERCIAL pede `seller_id` de outro vendedor e recebe só as próprias linhas (escopo no servidor, já existente).

**Revisão adversarial: parcial.** Incluir no_banco é necessário, não lateral: sem isso o cenário 21 dá Σ = 20 na Planilha (routes.py:922 inclui no_banco) e −80 em Comissões (comissoes_ops.py:300 não inclui). O bundle em cache não quebra: a tela imprime status_label vindo do servidor (ComissoesPage.tsx:78, 285) e month_status continua binário. pay_seller_month não muda o que paga (:521-525).

Quatro problemas:

1. Os três cards deixam de fechar. A tela mostra 'Total do mês', 'Total pago' e 'A pagar' (ComissoesPage.tsx:378-396). Com total_month somando no_banco, e total_paid e total_pending não, o financeiro vê 300 = 100 + 100 sem explicação. Hoje total_month = pago + pendente por construção (comissoes_ops.py:480-484).

2. Touchpoint errado: o tipo PagamentoItem mora em lib/financeiro.ts:344-362. lib/pagamentos.ts só o importa (:3-8) e guarda vocabulário visual. commission_lines opcional entra em financeiro.ts.

3. 'ciclo' calculado em Python vira segunda cópia de ciclo_de_pagamento_expr (coalesce de três degraus, o terceiro em UTC). A PARADA e a 267 existem por causa de cópias dessa expressão.

4. É mudança visível em TODO mês com comissão no banco — totais por vendedor e KPI sobem — e a spec não a decide. A proposta trata como risco 'a conferir na tela'; tem de ser decisão registrada e dita ao dono antes do merge.

sale_count só com original_id IS NULL muda meses históricos com estorno legado (um a menos em 'venda(s)' e no CSV, financeiro.ts:309-317). É correção certa e pequena, mas precisa constar no docs/03.

**Emenda.** 1. kpis ganha total_no_banco opcional e a tela ganha o quarto card, ou o card 'Total pago' passa a dizer 'Pago + no banco' com sublinha. O verify confere total_month == total_paid + total_no_banco + total_pending.

2. Corrigir o touchpoint para lib/financeiro.ts:194 (CommissionStatus), :198-209 (CommissionEntry) e :344-362 (PagamentoItem).

3. 'ciclo' sai de um helper único ao lado de ciclo_de_pagamento_expr (ciclo_de_pagamento_da_linha(cp) -> date, documentado como espelho da expressão) e é usado também por primeiro_repasse_aberto. O verify compara os dois para todas as linhas do espelho.

4. Contar em produção quantas linhas no_banco existem hoje e em quais meses, e levar ao dono como item de conferência. Entrada no docs/03 dizendo que a tela de Comissões passou a mostrar 'No banco'.

5. docs/01: 'no_banco' é valor novo de entries[].status.

**Evidência da revisão.** app/financeiro/comissoes_ops.py:31-35, 299-300, 423, 460, 471-484, 521-525; app/financeiro/routes.py:922; frontend/apps/internal/src/pages/ComissoesPage.tsx:78, 134, 144, 242-245, 285, 378-396; frontend/apps/internal/src/lib/financeiro.ts:194-209, 309-317, 344-362; frontend/apps/internal/src/lib/pagamentos.ts:3-8

## C10 — O que acontece quando o desconto zera exatamente o repasse do vendedor (item da Planilha some; mês fica 'Pago' com linhas a pagar)?

**Decisão.** O item de soma zero com linhas de valor não some mais.
- Em `_build_commission_items`, o `continue` passa a valer só quando o total é zero E nenhuma linha tem valor diferente de zero. O caso das comissões de R$ 0,00 da venda simbólica continua escondido.
- Em `get_month_summary_by_seller`, `month_status` é 'pendente' quando existe linha a_pagar de valor diferente de zero, mesmo com `pending_amount == 0`.

Assim o financeiro vê 'Comissões MM/AAAA — R$ 0,00 — não pago', marca como pago e fecha a comissão e o desconto juntos.

**Porquê.** - Hoje `if total == 0: continue` (financeiro/routes.py:935-937) esconde o item, e `month_status='pago' if pending_amount == 0` (comissoes_ops.py:463) esconde o botão.
- As linhas +100 e −100 ficariam a_pagar para sempre. O ciclo contaria como 'aberto' para todo desconto futuro do vendedor (C2), e a tela diria 'Pago' sobre linhas 'A pagar'.
- A spec já descreve o sintoma ('ou a faz sumir, se zerar') como parte do defeito da 224g.
- Com a devolução total (cenário 22), desconto = comissão inteira, e cair no mesmo ciclo de outra comissão de mesmo valor deixa de ser raro.

**Alternativas rejeitadas.** 1. Deixar como está e registrar dívida: rejeitada. A C2 usa 'tem linha a_pagar' como sinal de repasse aberto; ciclo de soma zero nunca fecharia e atrairia descontos para um item invisível.
2. Mostrar todo item de total zero: rejeitada (traria à Planilha as comissões de R$ 0,00 das vendas simbólicas da 299).

**Contrato.** - `_build_commission_items`: pula o vendedor só se `total == 0 and not any(c.amount for c in lst)`.
- `CommissionMonthSummaryRow.month_status`: 'pendente' se `any(status == 'a_pagar' and amount != 0)`, senão 'pago'.
- Tipos e campos inalterados.

**Pontos de toque.**
- app/financeiro/routes.py:935-937 (condição do continue)
- app/financeiro/comissoes_ops.py:453-463 (month_status)
- frontend/apps/internal/src/pages/ComissoesPage.tsx:134, 155-159 (botão 'Pagar Mês (R$ 0,00)' aparece — só conferir na tela)

**Riscos.**
- Itens de R$ 0,00 aparecem na Planilha (nova e Jinja) onde hoje há soma zero com estorno legado. Contar no espelho quantos ciclos antigos têm soma zero com linha de valor antes do deploy.
- O diálogo do 'Pagar Mês' vai dizer 'Confirmar pagamento de R$ 0,00'. Conferir o texto na tela.

**Verify.** Cenário novo (22b): vendedor descartável com comissão a pagar de 100 de outro evento no ciclo corrente, mais cancelamento com devolução total de um evento com comissão paga de 100.
- A Planilha mostra o item `S:ciclo` com amount 0 e status 'nao_pago'.
- Comissões mostra `month_status='pendente'`.
- Marcar pago na Planilha deixa as duas linhas 'pago' (conexão separada).

Regressão: vendedor só com linha de R$ 0,00 continua sem item.

**Revisão adversarial: sim.** Não consegui refutar. O sintoma está na própria spec ('ou a faz sumir, se zerar', spec.md:212). Sem a mudança, um ciclo de soma zero com linhas +100 e −100 fica a_pagar para sempre e, pela C2, conta como 'aberto' e atrai descontos para um item invisível.

O frontend não precisa de mudança: o botão aparece por month_status === 'pendente' (ComissoesPage.tsx:134, 155-159) e brl(0) devolve 'R$ 0,00' (:35-38). A Planilha React imprime o valor zero normalmente (PagamentoItemViews.tsx:207, 318). pay_seller_month com total zero audita e liquida (comissoes_ops.py:540-549). Os totais da Planilha não mudam (_amt devolve 0).

Único cuidado: na Planilha Jinja o item aparece sem valor (pagamentos.html:178).

**Emenda.** Manter. Usar o mesmo predicado da C2 emendada — linha a_pagar com amount ≠ 0 — nos três lugares (_build_commission_items, month_status, primeiro_repasse_aberto), num helper só.

A contagem pré-deploy (ciclos antigos de soma zero com linha de valor) vira número no plano: cada um reaparece como item 'não pago' de R$ 0,00 no primeiro acesso.

**Evidência da revisão.** app/financeiro/routes.py:934-944; app/financeiro/comissoes_ops.py:453-463, 540-549; frontend/apps/internal/src/pages/ComissoesPage.tsx:35-38, 109, 134, 155-159; frontend/apps/internal/src/components/Pagamentos/PagamentoItemViews.tsx:207, 318; app/templates/financeiro/pagamentos.html:178

## C11 — De onde vêm a comissão cheia e a venda usadas na conta (congelamento), e como a tela mostra o efeito antes de confirmar (FR-015)?

**Decisão.** **Congelamento.** No cancelamento, antes de gravar `cancelled_at`, congelam-se dois valores: a venda (`sale_value` do momento) e a comissão cheia pela regra (`comissao_cheia_do_evento` = `_event_commission` quando `_beneficiario_comissionado` existe, senão 0).

**Conta.** A comissão do retido é função pura: `comissao_do_retido(cheia, retido, venda) = min(cheia, arredonda(cheia × retido ÷ venda))`, e 0 se venda, retido ou cheia ≤ 0. A função da FR-026 (`resumo_do_cancelado`, de outra frente) chama essa conta com os valores congelados e com pago e devolvido lidos na hora.

**Prévia (FR-015).** Reusa a mesma reconciliação com `simular=True`. O servidor devolve retido, comissão resultante, quanto já foi liquidado (pago + no banco), o desconto e em que repasse ele cai. O diálogo não faz conta.

**Porquê.** - A cheia é recalculada a cada chamada, e a aba Comercial e a escala do cancelado continuam editáveis. Sem congelar, editar o evento depois reescreveria comissão, DRE e desconto de um mês passado (a FR-026 proíbe: 'nunca recalculados da venda').
- Cheia pela regra, e não pela soma das linhas, é a letra da FR-016 ('pela regra do seu tipo').
- O diálogo de hoje só enxerga `status === 'pago'` (ExcluirEventoDialog.tsx:31); a comissão no banco fica invisível na prévia, embora a FR-017 a trate como paga.
- Prévia e execução pelo mesmo código impedem que a tela prometa um desconto e o cancelamento gere outro.

**Alternativas rejeitadas.** 1. Não congelar; usar Σ linhas vivas antes do cancelamento como cheia: rejeitada (linha paga desatualizada viraria a regra; contraria a FR-016).
2. Congelar só a taxa: rejeitada (no EducaManto a base depende de BV e cachês, que mudam).
3. Calcular a prévia no frontend com cheia, venda e pago: rejeitada (segunda cópia da regra de dinheiro).
4. Congelar também o beneficiário: rejeitada. Ele sai da linha existente; só falta quando não há linha nenhuma, e aí vale o beneficiário do evento.

**Contrato.** **Colunas** (nomes propostos; se a frente do resumo optar por tabela própria, mudam os nomes, não o contrato), ambas `Numeric(12,2) NULL` em `calendar_events`:
- `cancelled_sale_value`
- `cancelled_commission_full`

`NULL` = cancelado antes da 303 → comissão do retido 0.

**Funções** em `comissoes_ops.py`:

```python
def comissao_cheia_do_evento(event, settings) -> Decimal
def comissao_do_retido(cheia: Decimal, retido: Decimal, venda: Decimal) -> Decimal
```

**Prévia:** `GET /api/events/<id>/impacto-exclusao?devolucao=<decimal>` (RBAC `_can_delete`, inalterado) devolve o bloco opcional:

```
comissao_cancelamento: {
  venda, comissao_cheia, total_recebido, retido, comissao_retido,
  ja_liquidada, a_pagar_atual, ajuste, ciclo ('AAAA-MM' | null),
  repasse_em ('AAAA-MM-05' | null), beneficiario
}
```

- `ajuste` negativo = desconto.
- Sem o parâmetro `devolucao`, o bloco vem para devolução 0.

**Dependência da outra frente:** `resumo_do_cancelado(event)` precisa expor `retido` e `comissao_retido` como Decimal.

**Pontos de toque.**
- app/models.py:283-289 (duas colunas novas ao lado de cancelled_at — a casa final é da frente do resumo/FR-026)
- migrations/versions/ (migration aditiva escrita à mão; down_revision = e5a1c7d93b20, head atual; as colunas desta frente entram na mesma migration da feature)
- app/calendar/cancel_ops.py:236-313 (cancelar_evento: congelar antes de :288; chamar a reconciliação depois de registrar a devolução)
- app/calendar/cancel_ops.py:77-125 (resumo_impacto: bloco de prévia; devolucao_sugerida sai — outra frente)
- app/api/agenda_write.py:484-501 (impacto-exclusao: aceita o valor da devolução para a prévia)
- frontend/apps/internal/src/components/EventDetail/ExcluirEventoDialog.tsx:31, 67-71 (usa o bloco do servidor; textos da FR-025)

**Riscos.**
- Se a frente do resumo guardar o congelamento em outro lugar, os nomes acima mudam. O que não pode mudar: venda e cheia gravadas ANTES de `cancelled_at`, e lidas por todos.
- Arredondamento: HALF_UP em 2 casas sobre cheia × retido ÷ venda. Conferir 90 × 400 ÷ 2000 = 18,00 e um caso com dízima (cheia 33,33, retido 1/3 da venda).
- Cliente que pagou mais que a venda (retido > venda): o teto na cheia segura.

**Verify.** - Cenário 19: 100 → 20,00; com BV de 200, cheia 90 → 18,00; teto com retido = venda → igual à cheia.
- Congelamento: depois de cancelar, mudar venda, taxa e BV na aba Comercial e remover um escalado. `comissao_retido`, as linhas e a DRE não mudam.
- Prévia: `GET impacto-exclusao?devolucao=600` antes de cancelar devolve `comissao_retido` 20, `ja_liquidada` 100, `ajuste` −80 e o mesmo ciclo em que o ajuste nasce depois. Comparar prévia × resultado nos cenários 20 e 21.
- DEVE falhar: COMERCIAL chama a prévia e recebe 403.

**Revisão adversarial: parcial.** Congelar venda e cheia é decisão da spec (Entidades, spec.md:622-625) e a conta bate (90 × 400 ÷ 2000 = 18,00; teto na cheia). e5a1c7d93b20 é o head: nenhuma migration o cita como down_revision. A prévia pelo mesmo código da execução é o desenho certo. O endpoint já é só Superadmin (agenda_write.py:496), então o 403 do COMERCIAL é comportamento existente, não prova nova.

Lacunas de contrato:

1. O parâmetro devolucao não tem validação definida: valor inválido, negativo ou maior que o pago. A spec manda recusar devolução maior que o recebido (spec.md:418); a prévia precisa do mesmo erro, no envelope json_error.

2. A prévia trava linhas (C1, item 3).

3. O diálogo busca o impacto uma vez, ao abrir (eventOps.ts:111-114, queryKey sem o valor). Com ?devolucao= vira uma request por valor digitado, sem debounce definido. Request por tecla em horário de equipe é o padrão de sangria já conhecido neste projeto.

4. Dependência cruzada não fechada: o bundle em cache lê impacto.data.devolucao_sugerida e pré-preenche o campo (ExcluirEventoDialog.tsx:105-110). Manter a chave = bundle antigo manda 'Tudo' calado, contra a Clarification. Tirar a chave só é seguro se o servidor passar a recusar cancelamento sem a escolha explícita. Pertence à outra frente, mas esta proposta lista a remoção como touchpoint sem a condição.

5. comissao_cheia_do_evento lê a regra no instante do cancelamento. Se a aba Comercial foi gravada na mesma transação ou há escala sem flush, a base EducaManto sai do cache — a armadilha documentada em event_ops.py:952-955.

**Emenda.** 1. Contrato da prévia: devolucao ausente = 0; não numérico, negativo ou maior que total_recebido → 400 json_error com fields={'devolucao': …}. Parse por Decimal, nunca float.

2. queryKey inclui o valor. A tela só pede a prévia ao escolher Tudo ou Nada, ou no blur/debounce (≥ 400 ms) de 'Parte'.

3. with_for_update só fora da simulação.

4. Anotar no plano a condição casada com a frente da devolução: devolucao_sugerida só sai do payload no mesmo deploy em que o POST /cancelar passa a exigir a escolha.

5. db.session.flush() antes de congelar a cheia, com o comentário do porquê.

6. Cada coluna com docstring dizendo NULL ≠ 0: NULL = cancelado antes da 303.

**Evidência da revisão.** app/api/agenda_write.py:484-501, 541-566; app/calendar/cancel_ops.py:77-125; frontend/apps/internal/src/lib/eventOps.ts:111-114; frontend/apps/internal/src/components/EventDetail/ExcluirEventoDialog.tsx:31, 105-110; app/calendar/event_ops.py:952-955; migrations/versions/e5a1c7d93b20_formulario_destino.py:30; specs/303-sync-nao-apaga-venda/spec.md:418, 622-625

## C12 — O caminho de exclusão (`_delete_event`) e os estornos antigos já pendentes entram na regra nova?

**Decisão.** Não entram no código. `aplicar_estorno_comissao` fica como está para `_delete_event` (só a docstring é corrigida): a linha perde o `event_id` porque o evento é apagado, e o estorno órfão segue a regra antiga (ciclo da venda, resgatado no mês corrente pela C3).

Para os estornos órfãos já pendentes em produção, a feature entrega um script avulso em `scripts/oneoff/`, em modo de leitura por padrão. Ele lista cada estorno pendente (vendedor, valor, ciclo atual) e, com `--execute`, reposiciona `sale_date` e `payable_from` para o primeiro repasse aberto. O dono roda no Shell do Render depois do deploy.

Antes do deploy, o plan conta em produção (só leitura): `status='a_pagar' AND amount<0`.

**Porquê.** - Depois da FR-001 o sync não apaga mais evento com venda, e o DELETE da 224 recusa evento com venda, pagamento, contrato ou escalado (agenda_write.py:522-527). O estorno órfão novo só nasce ao excluir evento de venda zerada com comissão paga antiga — raro.
- Estender a regra nova a ele exigiria um discriminador em coluna (o `event_id` some com o evento).
- O estorno do 1244 (−comissão com `sale_date` 21/08) está hoje reabrindo a Planilha de setembro. Reposicioná-lo é correção de dado de dinheiro real, e o padrão da casa é script com dry-run rodado pelo dono (precedentes: backfill 267b, reclassificar 239b).

**Alternativas rejeitadas.** 1. Reposicionar os estornos legados dentro da migration: rejeitada (migration é aditiva e de schema; mexer em linha de comissão no `startCommand` é risco de produção).
2. Aplicar a C2 também no caminho de exclusão: rejeitada por ora. O órfão posto em ciclo diferente do corrente voltaria a aparecer em dois meses pela via dos pendentes, e resolver isso pede coluna nova.

**Contrato.** ```
python scripts/oneoff/303_reposicionar_estornos_legados.py [--execute]
```

- Roda com `MANTO_SEM_THREADS=1`.
- Alvo: linhas `status='a_pagar' AND amount<0 AND event_id IS NULL`.
- Sem `--execute`: só imprime id, vendedor, valor, ciclo atual e ciclo proposto.
- Com `--execute`: grava `sale_date = payable_from = primeiro_repasse_aberto(seller_id, hoje)` e acrescenta a nota 'Reposicionado pela 303'.
- Auditoria via `audit()`.

**Pontos de toque.**
- app/calendar/cancel_ops.py:128-155 (docstring; comportamento intacto)
- app/calendar/routes.py:305-338 (_delete_event — não tocar)
- scripts/oneoff/303_reposicionar_estornos_legados.py (novo; dry-run por padrão; usa primeiro_repasse_aberto)
- docs/05 (dívida: estorno de exclusão segue no ciclo da venda)

**Riscos.**
- Se algum estorno pendente já foi abatido à mão pelo financeiro fora do sistema, reposicioná-lo desconta duas vezes. Por isso é dry-run e decisão do dono (pergunta em aberto).
- Enquanto não rodar, os estornos legados continuam reabrindo a Planilha do ciclo antigo. É o comportamento de hoje, não regressão.

**Verify.** - `_delete_event` de evento vazio com comissão paga (semeado): nasce estorno órfão com `event_id NULL`, como hoje — regressão da 224.
- O script em dry-run no espelho não altera nada (contagem e checksum de `commission_payments` antes e depois).
- Com `--execute` num estorno semeado, ele sai do ciclo antigo e o item antigo da Planilha volta a 'pago'.

**Revisão adversarial: nao.** Três problemas, o primeiro impeditivo:

1. scripts/oneoff/ é gitignorado (.gitignore:41). Um script ali nunca chega ao Render, e 'o dono roda no Shell do Render depois do deploy' é impossível. Os dois precedentes citados moram em specs/, versionados: specs/267b-hotfix-data-da-venda/backfill_data_da_venda.py e specs/239b-hotfix-carrinho-fora-de-sp/reclassificar_fora_de_sp.py.

2. Reposicionar não resolve o que promete na tela de Comissões. O órfão continua com event_id NULL, então continua entrando pelo resgate do mês corrente (_estornos_do_mes) e sendo liquidado pelo 'Pagar Mês' de qualquer mês (comissoes_ops.py:517-518). Com sale_date novo em C, ele aparece em C pela via normal e de novo no mês corrente sempre que C ≠ mês corrente — o defeito descrito na História 4. O script conserta só a Planilha.

3. Nenhum FR pede mexer em linha de comissão legada. É escrita em dinheiro real fora do escopo declarado, e depende de uma resposta que só o dono tem: se já foi abatido à mão, reposicionar desconta duas vezes.

Manter aplicar_estorno_comissao para _delete_event se sustenta. Mas o caminho segue sem ramo para no_banco (cancel_ops.py:140-155): a linha fica viva, o SQLAlchemy anula o event_id ao apagar o evento, e ela é paga cheia — o mesmo defeito que a História 4 aponta no cancelamento, preservado na exclusão.

**Emenda.** 1. A 303 entrega só a contagem e a listagem, em modo leitura, em specs/303-sync-nao-apaga-venda/listar_estornos_orfaos.py (versionado, sem --execute): id, vendedor, valor, ciclo atual, original_id. O plano leva o número ao dono junto da pergunta aberta.

2. A correção de dado vira Nível 2 (303b ou hotfix), depois da resposta do dono, com o verbo certo para cada resposta: 'marcar liquidado' se já foi abatido, 'reposicionar' se não.

3. Se o dono quiser reposicionar já, o script mora em specs/303-…/ e o plano registra que Comissões seguirá mostrando o órfão no mês corrente até a liquidação.

4. docs/05 ganha duas dívidas: estorno de exclusão segue no ciclo da venda; exclusão não trata comissão no_banco.

5. api_delete_event recusa evento cancelado (emenda 6 da C1).

**Evidência da revisão.** .gitignore:41 (/scripts/oneoff/); git ls-files: specs/267b-hotfix-data-da-venda/backfill_data_da_venda.py, specs/239b-hotfix-carrinho-fora-de-sp/reclassificar_fora_de_sp.py; app/financeiro/comissoes_ops.py:358-372, 516-518; app/calendar/cancel_ops.py:139-155; app/calendar/routes.py:305-338; app/api/agenda_write.py:504-538

## O que a frente deixou de decidir (revisão)

- Quem dispara a reconciliação quando o PAGO muda depois do cancelamento. Adicionar, corrigir e excluir comprovante não checam cancelamento (app/api/agenda_write.py:1540-1613; app/calendar/routes.py:1097-1134). O retido é lido na hora pela função da FR-026, e as linhas só mudam quando a reconciliação roda. A frente precisa decidir: travar comprovante de evento cancelado (recomendado) ou reconciliar nos três endpoints. Sem isso a FR-020 quebra sem erro.
- Lista fechada dos chamadores da reconciliação. A proposta diz que ela 'serve ao cancelamento e ao recálculo', mas não enumera. O plano precisa da lista: cancelar_evento, o endpoint de alterar a devolução (FR-015a, inclusive o complemento de devolução já paga) e, se não travar, os comprovantes. Também precisa dizer que nenhum outro caminho altera devolução de cancelado (a trava de Gastos Extras é de outra frente).
- O link 'ver em comissões' da tela do evento aponta para o mês da VENDA e o vendedor do EVENTO (ComercialSection.tsx:92-94). O ajuste mora em outro mês e, no EducaManto, em outro beneficiário. Falta o contrato entre frentes: o resumo do cancelado expõe ciclo e beneficiário de cada linha viva, e o bloco 'Resultado do cancelamento' linka para lá.
- Rastro das escritas da reconciliação (FR-023): audit() por linha reescrita ou criada, EventLog no evento e nota sem duplicar a cada recálculo. Hoje toda liquidação audita e a proposta só prevê texto em notes.
- Exclusão de evento cancelado. DELETE /api/events/<id> não checa is_cancelled (agenda_write.py:504-538) e pode_excluir passa para cancelado de venda 0 sem comprovante (ex-satélite com comissão paga). _delete_event cancelaria o ajuste pendente e recriaria um estorno órfão no ciclo antigo. A tela não oferece o botão (EventHeader.tsx:306), mas a API aceita. Guarda de uma linha.
- Predicado único de 'linha que abre ciclo' (a_pagar com valor ≠ 0 e que não seja estorno órfão), compartilhado por primeiro_repasse_aberto (C2), month_status e o continue do builder (C10). A proposta usa três definições ligeiramente diferentes.
- Defeito pré-existente de exibição de data em ComissoesPage.tsx:40-43: new Date('AAAA-MM-DD') é lido como UTC e exibido um dia antes em Brasília. Com as datas de borda de mês que a C2 cria (dia 1º do ciclo), a linha aparece num mês com data do mês anterior. Decidir se a 303 corrige (uma função) ou registra no docs/05. Afirmação pela semântica do Date; não rodei a tela.
- Contagens pré-deploy que faltam, todas só leitura: (a) linhas a_pagar negativas COM event_id (esperado 0, senão a C3 as esconde do mês corrente); (b) linhas no_banco por mês e vendedor, para dimensionar a mudança da C9; (c) eventos já cancelados sem congelamento (a spec registra zero uso do cancelamento da 224, spec.md:40 — confirmar); (d) eventos cancelados com CommissionPayment ainda ligada.
- Os eventos 69, 62 e 203 têm venda e nenhuma linha, e estão listados como 'decisão do dono, nada foi tocado' (docs/PARADA_REMOCAO_JINJA.md:112-114). Pela C1, cancelar um deles com retido > 0 CRIA a linha de comissão. É a letra da FR-016, mas o plano deve dizer explicitamente que o cancelamento passa a resolver essa pendência para o evento cancelado.
- Comportamento quando o beneficiário não tem repasse futuro (usuário desativado ou sem vendas). O desconto vira item negativo isolado e o único gesto disponível na Planilha é 'marcar pago' — que liquida sem ter descontado de nada, o defeito que a História 4 descreve. A spec aceita o item negativo (spec.md:408-409), mas o plano deve registrar no docs/05 que não há prova de abatimento, junto da D20.

## Perguntas em aberto da frente

- Os estornos de comissão que já estão pendentes em produção (o do evento 1244, de 17/09, e qualquer outro a pagar com valor negativo) já foram descontados à mão de algum repasse? Se sim, o script da C12 deve marcá-los como liquidados em vez de reposicioná-los; se não, reposiciona para o primeiro repasse aberto. Só o dono ou o financeiro sabe. O plan conta quantos são antes de perguntar.