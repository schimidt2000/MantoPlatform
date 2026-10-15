<!-- ADAPTADO PARA A MANTO (2026-09-08) — reaplicar após qualquer atualização do Spec Kit; para este
     arquivo o hash em .specify/integrations/speckit.manifest.json deixa de conferir de propósito. -->
# Feature 305 — O BV do orçamento chega ao evento no valor certo, com quem recebe e o PIX

**Branch**: `305-bv-do-orcamento-no-evento` (da `main`) · **Created**: 2026-10-14 · **Status**: Rascunho ·
**Migration**: nenhuma (`bv_recipient` e `bv_pix` já são colunas de `event_acrescimos`,
`app/models.py:1863-1864`) · **Nível**: 1 (feature) — escreve em dois domínios (`app/calendar/` e
`app/orcamento/`) e cria regra nova de campo obrigatório com recusa em três contratos de escrita

**Input**: pedido do dono: item 3a do backlog de setembro ("BV do orçamento chega ao evento", apelido
"099b"). Plano revisado em nove rodadas de respostas: `docs/backlog/3a-bv-do-orcamento-no-evento-099b.md`
(seções 1–10; nenhuma dúvida aberta). Decisões D2 e D15 em `docs/PLANO_BACKLOG_SETEMBRO.md`.

## O pedido, nas palavras do dono *(obrigatório)*

O fato da triagem: **o BV do orçamento não chega ao evento.** O Novo evento manda a lista de
acréscimos vazia (`EventCreatePage.tsx:432`); quando chega por outro caminho, o % é calculado sobre a
venda cheia, que já inclui o próprio BV e a nota — no exemplo da D2, o evento grava R$ 130,95 onde quem
indicou deve receber R$ 100,00.

**D2**: "O BV é o valor em R$ que o orçamento **somou ao preço** — 10% do preço antes do BV e da nota.
Ex.: show de R$ 1.000 com BV de 10% e nota → cliente paga R$ 1.309,52, quem indicou recebe R$ 100,00."

**O que é BV** (o dono, 06/10): "BV é um extra que a pessoa que indicou a Manto cobra de um terceiro.
Aí, quando a cliente nos paga, nós repassamos o BV para o intermediador."

**Regra nova do PIX** (06/10): "É de extrema importância que, ao colocar na agenda um evento com BV,
seja obrigatório colocar o PIX de quem receberá o BV. Para que isso vá para a planilha de pagamentos."

### Clarifications (respostas do dono, transcritas — não reabrir)

- **3a-Q1 = B** (06/10): "O BV deve ser calculado e definido na calculadora de orçamento. Se o valor
  total do orçamento mudar, o BV deve acompanhar proporcionalmente." → desconto, arredondamento ou
  negociação encolhem o BV junto; o BV a pagar acompanha a venda que muda depois.
- **3a-Q2 = A, com alerta** (06/10): "Alerta sobre isso e pede para que seja preenchido com atenção o BV
  e o valor total com BV." → venda digitada à mão não cria BV sozinha; a tela alerta.
- **3a-Q3 = A** (06/10): "Deixa como está os do passado. Fazemos diferente daqui pra frente."
- **3a-Q4 = A** (06/10): "Não mexer no passado. Vamos tratar daqui para frente apenas. Todos do passado
  já foram pagos, mas não quero ter que inputar agora." → sem lista nem script; a D15 fica sem efeito.
- **3a-Q5 = B** (06/10): "Pega o valor do evento, aumenta 10%. Esses 10% acima do valor normal são o BV
  que deve ser repassado." → o % é sobre o preço antes do BV e da nota.
- **3a-Q7 = B** (13/10): "Tanto em real quanto porcentagem." → o BV lançado à mão no evento aceita os dois.
- **3a-Q8 = A, lida** (13/10): "…o intermediador fala para colocar X de BV. Aí o intermediador passa o
  valor cheio + X para a cliente. Nesse caso o valor não muda. Mas se o valor diminuir, acredito que
  deva diminuir proporcionalmente o BV." → o BV em reais acompanha a venda enquanto a pagar. **A subida
  é leitura do plano** (premissa P-38): o dono falou da descida.
- **3b-Q7** (13/10): "O acréscimo adicionado manualmente é colocado por cima de tudo no valor. E o BV é
  calculado em cima de tudo isso." → a base do BV em % inclui os outros acréscimos, antes da nota.
- **3b-Q9 = B** (13/10): o BV em reais continua na calculadora, "reformulado para funcionar com todas
  essas mudanças atuais" (é da 3b; aqui só se lê o que ela gravar).
- **1b-Q2 / Q10 / Q12** (06/10 e 13/10): BV de cancelado e a diferença de comissão que sobe depois do
  repasse são da 1b e da 1e, não desta entrega.

#### Session 2026-10-14 (`/speckit-clarify`)

Nenhuma ambiguidade crítica: as nove rodadas de respostas do backlog já fecham escopo, dinheiro, RBAC e
o passado. O único ponto que é leitura, e não palavra do dono — o BV em reais que **sobe** com a venda
enquanto a pagar (Q8) —, segue como premissa P-38, listada no `docs/backlog/README.md` entre as
"leituras que você pode contestar"; o dono mandou seguir com a 305 em 14/10 sem contestá-la. Travar a
subida, se ele pedir depois, custa ~1 tarefa.

