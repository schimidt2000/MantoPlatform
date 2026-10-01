# Frente comercial

Relatórios comerciais — o retido conta como venda no mês do cancelamento (FR-032; FR-034/035/036 nas superfícies comerciais: Dashboard Comercial, Top Vendedores, /admin/desempenho, Performance da Home, fichas de cliente e talento, Jinja /vendas/)

Tamanho: M — sem migration e sem endpoint novo. Backend: 8 arquivos (app/financeiro/vendas_ops.py, app/api/financeiro_read.py, app/api/admin_config_read.py, app/api/dashboard_service.py, app/clientes/client_ops.py, app/api/clientes_read.py, app/talents/talent_ops.py e 1 linha em app/financeiro/routes.py). Frontend: 4 telas (VendasPipelinePage, AdminDesempenhoPage, ClientDetailPage, TalentDetailPage), 4 arquivos de tipos em lib/ e 1 componente de selo. Depende da função única da FR-026 (outra frente) e da migration que congela venda/comissão/BV/imposto. Se o plano dividir em 303b: RC-01, RC-02, RC-03, RC-07, RC-08 e a parte de soma de RC-09/RC-10 (FR-032, números) ficam na 303; RC-04, RC-05, RC-06, RC-11 e RC-12 (card, botão, status, selo — FR-034/035/036) podem ir para a 303b. Nesse caso o subtítulo do KPI "inclui R$ X retidos" (RC-03) tem de ficar na 303, senão o total sobe sem explicação.

## RC-01 — Como o cancelado entra com o retido no mês do cancelamento e sai do mês original, no núcleo comercial?

**Decisão.** O filtro que tira o cancelado de `list_closed_sales` fica como está (é ele que faz a venda original sair do mês dela). Entra uma função irmã, `list_cancelled_sales`, no mesmo módulo, com a mesma régua de venda e o eixo trocado para `cancelled_at`. Cada cancelado conta em um período só: o do cancelamento.

**Porquê.** A venda original já sai do mês dela hoje: `CalendarEvent.cancelled_at.is_(None)` em app/financeiro/vendas_ops.py:169, com eixo `closing_date` = `sale_date` ou `start_at` (:69-78, :175-186). Falta só a entrada pelo mês do cancelamento. `cancelled_at` é gravado como horário de parede de São Paulo, sem fuso (app/calendar/cancel_ops.py:272, :288), então comparar com `datetime.combine(start_date, min)` / `(end_date, max)` — a mesma conta de vendas_ops.py:165-166 — dá o mês certo sem conversão. Satélite e venda virtual cancelados não geram retido (FR-029), por isso ficam fora da consulta.

**Alternativas rejeitadas.** (a) Remover o filtro de :169 e trocar o eixo dentro de `list_closed_sales` com um `case` SQL: rejeitado, porque a função tem um único chamador que soma `sale_value` cheio em `build_kpis` (:269) e serializa comissão cheia (:339) — o cancelado entraria com R$ 2.000 e R$ 90 em qualquer ponto esquecido. (b) Manter o cancelado também no mês original, com valor zero: rejeitado, porque a lista deixaria de somar o KPI e o mesmo evento apareceria em dois períodos, contra a promessa de `closing_date` (:72-74).

**Contrato.** Em app/financeiro/vendas_ops.py:

`def list_cancelled_sales(start_date: date, end_date: date, *, seller_id: int | None = None, educamanto_only: bool = False) -> list[CalendarEvent]`
Filtros: `event_type != 'ENSAIO'`; `event_type != EVENT_TYPE_VIRTUAL`; `group_leader_id IS NULL`; `cancelled_at >= start_dt AND cancelled_at <= end_dt`; `seller_id` e prefixo EducaManto iguais aos de `list_closed_sales` (:188-191). Ordena por `cancelled_at desc`. Não filtra por `sale_value` no SQL: quem decide se 'foi venda' é o chamador, com o resumo em mãos (venda congelada > 0, ou permuta, ou pago > 0).

`def data_de_competencia(event: CalendarEvent) -> date | None` — `cancelled_at.date()` para cancelado; `closing_date(event)` para os demais. Usada para ordenar a lista mesclada.

**Pontos de toque.**
- app/financeiro/vendas_ops.py:134-194 (list_closed_sales; filtro :169 fica; item 4 da docstring :154-157 é reescrito — hoje diz que a devolução 'aparece do outro lado', o que esta tela nunca mostrou; está na lista da FR-025)
- app/financeiro/vendas_ops.py:69-78 (closing_date — ganha a irmã data_de_competencia)
- app/calendar/cancel_ops.py:272,288 (cancelled_at = horário de São Paulo sem fuso)
- app/financeiro/routes.py:155-178 (_resolve_period: já aceita period=custom&start=&end=, que o verify usa para pedir o mês do evento)

**Riscos.**
- A aba Comercial do cancelado continua editável (spec, Entidades): trocar o vendedor depois do cancelamento move o retido de um vendedor para outro. Só fecha se a frente da FR-016 congelar também o beneficiário.
- Evento cancelado antes da 303 não tem valores congelados; o retido ainda é derivável (pago − devolvido). A spec registra zero cancelamentos em produção em 29/09 — recontar antes do deploy.

**Verify.** Cenário 40. Pedir `GET /api/vendas/pipeline?period=custom&start=&end=` para o mês do cancelamento e para o mês original, em duas variantes: `sale_date` preenchida (mês original = mês da venda) e `sale_date` nula (mês original = mês do evento). Provar o eixo com `cancelled_at` regravado por SQL direto para 23:30 do último dia do mês: conta nesse mês, não no seguinte. Satélite cancelado com comprovante e venda virtual cancelada não entram. Regressão: em mês sem cancelamento, `kpis` e `eventos` idênticos entre main e branch.

**Revisão adversarial: parcial.** O eixo (cancelled_at, horário de parede de SP) e a função irmã se sustentam, mas há três furos. (1) A função nova copia a dívida 47: `event_type != 'ENSAIO'` em SQL descarta tipo NULL, e a proposta ainda soma `event_type != EVENT_TYPE_VIRTUAL`; um cancelado sem tipo (o caso do evento 395) some do Dashboard Comercial. (2) A lista de cancelados do período nasce duplicada: a RC-07 admite que a frente da DRE monta a sua própria lista. Duas consultas com réguas diferentes fazem o card da DRE e o do Dashboard divergirem para o gestor no mesmo período (Princípio I). (3) O recorte por vendedor usa `CalendarEvent.seller_id` ao vivo, enquanto a comissão usa o beneficiário congelado. O vendedor do cancelado continua editável, então os +400 podem ir para um vendedor e os 18 para outro. A proposta cita isso como risco, mas não decide.

**Emenda.** Uma função só para os cancelados do período, usada pelo Dashboard Comercial, por /admin/desempenho e pelas duas DREs. Ela devolve pares (evento, resumo) já filtrados pela regra 'foi venda'. O filtro de tipo passa a ser `or_(event_type.is_(None), event_type.notin_([ENSAIO, VIRTUAL]))`, registrado no docs/05 ao lado da dívida 47. O recorte por vendedor usa o vendedor congelado no cancelamento (pedir o campo à frente da FR-016); se a migration não congelar, a alternativa é recusar troca de vendedor em evento cancelado no caminho de escrita.

**Evidência da revisão.** app/financeiro/vendas_ops.py:168-169 (filtros atuais), :188-189 (recorte por seller_id ao vivo); app/models.py:256 (event_type nullable); app/financeiro/cobranca_ops.py:249-250 (comentário sobre o NULL e o evento 395); docs/05_DIVIDA_TECNICA.md:469 (dívida 47); app/api/financeiro_read.py:230 (a DRE usa o mesmo `!=`); app/calendar/event_ops.py:857 e :1121 (gravam seller_id; o único filtro de cancelado do arquivo é :1288, na disponibilidade); grep por is_cancelled/cancelled_at em app/api/agenda_write.py sem resultado; app/calendar/cancel_ops.py:272, :288 (cancelled_at naive SP, confirmado).

## RC-02 — O que esta frente precisa da função única de resumo do cancelado (FR-026)?

