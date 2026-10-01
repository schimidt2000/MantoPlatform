# Revisão dos três mapas: o que se sustenta, o que é falso e o que ficou sem evidência

O exemplo e o "−600" se sustentam no código. Achei três afirmações falsas e três imprecisas. Duas premissas do exemplo (a taxa de 5% e o imposto de 16%) dependem de configuração e não dá para confirmar sem o banco.

## 1. O que se sustenta (conferido no código)

### Regime e as duas DREs
- **A DRE é por competência, pela data do evento.** Ela filtra por `start_at` no período. A receita é `sale_value`, não o que foi recebido (routes.py:218). O mesmo filtro está na API (financeiro_read.py:228-229) e no Jinja (routes.py:277-278).
- **O `EventPayment` não entra na DRE, nem em nenhum relatório de caixa por data.**
  - Ele só alimenta o "a receber" (financeiro_read.py:306-318).
  - Os únicos usos de `EventPayment.created_at` são ordenações (agenda_read.py:903; calendar/routes.py:1663).
- **Como cada linha de custo entra:**
  - Gastos extras entram pela `expense_date`, com `status == "aprovado"`, sem olhar categoria nem evento (financeiro_read.py:243-250; routes.py:294-301).
  - Recorrentes entram pelo `month_ref` (financeiro_read.py:253-260).
  - Pessoal é o `SalaryPayment` do mês ou o pro-rata (routes.py:181-202).
- **Realizado × Projetado se separa por `start_at < agora`** (financeiro_read.py:239-240). O Projetado recebe 0 de custo fixo (financeiro_read.py:263; routes.py:318).
- **O evento cancelado sai inteiro da cascata** (financeiro_read.py:233; routes.py:282). Nas duas DREs o tratamento do cancelado é idêntico.
- **A API copia o corpo do Jinja em vez de reusá-lo.**
  - A docstring de financeiro_read.py:188-189 está errada duas vezes: diz "sem duplicar" e cita `:387`, mas o `def dashboard()` está em routes.py:263.
  - docs/04:237 cita `routes.py:351`, mas `_compute_drg` está em :205.
- **O Jinja está registrado** (app/__init__.py:831) e o `server.js` não repassa `/financeiro` (server.js:253-264, 298-302).
- **A nota de rodapé do Jinja omite os recorrentes** (dashboard.html:201), embora a cascata os desconte (dashboard.html:183-188). O React os menciona (FinanceiroDashboardPage.tsx:412).

### Origem do −600
- **A devolução nasce já como gasto da DRE.** `_registrar_devolucao` cria um `SpecialExpense` com:
  - `status="aprovado"`, `expense_date` igual ao dia do cancelamento e `event_id` preenchido;
  - `disbursement_type="cliente"` e categoria "Devolução a cliente" (cancel_ops.py:174-189; models.py:1021).
- **Na DRE de setembro:** Gastos Extras +600 e Resultado Líquido −600, no Realizado e no Total.
- **A diferença de 942** (342 − (−600)) está com a aritmética certa, mas o 342 é uma projeção que depende das decisões do dono.

### Números de novembro antes do cancelamento
Com cachês = C, pela fórmula de `_compute_drg` (routes.py:218-237):

| Linha | Sem nota | Com nota (16%) |
|---|---|---|
| Receita | 2.000 | 2.000 |
| Impostos | 0 | 320 |
| CPV (cachês + BV) | C + 200 | C + 200 |
| Lucro bruto | 1.800 − C | 1.480 − C |
| Comissão | 90 | 90 |
| Contribuição (Projetado) | 1.710 − C | 1.390 − C |

Depois do cancelamento, isso tudo some de novembro e não vai para outro mês.

### Comissão na DRE
- **A DRE nunca lê `CommissionPayment`.** A linha Comissões é a fórmula `_event_commission` (routes.py:231; comissoes_ops.py:656-686).
- **No cancelamento** (cancel_ops.py:139-155):
  - comissão `a_pagar` vira `cancelado`, com `event_id` nulo;
  - comissão `pago` gera um estorno de −valor pago, `a_pagar`, com `event_id` nulo e o `sale_date` da venda original;
  - comissão `no_banco` não é tocada (não há ramo para ela).

