# Proposta para a spec 303: evento cancelado na DRE com o retido (+400) no lugar do −600, e como sinalizar e filtrar cancelados

Spec: `specs/303-sync-nao-apaga-venda/spec.md`. Não editei nada, não acessei banco nem Google. Conferi no código os pontos em que a proposta se apoia.

**Premissas do exemplo:**
- Evento em 15/11/26, cancelado em 29/09/26. C = cachês escalados. Sem nota, salvo onde digo.
- A taxa de 5% tem de estar gravada no próprio evento. O padrão do código é 2,5% (`app/financeiro/comissoes_ops.py:576`, `:590-596`); com ele, a comissão cheia seria 45 e a do retido, 9.
- O imposto de 16% é o padrão do código (`app/financeiro/routes.py:112`), mas é configurável (`:129-132`).

---

## 1. O desenho do retido na DRE

### 1.1 Linha a linha (igual na tela nova e na antiga)

| Linha | Hoje, com o cancelado | Proposta |
|---|---|---|
| Receita Bruta | O evento sai inteiro (`app/api/financeiro_read.py:233`; `routes.py:282`) | Soma o **retido** = pago − soma de todas as devoluções = 400, numa linha própria "↳ Retido de cancelamentos (pago − devolvido)" |
| Impostos | 16% × venda, só com nota (`routes.py:219-222`); sai com o evento | Depende da D3. Na recomendação, 16% × retido se o evento era "com nota" |
| CPV | Cachês + BV (`routes.py:225-227`); sai com o evento | Soma o **BV que conta**: o negociado (40) ou, se o BV já tinha sido pago, o valor pago (FR-019). Os cachês do cancelado continuam fora |
| Comissões | Fórmula `_event_commission` (`routes.py:231`); sai com o evento | Soma a **comissão do retido** (18), lida do valor congelado no cancelamento (FR-016; Entidades `spec.md:449-452`), nunca recalculada |
| Gastos Extras | Soma todo gasto aprovado, sem olhar categoria (`financeiro_read.py:243-250`; `routes.py:294-301`). A devolução nasce aprovada (`app/calendar/cancel_ops.py:174-189`) e **é daí que vem o −600** | Deixa de somar gasto da categoria "Devolução a cliente" ligado a evento cancelado. Ele já está descontado no retido |
| Estorno e desconto da comissão | Nunca chega à DRE (ela não lê `CommissionPayment`) | Continua fora. O desconto de 72 no próximo repasse é acerto de caixa na Planilha; a DRE é por competência |
| Mês do evento (novembro) | Perde tudo | Continua sem nada. O evento não volta para lá, senão conta duas vezes |

**Em que mês cada valor cai:**
- Retido, imposto, BV e comissão do retido caem **todos no mesmo mês**: o do cancelamento (`cancelled_at`), se o dono escolher a opção recomendada da D1.
- A devolução não cai em mês nenhum da DRE.
- A Planilha segue os eixos dela (BV no mês do evento, cenário 4.4; comissão no ciclo). Os meses diferem de propósito, mas o valor por evento tem de bater (FR-020 alterada, abaixo).

**Realizado × Projetado:**
- O retido entra em **Realizado e Total**, nunca no Projetado. Como `cancelled_at ≤ agora`, o dinheiro já está no caixa.
- É a mesma regra que hoje manda gastos extras e pessoal só para o Realizado (`financeiro_read.py:262-264`).
- A nota de rodapé passa a mencionar cancelamentos (`FinanceiroDashboardPage.tsx:410-414`; `dashboard.html:199-202`).

**Por que o retido líquido, e não "+1.000 recebido e −600 devolvido":**
- O `EventPayment` não tem data de competência; o `created_at` só serve para ordenar (`app/api/agenda_read.py:903`).
- O complemento de devolução da FR-015a nasce em outra data e cairia em outro mês.
- O retido líquido é o mesmo número que o evento mostra (FR-014).

### 1.2 Onde mora o código