**Decisão.** Esta frente não calcula pago, devolvido, retido, comissão, BV nem imposto em lugar nenhum. Precisa de três coisas da FR-026, em app/calendar/cancel_ops.py: o resumo por evento, uma versão em lote e um consolidador do período. `vendas_ops`, `client_ops` e o endpoint de desempenho importam de lá, com import tardio (o padrão de vendas_ops.py:244, :266).

**Porquê.** A FR-026 proíbe qualquer tela de refazer a conta. O lote é obrigatório: `total_recebido` faz uma consulta por evento (cancel_ops.py:47-54) e `listar_cancelamentos` faz um `.first()` por evento (:339-350); em lista de período isso repete o N+1 que a feature 300 removeu do catálogo. O precedente de lote já existe em vendas_ops.py:118-131 (`received_map`). `cancel_ops` só importa `app.db` e `app.models` no topo (:24-34), então não há ciclo.

**Alternativas rejeitadas.** Uma função `retido_do_evento` dentro de `vendas_ops`: rejeitada, porque seria a segunda cópia da conta que a FR-026 manda existir uma vez.

**Contrato.** Pedido à frente dona da FR-026 (os nomes finais são dela):

1. `resumo_do_cancelado(event) -> ResumoCancelado`, com campos em Decimal: `event_id`, `cancelled_at`, `venda` (congelada no cancelamento), `pago`, `devolucoes: list[{id, valor, destinatario, estado: 'a_pagar'|'no_banco'|'paga'}]`, `devolvido`, `falta_devolver` (soma das devoluções ainda 'a_pagar'; 'no_banco' conta como paga), `retido` (≥ 0; 0 para satélite e venda virtual), `comissao_retido`, `beneficiario_id` (de quem é a comissão congelada, ou None), `bv_que_conta`, `imposto_retido`, `efeito_resultado` (= retido − comissão − BV − imposto).

2. `resumos_dos_cancelados(events: list[CalendarEvent]) -> dict[int, ResumoCancelado]` — mesmas contas com consultas agregadas por `event_id IN (...)`. Número de consultas constante, não proporcional à lista.

3. `consolidar_cancelamentos(resumos: Iterable[ResumoCancelado]) -> dict` — soma para o card: `quantidade`, `pago`, `devolvido`, `falta_devolver`, `retido`, `comissao_retido`, `bv`, `imposto`, `efeito_resultado`. Um consolidador só, usado pelo card da DRE e pelo do Dashboard Comercial (cada um passa a sua lista).

**Pontos de toque.**
- app/calendar/cancel_ops.py:47-54 (total_recebido — base do 'pago')
- app/calendar/cancel_ops.py:339-350 (_devolucao com .first() e destinatário 'cliente' — a FR-026 troca pela soma por categoria)
- app/financeiro/vendas_ops.py:118-131 (received_map — modelo da consulta agregada)
- app/financeiro/comissoes_ops.py:643-653 (_commission_beneficiary — reserva quando não houver beneficiário congelado)

**Riscos.**
- Se a FR-026 entregar só a versão por evento, o Dashboard Comercial e /admin/desempenho fazem várias consultas por cancelado. Funciona com o volume de hoje, mas contraria a lição da 300.
- Sem `beneficiario_id` no resumo, a comissão prevista usa `_commission_beneficiary` ao vivo — o valor fica congelado, mas o dono do valor pode mudar com uma edição.

**Verify.** Os números do Dashboard, do card, de /admin/desempenho e da ficha da cliente têm de ser iguais, por evento, aos que a tela do evento e a página de Cancelamentos mostram (FR-020/FR-026): o verify compara `retido` e `comissao_retido` entre os payloads, não contra constantes repetidas em cada asserção.

**Revisão adversarial: parcial.** A decisão de não calcular nada aqui e pedir resumo, lote e consolidador à FR-026 se sustenta, e não há ciclo de import. O contrato pedido está incompleto para o que as RC-01, 03, 04 e 07 usam: falta a lista do período (item 1 da RC-01), o vendedor congelado, a regra 'foi venda' como predicado do núcleo e o comportamento para cancelado anterior à 303 (sem valores congelados). A justificativa do import tardio está imprecisa: o padrão de vendas_ops.py:244 e :266 existe por causa de `app.financeiro.routes`, não de cancel_ops.

**Emenda.** Acrescentar ao pedido à frente da FR-026: (4) a função de cancelados do período com escopo de vendedor e EducaManto; (5) `seller_id` congelado e `is_permuta` no resumo; (6) o que o resumo devolve para cancelado sem valores congelados (derivar pago − devolvido e comissão zero, ou recusar). Import de cancel_ops pode ser no topo de vendas_ops e client_ops.

**Evidência da revisão.** app/calendar/cancel_ops.py:24-34 (só app.db e app.models no topo), :47-54 (uma consulta por evento), :339-343 (.first() por evento e destinatário 'cliente'); app/financeiro/vendas_ops.py:118-131 (received_map, modelo do lote), :244 e :266 (imports tardios de app.financeiro.routes).

## RC-03 — Como o total vendido, o ranking e a meta do vendedor contam o retido no Dashboard Comercial?

**Decisão.** O retido soma em `total_vendido` e a comissão do retido soma em `comissao_prevista`, no período do cancelamento e no mesmo escopo de vendedor das vendas vivas. `ticket_medio`, `eventos_fechados` e `desconto_concedido` continuam só com venda viva. O Dashboard Comercial não tem ranking nem meta gravada: a 'meta' é o próprio Total vendido por vendedor, e o ranking está em RC-07.

**Porquê.** Busquei 'meta', 'ranking', 'goal' e 'target' no app e no frontend: no comercial, 'meta' só aparece em texto (VendasPipelinePage.tsx:219, :243) e não há campo de meta no banco. O que o vendedor e o gestor leem como meta é o KPI Total vendido no escopo (financeiro_read.py:166-167). Ticket médio e contagem ficam de fora pela mesma razão da FR-030 na DRE: R$ 400 retidos não são um evento fechado, e dividir por ele afundaria a média. A comissão do retido entra na Comissão prevista para o vendedor não ver +400 de venda com comissão zero, e para bater com a tela de Comissões (FR-020; o mês pode diferir).

**Alternativas rejeitadas.** (a) Contar o cancelado em `eventos_fechados` e no ticket médio: rejeitado, distorce a média e contradiz a FR-030. (b) Mostrar o retido só no card, fora do total: era a opção D4-A, que o dono recusou em 29/09. (c) Criar um ranking ou um campo de meta no Dashboard Comercial: rejeitado, é funcionalidade nova fora da spec.

**Contrato.** `def build_kpis(sales, settings, commission_target_id, *, cancelados: Sequence[ResumoCancelado] = ()) -> dict` — parâmetro novo só por nome, vazio por padrão.
- `total_vendido` = Σ venda viva + Σ `retido`.
- `retido_cancelamentos` (chave nova) = Σ `retido`.
- `comissao_prevista` += Σ `comissao_retido` dos cancelados em que `commission_target_id is None` ou `beneficiario_id == commission_target_id`.
- `ticket_medio` = venda viva ÷ nº de vendas vivas (não divide o total novo). `eventos_fechados` e `desconto_concedido` sem mudança.

No endpoint: `cancelados = list_cancelled_sales(start_date, end_date, seller_id=scope.seller_id, educamanto_only=scope.educamanto_only)`; resumos em lote; ficam os que têm `venda > 0`, ou são permuta, ou têm `pago > 0`. Os KPIs recebem os cancelados sempre, com o botão ligado ou não.

TypeScript: `VendasKpis.retido_cancelamentos?: number`.

Tela: quando `retido_cancelamentos > 0`, o subtítulo do card Total vendido passa a 'inclui R$ X retidos de cancelamento'.