## Cenários e Verificação *(obrigatório)*

### História 1 — Criar evento a partir do orçamento leva o BV certo, com quem recebe e o PIX (Prioridade: P1)

A comercial cria o evento pelo "Criar evento" de um orçamento com BV. O evento nasce com o BV em reais,
na proporção da venda, e com quem recebe e o PIX — obrigatórios. O BV cai na Planilha sem "⚠ falta
PIX", sai da base da comissão e entra no custo da DRE.

**Por que esta prioridade**: é o caminho comum; hoje o BV não chega por ele, e o PIX é "de extrema
importância".

**Verificação**: cenários 10–13, 31 (parte da criação), 37, 44 e 46 do `verify_305.py`.

**Cenários de aceite**:

1. **Dado** orçamento de R$ 1.000 com BV 10% e nota (total R$ 1.309,52), **Quando** a comercial cria o
   evento com venda R$ 1.309,52, quem recebe e PIX, **Então** nasce uma linha BV de **R$ 100,00**
   (`is_percent=false`, descrição "10% no orçamento #N"), recebedor e PIX gravados, `nao_pago`, e a
   comissão a pagar sai sobre 1.309,52 − 100,00.
2. **Dado** o mesmo orçamento, **Quando** a venda é R$ 1.244,04 (5% à vista), **Então** o BV é
   **R$ 95,00**, com "…, na proporção da venda" na descrição.
3. **Dado** orçamento com BV em reais de R$ 10,00 e venda 5% abaixo do total, **Então** o BV é R$ 9,50.
4. **Dado** orçamento com BV, **Quando** o pedido vem sem quem recebe ou sem PIX, **Então** 400 com os
   campos nomeados, o Google não é chamado e nenhum evento nasce. **(deve falhar)**
5. **Dado** cortesia/permuta ou "Valor a definir", **Então** nenhuma linha nasce e o PIX não é exigido.
6. **Dado** um corpo com uma lista de acréscimos inventada (BV de R$ 9.999), **Então** vale o valor do
   orçamento: a lista do navegador é ignorada.

---

### História 2 — "Vincular e aplicar" leva o mesmo BV que a criação (Prioridade: P2)

No painel Orçamento da aba Comercial, a comercial vincula um orçamento a um evento **sem venda** e
escolhe a duração. O evento recebe a venda e o BV iguais aos da criação, com quem recebe e PIX
obrigatórios. Hoje esse caminho grava R$ 130,95.

**Por que esta prioridade**: é o segundo caminho por onde o BV nasce (feature 273), e hoje grava errado.

**Verificação**: cenários 14, 31 (parte do vínculo), 32, 34, 38 e 42.

**Cenários de aceite**:

1. **Dado** evento sem venda, **Quando** vem o vínculo com aplicar 2h, quem recebe e PIX, **Então**
   nasce a mesma linha da História 1 e a frase diz "BV de R$ X para <quem recebe>"; repetir não duplica.
2. **Dado** o mesmo pedido sem os dois campos, **Então** 400, e o evento segue sem vínculo, sem venda e
   sem equipe nova. **(deve falhar)**
3. **Dado** Comercial que não é a autora reaplicando em evento ligado a orçamento de outra, **Então**
   409 `orcamento_de_outro`, sem linha (a guarda da 301 vem antes da do PIX). **(deve falhar)**
4. **Dado** duas sessões aplicando no mesmo evento, **Então** fica uma linha só.
5. **Dado** evento que já tem acréscimos, **Quando** se vincula outro orçamento, **Então** o BV fica
   intacto e o relatório avisa.

---

### História 3 — O editor de Acréscimos aceita BV à mão (R$ ou %), exige o PIX e para de estragar o BV (Prioridade: P2)

A comercial abre Acréscimos na aba Comercial, lança ou confere o BV e salva. Salvar sem mexer não
apaga o PIX nem "despaga" o BV; o % segue a régua da D2 (sobre o preço com os outros acréscimos, antes
do BV e da nota); o BV em reais entra como digitado; quem recebe e PIX são obrigatórios; a comissão a
pagar muda na mesma requisição.

**Por que esta prioridade**: o editor é a porta do BV à mão e do alerta; hoje ele apaga o PIX e
recalcula o BV sobre a venda cheia.

**Verificação**: cenários 16, 17, 35, 36, 43, 47 e a primeira metade do 49.

**Cenários de aceite**:

1. **Dado** um BV pago vindo do orçamento, **Quando** o editor é salvo sem mudança (ou com PIX vazio,
   bundle antigo), **Então** PIX, status `pago` e valor ficam iguais.
2. **Dado** venda R$ 1.309,52 com nota, **Quando** se lança BV 10% com quem recebe e PIX, **Então**
   R$ 100,00 (não R$ 130,95); com um "Outro" de R$ 300 e venda R$ 1.430 sem nota, **R$ 130,00**.
3. **Dado** BV de R$ 200 em reais numa venda de R$ 2.000 com nota, **Então** R$ 200,00 exatos.
4. **Dado** um BV sem quem recebe ou sem PIX (sem PIX anterior) no meio de uma lista válida, **Então**
   400 e as linhas de antes intactas. **(deve falhar)**