1. **Resumo do cancelado, por evento.** Uma função única em `cancel_ops`, ao lado de `total_recebido` (`cancel_ops.py:47-54`). Ela devolve pago, a lista de devoluções, o devolvido, o retido (nunca negativo), a comissão do retido e o BV que conta.
   - Tem de somar **todas** as devoluções. A `_devolucao` atual pega só a primeira (`.first()`) e exige destinatário "cliente" (`cancel_ops.py:339-350`).
2. **Helpers do período, chamados pelas duas views:**
   - `cancelamentos_do_periodo`;
   - gastos extras do período sem as devoluções de cancelado;
   - tendência filtrada.
3. **`_compute_drg` ganha um parâmetro opcional `cancelados`**, vazio por padrão. Assim o Projetado e qualquer outro chamador ficam como estão. Ele passa a devolver também `retido_cancelamentos` e `n_cancelados`.

Por que um helper comum: a API **copia** o corpo do Jinja em vez de reusá-lo (`financeiro_read.py:225-264` × `routes.py:274-319`). A docstring de `financeiro_read.py:188-189`, que diz "sem duplicar", está errada.

**Tela antiga (Jinja):**
- Os números vêm dos helpers.
- Ganha uma única `<tr>` com a linha do retido em `dashboard.html`.
- O ticket médio tem de ser corrigido: ele divide a Receita Bruta da cascata pelo número de eventos (`routes.py:327-330`), e o retido o inflaria.
- Nada de card, botão ou linhas de cancelado na tela antiga.

### 1.3 Os indicadores ao redor

- **Dentro, porque dependem do resultado:** margens, custo de talento ÷ receita (`financeiro_read.py:296`), Fator R (`:303`) e break-even (`:298-300`). É o precedente da Loja Virtual (`:272-273`). No exemplo:
  - o Fator R ganha +400 no denominador;
  - o break-even ganha +360 de lucro bruto e +18 de custo fixo.
- **Fora, porque são indicadores de evento:** ticket médio, "a receber" e Top Vendedores (`:287-295`, `:306-318`, `:348-363`). Eles já saem de `eventos_com_venda`.
- **Receita por Tipo:** ganha a barra "Retido de cancelamentos", como a da Loja Virtual (`:341-342`), para as barras continuarem batendo com a receita.
- **Tendência:**
  - hoje ela **não filtra** o cancelado (`financeiro_read.py:369-373`; `routes.py:399-403`);
  - passa a filtrar;
  - o retido entra na receita e no lucro do mês em que a cascata o lança, sem contar como evento.

### 1.4 A DRE do exemplo, linha a linha

Contribuição deste evento. Pessoal e recorrentes não mudam.

| Linha | Set/26 hoje | **Set/26 depois** | Nov/26 hoje (já cancelado) | Nov/26 depois |
|---|---|---|---|---|
| Receita Bruta | 0 | **+400** | 0 | 0 |
| ↳ Retido de cancelamentos | — | **400** | — | — |
| Impostos | 0 | **0** (64 se "com nota", pela D3) | 0 | 0 |
| Receita Líquida | 0 | **+400** (336) | 0 | 0 |
| CPV (cachês + BV) | 0 | **40** (BV negociado) | 0 | 0 |
| Lucro Bruto | 0 | **+360** (296) | 0 | 0 |
| Comissões | 0 | **18** | 0 | 0 |
| EBITDA | 0 | **+342** (278) | 0 | 0 |
| Gastos Extras | **600** | **0** | 0 | 0 |
| **Resultado Líquido** | **−600** | **+342** (+278 com nota) | 0 | 0 |
| Colunas | Realizado e Total | Realizado e Total; Projetado 0 | — | — |

A diferença entre +342 e −600 é de R$ 942.

**O que continua igual:** antes do cancelamento, novembro mostrava 2.000 / C + 200 / 90 / contribuição 1.710 − C, no Projetado e no Total. Isso já some hoje e continua sumido.

**Tendência:**
- 09/26 mostra receita +400 e lucro +400, com o número de eventos inalterado.
- 11/26 deixa de mostrar +2.000 / +C / +1 evento (a janela é ancorada em hoje, `financeiro_read.py:366`).