**Pontos de toque.**
- app/financeiro/vendas_ops.py:249-298 (build_kpis: total :269, ticket :278-282, comissão :284-290)
- app/api/financeiro_read.py:120-175 (api_vendas_pipeline: chamada :139-144, payload :159-173)
- app/api/financeiro_read.py:82-106 (_resolve_vendas_scope: o mesmo escopo vale para os cancelados)
- frontend/apps/internal/src/lib/vendas.ts:43-49 (VendasKpis)
- frontend/apps/internal/src/pages/VendasPipelinePage.tsx:81-121 (KpiGrid: subtítulo do Total vendido em :96-102)

**Riscos.**
- `total_vendido` deixa de ser `ticket_medio × eventos_fechados`; o subtítulo é o que explica a diferença.
- O backend sobe antes do bundle: por cerca de 1 minuto o total já inclui o retido sem o subtítulo.

**Verify.** Cenário 40. Como Superadmin com `seller_id` e como um COMERCIAL real (o vendedor): mês do cancelamento com `total_vendido` +400, `retido_cancelamentos` 400, `comissao_prevista` +18 (com BV 200 e taxa 5% gravada no evento), `eventos_fechados` e `ticket_medio` iguais aos de antes do cancelamento. Mês original sem os 2.000 e sem os 90. Cenário que DEVE falhar: outro COMERCIAL (não é o vendedor) não recebe os +400 nem o evento no card; FIGURINO recebe 403. Depois de alterar a devolução de 600 para 800, o total cai 200 na mesma consulta.

**Revisão adversarial: parcial.** A soma (retido no total, comissão do retido na prevista, ticket e contagem só com venda viva) se sustenta e bate com a decisão do dono. Três problemas de execução. (1) O subtítulo proposto substitui o subtítulo atual do card Total vendido, que hoje mostra o desconto concedido: no mês com cancelamento a tela perde essa informação. (2) O `KpiGrid` tipa `kpis` com um objeto inline, fora dos touchpoints; sem mexer ali o campo novo não é acessível. (3) O contrato põe no endpoint a regra 'ficam os que têm venda > 0, ou permuta, ou pago > 0'; isso é regra de negócio em view (Princípio III) e seria repetida em /admin/desempenho. Além disso a spec fala em 'ranking e meta do Dashboard Comercial', que não existem no código: é correção de texto da spec, não só do plano.

**Emenda.** O subtítulo acumula em vez de substituir: desconto e, quando houver, 'inclui R$ X retidos de cancelamento'. Trocar o tipo inline do KpiGrid por `VendasKpis`. A regra 'foi venda' mora na função de cancelados do período (emenda da RC-01); o endpoint só passa o escopo. Corrigir a FR-032 na spec: no Dashboard Comercial o retido entra no Total vendido e na Comissão prevista; ranking é Top Vendedores e /admin/desempenho.