5. **Dado** um BV em % gravado como hoje (R$ 130,95), **Quando** reenviado: a pagar vira R$ 100,00;
   pago ou no banco continua R$ 130,95.

---

### História 4 — Alerta quando a venda é digitada à mão em evento ligado a orçamento com BV (Prioridade: P2)

Evento ligado a orçamento com BV que recebe a venda digitada, ou orçamento com BV vinculado a evento que
já tem venda: o BV **não** entra sozinho. A aba Comercial alerta e pede atenção ao BV e ao valor total
com BV; "Lançar o BV" abre o editor já preenchido. Só vale para evento criado ou ligado depois do deploy.

**Por que esta prioridade**: é a decisão Q2 = A — sem o alerta, o BV some calado nesses casos.

**Verificação**: cenários 15 e 45.

**Cenários de aceite**:

1. **Dado** evento com venda, **Quando** se vincula orçamento com BV, **Então** nenhuma linha nasce, a
   frase pede o lançamento em Acréscimos e o detalhe do evento traz o alerta.
2. **Dado** o alerta aceso, **Quando** o BV é lançado com quem recebe e PIX, **Então** o alerta some.
3. **Dado** evento cancelado, satélite, cortesia, "Valor a definir", orçamento personalizado ou sem BV,
   **Então** não há alerta.
4. **Dado** evento criado e ligado antes do deploy, **Então** não há alerta (Q4 = A).

---

### História 5 — O BV a pagar acompanha a venda que muda depois (Prioridade: P3)

A comercial digita uma venda nova num evento que já tem BV a pagar. Cada BV a pagar — do orçamento ou à
mão, em R$ ou % — acompanha na mesma proporção, e a tela diz o que mudou.

**Por que esta prioridade**: é a mesma Q1 = B (e Q8 = A) depois da criação; menos frequente.

**Verificação**: cenários 38, 39, 48 e a segunda metade do 49.

**Cenários de aceite**:

1. **Dado** BV a pagar de R$ 200 em venda de R$ 2.000, **Quando** a venda vai a R$ 1.800, **Então** o BV
   vira R$ 180,00 na mesma gravação, a tela diz "O BV acompanhou a venda: de R$ 200,00 para R$ 180,00.
   Confira o BV e o valor total com BV.", o histórico registra sem o PIX, e a comissão a pagar fica sobre
   1.800 − 180. De volta a R$ 2.000, o BV volta a R$ 200.
2. **Dado** BV pago ou no banco, **Então** fica intacto.
3. **Dado** a venda que vai a "Valor a definir" ou cortesia, **Então** a linha fica; na volta a um
   valor, o BV em reais fica com o aviso "confira o BV" e o em % é recalculado pela régua.
4. **Dado** só a nota muda, com a mesma venda, **Então** o BV em reais acompanha o preço (líquido);
   **dado** a nota sai com a venda caindo 16% (a cliente desistiu da nota), **Então** o BV fica.

---

### História 6 — O passado fica como está (Prioridade: P3)

Nenhum evento que já estava na agenda ganha BV, lista ou alerta; comissão paga não é reescrita.

**Verificação**: cenários 25, 45 (lado "antes do corte") e 17 (pago mantém o valor).

**Cenários de aceite**:

1. **Dado** os 3 eventos do espelho com BV no orçamento e sem linha (R$ 599,81 no total), **Então** não
   ganham linha nem alerta.
2. **Dado** comissão paga, **Quando** um BV é acrescentado depois, **Então** a comissão paga fica intacta.

### Casos de borda

- Orçamento personalizado: nenhuma linha; a tela avisa que o BV não foi somado ao preço.
- Duração acima de 4h: régua linear da calculadora (linha de 4h × horas ÷ 4, inclusive a fixa), com o
  mesmo total que o Novo evento mostra; a regra da 3b chega com a 3b.
- Criação sem duração no corpo: deduzir pelo valor (igual a um dos totais), depois pelo horário (1–4h,
  ou o personalizado); senão não grava ("duração não identificada"). Orçamento só com % não precisa.
- Entradas ruins (total zero, base ≤ 0, negativos, snapshot corrompido): lista vazia, sem exceção — a
  gravação roda depois do Google e nunca pode levantar erro.
- Meio centavo: tolerância de R$ 0,01 entre a memória do orçamento e a conta.
- Evento que já tem qualquer acréscimo: os caminhos automáticos não o tocam.
- Venda acima do total: o BV sobe junto, sem teto.
- Dois BVs (R$ e %): o em reais fica fora da base do em %.
- Bundle antigo: sem os campos novos e orçamento com BV → 400 até recarregar; sem a chave `descricao`
  → mantém a descrição; PIX vazio → mantém o PIX. Bundle novo com backend antigo é neutro.
- PIX vazio quer dizer "mantém": não existe apagar PIX, só trocar.
- Formulário Jinja de criação de orçamento com BV: recusa com aviso para usar a tela nova.
- Cancelamento (do evento ou de um dia): a conta do BV é da 1b, não desta entrega.

## Requisitos *(obrigatório)*

### Requisitos funcionais

**A conta**