**Card novo:** "1 cancelado · pago 1.000 · devolvido 600 (a pagar) · retido 400 · comissão 18 · BV 40 · efeito +342".

**Linha na tabela "Eventos no Período"** (com o botão ligado): Cancelado · Receita 400 · Custo 0 · Lucro 400 · Comissão 18. O custo é 0 porque a tabela usa a régua das linhas vivas, que é só cachês (`:401`, `:418`).

---

## 2. Decisões que só o dono pode tomar

**D1. Em que mês o retido entra na DRE?** (Está em aberto: a spec adiou, `spec.md:544-547`.)
- **(A, recomendada) No mês do cancelamento, em Realizado e Total.** O dinheiro já está no caixa, e é no mês do cancelamento que o −600 aparece hoje; o +342 toma o lugar dele, no mesmo mês.
- (B) No mês do evento, seguindo o regime atual por data do evento. Num evento futuro, o retido cai num mês que ainda não aconteceu (no exemplo, novembro), e cancelar um evento passado reescreve aquele mês.

**D2. Onde sinalizar e filtrar os cancelados?**
- **(A, recomendada) Card sempre visível e listas sob pedido.**
  - DRE e Dashboard Comercial ganham um card "Cancelamentos do período", como o da Loja Virtual (`vendas_ops.py:222-235`).
  - A agenda (Mês, Lista e Dia), a tabela "Eventos no Período" e a lista de vendas ganham o botão "Mostrar cancelados", desligado por padrão (padrão `incluir_loja_virtual`, `financeiro_read.py:279-284`). O cancelado aparece riscado, com o selo "Cancelado".
  - Onde ele já aparece hoje (busca, ficha da cliente, ficha do talento), aparece sempre com o selo.
  - O relatório `/events/cancelamentos` ganha o retido, e o Financeiro passa a lê-lo.
- (B) Só o relatório `/events/cancelamentos` enriquecido, e selo onde o cancelado já aparece; nenhum botão novo.
- (C) Cancelados sempre visíveis, riscados e no fim das listas, sem botão.

Por que A: repete o padrão da Loja Virtual. Quem abre a tela sem escolher nada continua vendo os números limpos, e o sinal está sempre lá.

**D3. O retido paga imposto provisionado na DRE?**
- **(A, recomendada) Sim, pela régua do evento vivo:** 16% × retido quando o evento era "com nota". No exemplo com nota, −64 e resultado +278. Por que A: a DRE fica conservadora e com uma régua só. O que fazer com a nota em si segue fora do sistema.
- (B) Não; o retido nunca provisiona imposto.
- (C) Perguntar ao contador antes do plan, usando A até a resposta.

**D4. A venda cancelada e o retido contam nos números do comercial?** Vale para o Dashboard Comercial, o Top Vendedores, `/admin/desempenho` e a ficha da cliente.
- **(A, recomendada) Não.**
  - A venda cancelada sai de "vendido" e de "cliente recorrente".
  - O retido aparece à parte, no card (venda perdida · devolvido · retido).
  - A "Comissão prevista" mostra os 18 numa sublinha, para bater com a tela de Comissões.
  - Por que A: "vendido" é venda que vai acontecer; o retido já está na DRE e na comissão. É a regra da Loja Virtual para os indicadores de evento.
- (B) O retido conta como venda do vendedor (total, ranking e meta) no mês do cancelamento.

---

## 3. Requisitos para a spec

### Bloco novo: "Cancelado nos relatórios"

- **FR-026 — Resumo único do cancelado.** O sistema DEVE calcular, numa única função, o resumo financeiro do evento cancelado:
  - venda;
  - total pago (soma dos comprovantes do próprio evento);
  - cada devolução, com valor, destinatário e estado (a pagar, no banco, paga);
  - total devolvido, somando todas as devoluções do evento;
  - retido = pago − devolvido, nunca negativo;
  - comissão do retido (FR-016);
  - BV que conta: o negociado, ou o pago quando já tinha sido pago (FR-019).

  Leem essa função, e nenhuma delas refaz a conta: a tela do evento, `/events/cancelamentos`, a DRE (tela nova e antiga), o Dashboard Comercial, a Planilha e a tela de Comissões.