**Evidência da revisão.** frontend/apps/internal/src/pages/VendasPipelinePage.tsx:96-102 (descontoSub é o subtítulo do Total vendido), :86-92 (tipo inline de kpis), :219 e :243 ('meta' só em texto); app/financeiro/vendas_ops.py:249-298 (build_kpis; único chamador em app/api/financeiro_read.py:167); grep por meta/ranking/goal em app/*.py sem campo comercial; spec.md FR-032 e Clarification de 29/09 ('no total vendido, no ranking e na meta').

## RC-04 — Como é o card 'Cancelamentos do período' no Dashboard Comercial e que padrão ele copia?

**Decisão.** Copia o card da Loja Virtual: um resumo calculado no núcleo, entregue numa chave própria do payload e desenhado num Card separado, só quando a quantidade é maior que zero. Difere da loja em um ponto: aparece para todo mundo que abre a tela, no escopo de cada um, e não só para o gestor. 'Imposto' e 'efeito no resultado' vão só para o gestor (Financeiro/Superadmin).

**Porquê.** O padrão está em vendas_ops.py:222-235 (`resumo_loja_virtual`), financeiro_read.py:170-173 (chave `loja_virtual`) e VendasPipelinePage.tsx:311-333 (card). O cenário de aceite 8.3 diz que o Comercial vê o card com '1 cancelado, pago 1.000, devolvido 600, retido 400', então o card não pode ser só do gestor. Imposto e efeito no resultado são resultado financeiro: a feature 196 tirou custo e lucro deste payload de propósito (financeiro_read.py:125-126; VendasPipelinePage.tsx:219-221) e o papel COMERCIAL não acessa o Painel Financeiro. O BV o vendedor já conhece (é ele quem lança na aba Comercial).

**Alternativas rejeitadas.** (a) Card só para gestor, como a Loja Virtual: rejeitado pelo cenário 8.3. (b) Todos os oito campos da FR-034 para o COMERCIAL: não adotado por padrão, porque expõe resultado a um papel que a 196 isolou dele — ver a pergunta em aberto. (c) Um consolidador próprio em `vendas_ops`: rejeitado, a soma é a mesma do card da DRE e tem de ser uma função só (RC-02, item 3).

**Contrato.** Payload de `GET /api/vendas/pipeline`, chave nova `cancelamentos` (sempre presente; a tela só desenha com `quantidade > 0`):
`{ quantidade, pago, devolvido, falta_devolver, retido, comissao_retido, bv, imposto?, efeito_resultado?, eventos: [{ event_id, title, event_date, cancelled_at, seller_name, pago, devolvido, falta_devolver, retido, comissao_retido }] }`
`imposto` e `efeito_resultado` só quando `scope.can_filter_seller`; o endpoint retira as duas chaves para os demais (o núcleo devolve tudo).

TypeScript: `DashboardComercial.cancelamentos?: CancelamentosResumo`, com `imposto?` e `efeito_resultado?` opcionais.

Tela: Card 'Cancelamentos do período' logo abaixo dos KPIs — '1 cancelado · pago R$ 1.000,00 · devolvido R$ 600,00 (falta pagar R$ 600,00) · retido R$ 400,00 · comissão do retido R$ 18,00 · BV R$ 40,00', e abaixo a lista com link para `/events/:id`.

**Pontos de toque.**
- app/financeiro/vendas_ops.py:222-235 (resumo_loja_virtual — padrão do 'à parte')
- app/api/financeiro_read.py:159-173 (payload; chaves só de gestor em :170-173)
- frontend/apps/internal/src/pages/VendasPipelinePage.tsx:311-333 (card da loja — estrutura a copiar)
- frontend/apps/internal/src/pages/FinanceiroDashboardPage.tsx:545-572 (card Auditoria de Input — padrão de lista com link por evento)
- frontend/apps/internal/src/lib/vendas.ts:56-79 (DashboardComercial)

**Riscos.**
- O card do Comercial tem 6 dos 8 campos que a FR-034 lista; se o dono quiser os 8, é tirar o corte do endpoint.
- Com 'últimos 30 dias', o card mistura cancelamentos de dois meses — é o mesmo comportamento das vendas nesse período.

**Verify.** Cenário 40. Card com `quantidade` 1, `pago` 1000, `devolvido` 600, `retido` 400, `comissao_retido` 18, `bv` 40. `falta_devolver` 600 antes e 0 depois de a devolução ser paga na Planilha (cenário 18). Como gestor: `imposto` e `efeito_resultado` presentes (342 sem nota; 278 com imposto 64). Como COMERCIAL: as duas chaves ausentes. Mês sem cancelamento: `quantidade` 0 e lista vazia. Conferência de tela como Superadmin e como Comercial.

**Revisão adversarial: parcial.** O padrão do card (chave própria, só desenha com quantidade > 0, visível a todos no escopo) confere com a Loja Virtual e com o aceite 8.3. O corte de 'imposto' e 'efeito no resultado' para o Comercial contradiz a letra da FR-034, que lista os oito campos para DRE e Dashboard Comercial. A justificativa pela feature 196 é boa, mas o plano não pode sair com um padrão que o verify codifica ('como COMERCIAL: as duas chaves ausentes') sem a spec dizer o mesmo. Segundo ponto: `comissao_retido` do card soma todos os eventos do escopo, enquanto o KPI só soma quando o beneficiário é o próprio usuário; em evento EducaManto vendido por um Comercial, card e KPI mostram valores diferentes. Terceiro: o contrato não nomeia a função do núcleo que monta a chave `cancelamentos` com a lista por evento.

**Emenda.** Levar a pergunta ao dono antes do /speckit-tasks e gravar a resposta na FR-034 (campos por papel). Até lá, manter o padrão fechado. Filtrar a comissão do card pela mesma regra do KPI (beneficiário = alvo, ou todos para gestor). Nomear no plano uma função pura em vendas_ops que recebe os pares (evento, resumo) e devolve o bloco; o endpoint só retira as duas chaves de gestor.

**Evidência da revisão.** spec.md FR-034 e História 8 (oito campos) e aceite 8.3 (quatro campos para o Comercial); app/api/financeiro_read.py:125-126 (custo e lucro fora do payload por decisão da 196), :170-173 (chaves só de gestor); app/financeiro/vendas_ops.py:222-235 (resumo_loja_virtual), :284-290 (comissão do KPI filtra por beneficiário); VendasPipelinePage.tsx:311-333 (card da loja).

## RC-05 — Como funciona o botão 'Mostrar cancelados' na lista de vendas (parâmetro, padrão, endereço, linha)?

**Decisão.** Parâmetro de API `incluir_cancelados`, desligado por padrão e aceito de qualquer papel que abre a tela. Na tela, o estado mora no endereço como `?cancelados=1`. Ligado, os cancelados do período entram na mesma lista, pelo eixo do cancelamento, com o retido no lugar da venda e a comissão do retido no lugar da cheia. O botão fica no cabeçalho da lista, sempre visível.

**Porquê.** O opt-in por query string é o padrão de `incluir_loja_virtual` (financeiro_read.py:153-156; lib/vendas.ts:104). A tela hoje guarda período e vendedor em `useState` (VendasPipelinePage.tsx:224-228), mas a FR-035 pede o botão no endereço; o padrão de estado na URL já existe em ComissoesPage.tsx:303-315 (`useSearchParams` com `replace`). Só o botão vai para a URL — período e vendedor ficam como estão. A linha entra no mês do cancelamento, e não no mês original, para a lista somar o KPI (RC-01). Bundle antigo nunca manda o parâmetro, então nunca recebe linha com status desconhecido.

**Alternativas rejeitadas.** (a) Botão só para gestor, como a loja: rejeitado — o vendedor precisa achar o próprio cancelado. (b) Botão dentro do card: rejeitado, porque o card some quando não há cancelado e a FR-035 liga o botão à lista. (c) Estado em `useState`: rejeitado, a FR-035 pede no endereço. (d) Uma função nova para serializar o cancelado: rejeitado — estender `serialize_sale` mantém as chaves da linha iguais.

**Contrato.** `GET /api/vendas/pipeline?incluir_cancelados=1` (aceita '1', 'true', 'sim'). O payload devolve `incluir_cancelados: bool`.

`serialize_sale(event, settings, *, contract_status, received, cancelado: ResumoCancelado | None = None)`. Com `cancelado`: `sale_value` = retido; `sale_value_gross` = None (não confundir com desconto); `comissao` = `comissao_retido`; `payment_status` = 'cancelado'; e as chaves novas `cancelado: true`, `cancelled_at`, `venda_original`, `devolvido`, `falta_devolver`. `serialize_sales` recebe o dicionário de resumos e ordena por `data_de_competencia`, decrescente.

TypeScript: em `VendaFechada`, `cancelado?: boolean`, `cancelled_at?: string | null`, `venda_original?: number`, `devolvido?: number`, `falta_devolver?: number`. `useDashboardComercial` ganha `incluirCancelados` (entra na queryKey).

Tela: botão 'Mostrar cancelados' / 'Ocultar cancelados' com `aria-pressed`. Linha cancelada esmaecida, título riscado, selo 'Cancelado' (RC-11), valor = retido com a sublinha 'retido de R$ 2.000,00' e 'Cancelado em dd/mm/aaaa' no lugar de 'Venda fechada em'.

**Pontos de toque.**
- app/api/financeiro_read.py:150-157 (leitura do opt-in da loja — modelo)
- app/api/financeiro_read.py:168 (eventos do payload)
- app/financeiro/vendas_ops.py:301-357 (serialize_sale / serialize_sales; comissão cheia em :339)
- frontend/apps/internal/src/lib/vendas.ts:17-40, 81-109 (VendaFechada, parâmetros e queryKey do hook)
- frontend/apps/internal/src/pages/VendasPipelinePage.tsx:123-178 (SaleRow: selos :136-145, sublinha :146-148, valor :150-157), :224-230 (estado), :336-341 (cabeçalho da lista)
- frontend/apps/internal/src/pages/ComissoesPage.tsx:303-315 (padrão de estado na URL)

**Riscos.**
- Quem liga o botão no mês original do evento não vê o cancelado ali — ele está no mês do cancelamento. O card e a página de Cancelamentos são o caminho.
- O contador 'N evento(s) no período' usa `eventos.length` (VendasPipelinePage.tsx:339) e passa a incluir os cancelados com o botão ligado; trocar por 'N venda(s) · M cancelado(s)'.

**Verify.** Cenários 37 e 40. Sem o parâmetro: `eventos` sem o cancelado e `incluir_cancelados` false. Com ele: linha com `cancelado` true, `payment_status` 'cancelado', `sale_value` 400, `venda_original` 2000, `comissao` 18, nunca 90. Evento que estava marcado 'Sumiu do Google' e foi cancelado aparece só como cancelado. Tela: recarregar com `?cancelados=1` mantém o botão ligado; o cancelado não é sinalizado só por cor.

**Revisão adversarial: sim.** Sem refutação de fundo. O opt-in por query string, o estado na URL e a extensão de `serialize_sale` conferem com os padrões citados; `serialize_sales` tem um chamador só; zerar `sale_value_gross` evita o falso desconto na linha. Observações menores: a lista não tem coluna de comissão, então 'comissão do retido no lugar da cheia' vale só no payload; o texto de lista vazia ('Nenhuma venda fechada neste período') aparece com o botão desligado mesmo quando o KPI já inclui retido.

**Emenda.** Manter. Ajustar o texto de lista vazia para citar os cancelados quando `cancelamentos.quantidade > 0`. Rodar de novo os cenários de pipeline do verify_205, que consomem o mesmo endpoint.

**Evidência da revisão.** app/api/financeiro_read.py:153-156 (opt-in da loja), :168 (único chamador de serialize_sales); VendasPipelinePage.tsx:123-178 (colunas da linha: sem comissão; desconto em :124-127), :181-186 (texto de lista vazia), :224-228 (useState), :339 (contador); frontend/apps/internal/src/pages/ComissoesPage.tsx:303-315 (useSearchParams com replace); specs/205-loja-interacoes-virtuais/verify_205.py:1142 e :1259.

## RC-06 — Como entra o status 'cancelado' em event_payment_status?

**Decisão.** `event_payment_status` ganha um argumento só por nome, `cancelado`, falso por padrão; verdadeiro, devolve 'cancelado' antes de qualquer outra regra. `PAYMENT_STATUS_LABELS` ganha 'cancelado': 'Cancelado'. A DRE antiga (Jinja) não muda.

**Porquê.** A função é a fonte única do rótulo de cobrança do Dashboard Comercial e da tabela 'Eventos no período' da DRE nova (vendas_ops.py:44-66; chamadores em vendas_ops.py:317 e financeiro_read.py:406). Sem o ramo, o cancelado do exemplo sairia 'parcial' (2.000 de venda, 1.000 recebidos). O argumento com padrão falso não muda nenhuma chamada existente. A DRE Jinja calcula o status à parte (app/financeiro/routes.py:437-446) e não chama esta função, e a spec limita o que entra na tela antiga.

**Alternativas rejeitadas.** (a) Decidir 'cancelado' em cada chamador, fora da função: rejeitado, são dois chamadores e a regra se espalha. (b) Passar o evento inteiro à função: rejeitado, muda a assinatura pura (três escalares) sem necessidade.

**Contrato.** `def event_payment_status(sale_value: float, received: float, is_permuta: bool, *, cancelado: bool = False) -> str` — `if cancelado: return 'cancelado'` na primeira linha.

TypeScript: 'cancelado' entra em `SalePaymentStatus` e em `EventoStatus`. `PAYMENT_TONE`, `STATUS_LABEL` e `STATUS_CLASS` são `Record<união, …>`, então o `tsc` obriga a pôr a chave nas duas páginas (tom 'neutral' e rótulo 'Cancelado').

**Pontos de toque.**
- app/financeiro/vendas_ops.py:32-38 (PAYMENT_STATUS_LABELS)
- app/financeiro/vendas_ops.py:44-66 (event_payment_status)
- app/financeiro/vendas_ops.py:317 e app/api/financeiro_read.py:406 (os dois chamadores)
- app/financeiro/routes.py:437-446 (status inline do Jinja — não toca)
- frontend/apps/internal/src/lib/vendas.ts:9-14 (SalePaymentStatus)
- frontend/apps/internal/src/lib/financeiro.ts:94 (EventoStatus)
- frontend/apps/internal/src/pages/VendasPipelinePage.tsx:39-45 (PAYMENT_TONE)
- frontend/apps/internal/src/pages/FinanceiroDashboardPage.tsx:60-74 (STATUS_LABEL / STATUS_CLASS)

**Riscos.**
- A chave de `EventoStatus` e os mapas de FinanceiroDashboardPage pertencem à frente da DRE; as duas frentes têm de subir a união juntas para o typecheck passar.

**Verify.** Linha cancelada do Dashboard Comercial com `payment_status` 'cancelado' e `payment_status_label` 'Cancelado' (cenário 40), nunca 'parcial'. Evento vivo com os mesmos valores segue 'parcial'. `npm run typecheck` limpo nas três SPAs.

**Revisão adversarial: sim.** Sem refutação. A função tem exatamente dois chamadores, o argumento só por nome não muda nenhum deles, os mapas do frontend são Record sobre a união (o tsc obriga a chave) e a DRE Jinja calcula o status inline. Observação: com o selo vermelho ao lado do título e a coluna Cobrança também dizendo 'CANCELADO', a linha repete a palavra duas vezes.

**Emenda.** Manter. Subir a união `EventoStatus` e os dois mapas da página da DRE no mesmo commit da frente da DRE. Opcional: na coluna Cobrança do cancelado, mostrar 'Retido R$ X' em vez de repetir 'Cancelado'.

**Evidência da revisão.** app/financeiro/vendas_ops.py:44-66, :317; app/api/financeiro_read.py:406; app/financeiro/routes.py:437-446 (status inline do Jinja); VendasPipelinePage.tsx:39-45 (Record<SalePaymentStatus,…>); frontend/apps/internal/src/pages/FinanceiroDashboardPage.tsx:60 e :68 (Record<EventoStatus,…>); frontend/apps/internal/src/lib/financeiro.ts:94.

## RC-07 — Como o ranking de vendedores conta o retido (Top Vendedores da DRE e /admin/desempenho)?

**Decisão.** Em /admin/desempenho, o cancelado sai da soma do mês do evento e o retido entra no total do vendedor no mês do cancelamento; a contagem de vendas não conta o cancelado, e o item ganha os campos `retido` e `cancelados`. No Top Vendedores da DRE nova (API), o retido soma na receita e no 'lucro' do vendedor no período do cancelamento. O Top Vendedores da DRE antiga (Jinja) não muda.

**Porquê.** /admin/desempenho hoje conta o cancelado com o valor cheio, por `start_at`, sem filtro (admin_config_read.py:149-157). A spec manda corrigir só o cancelado ali; as outras diferenças de régua (satélite, ensaio, permuta, eixo de data) ficam como dívida. O Top Vendedores sai de `eventos_com_venda`, que já exclui o cancelado (financeiro_read.py:225-237, :348-363); a FR-032 cita 'ranking de vendedores' e a FR-030 final não lista mais o Top Vendedores entre as exclusões. O 'lucro' do ranking é venda − cachês, sem BV (financeiro_read.py:353); como os cachês do cancelado ficam fora (FR-027), o lucro do cancelado é o próprio retido. Na tela antiga o ranking é calculado inline (routes.py:381-392) e a spec só admite ali números vindos das funções comuns, uma linha de template e o ajuste do ticket médio.

**Alternativas rejeitadas.** (a) Trocar a consulta de /admin/desempenho por `list_closed_sales`: rejeitado, a spec deixa as outras réguas fora. (b) Contar o cancelado na contagem de vendas do vendedor: rejeitado, coerente com `eventos_fechados` (RC-03). (c) Levar o retido também ao Top Vendedores do Jinja: rejeitado, é mexer na view antiga além do mínimo da parada.

**Contrato.** `GET /api/admin/desempenho?month=YYYY-MM` (RBAC inalterado: Superadmin):
- a consulta de :150-154 ganha `CalendarEvent.cancelled_at.is_(None)`;
- depois dela: `list_cancelled_sales(start.date(), (end − 1 dia).date())` + resumos em lote; para cada cancelado com vendedor: `total += retido`, `retido += retido`, `cancelados += 1`; `count` não muda;
- payload: `vendas: [{ name, count, total, retido?, cancelados? }]`, e `totals.valor` inclui o retido, com `totals.retido` novo.
TypeScript: `DesempenhoItem.retido?: number`, `DesempenhoItem.cancelados?: number`, `totals.retido?: number`. Tela: 'Fulana (5) R$ 18.400,00' com a sublinha 'inclui R$ 400,00 retidos de 1 cancelamento'.

Top Vendedores (API): para cada resumo dos cancelados do período que a DRE já carrega para a cascata, com vendedor: `seller_revenue[seller_id] += retido` e `seller_margin[seller_id] += retido`. Sem campo novo no payload.

**Pontos de toque.**
- app/api/admin_config_read.py:117-178 (api_admin_desempenho: consulta :149-157, payload :163-178)
- app/api/financeiro_read.py:348-363 (Top Vendedores da API — arquivo da frente da DRE)
- app/financeiro/routes.py:381-392 (Top Vendedores do Jinja — não toca)
- frontend/apps/internal/src/lib/adminConfig.ts:85-97 (DesempenhoItem, AdminDesempenho)
- frontend/apps/internal/src/pages/AdminDesempenhoPage.tsx:86-108 (card Vendas)
- frontend/apps/internal/src/lib/financeiro.ts:46-51 (TopSeller — sem campo novo)

**Riscos.**
- /admin/desempenho mistura dois eixos: venda viva pelo mês do evento e retido pelo mês do cancelamento. É a divergência de régua que a spec já manda registrar no docs/05.
- O Top Vendedores da tela antiga diverge do da API pelo valor do retido; registrar no docs/05 junto das outras divergências entre as duas DREs.
- A soma no Top Vendedores depende da lista de cancelados que a frente da DRE monta no mesmo endpoint — combinar o nome da variável no plano.

**Verify.** Cenário 40. `/api/admin/desempenho?month=<mês do cancelamento>`: vendedor com `total` +400, `retido` 400, `cancelados` 1 e `count` sem o cancelado. `?month=<mês do evento>`: sem os 2.000 e sem o evento em `count` (na main, o mesmo cenário traz os 2.000 — prova por mutação). DRE da API no mês do cancelamento: o vendedor em `paineis.top_sellers` com `receita` +400. Cenário que DEVE falhar: COMERCIAL em /api/admin/desempenho recebe 403.

**Revisão adversarial: parcial.** O conteúdo (filtrar o cancelado na consulta de /admin/desempenho, somar o retido no mês do cancelamento, não contar na contagem; retido no Top Vendedores da API e não no Jinja) é coerente com a spec e com o código. O desenho repete a mesma agregação 'retido por vendedor no período' em dois endpoints, escrita inline em cada view, junto com a regra 'foi venda' (Princípios I e III). O vendedor do cancelado é lido ao vivo (`ev.seller`), com o mesmo problema da RC-01. Um vendedor que só tem retido no mês aparece como 'Fulana (0) R$ 400,00'. E o cenário 26 da spec exige API e tela antiga 'iguais ao centavo': se a comparação incluir o painel de Top Vendedores, o verify falha por construção.

**Emenda.** Uma função pura em vendas_ops que devolve, por vendedor, retido e quantidade de cancelados do período, a partir da função única de cancelados; os dois endpoints só chamam e serializam. Usar o vendedor congelado. Na tela, a sublinha 'inclui R$ X retidos de N cancelamento(s)' cobre o caso de contagem zero. No verify, a comparação API × Jinja do cenário 26 fica restrita à cascata, e a divergência do Top Vendedores vai para o docs/05.

**Evidência da revisão.** app/api/admin_config_read.py:149-157 (consulta sem filtro, agregação inline por nome do vendedor), :163-178 (payload); app/api/financeiro_read.py:348-363 (Top Vendedores da API; lucro = venda − _group_cost); app/financeiro/comissoes_ops.py:599-620 (_group_cost só cachês, sem BV); app/financeiro/routes.py:381-392 (Top Vendedores do Jinja); frontend/apps/internal/src/pages/AdminDesempenhoPage.tsx:95-104; frontend/apps/internal/src/lib/adminConfig.ts:85-97; spec.md FR-030 (não exclui Top Vendedores), FR-032, cenário 26 e Fora de escopo (réguas de /admin/desempenho).

## RC-08 — O que muda na Performance da Home?

**Decisão.** O painel passa a ignorar evento cancelado nas três métricas: casting escalado, figurino pronto e cachês escalados. O retido não entra nele, porque o painel não tem número de venda.

**Porquê.** `compute_performance` devolve só contagens de vagas e a soma dos cachês (app/api/dashboard_service.py:267-328); a tela mostra 'Casting escalado', 'Figurino pronto' e 'Cachês escalados' (HomePerformance.tsx:172-192). Não existe total vendido nem vendedor ali, então 'o retido conta como venda na Performance da Home' (FR-032) não tem onde cair. O que o painel erra hoje é contar vagas e cachê de cancelado: `perf_filter` só olha data e ensaio (:290-293), enquanto as tarefas da mesma Home já usam `not_cancelled` (:35-37) e a Planilha não paga cachê de cancelado (app/financeiro/routes.py:701). A função tem um único chamador (:537).

**Alternativas rejeitadas.** Criar um número de vendas do período na Home para receber o retido: rejeitado, é painel novo fora da spec.

**Contrato.** Sem mudança de payload nem de tela. `perf_filter = and_(start_at >= start_dt, start_at < end_dt, exclude_ensaios, CalendarEvent.cancelled_at.is_(None))`.

**Pontos de toque.**
- app/api/dashboard_service.py:290-293 (perf_filter ganha `CalendarEvent.cancelled_at.is_(None)`)
- app/api/dashboard_service.py:26-38 (_base_filters['not_cancelled'] — a mesma expressão, já usada pelas tarefas)
- app/api/dashboard_service.py:533-547 (único chamador)
- frontend/apps/internal/src/components/HomePerformance.tsx:165-193 (sem mudança)

**Riscos.**
- O texto da spec precisa ser corrigido: a FR-032 e o cenário 40 do verify falam em retido e em 'vendedor com +400' na Performance da Home, e esse painel não tem venda. No plano, a Performance da Home sai da lista da FR-032 e entra como 'não conta o cancelado'.

**Verify.** `GET /api/dashboard?perf_range=custom&perf_start=&perf_end=` como Superadmin, cobrindo a data do evento, antes e depois do cancelamento: `casting_total`, `casting_done` e `money_total` caem exatamente as vagas e o cachê do evento cancelado. Usar role existente com `talent_id` (nunca `character_name` inventado). O cenário 40 da spec troca 'Performance da Home: vendedor com +400' por esta asserção.

**Revisão adversarial: sim.** O fato confere: o painel só tem contagens de cargos e soma de cachês, é exclusivo do Superadmin e tem um chamador só. Não há onde lançar retido nem 'vendedor com +400'. O que falta é processo: a FR-032 e o cenário 40 citam a Performance da Home, e a correção precisa entrar na spec, não só no plano. Não é reabrir decisão do dono: a resposta dele fala em total vendido, ranking e meta, sem citar esse painel.

**Emenda.** Manter o filtro de cancelado no `perf_filter`. Antes do /speckit-tasks, editar a FR-032 (tirar a Performance da Home da lista do retido e dizer que o painel não conta cargo nem cachê de cancelado) e o cenário 40 (trocar 'vendedor com +400' pela asserção de casting_total, casting_done e money_total).

**Evidência da revisão.** app/api/dashboard_service.py:267-328 (compute_performance; perf_filter em :290-293), :26-38 (not_cancelled já usado nas tarefas), :533-547 (único chamador, dentro de `if is_superadmin`); frontend/apps/internal/src/components/HomePerformance.tsx:172-192 (três métricas, nenhuma de venda); spec.md FR-032 e cenário 40.

## RC-09 — Como a ficha da cliente conta o total vendido e a recorrência, e como mostra o cancelado?

**Decisão.** O total vendido soma a venda dos eventos vivos mais o retido dos cancelados. A contagem de eventos da cliente, a ordenação da lista de clientes e a métrica de clientes recorrentes deixam de contar o cancelado. Na ficha, o cancelado continua na lista, esmaecido, riscado e com o selo.

**Porquê.** Hoje `total_sales` soma `sale_value` de todo evento, inclusive cancelado (app/clientes/client_ops.py:158), e as contagens não filtram (:117-121, :216-220). A FR-032 manda o total contar o retido no lugar da venda original; a Premissa diz que o cancelado não conta como evento realizado para a recorrência; a FR-036 manda mostrar sempre, com o selo. A assinatura de `get_client_detail` fica igual (tupla de 4): ela tem três chamadores, e dois só desempacotam a tupla para pegar a cliente (app/api/clientes_write.py:75, :101). O retido de satélite e de venda virtual já vem zero da FR-026.

**Alternativas rejeitadas.** (a) Tirar o cancelado do total e mostrar 'R$ X retidos' à parte: era a D4-A, recusada pelo dono. (b) Devolver uma tupla de 5 com o retido separado: rejeitado, obriga a mexer nos dois chamadores de escrita por um subtítulo que a spec não pede. (c) Filtrar o cancelado da lista da ficha: rejeitado, a FR-036 manda mostrar sempre.

**Contrato.** `get_client_detail(client_id)` — mesma assinatura. O quarto item passa a ser: Σ `sale_value` dos eventos sem `cancelled_at` + Σ `resumo.retido` dos cancelados (via `resumos_dos_cancelados`, import tardio), em Decimal.

`list_clients` e `client_metrics`: as duas consultas de contagem ganham `.join(CalendarEvent, EventClient.event_id == CalendarEvent.id).filter(CalendarEvent.cancelled_at.is_(None))`.

`GET /api/clientes/<id>`: cada item de `events` ganha `cancelado: bool`; `event_count` = só os vivos; chave nova `cancelled_count`.

TypeScript: `ClientEvent.cancelado?: boolean`, `ClientDetail.cancelled_count?: number`.

Tela: 'N evento(s) · M cancelado(s) · total vendido: R$ X'; linha cancelada com `opacity-60`, título riscado e o selo (RC-11) ao lado da relação.

**Pontos de toque.**
- app/clientes/client_ops.py:132-159 (get_client_detail; total em :158)
- app/clientes/client_ops.py:111-129 (list_clients; contagem em :117-121)
- app/clientes/client_ops.py:183-225 (client_metrics; contagem em :216-220, recorrentes em :223)
- app/api/clientes_read.py:64-106 (eventos em :81-89, event_count :90, total_sales :91)
- app/api/clientes_write.py:75, :101 (chamadores que não mudam)
- frontend/apps/internal/src/lib/clientes.ts:23-28, 41-49 (ClientEvent, ClientDetail)
- frontend/apps/internal/src/pages/ClientDetailPage.tsx:179-205 (cabeçalho e linhas)

**Riscos.**
- `clients_with_event` sai da mesma consulta de `recurring_clients` (:224): cliente cujo único evento foi cancelado deixa de contar como 'cliente com evento'. É coerente com a Premissa, mas é um número que muda.
- A ficha lê o evento por `EventClient`; evento ligado só pelo `client_id` antigo já não aparece hoje — não muda.

**Verify.** Cenário 40. `GET /api/clientes/<id>`: `total_sales` = 400 + vendas vivas (2.000 antes do cancelamento — prova por mutação), `event_count` sem o cancelado, `cancelled_count` 1, item com `cancelado` true. `GET /api/clientes/metricas`: cliente com 1 evento vivo e 1 cancelado não entra em `recurring_clients` (comparar antes e depois). `GET /api/clientes/?q=`: `event_count` da cliente sem o cancelado. Depois de alterar a devolução para 800: `total_sales` cai 200.

**Revisão adversarial: parcial.** A regra (total = venda dos vivos + retido dos cancelados; contagens e recorrência sem o cancelado; cancelado visível com selo) segue a FR-032, a FR-036 e a Premissa. O furo está em manter a assinatura sem olhar o custo: `get_client_detail` é chamada pelo PATCH e pelo DELETE da cliente só para buscar o registro. Com o resumo dentro dela, editar CPF ou excluir cliente passa a rodar as consultas do resumo do cancelado e fica acoplado a cancel_ops: um erro no resumo derruba edição e exclusão de cliente.

**Emenda.** Calcular o resumo só quando a cliente tiver evento cancelado (`cancelados = [e for e in events if e.is_cancelled]`; sem cancelado, nenhuma consulta nova e nenhum import exercitado). Registrar no docs/02 que 'Com evento' e 'Recorrentes' passam a ignorar cancelado.

**Evidência da revisão.** app/clientes/client_ops.py:132-159 (total em :158), :117-121 e :216-224 (contagens sem filtro); app/api/clientes_write.py:75 e :101 (PATCH e DELETE chamam get_client_detail e descartam eventos e total); app/api/clientes_read.py:71-91; frontend/apps/internal/src/lib/clientes.ts:145-156 (o PATCH só invalida a query); frontend/apps/internal/src/pages/ClientsListPage.tsx:102-112 (rótulos das métricas); app/marketing/desempenho_ops.py:300 e :860 (usam só new_by_month, não são afetados).

## RC-10 — Como a ficha do talento trata o cachê e o evento cancelado?

**Decisão.** O evento cancelado continua no histórico do talento, com o selo, mas sai dos quatro agregados do cabeçalho: Total faturado, Eventos, Personagens e Último evento.

**Porquê.** Hoje os agregados saem da lista inteira, sem olhar cancelamento (app/talents/talent_ops.py:302-316; a consulta está em :225-235). A FR-036 proíbe contar cachê de cancelado em 'Total faturado' e manda mostrar o cancelado sempre, com o selo. Tirar só o cachê deixaria 'Eventos: 5' ao lado de um total de 4 eventos e poria como 'Último evento' um show que não aconteceu. A Planilha já não paga cachê de cancelado (app/financeiro/routes.py:701). `r.event` já é lido linha a linha para o título (:293), então não há consulta nova.

**Alternativas rejeitadas.** (a) Excluir só o cachê do total, como a letra da FR-036: rejeitado pela incoerência entre os quatro números do mesmo cabeçalho. (b) Filtrar o cancelado na consulta: rejeitado, ele sumiria do histórico e a FR-036 manda mostrar.

**Contrato.** Em `get_talent_profile`: `vivos = [r for r in history if not (r.event and r.event.is_cancelled)]`; `total_events`, `total_earned`, `characters_done` e `last_event` passam a sair de `vivos`; `items` continua com todos e ganha `cancelado: bool`.

TypeScript: `TalentHistoryItem.cancelado?: boolean`.

Tela: linha cancelada com `opacity-60`, título e cachê riscados, selo (RC-11) ao lado do título.

**Pontos de toque.**
- app/talents/talent_ops.py:203-318 (get_talent_profile: consulta :225-235, itens :290-301, agregados :302-316)
- app/api/talents_read.py:86-132 (endpoint; só repassa o resultado)
- frontend/apps/internal/src/lib/talents.ts:141-147 (TalentHistoryItem)
- frontend/apps/internal/src/pages/TalentDetailPage.tsx:850-863 (cabeçalho), :879-895 (linhas)

**Riscos.**
- Cachê que já tinha sido pago ao talento antes do cancelamento sai do 'Total faturado', embora o dinheiro tenha saído. A spec manda excluir sem exceção; multa e cachê de cancelamento em cima da hora seguem como gasto extra à parte (fora de escopo).

**Verify.** Cenário 40. `GET /api/talents/<id>` de um talento escalado no evento (role existente com `talent_id`), antes e depois do cancelamento: `total_earned` cai o cachê, `total_events` cai 1, e o item continua em `items` com `cancelado` true. Se o evento era o mais recente, `last_event` passa ao anterior.

**Revisão adversarial: sim.** Sem refutação técnica: os quatro agregados saem da mesma lista, `r.event` já é lido por linha, e os cinco chamadores (um de leitura, quatro de escrita) só repassam o dicionário. A FR-036 só manda tirar o cachê de 'Total faturado'; estender a Eventos, Personagens e Último evento é coerente, mas é comportamento que a spec não descreve.

**Emenda.** Manter. Acrescentar uma linha à FR-036 dizendo que os quatro agregados do cabeçalho ignoram o cancelado, para o analyze e o converge não acusarem divergência.

**Evidência da revisão.** app/talents/talent_ops.py:225-235 (consulta), :286-316 (itens e agregados); app/api/talents_read.py:114; app/api/talents_write.py:52, :182, :209, :236; app/models.py:383 (is_cancelled); frontend/apps/internal/src/pages/TalentDetailPage.tsx:850-863, :879-899; spec.md FR-036.

## RC-11 — Qual é o selo 'Cancelado' e de onde a tela sabe que o evento é cancelado?

**Decisão.** Um componente só, `SeloCancelado`, usado em todas as superfícies desta frente (lista de vendas, card, ficha da cliente, ficha do talento), sempre junto de texto riscado e linha esmaecida. O servidor manda um booleano `cancelado` por linha; a tela nunca deduz o cancelamento de outro campo.

**Porquê.** A FR-035 exige que o cancelado não seja sinalizado só por cor, e a SC-008 exige o mesmo sinal em todo lugar. Hoje não há selo de cancelado em lista nenhuma: a única marca é o banner do cabeçalho do evento (EventHeader.tsx:215, :364-370). O `Badge` do `@manto/ui` já tem o tom vermelho (frontend/packages/ui/src/components/badge.tsx:4-16) e a lista de vendas já põe selos ao lado do título (VendasPipelinePage.tsx:136-145). Nas fichas basta o booleano: o evento cancelado nunca mostra 'sumiu do Google' (o cancelado vence a marca, FR-033).

**Alternativas rejeitadas.** (a) Um `Badge` escrito à mão em cada tela: rejeitado, quatro cópias do mesmo sinal. (b) Mandar `cancelled_at` e deixar a tela decidir: rejeitado, o padrão do projeto é o servidor decidir e a tela espelhar. (c) Exportar o selo pelo `@manto/ui`: rejeitado por ora, só a SPA interna usa.

**Contrato.** `frontend/apps/internal/src/components/SeloCancelado.tsx`: `<Badge tone="red">CANCELADO</Badge>`, sem props além de `className`. Campo de payload `cancelado?: boolean` em `VendaFechada`, `ClientEvent` e `TalentHistoryItem` (opcional no TypeScript; ausente = falso). Se a frente da agenda (FR-033) criar um componente de situação mais geral, as quatro telas daqui passam a usar o dela e este arquivo não nasce.

**Pontos de toque.**
- frontend/packages/ui/src/components/badge.tsx:4-28 (Badge e tons — reuso)
- frontend/apps/internal/src/components/EventDetail/EventHeader.tsx:215, 364-370 (vocabulário visual existente)
- frontend/apps/internal/src/pages/VendasPipelinePage.tsx:136-145 (lugar do selo na linha)
- frontend/apps/internal/src/pages/ClientDetailPage.tsx:199-202 (lugar do selo na ficha da cliente)
- frontend/apps/internal/src/pages/TalentDetailPage.tsx:884 (lugar do selo na ficha do talento)

**Riscos.**
- Duas frentes podem criar dois selos (agenda/busca e comercial); o plano consolidado escolhe um arquivo só.

**Verify.** Conferência de tela (não é cenário de API): lista de vendas com o botão ligado, ficha da cliente e ficha do talento mostram a palavra 'Cancelado', o título riscado e a linha esmaecida. No verify, os três payloads trazem `cancelado` true para o evento e a chave ausente ou falsa para os vivos.

**Revisão adversarial: parcial.** O componente único e o reuso do Badge se sustentam (o tom vermelho existe e não há selo de cancelado em lista hoje). O booleano `cancelado` cria um segundo vocabulário ao lado da 'situação única' que a FR-033 manda o servidor devolver no resumo 'da agenda, da busca e das listas'. A proposta reconhece o risco de dois selos, mas deixa a escolha em aberto. Detalhe: o contrato escreve 'CANCELADO' e as notas de verificação procuram 'Cancelado'.

**Emenda.** Decidir no plano consolidado: um helper de servidor para a situação do evento e um componente só. As superfícies desta frente recebem o mesmo campo da agenda (o selo aparece quando a situação é cancelado), ou o plano declara que fichas e lista de vendas ficam com o booleano por não mostrarem as outras situações. Fixar a grafia do selo num lugar só.

**Evidência da revisão.** spec.md FR-033, FR-035, FR-036 e aceite 8.5; frontend/packages/ui/src/components/badge.tsx:4-21 (tons); frontend/apps/internal/src/components/EventDetail/EventHeader.tsx:215 e :364-370 (única marca de hoje); VendasPipelinePage.tsx:136-145 (selos em maiúsculas: GRUPO, PERMUTA).

## RC-12 — O que tocar no Jinja vivo de /vendas/?

**Decisão.** Uma linha: a consulta da view antiga passa a filtrar evento cancelado. O template não muda e nada é movido nem apagado.

**Porquê.** A view `pipeline()` lista todo evento que não é ensaio, sem filtro de cancelado, com a comissão cheia de `_event_commission` (app/financeiro/routes.py:1445-1454); o template mostra venda, custo, lucro e comissão como evento normal (app/templates/vendas/pipeline.html:27-69). Ela está registrada e responde pelo domínio direto do backend, embora o `server.js` não a repasse (docs/PARADA_REMOCAO_JINJA.md:31-34). Deixar como está contraria a SC-008 ('em nenhuma tela o cancelado aparece como evento normal') e a FR-020 (R$ 90 ali contra R$ 18 no resto). O filtro é a mesma expressão que as outras views Jinja do financeiro já usam (routes.py:282, :701).

**Alternativas rejeitadas.** (a) Não tocar e registrar dívida: rejeitado, fica uma rota viva mostrando comissão cheia de cancelado. (b) Levar selo, retido e botão ao template: rejeitado, é fazer crescer uma tela cuja remoção está pausada.

**Contrato.** `events_q = CalendarEvent.query.filter(CalendarEvent.event_type != "ENSAIO", CalendarEvent.cancelled_at.is_(None))` em app/financeiro/routes.py:1445. Nenhuma função movida, nenhum import novo.

**Pontos de toque.**
- app/financeiro/routes.py:1438-1466 (view pipeline; consulta em :1445)
- app/templates/vendas/pipeline.html (sem mudança)
- docs/PARADA_REMOCAO_JINJA.md:31-34, 58-69 (o que está vivo e o que não mover)

**Riscos.**
- A tela antiga fica sem nenhum jeito de ver o cancelado nem o retido; é aceito, porque ela não é alcançável pela porta pública.

**Verify.** `GET /vendas/` direto no Flask, com a sessão do Superadmin: o HTML contém o título de um evento vivo de controle e não contém o título único do evento cancelado. A asserção sobre HTML precisa de âncora e de prova por mutação: na main, o mesmo título aparece.

**Revisão adversarial: sim.** Sem refutação. A view lista todo evento que não é ensaio, sem período e sem filtro de cancelado, com a comissão cheia; o template não soma nada, então o filtro de uma linha não quebra total nenhum. Nada é movido. O custo é um cenário de verify sobre HTML para uma tela que não é alcançável pela porta pública.

**Emenda.** Manter. No verify, âncora pelo título único do evento e prova por mutação, como a própria proposta descreve. Se o plano precisar cortar, esta é a decisão mais barata de virar dívida no docs/05.

**Evidência da revisão.** app/financeiro/routes.py:1438-1466 (consulta em :1445, comissão cheia em :1454), :282 (mesma expressão no painel Jinja); app/templates/vendas/pipeline.html:27-69 (sem totais); docs/PARADA_REMOCAO_JINJA.md:31-34.

## O que a frente deixou de decidir (revisão)

- Função única para 'cancelados do período' compartilhada com a frente da DRE. A proposta cria `list_cancelled_sales` em vendas_ops e assume que a DRE monta a própria lista (RC-07). Sem uma régua só, o card da DRE e o do Dashboard Comercial podem divergir para o gestor no mesmo período.
- Vendedor do evento cancelado continua editável (app/calendar/event_ops.py:857 e :1121, sem guarda de cancelado). Falta decidir: congelar o vendedor no cancelamento e filtrar por ele, ou recusar a troca no caminho de escrita. A proposta só lista como risco.
- Dívida 47 (docs/05_DIVIDA_TECNICA.md:469): a função nova não deve herdar o `event_type != 'ENSAIO'` que descarta tipo NULL. Precisa de decisão explícita, porque o mesmo `!=` está na consulta da DRE (app/api/financeiro_read.py:230).
- Correções de texto na spec antes do /speckit-tasks (o /speckit-analyze cruza artefatos e não o código): FR-032 (Performance da Home; 'ranking e meta do Dashboard Comercial'), cenário 40, FR-034 (campos do card por papel) e FR-036 (os quatro agregados da ficha do talento).
- Cenário 26 do verify ('API e tela antiga iguais ao centavo'): com o retido só no Top Vendedores da API, a comparação precisa ficar restrita à cascata; a divergência do painel Jinja vai para o docs/05 junto com os dois eixos de /admin/desempenho.
- Regra 'foi venda' do cancelado (venda congelada > 0, ou permuta, ou pago > 0) não tem dono: a proposta a põe no endpoint do pipeline e ela se repetiria em /admin/desempenho. Deve ser um predicado do núcleo.
- A comissão do retido no card do Comercial soma o escopo inteiro, enquanto o KPI filtra por beneficiário (app/financeiro/vendas_ops.py:284-290). Em evento EducaManto vendido por um Comercial os dois números diferem; falta decidir qual regra vale no card.
- Regressão do verify_205, que consome /api/vendas/pipeline (specs/205-loja-interacoes-virtuais/verify_205.py:1142 e :1259): `build_kpis` e `serialize_sales` mudam de assinatura e o plano não lista esse verify entre os que precisam rodar de novo.
- Contrato em docs/01 dos quatro payloads alterados (/api/vendas/pipeline, /api/admin/desempenho, /api/clientes/<id>, /api/talents/<id>) e a tela correspondente em docs/02: a proposta não lista docs a atualizar para esta frente.
- A skill `financeiro` (.claude/skills/financeiro/SKILL.md) responde 'quanto vendeu' por SQL direto no banco e não conhece a regra do retido no mês do cancelamento. Depois da 303 ela daria número diferente do Dashboard; falta ao menos registrar a regra no docs/04 e apontar da skill.

## Perguntas em aberto da frente

- Card 'Cancelamentos do período' no Dashboard Comercial, para quem é só Comercial: a FR-034 lista 'imposto' e 'efeito no resultado' entre os campos, mas a feature 196 tirou custo e lucro dessa tela de propósito, porque o Comercial não acessa o Painel Financeiro. O plano sai com o padrão mais fechado: o Comercial vê quantidade, pago, devolvido (e o que falta pagar), retido, comissão do retido e BV; imposto e efeito no resultado só para Financeiro e Superadmin. Se o dono quiser os oito campos para o Comercial, é retirar um corte no endpoint — não bloqueia o plano.