- **FR-001**: O sistema DEVE calcular, a partir do orçamento congelado e da duração, o valor **cheio** de
  cada acréscimo que o orçamento somou ao preço — primeiro pelos valores em reais gravados no orçamento,
  depois pela conta inversa (líquido = total × 0,84 com nota; base = (líquido − fixos) ÷ (1 + soma dos %
  ÷ 100), **arredondada ao centavo antes do %**; linha em % = base × % ÷ 100; fixa = o digitado). No
  exemplo da D2, R$ 100,00. Os valores gravados no orçamento só valem se forem números finitos, ≥ 0 e
  não maiores que o total da duração (research R1, R2).
- **FR-002**: Orçamento personalizado DEVE devolver lista vazia; entradas ruins DEVEM devolver lista ou
  linha vazia, sem exceção.
- **FR-003**: A calculadora DEVE passar a gravar, em cada acréscimo do orçamento salvo, o valor em reais
  nas quatro durações — sem mudar o total de nenhum orçamento.
- **FR-004**: O sistema DEVE ter **uma** conta de proporção do BV (BV cheio × venda ÷ total, ao centavo,
  meio para cima; total zero → 0), reusada pela 3b e pela 2b.
- **FR-005**: O divisor da nota (0,84) DEVE ser uma constante única, sem mudar valor nenhum.

**Onde o BV nasce**

- **FR-006**: Na criação do evento a partir de orçamento, com venda de verdade (não cortesia, não
  "Valor a definir"), o sistema DEVE gravar todas as linhas do orçamento em reais, já na proporção da
  venda, com a origem na descrição, quem recebe e PIX no BV, `nao_pago`. A lista de acréscimos vinda do
  navegador DEVE ser ignorada **em toda criação**, com ou sem orçamento (senão um BV nasce sem PIX).
  Venda que difere do total em até R$ 0,01 conta como igual (BV cheio).
- **FR-007**: No "Vincular e aplicar" (273), DEVE gravar o mesmo, com a duração escolhida; o relatório
  DEVE dizer quantas linhas nasceram, o total de BV, ou por que não nasceram, e o mês da Planilha
  quando o evento é de mês anterior.
- **FR-008**: Os caminhos automáticos NÃO DEVEM tocar evento que já tem qualquer acréscimo nem evento
  cancelado; DEVEM reler o evento com trava antes de olhar as linhas (fora da criação).
- **FR-009**: Venda digitada à mão (aba Comercial, edição completa, vínculo em evento com venda) NÃO
  DEVE criar BV (Q2 = A).
- **FR-010**: Trocar ou desvincular orçamento NÃO DEVE mexer no BV existente; o relatório avisa.
- **FR-011**: O histórico do evento DEVE registrar o BV criado (valor, %, duração, proporção, quem
  recebe) — **nunca o PIX**.

**PIX obrigatório**

- **FR-012**: BV sem quem recebe ou sem PIX (texto não vazio, até 200 e 140 caracteres) NÃO DEVE ser
  gravado, e a gravação inteira DEVE ser recusada com a mensagem "Este evento tem BV: informe quem recebe
  e o PIX, para o repasse ir à Planilha de Pagamentos." — sem "sem PIX ainda", sem pendência; PIX é
  texto livre.
- **FR-013**: Na criação, a recusa DEVE vir antes de qualquer escrita no Google (400 com os campos); no
  vínculo, depois das guardas de autoria da 301 e antes de gravar qualquer coisa; no editor de
  Acréscimos (API e Jinja), antes de apagar as linhas antigas, recusando a lista inteira.

**O editor de Acréscimos**

- **FR-014**: O detalhe do evento DEVE entregar, só a quem vê o bloco comercial, a descrição e o PIX de
  cada acréscimo.
- **FR-015**: O editor DEVE casar cada linha pela **identidade** (o `id` que a tela recebeu): só da linha
  de mesmo id herdam-se o status de pagamento, o PIX quando vem vazio e a descrição quando a chave não
  vem. Com a tela nova (que manda o `id`), linha sem id é nova e nasce **a pagar**. O bundle antigo
  e o Jinja não mandam id nenhum: aí a linha antiga é achada pela chave (BV: recebedor e PIX; outros:
  tipo e valor) **só quando há uma candidata** — salvar sem mexer mantém o "pago" (SC-003), e nunca
  há promoção a "pago" com ambiguidade.
- **FR-015a**: O editor DEVE aceitar valor no formato brasileiro ("1.309,52"); valor ilegível ou tipo
  preenchido sem valor válido DEVE ser recusado na linha — nunca descartado em silêncio. "bv" é BV.
- **FR-016**: BV em % à mão DEVE ser calculado sobre o preço com os outros acréscimos, antes do BV e da
  nota (D2, 3b-Q7), e recalculado ao salvar **só se a pagar**; com a venda sem valor, o BV em % existente
  mantém o valor e um BV em % novo é recusado ("lance em reais ou depois do valor de venda").
- **FR-017**: BV em reais à mão DEVE ser gravado como digitado (Q7 = B), sem recálculo ao salvar.
- **FR-017a**: BV pago ou no banco NÃO DEVE mudar de valor pelo editor, em R$ ou em % (P-20), nem
  sair da lista ou mudar de tipo (400; desfaz-se o pagamento na Planilha); quem recebe e PIX
  continuam editáveis.