- **FR-027 — O cancelado na cascata.** A DRE (tela nova e antiga) DEVE lançar o evento cancelado no mês [D1], nas colunas Realizado e Total e nunca no Projetado:
  - o retido soma na Receita Bruta e aparece na linha "Retido de cancelamentos (pago − devolvido)";
  - o BV que conta soma no CPV;
  - a comissão do retido soma nas Comissões;
  - [imposto conforme D3].

  Os cachês do cancelado ficam fora. Comissão e BV são lidos do que ficou congelado no cancelamento, não recalculados.

- **FR-028 — A devolução fora de Gastos Extras.** A devolução à cliente de evento cancelado NÃO DEVE somar em Gastos Extras da DRE, em mês nenhum.
  - A DRE a reconhece pelo vínculo com um evento cancelado e pela categoria "Devolução a cliente", nunca pelo destinatário.
  - Gasto de outra categoria ligado ao cancelado (multa, cachê à parte) continua em Gastos Extras. Devolução ligada a evento não cancelado também.
  - Na Planilha e na página Gastos Extras, a devolução continua sendo saída.

- **FR-029 — Conta uma vez só.** O cancelado NÃO DEVE voltar à DRE do mês do evento. Satélite de grupo e venda virtual cancelados NÃO geram retido.

- **FR-030 — Indicadores.** O retido DEVE entrar em margens, custo de talento ÷ receita, Fator R e break-even.
  - NÃO DEVE entrar em ticket médio, "a receber", Top Vendedores nem na contagem de eventos.
  - Na Receita por Tipo, ele aparece como a barra "Retido de cancelamentos".
  - Na tela antiga, o ticket médio DEVE deixar de dividir a Receita Bruta da cascata pelo número de eventos.

- **FR-031 — Tendência e pendências.** Nas duas telas:
  - a Tendência de 6 meses NÃO DEVE contar venda, cachê nem evento de evento cancelado, e DEVE somar o retido à receita e ao lucro do mês em que a cascata o lança;
  - "Recebimentos Previstos" NÃO DEVE listar parcela de evento cancelado;
  - a nota "a emitir" de evento cancelado DEVE continuar na lista, com o selo "evento cancelado · retido R$ X".

### Bloco novo: "Sinalizar e filtrar" (segue a D2-A)

- **FR-032 — Painel financeiro.** O painel DEVE mostrar, quando houver cancelado no período, o card "Cancelamentos do período", com link para cada evento. O card traz:
  - quantidade, pago, devolvido (e quanto ainda falta pagar), retido;
  - comissão do retido, BV e efeito no resultado.

  A tabela "Eventos no Período" DEVE ter o botão "Mostrar cancelados", desligado por padrão, que traz os cancelados com o selo "Cancelado", a receita igual ao retido e a comissão do retido.
  - "cancelado" passa a ser um estado de `event_payment_status` (`vendas_ops.py:44-66`).
  - O status da tela antiga é calculado à parte (`routes.py:437-446`) e não muda.

- **FR-033 — Dashboard Comercial.** A venda cancelada DEVE ficar fora de "Total vendido", do ticket médio e de "Eventos fechados" [D4]. O Dashboard DEVE mostrar:
  - o card "Cancelamentos do período", com venda perdida, devolvido e retido;
  - o botão "Mostrar cancelados na lista", com a cobrança "Cancelado · retido R$ X" e a comissão do retido, nunca a cheia;
  - a comissão do retido dentro da "Comissão prevista", em sublinha.

- **FR-034 — Agenda.**
  - Mês, Lista e Dia NÃO DEVEM mostrar o cancelado por padrão. Hoje o Dia mostra (`app/api/agenda.py:85-90`).
  - Com o filtro "Mostrar cancelados", guardado no endereço, ele aparece esmaecido, riscado e com a palavra "Cancelado". Não só cor: a cor do chip é da categoria.
  - A busca DEVE mostrar o cancelado sempre, com o selo.
  - Os seletores que reusam a busca (vincular ensaio, tag NFC, candidato a grupo) NÃO DEVEM aceitar evento cancelado: ele aparece bloqueado, com o motivo.

