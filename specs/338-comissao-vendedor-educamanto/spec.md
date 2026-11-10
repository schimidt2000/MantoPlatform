# Feature 338 — Comissão do vendedor e lucro real no EducaManto

**Branch**: `338-comissao-vendedor-educamanto` (da `main`) · **Created**: 2026-11-06 · **Status**: Implementado na branch (verify 12/12; sem merge) ·
**Migration**: `338a` (aditiva — 4 colunas anuláveis, nenhum dado reescrito) · **Nível**: 1 (feature) —
constituição, Princípio VI

**Input**: pedido do dono, depois da conferência das comissões do Gabriel e da venda do Jundiaí Shopping
(06/11/2026).

## O pedido, nas palavras do dono *(obrigatório)*

> "A ideia é que várias pessoas usem essa calculadora do EducaManto. Aí, por exemplo, um vendedor X vai
> vender lá e coloca 2.000 acima. Ou seja, de tudo que entrou, esses 2.000 vão direto para a pessoa. É
> como se fosse um BV, só que é interno. Quando vira evento, tem que definir para quem vai. Nesse caso,
> vai para a Thaís esse 1.500 e isso não entra como lucro. Isso entra na comissão dela, porque é uma
> comissão de uma fonte diferente, que não é da venda de eventos, só que é uma comissão de fato."
>
> "Preciso então que ajuste essa regra para consertar a comissão do Gabriel. […] O que eu acho mais justo
> e mais correto é que seja sempre calculado dessa forma." — com a conferência pelo chat antes de pagar.

O sintoma, como o dono viu (05/11): duas comissões do Gabriel (responsável EducaManto) no repasse de
05/11 — R$ 1.012,50 do Jundiaí Shopping (3 dias, venda R$ 44.800) e R$ 190,00 do Colégio Santo Américo
(venda R$ 12.000, com nota) — calculadas como 5% de (venda − cachês). A conta ignorava:

- os **R$ 1.500** que a Thaís pôs no campo "Comissão do vendedor" da calculadora (orçamento nº 34,
  14/08). O valor ficou só no orçamento: não virou comissão dela e entrou como lucro na base do Gabriel;
- os **gastos extras aprovados** do evento (R$ 3.313,65 no Jundiaí; R$ 659,87 no Santo Américo);
- o **imposto da nota** (16% no Santo Américo).

Decisões do dono (06/11): a comissão do vendedor entra no ciclo do **mês do evento**; o **imposto sai** da
base do responsável quando o evento tem nota; no **cancelado**, a comissão do vendedor fica
**proporcional ao retido**, como a do responsável e o BV.

## Clarifications

### Session 2026-11-06

- Q: Em que mês a comissão do vendedor EducaManto entra para pagamento? → A: no mês do **evento**, como a do
  responsável (Jundiaí, 03/10 → repasse de 05/11). Aplicado em FR-003.
- Q: O imposto da nota sai da base da comissão do responsável quando o evento tem nota? → A: **sim**, a
  alíquota da DRE sobre a venda (Santo Américo: R$ 157,01 → R$ 61,01). Aplicado em FR-001.
- Q: No cancelado, o que acontece com a comissão do vendedor? → A: **proporcional ao retido**, como a do
  responsável e o BV. Aplicado em FR-005.

## Cenários e Verificação *(obrigatório)*

### História 1 — A comissão do responsável sobre o lucro real (Prioridade: P1)

O Financeiro abre Comissões ou a Planilha de Pagamentos e vê a comissão do responsável EducaManto
calculada sobre o que de fato sobrou do evento: a venda menos BV, cachês, gastos extras aprovados,
imposto da nota (quando há nota) e a comissão do vendedor.

**Por que esta prioridade**: é o número que vai ser pago ao Gabriel no repasse de 05/11, que está em
aberto.

**Verificação**: cenários 1 e 2 do `verify_338.py` — os dois eventos reais do espelho dão os números da
conferência.

**Cenários de aceite**:

1. **Dado** o Jundiaí Shopping (venda R$ 44.800, sem nota, cachês R$ 24.550 nos três dias, gastos extras
   aprovados R$ 3.313,65) com vendedora Thaís e comissão do vendedor R$ 1.500, **Quando** a comissão é
   calculada, **Então** a do Gabriel é 5% × 15.436,35 = **R$ 771,82**.
2. **Dado** o Santo Américo (venda R$ 12.000, com nota, cachês R$ 8.200, gastos aprovados R$ 659,87, sem
   comissão do vendedor), **Quando** a comissão é calculada, **Então** a do Gabriel é 5% ×
   (12.000 − 1.920 − 8.200 − 659,87) = **R$ 61,01**.
3. **Dado** um gasto extra **pendente** ou **rejeitado** no evento, **Quando** a comissão é calculada,
   **Então** ele não entra; aprovado depois, entra enquanto a comissão estiver a pagar.

---

### História 2 — A comissão do vendedor EducaManto (Prioridade: P1)

Quem fecha a venda informa no card Comercial do evento EducaManto a comissão do vendedor que entrou no
preço pela calculadora. Ela vira uma linha de comissão do vendedor do evento, separada da comissão do
responsável, a pagar no repasse do mês do evento. O valor não conta como lucro.

**Por que esta prioridade**: sem ela, a Thaís não recebe os R$ 1.500 e o Gabriel continua recebendo 5%
sobre eles.

**Verificação**: cenários 3 a 7 do `verify_338.py`.

**Cenários de aceite**:

1. **Dado** um evento EducaManto com responsável configurado e vendedora que recebe comissão, **Quando** o
   Comercial informa R$ 1.500 na comissão do vendedor e salva, **Então** nasce uma linha de comissão de
   R$ 1.500 da vendedora, a pagar, no ciclo do mês do evento, e a do responsável cai na mesma medida
   (5% × 1.500 = R$ 75).
2. **Dado** a linha do vendedor a pagar, **Quando** o valor muda ou o vendedor é trocado, **Então** a
   linha acompanha; **quando** o valor é apagado, **Então** a linha a pagar é cancelada.
3. **Dado** a linha do vendedor **paga**, **Quando** o valor muda, **Então** a linha paga não muda.
4. **Dado** um vendedor que não recebe comissão (ou evento sem vendedor), **Quando** o valor é informado,
   **Então** nenhuma linha nasce e o valor não sai da base do responsável.
5. **Dado** o valor acima da venda, **Quando** salva, **Então** a API recusa com "A comissão do vendedor
   não pode passar do valor da venda." no campo.
6. **Dado** a DRE do mês do evento, **Quando** é aberta, **Então** as comissões somam a do responsável e a
   do vendedor.

---

### História 3 — No cancelado, as duas comissões acompanham o retido (Prioridade: P2)

O Superadmin cancela um evento EducaManto que tinha comissão do vendedor. O ato congela o vendedor e o
valor; a comissão do vendedor passa a ser valor × retido ÷ venda (teto no valor), na mesma regra da
comissão do responsável e do BV. A correção do retido refaz as duas.

**Por que esta prioridade**: cancelamento de EducaManto é raro, mas sem a regra o ato zeraria a linha do
vendedor (a reconciliação da 306 dá alvo 0 a quem não é o beneficiário congelado).

**Verificação**: cenário 8 do `verify_338.py`.

**Cenários de aceite**:

1. **Dado** um evento EducaManto com venda R$ 10.000, comissão do vendedor R$ 1.000 e R$ 5.000 recebidos,
   **Quando** é cancelado sem devolução, **Então** a linha do vendedor vai a R$ 500 e a do responsável à
   cheia × 50%.
2. **Dado** o cancelado, **Quando** a comissão do vendedor é alterada no card Comercial, **Então** a API
   recusa com 409 `cancelado` (o valor é do ato).

---

### História 4 — As telas mostram de onde vem cada comissão (Prioridade: P3)

Em Comissões e na Planilha de Pagamentos, a linha do vendedor aparece como "Comissão do vendedor
(EducaManto)". No card Comercial do evento EducaManto, o campo "Comissão do vendedor" aparece junto dos
dados da venda.

**Verificação**: conferência de tela (Browser pane), card Comercial e Comissões.