- **FR-018**: Salvar o editor DEVE sincronizar a comissão a pagar na mesma requisição.

**O alerta**

- **FR-019**: O detalhe do evento DEVE trazer o alerta "BV do orçamento pendente" quando o evento está
  ligado a orçamento com BV (não personalizado), tem venda de verdade, não tem linha de BV com valor, não está
  cancelado, não é satélite, **e** foi criado ou ligado depois do momento do deploy. Só para quem vê o
  bloco comercial, sem o id do orçamento.
- **FR-020**: A tela DEVE mostrar o alerta no painel Acréscimos, sob o valor de venda da aba Comercial e
  na edição completa, com "Lançar o BV" abrindo o editor preenchido **em reais** com o valor do
  orçamento na proporção da venda (nada gravado sem o clique); sem duração identificada, mostra o % e
  "confira a duração". A edição completa que deixa o alerta aceso avisa antes de sair da tela.

**Venda que muda depois**

- **FR-021**: Quando a venda **ou a nota** muda de um valor de verdade a outro (aba Comercial, edição
  completa e o gêmeo Jinja), cada BV **a pagar** DEVE acompanhar: em reais, na proporção do valor
  líquido (venda × 0,84 com nota) — a nota que sai com a venda caindo 16% não mexe no BV, a que entra
  ou sai com a mesma venda muda o preço e o BV acompanha —; em %, pela régua; na mesma gravação, com histórico sem PIX, comissão a pagar sincronizada e o aviso "O BV acompanhou a
  venda: de R$ Z para R$ W. Confira o BV e o valor total com BV."
- **FR-022**: NÃO DEVEM mudar sozinhos: BV pago ou no banco; a ida da venda a "Valor a definir" ou
  cortesia; na volta a um valor, o BV em reais (só o aviso "confira o BV") — o em % é recalculado pela
  régua, por ser % do preço —; evento cancelado (1b).

**Telas**

- **FR-023**: Novo evento de orçamento com BV DEVE mostrar o BV na duração escolhida e, quando ele vai
  nascer, os campos **obrigatórios** "Quem recebe o BV" e "PIX de quem recebe"; com venda diferente do
  total, avisar que o BV acompanha na mesma proporção, "calculado ao salvar". Nenhuma conta de dinheiro
  no navegador.
- **FR-024**: O painel Orçamento DEVE mostrar o chip do BV e pedir os dois campos no "Vincular e aplicar".
- **FR-025**: O painel Acréscimos DEVE mostrar a origem, a régua do % do BV, os dois exemplos da ajuda, e
  os campos obrigatórios nas linhas BV; linha BV nova nasce em %.

**Reuso sem mudar código**

- **FR-026**: O BV gravado DEVE sair da base da comissão e entrar no custo da DRE e na Planilha (com
  recebedor, PIX e sem "falta PIX"), pelas consultas que já existem. Esta entrega não reescreve comissão
  paga nem no banco.

### Entidades *(se houver dados)*

- **Acréscimo do evento** (`EventAcrescimo`, `app/models.py:1841-1875`): tipo, descrição (origem),
  `is_percent`, `value`, `amount_brl` (o R$ congelado), `is_bv`, `bv_recipient`, `bv_pix`,
  `bv_payment_status` (`nao_pago | pago | no_banco`). Sem coluna nova.
- **Orçamento** (`OrcamentoHistory`): totais por duração e `form_snapshot.acrescimos`; chave nova
  opcional `valores_brl` em cada acréscimo (JSON, sem migration).
- **Evento** (`CalendarEvent`): venda, valor antes do desconto, nota, cortesia, orçamento ligado,
  cancelado, satélite, `created_at` (corte do alerta).
- **Histórico** (`EventLog`): "Vinculou o orçamento #N" decide o corte do alerta; ganha as frases do BV.

### RBAC *(obrigatório se houver endpoint novo ou alterado)*

Nenhuma rota nem papel novo; a tabela de `docs/01` §4.3 não muda.

- `GET /api/events/new/prefill` — Comercial, Superadmin; demais 403.
- `POST /api/events` — Comercial, Superadmin; Financeiro e demais 403; **400 do PIX antes do Google**.
- `PATCH /api/events/<id>/orcamento` — Comercial, Financeiro, Superadmin; ordem: 404 → 403 → 409
  satélite → autoria 301 (409/404) → **400 do PIX**.
- `PUT /api/events/<id>/acrescimos` — Comercial, Financeiro, Superadmin; 404, 403, 409 satélite, 401 sem
  sessão, **400 do PIX** sem apagar.
- `PATCH /api/events/<id>/comercial` e `PATCH /api/events/<id>` — Comercial, Superadmin (com a checagem
  do 215b antes); sem poder novo; só regravam o BV a pagar.
- `GET /api/events/<id>` — acréscimos e venda só para quem vê o bloco comercial (Comercial, Financeiro,
  Superadmin); demais sem o bloco.
- Marcar BV pago na Planilha — Financeiro, Superadmin; Comercial 403.

## Verificação (`verify_305.py`) *(obrigatório — Princípio VIII)*