- **FR-035 — Situação única.** O resumo do evento na agenda e na busca DEVE trazer uma situação única, calculada no servidor, com precedência cancelado > sumiu do Google > exclusão solicitada. A contagem da faixa (FR-009) NÃO DEVE contar cancelado.

- **FR-036 — Tela do evento cancelado.**
  - A tela DEVE trocar a grade "Resultado" por "Resultado do cancelamento": pago, devolvido, retido, comissão do retido e BV.
  - Hoje a grade mostra lucro de 1.200 − C, porque desconta a devolução e o BV original (`agenda_read.py:374-400`).
  - A faixa de pendências DEVE mostrar a devolução e o retido, em vez de "R$ 1.000,00 em aberto".
  - "Sincronizar" e "Editar no Google Agenda" NÃO DEVEM aparecer.

- **FR-037 — `/events/cancelamentos`.** A tela DEVE mostrar:
  - pago, cada devolução com o estado (inclusive "no banco"), retido, comissão do retido e BV;
  - filtro por mês do cancelamento e por estado da devolução;
  - total de retido do período.

  O Financeiro lê; as ações seguem só do Superadmin.

- **FR-038 — Onde o cancelado já aparece sem marca.** Ele DEVE ganhar o selo "Cancelado" e sair das somas:
  - ficha da cliente: fora de "total vendido" e da recorrência [D4], com "R$ X retidos em N cancelado(s)" à parte;
  - ficha do talento: fora de "Total faturado" (`app/talents/talent_ops.py:225-235`, `:303`);
  - coluna Evento de Gastos Extras.

  A Performance da Home (`app/api/dashboard_service.py:291-293`) e o ranking de `/admin/desempenho` (`app/api/admin_config_read.py:149-157`) NÃO DEVEM contar evento cancelado.

### Alterações no que a spec já tem

- **FR-015a:** acrescentar **categoria** ao que fica travado em Gastos Extras. Hoje a categoria é editável (`app/gastos/gastos_ops.py:410`, `:421`), e a FR-028 depende dela.
- **FR-020:** passa a valer para Planilha, Comissões, tela do evento, `/events/cancelamentos` e DRE: todas mostram o mesmo valor de comissão do retido por evento. O mês pode diferir.
- **FR-025:** acrescentar os textos que descrevem o cancelado de forma errada:
  - `app/models.py:383-389`;
  - `cancel_ops.py:10`, `:166-167` e `:246`;
  - `financeiro_read.py:188-189` e `:231-232`;
  - `vendas_ops.py:154-157`;
  - `lib/agenda.ts:300`;
  - `EventHeader.tsx:373`, que diz "Não conta em nenhuma métrica e sumiu da agenda". É falso, e "sumiu" colide com a marca "Sumiu do Google Agenda" da 303;
  - o rótulo do CPV vira "cachês + BV" (`FinanceiroDashboardPage.tsx:43`; `dashboard.html:137`).
- **História 4, `spec.md:194`:** corrigir "só aparece no mês corrente". O estorno aparece no mês da venda, pela `sale_date` (`comissoes_ops.py:299-311`), e de novo no mês corrente (`:358-372`).
- **Fora de escopo, `spec.md:544-547`:** remover o item da DRE e do Dashboard Comercial, que entra no escopo.
- **SC-007 novo:** todo cancelamento com dinheiro retido aparece na DRE do mês [D1] como retido − comissão do retido − BV [− imposto]. Nenhum mês mostra a devolução de cancelado como gasto. Todo mês sem cancelamento continua idêntico, centavo a centavo.
- **RBAC:**
  - `GET /api/events/cancelamentos` ganha FINANCEIRO, só leitura;
  - o parâmetro `incluir_cancelados` da agenda vale para quem já vê a agenda, e o payload continua sem dinheiro;
  - `/api/financeiro/dashboard` segue com FINANCEIRO e SUPERADMIN.