### Casos de borda

- **Vendedor = responsável**: duas linhas para a mesma pessoa, uma de cada fonte; o resumo por vendedor
  conta o evento uma vez.
- **Comissão do vendedor maior que o lucro**: o vendedor recebe o valor inteiro (é dinheiro que o cliente
  pagou para ele); a base do responsável vai a zero.
- **Venda "a definir"**: sem venda, nenhuma das duas comissões existe; o valor fica gravado.
- **Evento de grupo**: o valor mora no principal (é campo de venda, sai do satélite ao agrupar) e passa ao
  novo 1º dia na passagem da venda; os gastos extras somam os dias vivos.
- **Corte de um dia**: a base do responsável perde o cachê e os gastos extras do dia cortado.
- **Cortesia/permuta e Loja Virtual**: nenhuma comissão, como hoje.
- **Devolução ao cliente** (Gasto Extra de devolução): fica fora da base — no cancelado ela já está
  descontada no retido.
- **Evento deixa de ser EducaManto** (título muda no Google) ou responsável é retirado em Configurações: a
  linha do vendedor a pagar é cancelada; o valor fica gravado e é ignorado.
- **Comissão paga**: nunca é reescrita (histórico), nos dois tipos de linha.

## Requisitos *(obrigatório)*

### Requisitos funcionais

- **FR-001**: A base da comissão do responsável EducaManto DEVE ser venda − BV − cachês dos dias vivos −
  gastos extras **aprovados** ligados aos dias vivos, de qualquer data (fora a devolução) − imposto da nota
  (alíquota de Configurações, padrão 16%, sobre a venda, só com nota) − comissão do vendedor (só quando há
  quem a receba). Taxa e piso de zero como hoje; um arredondamento só, no fim (`ROUND_HALF_UP`, 2 casas).
- **FR-002**: O evento EducaManto (principal) DEVE ter o campo "Comissão do vendedor" (R$, opcional, de 0
  até a venda), salvo pelo card Comercial com o gate de hoje desse card.
- **FR-003**: Com valor > 0, venda > 0 sem cortesia/permuta, evento EducaManto com responsável, vendedor
  que recebe comissão e evento vivo, o sistema DEVE manter uma linha de comissão do vendedor do evento,
  marcada como de fonte própria, com o valor (teto na venda), a data da venda e a liberação no dia do
  evento; enquanto a pagar, acompanha valor e vendedor; sem quem receba, a pagar vira cancelada; paga ou
  no banco nunca muda.
- **FR-004**: A DRE DEVE somar a comissão do vendedor nas comissões do evento (mês do evento), e a
  comissão prevista do Dashboard Comercial DEVE somá-la — em "Minhas vendas", para o próprio vendedor.
- **FR-005**: O cancelamento (regime venda) DEVE congelar vendedor e valor e levar a linha do vendedor a
  valor × retido ÷ venda (teto no valor), pela reconciliação por beneficiário da 306, separada da linha do
  responsável; a correção do retido e a troca de vendedor no cancelado DEVEM refazê-la. Linha do vendedor já
  paga acima do alvo vira ajuste negativo no primeiro repasse aberto, como na 306. A comissão do vendedor
  do retido DEVE entrar nas comissões da DRE pelo mês do cancelamento.
- **FR-006**: No cancelado, alterar a comissão do vendedor DEVE ser recusado com 409 `cancelado` para todos.
- **FR-007**: Comissões e a Planilha de Pagamentos DEVEM identificar a linha do vendedor; o card Comercial
  DEVE mostrar o campo só em evento EducaManto com responsável; o KPI "Comissão" do detalhe DEVE mostrar a
  do responsável e, à parte, a do vendedor (hoje somaria as duas).

### Entidades *(se houver dados)*

- **CalendarEvent.educamanto_seller_commission** (`NUMERIC(12,2)`, anulável) — a comissão do vendedor
  posta no preço; campo de venda (some do satélite, passa na passagem).
- **CommissionPayment.source** (`VARCHAR(30)`, anulável) — `NULL` = comissão do evento (a de sempre);
  `vendedor_educamanto` = a do vendedor.