Arquivo: `specs/305-bv-do-orcamento-no-evento/verify_305.py`, contra `manto_local` (`DATABASE_URL` de
`.local-db-url`, `FLASK_ENV=development`, `MANTO_SEM_THREADS=1`), Google dublado. Login só por
`POST /api/auth/login`; requisições fora do `app_context`; escrita conferida por conexão separada;
limpeza no `finally`. Eventos R&I (nunca SHOW: cria ensaio e e-mail). O verify fixa a constante do
corte antes de criar eventos. Numeração do plano (28, 29, 30 e 41 saíram com o script do passado).

| # | Cenário | O que prova | Deve falhar? |
|---|---|---|---|
| 1 | D2: R$ 1.000 + 10% + nota = 1.309,52 → BV 100,00 | a conta inversa | não |
| 2 | BV % sem nota, com fixo e outro % juntos | base comum dos % | não |
| 3 | BV fixo em R$ em 1h e 4h | valor cheio | não |
| 4 | Duração extra (6h) | régua linear pré-3b | não |
| 5 | Personalizado com BV | lista vazia | não |
| 6 | Paridade com a memória (15 orçamentos, 4 durações) | tolerância R$ 0,01 | não |
| 7 | Orçamento novo salvo traz `valores_brl`; recalcular não muda total | FR-003 | não |
| 8 | Prefill traz os 4 valores; chave antiga continua | leitura | não |
| 9 | Detalhe traz descrição e PIX para Comercial; Casting sem o bloco | leitura/RBAC | não |
| 10 | Criação com BV 10%, 2h, venda = total | linha cheia, comissão sobre venda − BV | não |
| 11 | Criação com lista inventada no corpo | vale o orçamento | não |
| 12 | Criação com venda 5% abaixo | 147,50 → 140,13 | não |
| 13 | Cortesia e "Valor a definir" | sem linha, sem 400 | não |
| 14 | Vincular e aplicar 2h com PIX | mesma linha; não duplica | não |
| 15 | Vínculo em evento com venda; "a definir" que recebe valor; cancelado | sem linha, alerta | não |
| 16 | Editor reenviado como carregou (e PIX vazio) | PIX e pago preservados | não |
| 17 | BV à mão 10%: 100,00; com "Outro" 130,00; R$ 50 junto (mutação 134,55 quebra); 130,95 legado | régua da D2 | não |
| 18 | Planilha como Financeiro | recebedor, PIX, sem "falta PIX" | não |
| 19 | Prefill como Casting | 403 | **sim** |
| 20 | Criação como Financeiro | 403 | **sim** |
| 21 | Editor como Casting; em satélite | 403; 409 | **sim** |
| 22 | Vínculo como Casting | 403 | **sim** |
| 23 | Evento sem orçamento, com uma lista de acréscimos (BV sem PIX) no corpo | lista ignorada, sem linha | não |
| 24 | Orçamento sem acréscimos | igual a hoje | não |
| 25 | Comissão paga com BV acrescentado depois | intacta | não |
| 26 | DRE do mês do evento | CPV sobe o BV | não |
| 27 | Regressão: `verify_273`, `verify_267b`, `verify_301`, `verify_215b`, `verify_267c` | verdes | não |
| 31 | Sem PIX na criação, no vínculo e no editor; PIX de 141 caracteres | 400, nada gravado, Google não chamado | **sim** |
| 32 | Não-autora reaplica; Financeiro com orçamento alheio | 409 / 404, sem linha | **sim** |
| 33 | Editor sem sessão; BV pago como Comercial; Artista 3D e "como Casting" | 401 / 403 / sem bloco | **sim** |
| 34 | Duas gravações simultâneas | uma linha | não |
| 35 | Bundle antigo sem `descricao`; `descricao:""`; no banco | preserva / apaga / mantém | não |
| 36 | BV sem PIX no meio de lista válida (API e Jinja) | 400/rollback, linhas intactas | **sim** |
| 37 | Criação sem duração: deduz; dia inteiro com linha R$; só com % | deduz / não grava / proporção | não |
| 38 | Trocar orçamento; voltar a "a definir" e receber de novo | BV intacto; uma linha + aviso | não |
| 39 | Histórico sem PIX em criação, vínculo e B10 | rastro | não |
| 40 | Entradas ruins (pura) | lista vazia, sem exceção | não |
| 42 | Vincular e aplicar em evento de mês anterior | frase com o mês da Planilha | não |
| 43 | Gêmeo Jinja do editor (função) | igual ao PUT, inclusive a recusa | não |
| 44 | Conta da proporção: igual, 140,13, 95,00, 9,50, acima, zero | FR-004 | não |
| 45 | Alerta presente/ausente; Comercial e Financeiro; Casting sem; corte | FR-019 | não |
| 46 | Bundle antigo na criação: sem BV cria; com BV 400 | deploy cruzado | **sim** (parcial) |
| 47 | BV antigo sem PIX reenviado sem PIX; com PIX | 400; grava e preserva status | **sim** (parcial) |
| 48 | Venda muda com BV a pagar (comercial, edição completa, Jinja); pago intacto; "a definir" | FR-021/022 | não |
| 49 | BV R$ 200 à mão: exato; 1.800 → 180; volta 200 (mutação: régua do % quebra) | Q7/Q8 | não |
| 51 | Editor com "100,00" e "10,5"; valor ilegível; tipo "bv" | aceita vírgula; 400 na linha; "bv" é BV | **sim** (parcial) |
| 52 | Editor: BV novo sem id para quem já tem BV pago; dois BVs da mesma pessoa | nasce a pagar; não se fundem | não |
| 53 | Só a nota muda, venda igual | BV em R$ igual; BV em % pela régua | não |
| 54 | BV em % com venda "a definir": existente mantém; novo recusado; volta a valor recalcula o % | FR-016/022 | **sim** (parcial) |
| 55 | Comissão logo após PUT e após B10, lida por conexão separada sem abrir a Planilha | coleção atualizada (flush+expire) | não |
| 56 | "Lançar o BV" em orçamento com outro acréscimo (como o 2407) | o alerta traz o valor do orçamento em R$, não o % | não |
| 57 | BV pago fora da lista, retipado ou com outro valor | 400 sem apagar; valor congelado | **sim** |
| 58 | Converge: a constante do commit (naive) e a vazia | 1218/1236/1268 sem alerta nem linha; sem corte, nada acende pelo GET | não |
| 59 | Converge: nota diferente entre orçamento e evento (criação nos dois sentidos e alerta) | o mesmo BV de R$ 100,00 (proporção pelo líquido) | não |
| 60 | Converge: BV a pagar com valor apagado, "0", 0 ou nulo | 400 em `items.0.value`, nada apagado; linha sem tipo ignorada | **sim** |
| 61 | Converge: "1.500", "R$ 1.200", "1,309.52", 130952000000, 1e30; id infinito | 400 na linha (nunca R$ 1,50 nem 500); "1.500,00" e 1500 gravam R$ 1.500,00 | **sim** |
| 62 | Converge: o `id` de um BV pago duas vezes no PUT | 400 em `items.1.id`, nada muda | **sim** |
| 63 | Converge: BV negativo em R$ e em % | 400, comissão intacta; "Outro" negativo segue aceito | **sim** |
| 64 | Converge: "a definir" e volta pelo "Vincular e aplicar" | % recalculado sobre a venda nova; R$ fica, com "confira o BV" na frase | não |
| 65 | Converge: Jinja com o BV redigitado junto com a venda; e reenviado sem mexer | redigitado fica como digitado; reenviado acompanha | não |
| 66 | Converge: corridas (duas mudanças de venda; editor × venda), com outra transação travando o evento | BV 150 (não 180); % sobre a venda nova | não |
| 67 | Converge: marcar pago com `valor_esperado` diferente / igual / ausente | 409 sem gravar / 200 / 200 | **sim** |
| 68 | Converge: trocar o PIX de um BV pago | um `AuditLog` com o PIX mascarado; sem troca, nenhum | não |
| 50 | limpeza | registros e usuários descartáveis apagados (`roles.clear()` antes) | — |