- **Entidades:** nenhuma coluna nova para a DRE. O retido é derivado e depende do que a FR-016 e a FR-019 congelam.
- **Docs:**
  - `docs/04`: invariante "cancelado entra na DRE pelo retido; devolução de cancelado nunca é gasto na DRE";
  - `docs/02`: DRE, Comercial, agenda e cancelamentos;
  - `docs/01`: payloads;
  - `docs/05`: dívidas da seção 4.

### Cenários novos do `verify_303.py`

A limpeza continua sendo o último cenário.

| # | Cenário | O que prova | Deve falhar? |
|---|---|---|---|
| 26 | Evento em 15/11 com venda 2.000, BV 200, `commission_rate` 5 gravado no evento, sem nota, pago 1.000; cancelado hoje com 600 devolvidos e "parceiro recebe 40". DRE do mês do cancelamento, na API e na tela antiga | Linha do retido = 400; CPV +40; Comissões +18; Gastos Extras sem os 600; Resultado +342 em Realizado e Total; Projetado 0; API e tela antiga iguais ao centavo. Contra a `main`, o mesmo cenário dá −600 (prova por mutação) | não |
| 27 | Mesmo evento: DRE de novembro e Tendência | Novembro sem receita, CPV, comissão nem evento; Tendência sem +2.000 e com +400 no mês do cancelamento | não |
| 28 | Variante "com nota" (taxa lida do `SiteSetting`) | Impostos +64, Resultado +278 [D3-A] | não |
| 29 | Devolução alterada de 600 para 800 (FR-015a), e complemento depois de paga | Retido 200, comissão 9, Resultado +151 no mesmo mês; nenhuma devolução em Gastos Extras | não |
| 30 | "Salvar" numa devolução em Gastos Extras; depois, tentativa de trocar a categoria | A DRE não volta a somar a devolução; a troca de categoria é recusada | **sim** (a troca) |
| 31 | Multa do elenco ligada ao cancelado; "Devolução a cliente" ligada a evento vivo | As duas continuam em Gastos Extras | não |
| 32 | Satélite cancelado com comprovante; venda virtual cancelada; cancelado com tudo devolvido e BV de 200 já pago | Satélite e virtual sem retido; no terceiro, retido 0, comissão 0 e CPV +200 | não |
| 33 | Ticket médio, "a receber", Top Vendedores, Receita por Tipo, Fator R e break-even, nas duas telas | Indicadores de evento sem mudança; ticket médio da tela antiga não sobe; barra do retido = 400; Fator R +400; break-even +360 / +18 | não |
| 34 | Parcelas e nota "a emitir" do cancelado | Parcelas fora dos Recebimentos Previstos; nota na lista, com o selo | não |
| 35 | Abrir Comissões e Planilha (que rodam `_resync_pending_commissions`) e depois a DRE | A comissão do retido continua 18 nas três telas | não |
| 36 | Regressão: DRE e Tendência de todos os meses sem cancelamento do espelho, `main` × branch | Idênticas, centavo a centavo | não |
| 37 | Agenda Mês, Lista e Dia sem e com `incluir_cancelados`; busca; evento marcado e depois cancelado | Escondido por padrão nas três visões; visível com a situação "cancelado"; busca sempre com o selo; nunca aparece "Sumiu" | não |
| 38 | Vincular ensaio, tag NFC e grupo a evento cancelado | Recusado, com o motivo | **sim** |
| 39 | FINANCEIRO lê `/events/cancelamentos` e tenta alterar a devolução; COMERCIAL e FIGURINO leem o relatório; COMERCIAL abre a DRE | Financeiro lê e é recusado na escrita; os outros recebem recusa ou 403 | **sim** (os recusados) |
| 40 | Payload da tela do evento cancelado e do Dashboard Comercial | Resultado do cancelamento 1.000 / 600 / 400 / 18 / 40, sem "em aberto"; "vendido" sem os 2.000; card com 1 cancelado; linha com comissão 18 | não |

---

## 4. Riscos e o que NÃO fazer