- **EventCancellation.educamanto_seller_id** (FK `users`, sem `ondelete`) e
  **EventCancellation.educamanto_seller_commission** (`NUMERIC(12,2)`) — o congelado do ato.

### RBAC *(obrigatório se houver endpoint novo ou alterado)*

- `PATCH /api/events/<id>/comercial` — campo novo, mesmo gate de hoje (sem papel novo); no cancelado, o
  campo novo leva 409 `cancelado` para todos. Linha na tabela de `docs/01` §4.3 atualizada.

## Verificação (`verify_338.py`) *(obrigatório — Princípio VIII)*

Arquivo: `specs/338-comissao-vendedor-educamanto/verify_338.py`, contra o espelho da produção —
`manto_338`, restaurado do dump de 06/11 porque o `manto_local` está numa migration do CRM não publicada
(`research.md` R9) — com `DATABASE_URL` de `.local-db-url` do worktree, `FLASK_ENV=development`,
`MANTO_SEM_THREADS=1`. Login só por
`POST /api/auth/login`; escrita conferida por conexão separada; limpeza no `finally`.

| # | Cenário | O que prova | Deve falhar? |
|---|---|---|---|
| 1 | Jundiaí Shopping (1321) com Thaís e R$ 1.500 (sem gravar) | base nova: R$ 771,82 | não |
| 2 | Santo Américo (354) | imposto e gastos: R$ 61,01 | não |
| 3 | Comercial salva R$ 1.500 num EducaManto descartável | linha do vendedor nasce (valor, ciclo do evento, fonte); a do responsável cai R$ 75 | não |
| 4 | valor muda / vendedor troca / valor apagado | linha a pagar acompanha / é cancelada | não |
| 5 | linha do vendedor paga e valor muda | paga intacta | não |
| 6 | vendedor sem comissão | nenhuma linha; base cheia | não |
| 7 | valor acima da venda; papel sem acesso ao card | 400 no campo; **403** | **sim** (403) |
| 8 | cancelamento com 50% retido | vendedor R$ 500; responsável cheia × 50%; 409 ao alterar | não |
| 9 | DRE do mês | comissões = responsável + vendedor | não |
| 9b | comissão comum (evento não EducaManto do espelho) | o número de hoje, ao centavo (SC-003) | não |
| 10 | limpeza | eventos, linhas e usuários descartáveis apagados | — |

Conferência de tela: card Comercial de um evento EducaManto (campo novo) e Comissões (rótulo da linha), no
Browser pane, desktop.

## Critérios de sucesso *(obrigatório)*

- **SC-001**: As comissões do Gabriel do repasse de 05/11 passam a R$ 771,82 e R$ 61,01 assim que a venda
  do Jundiaí Shopping tiver a Thaís e os R$ 1.500.
- **SC-002**: A Thaís vê R$ 1.500 no repasse de 05/11 (ciclo de outubro), sem lançamento manual.
- **SC-003**: Nenhuma comissão comum (fora do EducaManto) muda de valor.

## Fora de escopo

- Ligar o orçamento da calculadora ao evento (o valor é informado no card; o orçamento não tem vínculo).
- O "Editar tudo", a criação de evento e o Jinja legado: o campo novo só existe no card Comercial.
- Conferência automática dos gastos (segue pelo chat, antes do repasse).
- Rever as outras quatro implementações divergentes de comissão (`docs/04` §Armadilhas).

## Docs a atualizar

`docs/01` (schema das 3 tabelas, contrato do `/comercial`, §4.3), `docs/02` (card Comercial, Comissões),
`docs/03` (entrada no topo), `docs/04` §2 (regra de comissão, ramo 5; invariantes do cancelado).

## Premissas

- Quem recebe a comissão do vendedor é o **vendedor do evento** (`seller_id`): no Jundiaí, trocar Roberto
  por Thaís faz parte da correção do dado, pela tela.
- O imposto usa a mesma alíquota da DRE (`SiteSetting.tax_rate`, padrão 16%) sobre a venda.
- A taxa do responsável segue a de hoje (5% ou a do evento).