Conferência de tela (desktop; app interno): Novo evento de orçamento com BV (quadro por duração, aviso
de proporção, campos obrigatórios e o 400 neles); painel Acréscimos (salvar sem mexer, rótulo, recusa
sem PIX, linha nova em %, BV em reais como digitado); painel Orçamento (chip, frase, campos); alerta no
painel, na aba e na edição completa num evento depois do corte, e um evento antigo sem alerta; Planilha
com recebedor e PIX.

## Critérios de sucesso *(obrigatório)*

- **SC-001**: No exemplo da D2, o evento criado do orçamento grava BV de R$ 100,00 (não R$ 130,95); com
  5% de desconto, R$ 95,00; criação e "Vincular e aplicar" dão o mesmo valor.
- **SC-002**: Nenhum BV nasce sem quem recebe e PIX depois do deploy: zero "⚠ falta PIX" em BVs novos;
  toda tentativa sem os dois é recusada sem gravar nada (na criação, sem chamar o Google).
- **SC-003**: Salvar Acréscimos sem mexer não muda PIX, status, descrição nem valor de BV: zero diferenças.
- **SC-004**: Em toda porta, a comissão a pagar fica em taxa × (venda − BV) na mesma requisição; comissão
  paga ou no banco nunca muda.
- **SC-005**: O custo da DRE do mês do evento sobe exatamente o BV, e o BV aparece na Planilha desse mês
  com recebedor e PIX.
- **SC-006**: O alerta aparece em todo evento criado ou ligado depois do deploy com orçamento com BV,
  venda digitada e sem linha de BV, e some quando o BV é lançado.
- **SC-007**: BV a pagar de R$ 200 em venda de R$ 2.000 vira R$ 180 com a venda em R$ 1.800 e volta a
  R$ 200; a tela diz o que mudou; BV pago não muda.
- **SC-008**: O passado fica intacto: os 3 eventos do espelho não ganham linha nem alerta; nenhuma
  comissão paga é reescrita.

## Fora de escopo

- Aceitar o valor do repasse vindo do navegador; recalcular o orçamento (vale o total congelado).
- BV de cancelado, conta proporcional ao retido, filtrar cancelado na Planilha: 1b.
- Diferença de comissão no próximo repasse quando a base sobe depois de paga: 1e.
- BV do passado (lista, script, alerta): Q4 = A.
- Guardar recebedor ou PIX no orçamento; sugerir o recebedor pelo "Quem indicou?": 6a.
- Aceitar "sem PIX ainda"; validar formato do PIX; teto do BV na subida.
- Criar BV sozinho quando a venda é digitada (só o alerta).
- O escalar `acrescimo_value` e o campo "Acréscimo (R$)"; limpar o Jinja (o `acrescimos_json` fica,
  ignorado); migration ou coluna "veio do orçamento".