### CPV, Tendência e KPIs
- **O BV é custo** (routes.py:226-227) e o BV do cancelado some.
- **O rótulo do CPV** omite o BV (FinanceiroDashboardPage.tsx:43; dashboard.html:137).
- **O card "Pago — Talentos" também perde o cachê do cancelado**, porque sai da mesma consulta filtrada (financeiro_read.py:324-333).
- **A Tendência não filtra o cancelado** (financeiro_read.py:369-373; routes.py:399-403).
  - A janela de 6 meses começa em hoje (financeiro_read.py:366-368): hoje vai de abr a set.
  - A linha 11/26 mostraria +2.000 de receita, +C de custo, lucro 2.000 − C e +1 evento.
  - Setembro não mostra nem o −600 nem o +400, porque a Tendência ignora gastos.
- **Ticket médio, "a receber", receita por tipo e Top Vendedores** saem de `eventos_com_venda`, que já exclui o cancelado.
- **Break-even e Fator R** usam `pessoal + comissões` e `receita_bruta`, sem gastos extras (financeiro_read.py:298-304). Em novembro, a receita cai 2.000 e o Fator R sobe; em setembro o −600 não afeta os dois.
- **Divergências entre Jinja e API** fora do cancelado:
  - ticket médio: o Jinja inclui a Loja Virtual (routes.py:323-330); a API a exclui (financeiro_read.py:280-295);
  - "a receber": o Jinja inclui a loja; a API não.

### Pendências
- **Recebimentos Previstos e Notas não filtram o cancelado:**
  - parcelas: financeiro_read.py:425-435; routes.py:466-476;
  - notas a emitir, sem filtro de período: financeiro_read.py:449-455;
  - custo das notas emitidas, pela data de emissão: financeiro_read.py:468-477.
- **`cancelar_evento` não toca parcelas, notas, elenco nem comprovantes** (cancel_ops.py:236-313).

### Outras superfícies
- **Dashboard Comercial:** exclui o cancelado (vendas_ops.py:169), com eixo `closing_date` = `sale_date` ou `start_at` (vendas_ops.py:69-78). Some de forma retroativa. Se o cancelado fosse reincluído, a linha mostraria comissão cheia (vendas_ops.py:339) e status "parcial" (vendas_ops.py:62-65).
- **Home, Cobranças e Sem valor:** o principal cancelado fica fora (cobranca_ops.py:420). O satélite cancelado continua somando no recebido do grupo (cobranca_ops.py:217-221, 425-428).
- **Home, Performance:** conta o cancelado; `perf_filter` não tem `cancelled_at` (dashboard_service.py:291-293, 312-321).
- **Ficha do cliente:** mostra "total vendido R$ 2.000" e o evento conta para a recorrência (client_ops.py:158, 117-121, 216-223).
- **/admin/desempenho:** conta o cancelado com o valor cheio, por `start_at`, sem tirar satélite, ensaio ou permuta (admin_config_read.py:150-157).
- **/vendas/ no Jinja:** lista o cancelado com a comissão cheia (routes.py:1445-1454).
- **Marketing:** exclui o cancelado (desempenho_ops.py:257).
- **Detalhe do evento, grade Resultado:**
  - lucro = 2.000 − C − 600 − 200 = **1.200 − C** (agenda_read.py:374-400), em verde se C < 1.200 (ComercialSection.tsx:133-137);
  - comissão 0 com origem "linha" (comissoes_ops.py:285-286).
- **Detalhe do evento, chip de pendência:** "R$ 1.000,00 em aberto", porque `outstanding = max(saldo, 0)` ignora o `motivo_fora` (agenda_read.py:431, 1008-1009; cobranca_ops.py:137-139; ResumoSection.tsx:393-399).
- **/events/cancelamentos:** mostra "Venda 2.000 · Devolução 600 a devolver".
  - A devolução vem com `.first()` e exige `disbursement_type="cliente"` (cancel_ops.py:339-350).
  - `no_banco` cai em "a devolver" (EventosCancelamentosPage.tsx:29-32, 146-148).