**Riscos:**
- **As duas pontas ao mesmo tempo.** Se o retido entrar e a devolução continuar em Gastos Extras, a DRE mostra 400 − 40 − 18 − 600 = −258. O cenário 26 pega isso.
- **Duas implementações.** Mudar só uma faz as telas divergirem em silêncio. O ticket médio da tela antiga (`routes.py:327-330`) sobe com o retido se não for ajustado.
- **A sincronização de comissões zera os 18.** Toda abertura de Comissões e da Planilha roda uma sincronização que cancela a comissão "a pagar" de evento cancelado (`comissoes_ops.py:816-839`, `:885-900`). Se a 303 mantiver o vínculo da linha com o evento sem isentar o cancelado, os 18 viram 0 na primeira abertura. A DRE, que lê o valor congelado, mostraria 18 e Comissões mostraria 0.
- **Recalcular em vez de congelar.** A aba Comercial do cancelado continua editável (`spec.md:452`). Se a DRE usar `_event_commission`, uma edição reescreve setembro.
- **A DRE não tem mês fechado.** Ela é recalculada do estado atual a cada abertura. Por isso:
  - a alteração da devolução pela FR-015a reescreve o mês do cancelamento;
  - cancelar um evento passado já reescreve o mês dele desde a 224.

  Registrar em `docs/04`; não construir fechamento de mês.
- **Premissas do exemplo.** 5% não é a taxa padrão, e 16% é configurável. O verify tem de gravar a taxa no evento e ler o imposto do `SiteSetting`.
- **Escopo.** A 303 já é Nível 1 e toca quatro domínios.
  - Se o plan estourar, a FR-026 a FR-031 e a FR-035 ficam na 303.
  - A FR-033, a FR-034 e a FR-036 a FR-038 podem virar uma 303b sem migration.
  - Nunca cortar a FR-028 separada da FR-027.
- **Dado de produção.** A spec registra zero uso do cancelamento da 224 (`spec.md:40`); não conferi no banco. O plan deve contar os cancelados que já existem antes do deploy.
- **Desempenho.** O resumo faz algumas consultas por evento. `/events/cancelamentos` lista até 200 (`cancel_ops.py:335`), então agrupar as consultas (lição da 300).

**O que NÃO fazer:**
- **Remoção do Jinja pausada.**
  - Não extrair nem apagar a view `dashboard()`.
  - Não mover `_compute_drg` nem `_event_commission`.
  - Não tocar `_compute_performer_caches` nem `_create_event_row` (`docs/PARADA_REMOCAO_JINJA.md:62-68`).
  - Na tela antiga entram só três coisas: os números via helper, uma linha no template e o ajuste do ticket médio.
  - A comparação `main` × branch que a parada exige para código de dinheiro (`:89-91`) é o cenário 36.
- **Na DRE:** não ler `CommissionPayment` e não lançar nela o desconto (72) nem o estorno.
- **Identificação da devolução:**
  - não usar a versão "bruta" (+1.000 recebido e −600 devolvido);
  - não reconhecer a devolução pelo destinatário, que o "Salvar" apaga (`gastos_ops.py:222-238`).
- **Agenda e busca:** não tirar o cancelado da busca, que é o único caminho do Comercial até ele, e não marcar o chip só com cor de fundo.
- **`/admin/desempenho`:** só o filtro de cancelado. A régua dele diverge também em satélite, ensaio, permuta e eixo de data; isso vai para `docs/05`.

**Fora de escopo:**
- O que fazer com a nota fiscal do cancelado.
- Marketing contar cancelado como conversão (`app/marketing/desempenho_ops.py:257`).
- Meta de vendedor.
- Fechamento de mês na DRE.
- Card "Devoluções a pagar" na Home.
- O painel Jinja de estornos, que desconta duas vezes (`routes.py:1496-1532`): não usar como modelo; vai para `docs/05`.
- `EventInstallment.received` nunca é gravado (`models.py:725`; `comercial_ops.py:237-243`), então os Recebimentos Previstos listam até o sinal já pago de evento vivo. Vai para `docs/05`, não para a 303.