- Dívidas registradas, não resolvidas: BV de evento que vira satélite; BV não prende a exclusão; lucro do
  painel Financeiro sem BV; id do acréscimo muda a cada salvamento; corrida da criação (273).
- Botão de PIX à vista (3b-Q2 = C); contratação Manto do EducaManto (2b); portal e público.

## Docs a atualizar

`docs/01` (contratos do prefill, do `PUT` de acréscimos, de `POST /api/events` e `PATCH …/orcamento`
com `bv_recipient`/`bv_pix`, relatório do vínculo, `venda.orcamento.bv`, `venda.bv_do_orcamento_pendente`,
`aviso_bv`); `docs/02` (Novo evento, aba Comercial — deixar de dizer "BV em leitura" —, alerta);
`docs/03` (entrada no topo: Q4 = A sem retroativo, o corte do alerta, o cenário 4 da `specs/103` que
nunca valeu no React); `docs/04` (corrigir "só o Jinja escreve acréscimos"; invariantes do BV); `docs/05`
(riscar o que toca acréscimos; cinco dívidas novas).

## Premissas

Legenda: **[P]** premissa do plano, não decisão do dono; **[D]** decisão do dono; **[P sobre D]** leitura
do plano sobre uma decisão. Numeração do plano.

- P-2 **[P]** Quem calcula é o servidor; do navegador vêm só quem recebe e o PIX (deploy cruzado, bundle
  em cache).
- P-3 **[P]** A linha chega em reais (`is_percent=false`), com a origem na descrição, já na proporção.
- P-4 **[P]** Duas fontes para o valor: `valores_brl` e a conta inversa; a memória só confere no verify.
- P-5 **[P]** Vão todas as linhas do orçamento, com o mesmo fator; as que não são BV são registro.
- P-6 **[P]** Orçamento personalizado não leva acréscimo; a tela avisa.
- P-7 **[P sobre D: Q1 = B, 3b-Q7, 3b-Q9 = B]** O BV fixo em reais segue o que a calculadora somou e
  acompanha a venda, como o em %.
- P-8 **[D: Q2 = A]** Cortesia e "Valor a definir" nascem sem acréscimo; venda digitada depois só alerta.
- P-9 **[P]** Evento que já tem qualquer acréscimo não é tocado pelos caminhos automáticos.
- P-10 **[D: regra do PIX]** Quem recebe e PIX entram onde o BV nasce e são obrigatórios; não entram no
  orçamento.
- P-11 **[P]** O conserto do editor (PIX apagado, BV "despago") entra neste item.
- P-12 **[P]** O editor de Acréscimos passa a sincronizar a comissão na hora.
- P-14 **[P sobre D: Q2 e Q4 = A]** Orçamentos com BV sem evento ligado ficam até alguém vincular; o
  vínculo depois do deploy acende o alerta.
- P-16 **[P]** A Planilha não muda (consultas, mês pela data do evento).
- P-17 **[P]** Sem conta de dinheiro no navegador: "calculado ao salvar".
- P-19 **[P]** Divisor 0,84 como constante única.
- P-20 **[P]** BV pago ou no banco não muda; a venda que sobe depois do repasse ao parceiro não gera
  diferença sozinha.
- P-22 **[D: 1b-Q2, Q10]** Evento cancelado nunca recebe BV automático.
- P-26 **[P]** No editor: PIX vazio = mantém; BV pago continua editável; o id muda a cada salvamento.
- P-28 **[P sobre D: Q4 = A]** Evento retroativo criado agora, ou vínculo em evento sem venda de mês
  fechado, põe o BV na Planilha e na DRE daquele mês; a frase diz o mês.
- P-29 **[P]** Rollback é reverter o commit.
- P-30 **[P sobre D: Q1 = B]** A proporção vale para os dois lados (venda acima do total faz o BV subir),
  sem teto.
- P-31 **[D: regra do PIX]** Obrigatório quer dizer obrigatório: sem pendência; PIX é texto livre.
- P-32 **[P]** O BV antigo sem PIX (1 linha) fica até alguém salvar os Acréscimos daquele evento.
- P-33 **[P]** O formulário Jinja de criação não ganha os campos e recusa com aviso.
- P-34 **[P]** Deploy cruzado: backend novo com bundle antigo recusa criar de orçamento com BV até
  recarregar a página.
- P-36 **[P sobre D: Q4 = A]** "Não mexer no passado": evento criado e ligado antes do deploy não ganha
  linha nem alerta; a comissão a pagar desses eventos fica como está; a linha existente só segue as
  regras novas quando alguém age no evento, e só muda se a pagar.
- P-37 **[P sobre D: Q7 = B, 3b-Q9 = B]** No editor, a linha BV nova nasce em %; o BV em reais fica fora
  da base do em %.
- P-38 **[P sobre D: Q8 = A]** O "caso normal" do intermediador é a proporção com a venda parada; a
  **subida** é leitura (travar na subida custaria ~1 tarefa).