- **Planilha de Pagamentos:**
  - devolução de 600 em setembro (financeiro_read.py:691-702);
  - BV de 200 em novembro, sem filtro de cancelado (financeiro_read.py:706-714);
  - cachês do cancelado fora (routes.py:701).
- **Tela de Comissões:**
  - `no_banco` não aparece (comissoes_ops.py:300) e a Planilha a inclui (routes.py:922);
  - `sale_count = len(entries)` conta o estorno como venda (comissoes_ops.py:460);
  - o recorte `?evento=` compara `event_id` e não acha a comissão do cancelado, porque o `event_id` foi anulado (ComissoesPage.tsx:221).
- **Armadilha do resync:** `_resync_pending_commissions` roda em todo GET de Comissões e da Planilha. Ele pega as linhas `a_pagar` com `event_id` e valor ≥ 0, e cancela a do evento cancelado (comissoes_ops.py:816-839, 885-900). Se a 303 mantiver o `event_id` na linha de 18, ela é zerada na primeira abertura da tela.
- **Agenda:** Mês e Lista escondem o cancelado (calendar/routes.py:200). O Dia (agenda.py:85-90) e a busca (event_ops.py:1537-1552) o mostram sem marca.
- **Não existe cálculo de "retido" em lugar nenhum.** O grep por "retid" só acha homônimos (models.py:3117; virtuais_ops.py).

## 2. Falso ou impreciso (com o certo)

**F1 (leitor 2, Comissões): "o estorno … só aparece no mês corrente (comissoes_ops.py:358-372)". Falso.**
- O estorno é `a_pagar` com o `sale_date` da venda, então `_month_scoped_query` também o traz no mês da venda (comissoes_ops.py:299-311, e `_sem_loja_virtual` deixa passar `event_id` nulo em :175-176). A docstring em :366-368 diz o mesmo.
- O certo, no caso "paga": o mês da venda mostra +90 "Pago" **e** −90 "A pagar" (saldo 0, com o KPI "A pagar" em −90). O mês corrente mostra −90 de novo.
- Só aparece apenas no mês corrente quando `sale_date` é nulo (o recorte cai no `created_at`).
- **A spec 303:194 repete o mesmo erro** ("só aparece no mês corrente").

**F2 (leitor 2, Tendência): "No mês do evento… Na mesma tela, o DRE mostra R$ 0 de receita e R$ 600 de gasto". Falso para o exemplo.**
- O −600 cai no mês do cancelamento (setembro, pela `expense_date`). O +2.000 cai no mês do evento (novembro).
- A Tendência é ancorada em hoje (financeiro_read.py:366); a cascata segue o período escolhido. Os dois só se encontram quando evento e cancelamento são no mesmo mês, ou num período personalizado.
- No exemplo, a linha 11/26 só existe na tela a partir de nov/26. O leitor 3 descreve certo: "−600 no mês da devolução, +2.000 no mês do evento".

**F3 (leitores 1 e 2, Recebimentos Previstos): "parcela ainda não recebida" / "sinal de R$ 1.000 (marcado recebido)". Premissa impossível no código atual.**
- Nada grava `EventInstallment.received = True`:
  - a coluna nasce falsa (models.py:725);
  - `substituir_parcelas` apaga e recria as parcelas sem esse campo (comercial_ops.py:237-243);
  - o grep não acha nenhum outro escritor.
- O certo: **todas** as parcelas do cancelado continuam em Recebimentos Previstos, cada uma no mês do vencimento, inclusive o sinal já pago. Com sinal e saldo, isso dá até R$ 2.000, não 1.000.
- Dado histórico no banco com `received = True` fica sem evidência.

**F4 (leitores 1 e 2): "o único lugar que lista cancelados é /events/cancelamentos" / "única porta" (docs/02:1710). Falso.**
- A visão Dia (agenda.py:85-90) e a busca (event_ops.py:1537-1552), com os seletores de ensaio, NFC e grupo que a reusam, devolvem o cancelado sem marca.
- /events/cancelamentos é a única lista com dado de devolução.

**F5 (leitor 2, Planilha): "estorno de −R$ 90 no mês seguinte ao da venda". Impreciso.**
- O mês está certo: o ciclo é o `sale_date` e a Planilha do mês M mostra o ciclo M−1 (financeiro_read.py:717-720).
- Mas o estorno não é uma linha própria. Ele entra na soma da linha agregada do vendedor (routes.py:928-935).
  - Essa linha reabre como "nao_pago" (routes.py:939-944).
  - Ela some quando o total zera (routes.py:936-937).
- A spec 303:191-193 descreve isso corretamente.

**F6 (leitor 1): acrescentar o status "cancelado" em `event_payment_status`, "fonte única das duas telas". Impreciso para o Jinja.**
- A DRE Jinja calcula o status inline (routes.py:437-446) e não chama `vendas_ops.event_payment_status`.
- As "duas telas" da docstring são a API financeira e o Dashboard Comercial. O status novo não chega ao Jinja sem mexer ali também.

**F7 (leitor 2): reusar o painel Jinja "Estornos pendentes" como modelo. Com ressalva.**
- A consulta dele não tem filtro de mês (routes.py:1516-1523): o estorno aparece em **todo** mês.
- No mês da venda, `total_a_pagar` desconta o estorno duas vezes, porque ele está em `entries` e em `estornos` (routes.py:1496-1532): −180, não −90.
- O texto "descontadas do próximo ciclo" (comissoes.html:39) contradiz a Planilha, que usa o ciclo da venda.

**Nuance de regime que nenhum leitor citou: o mês do −600 é o mês do cancelamento só na criação.**
- A `expense_date` pode ser editada em Gastos Extras sem trava (gastos_ops.py:407-428). Editar a data move o −600 de mês.
- Qualquer "Salvar" troca `disbursement_type="cliente"` por `None` (gastos_ops.py:237-238), enquanto o status continua "aprovado" (gastos_ops.py:430-436). A devolução então:
  - sai da Planilha (financeiro_read.py:695);
  - sai de /events/cancelamentos (cancel_ops.py:341);
  - **continua como −600 na DRE**.
- Para o plano: tirar a devolução de Gastos Extras filtrando por `category == CATEGORY_DEVOLUCAO` e `event_id` (proposta do leitor 1) resiste a esse "Salvar". Filtrar por `disbursement_type` não resiste. Mas a categoria também é editável.

**Detalhe menor (leitor 3, grade Resultado):** a dica "venda − cachês − gastos" (ComercialSection.tsx:136) não diz que o BV também é descontado (agenda_read.py:400). Os 1.200 − C incluem −200 de BV.

## 3. Sem evidência (premissas ou fora do que li)

- **Comissão de 90 (5% × 1.800):** a taxa vem de `event.commission_rate`, depois de `SiteSetting.default_commission_rate`, e o padrão do código é **2,5%** (comissoes_ops.py:576, 590-596). Na taxa padrão a comissão cheia seria 45 e a do retido, 9. Os 5% são premissa da spec (spec.md:183-186); não dá para confirmar sem o banco.
- **Imposto de 16%:** é o padrão do código (routes.py:112, 129-132), mas `SiteSetting.tax_rate` pode trocá-lo, e só vale com `with_invoice`.
- **O −600 como número de produção:** a spec registra zero uso do Cancelar da 224 (spec.md:40), e o −600 é o exemplo da própria spec (spec.md:544-547). Não consultei o banco.
- **Os +342, 278 e 942:** são projeções que dependem das decisões do dono (mês do retido, imposto sobre o retido, BV negociado de 40). As contas estão certas.
- **Não conferi** o rodapé de Cobranças e Sem valor, o sync ignorando cancelado (calendar/routes.py:2226-2227), o total da página Gastos Extras (gastos_ops.py:122-133), a disponibilidade do casting (event_ops.py:1281-1290) nem `search_events_by_date` (gastos_ops.py:136-150). Nenhum deles é número do exemplo nem regime.