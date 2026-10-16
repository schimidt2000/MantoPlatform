<!-- ADAPTADO PARA A MANTO (2026-09-08) — reaplicar após qualquer atualização do Spec Kit; para este
     arquivo o hash em .specify/integrations/speckit.manifest.json deixa de conferir de propósito. -->
# Feature 306 — Cancelar devolvendo o dinheiro: o que a Manto retém entra na DRE, na comissão e no BV na mesma proporção

**Branch**: `306-dinheiro-do-cancelamento` (da `main`) · **Created**: 2026-10-15 · **Status**: Rascunho ·
**Migration**: uma, aditiva. Só `create_table`, com três tabelas (`event_cancellations`, `event_cancellation_bvs`,
`event_cancellation_elenco`) e `down_revision = "a7c3e91f4d28"`, que segue sendo a cabeça em `d855d1a`
(conferido). Nenhuma coluna em tabela existente e nenhum backfill. Não é destrutiva, mas o rollback deixa de ser
simétrico depois do primeiro cancelamento real (L3597-3621) · **Nível**: 1 (feature). A constituição, Princípio VI,
pede Nível 1 por quatro motivos: migration, dois endpoints novos, contrato alterado de outros dez, mais o
`PUT …/acrescimos` e as três rotas de reembolso no cancelado, e três domínios (agenda, comissões, financeiro, mais
Gastos Extras e comercial) (L3-4, L3419-3423)

**Input**: pedido do dono no item 1b do backlog de setembro, "Dinheiro do cancelamento", a 2ª das três entregas
da 303 (D34).
- **Plano**: `docs/backlog/1b-dinheiro-do-cancelamento.md`, revisado em nove rodadas de respostas, sem dúvida
  aberta (L5265, L5363). Toda referência Lnnn abaixo é linha desse arquivo.
- **Texto de partida**: as Histórias 3 (parte do dinheiro), 4 e 7 de
  `specs/303-sync-nao-apaga-venda/entregas-2-e-3-rascunho.md`, com as correções do plano (L3424-3432).
- **224g**: esta entrega a absorve (L122-131).
- **Base de código**: `main` em `6356b80`, já com 303, 215b, 267c, 305 e 307 (rebase de 16/10). A spec nasceu sobre
  `d855d1a`; a 307 não trouxe migration nem mexeu em código que a 306 altera, só deslocou linhas, e as citações
  `arquivo:linha` destes artefatos foram reconferidas contra `6356b80`.
- **Citações `arquivo:linha` do plano**: são de `f6ad283` (01/10). Depois disso, `comissoes_ops.py`,
  `agenda_write.py`, `comercial_ops.py`, `event_ops.py` e `financeiro/routes.py` mudaram, então o
  `/speckit-plan` reconfere cada citação contra o HEAD.

## O pedido, nas palavras do dono *(obrigatório)*

Linha da onda (L116-120): "Dinheiro do cancelamento — cancelar com devolução, comissão do retido, BV negociado,
imposto, correção pelo Superadmin, DRE com o retido, retido como venda". A 1b-Q2 trocou o "BV negociado" por
"proporcional ao retido" (L191-195).

- **22/09 (D14), comissão do cancelado**: "sim, sobre o valor retido" (rascunho `:54`). O plano registra
  (L141-144): mesmo % do vendedor sobre (pago − devolvido). Exemplo: venda de R$ 2.000 a 5%, sinal de R$ 1.000 e
  R$ 600 devolvidos dão retido de R$ 400 e comissão de R$ 20. Se os R$ 100 cheios já foram pagos, o próximo
  repasse desconta R$ 80.
- **29/09 (D22), devolução**: "Existe o ponto também de muitas vezes precisarmos devolver o dinheiro. Isso também
  precisa estar nessa spec." (rascunho `:59-60`; L148-150).
- **29/09 (D30–D33), relatórios**: "Precisamos incluir no plano essa questão do evento cancelado e com 600
  devolvido aparecendo como −600, sendo que ele é +400. E acredito que possa ter algo especial para sinalizar e/ou
  filtrar eventos cancelados." (rascunho `:118-120`; L158-162). A parte de sinalizar e filtrar é da 1c.
- **30/09, cachê pago**: "não é possível um evento com valores pagos sumir da agenda. Se foi pago é porque foi
  realizado. O único que nós podemos ter pago e ter sido cancelado é a comissão do vendedor"
  (`specs/303-…/spec.md:101-103`).
- **30/09 (D36), correção depois de cancelado**: "Sim, só o Superadmin". Serve para acrescentar comprovante
  esquecido e corrigir, com retido e comissão recalculados (spec 303 `:89-90`; L170-171).
- **30/09, exclusão com comissão paga**: "Apaga como hoje", e o estorno contra o vendedor sai (spec 303
  `:97-99`). Esta entrega põe esse estorno no ciclo certo (L998-1018).

**O sintoma, como a equipe vê** (L49-92, L309-511; conferido no código e no espelho de 01/10):

- **DRE**: um cancelado com R$ 600 devolvidos de R$ 1.000 pagos aparece como **−600**, porque a devolução vira
  gasto extra no mês do cancelamento. O retido de **+400** não aparece em mês nenhum (L402-407).
- **Comissão**:
  - A comissão já paga vira estorno com a data da venda e cai num repasse que já saiu. Em produção, o estorno
    211 (−R$ 92,39) nasceu em 17/09 com data de 21/08 (L124-137).
  - A comissão "no banco" é paga cheia, e a "a pagar" é cancelada inteira.
  - Abrir Comissões ou a Planilha zeraria qualquer comissão do retido (L335-376).
- **BV**: o BV de evento cancelado continua na Planilha (L130-131).
- **Gastos Extras**: qualquer "Salvar" numa devolução apaga destinatário, nome e PIX (L417-423).
- **Evento marcado pela 303**: só oferece "Devolver ao Google" e não se cancela até esta entrega (D35,
  L167-169). O banner promete que "o cancelamento com devolução chega na próxima entrega".
- **Venda de vários dias, ensaio, aviso e cachê**: para cancelar é preciso desagrupar; o ensaio do show cancelado
  fica marcado; ninguém é avisado; nada confere cachê pago (L464-511).
- **Exposição**: no espelho, 59 eventos futuros somam R$ 185.825,49 em comprovantes. Há 32 linhas de comissão
  **já paga** de evento futuro (R$ 4.577,11), e 28 dos 59 eventos futuros com comprovante já têm comissão paga.
  Então descontar no próximo repasse é o caso comum (L570-571, L596-598).

## Clarifications

As respostas do dono estão transcritas literalmente, por rodada. A "Leitura" é o que o plano tira de cada
resposta e o que esta spec aplica; nada foi reaberto. Pergunta de outro item leva o prefixo dele (1c-, 1e-, 2a-,
2b-, 3a-, 3b-).

### Session 2026-09-22 a 2026-09-30 — decisões do plano de setembro e clarify da 303

- **D14** (22/09): "sim, sobre o valor retido". → A comissão do cancelado aplica o mesmo % sobre (pago −
  devolvido) (L141-144).
- **D22** (29/09): "Existe o ponto também de muitas vezes precisarmos devolver o dinheiro." → Cancelar com
  devolução total, parcial ou nenhuma. O evento mostra devolvido, retido e estado (L148-150).
- **D23** (29/09), registrada pelo plano sem fala do dono transcrita; *leitura do plano*: a D14 entra junto da
  devolução → a 224g vai junto, por ser a mesma função (L151-153; `PLANO_BACKLOG_SETEMBRO.md:104`). A 224g é o
  estorno no ciclo certo e o BV de cancelado fora da Planilha.
- **D25** (clarify da 303, 29/09): "**Proporcional**". → Comissão cheia × (retido ÷ venda), nunca acima da cheia,
  e igual no EducaManto (rascunho `:98-100`).
- **D26** (29/09): "**Caso a caso, depende da negociação**". → **Superada pela 1b-Q2**: o BV passa a ser
  proporcional ao retido (L191-195).
- **D27** (29/09): "**Vem vazio**". → Tudo, Parte ou Nada; sem escolher, não cancela (rascunho `:104-106`).
- **D28** (29/09): "**Acompanham**". → Se a devolução muda depois, retido e comissão se refazem. A parte já paga
  se ajusta no próximo repasse, para mais ou para menos (rascunho `:107-110`).
- **D30** (29/09): "**No mês do cancelamento**". → O retido entra na DRE em Realizado e Total (rascunho
  `:123-124`).
- **D31** (29/09): card e "Mostrar cancelados" são da 1c. O botão saiu na 1c-Q6 (L173, L246-249; plano 1c
  `:2238`).
- **D32** (29/09): "**Depende da negociação, dos prazos e do resto**". → O imposto do retido é informado no ato,
  com 16% do retido ao lado só como referência. A 1b-Q2 não mexeu nisso (rascunho `:129-131`; L195).
- **D33** (29/09): "**O retido conta como venda**" do vendedor, no mês do cancelamento (rascunho `:132-134`).
- **D34** (30/09): "**Três entregas**". Esta é a 2ª, e é uma entrega só, sem dividir (spec 303 `:84-85`;
  L163-166).
- **D35** (30/09): "**Só 'Devolver ao Google Agenda'**" até esta entrega. → *Leitura do plano*: nenhum
  cancelamento sai com a regra velha (spec 303 `:86-88`).
- **D36** (30/09): "**Sim, só o Superadmin**" (spec 303 `:89-90`). → Acrescentar comprovante esquecido e corrigir,
  com retido e comissão recalculados. O "BV negociado" virou proporção (1b-Q2).
- **Exclusão com comissão paga** (30/09): "**Apaga como hoje**". → O estorno sai, agora no primeiro repasse
  aberto (spec 303 `:97-99`; L1005-1007).
- **Cachê pago** (30/09): "não é possível um evento com valores pagos sumir da agenda. Se foi pago é porque foi
  realizado. O único que nós podemos ter pago e ter sido cancelado é a comissão do vendedor". → É a base da 1b-Q4
  e do BV pago que não se mexe (L2755-2756, L4064-4065).
- **D16**: é operação do Financeiro; não sobra nada dela nesta entrega (1b-Q3 e Q7; L173-178).

### Session 2026-10-06 — primeira rodada

- **1b-Q1** (L2097). Cancelar uma venda de vários dias exige desagrupar?
  - **Resposta: C** — "Pode-se cancelar todos os dias ou apenas alguns. De qualquer forma, não necessariamente
    deve-se ter que desagrupar para cancelar. Ou seja, resposta C." (L2124). A 3b-Q6 = C é a mesma decisão
    (L187-190).
  - *Leitura* (L1229-1272):
    - Cancelar o principal cancela todos os dias vivos numa confirmação, sem desagrupar.
    - Cancelar um dia que não é o principal cancela só esse dia. A venda do principal diminui, e retido e
      comissão acompanham.
    - O dia cancelado fica no grupo.
- **1b-Q2** (L2130). BV e comissão do cancelado ficam na data original ou vão para o cancelamento?
  - **Resposta: A, com regra** — "Se um evento é cancelado, o BV também é cancelado. A comissão também deve ser
    cancelada. A não ser que sobre alguma multa contratual. Se sobrar, devemos dividir de forma proporcional. Mas
    ficam na data original." (L2157).
  - *Leitura* (L775-781, L828-840, L970-977):
    - Comissão e BV do retido = cheio × retido ÷ venda, nunca acima do cheio.
    - Não há campo de BV negociado nem ajuste manual.
    - O BV proporcional fica na Planilha do mês do evento.
    - A comissão EducaManto a pagar fica no ciclo da data do evento, e a linha nova positiva nasce nessa data.
    - O ajuste de linha já paga vai ao primeiro repasse aberto (D14).
    - Vale também para a comissão do vendedor no EducaManto, quando a 2b a criar (L5250-5260).
- **1b-Q3** (L2163). Os dois estornos antigos (R$ 262,39) se descontam à mão ou pelo sistema?
  - **Resposta: A, com exceção** — "Vamos deixar tudo de comissão que foi pago errado no passado para trás e
    trabalhar daqui para frente. A não ser que deveria ter pago mais e paguei de menos." (L2189).
  - *Leitura*: os estornos 151 (−R$ 170,00) e 211 (−R$ 92,39) não são tocados, e a conferência da D16 deixa de
    existir. A exceção do pago a menos, para o passado, caiu na Q7 (L196-199).
- **1b-Q4** (L2198). Evento com cachê já pago ao elenco pode ser cancelado?
  - **Resposta: B, com regra nova** — "Não. Mas um evento cancelado em cima da hora pode ter cachês a serem pagos
    em formato de multa." (L2225).
  - *Leitura* (L1469-1472):
    - A recusa é 409 `cache_pago` para todo papel.
    - O evento marcado pela 303 com cachê pago fica só com "Devolver ao Google".
    - A multa ao elenco foi decidida nas Q8–Q10.
- **1c-Q3** (plano 1c `:2120`). O que acontece com o ensaio de um show cancelado?
  - **Resposta: C, com aviso** — "O ensaio também é cancelado. E avisa não só a pessoa responsável por marcar o
    ensaio no sistema como também os artistas já escalados."
  - *Leitura* (L203-205, L1382-1403):
    - É trabalho desta entrega.
    - Todo ensaio vivo do cancelado cai no mesmo ato, no banco e no Google.
    - "Quem marcou" é a equipe de Ensaio, porque o sistema não grava o autor do ensaio.
- *Ponteiro*: **3a-Q1 = B**: o BV acompanha o valor final na mesma proporção (L232-233). É a base do BV não
  pago no corte de um dia (FR-056). E a regra do PIX do BV (`3a-bv-do-orcamento-no-evento-099b.md:144-145`):
  "Lembrando que é de extrema importância que, ao colocar na agenda um evento com BV, seja obrigatório colocar o
  PIX de quem receberá o BV. Para que isso vá para a planilha de pagamentos." → O cancelamento pede recebedor e
  PIX do BV a pagar quando faltam (L232-236, L841-855).

### Session 2026-10-06 — segunda rodada

- **1b-Q5** (L2231). A cliente desiste só do 1º dia, o que guarda a venda.
  - **Resposta: B** — "b" (L2257). A opção B dizia: "O sistema passa a venda para o próximo dia que fica — ele vira
    o 1º dia do grupo, e valor, vendedor, comprovantes, comissão, BV, parcelas, nota e contrato vão junto, com os
    mesmos valores e datas — e cancela o antigo 1º dia como um dia qualquer, com a venda diminuindo." (L2254).
  - *Leitura* (L1273-1363):
    - Passar a venda e cortar o dia acontecem numa transação só.
    - Quem recebe a venda é o dia vivo mais cedo.
    - Tudo muda de dono só pelo vínculo, sem mudar valor nem data.
    - A prova é "soma antes = soma depois".
- **1b-Q7** (L2263). Pagar o que se pagou a menos no passado?
  - **Resposta: nenhuma das três** — "Como é pouco valor, podemos deixar esse passado quieto e pensar em como será
    daqui pra frente." (L2291).
  - *Leitura* (L2293-2295): o pago a menos (R$ 385,88 no espelho) não ganha lista, acerto nem lançamento, e isso
    vale também para a exceção da Q3. O cenário 26 prova que nada do passado muda.
- **1b-Q8** (L2297). Quem decide quem recebe a multa e quanto?
  - **Resposta: A** — "A" (L2317). A opção A dizia: "Quem cancela (o Superadmin) informa, artista por artista,
    quanto cada um recebe; o cachê da vaga aparece ao lado só como referência; vazio = sem multa." (L2312).
- **1b-Q9** (L2323). Existe prazo para o "em cima da hora"?
  - **Resposta: A** — "A" (L2340). A opção A dizia: "Sem prazo no sistema: o espaço da multa aparece em todo
    cancelamento com elenco escalado, com 'faltavam N dias para o evento' ao lado; quem cancela decide." (L2336).
- **1b-Q10** (L2346). A multa ao elenco diminui comissão e BV?
  - **Resposta: A** — "A" (L2367). A opção A dizia: "Não: comissão e BV seguem a proporção do retido; a multa é
    só custo na DRE e pagamento na Planilha." (L2363).
- **1b-Q11** (L2373). Quem o sistema avisa e por onde?
  - **Resposta: B** — "B" (L2398). A opção B dizia: "Em todo cancelamento, os artistas escalados recebem o e-mail;
    a equipe de Ensaio recebe o sino só quando havia ensaio marcado." (L2394).
  - *Leitura* (L2400-2402):
    - O e-mail é o que já existe, enviado depois do commit, uma vez por pessoa.
    - Quem recusou o convite não recebe.
    - O sistema não passa a gravar quem marcou o ensaio.
- *Ponteiros*:
  - **1c-Q2 = B, 1c-Q4 e 1c-Q5**: o cancelado não aparece em lista de escolha nem no calendário; ver cancelados é
    na página de Cancelamentos; o cancelado recusa escalar, avaliar e pedir figurino. São telas da 1c
    (L225-228).
  - **3b-Q4 = A**: a proposta de vários dias não tem preço por dia, então quem cancela um dia informa a venda nova
    (L229-231).

### Session 2026-10-13 — terceira rodada

- **1b-Q12** (L2404). Venda viva que muda depois de a comissão ser paga.
  - **Resposta: B** (o recomendado) — "sim" (L2443).
  - *Leitura* (L2445-2447, L1028-1034): fica **fora desta entrega** e vira o item **1e**. Até a 1e subir, vale a
    regra de hoje, registrada como dívida no `docs/05`. Esta entrega só deixa pronta a reconciliação no primeiro
    repasse aberto, que a 1e reaproveita.
- **1b-Q13** (L2449). Corte do 1º dia quando o próximo dia cai noutro mês.
  - **Resposta: parcial** — "A data importante para a comissão segue sendo a data de venda, não a data de
    realização do evento." (L2475).
  - *Leitura* (L1342-1346): passar a venda não muda a data de venda, e o ciclo da comissão comum segue a data de
    venda, no mesmo repasse. O mês da receita virou a Q15.
- **1c-Q6** (plano 1c `:2238`). Botão "Mostrar cancelados".
  - **Resposta: A** — "Não deve ser mostrado na agenda."
  - *Leitura* (L1628-1633): esta entrega não faz botão nem `incluir_cancelados`. O dinheiro fecha pela linha
    "Retido de cancelamentos" da DRE.
- **1c-Q7** (plano 1c `:2280`). A tela do cancelado fica só para consulta?
  - **Resposta: A, com os dados de venda editáveis** — "Acredito que dados de venda ainda devam poder ser
    editados, porque podemos alterar valores e inserir pagamentos de multas, mas de resto melhor não dar para
    mexer."
  - *Leitura* (L1117-1159): ficam abertos os dados de venda (a)–(h) da FR-048, e o orçamento fica travado. A
    trava geral do resto da tela é da 1c.
- *Ponteiros*:
  - **2a-Q2 = B e 2a-Q5 = D**: o pedido traz a devolução combinada, mostrada ao lado; o diálogo daqui continua
    vazio (D27) (L250-252).
  - **3b-Q7**: nada muda aqui; o cancelado escala o BV gravado (L252-253).

### Session 2026-10-13 — quarta rodada

- **1b-Q15** (L2481). Mês da receita na DRE no corte do 1º dia.
  - **Resposta: A** — "DRE do mês novo." (L2509).
  - *Leitura* (L1337-1351): receita, imposto, BV, cachês de todos os dias e a comissão como custo vão à DRE do mês
    do novo 1º dia, e o BV vai à Planilha desse mês. É a competência de hoje, sem data nova guardada.
- **1c-Q8** (plano 1c `:2324`). Quem mexe nos dados de venda do cancelado.
  - **Resposta: A** — "Superadmin apenas."
  - *Leitura* (L1187-1197): uma regra de permissão só, Superadmin real. Quem passa no gate de hoje recebe 409
    `codigo: "cancelado"`.
- **1c-Q10** (plano 1c `:2387`). Tirar da escala no cancelado.
  - **Resposta: nenhuma das três, com fluxo novo** — "Quando cancelado, pede para o casting excluir e avisar por
    WhatsApp para a pessoa que o evento foi cancelado."
  - *Leitura* (L1441-1455, L710-723):
    - O Casting recebe um sino por dia cancelado com escalados.
    - O sistema não manda WhatsApp.
    - Tirar da escala continua possível.
    - O elenco do ato fica guardado, e a multa vale para quem já saiu da vaga.
- **1c-Q11** (plano 1c `:2434`). Vendedor, acréscimos e reembolsos do cancelado.
  - **Resposta: C** — "Pode mexer sim."
  - *Leitura* (L1146-1157): entram nos dados de venda (f) o vendedor, (g) os acréscimos — valor, recebedor e PIX
    do BV, sem mexer no BV pago — e (h) os reembolsos.
- **1e-Q2** (aqui, L282-288). Taxa da comissão.
  - **Resposta: C, com regra nova** — "Vou gerar um exemplo para entender como agir: um evento com data de venda
    12/10 deve usar a comissão configurada no dia 12/10. Se a comissão muda dia 13/10, os eventos a partir desse
    dia usam essa taxa." (`1e-comissao-acompanha-a-venda.md:1259`).
  - *Leitura* (L884-906):
    - A taxa usada no ato fica congelada no cancelamento.
    - A tabela de histórico da taxa padrão é da 1e.
    - Até a 1e subir, vale a taxa do evento ou a padrão do dia do ato.
- *Ponteiro*: **1c-Q9 = A** (plano 1c `:2356`): "Apenas para os comercial, financeiro e admin mesmo." → Motivo e
  autor do cancelamento só para Comercial, Financeiro e Superadmin. É tela da 1c, e nada muda aqui: o bloco
  `cancelamento` já sai só com `show_comercial` (L297-299).

### Session 2026-10-13 — quinta rodada

- **1b-Q16** (L2515). Vendedor do cancelado trocado depois de a comissão ser paga.
  - **Resposta: A** — "Deve gerar um saldo negativo em uma comissão futura desse vendedor. Por isso é importante
    ser tudo bem auditado pela tela das comissões." (L2545).
  - *Leitura* (L919-959, L1173):
    - A invariante é por beneficiário: o vendedor antigo tem alvo zero e devolve o que recebeu como linha
      negativa no primeiro repasse aberto dele.
    - O novo vendedor recebe a comissão do retido inteira.
    - Toda linha de ajuste leva evento, valor, a paga que acerta e o motivo.
- **1b-Q17** (L2551). Corrigir a taxa (ou a data de venda) do cancelado mexe na comissão paga?
  - **Resposta: A** — "Sim." (L2581).
  - *Leitura* (L884-906):
    - Só duas correções do Superadmin trocam a taxa congelada: a da taxa, e a da data de venda, que relê a taxa
      daquela data (L896-898, L1179-1185). Toda correção do cancelado refaz a comissão do retido (L1161-1176).
    - O refazer dessas duas vale para mais e para menos, também na parte já paga, e entra no primeiro repasse
      aberto.
    - Mudar a taxa padrão não mexe em cancelado nenhum.
    - Não se guarda com que taxa cada parte foi paga.
- **1c-Q12** (plano 1c `:2470`). E-mail do ato × e-mail de remoção pelo Casting.
  - **Resposta: A** — "Não. Se ele já recebeu o e-mail automático de cancelamento, não precisa do e-mail 'sua
    participação foi cancelada'."
  - *Leitura* (L1456-1465): o e-mail do ato continua, e tirar da escala do cancelado não manda o segundo.
- *Ponteiro*: a **1e-Q6** foi conferida contra a Q2 daqui. Ela bate para o responsável e abriu a Q18 (L289-296).

### Session 2026-10-13 — sexta rodada

- **1b-Q18** (L2587). Comissão EducaManto a pagar no corte do 1º dia.
  - **Resposta: A** — "Passa para o próximo mês mesmo." (L2616).
  - *Leitura* (L1329-1336, L5244-5249): a passagem não marca a linha, e o sincronismo de hoje leva a data de
    liberação à data do novo 1º dia. A comissão comum não muda.
- *Ponteiros*:
  - **1e-Q7 = B / 2b-Q4 = B**: "esse acréscimo do vendedor é a comissão do vendedor" (L292-296). No cancelado,
    ela segue a regra do retido. Quem a liga à reconciliação é a 2b, sem tarefa aqui (L5250-5260).
  - **1e-Q8 = B**: "Por enquanto nada. Mas precisa ficar anotado para negociação de quando a pessoa estiver
    saindo da empresa, por exemplo." (`1e-comissao-acompanha-a-venda.md:1428`). O desconto de vendedor sem repasse
    futuro fica a pagar, à vista, sem baixa, e vira dívida no `docs/05`. O texto da 1b ainda chama a 1e-Q8 de
    "aberta" (L2748); está desatualizado.
  - **2b-Q1 = B e 3a-Q8 = A**: nada muda aqui (L5261-5264).

### Session 2026-10-13/14 — sétima a nona rodadas

Nenhuma resposta da 1b mudou (L5307-5363). A 2b muda a regra do ensaio **a partir da noite 7**, com 2b-Q14 = A,
Q15 = B, Q16 = A, Q19 com regra nova e Q21 = C. Até lá, "todo ensaio vivo do dia cancelado cai" é exato, e esta
entrega constrói só isso (L5298-5302, L5334-5346, L5355-5362).

### Dúvidas que saíram

- **1b-Q6** (ajuste manual do BV): saiu na conferência de 06/10. "Devemos dividir de forma proporcional" (Q2) já
  responde: não há campo (L94-95, L2053-2056).
- **1b-Q14** (ensaio do 1º dia cortado): saiu na conferência da segunda rodada. O 1º dia cai "como um dia
  qualquer" (Q5) e "O ensaio também é cancelado" (1c-Q3) (L99-101).

### Session 2026-10-15 (`/speckit-specify`) — leituras fixadas por esta spec, não palavras do dono

São pontos que o plano deixou a quem fizesse o specify, ou em que duas passagens do plano não batem. Cada um vale
como premissa, e o dono pode contestar.

1. **Gate do Financeiro e menu da página de Cancelamentos ficam na 1c.**
   - *Fonte da escolha*: é a premissa mais nova do plano (L3404-3408), e o plano 1c, `:3064-3071`, diz o mesmo.
   - *Contra*: as seções 4–6 ainda os põem aqui (L1523, L1636-1637, L1880, L1938), e a premissa "Esteira"
     (L2788) também. A premissa de L3404 manda escolher uma entrega só.
   - *O que fica aqui*: o `resumo` e o `no_banco` no payload e na página. O cenário 6 perde a leitura do
     FINANCEIRO.
2. **Cenário 19 reescrito.** A quarta rodada abriu os acréscimos do cancelado ao Superadmin (1c-Q11 = C;
   L1106-1107, L1518). Por isso o `PUT …/acrescimos` dá 409 `cancelado` a quem passa no gate de hoje e não é
   Superadmin (Comercial, Financeiro), ou quando muda um BV pago (16d); Casting e Figurino seguem com 403. O texto
   que ficou de pé é o do próprio cenário, em L1956 ("409 nos três"), e o "`PUT …/acrescimos` dá 409" de L846
   também ficou por riscar. Além disso, o `DELETE` pela COMERCIAL dá 403, e não 409, porque o gate de hoje
   (`_can_delete()`, `agenda_write.py:549-550`) é só do Superadmin.
3. **Cenário 16b, base da taxa.** O caso "taxa 2,5 → 3,0" roda num cancelado semeado **sem taxa própria**, com a
   padrão de 2,5% do espelho (L666-669). Os outros casos do 16b usam o exemplo-padrão, com taxa 5 gravada no
   evento (L1919-1920).
4. **Cancelado sem dinheiro nenhum** (sem venda e sem comprovante) fica fora da contagem de cancelados e da DRE e
   aparece só na página de Cancelamentos. É a premissa de L2801-2805, que emenda o "conta em `n_cancelados`" da
   mesma passagem.
5. **Ordem de fechamento das Histórias.**
   - A fase 9 do plano ("dados de venda", L3490) fecha depois da DRE, porque o 16c confere o retido trocando de
     vendedor no Dashboard Comercial, e antes da venda de vários dias ("antes da fase 6").
   - Três itens que o plano punha na fase 9 (L3495-3503) fecham com a multa no ato (História 6), porque dependem
     dela: a multa lançada depois, a lista do elenco do ato e o sino ao Casting.
   - O 42e e as partes de aviso, ensaio, multa e cachê pago do 2b, 42, 42b e 42d fecham na História 6, porque
     dependem do ensaio, do aviso, da multa e do cachê pago que o plano só constrói na fase 7, depois da fase 6
     (L3478-3481).
   - *Contra (1)*: L3490 põe a fase 9 "dentro da História 3" do plano (cancelar e devolver, a História 2 daqui),
     e não depois da DRE.
   - *Contra (2)*: a História 1 daqui traz `bv_da_planilha` (cenário 17 do verify, aceite 10 da História 1), que
     o plano põe na fase 4, "História 7 — DRE e comercial" (L3459-3461). Aqui ele fecha com a comissão, porque é
     a mesma regra do retido (Q2 = A), e o 17 só fica verde junto da História 2, que constrói o ato.
   - *Contra (3)*: L3477 põe os cenários 37–42e na fase 6.
6. **BV pago ausente do corpo** do `PUT …/acrescimos` no cancelado: 400 `items`, como no evento vivo, e nada é
   gravado.
   - *Contrato de hoje*: no evento vivo, a 305 (já na base `d855d1a`) responde 400 `items` quando um BV pago ou no
     banco some da lista ("Um BV já pago (ou no banco) saiu da lista…", `comercial_ops.py:283-293`).
   - *Por que alinhar*: é o mesmo endpoint e o mesmo editor, que sempre manda o BV pago (só leitura na tela,
     FR-052). A ausência só acontece com tela velha, e o 400 manda recarregar. Deixar o BV no lugar sem avisar
     daria dois contratos para o mesmo corpo.
   - *Fonte*: o plano só diz que o ausente **não pago** sai (L1152-1153), e BV pago nunca é reescrito nem
     escondido (FR-040); nas duas saídas o BV pago fica intacto.
7. *(Saiu das leituras: "troca de vendedor no EducaManto muda só o recorte comercial" é texto do plano,
   L1178-1179, conferido "fiel" em L5025-5026. Foi para as Premissas como P-50, premissa do plano. O número fica
   para não mudar as referências às outras leituras.)*
8. **Erros do corte de um dia**: "Tudo" dá 400 `fields.devolucao_modo`, e valor acima do teto dá 400
   `fields.devolucao_valor`. O plano não nomeia esses campos (L1255-1257).
9. **"Regime sem retido"** no `PATCH …/devolucao` são `satelite` e `virtual`, os que entram com retido zero e não
   têm devolução própria a corrigir (L818-827). O `dia` **não** entra: ele tem devolução própria, e o dono decidiu
   no clarify de 15/10 (resposta "A") que ela se corrige por esse PATCH, sem mexer em comissão enquanto o principal
   vive (FR-017; o principal já cancelado inteiro está na Session do `/speckit-plan`, ponto 1). O
   `legado` aceita. Como o `legado` não tem linha em `event_cancellations` e tem imposto 0 (FR-003),
   nele `imposto_retido` no corpo dá 400 `fields.imposto_retido`; o PATCH não cria a linha nem congela nada, e o
   evento segue `legado`. Hoje não há nenhum legado (P-4), e a D35 garante que nenhum nasce (L591-594).
10. **BV do retido pago na Planilha depois do ato** fica pelo valor pago. Uma correção posterior do retido não o
    reescreve e não gera acerto ao parceiro, como o BV pago antes do cancelamento (L2754-2757). O `/speckit-plan`
    fixou o registro: o valor pago fica no congelado do BV (`paid_amount`), e desfazer o pago o devolve ao
    proporcional (FR-039, FR-040).
11. **Desfazer "pago" de uma linha do cancelado pela Planilha.** A linha volta a "a pagar" com o mesmo valor, a
    invariante por beneficiário continua, e a sincronização automática segue sem tocá-la.
    - *Fonte*: o "desfazer" da 267c, que só o Superadmin usa, e só para corrigir pagamento marcado por engano
      (1e-Q5 = A, L3186-3188). O plano não trata o caso no cancelado (o "desfazer pago" de L2708-2710 é o da
      devolução, não o da linha de comissão).
    - Conferido pelo `/speckit-plan`: o desfazer não ganha ramo novo, porque a soma não muda e a próxima correção
      absorve. No principal **vivo** depois de um corte, o desfazer da base com o ajuste vivo ganhou regra própria
      (FR-057, cenário 38c).

### Session 2026-10-15 (`/speckit-clarify`)

A varredura achou doze candidatas; onze já estavam decididas pela spec ou pelo plano. A que sobrou, perguntada
ao dono:

- Q: Quando a cliente desiste de só um dia de uma venda de vários dias e recebe parte do dinheiro de volta, e esse
  valor de devolução foi digitado errado (300 em vez de 30), por onde a devolução se corrige? → A: **"A"** — o
  "Alterar devolução" passa a valer também no dia cortado: o novo total é o da devolução daquele dia, entre o já
  pago à cliente e o pago do grupo menos as outras devoluções; não mexe em comissão (o resto do grupo segue vivo);
  refazem-se só a devolução, o "já devolvido" do grupo e a cobrança da Home. *(Aplicado em: leitura 9, FR-017,
  FR-056, RBAC do `PATCH …/devolucao`, casos de borda das devoluções, cenário 38 do verify.)*

### Session 2026-10-15 (`/speckit-plan`) — o que o plan acrescentou

Nenhuma pergunta nova ao dono e nenhuma decisão dele reaberta. O Princípio VII (Living Spec) manda a spec refletir,
antes do `/speckit-tasks`, o que o `plan.md` acrescenta ao comportamento ou fecha do que esta spec lhe deixou. Cada
ponto diz de onde vem:
- **derivado (decisão do dono: …)**: a decisão citada já responde; o plan só a aplica a um caso que a pergunta não
  descreveu;
- **técnico**: escolha do plan, sem resposta do dono por trás; vale como premissa, e o dono pode contestar.

O porquê, as citações do HEAD e as alternativas descartadas estão em `research.md`. Os nomes que a 1c, a 2a, a 2b e
a 6a reusam (constantes, funções e listas) estão na tabela única do `data-model.md` §6.

**Derivados de decisão do dono**

1. **"Alterar devolução" do dia cortado depois de o principal ser cancelado inteiro** (FR-017, FR-004) — derivado
   da **D28** ("**Acompanham**": se a devolução muda, retido e comissão se refazem), não da resposta do clarify de
   15/10. Cancelado o principal inteiro, a devolução do dia passa a ser devolvido daquela venda (FR-004), e
   corrigi-la refaz também o retido, a comissão e o BV do retido do principal. O "não mexe em comissão" da resposta
   "A" vale enquanto o principal vive, que é o caso que a pergunta descreveu ("o resto do grupo segue vivo").
   *(Aplicado em: FR-017, FR-049, RBAC do `PATCH …/devolucao`, História 5, casos de borda, variante do 39.)*
2. **Comprovante num dia de grupo** (FR-018, FR-049) — derivado da **D36** ("Sim, só o Superadmin", com retido e
   comissão recalculados) e da FR-004 (o pago é do grupo). O comprovante de qualquer dia refaz o cancelamento
   `venda` do principal; com o principal vivo (o dia cortado), nada se refaz; o pago do grupo abaixo do devolvido dá
   409 `pago_abaixo_do_devolvido`. *(Aplicado em: FR-018, FR-049, RBAC dos comprovantes, cenário novo 37b, variante
   38-comprovante.)*
3. **BV do retido pago depois do ato, e o pago desfeito** (leitura 10, FR-039, FR-040) — derivado da decisão de
   30/09 (base do "BV pago que não se mexe") e da **1b-Q2 = A** (o BV não pago é o proporcional). Pago no ato ou
   depois, pela Planilha, o BV fica pelo valor pago, sem acerto ao parceiro; desfeito o pago (1e-Q5 = A), deixa de
   estar pago e volta ao proporcional. *Técnico*: o valor pago fica no congelado do BV (`paid_amount`), e marcar o
   BV, na Planilha nova e na antiga, passa por uma função só, que trava o evento antes do acréscimo. *(Aplicado em:
   leitura 10, FR-039, FR-040, Entidades, RBAC do `set-status`, variante 16/17-`paid_amount`.)*
4. **Multa vazia ou 0** (FR-071, FR-072) — derivado da **1b-Q8 = A** ("vazio = sem multa"): 0 vale o mesmo, nos
   dois caminhos (no ato e no `POST …/multas`); 400 só para valor negativo ou inválido, ou para linha fora do ato.

**Técnicos**

5. **Comissão cheia em duas camadas** (FR-027, FR-049, P-3) — a regra de hoje da comissão do evento vivo fica
   intocada; a cheia passa antes pelo beneficiário comissionado (sem beneficiário, beneficiário que não recebe
   comissão, cortesia/permuta, Loja Virtual → 0) e só então usa a regra de hoje. Assim cortesia/permuta com valor e
   evento sem vendedor congelam cheia 0, sem mudar a comissão nem a DRE do evento vivo (FR-038, Princípio IV). O
   cenário 1 confere o vivo; a variante "cheia 0" do 16b confere a camada.
6. **Desfazer a base no principal vivo depois do corte** (FR-057; leitura 11 conferida) — na linha do cancelado, o
   desfazer da 267c não ganha ramo novo: a soma não muda e a próxima correção absorve. No principal **vivo** depois
   de um corte, a base devolvida a "a pagar" seria regravada com a cheia nova e somada ao ajuste (desconto em dobro);
   por isso, com o ajuste vivo e a base de volta a "a pagar", a sincronização reconcilia com alvo = cheia (base no
   alvo, ajuste cancelado). Cenário novo **38c** e variante 9/10-desfazer.
7. **Prévia = execução** (FR-011) — a prévia não grava nada, nem por autoflush, e mostra o que o ato grava, também
   nos dias 1 a 5. Variante do 2 e do 8, com `hoje` no dia 2 e no dia 10, conferida pela conexão separada.
8. **Edição completa e Jinja no cancelado** (FR-047, FR-048, P-27) — nem a porta "Editar tudo"
   (`PATCH /api/events/<id>`) nem a tela antiga recongelam. Por isso um dado de venda que chegue diferente do
   gravado nessa porta dá 409 `cancelado` a **todos**, inclusive o Superadmin ("corrija pela aba Comercial"), e o
   despachante Jinja recusa aba Comercial, venda, comprovantes e reembolsos do cancelado para todos os papéis.
   Vai além da FR-047 só no caminho: o Superadmin continua corrigindo tudo pela tela nova (1c-Q8 = A). A Planilha
   antiga recusa mexer em linha de comissão de evento cancelado e trava o evento antes de mudar o estado de uma
   devolução de cancelado. "Editar tudo" some no cancelado.
9. **Conferência de valor na devolução** (FR-040, FR-019) — a mesma da 305 para o BV: a tela nova manda o valor que
   mostrou, no BV e na devolução, e uma devolução que mudou desde que a Planilha abriu dá 409 em vez de ser marcada
   paga pelo valor velho. Sem o campo, vale o comportamento de hoje.
10. **Um sino por ato** (FR-067, FR-068) — a chave que impede sino duplicado é a do ato (o evento da URL; no
    Casting, mais o dia), porque ela é permanente: com a chave do principal, o segundo ato do mesmo grupo calaria.
    Variante do 44 (dois sinos por pessoa da equipe de Ensaio).
11. **Multa por escalação** (FR-070 a FR-072) — compatível com a 1b-Q8 = A ("artista por artista"): a lista do ato é
    por vaga × dia, então um artista em 2 dias, ou em 2 vagas, tem 2 linhas, 2 campos e 2 gastos.
12. **FR-062** — no evento avulso, o ponto de extensão da 2a recebe `"todos"` e nenhum dia novo; no corte de um dia
    que não é o principal, `"so_este_dia"` e nenhum dia novo, porque nenhum dia passou a guardar a venda.
13. **Bloco "o que foi pedido"** (FR-023) — é da 2a (Fora de escopo): esta entrega não constrói nada dele, nem a
    propriedade no diálogo.
14. **Gastos extras na tela** (FR-061) — o principal vivo lista só os dias vivos; o cancelado lista o próprio dia
    e, no regime `venda`, os dias do ato.
15. **Modelo** (Entidades) — colunas que a spec não listava: `commission_cost`, `sale_handed_over`, `paid_amount` e
    `special_expense_id`; a taxa em `Numeric(6,3)`; o dia da linha do elenco sai em cascata com o dia.
16. **RBAC e recusas** — três portas que a spec não listava (`PATCH /api/events/<id>`,
    `DELETE …/grupo/satelites/<sat>` e `POST /api/financeiro/pagamentos/set-status`); os 18 códigos 409, com a porta
    em que cada um nasce; imposto enviado sem nota dá 400; a ordem das recusas do `PATCH …/devolucao`; a ordem de
    gate de Gastos Extras porta a porta, como está hoje.
17. **Premissas confirmadas** — P-24 a P-27 confirmadas; P-28: a tela Jinja do cancelado fica com comissão 0, com
    dívida; P-29: a marca da comissão própria é um prefixo de nota por constante.
18. **Verificação e docs** — 59 cenários (entram 37b e 38c); 12 e 32 fecham sem a DRE na História 2 e com ela na
    3; a multa do 21 é semeada por ORM; `docs/00` §4 e §6 e uma linha em `docs/01` §4.3 por porta alterada.

### Session 2026-10-16 (`/speckit-checklist`) — o que os checklists de dinheiro e de regressão acrescentaram

Nenhuma decisão do dono foi reaberta. São escolhas técnicas ou derivações, cada uma no requisito que muda; o
registro item a item está em `checklists/dinheiro.md` e `checklists/regressao.md`.

1. **Base** — rebase sobre `6356b80` (307 em produção); citações reconferidas; `verify_307` na lista.
2. **Devolução travada pela edição** (FR-019) — o `PATCH` recusa o gasto que passaria a ser devolução de cancelado.
3. **BV pago com outro valor no editor do cancelado** (FR-052) — mantém o gravado, como no vivo; sem 409 novo.
4. **Grupo** — a pendente de qualquer dia recusa o ato (FR-012); a comissão própria de outro dia fica fora da
   conta também no "todos" e no corte (FR-030, P-51, derivada da 1b-Q3 = A); o alvo dos outros beneficiários é 0
   (FR-030, derivado da Q16 = A).
5. **Corte** — piso da devolução para a cliente não ficar com mais pago que a venda nova; o cheio cai na proporção e
   o desconto em reais cai com ele (FR-056).
6. **"Alterar devolução" no grupo** — o piso soma os dias cortados; as devoluções abertas dos `satelite` absorvem
   depois da do principal (FR-017).
7. **Travas no vivo** — comprovante trava o grupo também no vivo; reembolsos, parcelas e notas, só o evento (FR-053).
8. **Contas** — arredondamento e tolerância de R$ 0,01 (FR-028); a referência do imposto (FR-009); o teto de 24
   ciclos (FR-031); as chaves do Dashboard Comercial (FR-046).
9. **Regressão** — seis regressões `main` × branch com cenário (SC-002, `retrato_main_branch.py`); o recorte do
   SC-008; mudanças intencionais e rollback listados por inteiro; mais seis verifies antigos.

## Cenários e Verificação *(obrigatório)*

É uma entrega só (D34, L163-166). O `tasks.md` fecha as Histórias **nesta ordem**, cada uma com os cenários dela
verdes antes de abrir a seguinte, para um corte por limite de uso não deixar dinheiro pela metade (L3517-3520):

1. **Fundação**: migration, modelos e constantes; `verify_306.py`, `retrato_main_branch.py` e `contagem_pre_deploy.py`
   nascem vermelhos; comissão cheia em duas camadas, com a regra de hoje da comissão do evento vivo intocada;
   resumo do cancelado e `cancelados_do_periodo` (L3446-3449);
   cenários 1, 23 e 26.
2. História 1.
3. História 2.
4. História 3.
5. História 4.
6. História 5.
7. História 6.
8. Polimento.

Não existe fase 8: o passado fica quieto e a Q12 virou a 1e (L3482-3489).

**Exemplo-padrão** (L1919-1922): venda de R$ 2.000 com taxa de 5% gravada no evento e BV de R$ 200, o que dá
comissão cheia de R$ 90. A cliente pagou R$ 1.000 e recebeu R$ 600 de volta, sem nota. Com isso:
- retido: R$ 400;
- comissão do retido: R$ 18;
- BV do retido: R$ 40 (200 × 400 ÷ 2.000);
- na variante com nota, imposto de R$ 64.

### História 1 — A comissão e o BV acompanham o dinheiro que ficou (Prioridade: P1)

**Quem e o que muda**:
- **Comissão**: o vendedor de um evento cancelado (no EducaManto, o responsável) passa a receber a comissão
  cheia na proporção do que a Manto reteve, pago menos devolvido, nunca acima da cheia. Se a comissão já foi paga
  ou está no banco, ela fica como foi paga, e a diferença cai no **primeiro repasse aberto** dele, nunca num mês
  já pago.
- **BV**: o parceiro do BV recebe a mesma proporção, na Planilha do mês do evento. O BV pago antes fica como foi
  pago.
- **Financeiro**: vê na Planilha e em Comissões as mesmas linhas, com tipo, ciclo e "No banco", e abrir as telas
  não desfaz nada.
- **Exclusão (224g)**: o estorno de evento excluído também passa a cair no primeiro repasse aberto.

**Por que esta prioridade**:
- Hoje o cancelamento cancela a comissão a pagar inteira, joga o estorno da paga num repasse que já saiu (o 211)
  e paga cheia a "no banco". Além disso, o resync zeraria a comissão do retido (L335-376).
- Com 32 linhas já pagas de evento futuro, o desconto no próximo repasse é o caso comum (L596-598).
- Não sobe sem a História 2, porque o rollback é assimétrico (L3609-3613). E fecha antes dela porque o cancelar
  chama a reconciliação (L3450-3458; `pesquisa/00-integracao.md` §5).

**Verificação** do `verify_306.py`:
- Fecham esta História os cenários 13, 14 e 14b, com 1, 23 e 26 verdes desde a Fundação.
- Os cenários da regra do retido (7, 8, 9, 10, 11, 12, 17 e 30) passam pelo ato de cancelar e ficam verdes junto
  da História 2, que constrói o ato. O 12 fecha ali sem a parte da DRE, que fecha na História 3.

**Cenários de aceite**:

1. **Dado** comissão de R$ 100 **a pagar** (venda de 2.000 a 5%, sem BV), **Quando** o evento é cancelado com
   R$ 600 devolvidos de R$ 1.000 pagos, **Então** a mesma linha vira **R$ 20,00**, ligada ao mesmo evento e com a
   mesma data. Com BV de R$ 200, a cheia é R$ 90 e a do retido, R$ 18.
2. **Dado** a mesma comissão **paga** ou **no banco**, **Quando** o mesmo cancelamento, **Então** a linha paga
   fica intacta e nasce **−R$ 80,00** ligada a ela. A data de venda e a de liberação ficam no primeiro repasse
   aberto:
   - no dia 2, é o ciclo anterior, se o vendedor ainda tem nele linha a pagar;
   - no dia 10, é o mês corrente;
   - nenhum repasse liquidado é reaberto.
3. **Dado** "Tudo" devolvido, **Então**:
   - a comissão a pagar é cancelada (nunca fica em R$ 0,00);
   - a comissão paga gera −R$ 100,00 no primeiro repasse aberto.
4. **Dado** evento com venda e sem linha de comissão de vendedor comissionado, **Quando** é cancelado com retido,
   **Então** a linha da comissão do retido nasce. Com vendedor que não recebe comissão, a cheia é 0 e nada nasce.
5. **Dado** EducaManto com comissão a pagar na data do evento, **Então**:
   - a linha é reduzida no lugar e a data não muda;
   - a linha já paga gera ajuste no primeiro repasse aberto do responsável;
   - sem linha a pagar, a nova do retido nasce com liberação na data do evento.
6. **Dado** qualquer cancelado, **Quando** Comissões e Planilha são reabertas, **Então** a comissão do retido é a
   mesma nas quatro telas, e a soma das linhas vivas bate com o alvo.
7. **Dado** um vendedor com ajuste, **Então** Planilha e Comissões mostram as mesmas linhas (tipo, evento, valor,
   ciclo) e o mesmo desconto, com "No banco" e com total do mês = pago + no banco + a pagar.
8. **Dado** um desconto que zera o repasse, **Então** o item continua na Planilha. Um estorno órfão a pagar não
   abre ciclo.
9. **Dado** um evento vazio excluído com comissão paga ou no banco, **Então** o estorno nasce no primeiro repasse
   aberto, não na data da venda, e o ciclo da venda, já pago, não reabre.
10. **Dado** BV de R$ 200 a pagar, **Quando** o evento é cancelado com R$ 600 devolvidos, **Então** a Planilha do
    **mês do evento**, nas telas nova e antiga, mostra R$ 40,00 com recebedor e PIX. Nos outros casos:
    - com "Nada", mostra R$ 100,00;
    - com "Tudo", não mostra nada;
    - se o BV já estava pago antes, mostra os R$ 200 intactos.
11. **Dado** outra sessão marcando "pago" na Planilha no instante do cancelamento, **Então** a paga fica em R$ 100
    e nasce o −R$ 80. Nunca aparece "paga de 20".
12. **Dado** o espelho inteiro, **Então** nenhuma linha de comissão anterior a esta entrega muda: nem os estornos
    151 e 211, nem o pago a menos ou a mais do passado.
13. **Dado** a linha paga de um cancelado, **Quando** o Superadmin desfaz o "pago" pela Planilha (267c), **Então**
    ela volta a "a pagar" com o mesmo valor, a sincronização não a toca e a soma continua no alvo; a próxima correção
    absorve a diferença (leitura 11).
14. **Dado** o BV do retido de R$ 40 marcado pago na Planilha depois do ato, **Quando** um comprovante esquecido
    leva o proporcional a R$ 60, **Então** o BV fica em R$ 40 pago, sem acerto ao parceiro. Desfeito o pago, a
    Planilha volta a mostrar o proporcional, R$ 60 (leitura 10).

---

### História 2 — Cancelar e devolver o dinheiro (Prioridade: P1)

**O ato de cancelar**:
- Na tela de um evento, marcado "Sumiu do Google" ou não, o Superadmin abre "Cancelar e devolver o dinheiro".
- Informa o motivo e escolhe Tudo, Parte ou Nada (nenhum vem marcado), com nome e PIX de quem recebe.
- Informa o imposto quando o evento era com nota, e o recebedor e o PIX do BV quando faltam.
- Antes de confirmar, vê o que o servidor calculou: pago, já devolvido, retido, comissão e BV do retido, e em que
  repasse cai o ajuste.
- A devolução vira pagamento a fazer na Planilha do mês do cancelamento, e o evento passa a mostrar o "Resultado
  do cancelamento".
- O evento marcado cancela sem chamar o Google e perde a marca.

**Depois do ato**:
- Só o Superadmin altera a devolução e acrescenta comprovante esquecido, com tudo recalculado.
- Gastos Extras trava a devolução e para de apagar o PIX.

**Por que esta prioridade**: é o MVP. Destrava a D35 (hoje o marcado só tem "Devolver ao Google") e responde ao
"muitas vezes precisamos devolver o dinheiro" (D22).

**Verificação**:
- **Fecham aqui**: 2 (com a variante prévia = execução), 3, 5, 6, 15, 16 (com a variante 16/17-`paid_amount`),
  18, 19, 25, 28, 31, 34 e 36.
- **Fecham em parte**:
  - 2b: o aviso fecha na História 6;
  - 4: aqui fecham as validações de devolução, imposto, prévia e BV; as do corte fecham na História 5 e as da
    multa, na 6;
  - 12 e 32: fecham aqui sem a DRE; a parte da DRE fecha na História 3.
- **Com o ato pronto, fecham também os da História 1**: 7–11 (o 8 com a variante prévia = execução; o 9 e o 10
  com a variante do desfazer) e 30, o 12 sem a DRE, e o 17 menos a parte do satélite, que fecha na História 5.

**Cenários de aceite**:

1. **Dado** o exemplo-padrão num evento vivo não marcado, **Quando** o Superadmin cancela com motivo, "Parte" de
   R$ 600, nome e PIX, **Então**:
   - o evento fica cancelado;
   - nasce um Gasto Extra aprovado e a pagar de R$ 600 — "Devolução a cliente", destinatário cliente, com nome e
     PIX, ligado ao evento — na Planilha do mês do cancelamento;
   - o congelamento grava venda de 2.000, cheia de 90 e modo `parte`, e o retido é 400;
   - o histórico registra modo, devolvido, retido, BV e imposto, na hora certa (±5 min);
   - a remoção do Google acontece depois do commit.
2. **Dado** o mesmo evento marcado pela 303, **Quando** é cancelado, **Então** o Google é chamado zero vezes, a
   marca sai com o motivo "cancelado" e não há aviso do Google.
3. **Dado** "Tudo", **Então** a devolução é o máximo que o servidor mandou (pago − já devolvido). **Dado** "Nada",
   **Então** não nasce gasto e o retido é o pago. **Dado** "Tudo" divergente (outra devolução aprovada antes),
   **Então** 409 com `max_devolucao`, e a tela refaz o impacto. **(deve falhar: o divergente)**
4. **Dado** os casos abaixo, **Então** 400 no campo certo e nada gravado:
   - sem modo → `devolucao_modo`;
   - valor acima do pago;
   - Parte sem nome ou sem PIX;
   - evento com nota sem imposto, ou imposto enviado em evento sem nota;
   - prévia com valor inválido;
   - BV a pagar sem PIX → `bv_pix_<id>`.

   Com os `bvs` preenchidos, o cancelamento passa, e o PIX vai ao acréscimo e à Planilha do mês do evento.
   **(deve falhar, menos a variante)**
5. **Dado** devolução **pendente** ligada ao evento, **Então** 409 "aprove ou rejeite antes de cancelar". **Dado**
   evento já cancelado, **Então** 409, e a tela recarrega o evento. **Dado** clique duplo, **Então** um registro
   só. **(deve falhar)**
6. **Dado** a Comercial (usuária real), o Financeiro ou o Figurino, **Quando** tentam cancelar, alterar a
   devolução ou ler a prévia, **Então** 403. Sem sessão, 401. **(deve falhar)**
7. **Dado** a escolha "Parte 600", **Então** a prévia mostra, com a mesma conta da execução:
   - pago 1.000 e já devolvido 0;
   - retido 400;
   - cheia 90 e comissão do retido 18;
   - quanto já foi liquidado, o ajuste e a data do repasse em que ele cai;
   - BV do retido 40;
   - a referência do imposto.

   A prévia não grava nada, e o que ela mostra é o que o ato grava logo depois, nos dias 1 a 5 e depois do dia 5.
8. **Dado** um cancelado com a devolução de 600 aberta (sem BV, comissão de 20 a pagar), **Quando** o Superadmin
   altera para 800, **Então** a comissão vira 10. Nos outros casos:
   - com a comissão de 100 já paga (e o ajuste de −90 a pagar), 800 → 500: o ajuste vai de −90 para −75 **no
     lugar** (Σ 25); se o −90 já estiver liquidado, nasce +15 no primeiro repasse aberto;
   - diminuir uma devolução já paga → 409;
   - duas alterações simultâneas de "Nada" para 300 → um complemento só.

   **(deve falhar: os dois últimos)**
9. **Dado** o exemplo-padrão (comissão 18, BV 40), **Quando** o Superadmin acrescenta um comprovante esquecido de
   R$ 200, **Então** o retido vira 600, a comissão 27 e o BV 60 na Planilha, sozinhos. Nos outros casos:
   - o Casting tenta acrescentar comprovante → 409;
   - o Casting tenta alterar a devolução → 403;
   - um comprovante que deixa o pago abaixo do devolvido → 409.

   **(deve falhar: o Casting e o comprovante abaixo do devolvido)**
10. **Dado** a devolução de um cancelado em Gastos Extras, **Então**:
    - "Salvar" sem mexer mantém destinatário, nome e PIX, e não marca "aprovado com edição";
    - corrigir o PIX passa;
    - mudar valor, data, categoria ou vínculo, excluir, aprovar ou rejeitar → 409 com o evento;
    - criar um gasto do tipo cliente, ou converter um gasto comum, → 400;
    - a devolução de evento vivo segue editável;
    - pago, no banco e desfazer, pela Planilha, seguem livres.

    **(deve falhar: os recusados)**
11. **Dado** um evento cancelado, **Então**:
    - aplicar orçamento dá 409 para todos que passam no gate;
    - excluir dá 409 ao Superadmin, e os demais seguem com 403 (`_can_delete()`, só Superadmin);
    - o `PUT …/acrescimos` de quem passa no gate de hoje e não é Superadmin (Comercial, Financeiro) dá 409
      `cancelado`.

    **(deve falhar)**
12. **Dado** o cancelado do exemplo, **Então** a tela mostra "Resultado do cancelamento" com 1.000 / 600 / 400 /
    18 / 40, sem `kpi`. O Casting não vê o bloco; comissão, BV, imposto e PIX só aparecem para quem vê o
    financeiro.
13. **Dado** um Google que falha, **Então** o cancelamento conclui com aviso. **Dado** a trava de ambiente
    ligada, **Então** zero chamadas e aviso. "Sincronizar" não toca o cancelado.
14. **Dado** pago maior que a venda, **Então** a comissão do retido é a cheia. **Dado** comprovante sem valor,
    **Então** ele conta zero e o impacto diz quantos são.
15. **Dado** o vendedor congelado de um cancelamento que já não vende nenhum evento, **Quando** alguém tenta
    excluir o usuário, **Então** a exclusão é recusada com o bloqueio "cancelamentos", sem erro 500. **(deve
    falhar)**

---

### História 3 — O cancelado na DRE pelo que ficou (+400, não −600), e o retido conta como venda (Prioridade: P1)

O dono e o Financeiro abrem a DRE do mês do cancelamento e veem o retido numa linha própria, com o BV e a
comissão do retido no custo e o imposto informado: +R$ 342 no exemplo, não −R$ 600. O mês do evento não mostra
nada dele. A Comercial vê o retido como venda do vendedor no mês do cancelamento.

**Por que esta prioridade**: é o pedido literal de 29/09 ("−600, sendo que ele é +400"). Sem isso, a DRE mente a
cada cancelamento (L402-407).

**Verificação**: cenários 20, 21, 22 e 24, com o 23 verde, e as partes da DRE do 12 e do 32. Do 21, a parte do
satélite fecha na História 5; a parte virtual fecha aqui, e a multa ligada ao cancelado é semeada por ORM, com a
categoria "Multa de cancelamento" criada na Fundação, sem esperar a História 6.

**Cenários de aceite**:

1. **Dado** o exemplo-padrão sem imposto, **Quando** se abre a DRE do mês do cancelamento, na tela nova e na
   antiga, **Então**:
   - a linha "Retido de cancelamentos" mostra R$ 400;
   - o custo tem +R$ 40 e as comissões, +R$ 18;
   - os gastos extras não têm os R$ 600;
   - o resultado é **+R$ 342** em Realizado e Total, e nada no Projetado;
   - API e Jinja batem ao centavo;
   - contra a `main`, o mesmo caso dá −600.
2. **Dado** o mesmo evento, **Quando** se abre o mês do evento, **Então** ele não aparece. A Tendência não tem os
   2.000 e tem +400 no mês do cancelamento.
3. **Dado** imposto informado de R$ 64, **Então** os impostos têm +R$ 64 e o resultado é +R$ 278.
4. **Dado** a devolução alterada para 800, **Então** o retido vira 200, com BV, comissão e resultado refeitos no
   mesmo mês, e nenhuma devolução em gastos extras. Pela conta desta spec, não escrita no plano: BV 20, comissão 9
   e resultado +R$ 171.
5. **Dado** uma multa ao elenco ligada ao cancelado, **Então** ela segue em gastos extras. O mesmo vale para uma
   devolução ligada a evento vivo. Nos outros casos:
   - satélite e venda virtual cancelados não trazem retido;
   - "Tudo" com BV de 200 já pago dá retido 0, comissão 0 e custo +200.
6. **Dado** as duas telas da DRE, **Então**:
   - ticket médio e "a receber" não mudam;
   - a Receita por Tipo ganha a barra de 400;
   - Fator R e break-even contam o retido;
   - a parcela do cancelado sai de Recebimentos Previstos;
   - a nota a emitir aparece com selo;
   - o vendedor tem +400 em Top Vendedores.
7. **Dado** qualquer mês sem cancelamento, **Então** DRE e Tendência são idênticas entre `main` e branch, centavo
   a centavo.
8. **Dado** o Dashboard Comercial do mês do cancelamento, **Então**:
   - o vendedor congelado tem +R$ 400 no total vendido e +R$ 18 na comissão prevista, com a sublinha "inclui R$ X
     retidos de N cancelamento(s)";
   - o mês do evento não tem os R$ 2.000;
   - `/admin/desempenho` mostra o retido e os cancelados;
   - a ficha da cliente soma 400;
   - a Performance da Home não conta cargo nem cachê do cancelado.

---

### História 4 — Dados de venda do cancelado: só o Superadmin corrige, e as contas se refazem (Prioridade: P2)

No cancelado, o Superadmin corrige o valor da venda, a taxa, a cortesia, a data, as parcelas e as notas, o
vendedor, os acréscimos e os reembolsos. O que acontece em seguida:
- retido, comissão e BV do retido se refazem na hora;
- a comissão paga fica como foi paga, e a diferença cai no primeiro repasse aberto de quem recebe;
- se o vendedor muda, o antigo devolve o que recebeu como saldo negativo e o novo recebe a comissão inteira, tudo
  auditável em Comissões.

Comercial e Financeiro só consultam.

**Por que esta prioridade**: o dono quer corrigir depois do fato ("podemos alterar valores e inserir pagamentos de
multas", 1c-Q7), mas isso depende das três primeiras Histórias. Fecha depois da História 3, porque o 16c confere o
Dashboard Comercial, e antes da 5 (L3490).

**Verificação**: cenários 16b, 16c, 16d e 16e. O 16b fecha com a variante "cheia 0" (cortesia/permuta com valor e
evento sem vendedor); o satélite cancelado do 16b fecha na História 5.

**Cenários de aceite**:

1. **Dado** um cancelado com a comissão cheia já paga, **Quando** o Superadmin corrige a venda de 2.000 para
   2.400, **Então**:
   - a venda e a comissão cheia são recongeladas;
   - comissão e BV do retido seguem a proporção nova;
   - a linha paga fica intacta, e a diferença vai ao primeiro repasse aberto.
2. **Dado** um cancelado sem taxa própria, congelado com 2,5% e com a comissão paga, **Quando** a taxa é corrigida
   para 3,0, **Então** a taxa congelada vira 3,0 e a diferença para mais entra no primeiro repasse aberto, com o
   motivo "Cancelamento: taxa corrigida". De 3,0 para 2,0, entra como desconto. A paga fica intacta.
3. **Dado** cortesia/permuta marcada, **Então** a cheia vira 0 e o que já foi pago é descontado no primeiro
   repasse aberto. No ato vale o mesmo: cortesia/permuta com valor, ou evento sem vendedor, cancela com cheia 0, e a
   comissão do evento vivo continua a de hoje.
4. **Dado** uma nota fiscal e uma parcela gravadas pelo Superadmin, **Então** o congelado não muda.
5. **Dado** a Comercial no `PATCH …/comercial` ou o Financeiro lançando nota, **Então** 409 `cancelado`. Num
   satélite cancelado, **Então** 409. **(deve falhar)**
6. **Dado** retido de 400, comissão do retido de 18, cheia de 90 já paga ao vendedor A e o ajuste −72 a pagar,
   **Quando** o vendedor vira B, **Então**:
   - a paga de 90 fica intacta;
   - o −72 vira −90 (o alvo de A é zero);
   - B ganha +18 no primeiro repasse aberto dele;
   - vendedor e beneficiário congelados passam a B;
   - o retido de 400 sai de A e vai a B no Dashboard Comercial e em `/admin/desempenho`;
   - a linha de A leva evento, −90, a paga que acerta e o motivo; a de B, evento, +18 e o motivo.

   Nos outros casos:
   - com a comissão só a pagar, a de A é cancelada e a de B nasce com 18;
   - B não comissionado → ninguém recebe;
   - no EducaManto, só o recorte comercial muda;
   - a Comercial tentando trocar → 409 `cancelado`. **(deve falhar: a Comercial)**
7. **Dado** um BV não pago, **Quando** passa de 200 para 300, **Então**:
   - o BV cheio congelado é 300, e o do retido, 60;
   - a cheia é recongelada sobre 2.000 − 300 com a taxa congelada;
   - o acréscimo mantém a mesma identidade;
   - a Planilha do mês do evento mostra o PIX novo;
   - mudar o transporte não mexe no congelado;
   - mandar o BV pago com outro valor → o valor pago fica, como no evento vivo (FR-052);
   - deixar o BV pago fora do corpo → 400 `items`, nada gravado e o pago intacto;
   - um acréscimo novo nasce;
   - o reembolso grava sem mexer no retido;
   - a Comercial no `PUT …/acrescimos` → 409 `cancelado`.

   **(deve falhar: o BV pago com outro valor, o BV pago ausente e a Comercial)**
8. **Dado** um cancelado com a padrão de 2,5%, **Quando** a padrão vai a 3% e o Superadmin corrige venda,
   vendedor e comprovante, **Então** tudo continua em 2,5%. Só a correção da taxa do próprio cancelado a leva a 3%.

---

### História 5 — Venda de vários dias cancela inteira ou em parte, sem desagrupar (Prioridade: P2)

O Superadmin cancela uma venda de vários dias de três jeitos:
- **Pelo principal, "Cancelar todos os dias"**: tudo numa confirmação, com o pago somando os comprovantes de todos
  os dias.
- **Um dia que não é o principal**: informa o novo valor da venda. O principal segue vivo com a venda nova; cheio,
  BV não pago e comissão acompanham.
- **Só o 1º dia**: a venda inteira passa ao próximo dia vivo, sem mudar valor nem data. A receita vai à DRE do mês
  do novo 1º dia.

**Por que esta prioridade**: hoje é raro (7 grupos no espelho, 1 com dias no futuro, nenhum cruzando o mês), mas
fica comum depois da 3b. É a costura natural se o dono quiser dividir a entrega; isso é decisão dele, não premissa
(L3535-3538).

**Verificação**:
- **Fecham aqui**: 29, 35, 37, 37b, 38 (com a variante 38-comprovante), 38c, 39 (com a variante da devolução do
  dia depois do principal cancelado), 41 e 42c.
- **Fecham em parte**:
  - 42: o aviso e o ensaio do antigo 1º dia fecham na História 6;
  - 42b: a multa fecha na 6;
  - 42d: o cachê pago fecha na 6.
- **Também fecham aqui**: as partes de vários dias dos cenários 4, 16b, 17 e 21.

**Cenários de aceite**:

1. **Dado** um grupo (principal com venda de 3.000 e mais 2 dias; comprovantes de 1.000 no principal e de 500 num
   dia; comissão de 75 a pagar), **Quando** o Superadmin escolhe "Cancelar todos os dias" com Parte de 900,
   **Então**:
   - os 3 dias são cancelados numa transação, sem desagrupar;
   - o pago é 1.500 e o retido, 600;
   - a comissão vira 15 no lugar;
   - cada dia ganha um histórico;
   - o Google recebe 3 remoções, depois do commit;
   - um dia já cancelado antes fica intocado.
2. **Dado** o grupo vivo, **Quando** se cancela só um satélite com venda nova de 2.000 e Parte de 300, **Então**:
   - o principal segue vivo com 2.000, que a DRE mostra no mês do evento;
   - a comissão a pagar vira 50 no lugar; se já estava paga, fica intacta e nasce −25 no primeiro repasse aberto;
   - a devolução de 300 fica ligada ao dia, fora dos gastos extras da DRE e dentro do "já devolvido";
   - o cheio vai de 3.300 a 2.200 (o selo de 10% fica igual);
   - o BV não pago cai na mesma proporção;
   - a cobrança da Home mostra 800 a receber.

   **Quando**, depois, o Superadmin usa "Alterar devolução" no dia cancelado e corrige a devolução de 300 para 30
   *(clarify de 15/10, resposta "A")*, **Então** a devolução do dia passa a 30, o "já devolvido" do grupo e a
   cobrança da Home se refazem, e a comissão do principal e a linha `dia` não mudam, com auditoria. Acima do pago
   do grupo menos as outras devoluções → 409. **(deve falhar: o acima do teto)**
3. **Dado** o corte anterior, **Quando** a aba Comercial do principal é gravada e as telas são reabertas, **Então**
   o −25 não é sobrescrito. **Quando** se cancela o resto depois, **Então** os 300 entram no "já devolvido".
   **Quando**, depois disso, o Superadmin usa "Alterar devolução" no dia cortado, **Então** o retido e a comissão do
   principal se refazem (D28, "Acompanham"); com o principal vivo, a comissão não muda.
4. **Dado** "Cancelar só este dia" **no principal**, **Quando** confirmado, **Então**:
   - a venda inteira passa ao dia vivo mais cedo, e o diálogo diz qual antes de confirmar;
   - cada linha mantém id, valor, datas, estado e beneficiário, e só o vínculo muda;
   - as somas de comprovantes, acréscimos, comissões e devolução ficam **iguais** antes e depois, em qualquer mês;
   - com o novo 1º dia no **mesmo mês**, DRE, Planilha, Comissões, Dashboard Comercial e cobrança também ficam
     iguais; noutro mês, vale o aceite 5;
   - o antigo 1º dia cancela como `dia`.
5. **Dado** o novo 1º dia noutro mês (31/10 → 01/11), **Então**:
   - receita, imposto, BV, cachês e comissão vão à DRE de novembro, e o BV à Planilha de novembro;
   - a data de venda e o ciclo da comissão comum não mudam;
   - a comissão EducaManto a pagar vai para 01/11;
   - a comissão própria que o novo principal já tinha fica fora da conta.
6. **Dado** os casos abaixo, **Então** nada muda de vínculo nem de valor:
   - `alcance` ausente → 400;
   - "só este dia" num principal sem outro dia vivo → 409;
   - devolução pendente ligada ao antigo 1º dia → 409;
   - cachê pago no antigo 1º dia → 409 `cache_pago` (fecha na História 6);
   - dia indicado que não é mais o vivo mais cedo → 409 `grupo_mudou`, e a tela refaz o impacto;
   - erro no meio → tudo desfeito;
   - duas confirmações → uma passa e a outra recebe 409;
   - a Comercial → 403.

   **(deve falhar)**
7. **Dado** um dia cancelado no grupo, **Então** soltá-lo dá 409, e agrupar evento cancelado, como satélite ou
   como principal, também dá 409. Desagrupar um dia vivo passa. **(deve falhar: os três primeiros)**
8. **Dado** um principal marcado pela 303, **Então** o impacto oferece "cancelar", leva todos os dias e tira a
   marca de cada um. Num satélite marcado, cancela só aquele dia, com a venda nova.
9. **Dado** o grupo do aceite 1 cancelado inteiro, **Quando** o Superadmin acrescenta um comprovante de R$ 200
   num dia, **Então** o pago do grupo vai a 1.700, o retido do principal a 800 e a comissão a 20, sozinhos. Num dia
   cortado com o principal vivo, nada se refaz; um comprovante que deixaria o pago do grupo abaixo do devolvido
   → 409. **(deve falhar: o abaixo do devolvido)**
10. **Dado** um corte de dia com a comissão do principal já paga e o ajuste negativo a pagar, **Quando** o
    Superadmin desfaz o "pago" da base pela Planilha e as telas são reabertas, **Então** a base vai ao alvo da
    venda nova no lugar e o ajuste é cancelado: a soma fica no alvo, sem desconto em dobro.

---

### História 6 — O ensaio cai junto, elenco e equipes são avisados, cachê pago recusa, e a multa ao elenco (Prioridade: P2)

**Quem é avisado e o que cai**:
- No mesmo ato, o ensaio do show cancelado cai, no banco e no Google.
- O elenco escalado recebe uma vez o e-mail que já existe.
- A equipe de Ensaio recebe o sino quando havia ensaio.
- O Casting recebe o pedido de tirar os escalados e avisá-los pelo WhatsApp.

**Cachê pago**: evento com cachê pago ao elenco não se cancela.

**Multa ao elenco**:
- O Superadmin informa a multa artista por artista, no ato ou depois, inclusive para quem o Casting já tirou da
  vaga.
- A multa vira Gasto Extra do mês, sem mexer em comissão nem em BV.

**Por que esta prioridade**: a resposta do dono pede (1c-Q3, Q4, Q8–Q11, 1c-Q10, 1c-Q12), mas depende das
Histórias anteriores. A multa no ato, a lista do elenco e a multa depois fecham juntas.

**Verificação**: cenários 33, 40, 42e, 43, 44 (com a variante dos dois sinos), 45, 45b e 45c. Fecham também aqui o aviso do 2b, o aviso e o
ensaio do 42, a multa do 4 e do 42b, e o cachê pago do 42d. Os dois primeiros casos do 40 já passam com a História 5.

**Cenários de aceite**:

1. **Dado** um evento passado com cachê pago (ou no banco), **Quando** se tenta cancelar pela API ou pelo marcado,
   **Então**:
   - a resposta é 409 `cache_pago`, com "Este evento tem cachê pago ao elenco e não pode ser cancelado. Para
     devolver dinheiro à cliente, lance uma Devolução em Gastos Extras.";
   - nada é gravado;
   - o marcado continua só com "Devolver ao Google";
   - a vaga de presença do técnico de som não conta.

   No grupo, a frase diz qual dia. **(deve falhar)**
2. **Dado** um evento do tipo Ensaio, **Então** 409 `ensaio`. **(deve falhar)**
3. **Dado** um show com 2 ensaios futuros, **Quando** é cancelado, **Então**:
   - os ensaios saem do banco na mesma transação e do Google depois do commit;
   - com a trava de ambiente, zero chamadas e aviso;
   - uma falha vira aviso, sem desfazer nada;
   - o histórico do show registra data e local de cada ensaio.
4. **Dado** 3 escalados, um deles em 2 dias e um que recusou o convite, **Então**:
   - cada pessoa recebe um e-mail só, e quem recusou não recebe;
   - o e-mail sai depois do commit, e zero envios reais fora da produção;
   - cada usuário ativo da equipe de Ensaio recebe `evento.cancelado` só se havia ensaio, um por ato (um corte de
     dia com ensaio e, depois, o "Cancelar todos os dias" com ensaio dão dois);
   - cada usuário ativo do Casting recebe `evento.cancelado_escala`, um por dia com escalados, `urgent` a 2 dias e
     `info` a 60 dias, com link para a aba de produção;
   - sem elenco, o Casting não recebe nada;
   - um cancelamento recusado não avisa ninguém;
   - no corte de um dia, avisa só o elenco daquele dia.
5. **Dado** 2 escalados, com multa de 150 para um e campo vazio (ou 0) para o outro, **Então**:
   - o bloco mostra "faltavam 60 dias" (ou 2), sem nenhum valor sugerido;
   - nasce 1 Gasto Extra "Multa de cancelamento", aprovado e a pagar, com nome e PIX do talento e a data do
     cancelamento;
   - Planilha e DRE do mês do cancelamento ganham +150;
   - retido 400, comissão 18 e BV 40 não mudam;
   - se o talento não tem PIX, o gasto nasce e a Planilha mostra "sem PIX";
   - um artista escalado em 2 dias aparece em 2 linhas do bloco, com vaga e dia, e cada valor vira o seu gasto.
6. **Dado** um cancelado sem multa no ato, **Quando** o Superadmin lança uma multa de 150 depois, **Então** ela
   entra com a data do lançamento, no mês do lançamento. Nos outros casos **(deve falhar)**:
   - em evento vivo → 409;
   - Casting e Comercial → 403.
7. **Dado** um artista que o Casting tirou da vaga do cancelado, **Então**:
   - ele não recebe e-mail de remoção (em evento vivo, recebe);
   - continua na lista do ato, marcado "saiu da escala", e a multa é aceita;
   - um artista fora da lista → 400 `fields.multa_<id>`. **(deve falhar)**
8. **Dado** um grupo SHOW com um ensaio ligado ao 1º dia e outro ligado a um dia que fica, **Quando** o
   Superadmin escolhe "Cancelar só este dia" no principal, **Então** (L1982):
   - o ensaio do antigo 1º dia sai do banco na transação e do Google depois do commit, com sino à equipe de
     Ensaio;
   - nenhum ensaio muda de `parent_event_id`;
   - o ensaio do outro dia não é tocado;
   - o "precisa ensaio" do novo principal fica como estava.

### Casos de borda

- **Valores fora do comum**:
  - **Pago maior que a venda**: a comissão do retido é a cheia (o teto), a DRE leva o retido inteiro e "Tudo"
    devolve o pago (L1969).
  - **Comprovante sem valor**: conta zero no pago. O impacto diz quantos são, e o diálogo avisa antes de oferecer
    só "Nada" (L2806-2808).
  - **Pago zero**: só "Nada" fica habilitado, e escolher continua obrigatório (L1550-1551).
  - **Cancelado sem venda e sem comprovante**: só "Nada". Fica fora da contagem e da DRE e aparece só na página de
    Cancelamentos (L2797-2805).
  - **"Tudo" devolvido com BV pago**: retido 0, comissão 0 e custo +BV pago (L1958).
- **Devoluções**:
  - **Devolução lançada antes do cancelamento**: conta como devolvido e sai do gasto do mês dela (L2876-2881).
  - **Devolução pendente ligada**: 409, até alguém aprovar ou rejeitar (L745-746).
  - **Parte digitada errada no corte de um dia**: o Superadmin corrige pelo "Alterar devolução" do dia cancelado,
    entre o já pago à cliente e o teto do grupo; a comissão do principal vivo não muda (FR-017, clarify 15/10). Se o
    principal já foi cancelado inteiro, a correção refaz o retido e a comissão dele (FR-017, D28).
- **Tipos de evento**:
  - **Venda virtual**: o diálogo pede só o motivo, e o estorno próprio continua, sem retido (L1549-1550).
  - **Evento do tipo Ensaio**: 409 `ensaio`.
- **Repetição e deploy cruzado**:
  - **Clique duplo, ou repetição depois do 502 do deploy**: 409 "já cancelado", e a tela recarrega o evento em vez
    de mostrar erro (L3676-3677).
  - **Bundle antigo com backend novo**: cancelar sem modo dá 400 legível.
  - **Bundle novo com backend antigo**: a trava de capacidade desabilita o envio (L3670-3677).
- **Google**:
  - **Falha na remoção**: vira aviso, sem desfazer o cancelamento. Com a trava, zero chamadas (L856-865).
  - **Cancelado que ainda está no Google**: o sync o pula, e "Sincronizar" não o toca (L1968).
- **Comissão e repasse**:
  - **Vendedor antigo sem repasse futuro**: o desconto fica a pagar, à vista, sem baixa (1e-Q8 = B; dívida).
  - **Dias 1 a 5 com o PIX do repasse já feito e a Planilha sem "pago"**: um desconto novo pode ser dado como
    liquidado sem ter sido descontado. A regra de uso é marcar no dia do PIX (L2716-2719).
  - **Desfazer "pago" de uma linha do cancelado pela Planilha (267c)**: a linha volta a "a pagar" com o mesmo
    valor, a invariante por beneficiário continua, e a sincronização automática segue sem tocá-la (leitura 11
    desta spec, conferida pelo `/speckit-plan`). No principal **vivo** depois de um corte, desfazer a base com o
    ajuste vivo não desconta em dobro (FR-057, cenário 38c).
- **Correções depois do ato**:
  - **Venda corrigida abaixo do retido**: não é recusada, porque comissão e BV têm teto no cheio (L807-809).
  - **Comprovante corrigido que deixa o pago abaixo do devolvido**: 409 `pago_abaixo_do_devolvido` (L802). No grupo,
    conta o pago do grupo inteiro.
  - **Comprovante num dia de grupo**: refaz o cancelamento `venda` do principal; com o principal vivo (dia
    cortado), nada se refaz (FR-018).
- **Grupos**:
  - **Grupo que muda entre abrir o diálogo e confirmar**: 409 `grupo_mudou`, e a tela refaz o impacto
    (L1280-1281).
  - **Principal sem outro dia vivo**: só "Cancelar todos os dias" (L1244-1246).
  - **Dia já cancelado num grupo**: não vira linha no diálogo, mas entra no "já devolvido" (L1231-1240).
  - **Satélite que vira principal com comissão própria paga** (o caso de R$ 137,50 no espelho): fica fora da
    conta e não vira desconto nem pagamento em dobro (L1038-1045).
- **Elenco e multa**:
  - **Talento sem PIX no cadastro**: a multa nasce, a Planilha mostra "sem PIX", e o diálogo avisa (L1986).
  - **Artista escalado em dois dias**: recebe um e-mail só, mas tem uma linha por dia na lista do ato, com uma multa
    possível em cada (FR-070).
  - **Quem recusou o convite e a vaga de presença do técnico de som**: ficam fora do aviso, da lista do ato e da
    régua de cachê pago.
- **Permissão**: o Superadmin "vendo como Comercial" recebe as flags apagadas, mas a API aceita pelo papel real.
  É o comportamento de hoje, só registrado (L1965).
- **Taxa**: mudar a taxa padrão depois não mexe em cancelado nenhum. Num evento com taxa própria, corrigir a data
  de venda não mexe na taxa (L1180-1185).

## Requisitos *(obrigatório)*

### Requisitos funcionais

**Regra única, congelamento e resumo**

- **FR-001**: Todo cancelamento DEVE seguir uma regra só de dinheiro, para o mesmo evento nunca ter duas contas.
  Vale para o evento marcado pela 303, o botão Cancelar (224), a venda inteira pelo principal e o corte de um dia.
  A exceção é a venda virtual, que mantém o estorno próprio, sem retido (regime `virtual`) (L674-681).
- **FR-002**: No ato, o sistema DEVE congelar:
  - valor da venda, comissão cheia, beneficiário da comissão, vendedor, se era com nota, imposto informado
    (vazio = não se aplica) e a taxa de comissão usada;
  - por acréscimo BV: recebedor, PIX, BV cheio e se estava pago ("no banco" conta como pago);
  - o elenco alcançado;
  - nos dias de grupo, o principal do ato;
  - no corte de um dia (só no regime `dia`), a venda e o valor cheio do principal antes e depois (L1264, L3613).

  Pago e devolvido NÃO DEVEM ser congelados: são lidos ao vivo, para que corrigir comprovante ou devolução refaça
  as contas. Nada DEVE ser recalculado da venda viva, só do congelado (L687-732, L1679-1680).
- **FR-003**: O regime DEVE ser um destes:
  - `venda`: venda inteira;
  - `satelite`: dia cancelado junto com o principal;
  - `dia`: dia de grupo cancelado sozinho, inclusive o antigo 1º dia que passou a venda;
  - `virtual`.

  Cancelado sem registro (anterior a esta entrega) é `legado`: comissão 0, imposto 0 e BV só o já pago
  (L687-688, L730-731).
- **FR-004**: Retido DEVE ser pago − devolvido, nunca negativo.
  - **Pago**: soma dos comprovantes da cliente, no grupo de todos os dias. Comprovante sem valor conta zero, e o
    reembolso a cobrar da cliente não entra.
  - **Devolvido**: devoluções "Devolução a cliente" aprovadas e ligadas ao evento (no grupo, a qualquer dia).
    Reconhece-se a devolução por categoria + vínculo + aprovação, **nunca** pelo tipo de destinatário. A devolução
    lançada antes do cancelamento conta.

  (L729, L772-775, L782-783, L2806-2808, L2871-2881)
- **FR-005**: Um resumo único do cancelado DEVE calcular, em Decimal e também em lote:
  - regime, venda congelada e pago;
  - cada devolução (valor, destinatário, estado `nao_pago`, `no_banco` ou `pago`) e o total devolvido;
  - retido, comissão do retido e o BV que conta (o proporcional ou o pago);
  - imposto gravado;
  - ciclo e beneficiário de cada linha viva de comissão.

  Leem dele: tela do evento, página de Cancelamentos, as duas DREs, Dashboard Comercial, `/admin/desempenho`,
  Planilha e Comissões. Nenhuma refaz a conta (L771-778).

**Cancelar e devolver**

- **FR-006**: Só o Superadmin DEVE poder cancelar com dinheiro, informando o motivo e a devolução, em evento
  marcado pela 303 ou não (L1513).
- **FR-007**: A devolução NÃO DEVE vir escolhida (D27). Tudo, Parte ou Nada é obrigatório no regime `venda`.
  - **Sem escolha**: 400 `devolucao_modo`, sem ramo de compatibilidade (o bundle antigo mostra a mensagem).
  - **Tudo**: o máximo devolvível (pago − já devolvido), que o servidor manda e a tela só mostra.
  - **Parte**: valor maior que zero e não acima desse máximo.
  - **Pago zero**: só Nada é aceito.
  - **Tudo e Parte**: nome e PIX de quem recebe são obrigatórios.

  O modo escolhido não muda depois; o modo corrente sai de pago × devolvido (L688-690, L755-757, L767-769,
  L1541-1551).
- **FR-008**: A devolução DEVE nascer como Gasto Extra **aprovado** e a pagar, na categoria "Devolução a cliente",
  com destinatário cliente, nome e PIX, ligado ao evento e com a data do cancelamento. Vira pagamento a fazer na
  Planilha do mês do cancelamento (L767-769, L1973).
- **FR-009**: Evento com nota DEVE exigir o imposto sobre o retido, em reais, de zero para cima, num campo vazio
  com "16% do retido" ao lado só como referência (D32). Sem nota, o bloco não aparece, e um imposto enviado sem nota
  dá 400 `fields.imposto_retido`, como no corte de um dia, que não tem retido. O imposto pode ser alterado depois
  (FR-017) (L691-692, L1547).
  - **A referência** (Living Spec do checklist): "16%" é o valor de hoje, não um literal. O rótulo mostra a
    alíquota que o servidor manda (`imposto_aliquota`, a de Configurações; vazia, vale 16), e a referência
    (`imposto_referencia`) é alíquota × retido, ao centavo com `ROUND_HALF_UP`. É só sugestão: a DRE lança o valor
    digitado.
- **FR-010**: No regime `venda`, todo BV **não pago** cuja proporção do retido dá mais que zero DEVE ter recebedor
  e PIX, vindos do acréscimo ou do diálogo.
  - Faltando, a resposta é 400 `bv_pix_<acrescimo_id>` e nada é gravado.
  - O que vier no corpo é gravado no acréscimo, na mesma transação e antes do congelamento, e copiado para o
    congelado.
  - BV com proporção zero ou já pago não pede nada, e o corte de um dia também não (o principal segue editável).

  É a regra do PIX da 3a aplicada ao BV que já estava no evento (L841-855).
- **FR-011**: Antes de confirmar, a tela DEVE mostrar a prévia calculada pelo servidor, com a **mesma conta** da
  execução:
  - pago, já devolvido e retido;
  - comissão cheia, comissão do retido e quanto já foi liquidado (pago e no banco);
  - o ajuste, e o ciclo e a data do repasse em que ele cai;
  - o BV do retido por acréscimo;
  - a referência do imposto.

  Valor inválido, negativo ou acima do recebido dá 400 `fields.devolucao` (ou `fields.venda_nova`). Nenhum
  dinheiro é calculado no navegador (L784-787, L1514, L1548, L1803).

  A prévia NÃO DEVE gravar nada, nem por autoflush, e o que ela mostra (retido, comissão do retido, ajuste, ciclo,
  data do repasse e BV do retido) DEVE ser o que o ato grava logo depois, também nos dias 1 a 5, quando o ajuste
  pode cair no ciclo anterior. A prova é a variante "prévia = execução" do 2 e do 8.
- **FR-012**: O sistema DEVE recusar com 409, sem gravar nada:
  - devolução "Devolução a cliente" **pendente** ligada ao evento ("aprove ou rejeite antes de cancelar"). Num
    grupo, vale a pendente ligada a **qualquer dia** do grupo, no "Cancelar todos os dias" e no corte, porque o
    teto da devolução lê o "já devolvido" do grupo e a pendente aprovada depois o mudaria; a frase diz qual dia
    (extra `dias`, como no `cache_pago`) (Living Spec do checklist);
  - evento já cancelado;
  - "Tudo" diferente do que o servidor calcula, devolvendo `max_devolucao`;
  - cancelamento simultâneo (o registro único estoura).

  Cada recusa leva o seu `codigo` (tabela "Códigos 409" do RBAC); um deadlock residual vira 409 `tente_de_novo`.

  A recusa do líder de grupo ("desagrupe antes") DEVE sair (Q1 = C) (L743-747, L751-752).
- **FR-013**: O ato DEVE ser atômico e seguir esta ordem:
  1. travar o evento e as linhas de comissão dele, **relendo-os** do banco;
  2. validar;
  3. congelar;
  4. registrar a devolução;
  5. calcular o alvo;
  6. reconciliar a comissão;
  7. marcar cancelado;
  8. gravar o histórico.

  Uma validação que falha não grava nada. Um "pago" marcado na Planilha no mesmo instante nunca vira "paga de 20"
  (L738-743, L866-874).
- **FR-014**: O evento marcado pela 303 DEVE cancelar sem chamar o Google e sem aviso do Google.
  - A marca sai com o motivo novo "cancelado" **antes** de gravar o cancelamento; depois, ela ficaria para sempre.
  - A recusa de evento marcado sai do cancelar e fica só na exclusão.
  - O servidor manda `acao: "cancelar"` para todo evento marcado.
  - O id `virtual-local-…` também não chama o Google.

  (L758-766, L1615-1617)
- **FR-015**: No evento não marcado, a remoção do Google DEVE acontecer **depois** do commit, fora da trava.
  - Uma falha vira `aviso` e não desfaz o cancelamento.
  - O evento que sobrar no Google não volta: o sync pula cancelado e "Sincronizar" não o toca.
  - A remoção DEVE respeitar a trava de escrita no calendário fora da produção (Princípio XIV): travada, conclui
    no banco, não chama o Google e devolve aviso.

  É premissa do plano, confirmada pelo `/speckit-plan` (P-26): a trava é lida a cada chamada, e chave ausente vale
  como travada (L856-865).
- **FR-016**: O histórico do cancelamento DEVE registrar, na hora real (hoje sai 3 h antes):
  - modo, valor devolvido e retido;
  - BV proporcional por recebedor e imposto;
  - dias cancelados e ensaios cancelados;
  - multa por escalação (artista, vaga e dia);
  - quem foi avisado.

  (L741-743, L765-766)
- **FR-017**: O Superadmin DEVE poder **alterar a devolução** do cancelado, informando o **novo total devolvido**
  e, se quiser, nome, PIX, observação e imposto (D28, D36; L788-799, L1515).
  - **Limites**: o piso são as devoluções pagas ou no banco; o teto é o pago.
  - **No `venda` em grupo** (Living Spec do checklist; data-model §7.2): o novo total é o devolvido do **grupo**.
    - O piso soma as devoluções pagas ou no banco de todos os dias **e** as devoluções aprovadas dos dias
      cortados antes (regime `dia`), que contam como fixas, porque só o "Alterar devolução" daquele dia as muda.
    - A devolução aberta do principal absorve a diferença primeiro. Depois dela, as abertas dos dias que
      cancelaram junto (regime `satelite`, lançadas antes do ato), em ordem de id: sem isso, uma devolução lançada
      antes num satélite ficaria sem caminho de correção, porque o satélite não tem "Alterar devolução" próprio e
      Gastos Extras a trava.
    - O teto é o pago do grupo.
  - **Como a diferença entra**: a devolução aberta absorve a diferença e fica uma só; se zerar, é excluída com
    auditoria. Sem devolução aberta e acima do piso, nasce um complemento à cliente, na Planilha do mês em que
    nasce. Vale também para o cancelado com "Nada".
  - **O que se refaz na hora**: retido, comissão e BV não pago. Comissão paga ou no banco é ajustada no primeiro
    repasse aberto, para mais ou para menos. BV pago nunca é reescrito. O imposto é regravado se vier; no
    `legado` (sem linha de cancelamento), `imposto_retido` no corpo dá 400 `fields.imposto_retido` e o PATCH não
    cria a linha nem congela nada (leitura 9).
  - **Recusas**: antes de travar, só 400 para `devolucao_total` ausente ou não numérico. Depois da trava, nesta
    ordem: 409 `nao_cancelado` (evento não cancelado); 409 `regime_sem_retido` (`satelite`, `virtual`; o `dia` tem a
    regra própria abaixo); 400 nos campos (`devolucao_total` negativo ou, no `venda` e no `legado`, acima do pago;
    nome e PIX; `imposto_retido` no `dia`, no `legado` ou sem nota); 409 `abaixo_do_piso`; e, só no `dia`, 409
    `acima_do_teto`.
  - É o único caminho que mexe na devolução travada, com auditoria e histórico.
  - **No dia cortado** (regime `dia`, a devolução de "Cancelar só este dia"; clarify de 15/10, resposta "A"):
    o "Alterar devolução" também vale, no dia cancelado. O novo total é o da devolução **daquele dia**; o piso
    são as devoluções dele pagas ou no banco; o teto é o pago do grupo menos as outras devoluções do grupo. Não
    há retido nem comissão a refazer (o principal segue vivo e a comissão dele segue a venda nova): refazem-se
    só a devolução do dia, o "já devolvido" do grupo e a cobrança da Home. `imposto_retido` no corpo → 400
    `fields.imposto_retido`. Sem isso, uma Parte digitada errada no corte ficava para sempre na Planilha e na
    cobrança, sem caminho de correção.
  - **Dia cortado depois de o principal ser cancelado inteiro** (derivado da D28, "Acompanham"): a devolução do
    dia passa a ser devolvido daquela venda (FR-004), então o "Alterar devolução" do dia refaz também o retido, a
    comissão do retido e o BV do retido do principal, na mesma transação, com o ajuste da comissão já paga no
    primeiro repasse aberto. O "não mexe em comissão" do clarify de 15/10 vale enquanto o principal vive.
- **FR-018**: O Superadmin DEVE poder acrescentar, corrigir e excluir comprovante de evento cancelado, inclusive o
  da multa contratual que a cliente paga depois (D36; L800-802, L2863-2870).
  - Retido, comissão e BV se refazem na mesma transação.
  - **Num dia de grupo**: o pago é do grupo (FR-004), então o comprovante de qualquer dia (inclusive `satelite` e
    `dia`) refaz o cancelamento `venda` do principal quando ele está cancelado inteiro. Com o principal vivo (dia
    cortado), nada se refaz: a comissão do principal segue a venda viva, e o "já devolvido" e a cobrança da Home são
    lidos ao vivo.
  - Pago novo do grupo abaixo do já devolvido dá 409 `pago_abaixo_do_devolvido`, sem gravar nada. A guarda vale em
    todo cancelado e no grupo com dia cancelado; em dia **vivo** do grupo fica fora (dívida no `docs/05`).
  - Comprovante recusado não deixa arquivo salvo.
  - Dinheiro pago depois do cancelamento entra como comprovante e conta no mês do cancelamento.
  - A comissão nunca passa da cheia.
- **FR-019**: A devolução de evento cancelado DEVE ficar travada nos seis caminhos de Gastos Extras: criar,
  aprovar, rejeitar, editar, excluir e vincular a evento (L1093-1104, L1973).
  - **Travados**: valor, data, categoria, vínculo e exclusão, recusados com 409, `fields` e o evento. A recusa
    vale quando o campo chega **diferente** do gravado, não só quando chega.
  - **Livres**: nome, PIX e descrição.
  - **Caminho inverso pela edição** (Living Spec do checklist): o `PATCH` recusa com o mesmo 409
    `devolucao_travada` o gasto que **passaria a ser** devolução de cancelado: um gasto ligado a evento cancelado
    que troca a categoria para "Devolução a cliente" (inclusive uma multa, que é livre), e uma devolução de evento
    vivo religada a um cancelado pelo `event_id`. É a mesma regra que o criar e o vincular já seguem: o
    predicado vale para o gasto gravado **e** para o gasto como ficaria, e os dois eventos travam em ordem de id.
    Sem isso, o devolvido mudaria sem refazer o retido e passaria do teto (SC-006).
  - Aprovar e rejeitar devolução de cancelado também são recusados.
  - O estado de pagamento (pago, no banco, desfazer) continua pela Planilha, fora da trava. Na Planilha nova,
    marcar pago ou no banco confere o valor que a tela mostrou (FR-040).
  - O gasto informa se está travado e se o evento está cancelado.
  - **Na tela**: Gastos Extras rotula a devolução como "Devolução à cliente" no formulário e na tabela (hoje
    "fornecedor", `GastosExtrasPage.tsx:528`), carrega e reenvia nome e PIX do tipo `cliente` e trava os campos
    por `expense.locked` (não por papel), com link para o evento (L1618-1620).
- **FR-020**: O tipo de destinatário cliente DEVE seguir estas regras (L769-770, L1099-1104):
  - Criar gasto com destinatário cliente, ou converter um gasto comum nele, DEVE ser recusado com 400
    "Devolução à cliente nasce pelo cancelamento do evento".
  - Numa devolução existente, o tipo cliente fica mesmo com corpo vazio ou "fornecedor" (bundle antigo).
  - Nome e PIX só trocam com valor não vazio.
  - Devolução de cancelado nunca vira "aprovado com edições".
  - Tocar uma devolução aberta regrava o destinatário cliente e completa nome e PIX vazios, vítimas do "Salvar"
    antigo.
- **FR-021**: Excluir evento cancelado DEVE ser recusado no núcleo, com 409 na API e aviso na rota Jinja. Cancelar
  não tem volta, e o cancelado por engano se recria à mão. Aplicar orçamento num cancelado DEVE dar 409 para
  todos, porque recriaria acréscimos e venda de uma vez (L1013-1016, L1108, L1157-1158, L2882-2891).
- **FR-022**: A tela do evento cancelado DEVE mudar assim (L1522, L1578-1591, L1869-1871):
  - **"Resultado do cancelamento"**: a grade "Resultado" do quadro Comercial ganha esse nome e mostra pago,
    devolvido com estado, retido, comissão do retido, BV e imposto.
  - **"Alterar devolução"**: botão com diálogo próprio (novo total, nome, PIX, observação e imposto; o BV não tem
    campo, porque acompanha o retido), que aparece pela flag do servidor (L1582-1583, L1871).
  - **Antigo 1º dia que passou a venda**: a tela diz para qual dia ela foi, com link (L1588-1589).
  - **`kpi`**: não é mandado, porque contaria a devolução como custo e o BV cheio. A aba Comercial continua
    aparecendo sem ele.
  - **Pendência "em aberto"**: dá lugar à devolução e ao retido.
  - **Link para Comissões**: aponta o ciclo e o beneficiário do ajuste.
  - **Caixa do cancelado**: termina com "saiu da agenda e das listas; fica na página de Cancelamentos e no card do
    período".
  - **Botões do Google**: "Sincronizar" e "Editar no Google Agenda" não aparecem; já somem hoje, então é só
    conferência.
  - **Quem vê o quê**: o bloco aparece só para quem vê o comercial; comissão, BV, imposto, PIX e taxa, só para
    quem vê o financeiro; o Casting não vê o bloco.
  - **Por onde se chega**: a tela abre pela página de Cancelamentos, pelo card do período, por link direto e pelo
    sino, para quem já abre evento hoje.
- **FR-023**: O diálogo de cancelar DEVE (L1540-1577, L1642-1647):
  - **Ao abrir**:
    - começar sem modo marcado, com "A cliente pagou R$ X" ao lado;
    - sugerir o nome uma vez por abertura e limpar tudo ao fechar.
  - **Campos**:
    - mostrar o valor só em Parte (em Tudo, só leitura), e nome e PIX só em Tudo e Parte;
    - com pago zero, habilitar só "Nada" e avisar quantos comprovantes estão sem valor;
    - mostrar o bloco "BV do parceiro" sem campo de valor: cheio, proporcional (da prévia) e "já pago". Quando
      faltam, recebedor e PIX são obrigatórios, com o aviso de que esse PIX vai à Planilha;
    - mostrar o bloco "Imposto sobre o retido" só quando há nota;
    - mostrar o bloco "Efeito na comissão" com o valor que vem do servidor;
    - na venda virtual, pedir só o motivo;
    - não trazer o bloco opcional "o que foi pedido", só leitura: ele é da 2a, que o monta e o acrescenta. Esta
      entrega não constrói nada dele, nem a propriedade no diálogo, e o diálogo é o mesmo sem ele (L3228-3230).
  - **Frase do que mais acontece** (L1565-1569, L1864):
    - "O ensaio de DD/MM também será cancelado";
    - "N artistas recebem o e-mail de cancelamento", que fica com a 1c-Q12 = A (L1566-1567, L5126);
    - "a equipe de Ensaio é avisada no sistema", quando havia ensaio;
    - "O Casting é avisado no sistema para tirar os N artistas da escala e avisá-los pelo WhatsApp".
  - **Envio**:
    - deixar Cancelar desabilitado até tudo estar informado, e mostrar cada erro no campo certo;
    - em "Tudo", mandar o `max_devolucao` da última resposta e, no 409 de divergência, refazer o impacto;
    - com backend antigo (sem `regime`), desabilitar o envio com "O sistema está atualizando — tente em um
      minuto";
    - tratar o 409 "já cancelado" recarregando o evento.
  - **Prévia**:
    - consulta separada do impacto, mantendo a anterior na tela;
    - pedida ao escolher Tudo ou Nada, ou depois de digitar a Parte (≥ 400 ms);
    - com o valor como decimal com ponto.
  - **Releitura depois de gravar** (L1872):
    - o cancelamento invalida o cache do principal, de cada dia e, na passagem, do novo principal;
    - as mutações de `POST …/multas`, `PATCH …/comercial`, `PUT …/acrescimos` e reembolso no cancelado releem o
      evento, porque o resumo muda.
- **FR-024**: O evento marcado DEVE ganhar a segunda saída (L1607-1617, L1647-1648, L1872):
  - "Excluir ou cancelar" deixa de ficar desabilitado e abre em "cancelar", com o aviso de que o evento já não está
    no Google.
  - O banner ganha a segunda saída, com largura total no celular.
  - A promessa "chega na próxima entrega" vira "devolva ao Google ou cancele" no banner, no botão "Analisar e
    decidir", no motivo de só devolver e na mensagem de recusa do marcado.
  - Depois de cancelar ou excluir, a faixa de sumidos se corrige na hora, sem esperar o poll de 60 s.
- **FR-025**: A página de Cancelamentos DEVE trazer, por cancelado, o resumo (FR-005) com **todas** as devoluções
  e o estado no banco; hoje ela mostra só a primeira (premissa do plano, L3404-3408; L345-347, L1523, L1636).
  - **Na tela, aqui**: `EventosCancelamentosPage.tsx` passa a mostrar o resumo, todas as devoluções e o estado
    `no_banco` (`:29-32`), obrigatórios porque o payload muda (L1636, L1879, L3404-3405).
  - O campo antigo `devolucao` fica por um ciclo de deploy.
  - O PIX só aparece para quem vê o financeiro.
  - O gate continua o de hoje, só Superadmin. Ficam com a 1c o gate do Financeiro, o item de menu, os filtros, o
    total e o redesenho da tela.
- **FR-026**: Toda tela nova DEVE seguir os princípios abaixo. O mobile-first (X) não se aplica, porque nenhuma
  superfície pública ou do portal muda (L1638-1649, L1808-1809).
  - **IX**: usar o campo monetário e a formatação de `@manto/money` no imposto, no novo total, no novo valor da
    venda e na multa por escalação.
  - **XI**: abrir e fechar diálogos com a transição dos outros, respeitando o movimento reduzido.
  - **V**: transformar toda recusa do servidor em frase em português.
  - **XIII**: decidir as travas pelas flags do servidor e por `expense.locked`, nunca pelo papel no React.

**Comissão**

- **FR-027**: "Comissão cheia" DEVE ter uma definição só, a mesma no congelamento, na prévia e na linha (L878-883).
  - Existe se o evento é venda, tem beneficiário, o beneficiário recebe comissão, não é cortesia/permuta e não é
    venda virtual. Cortesia/permuta com valor e evento sem vendedor dão cheia 0.
  - A comum é (venda − BV) × taxa. A EducaManto desconta o cachê do elenco, como hoje.
  - A comissão do evento vivo NÃO DEVE mudar número nenhum (regressão `main` × branch, cenário 1). Hoje ela zera só
    venda nula, Loja Virtual e beneficiário que não recebe comissão, e o evento sem vendedor tem comissão na DRE.
    Por isso a regra de hoje fica intocada, e a cheia é uma camada acima dela, que primeiro confere o beneficiário
    comissionado (sem beneficiário, sem comissão, cortesia/permuta ou Loja Virtual → 0). A variante "cheia 0" do
    16b prova a camada; o 1 prova que a comissão do vivo não mudou.
- **FR-028**: A comissão do retido DEVE ser mín(cheia, arredondada(cheia × retido ÷ venda)). Vale 0 quando venda,
  retido ou cheia são menores ou iguais a zero. Pago maior que a venda dá a cheia (D14, D25, Q2; L775-777,
  L1969).
  - **Arredondamento e tolerância** (Living Spec do checklist): "arredondada" é ao centavo, com `ROUND_HALF_UP`,
    na comissão e no BV do retido (FR-039), pela mesma conta de proporção da 305. Ela herda a tolerância de
    R$ 0,01: retido a até um centavo da venda vale o cheio, porque um centavo de diferença não é desconto. É a
    borda que decide o número quando o cliente pagou a venda inteira com um centavo de arredondamento.
- **FR-029**: A taxa usada no ato DEVE ficar congelada (L884-898, L903-906, L1179-1180).
  - **Qual taxa**: a do evento, se houver; senão a configurada na data de venda (1e-Q2). Até a 1e subir, é a
    padrão do dia do ato (hoje 2,5%). No EducaManto, a do dia, até o repensar da 1e-Q1 (L3113-3117,
    L3369-3370).
  - **Depois do ato**: todo recongelamento (venda, cortesia, vendedor, acréscimo, comprovante, devolução) DEVE
    reusar a taxa congelada.
  - A taxa padrão das Configurações nunca alcança um cancelado, e nenhum ponto lê a taxa padrão por fora da regra
    única.
- **FR-030**: A reconciliação DEVE manter, **por beneficiário**, Σ (a pagar + no banco + pago) = alvo. Ela é
  idempotente e trabalha com todas as linhas ainda ligadas ao evento (L907-918, L1942).
  - Linha paga ou no banco nunca é reescrita.
  - **O alvo de cada beneficiário**: a comissão do retido para o beneficiário congelado e 0 para todo outro
    beneficiário com linha viva ligada ao próprio evento. É o caso do vendedor trocado no evento vivo antes do ato,
    que devolve o que recebeu no primeiro repasse aberto dele (derivado da Q16 = A, a mesma regra da troca de
    vendedor no cancelado; no espelho, zero casos fora do 287, que é o da linha abaixo).
  - **Só as linhas do evento**: num grupo, a comissão própria de outro dia (a linha com o `event_id` do satélite,
    molde do 287) fica fora da conta no "Cancelar todos os dias", no corte e na passagem (P-29, P-51): não é
    reconciliada, cancelada nem ajustada.
  - falta = alvo − liquidadas.
  - Falta = 0: toda linha a pagar vira cancelada, e nunca fica linha a pagar de R$ 0,00.
  - Falta ≠ 0: a linha a pagar mais antiga recebe a falta, e as outras são canceladas.
  - Sem linha a pagar: nasce uma linha, positiva ou negativa, ligada à paga.
  - O ajuste de linha já liquidada vai a quem a recebeu; linha nova sem liquidada vai ao beneficiário congelado.
  - Evento com venda e sem linha de comissionado ganha a linha no cancelamento. Vendedor sem comissão: cheia 0, e
    nada nasce.
- **FR-031**: Linha nova DEVE cair no **primeiro repasse aberto** do beneficiário (D14; L960-969).
  - **Qual ciclo**: o do mês anterior, só nos dias 1 a 5 e só se o beneficiário ainda tem ali uma linha que abre
    ciclo; senão o mês corrente; senão o seguinte. Um ciclo está **liquidado** quando o beneficiário tem linha
    nele e nenhuma abre ciclo; a busca avança no máximo 24 ciclos e, sem achar, usa o ciclo corrente (Living Spec
    do checklist; R5).
  - **Datas da linha**: a data da venda e a de liberação são a de hoje, presa ao intervalo desse ciclo, para que
    Planilha e Comissões mostrem o mesmo.
  - **"Linha que abre ciclo"**: um predicado único — a pagar, valor diferente de zero e ligada a evento (ou sem
    linha original). Linha de R$ 0,00 e estorno órfão não abrem ciclo.
  - Repasse liquidado nunca é reaberto.
  - Item de soma zero com linhas de valor não some da Planilha.
  - O dia 5 é uma constante única, e os dois literais 5 de hoje ganham comentário, sem refatorar (L968-969).
- **FR-032**: Linha atualizada no lugar NUNCA DEVE mudar de data (L970-977).
  - A comissão EducaManto a pagar do cancelado fica no ciclo da data do evento (Q2 = A).
  - A linha nova **positiva** de EducaManto nasce com liberação na data do evento, quando essa data ainda não
    passou.
  - O ajuste negativo de EducaManto já paga vai ao primeiro repasse aberto.
- **FR-033**: Toda linha de comissão criada ou ajustada por esta entrega DEVE levar:
  - o evento (vínculo e título);
  - o valor, negativo no saldo a devolver;
  - a ligação com a linha paga que ela acerta;
  - o motivo, como prefixo da nota, tirado de uma lista única com o código que a 1e vai usar:

  | Motivo (prefixo da nota) | Código para a 1e |
  |---|---|
  | "Cancelamento: comissão do retido" | `cancelamento` |
  | "Cancelamento: vendedor trocado — devolve o já recebido" | `troca_de_vendedor` |
  | "Cancelamento: vendedor trocado — comissão do retido" | `troca_de_vendedor` |
  | "Cancelamento: taxa corrigida" | `correcao` |
  | "Cancelamento: correção da venda" | `correcao` |
  | "Corte de dia: venda diminuiu" | `corte_de_dia` |
  | "Exclusão do evento" | `exclusao` |
  | "Troca de tipo" (só declarado; usado pela 2b) | `troca_de_tipo` |

  Nenhum ajuste nasce sem evento, sem motivo ou somado a outro. É o "tudo bem auditado pela tela das comissões"
  da Q16 (L931-959).
- **FR-034**: A sincronização automática de comissões NÃO DEVE tocar as linhas do cancelado; ela roda ao abrir
  Comissões e a Planilha e nas gravações do evento (L978-981, L1019-1028, L1944).
  - Essas linhas são da reconciliação. O retorno da Loja Virtual continua antes.
  - Reabrir as telas mantém Σ = alvo.
  - Um ajuste (linha com linha original) nunca é tomado como "a comissão do evento" na próxima gravação.
- **FR-035**: Só o estorno **órfão** (evento apagado ou legado da 224) DEVE entrar pelo resgate do mês corrente,
  por um predicado único. O ajuste desta entrega entra pela via normal e nunca é liquidado pelo "Pagar Mês" de
  outro mês (L982-990).
- **FR-036**: A exclusão de evento com comissão paga **ou no banco** DEVE gerar o estorno no primeiro repasse
  aberto. Vale para o botão Excluir e para o sync de evento vazio (D23, 1b-Q3; L998-1018).
  - O estorno não copia as datas da venda e leva o motivo "Exclusão do evento".
  - Os estornos antigos (151, 211) não são tocados.
- **FR-037**: A tela de Comissões DEVE mostrar o estado "No banco" (L990-997, L1049-1050, L1526-1527, L1621-1623,
  L1873):
  - nas consultas do mês;
  - na lista de vendedores (quem só tem "no banco" não some);
  - nos rótulos;
  - no total `total_no_banco`, com total do mês = pago + no banco + a pagar.

  Além disso:
  - Comissões e Planilha DEVEM mostrar, por linha, o tipo (comissão, ajuste ou estorno) e o ciclo.
  - O item de comissão da Planilha DEVE trazer as linhas (tipo, evento, valor, ciclo).
  - Data sem hora deixa de aparecer um dia antes.
  - A exportação usa o mesmo rótulo de status.
  - A tela Jinja de Comissões fica fora (dívida).
- **FR-038**: Nenhuma linha de comissão anterior a esta entrega DEVE nascer, mudar ou ser cancelada por ela.
  Isso inclui os estornos 151 e 211 e o pago a menos ou a mais do passado: sem lista, acerto nem lançamento
  (1b-Q3, 1b-Q7; L1963, L2688-2691).

**BV**

- **FR-039**: Cancelado o evento, cada acréscimo BV DEVE valer o **BV do retido** = mín(BV cheio congelado,
  arredondado(BV cheio × retido ÷ venda)), que dá 40 no exemplo (Q2 = A, Q10 = A; L700-705, L778-782, L804-805,
  L1777-1779).
  - Calcula-se ao vivo, pela conta única de proporção do BV (a da 305), sem campo, sem ajuste manual e nunca
    gravado como número enquanto está a pagar.
  - Acompanha toda correção do cancelado: comprovante, devolução, venda e acréscimo.
  - A multa ao elenco não o muda.
  - Corrigir a venda ou a taxa não muda o BV cheio congelado.
  - **BV pago depois do ato** (leitura 10): marcado pago ou no banco na Planilha, ele fica pelo valor que estava a
    pagar naquele instante, guardado no congelado do BV; correção posterior não o reescreve nem gera acerto ao
    parceiro. Desfeito o pago (no ato ou depois), volta ao proporcional, porque deixou de estar pago.
- **FR-040**: A Planilha (nova e antiga) DEVE mostrar o BV por esta regra (L828-840; `specs/305-…/research.md`
  R11):

  | Situação | O que aparece |
  |---|---|
  | Evento vivo | o valor |
  | `venda` | o valor pago, enquanto pago ou no banco (o do ato, ou o do instante em que a Planilha o marcou); senão o proporcional (zero some) |
  | `venda` sem congelado, `legado`, `satelite`, `dia`, `virtual` | o valor, se pago ou no banco; senão nada (D23) |

  - O BV fica no **mês do evento** (data original), com recebedor e PIX do acréscimo.
  - BV pago, ou no banco, **nunca** é reescrito nem escondido, em regime nenhum.
  - Fecha o risco aceito da 305: cancelar e recriar do mesmo orçamento listava dois BVs. E não quebra a conferência
    do valor esperado ao marcar pago.
  - **Marcar o BV** na Planilha nova e na antiga passa por uma regra só, que trava o evento antes do acréscimo e
    confere o valor esperado contra o que a Planilha mostra (no cancelado, o proporcional): divergente → 409 com o
    valor atual; BV que não está a pagar → 409 `bv_nao_esta_a_pagar`. A Planilha antiga não manda o valor esperado
    e recebe a segunda recusa como aviso.
  - **Devolução de cancelado na Planilha nova**: ao marcar pago ou no banco, a tela manda o valor que mostrou
    (`valor_esperado`), no BV e na devolução. Divergente do gravado → 409 "A devolução mudou para R$ X…". Sem o
    campo (tela antiga, ação em lote), vale o comportamento de hoje.

**DRE e comercial**

- **FR-041**: As DREs Realizado e Total, na tela nova e no Jinja, DEVEM lançar o cancelado no **mês do
  cancelamento**, que é o do registro no sistema, não uma data informada (D30, D32; L1053-1058, L1069-1070,
  L2892-2895):

  | O que | Onde entra |
  |---|---|
  | retido | Receita Bruta, numa linha "Retido de cancelamentos" logo abaixo |
  | imposto gravado (nunca alíquota × retido) | Impostos |
  | BV do retido (ou o pago) | custo |
  | comissão do retido | Comissões |

  - O Projetado não muda.
  - Os cachês do cancelado ficam fora, e o mês do evento não mostra nada dele.
  - API e Jinja batem ao centavo.
  - `n_eventos`, `n_normais` e `n_permutas` não mudam.
  - A linha do retido e o aviso nos impostos aparecem pela **quantidade** de cancelados, não pelo valor:
    cancelado com retido zero mostra R$ 0,00.
- **FR-042**: Os gastos extras do período DEVEM ser todo gasto aprovado **menos** a devolução de evento cancelado
  (L1059-1061, L1267, L2876-2881).
  - Isso inclui a devolução ligada a um dia cortado e a lançada antes do cancelamento, que sai do mês dela.
  - A multa ao elenco e a devolução de evento vivo continuam.
  - Sem isso, o mesmo caso daria 400 − 40 − 18 − 600 = −258: a FR-027 e a FR-028 do rascunho são inseparáveis
    (`specs/303-sync-nao-apaga-venda/entregas-2-e-3-rascunho.md:581-582`; o plano não traz esse número).
- **FR-043**: Os painéis da DRE DEVEM tratar o cancelado assim (L1061-1068, L1628-1630, L1847):
  - **Tendência**: o cancelado NÃO DEVE contar venda, cachê nem evento. O retido DEVE somar em receita e lucro no
    mês do cancelamento, só quando é diferente de zero, para os meses sem cancelamento saírem idênticos.
  - **Recebimentos Previstos**: excluem cancelado.
  - **Nota a emitir de cancelado**: continua, com selo (`cancelado`, `retido`; no Jinja, no título).
  - **Top Vendedores**: usa o retido por vendedor nas duas telas.
  - **Indicadores**: o retido entra em margens, custo de talento ÷ receita, Fator R, break-even e numa barra da
    Receita por Tipo. Fica fora de ticket médio, "a receber" e contagem de eventos.
  - **Ticket médio do Jinja**: passa a dividir pela venda dos eventos com venda, como a API.
- **FR-044**: Os cancelados do período DEVEM sair de uma fonte única, a mesma das duas DREs, do Dashboard
  Comercial, de `/admin/desempenho` e da página de Cancelamentos (L814-827, L2797-2805).
  - **Recorte**: pela data do cancelamento, com recorte opcional pelo vendedor congelado, sem Ensaio nem Virtual e
    seguro contra tipo nulo. Regime e vendedor vêm do congelado.
  - **Quem traz dinheiro**: só `venda` e `legado` trazem retido, comissão e BV do retido. `satelite` e `dia`
    (inclusive o antigo 1º dia que passou a venda) entram com zero, porque o retido do dia cortado já está na
    venda nova do principal, no mês do evento.
  - **Contagem**: `satelite` e `dia` não contam em `n_cancelados`, que conta vendas, não dias.
  - Cancelado sem venda e sem pago fica fora da contagem e da DRE (premissa do plano).
- **FR-045**: O payload do dashboard financeiro DEVE trazer `paineis.cancelamentos` **sempre**, com quantidade 0
  quando não há cancelado. Ele leva quantidade, pago, devolvido e quanto falta pagar da devolução, retido,
  comissão do retido, BV, imposto, efeito no resultado e a lista com link. As chaves `retido_cancelamentos` e
  `n_cancelados` DEVEM estar sempre presentes nas DREs Realizado e Total. O card que lê isso é da 1c (L1056-1057,
  L1528).
- **FR-046**: O retido DEVE contar como venda do **vendedor congelado** no mês do cancelamento (D33; L1072-1078,
  L1634-1635):
  - **Dashboard Comercial**: entra no total vendido e na comissão prevista, com a sublinha "inclui R$ X retidos
    de N cancelamento(s)". O retido entra no total vendido do **vendedor** congelado; a comissão do retido entra na
    comissão prevista do **beneficiário** congelado, que no EducaManto não é o vendedor (Living Spec do checklist;
    R22).
  - **Top Vendedores** das duas DREs.
  - **`/admin/desempenho`**: retido e cancelados por vendedor; o cancelado sai do mês do evento.
  - **Só venda viva**: ticket médio, eventos fechados e desconto concedido.
  - **Ficha da cliente**: o total vendido inclui o retido; "Com evento" e "Recorrentes" não contam cancelado.
  - **Performance da Home**: ignora cancelado, porque não tem venda.
  - **Lista Jinja `/vendas/`**: filtra cancelado.
  - **Status de pagamento do evento**: ganha "cancelado".
  - Não existe "meta" no Dashboard; a meta é o próprio total vendido.

**Dados de venda do cancelado**

- **FR-047**: Só o **Superadmin real** DEVE mexer nos dados de venda do cancelado, por **uma** regra de
  permissão, sem parâmetro de "qual dado", chamada em todas as portas de (a) a (h) (1c-Q8 = A; L1110-1115,
  L1187-1197, L1215-1221).
  - **Quem passa no gate de hoje mas não é Superadmin** (Comercial, Financeiro, Casting, Figurino) DEVE receber
    409 `codigo: "cancelado"`, com uma frase dizendo que no cancelado só o Superadmin corrige os dados de venda.
  - **Quem já não passa no gate** recebe 403, como hoje.
  - **No `PATCH …/comercial`**: essa regra roda **antes** da checagem de taxa e vendedor da 215b, para a Comercial
    receber o 409 e não o 403 de campo.
  - **Flags**: o detalhe do evento DEVE trazer `flags.can_edit_venda_cancelado` (acesa só para o Superadmin) e
    `flags.can_edit_pagamentos`, calculadas no servidor.
  - **Jinja** (P-27, confirmada e estendida pelo `/speckit-plan`; L1220): o Jinja não recongela, então o
    despachante da tela antiga do evento recusa o cancelado com aviso **para todos os papéis, inclusive o
    Superadmin**, nas ações de dinheiro: aba Comercial, venda, os três de comprovante e os três de reembolso. O
    Superadmin corrige pela tela nova. A rota Jinja que muda o estado de uma linha de comissão
    (`set_commission_status`) recusa linha de evento cancelado, e a Planilha antiga trava o evento antes de mudar o
    estado de uma devolução de cancelado.
  - **Edição completa** (`PATCH /api/events/<id>`, o "Editar tudo"): no cancelado, venda, valor cheio, taxa,
    vendedor, cortesia/permuta ou nota que chegue **diferente** do gravado dá 409 `cancelado` **para todos os
    papéis**, com "corrija os dados de venda pela aba Comercial", porque essa porta não recongela. "Editar tudo"
    some no cancelado.
- **FR-048**: No cancelado ficam abertos estes dados, e só eles (L1121-1159):
  - (a) comprovantes, inclusive o da multa contratual;
  - (b) devolução e imposto;
  - (c) valor da venda, taxa e cortesia/permuta;
  - (d) data da venda, forma de pagamento, parcelas, vencimento, nota solicitada, valor antes do desconto,
    transporte, cronograma de parcelas e notas fiscais;
  - (e) multa ao elenco depois do ato;
  - (f) vendedor;
  - (g) acréscimos;
  - (h) reembolsos a cobrar.

  O orçamento fica travado para todos. O resto da tela é da trava geral da 1c; até ela subir, continua editável.
- **FR-049**: Corrigir um dado de venda do cancelado DEVE recongelar na mesma transação da gravação, só no regime
  `venda`, conforme a tabela abaixo (L1161-1176, L807-809).
  - Linha paga ou no banco nunca é reescrita, e a diferença vai ao primeiro repasse aberto de quem recebe.
  - A resposta traz o resumo novo.
  - Venda nova abaixo do retido NÃO é recusada, porque as contas têm teto no cheio.

| Dado corrigido | O que muda no congelado | O que se refaz |
|---|---|---|
| comprovante (a) | nada (o pago é lido ao vivo) | retido, comissão e BV do retido; o comprovante de qualquer dia do grupo refaz o principal cancelado inteiro, e com o principal vivo nada se refaz (FR-018) |
| devolução (b) | nada (lida ao vivo); o imposto, se vier | retido, comissão e BV do retido; a devolução do dia cortado só refaz o principal depois de ele ser cancelado inteiro (FR-017) |
| valor da venda (c) | venda; cheia = (venda − BV) × taxa congelada (no EducaManto, com os cachês, como no ato) | comissão e BV do retido pela proporção nova ("Cancelamento: correção da venda") |
| taxa (c) | taxa = a nova; cheia | comissão do retido, inclusive a paga, para mais e para menos ("Cancelamento: taxa corrigida") |
| cortesia/permuta (c) | cheia 0 quando marcada; restaurada quando desmarcada | comissão do retido (a paga vira desconto) |
| data da venda e resto (d) | nada; só a data relê a taxa da data nova, se o evento não tem taxa própria (e só depois da 1e) | a comissão, se a taxa mudou |
| vendedor (f) | vendedor e, se ele comissiona, beneficiário; cheia com a regra do novo e a taxa congelada | ver FR-051 |
| acréscimo (g) | BV não pago: cheio, recebedor e PIX, no congelado e no acréscimo; cheia (venda − BV) com a taxa congelada; acréscimo que não é BV não entra | BV e comissão do retido |
| reembolso (h), multa (e) | nada | nada |

- **FR-050**: Só duas correções do Superadmin DEVEM trocar a taxa congelada (Q17 = A; L896-906, L1179-1185):
  - a da **taxa** do próprio cancelado;
  - a da **data de venda**, que relê a taxa daquela data pela tabela da 1e. Isso só vale quando o evento não tem
    taxa própria e só depois de a 1e subir.

  As duas refazem a comissão do retido para mais e para menos, também a parte já paga, no primeiro repasse aberto.
  Nenhuma outra correção mexe na taxa congelada; as outras seguem a tabela da FR-049, sempre com a taxa
  congelada. Não se guarda com que taxa cada parte foi paga. Mudar a taxa padrão não mexe em cancelado
  nenhum.
- **FR-051**: Trocar o **vendedor** do cancelado DEVE passar o retido e a comissão do retido ao novo vendedor (Q16
  = A; L918-930, L1173, L1178-1179, L1602-1604):
  - O congelado ganha o novo vendedor, e também o novo beneficiário quando ele comissiona.
  - A linha a pagar do antigo é cancelada.
  - O que o antigo já recebeu (pago ou no banco) fica como foi pago e gera uma linha negativa no primeiro repasse
    aberto **dele**, com evento e motivo.
  - O novo recebe a comissão do retido inteira, no primeiro repasse aberto dele.
  - Se o novo não recebe comissão, a cheia é 0: o antigo devolve e ninguém recebe.
  - O retido muda de vendedor no Dashboard Comercial e em `/admin/desempenho` do mês do cancelamento.
  - Antes de gravar, a tela avisa: "o retido e a comissão do retido passam a <novo vendedor>".
  - No EducaManto o beneficiário é o responsável, então muda só o recorte comercial.
- **FR-052**: Os acréscimos do cancelado DEVEM ser corrigidos **no lugar** (L1147-1154, L1518, L1604-1605):
  - os itens se casam pela identidade (o `id`, opcional no corpo) e são regravados;
  - item sem `id` nasce;
  - item ausente e não pago sai; BV pago (ou no banco) ausente do corpo → 400 `items`, como no evento vivo (305,
    `comercial_ops.py:283-293`; leitura 6), e nada é gravado;
  - BV pago (ou no banco) que chega com outro valor ou unidade **mantém o gravado**, como no evento vivo (305,
    `comercial_ops.py:337-338`): o corpo não o reescreve (FR-040, "BV pago nunca reescrito") e não há recusa. Só o
    tipo diferente dá 400, também como no vivo. *(Living Spec do checklist: a redação anterior pedia um 409 sem
    `codigo`, e o mesmo corpo teria dois contratos, o do vivo e o do cancelado, o que a leitura 6 evitou no BV
    ausente.)*;
  - nunca apagar e recriar: isso trocaria a identidade que o congelado guarda e perderia o estado do BV pago;
  - o PIX do BV só vai a quem passa na regra da FR-047;
  - na tela, o BV já pago é só leitura;
  - `substituir_acrescimos` não faz nada em evento cancelado, para todo chamador (a API e o Jinja,
    `routes.py:883`); no cancelado, só a função de acréscimos do cancelado grava (L1108, L1839, L3875-3876).
- **FR-053**: Reembolsos (lançar, marcar cobrado, excluir), cronograma de parcelas, notas fiscais e o resto da
  venda (d) DEVEM ser aceitos no cancelado pela regra da FR-047, sem mexer no congelado. A "nota a emitir" do
  retido se resolve pelas rotas de notas (L1131-1137, L1155-1157).
  - **Travas no evento vivo** (Living Spec do checklist): o comprovante mexe no pago do grupo, que o ato lê sob
    a trava do grupo, então as três portas de comprovante travam o grupo **também no evento vivo**, antes de saber se
    está cancelado. Reembolsos, parcelas e notas não mexem no dinheiro do retido: travam só o próprio evento, como
    a 305 faz, e releem se ele está cancelado. No vivo, depois da trava, tudo segue como hoje, com as mesmas
    respostas e a mesma ordem de recusas; as únicas respostas novas aparecem sob concorrência (409 `tente_de_novo`
    num deadlock com o ato e, no comprovante, 409 `grupo_mudou` se o grupo mudou enquanto esperava). O cenário 16
    confere a porta viva.

**Venda de vários dias**

- **FR-054**: "Cancelar todos os dias", pelo **principal**, DEVE cancelar todos os dias **vivos** numa
  confirmação, **sem desagrupar** (Q1 = C; L1231-1246):
  - **Bloqueio e validação**: trava todos os dias em ordem de id, para duas sessões nunca travarem cruzado, e
    valida todos antes de gravar qualquer um.
  - **Congelamento**: no principal, regime `venda`. Pago = comprovantes de todos os dias; devolvido = devoluções
    ligadas a qualquer dia.
  - **Cada dia vivo**: ganha o cancelamento, o motivo, o registro `satelite` com o principal e um histórico.
  - **Dia já cancelado**: fica como está e não vira linha no diálogo; entra só no "já devolvido".
  - **Google e aviso**: a remoção de cada dia vai depois do commit, e o aviso vai uma vez por pessoa.
  - **Dia marcado pela 303**: não é recusado, e perde a marca (`motivo="cancelado"`) antes de gravar o
    cancelamento (L1241-1242).
- **FR-055**: O alcance ("todos" ou "só este dia") DEVE ser obrigatório no principal que tem outro dia vivo, e
  ausente fora do principal. Sem outro dia vivo, o principal só tem "todos" (L1244-1246, L1513).
  - `alcance` ausente no principal com outro dia vivo, ou presente fora do principal → 400 `fields.alcance`.
  - `"so_este_dia"` num principal sem outro dia vivo → 409 (L1983, cenário 42d).
- **FR-056**: "Cancelar só este dia", num dia que não é o principal (regime `dia`), DEVE seguir estas regras
  (Q1 = C, 3b-Q4 = A, 3a-Q8 = A; L1247-1264, L2681-2707):
  - **O que pede**:
    - o motivo;
    - o **novo valor da venda**: obrigatório, maior que zero e não acima da venda atual. O rótulo diz que é o
      total que a cliente paga depois do corte, ou seja, os dias que ficam mais o que a Manto retém do dia;
    - a devolução, só em Parte ou Nada, com teto = pago do grupo − já devolvido;
    - **e com piso** (Living Spec do checklist): o corte não pode deixar a cliente com mais pago do que a venda
      nova. A devolução DEVE ser pelo menos (pago do grupo − já devolvido − venda nova), descontado o que ela já
      tinha pago a mais antes do corte (pago do grupo − já devolvido − venda atual, se positivo). Abaixo disso,
      400 `fields.devolucao_valor` na Parte, ou `fields.devolucao_modo` no "Nada": "A cliente pagou R$ X: devolva
      pelo menos R$ Y ou aumente o novo valor da venda." Exemplo: venda de 3.000 quitada e venda nova de 2.000 →
      devolução mínima de 1.000. Sem isso, os 1.000 ficariam fora do retido, da venda e da devolução, e a cobrança
      da Home mostraria −1.000.
  - **A devolução**: nasce ligada ao **dia**. Fica fora dos gastos extras da DRE e dentro do "já devolvido" do
    grupo. Corrige-se pelo "Alterar devolução" do dia cancelado (FR-017, clarify de 15/10 = A).
  - **O principal**:
    - continua vivo, com a venda nova e histórico, na DRE do mês do evento;
    - o valor cheio cai na mesma proporção (cheio novo = cheio × venda nova ÷ venda antiga, ao centavo com
      `ROUND_HALF_UP`). O que não muda é o **percentual** do desconto (o selo de %); o desconto concedido em
      **reais** cai na mesma proporção (300 → 200 no cenário 38), e o corte nunca aumenta o desconto (Living Spec do
      checklist: a redação anterior dizia que o "desconto concedido" não mudava);
    - o BV **não pago** acompanha na mesma proporção, **uma vez só** (não passa também pelo acompanhamento
      automático da 305);
    - o BV pago fica.
  - **O registro `dia`**: guarda o principal e a venda e o valor cheio de antes e de depois (L1264).
  - **PIX do BV**: não é pedido.
- **FR-057**: No corte de um dia, a comissão do principal vivo DEVE ir ao alvo da venda nova pela reconciliação
  (L1019-1034, L1264-1266, L1976):
  - a linha a pagar é ajustada no lugar;
  - a paga gera ajuste no primeiro repasse aberto, com o motivo "Corte de dia: venda diminuiu";
  - esse ajuste nunca é sobrescrito pela próxima gravação da aba Comercial nem pelo resync;
  - desfazer o "pago" da linha base pela Planilha (267c) com esse ajuste ainda vivo NÃO DEVE descontar em dobro: a
    sincronização leva a base de volta ao alvo da venda nova e cancela o ajuste, e a soma fica no alvo; com a base
    paga ou no banco, nada muda (cenário 38c);
  - depois do corte, nova mudança da venda viva segue a regra de hoje (o acerto é da 1e).
- **FR-058**: "Cancelar só este dia" **no principal** que tem outro dia vivo DEVE passar a venda e cancelar o
  antigo 1º dia (Q5 = B; L1273-1287, L1553-1558):
  - **Para quem vai**: ao dia vivo mais cedo, sem contar o antigo 1º dia (por data e hora; no empate, pelo id). O
    diálogo mostra antes de confirmar: "A venda, os comprovantes, a comissão, o BV, as parcelas, a nota e o
    contrato passam para DD/MM — título".
  - **O antigo 1º dia**: cancela como um dia qualquer (regime `dia`, com a venda nova informada).
  - **Transação**: tudo numa transação só, sob o mesmo bloqueio.
  - **Validação antes de mover**: cachê pago e devolução pendente no antigo 1º dia, venda nova, Parte/Nada,
    multa, e se o dia indicado ainda é o vivo mais cedo. Se não for, 409 `grupo_mudou`, e a tela refaz o impacto.
  - **Falhas**: recusa não move nada, e erro no meio desfaz tudo.
- **FR-059**: Na passagem, tudo o que muda de dono DEVE passar como **a mesma linha, com o mesmo valor e a mesma
  data**. Só o vínculo ao evento, ou o campo, muda; nunca se apaga e recria (L1288-1355, L1376-1378).
  - **O que passa ao novo principal**:
    - os 14 campos comerciais, com o retrato dos dois dias no histórico;
    - a previsão da nota e o nome do grupo;
    - comprovantes, parcelas, notas e contratos;
    - reembolso a cobrar;
    - acréscimos, com o estado do BV;
    - a devolução aprovada já ligada ao antigo 1º dia;
    - o formulário de pré-contrato e o vínculo do orçamento;
    - as clientes que faltam no novo principal;
    - **todas** as linhas de comissão: a pagar, no banco, paga, cancelada e ajustes. Junto com a exclusão (FR-036,
      que solta o `event_id` da paga), é um dos dois únicos toques em linha paga ou no banco, e só no vínculo
      (L1036-1038, L3174-3176).
  - **Grupo**: todo dia do grupo passa a apontar ao novo principal.
  - **Listas únicas**: os campos que passam formam uma lista, e as tabelas filhas outra, para a 2b e a 6a
    acrescentarem nomes.
  - **O que fica com o antigo 1º dia**: elenco, ensaios (que caem), "precisa ensaio", histórico, observações,
    logística, confirmação, avaliação, 3D/NFC, figurino, Gastos Extras que não são devolução, o dia do orçamento
    (3b) e o orçamento e a página EducaManto (2b).
  - **Comissão própria do novo principal** (de quando era venda avulsa): DEVE ficar marcada fora da conta da venda,
    e nenhum ajuste nasce contra ela. A marca é um prefixo de nota por constante, que a reconciliação e a
    sincronização ignoram (P-29) (L1045).
  - **Rastro e prova**: histórico nos dois dias e auditoria por linha de comissão movida. A prova é "soma antes =
    soma depois", linha a linha.
- **FR-060**: Na passagem, tudo o que tem data própria DEVE manter a data (L1323-1351, L1361-1363):
  - venda, vencimentos, notas, comprovantes e ciclo das linhas de comissão;
  - a comissão comum segue a data de venda e fica no mesmo repasse (Q13).

  Exceções:
  - a comissão EducaManto **a pagar** vai à data do novo 1º dia, pelo sincronismo de hoje, sem marca (Q18 = A);
  - receita, imposto, BV, cachês de todos os dias e comissão como custo vão à DRE do mês do novo 1º dia, e o BV à
    Planilha desse mês (Q15 = A), sem guardar data nova.

  A passagem não chama o Google, salvo para remover o antigo 1º dia e os ensaios dele, depois do commit.
- **FR-061**: No grupo (L1201-1214, L1364-1373, L1865):
  - Desagrupar dia cancelado DEVE dar 409, na API e no Jinja. Desagrupar dia vivo segue livre.
  - Agrupar evento cancelado, como satélite ou como principal, DEVE dar 409 pela regra de núcleo do agrupamento,
    na API e no Jinja. `blocked_reason` e selo são da 1c.
  - O KPI do grupo e o custo do grupo (base da comissão EducaManto) ignoram o dia cancelado.
  - Na tela, "Gastos extras vinculados" do principal vivo lista só os dias vivos. No evento cancelado, lista os do
    próprio dia (a devolução e a multa) e, no regime `venda`, os dos dias do ato.
  - A cobrança da Home continua somando o comprovante do dia cancelado, tira o dia só da data do grupo e passa a
    descontar do recebido as devoluções ligadas aos dias. Exemplo: venda 2.000, pago 1.500 e devolvido 300 dão
    800 a receber.
  - O painel "Grupo comercial" não oferece soltar dia cancelado e, depois da passagem, é lido do novo principal.
- **FR-062**: O ponto de extensão da 2a DEVE rodar em **todo** cancelamento: evento avulso, cada dia do laço,
  corte de um dia e, depois da passagem, o antigo 1º dia.

  Cancelar direto, sem pedido, também fecha o pedido aberto do evento por esse ponto (L3235-3237).

  O ponto recebe o alcance e o dia que passou a guardar a venda: no "todos", `"todos"` e nenhum dia novo; na
  passagem, **depois** dela e na mesma transação, `"so_este_dia"` e o novo principal (L1244-1245, L1356-1360). No
  evento avulso, recebe `"todos"` e nenhum dia novo; no corte de um dia que não é o principal, `"so_este_dia"` e
  nenhum dia novo, porque nenhum dia passou a guardar a venda (fixado pelo `/speckit-plan`; a 2a reusa o ponto).

**Ensaio, avisos, cachê pago e multa**

- **FR-063**: Evento com **cachê pago** ao elenco NÃO DEVE ser cancelado, por papel nenhum (Q4 = B; L747-755,
  L1469-1472, L1561-1562).
  - **A recusa**: 409 `codigo: "cache_pago"`, com "Este evento tem cachê pago ao elenco e não pode ser cancelado.
    Para devolver dinheiro à cliente, lance uma Devolução em Gastos Extras." Nada é gravado: nem devolução, nem
    ensaio, nem aviso.
  - **No grupo**: vale para qualquer dia alcançado, e a frase diz qual (extra `dias`).
  - **A régua**: "cachê pago" é uma régua única — escalação com artista em pago **ou no banco**, fora a vaga de
    presença do técnico de som. A 2a importa a mesma régua.
  - **Evento marcado com cachê pago**: fica só com "Devolver ao Google".
  - **Na tela**: o impacto traz `cache_pago`, e o diálogo mostra o motivo, aponta a Devolução em Gastos Extras e
    não oferece cancelar.
- **FR-064**: Evento do tipo Ensaio NÃO DEVE passar pelo cancelar: 409 `codigo: "ensaio"`. Ele tem botão próprio,
  e o ensaio segue o show (L751, L2809-2813).
- **FR-065**: Todo ensaio vivo de cada dia cancelado DEVE cair no mesmo ato (1c-Q3 = C; L1382-1404).
  - Sai do banco na transação e do Google depois do commit, junto com o show, com a mesma trava de ambiente e o
    mesmo aviso quando falha.
  - O histórico do show registra data, hora e local de cada ensaio.
  - No corte do 1º dia, o ensaio do antigo 1º dia cai e não passa ao novo principal.
  - O botão "Cancelar ensaio" e a troca de tipo continuam iguais.
  - A regra é exata até a 2b (noite 7), que a troca sem código desta entrega.
- **FR-066**: Em **todo** cancelamento (venda inteira, um dia ou o 1º dia que passa a venda), cada artista
  escalado nos dias cancelados DEVE receber o e-mail que já existe, "Sua participação neste evento foi cancelada",
  sem modelo novo (Q11 = B, 1c-Q12 = A; L1425-1440).
  - O envio é em segundo plano, **depois** do commit, **uma vez por pessoa**.
  - Não recebem quem recusou o convite nem a vaga de presença do técnico de som.
  - No corte, só o elenco daquele dia recebe.
  - Cancelamento recusado não avisa ninguém.
  - Fora da produção, a trava que já existe cala o e-mail.
- **FR-067**: A equipe de Ensaio (usuários ativos com o papel) DEVE receber o sino `evento.cancelado`, na mesma
  transação, **só quando** algum dia cancelado tinha ensaio. É uma notificação por pessoa **e por ato**, com os
  ensaios cancelados: um corte de dia com ensaio e, depois, o "Cancelar todos os dias" com ensaio dão dois sinos a
  cada pessoa, e o sino de um ato nunca cala o de outro ato do mesmo grupo. O sistema não passa a gravar quem marcou
  o ensaio (Q11 = B; L1425-1438).
- **FR-068**: O Casting (usuários ativos com o papel, sem o Superadmin) DEVE receber o sino
  `evento.cancelado_escala`, na mesma transação (1c-Q10; L1441-1455):
  - **uma notificação por dia cancelado com escalados**, em cada ato; sem elenco, nenhuma;
  - `urgent` quando o evento está a 7 dias ou menos;
  - com link para a aba de produção do cancelado;
  - com o texto "Evento cancelado: tire os N artistas da escala e avise cada um pelo WhatsApp".

  O sistema não manda WhatsApp, e tirar da escala no cancelado continua possível pelo Casting.
- **FR-069**: Tirar um artista da vaga de evento **cancelado** NÃO DEVE mandar o e-mail de remoção, porque ele já
  recebeu o do ato. Em evento vivo, o e-mail continua (1c-Q12 = A; L1456-1465).
- **FR-070**: O ato DEVE guardar o **elenco alcançado**: uma linha por **escalação** (vaga × dia) nos dias
  cancelados, sem quem recusou e sem a vaga de presença (1c-Q10; L710-723, L1497-1504). Um artista em 2 dias, ou
  em 2 vagas, tem 2 linhas.
  - Cada linha tem artista, vaga, personagem, cachê da vaga só como referência, dia e a multa lançada.
  - É a lista do aviso, do sino ao Casting e da multa.
  - Tirar o artista da vaga depois não apaga a linha nem o direito à multa.
- **FR-071**: Em todo cancelamento com elenco escalado, o diálogo DEVE ter o bloco "Multa ao elenco" (Q8–Q10 = A;
  L1473-1486, L1504-1507, L1562-1565).
  - **O bloco**:
    - uma linha por escalação da lista do ato, com nome, vaga e dia (um artista em 2 dias tem 2 linhas e 2 campos);
    - campo vazio (vazio ou 0 = sem multa), sem sugestão de valor;
    - o cachê da vaga ao lado, só como referência;
    - "faltavam N dias para o evento" (ou "o evento foi há N dias"), contado pelo servidor no fuso de São Paulo e
      por dia no grupo, sem prazo;
    - aviso quando o talento não tem PIX.
  - **Cada valor vira um Gasto Extra por escalação**:
    - aprovado e a pagar, ligado ao cancelado;
    - na categoria nova "Multa de cancelamento", tipo fornecedor;
    - com nome e PIX do cadastro do talento e a data do cancelamento;
    - na Planilha e na DRE (gastos extras) do mês do cancelamento;
    - sem trava: corrige-se em Gastos Extras;
    - sem mexer em comissão nem em BV.
  - **Recusa**: multa negativa ou inválida, ou para vaga fora dos dias alcançados, dá 400 `fields.multa_<role_id>`.
    Vazio ou 0 é ignorado, sem recusa.
- **FR-072**: A tela do cancelado DEVE ter "Lançar multa ao elenco", para o Superadmin, pela regra da FR-047
  (1c-Q7 = A, 1c-Q10; L1487-1503, L1605-1606).
  - Usa o mesmo bloco e a mesma regra, com a lista do ato, inclusive quem o Casting já tirou da vaga, marcado
    "saiu da escala".
  - A multa entra com a data do lançamento, na Planilha e na DRE do mês em que é lançada. A data do lançamento é
    premissa do plano, não resposta do dono (L2838-2842, L4767-4769; P-34).
  - Em evento vivo, dá 409 `nao_cancelado`.
  - Valor vazio ou 0 é ignorado, como no ato. Valor negativo ou inválido, linha fora da lista do ato (artista fora
    dela ou linha de outro evento) ou multa já lançada na linha (corrige-se em Gastos Extras) dá 400
    `fields.multa_<elenco_id>`, e nada é gravado.

**Outros**

- **FR-073**: Excluir um usuário que é vendedor ou beneficiário congelado de um cancelamento DEVE ser recusado com
  o bloqueio "cancelamentos"; hoje daria erro 500. Se o usuário que atualizou o cancelamento sair, esse campo fica
  nulo (L1222-1227, L1536).
- **FR-074**: Os textos que mentem DEVEM ser reescritos (L1071, L1577, L1831-1833):
  - no diálogo: "Deixe zerado se não há nada a devolver" e "vira estorno no próximo repasse";
  - a descrição do estorno no app;
  - as docstrings do cancelamento e do estorno;
  - "Não conta em nenhuma métrica e sumiu da agenda";
  - o "sem duplicar" da DRE;
  - as docstrings dos modelos: cancelado, linha de comissão e gasto, incluindo o tipo cliente;
  - a docstring da cobrança ("a devolução, se houve, é gasto");
  - a docstring do agrupamento, que passa a dizer que o principal pode mudar.

### Entidades *(se houver dados)*

A migration é uma só, escrita à mão. Ela só cria tabelas, sem backfill e sem coluna em tabela existente
(L685-732, L3597-3621). Os nomes foram fechados pelo `/speckit-plan` (`data-model.md`; a tabela única de nomes
está no §6) (L699). A relação fica declarada no
filho, no molde de `Event3DDismissal`, e `CalendarEvent` e `_clear_event_side_tables` não são tocados. Dinheiro é
`Numeric(12,2)`; a FK da filha tem índice; as FKs vão para `users`. O `downgrade` derruba as filhas primeiro.

- **Cancelamento do evento** (`event_cancellations`): um por evento, com `event_id` UNIQUE e CASCADE, então some
  junto com o evento. Guarda:
  - o regime (`venda`, `satelite`, `virtual` ou `dia`) e o modo escolhido (`tudo`, `parte` ou `nada`, que não muda
    depois);
  - os valores congelados no ato: venda, comissão cheia, beneficiário da comissão, vendedor, se era com nota,
    imposto retido (nulo = não se aplica) e a taxa da comissão (em `Numeric(6,3)`, porque a origem é `Float`);
  - no EducaManto, o custo de cachês da cheia no ato (`commission_cost`), pela mesma régua de custo da comissão
    (o custo do grupo no principal, o do evento no que não é principal), porque o custo ao vivo muda quando o
    Casting esvazia a escala (FR-049);
  - nos dias de grupo, o principal do ato;
  - no antigo 1º dia que passou a venda, a marca `sale_handed_over` (verdadeira só nele), de onde a tela tira "a
    venda passou para" (FR-022): um `dia` comum também guarda o principal, e o histórico não se consulta;
  - só no regime `dia`, a venda **e o valor cheio** do principal antes e depois do corte (L1264, L3613);
  - criado e atualizado em (hora de São Paulo) e quem atualizou (SET NULL).

  Pago e devolvido **não** são guardados. Cancelado sem este registro é `legado`.
- **BV congelado do cancelamento** (`event_cancellation_bvs`): uma linha por acréscimo BV no ato. Guarda
  recebedor, PIX, **BV cheio**, se estava pago no ato e o **valor pago** (`paid_amount`, leitura 10): o do ato, se
  estava pago, ou o do instante em que a Planilha o marcou depois; nulo enquanto não está pago, e de volta a nulo no
  desfazer. O vínculo ao acréscimo vira nulo se ele for apagado, e linha sem vínculo não soma em lugar nenhum. Não
  há BV negociado: saiu na 1b-Q2.
- **Elenco do cancelamento** (`event_cancellation_elenco`): uma linha por **escalação** (vaga × dia) nos dias
  alcançados; um artista em 2 dias ou em 2 vagas tem 2 linhas.
  - Guarda o artista (nunca apagado em cascata), a vaga (nula se apagada), o personagem, o cachê de referência e
    o dia (`day_event_id`, obrigatório, que sai em cascata com o dia; o dia cancelado não se exclui, FR-021).
  - Guarda a multa lançada (`special_expense_id`): uma multa por linha; se o gasto for excluído em Gastos Extras,
    o vínculo fica nulo e a linha volta a "não lançada".
  - Sai em cascata com o cancelamento.
  - É tabela, e não JSON nem histórico, porque a multa aponta para a linha e o cachê de referência é dinheiro.
- **Já existentes, tocados sem coluna nova**:
  - **Evento** (`CalendarEvent`): cancelamento, motivo e grupo, onde o principal pode mudar.
  - **Linha de comissão** (`CommissionPayment`): estados `a_pagar`, `no_banco`, `pago` e `cancelado`; ligação com
    a paga; motivo no prefixo da nota.
  - **Gasto Extra** (`SpecialExpense`): "Devolução a cliente" com destinatário cliente. A categoria nova "Multa de
    cancelamento" é texto, sem migration.
  - **Acréscimo** (`EventAcrescimo`): recebedor e PIX do BV.
  - **Notificação**: dois kinds novos, texto.
  - **Histórico** (`EventLog`): passa a usar o default UTC do modelo.

### RBAC *(obrigatório se houver endpoint novo ou alterado)*

Nenhum papel novo. Os dois endpoints novos têm gate no início da view, comentário `RBAC:` e linha em `docs/01`
§4.3. Na mesma tabela, a linha de `_can_delete()` ganha o `PATCH …/devolucao`, e cada porta alterada abaixo ganha
linha com o papel e o 409. Os novos campos de payload nascem opcionais no TypeScript (L1509-1536).

**Códigos 409**: as recusas novas desta entrega levam `codigo`, de constante no servidor e de uma união no
TypeScript. São 18:

| `codigo` | Onde nasce |
|---|---|
| `cancelado` | regra única do cancelado (FR-047) nas portas de (a) a (h); `PATCH /api/events/<id>`; orçamento; exclusão; agrupar e desagrupar |
| `ja_cancelado` | `POST …/cancelar` (inclusive o registro único que estoura) e a prévia |
| `ensaio` | `POST …/cancelar` em evento do tipo Ensaio |
| `grupo_mudou` | `POST …/cancelar` (o dia indicado ou a composição do grupo mudou) e os comprovantes do grupo |
| `sem_outro_dia_vivo` | `POST …/cancelar` com `"so_este_dia"` num principal sem outro dia vivo |
| `cache_pago` | `POST …/cancelar`, com `dias` |
| `devolucao_pendente` | `POST …/cancelar`, com `dias` no grupo (a pendente de qualquer dia) |
| `max_devolucao_mudou` | `POST …/cancelar` com "Tudo" divergente, com `max_devolucao` |
| `tente_de_novo` | deadlock residual nos endpoints desta entrega |
| `nao_cancelado` | `PATCH …/devolucao` e `POST …/multas` em evento vivo |
| `regime_sem_retido` | `PATCH …/devolucao` em `satelite` e `virtual` |
| `abaixo_do_piso` | `PATCH …/devolucao`, com `piso` |
| `acima_do_teto` | `PATCH …/devolucao` no `dia`, com `teto` |
| `pago_abaixo_do_devolvido` | editar ou excluir comprovante, com `pago` e `devolvido` |
| `bv_nao_esta_a_pagar` | `POST /api/financeiro/pagamentos/set-status` no BV |
| `devolucao_travada` | as seis portas de Gastos Extras, com `fields` e `event_id` |
| `estado_mudou` | `PATCH …/comercial` e `PUT …/acrescimos` do evento vivo, quando ele vira cancelado entre a leitura e a trava |
| `valor_mudou` | `POST /api/financeiro/pagamentos/set-status`, BV ou devolução de cancelado com `valor_esperado` divergente (o 409 da 305 ganha o código) |

O 409 de valor divergente ao marcar BV ou devolução na Planilha segue o formato da 305: a frase traz o valor atual,
agora com `codigo: "valor_mudou"`.

- **`POST /api/events/<id>/cancelar`** (alterado).
  - **Papéis**: SUPERADMIN real (`_can_delete()`), checado depois do 404. Os demais recebem 403; sem sessão, 401.
  - **Corpo**: `{motivo, devolucao: {modo, valor?, nome?, pix?, observacao?}, imposto_retido?, venda_nova?,
    multas?: [{role_id, valor}], bvs?: [{acrescimo_id, recebedor, pix}], alcance?, novo_principal_id?}`. Sai
    `bv_negociado`.
  - **Resposta**: `{ok, resumo, dias_cancelados?, ensaios_cancelados?, avisados?, venda_passou_para?}`.
  - **400** em `fields.motivo`, `devolucao_modo`, `devolucao_valor`, `devolucao_nome`, `devolucao_pix`,
    `imposto_retido` (também quando enviado sem nota), `venda_nova`, `alcance`, `multa_<role_id>` (negativa ou
    inválida, ou vaga fora dos dias alcançados; vazia ou 0 é ignorada) e `bv_pix_<acrescimo_id>`, todos de uma vez.
  - **Ordem** (a de `contracts/api.md` §1): 401 → 404 → 403 → trava do grupo → 409 `ja_cancelado` → 409 `ensaio` →
    400 `alcance` → 409 `sem_outro_dia_vivo` → 409 `grupo_mudou` → 409 `cache_pago` → 409 `devolucao_pendente` →
    400 nos campos, todos de uma vez → 409 `max_devolucao_mudou`. Os 400 de campo vêm **depois** da trava, porque
    dependem do pago, do regime e da nota relidos nela.
  - **409** (depois de travar o grupo): `ja_cancelado`; `ensaio`;
    `sem_outro_dia_vivo` (`"so_este_dia"` num principal sem outro dia vivo; L1983, cenário 42d); `grupo_mudou`;
    `cache_pago` (com `dias`); `devolucao_pendente`; `max_devolucao_mudou` ("Tudo" divergente, com
    `max_devolucao`). O registro único que estoura na concorrência vira `ja_cancelado`, e o deadlock,
    `tente_de_novo`.
  - Sai a 409 de líder de grupo.
- **`GET /api/events/<id>/impacto-exclusao`** (alterado).
  - **Papéis**: `_can_delete()`.
  - **Chaves novas**:
    - `regime`, `sumiu_do_google`, `ja_devolvido`, `max_devolucao`, `com_nota`, `imposto_aliquota`;
    - `bvs[]`: cheio, recebedor, se já está pago, se falta recebedor ou PIX, e o proporcional na prévia;
    - `comissao {beneficiario, cheia, paga, a_pagar}`;
    - `grupo? {principal_id, dias: [{id, data, titulo, cancelado, cache_pago, faltam_dias}],
      proximo_principal?}`;
    - `ensaios? [{id, data, local}]`;
    - `elenco[]` com `role_id` e `talent_pix_informado` (o PIX em si, só com `show_financeiro`);
    - `faltam_dias?`, `comprovantes_sem_valor?` e `cache_pago?`;
    - `acao: "cancelar"` para todo marcado.
  - **Prévia**: com `?devolucao=` (e `&venda_nova=`), responde só `{efeito: {devolucao, retido, comissao_cheia,
    comissao_retido, bv_retido, bvs?, ja_liquidada, ajuste, ciclo, repasse_em, imposto_referencia}}`. Valor
    inválido dá 400; evento já cancelado, 409 `ja_cancelado`. A prévia não trava nem grava nada (FR-011).
  - `devolucao_sugerida` fica por um ciclo.
- **`PATCH /api/events/<id>/devolucao`** (**novo**).
  - **Papéis**: SUPERADMIN pela regra única (o mesmo que `_can_delete()`). 404 vem antes do 403; demais, 403; sem
    sessão, 401.
  - **Corpo e resposta**: `{devolucao_total, nome?, pix?, observacao?, imposto_retido?}` → `{ok, resumo}`.
  - **Ordem**: 401 → 404 → 403 → 400 só se `devolucao_total` faltar ou não for número → trava → 409
    `nao_cancelado` → 409 `regime_sem_retido` (`satelite`, `virtual`) → 400 nos campos → 409 `abaixo_do_piso` (com
    `piso`: as devoluções pagas ou no banco e, no `venda` em grupo, as dos dias cortados, FR-017) → só no dia cortado (`dia`), 409 `acima_do_teto` (com `teto`: o pago
    do grupo menos as outras devoluções).
  - **400**: `devolucao_total` (negativo; no `venda` e no `legado`, acima do pago), `devolucao_nome`,
    `devolucao_pix` e `imposto_retido` (no `legado`, no `dia` ou sem nota, leitura 9).
  - **No dia cortado**: corrige a devolução daquele dia; com o principal vivo, não refaz retido nem comissão
    (clarify 15/10 = A). Com o principal já cancelado inteiro, refaz também o retido e a comissão dele (D28,
    FR-017).
- **`POST /api/events/<id>/multas`** (**novo**).
  - **Papéis**: SUPERADMIN pela regra única. 404 vem antes do 403; demais, 403; sem sessão, 401.
  - **Corpo e resposta**: `{multas: [{elenco_id, valor}]}` → `{ok, resumo, gastos: [id]}`.
  - **Ordem** (a de `contracts/api.md` §4): 401 → 404 → 403 → trava do grupo e do elenco → 409 `nao_cancelado` →
    400.
  - **409** `nao_cancelado`: evento vivo. **400**: `fields.multa_<elenco_id>` para valor negativo ou inválido,
    artista fora da lista do ato, linha de outro evento ou multa já lançada na linha; valor vazio ou 0 é ignorado.
    Se, ignorados os vazios e zeros, não sobrar nenhuma multa, 400 `fields.multas` ("Informe a multa de ao menos
    um artista"): o endpoint existe para lançar. A lista é por escalação, e cada valor vira um gasto.
- **`PATCH /api/events/<id>/comercial`**.
  - **Evento vivo**: `_can_create_event()` mais a checagem da 215b, sem mudança.
  - **Cancelado**: a regra única roda **antes** da checagem da 215b. A Comercial recebe 409 `cancelado`; o
    Financeiro, que já fica fora do gate, recebe 403.
  - **Gravação do Superadmin**: valor, taxa, cortesia e vendedor recongelam na mesma transação, e a resposta (o
    detalhe) traz o resumo em `event.cancelamento`. Se o evento mudou de estado entre a leitura e a trava, 409
    `estado_mudou`.
- **`PATCH /api/events/<id>`** (edição completa, o "Editar tudo"; alterado).
  - **Gate**: sem mudança (`_can_create_event()`, depois do 404); a validação de hoje vem antes do 409.
  - **Cancelado**: se `sale_value`, `sale_value_gross`, `commission_rate`, `seller_id`, `is_cortesia_permuta` ou
    `with_invoice` chega **diferente** do gravado, 409 `cancelado` **para todos os papéis, inclusive o
    Superadmin**, com "Evento cancelado: corrija os dados de venda pela aba Comercial.", porque essa porta não
    recongela. Campo igual ao gravado passa. A tela esconde "Editar tudo" no cancelado.
- **`PUT /api/events/<id>/acrescimos`**.
  - **Evento vivo**: `_can_manage_sale()`, sem mudança.
  - **Cancelado**: a regra única. Comercial e Financeiro recebem 409 `cancelado`.
  - **Contrato**: `id?` por item; BV pago diferente dá 409; BV pago (ou no banco) ausente do corpo dá 400
    `items`, como no vivo (leitura 6); a resposta (o detalhe) traz o resumo em `event.cancelamento`; o PIX do BV
    só vai a quem passa na regra.
- **Reembolsos** (`POST /api/events/<id>/reimbursements`, `POST /api/reimbursements/<id>/collect`,
  `DELETE /api/reimbursements/<id>`).
  - **Gates de hoje**: lançar e marcar cobrado usam `_can_edit_event()` (Casting, Figurino, Comercial,
    Financeiro e Superadmin; `agenda_write.py:1829`, `:1865`); excluir usa `_is_superadmin()`.
  - **Cancelado**: a regra única. No lançar e no marcar cobrado, todos os que passam no gate e não são
    Superadmin recebem 409 `cancelado`; no excluir, os demais seguem com 403. O congelado não muda.
- **`PUT /api/events/<id>/parcelas`** e **`POST`/`PATCH`/`DELETE /api/events/<id>/invoices[/<id>]`**.
  - **Evento vivo**: o gate de hoje, `_can_manage_sale()` (Comercial, Financeiro e Superadmin).
  - **Cancelado**: a regra única. Comercial e Financeiro recebem 409 `cancelado`; Casting e Figurino, que não
    passam no gate, recebem 403. O congelado não muda.
- **Comprovantes**.
  - **Gates de hoje**: `POST` usa `_can_edit_event()` (Casting, Figurino, Comercial, Financeiro); `PATCH` e
    `DELETE` usam `_is_superadmin()`.
  - **Cancelado**: o `POST` de quem não é Superadmin dá 409 `cancelado`, **antes** de salvar o arquivo, e
    `PATCH`/`DELETE` já dão 403 a quem não é. O Superadmin grava e o servidor recalcula na mesma transação: num dia
    de grupo, refaz o cancelamento `venda` do principal; com o principal vivo (`dia`), nada (FR-018).
  - **409 novos**: `pago_abaixo_do_devolvido` (editar ou excluir que deixa o pago do grupo abaixo do devolvido, com
    `pago` e `devolvido`), `grupo_mudou` e `tente_de_novo`. Um 409 que nasce no `POST` depois de salvar o arquivo
    desfaz tudo e remove o arquivo novo. A resposta continua o detalhe, com `event.cancelamento`.
- **`PATCH /api/events/<id>/orcamento`**: gate sem mudança (`_can_manage_sale()`: Comercial, Financeiro e Superadmin;
  Casting e Figurino → 403); em cancelado, 409 `cancelado` para todos os que passam no gate.
- **`DELETE /api/events/<id>`**: gate sem mudança; 409 em cancelado. A rota Jinja recusa com aviso.
- **`GET /api/events/<id>`**.
  - **Gate**: sem mudança.
  - **Bloco do cancelamento**: `event.cancelamento?` só com `show_comercial`. Comissão, BV, imposto, PIX e
    `taxa?`, só com `show_financeiro`.
  - **Elenco**: `cancelamento.elenco?` (`elenco_id`, artista, vaga, cachê de referência, se ainda está na vaga,
    multa lançada) só com `flags.can_edit_venda_cancelado`.
  - **KPI**: `kpi` ausente no cancelado.
  - **Flags novas**: `flags.can_edit_pagamentos?` e `flags.can_edit_venda_cancelado?`.
- **`GET /api/events/cancelamentos`**.
  - **Gate**: **sem mudança, SUPERADMIN**. Demais, 403; sem sessão, 401.
  - **Contrato**: cada item ganha `resumo`, com `no_banco`. O campo `devolucao` legado fica por um ciclo. O PIX só
    vai com `show_financeiro`.
  - A leitura pelo FINANCEIRO e o item de menu são da 1c.
- **Gastos Extras** (`POST`, `PATCH`, `DELETE`, aprovar, rejeitar, vincular-evento).
  - **Gate**: sem mudança.
  - **Contrato**: a devolução travada dá 409 `devolucao_travada` com `fields` e `event_id`, depois da trava do
    evento e na ordem de gate de cada porta como está hoje (no `DELETE`, o 404 vem antes do 403; o `POST` não tem
    gate de papel); criar ou converter para o tipo cliente dá 400; o gasto ganha `locked?` e `event_cancelled?`.
- **`GET /api/financeiro/comissoes`**.
  - **Gate**: sem mudança.
  - **Contrato**: `status` pode ser `no_banco`; cada linha ganha `tipo?`, `original_id?`, `evento_cancelado?` e
    `ciclo?`; entra `kpis.total_no_banco?`.
- **`GET /api/financeiro/pagamentos`**.
  - **Gate**: sem mudança.
  - **Contrato**: entra `commission_lines?`, e o BV sai pela regra da FR-040.
- **`POST /api/financeiro/pagamentos/set-status`** (alterado).
  - **Gate**: sem mudança (Financeiro e Superadmin).
  - **BV**: trava o evento antes do acréscimo e confere `valor_esperado` contra o valor que a Planilha mostra
    (FR-040): divergente → 409 `valor_mudou` ("O BV mudou para R$ X…"); BV que não está a pagar → 409 `bv_nao_esta_a_pagar`. O
    valor pago fica no congelado do BV (leitura 10).
  - **Devolução de cancelado** (`expense`): trava o evento e o gasto; `valor_esperado?` divergente do gravado → 409
    "A devolução mudou para R$ X…". Sem o campo, o comportamento de hoje. A tela manda `valor_esperado` no BV e na
    devolução.
  - **Comissão**: contrato igual; o desfazer passa a travar os eventos antes das linhas.
- **`GET /api/financeiro/dashboard`**.
  - **Gate**: sem mudança (FINANCEIRO, SUPERADMIN).
  - **Contrato**: `dre.{realizado,projetado,total}.retido_cancelamentos?` e `n_cancelados?`;
    `paineis.cancelamentos?` sempre; a barra do retido; `monthly_trend[].retido?`; nota com `cancelado?` e
    `retido?`; Top Vendedores com o retido.
- **`GET /api/vendas/pipeline`**.
  - **Gate**: sem mudança.
  - **Contrato**: `kpis.retido_cancelamentos?`, `kpis.n_cancelados?` e `kpis.comissao_retido?` (as duas últimas
    fecham as sublinhas), e o retido entra em `total_vendido` e `comissao_prevista`. O nome `n_cancelados` é o mesmo
    da DRE.
- **`GET /api/admin/desempenho`**.
  - **Gate**: sem mudança.
  - **Contrato**: filtra o cancelado; entram `vendas[].retido?`, `cancelados?` e `totals.retido?`.
- **`GET /api/clientes/<id>`, `/api/clientes/`, `/metricas`**.
  - **Gate**: sem mudança.
  - **Contrato**: o total inclui o retido, e as contagens não incluem cancelado.
- **`GET /api/dashboard`**.
  - **Gate**: sem mudança.
  - **Contrato**: a Performance ignora cancelado.
- **`POST`/`DELETE /api/events/<id>/grupo`**.
  - **Gate**: `_can_group`, sem mudança.
  - **Contrato**: agrupar cancelado ou desagrupar dia cancelado dá 409 `cancelado`.
- **`DELETE /api/events/<leader>/grupo/satelites/<sat>`** (alterado; soltar um dia pela tela do principal).
  - **Gate**: `_can_group`, sem mudança.
  - **Contrato**: soltar dia cancelado dá 409 `cancelado`, como o `DELETE …/grupo`; hoje a recusa viraria erro 500.
- **`GET /api/notificacoes`**.
  - **Gate**: sem mudança.
  - **Contrato**: kinds `evento.cancelado` (Ensaio) e `evento.cancelado_escala` (Casting).
- **`POST /api/roles/<id>/assign`** (escala; chama `casting_ops.assign_role`, como a rota Jinja da escala).
  - **Gate**: sem mudança (`_can_edit_event()`).
  - **Contrato**: no cancelado, tirar da escala não manda o e-mail de remoção (1c-Q12 = A; L1461-1463, L1838). A
    condição fica no núcleo, então vale para a API e para o Jinja.
- **`DELETE /api/admin/users/<id>`**.
  - **Gate**: sem mudança.
  - **Contrato**: bloqueio novo "cancelamentos", com o mesmo status e o mesmo formato.
- **Jinja** (despachante da tela antiga do evento, agrupar e desagrupar, excluir, Planilha antiga e
  `set_commission_status`).
  - **Gate**: sem mudança.
  - **Contrato**: o despachante recusa o cancelado com aviso **para todos os papéis, inclusive o Superadmin**, em
    `update_comercial`, `update_sale`, nos três de comprovante e nos três de reembolso (o Jinja não recongela; o
    Superadmin corrige pela tela nova). Agrupar, desagrupar e excluir recusam o cancelado com aviso. Na Planilha
    antiga, marcar BV passa pela mesma regra da API (sem valor esperado; aviso em `bv_nao_esta_a_pagar`), e mudar o
    estado de uma devolução de cancelado trava o evento antes. `set_commission_status` recusa, com aviso, mexer em
    linha de comissão de evento cancelado.

## Verificação (`verify_306.py`) *(obrigatório — Princípio VIII)*

Arquivo: `specs/306-dinheiro-do-cancelamento/verify_306.py`, rodando contra `manto_local` (`DATABASE_URL` de
`.local-db-url`, `FLASK_ENV=development`, `MANTO_SEM_THREADS=1`). Regras de execução:
- login só por `POST /api/auth/login`;
- requisições fora do `app_context`;
- toda escrita conferida por **conexão separada**;
- limpeza no `finally`, com `roles.clear()` antes de apagar usuário.

**Chão herdado do `verify_303.py`** (L1910-1928):
- trava de e-mail;
- guarda de ambiente: sai com código 2 se `calendar_auto_sync_at` for recente;
- dublê do Google, que substitui `app.calendar.service.delete_event` em **todo** cancelamento de evento não
  marcado, show e ensaios. Hoje a remoção não tem trava fora da produção (L1916); com a FR-015 passa a ter, e o
  dublê fica como segunda barreira (L864), porque o espelho tem o token real;
- espera das threads antes de afirmar "zero e-mail".

**Preparação**:
- espião de `send_removal_email`, que conta destinatários;
- notificações contadas por conexão separada;
- matriz de `hoje` com dias 1 a 5 × depois do dia 5;
- Planilha aquecida de M−1 a M+2 antes de qualquer retrato;
- para a passagem da venda, um **retrato** linha a linha de toda tabela pendurada no evento, antes e depois;
- retrato das tabelas tocadas antes e depois de cada GET de prévia, pela conexão separada, para acusar a prévia que
  grava (mutação "simular escreve").

Eventos SHOW só com vaga existente com `talent_id IS NULL`; nunca `EventRole` inventada.

| # | Cenário | O que prova | Deve falhar? | História | Plano |
|---|---|---|---|---|---|
| 1 | Chão: travas, dublê de `delete_event` (show e ensaios), espião do e-mail; regressão `main` × branch da comissão do evento vivo (a regra de hoje, que fica intocada sob a comissão cheia) em todos os eventos do espelho, pelas chamadas de hoje | nada escapa; a comissão do evento vivo não muda número nenhum, inclusive a do evento sem vendedor, que segue com comissão na DRE; a cheia 0 de cortesia e de evento sem vendedor é provada na variante do 16b | não | Fundação | L1932; plan (Living Spec 16) |
| 2 | Superadmin cancela evento vivo com "Parte" de 600 sobre 1.000 pagos; variante prévia = execução, com `hoje` no dia 2 e no dia 10: `GET …/impacto-exclusao?devolucao=600` antes e o `POST` depois | cancelado; devolução aprovada a pagar de 600 (categoria, `cliente`, nome, PIX); `event_cancellations` com venda, cheia 90 e modo `parte`; retido 400; `EventLog` com modo, devolvido, retido, BV, imposto e hora certa (±5 min); na variante, `retido`, `comissao_retido`, `ajuste`, `ciclo`, `repasse_em` e `bv_retido` da prévia iguais ao gravado, e o GET não grava nada (retrato pela conexão separada; a mutação "simular escreve" acusa) | não | 2 | L1933; plan (Living Spec 14) |
| 2b | O mesmo em evento marcado pela 303 (`google_missing_since` preenchido) | Google chamado zero vezes; a marca sai com motivo `cancelado`; sem `aviso` do Google; elenco e equipe de Ensaio avisados como em todo cancelamento | não | 2 (aviso: 6) | L1934 |
| 3 | "Tudo" (envia `max_devolucao`), "Nada", e "Tudo" divergente (outra devolução aprovada antes) | Tudo preenche o total; Nada não gera gasto e retido = pago; divergente → 409 com `max_devolucao` | **sim** (o divergente) | 2 | L1935 |
| 4 | Sem `modo`; valor acima do pago; Parte sem nome ou PIX; nota sem imposto; imposto enviado sem nota; `?devolucao=` inválido; corte de um dia sem `venda_nova`, com zero, acima da venda, com "tudo", com imposto, ou com devolução abaixo do mínimo (venda 3.000 quitada, venda nova 2.000, "Nada" e Parte de 500); multa negativa ou com `role_id` de outro evento; BV a pagar com proporção > 0 sem PIX e sem `bvs` (variante: com `bvs`) | 400 com o campo certo (`bv_pix_<id>` no BV) e nada gravado; na variante, cancela, o PIX vai ao acréscimo e a Planilha do mês do evento mostra o BV proporcional com ele | **sim** (menos a variante) | 2 (corte: 5; multa: 6) | L1936 |
| 5 | Devolução pendente ligada; evento já cancelado; clique duplo; variante 5-grupo (roda com a História 5): pendente ligada a um satélite, no "Cancelar todos os dias" e no corte de outro dia | 409 nos três; uma linha só em `event_cancellations`; na variante, 409 `devolucao_pendente` com `dias` = o satélite, nos dois, sem gravar nada | **sim** | 2 (variante: 5) | L1937; checklist CHK033 |
| 6 | COMERCIAL real (não "Ver como") tenta cancelar, alterar a devolução e ler a prévia; FINANCEIRO tenta alterar; FIGURINO tenta | 403 em todos. A leitura de `/events/cancelamentos` pelo FINANCEIRO sai daqui e vai à 1c (leitura 1 desta spec) | **sim** | 2 | L1938 |
| 7 | Comissão a pagar de 100; cancela com 400 retidos (variante com BV: cheia 90) | a linha vira 20 (18) no lugar, mesmo evento e mesma data; nunca acima da cheia | não | 1 (fecha com a 2) | L1939 |
| 8 | Comissão paga de 100, mesmo cancelamento; `hoje` = dia 2 (com e sem `a_pagar` em M−1) e dia 10; variante prévia = execução nos mesmos `hoje`: a prévia antes e o `POST` depois | paga intacta; −80 com `sale_date = payable_from` = primeiro repasse aberto; liquidado não reabre; no dia 2 com `a_pagar` em M−1, cai em M−1; na variante, o `ajuste` (−80), o `ciclo` e o `repasse_em` da prévia são os do −80 gravado, e o GET não grava nada | não | 1 (2) | L1940; plan (Living Spec 14) |
| 9 | Comissão no banco; variante 9/10-desfazer: sobre a linha liquidada (a no banco deste cenário e a paga do "Tudo" do 10), o Superadmin desfaz o "pago" pela Planilha (267c), abre Comissões e a Planilha e corrige um comprovante | tratada como paga: −80 no primeiro repasse aberto; na variante, a linha volta a "a pagar" com o mesmo valor, o resync não a toca, e Σ linhas vivas = alvo nos três momentos (a correção absorve no lugar, com a data intacta) | não | 1 (2) | L1941; plan (leitura 11, decisão (b)) |
| 10 | "Tudo" com comissão a pagar e paga; evento semeado (futuro, sem cachê pago) com venda e sem linha de comissionado, cancelado com retido; o mesmo com vendedor sem `receives_commission` | cancelada / −100; a linha nasce no cancelamento; não comissionado: cheia 0 e nenhuma linha (os 62, 69 e 203 do espelho não servem: são passado quieto) | não | 1 (2) | L1942 |
| 11 | EducaManto com `a_pagar` na data do evento; variante semeada sem `a_pagar` | reduzida no lugar, data intocada (Q2 = A); ajuste de paga no primeiro repasse aberto do responsável; na variante, a linha nova nasce com liberação na data do evento | não | 1 (2) | L1943 |
| 12 | Reabrir Comissões e Planilha (resync), depois a DRE e o evento | comissão do retido 18 nas quatro; Σ linhas vivas = alvo para todo cancelado com congelamento | não | 1 (2, sem a DRE; a DRE: 3) | L1944 |
| 13 | Planilha × Comissões por identidade de linhas (vendedor descartável), mês da venda e mês do ajuste | mesmas linhas e mesmo desconto; `total_month == total_paid + total_no_banco + total_pending` | não | 1 | L1945 |
| 14 | Desconto que zera o repasse; ajuste em ciclo com estorno órfão `a_pagar` | o item de soma zero continua; o órfão não abre ciclo | não | 1 | L1946 |
| 14b | Exclusão de evento vazio com comissão paga e com comissão no banco (semeado), `hoje` nos dias 2 e 10 | estorno órfão no primeiro repasse aberto, não na data da venda; no banco igual; Planilha do ciclo da venda não reabre; mutação contra a `main` | não | 1 | L1947 |
| 15 | Alterar devolução: 600 → 800 com comissão 20 a pagar; com a paga, 800 → 500; diminuir devolução paga; "Nada" → 300 em duas chamadas simultâneas | comissão 20 → 10; com a paga, o ajuste a pagar vai de −90 a −75 no lugar (Σ 25; nasce +15 só se o −90 estiver liquidado); recalcula na hora; diminuir paga → 409; um complemento só | **sim** (os dois últimos) | 2 | L1948 |
| 16 | D36: Superadmin acrescenta comprovante de 200; CASTING acrescenta comprovante e tenta o `PATCH …/devolucao`; variante 16-vivo: COMERCIAL acrescenta comprovante, reembolso e parcela num evento vivo avulso e num dia vivo de grupo; pago abaixo do devolvido; variante 16/17-`paid_amount`: o BV do retido (40) marcado pago na Planilha antes do comprovante de 200 e depois desfeito; marcar com valor esperado divergente; marcar BV que não está a pagar | retido 600, comissão 27 e BV de 40 para 60 na Planilha, sem ajuste manual; CASTING recebe 409 no comprovante e 403 no `PATCH`; abaixo do devolvido → 409 `pago_abaixo_do_devolvido`; na variante, o BV pago fica em 40 depois do comprovante (não vira 60, sem acerto ao parceiro) e, desfeito, volta a 60; divergente → 409 com o valor atual; não a pagar → 409 `bv_nao_esta_a_pagar`; no 16-vivo, as respostas e a comissão sincronizada iguais às da `main` | **sim** (os dois últimos; na variante, os dois 409) | 2 | L1949; plan (leitura 10, decisão (a)); checklist regressão CHK010 |
| 16b | Superadmin corrige dados de venda: venda 2.000 → 2.400 com a comissão paga cheia; taxa 2,5 → 3,0 em cancelado semeado sem taxa própria (variantes: 3,0 → 2,0 e, quando a 1e existir, data de venda em outra taxa); cortesia/permuta; nota fiscal e parcela; satélite cancelado; COMERCIAL no `PATCH …/comercial`; FINANCEIRO lançando nota; variante "cheia 0": cancelar uma cortesia/permuta com valor e um evento sem vendedor | venda e cheia recongeladas; comissão e BV do retido pela proporção; paga intacta e diferença no primeiro repasse aberto; taxa: `commission_rate` 3,0 e diferença para mais com "taxa corrigida" (descendo, desconto); cortesia: cheia 0 e desconto do pago; nota e parcela gravadas e congelado intacto; satélite → 409; COMERCIAL e FINANCEIRO → 409 `cancelado`; na variante, cheia congelada 0 e nenhuma linha de comissão nasce, e a comissão desses eventos vivos, antes do ato, é a de hoje | **sim** (as três últimas) | 4 (satélite: 5; a variante também em modo núcleo na Fundação) | L1950; plan (Living Spec 16) |
| 16c | Troca de vendedor (retido 400, comissão 18, taxa congelada 5%): (i) cheia 90 paga a A, com −72 a pagar, troca para B; (ii) só a pagar; (iii) B sem comissão; (iv) EducaManto com responsável; (v) COMERCIAL | (i) paga de 90 intacta, −72 vira −90, B ganha +18 no repasse dele, congelado com B, retido sai de A e vai a B no Dashboard e em `/admin/desempenho`; (ii) a de A cancelada e a de B com 18; (iii) ninguém recebe; (iv) só o recorte comercial (variante da 2b no verify dela); (v) 409 `cancelado`; auditoria das linhas de A e B e varredura sem ajuste sem evento ou motivo; mutações: um beneficiário só, nota sem prefixo | **sim** (o v) | 4 | L1951 |
| 16d | Acréscimos e reembolsos: BV não pago 200 → 300; PIX e recebedor corrigidos; transporte mudado; BV pago com outro valor; BV pago ausente do corpo; acréscimo novo sem id; reembolso lançado e cobrado; COMERCIAL no `PUT …/acrescimos` | BV cheio 300; BV do retido 60; cheia sobre 2.000 − 300 com a taxa congelada; mesmo id antes e depois (mutação por apagar e recriar acusa); PIX novo na Planilha do mês do evento; transporte sem mexer no congelado; BV pago com outro valor → 200 com o valor pago intacto (como no vivo); BV pago ausente → 400 `items`, nada gravado e o pago intacto; o novo nasce; reembolso gravado com retido intacto; COMERCIAL → 409 `cancelado` | **sim** (o ausente e o COMERCIAL) | 4 | L1952 |
| 16e | Taxa congelada: cancela com a padrão 2,5%; a padrão vai a 3%; corrige venda, troca vendedor, acrescenta comprovante, abre Comissões e Planilha; corrige a taxa do cancelado para 3% à mão | 2,5 no ato e em toda recongelação; a padrão não mexe; só a correção à mão leva a 3 (e refaz a paga para mais); mutação lendo a taxa de hoje salta na primeira correção; configuração volta a 2,5 no `finally` | não | 4 | L1953 |
| 17 | BV 200 com "Nada" (retido 1.000), "Tudo" (retido 0) e já pago antes; satélite cancelado com BV pago e com BV não pago; variante 16/17-`paid_amount`: o BV pago antes do ato, com "Nada", desfeito na Planilha depois | Planilha (API e Jinja) no mês do evento: 100 / nada / 200 pago intacto / pago do satélite intacto / não pago do satélite fora; regressão `main` × branch dos itens de BV dos meses sem cancelado; na variante, desfeito o pago, a Planilha mostra o proporcional (100) | não | 1 (2; satélite: 5) | L1954; plan (decisão (a)) |
| 18 | Gastos Extras: "Salvar" sem mexer; corrigir PIX; mudar valor, data, categoria, vínculo ou excluir; aprovar ou rejeitar devolução de cancelado; `POST` tipo `cliente`; `PATCH` fornecedor → cliente; devolução de evento vivo editada; variante 18-inverso: `PATCH` de um gasto comum e de uma multa ligados ao cancelado trocando a categoria para devolução, e de uma devolução de evento vivo trocando o `event_id` para o cancelado | destinatário, nome e PIX mantidos, sem "aprovado com edição"; PIX trocado; travados → 409 com `event_id`; criar ou converter → 400; evento vivo editável; no inverso, 409 `devolucao_travada` (`fields.category`, `fields.event_id`) e o retido intacto | **sim** (os recusados) | 2 | L1955 |
| 19 | *(reescrito por esta spec, 1c-Q11 = C)* `PATCH …/orcamento` em cancelado, pelo Superadmin, pela COMERCIAL e pelo FINANCEIRO; `DELETE` em cancelado, pelo Superadmin e pela COMERCIAL; `PUT …/acrescimos` pela COMERCIAL e pelo FINANCEIRO | `PATCH …/orcamento` → 409 nos três; `DELETE` pelo Superadmin → 409 (COMERCIAL → 403, gate de hoje, `agenda_write.py:549-550`); `PUT …/acrescimos` → 409 `cancelado` nos dois; nada muda (o `PUT` do Superadmin é o 16d) | **sim** | 2 | L1956 (superado: "409 nos três"; também L846) |
| 20 | DRE do mês do cancelamento, API e tela antiga (`template_rendered`); mutação contra a `main` (`git archive`, mesmo banco, relógio fixo) | retido 400; custo +40; comissões +18; gastos extras sem os 600; +342 em Realizado e Total, 0 no Projetado; API = Jinja ao centavo; `main` dá −600; num mês **sem** cancelado, `paineis.cancelamentos.quantidade == 0` e `retido_cancelamentos` e `n_cancelados` presentes nas três DREs (FR-045) | não | 3 | L1957; checklist CHK029 |
| 21 | Mês do evento; Tendência; com nota (imposto 64); devolução alterada para 800; multa ligada ao cancelado (semeada por ORM, com a categoria "Multa de cancelamento" criada na Fundação); devolução ligada a evento vivo; satélite e virtual cancelados; "Tudo" com BV 200 pago | mês do evento sem nada; Tendência sem os 2.000 e com +400; +64 / +278; retido 200; multa e devolução viva seguem em gastos extras; satélite e virtual sem retido; retido 0, comissão 0, custo +200 | não | 3 (satélite: 5) | L1958 |
| 22 | Ticket médio, "a receber", Receita por Tipo, Fator R, break-even, Recebimentos Previstos, nota a emitir e Top Vendedores, nas duas telas | ticket e "a receber" iguais; barra 400; Fator R e break-even com o retido; parcela fora; nota com selo; vendedor +400 nas duas | não | 3 | L1959 |
| 23 | Regressão `main` × branch dos meses sem cancelamento (`retrato_main_branch.py`): DRE (API e Jinja), Tendência e painéis da DRE; Dashboard Comercial; `/admin/desempenho`; ficha de toda cliente com evento; Performance da Home; Comissões (KPIs, `by_seller`, `month_status`); itens de comissão e de BV da Planilha | idênticos ao centavo, antes de qualquer cancelamento do verify, com as mudanças de propósito listadas à parte (SC-002); mutação: somar o retido sem a condição da quantidade de cancelados acusa a diferença | não | Fundação (verde em todas) | L1960; checklist regressão CHK020, CHK021 |
| 24 | Dashboard Comercial, `/admin/desempenho`, ficha da cliente e Performance da Home, no mês do cancelamento e no do evento | +400 e comissão 18 no mês do cancelamento, nada no do evento; cliente com total 400; Performance sem cargo nem cachê do cancelado; status de pagamento "cancelado"; `/vendas/` Jinja sem o cancelado; "Com evento" e "Recorrentes" da cliente sem ele (FR-046) | não | 3 | L1961; checklist CHK029 |
| 25 | Payload do evento cancelado: `cancelamento` só com `show_comercial`, PIX só com `show_financeiro`, `kpi` ausente, `can_edit_pagamentos`; no evento **vivo**, `venda.pode_mudar_taxa` e `venda.pode_trocar_vendedor` para Superadmin e COMERCIAL | 1.000 / 600 / 400 / 18 / 40; CASTING sem o bloco; no vivo, as duas flags iguais às da `main` (a 215b intacta) | não | 2 | L1962; checklist regressão CHK009 |
| 26 | `contagem_pre_deploy.py` em modo leitura; retrato de todas as linhas de comissão do espelho antes e depois do verify inteiro (descontados os semeados) e de abrir Comissões e Planilha | a contagem não escreve nem lista pago a menos ou a mais; nenhuma linha nasce, muda ou é cancelada fora dos eventos do verify (270, 294, 311, 405, 62, 69, 203 e estornos 151 e 211 como estão) | não | Fundação (verde em todas) | L1963 |
| 27 | Limpeza | descartáveis apagados na ordem abaixo; nenhuma chamada de rede escapou do dublê | — | todas | L1964 |
| 28 | Sem sessão em `POST …/cancelar`, `PATCH …/devolucao`, `GET …/impacto-exclusao?devolucao=` e `GET /events/cancelamentos`; evento inexistente no `PATCH`; FINANCEIRO cancela e acrescenta comprovante em cancelado; MARKETING, ENSAIO e ARTISTA_3D leem `/events/cancelamentos`; Superadmin "vendo como Comercial" | 401 nos quatro; 404 antes do 403; FINANCEIRO 403 no cancelar e 409 no comprovante; 403 nos três; no "Ver como", `flags.can_delete` e `can_edit_pagamentos` falsas e a API aceita pelo papel real (comportamento de hoje, registrado) | **sim** | 2 | L1965 |
| 29 | Agrupar cancelado como satélite e como principal (API e Jinja, mesmo núcleo); desagrupar satélite cancelado; desagrupar dia vivo | 409 com a frase do agrupamento e nenhuma venda zerada; desagrupar o cancelado → 409; desagrupar o vivo passa | **sim** (os três primeiros) | 5 | L1966 |
| 30 | Corrida: outra sessão marca o item "pago" na Planilha entre a leitura do endpoint e o bloqueio do núcleo (injeção determinística); sincronização chamada com o evento lido antes | a paga fica 100 e nasce −80 (nunca "paga de 20"); a linha do retido não é regravada | não | 1 (2) | L1967 |
| 31 | Google: dublê que falha; trava `CALENDAR_SUPPRESS_EVENT_WRITES` ligada; cancelado ainda no Google + `POST /api/events/<id>/sync` | conclui com `aviso` e resumo certo; com a trava, zero chamadas; "Sincronizar" não toca o cancelado | não | 2 | L1968 |
| 32 | Pago maior que a venda; comprovante sem valor | comissão = cheia, DRE com o retido inteiro, "Tudo" devolve o pago; sem valor conta zero e o impacto diz quantos (`comprovantes_sem_valor?`) | não | 2 (a DRE: 3) | L1969 |
| 33 | Evento passado com cachê pago (e variante no banco), cancelado pela API e pelo marcado da 303 | 409 `cache_pago` com a frase; nada gravado (nem devolução, ensaio ou aviso); o marcado só com "Devolver ao Google"; impacto com `cache_pago` > 0; vaga de presença do técnico de som não conta | **sim** | 6 | L1970 |
| 34 | Excluir o usuário que é vendedor congelado de um cancelamento e não é vendedor de evento nenhum | bloqueio "cancelamentos", não 500 | **sim** | 2 | L1971 |
| 35 | Marcado pela 303 que é principal de grupo; satélite marcado | principal: impacto com `acao: "cancelar"`, leva todos os dias e a marca sai de cada um; satélite: só aquele dia, com `venda_nova`, e a marca sai | não | 5 | L1972 |
| 36 | Devolução na Planilha: mês em que aparece; complemento de "Alterar devolução"; marcar pago, no banco e desfazer | mês do cancelamento; complemento no mês em que nasce; a trava de Gastos Extras não alcança o status de pagamento | não | 2 | L1973 |
| 37 | Grupo semeado (principal com venda 3.000 e 2 dias; comprovantes de 1.000 no principal e 500 num dia; comissão 75 a pagar): "Cancelar todos os dias" com Parte 900 | 3 dias numa transação, sem desagrupar; pago 1.500; retido 600; comissão 15 no lugar; um `EventLog` por dia; linhas `venda` e `satelite` com o principal; 3 remoções no dublê depois do commit; dia já cancelado intocado; uma comissão própria paga semeada num satélite (molde do 287) fica paga e fora da conta (P-51); variante 37-devolução: uma devolução de 200 lançada antes num satélite e, depois do ato, o ato com Parte 900 (total devolvido 1.100) e o "Alterar devolução" do principal de 1.100 para 100 → a do principal (900) é excluída e a do satélite cai a 100, com auditoria nas duas (FR-017) | não | 5 | L1974 |
| 37b | O grupo do 37, já cancelado inteiro: o Superadmin acrescenta um comprovante de 200 num dia `satelite` | pago do grupo 1.700; retido do principal 600 → 800 e comissão do retido 15 → 20 no lugar, na mesma transação e sem ajuste manual; a linha `satelite` continua sem dinheiro próprio; `EventLog` no dia e no principal; a resposta é o detalhe do dia | não | 5 | plan (Living Spec 4; decisão (c)) |
| 38 | Grupo vivo: "Cancelar só este dia" num satélite, `venda_nova` 2.000, Parte 300; comissão do principal a pagar e, na variante, paga; *(clarify 15/10 = A)* depois, "Alterar devolução" do dia cancelado: 300 → 30 e, à parte, acima do teto do grupo; variante 38-comprovante: o Superadmin acrescenta um comprovante no dia cortado e, num grupo semeado para isso, corrige um comprovante do dia deixando o pago do grupo abaixo do devolvido | linha `dia` 3.000 → 2.000; principal vivo com 2.000 e `EventLog`; a pagar vira 50; paga: 75 intacta e −25 no primeiro repasse aberto com `original_id`; devolução de 300 ligada ao dia, fora dos gastos extras da DRE e dentro do "já devolvido"; DRE do mês do evento com 2.000; BV não pago na proporção; cheio 3.300 → 2.200 (selo de 10% igual, desconto 300 → 200); dia no grupo; Home com 800 a receber; alterada para 30: devolução do dia 30, "já devolvido" e cobrança da Home refeitos, comissão do principal e linha `dia` intactas, com auditoria; acima do teto → 409 `acima_do_teto`; na variante 38-comprovante, nada se refaz (comissão do principal e linha `dia` intactas; a cobrança da Home relê o pago) e o abaixo do devolvido → 409 `pago_abaixo_do_devolvido`, sem gravar nada | **sim** (o acima do teto; na variante, o abaixo do devolvido) | 5 | L1975; plan (Living Spec 4) |
| 38c | Grupo vivo semeado (venda 4.000 a 2,5%, comissão de 100 do principal **paga**): "Cancelar só este dia" num satélite, `venda_nova` 3.000, "Nada"; depois, o Superadmin desfaz o "pago" da base pela Planilha (267c); depois, abrir Comissões e a Planilha (resync) | depois do corte: 100 paga + −25 a pagar (Σ 75); depois do desfazer: 100 a pagar + −25 a pagar (Σ 75); depois do resync: base 75 no lugar e o −25 cancelado (Σ 75), nunca 75 − 25 = 50; com a base ainda paga, o resync não mexe; a mutação sem a regra nova da sincronização dá Σ 50 | não | 5 (a regra da sincronização nasce na 1) | plan (Living Spec 2; decisão (b)) |
| 39 | Depois do 38: gravar a aba Comercial do principal; abrir Comissões e Planilha; cancelar o resto do grupo; variante: depois de cancelar o resto, "Alterar devolução" do dia cortado | o −25 não é sobrescrito; o cancelamento do resto soma os 300 no "já devolvido" e o teto do "Tudo" os desconta; na variante, o "já devolvido" muda pela diferença, e o retido e a comissão do retido do principal se refazem na mesma transação (D28), com o ajuste da paga no primeiro repasse aberto | não | 5 | L1976; plan (Living Spec 6, derivado da D28) |
| 40 | Soltar o dia cancelado (API e Jinja); agrupar com ele; dia com cachê pago no "Cancelar todos os dias"; ENSAIO pela API de cancelar | 409 nos quatro: desagrupar; agrupamento; `cache_pago` dizendo qual dia, sem gravar nada em dia nenhum; `ensaio` | **sim** | 6 (os dois primeiros passam com a 5) | L1977 |
| 41 | Custo do grupo com dia cancelado: KPI do principal; custo de EducaManto principal com satélite cancelado; data do grupo na cobrança da Home | o cachê do dia cancelado sai do custo e da base EducaManto; o comprovante do dia segue na cobrança; regressão `main` × branch das comissões de todos os grupos do espelho e das cobranças da Home de toda venda sem devolução (`cobranca_ops`, pelas chamadas de hoje) | não | 5 | L1978; checklist regressão CHK014 |
| 42 | Passar a venda, soma antes = soma depois (grupo no mesmo mês: principal com 3.000 e cheio 3.300, comprovantes de 1.000 e 500, parcela, nota a emitir, contrato, BV 200 a pagar com recebedor e PIX, transporte 100, comissão 75 paga e −25 a pagar, devolução 100, formulário, cliente, orçamento e nome do grupo; outro dia vivo com comprovante de 200; um dia já cancelado). "Cancelar só este dia" no principal, venda nova 3.000, "Nada" | toda linha igual (id, valor, datas, estado, beneficiário), salvo o `event_id`, que vai ao dia vivo mais cedo; Σ por tipo igual (comprovantes 1.700, acréscimos 300 com o BV no mesmo estado, comissão 75 paga e −25 nas mesmas datas, devolução 100); campos no novo principal e zerados no antigo, com retrato no histórico dos dois; dias apontando ao novo; antigo 1º dia como `dia` (3.000 → 3.000), elenco avisado e ensaio apagado; DRE, Planilha, Comissões, Dashboard e cobrança iguais; mutação por apagar e recriar acusa ids novos e BV pago perdido | não | 5 (aviso e ensaio: 6) | L1979 |
| 42b | O mesmo grupo, venda nova 2.400 e Parte 300; variante com a comissão só a pagar | passagem como no 42 e corte como no 38 contra o novo principal; BV a pagar 200 → 160; cheio 3.300 → 2.640 sem aumentar o desconto; devolução de 300 ligada ao antigo 1º dia, fora dos gastos da DRE e dentro do "já devolvido"; multa por escalação do antigo 1º dia | não | 5 (multa: 6) | L1980 |
| 42c | Novo 1º dia noutro mês (31/10 → 01/11), EducaManto com comissão a pagar; satélite que vira principal com comissão própria paga de antes (molde do 287); coluna de dia de orçamento da 3b, se existir | Q15 = A: receita, imposto, BV, cachês e comissão na DRE de novembro, BV na Planilha de novembro, outubro sem nada nas duas DREs; data de venda e ciclo da comissão comum iguais; Q18 = A: EducaManto a pagar com liberação em 01/11 depois do resync (mutação: guardando a data antiga, fica em 31/10); comissão própria fora da conta; coluna de dia intocada | não | 5 | L1981 |
| 42d | Recusas da passagem: cachê pago no antigo 1º dia; devolução pendente ligada a ele; `alcance` ausente; "só este dia" em principal sem outro dia vivo; `novo_principal_id` que não é o mais cedo; exceção injetada no meio; duas confirmações simultâneas; COMERCIAL | 409 `cache_pago`; 409 pendente; 400 `alcance`; 409; 409 `grupo_mudou`; rollback com retrato idêntico; uma vence e a outra recebe 409; 403; em todos, nenhuma linha muda de `event_id` nem de valor | **sim** | 5 (cachê pago: 6) | L1983 |
| 42e | Grupo SHOW com um ensaio ligado ao 1º dia e outro ligado a um dia que fica; "Cancelar só este dia" no principal | o ensaio do antigo 1º dia sai do banco na transação e do Google depois do commit, com sino à equipe de Ensaio; nenhum ensaio muda de `parent_event_id`; o outro não é tocado; o "precisa ensaio" do novo principal fica | não | 6 | L1982 |
| 43 | Show com 2 ensaios futuros cancelado; variante com a trava; variante com o dublê falhando no 2º ensaio; grupo com ensaio em 2 dias | ensaios apagados na transação; dublê conta show + ensaios depois do commit; com a trava, zero chamadas e aviso; falha vira aviso sem desfazer; histórico do show com data e local de cada ensaio; "Cancelar ensaio" e troca SHOW → outro iguais | não | 6 | L1984 |
| 44 | Aviso: show com ensaio e 3 escalados (um em 2 dias, um com convite recusado); show sem ensaio; corte de um dia e passagem; variante: corte de um dia com ensaio e, depois, "Cancelar todos os dias" com ensaio | `evento.cancelado` por usuário ENSAIO ativo na transação; e-mail uma vez por pessoa, nenhum a quem recusou, depois do commit, zero envio real; sem ensaio, avisa os escalados e não a equipe de Ensaio; no corte, só o elenco do dia; 409 não avisa; `evento.cancelado_escala` a cada CASTING ativo, uma por dia com escalados, com os avisáveis, link `?aba=producao`, `urgent` a 2 dias e `info` a 60; sem elenco, nenhuma; lista do ato com as mesmas pessoas, uma linha por escalação (o escalado em 2 dias tem 2); na variante, cada usuário ENSAIO ativo recebe 2 `evento.cancelado`, um por ato (a mutação com a chave do principal acusa) | não | 6 | L1985; plan (Living Spec 15) |
| 45 | Multa no ato: 2 escalados, 150 para um e vazio (ou 0) para o outro; talento sem PIX; evento a 60 e a 2 dias; escalado que recusou | `faltam_dias` 60 / 2 e o bloco nos dois; nada sugerido; quem recusou fora; 1 Gasto Extra "Multa de cancelamento" aprovado, a pagar, ligado, com nome e PIX do talento e data do cancelamento; Planilha e DRE do mês do cancelamento +150 (resultado +342 − 150); retido 400, comissão 18 e BV 40 inalterados; sem PIX, nasce e a Planilha mostra "sem PIX"; editável em Gastos Extras | não | 6 | L1986 |
| 45b | Multa depois do ato: `POST …/multas` com 150 em cancelado sem multa no ato; o mesmo em evento vivo; CASTING e COMERCIAL | Gasto Extra igual ao do 45 com a data do lançamento; Planilha e DRE do mês do lançamento +150; retido, comissão e BV inalterados; vivo → 409; CASTING e COMERCIAL → 403 | **sim** (as três últimas) | 6 | L1987 |
| 45c | Multa a quem o Casting já tirou da vaga: 2 escalados; CASTING tira um pela escala; `POST …/multas` pela linha da lista do ato; à parte, `elenco_id` de outro evento e artista fora da lista | a vaga fica sem talento e a linha da lista intacta; multa com nome e PIX do cadastro; `cancelamento.elenco` mostra os dois, o tirado com "saiu da escala"; os de fora → 400 `fields.multa_<id>`, nada gravado; e-mail de remoção zero no cancelado e um em evento vivo; mutações: lista lida da escala de hoje e remoção sem a condição | **sim** (os dois de fora) | 6 | L1988 |

O cenário **46 saiu** em 13/10. A 1b-Q12 = B virou a 1e, com verify próprio, e o que restava dele já está provado
no 38 e no 42b (L1989).

**Contagem**: 59 cenários vivos — 45 números (1 a 45) mais 14 sufixos (2b, 14b, 16b, 16c, 16d, 16e, 37b, 38c,
42b, 42c, 42d, 42e, 45b, 45c). O 37b e o 38c entraram pelo `/speckit-plan`. Não existe 42a: o próprio 42 abre a
série (L3548). Pela coluna "Deve falhar?": 20 com "sim", total ou parcial (o 38 ganhou a recusa do "Alterar
devolução" acima do teto no clarify de 15/10); 38 "não", entre eles o 37b e o 38c; 1 "—", o 27.

**Variantes** (rodam dentro do cenário de origem, fecham com ele e não contam como cenário): 2 e 8, prévia =
execução; 9/10-desfazer; 16/17-`paid_amount`; 16b, "cheia 0"; 38-comprovante; 39, devolução do dia depois do
principal cancelado; 44, dois sinos. O 1 confere a comissão do evento vivo, que fica intocada.

**Mudanças em relação ao plano** (Clarifications, Session 2026-10-15):
- o 6 perde a leitura do FINANCEIRO;
- o 19 foi reescrito;
- o 16b ganhou base de taxa própria;
- o 45b e o 45c fecham na História 6, e não na fase 9;
- o 42e fecha na História 6, e também as partes de aviso, ensaio, multa e cachê pago do 2b, 42, 42b e 42d
  (leitura 5);
- o 17 fecha com a História 1 (verde junto da 2), e não na fase 4 do plano (leitura 5);
- o 16b, 16c, 16d e 16e fecham na História 4, depois da DRE, e não dentro da História 3 do plano (leitura 5);
- o 16d ganhou o caso "BV pago ausente do corpo → 400 `items`" (leitura 6);
- pelo `/speckit-plan` (Session 2026-10-15, `/speckit-plan`): entram o 37b e o 38c; o 1, o 2, o 8, o 9, o 16, o
  16b, o 17, o 38, o 39 e o 44 ganham variantes; o 12 e o 32 fecham sem a DRE na História 2 e com ela na 3; a multa
  do 21 é semeada por ORM; o 4 ganha o imposto enviado sem nota; o 45 aceita 0 como vazio.

**Limpeza** (L1991-2013) é por ORM, no molde de `verify_303.limpar`, porque o cancelado não se exclui pela API.
Ordem e cuidados:
1. A devolução e a multa são apagadas **antes** de `_clear_event_side_tables`, que só desvincula o gasto; senão
   ficam órfãs na DRE.
2. Primeiro os ajustes de comissão (com `original_id`), depois as linhas originais. `event_cancellations` sai por
   CASCADE.
3. O vendedor descartável sai depois das linhas e do cancelamento.
4. Os grupos saem do satélite para o principal.
5. As notificações `evento.cancelado` e `evento.cancelado_escala` saem por `apagar_por_entidade`.
6. Os ensaios saem pelo próprio cancelamento; a limpeza só confere que não sobrou nenhum.
7. As linhas semeadas são achadas pelos ids, nunca pelo evento.
8. O formulário de pré-contrato sai pelo id, antes dos eventos.
9. A lista do elenco do ato sai por CASCADE, depois das multas.
10. A taxa mudada no 16e volta no `finally`.
11. A vaga esvaziada no 45c volta ao talento de antes, com o e-mail espiado.

Salários e recorrentes criados pelo aquecimento da Planilha ficam no espelho, e o verify declara isso na saída.

**Harness `main` × branch** (nasce aqui, do zero; L1761-1763, L2784-2787, L3847-3850). Não há nada versionado
para reusar: o `subprocess` do `verify_303` é só a prova da trava de ambiente.
- `git archive` da `main` numa pasta temporária, não `worktree`, com a base em `git merge-base`.
- Os dois lados rodam em subprocesso.
- A comparação é exata: Decimal com quantize 0,01 e percentual a 0,1.
- `retrato_main_branch.py` não importa nada que só exista na branch.
- É exigido nos cenários 1, 14b, 17, 20, 23 e 41 (este com a regressão das cobranças da Home sem devolução).

**Scripts**:
- `specs/306-…/retrato_main_branch.py`: compara, `main` × branch e com relógio fixo, as telas do cenário 23 nos meses sem cancelamento.
- `specs/306-…/contagem_pre_deploy.py`: só leitura, roda por SSH, no molde do da 303. O que conta está em
  Premissas, "Deploy".
- Saíram `listar_estornos_orfaos.py` e `listar_comissao_paga_a_menos.py` (1b-Q3, Q7).

**Portões além do verify**:
- `npm run typecheck`, `ruff check` e `npm run build`;
- e-mail real travado durante a conferência de tela;
- `verify_303.py` e `verify_205.py` verdes de novo.

**Verifies antigos** (L1893-1906, L3512-3514):

| Verify | Situação | O que fazer |
|---|---|---|
| `verify_303.py` | o `c12_nao_cancela` esperava 409 ao cancelar o marcado | reescrever o cenário 12; a parte de excluir continua, comparando com a mensagem nova do marcado |
| `verify_267.py` | quebra: lê `kpi["commission"]` de um cancelado gravado à mão | passa a ler o bloco `cancelamento` de um `legado` |
| `verify_267b.py` | regressão da extração e do builder | rodar de novo |
| `verify_299.py` | ciclo da comissão | rodar de novo |
| `verify_205.py` | pipeline | rodar de novo |
| `verify_267c.py` | item da Planilha partido em aberto × pago, e o desfazer, que passa a travar os eventos antes das linhas | rodar de novo |
| `verify_305.py` | conferência do valor esperado do BV e o editor de acréscimos, cuja montagem esta entrega extrai e fatia | rodar ao fechar a História 1 (o ramo BV passa por `marcar_status_do_bv`) e de novo na História 4, logo depois da extração e antes de usar a montagem no cancelado |
| `verify_215b.py`, `verify_266.py`, `verify_258.py` e `verify_256.py` | portas e arquivos em comum (lista do `/speckit-plan`) | rodar de novo |
| `verify_273.py` e `verify_301.py` | o 409 novo em `set_event_orcamento` vem antes de aplicar a venda e antes da autoria da 301 (contratos §12); o 273 tem base conhecida de 8/15 | rodar de novo, comparando com a base |
| `verify_272.py` | o catálogo `DESTINATARIOS_POR_KIND` ganha dois kinds (os sinos do cancelamento) | rodar de novo |
| `verify_238.py` | `assign_role` ganha a condição do e-mail de remoção (FR-069) | rodar de novo |
| `verify_271.py` | a `GET /api/dashboard`, onde mudam a Performance e a cobrança da Home | rodar de novo |
| `verify_307.py` | a 307 mexeu em `orcamento_evento_ops.py`, `orcamento/quote_ops.py` e `calendar/routes.py`, que a 306 também altera | rodar de novo |
| não versionados de `scripts/db/` | envelhecem | registrar como dívida |

A fase em que cada um pode quebrar primeiro está no quickstart §5.

**Cenários daqui que outras entregas rodam de novo**:
- a **1e**: 9, 38 e 42b (sem acerto em dobro no corte);
- a **2b**: 11, 16c, 42c e 44, e a variante (iv) do 16c;
- a **6a**: o retrato do 42, com as três colunas de canal;
- a **3b**: o cenário 27 de lá passa a conferir este cancelamento.

**Conferência de tela** (app interno, desktop; inputs React pelo setter nativo; L2015-2032).

*Diálogo de cancelar*:
1. Parte, BV proporcional (com recebedor e PIX obrigatórios quando faltam), imposto e efeito.
2. Principal com a lista dos dias e "Cancelar todos os dias".
3. Dia não principal com "Novo valor da venda".
4. Recusa de cachê pago, sem botão de cancelar, apontando Gastos Extras.
5. Bloco "Multa ao elenco" com "faltavam N dias".
6. "Cancelar só este dia" no principal, dizendo para qual dia a venda passa.

*Evento cancelado*:
7. A tela do novo principal depois da passagem, com venda, comprovantes e comissão; o antigo 1º dia com o link
   para o dia que recebeu a venda.
8. "Resultado do cancelamento" e "Alterar devolução".
9. Dados de venda abertos para o Superadmin: valor corrigido com o resultado relido; vendedor trocado com o aviso;
   BV corrigido com o BV pago só leitura; reembolso lançado; nota e parcela gravadas.
10. "Lançar multa ao elenco" com quem saiu da escala marcado.
11. O sino do Casting abrindo o cancelado.
12. A mesma tela vista por papel sem a flag: só consulta, e o 409 `cancelado` aparece com o motivo.
13. A aba Comercial presente com `kpi` ausente.

*Evento marcado*:
14. As duas saídas no diálogo e no banner, este com largura total no celular; a faixa some logo depois de
    cancelar.

*Financeiro e comercial*:
15. Gastos Extras com a devolução travada.
16. Comissões com "No banco" e a data de borda no dia 1º.
17. Planilha com o BV proporcional no mês do evento e a multa no mês do cancelamento.
18. Painel "Grupo comercial" com um dia cancelado.
19. DRE nova e DRE antiga com a linha do retido.
20. Sublinha do retido no Dashboard Comercial e em `/admin/desempenho`.
21. Página de Cancelamentos (Superadmin) com o resumo e o estado no banco.

## Critérios de sucesso *(obrigatório)*

- **SC-001**: No exemplo-padrão, a DRE do mês do cancelamento mostra +R$ 400 de retido, +R$ 40 de custo e +R$ 18
  de comissões, sem os R$ 600 em gastos extras. O resultado é **+R$ 342** (+R$ 278 com imposto de 64) em
  Realizado e Total, igual ao centavo na tela nova e na antiga. O mês do evento não mostra nada dele. Na `main`,
  o mesmo caso dá −600.
- **SC-002**: Seis regressões ficam idênticas ao centavo entre `main` e branch, cada uma com o seu cenário:
  - DRE e Tendência de **todos** os meses sem cancelamento, com os painéis da DRE (Top Vendedores, Receita por
    Tipo, Recebimentos Previstos, NF a emitir e indicadores), o Dashboard Comercial, o `/admin/desempenho`, a
    ficha de toda cliente com evento e a Performance da Home (cenário 23);
  - Comissões (KPIs, `by_seller`, `month_status`) e os itens de comissão e de BV da Planilha dos meses sem
    cancelamento (cenário 23; os de BV também no 17);
  - comissões de todos os grupos (cenário 41);
  - a comissão do evento vivo (a regra de hoje, intocada sob a comissão cheia), em todos os eventos do espelho
    (cenário 1, L1932);
  - as cobranças da Home de toda venda sem devolução (cenário 41, L1836).

  Ficam fora da comparação, listadas à parte porque mudam de propósito: o ticket médio do Jinja (FR-043), o
  `sale_count` de Comissões, o item aberto de comissão de soma zero com linha de valor (R6) e o mês com cancelado
  `legado` (hoje nenhum). *(Living Spec do checklist: eram cinco regressões, sem as telas comerciais, Comissões
  nem cenário para a cobrança da Home.)*
- **SC-003**: A comissão de todo cancelado é cheia × retido ÷ venda, nunca acima da cheia. Depois de reabrir
  Comissões e Planilha, a soma das linhas vivas continua batendo com o alvo em 100% dos cancelados.
- **SC-004**: Nenhuma comissão ou BV já pago (ou no banco) é reescrito por cancelamento, correção ou troca de
  vendedor, salvo o vínculo ao evento na passagem da venda do 1º dia (Q5 = B; L1036-1038, L2666).
  - Toda diferença nasce no primeiro repasse aberto, e nenhum ajuste cai em repasse liquidado.
  - 100% das linhas de ajuste têm evento e motivo.
- **SC-005**: Para cada vendedor, Planilha e Comissões mostram as mesmas linhas e o mesmo desconto, com total do
  mês = pago + no banco + a pagar.
- **SC-006**: Nenhuma devolução passa do que a cliente pagou menos o já devolvido. Nenhuma edição em Gastos Extras
  perde o nome ou o PIX de uma devolução.
- **SC-007**: Proteções do ato:
  - todo evento marcado pela 303 **sem cachê pago ao elenco** pode ser cancelado com devolução, com zero chamadas
    ao Google; o marcado com cachê pago continua só com "Devolver ao Google" (L1469-1471, L2222, cenário 33);
  - 100% dos eventos com cachê pago são recusados, sem nada gravado.
- **SC-008**: Na passagem da venda do 1º dia, o retrato de toda linha pendurada no evento fica idêntico antes e
  depois, salvo o vínculo, e a soma por tipo fica igual em qualquer mês. Com o novo 1º dia no mesmo mês, DRE,
  Planilha, Comissões, Dashboard Comercial e cobrança da Home também ficam iguais (cenário 42). Noutro mês, a
  receita, o BV da Planilha e a comissão EducaManto a pagar mudam de mês, como manda a FR-060 (Q15 = A, Q18 = A), e
  a soma dos dois meses fica igual (cenário 42c). *(Living Spec do checklist: a redação anterior prometia as telas
  iguais sem esse recorte.)*
- **SC-009**: Em todo cancelamento:
  - cada escalado que não recusou, fora a vaga de presença do técnico de som, recebe **um** e-mail, e quem recusou
    não recebe nenhum (L1433-1434, L2817-2818);
  - a equipe de Ensaio recebe o sino só quando havia ensaio;
  - o Casting recebe um sino por dia cancelado com escalados;
  - cancelamento recusado não avisa ninguém;
  - fora da produção, zero e-mail real.
- **SC-010**: Isolamento das contas:
  - a multa ao elenco não altera retido, comissão nem BV;
  - mudar a taxa padrão nas Configurações não muda a comissão de nenhum cancelado.
- **SC-011**: O passado fica quieto. Nenhuma linha de comissão nasce, muda ou é cancelada fora dos eventos do
  verify, inclusive os estornos 151 e 211.
- **SC-012**: O retido conta como venda do vendedor congelado e da cliente no mês do cancelamento (+400 no
  Dashboard Comercial, em `/admin/desempenho` e na ficha da cliente), e nada no mês do evento.
- **SC-013**: O histórico registra o cancelamento na hora real (±5 min).
- **SC-014**: O deploy não pede ao dono nenhum script nem variável de ambiente nova. Os 59 cenários, com as
  variantes, e os verifies antigos refeitos ficam verdes.

## Fora de escopo

**Vai para a 1c**:
- o card "Cancelamentos do período" na DRE e no Dashboard (aqui só o payload);
- os filtros, o total e o redesenho da página de Cancelamentos (aqui ela só passa a mostrar o resumo, todas as
  devoluções e o estado `no_banco`, FR-025);
- o gate do FINANCEIRO e o item de menu dessa página;
- o "Mostrar cancelados", que não existe mais (1c-Q6);
- a trava geral do resto da tela do cancelado;
- o dia cancelado sair do painel "Grupo comercial";
- `blocked_reason` e selo nos seletores (grupo, ensaio, tag NFC, Gastos Extras);
- o rótulo `event_cancelled?` nas listas.

**Vai para a 1e**:
- a taxa pela data de venda (tabela de histórico da taxa padrão);
- o acerto da comissão paga de venda viva que muda depois do repasse (1b-Q12 = B);
- o recorte da tela de Comissões pelo beneficiário da linha;
- a linha de saldo;
- a trava de linha paga no modelo.

**Vai para a 2a**: o pedido de cancelamento, o bloco "o que foi pedido" e o fecho do pedido.

**Vai para a 2b**:
- o ensaio compartilhado e `ensaios_so_deste`;
- a linha da comissão do vendedor EducaManto na reconciliação;
- `educamanto_comissao_vendedor` na constante da passagem.

**Vai para a 3b e a 6a**: só os pontos de extensão daqui.

**Passado**: estornos 151 e 211; pago a menos e pago a mais; scripts de lista; acerto à mão.

**Portal e comunicação**: nenhuma tela nova no portal; o modelo do e-mail não muda; o WhatsApp é manual, pelo
Casting.

**Fora de vez** (mantido do rascunho, L2790-2796):
- regra nova de nota fiscal do cancelado (as notas seguem pelas rotas de hoje);
- marketing contar cancelado;
- card de devoluções na Home;
- painel antigo de "Estornos pendentes" e `set_commission_status`, fora a guarda de uma linha que recusa mexer em
  linha de evento cancelado (FR-047);
- parcelas nunca marcadas como recebidas;
- réguas de `/admin/desempenho` além do cancelado;
- a skill `financeiro`;
- a tela Jinja de Comissões (dívida).

**Também fora**:
- recuperar do parceiro o BV pago cheio antes do cancelamento (seria regra nova);
- desfazer cancelamento;
- informar a data do cancelamento.

**O que não fazer** (L1773-1822):
- **No modelo de dados**:
  - congelar o BV no próprio acréscimo;
  - pôr colunas de dinheiro em `calendar_events`, ou guardar dinheiro em JSON;
  - gravar o BV proporcional como número.
- **No grupo**:
  - desagrupar dia cancelado;
  - mover comprovante, comissão ou BV entre dias, fora da passagem da venda inteira;
  - apagar e recriar linha;
  - mudar valor, data, estado ou beneficiário de linha de comissão.
- **Avisos**:
  - mandar e-mail fora do envio em segundo plano ou antes do commit;
  - criar sino fora da transação;
  - mandar WhatsApp pelo sistema;
  - mandar e-mail de remoção no cancelado.
- **Multa**: tratar a multa como cachê de vaga.
- **Comissão**:
  - estender o resgate de órfãos para valor positivo;
  - herdar a data da venda no ajuste;
  - reescrever linha paga ou no banco;
  - recongelar com a taxa padrão de hoje;
  - guardar com que taxa cada parte foi paga;
  - deixar valor ou taxa editáveis sem recongelar.
- **BV**: esconder BV pago.
- **Jinja**: mover `_compute_drg`, extrair views ou "limpar" o template (`docs/PARADA_REMOCAO_JINJA.md`).
- **Scripts**: criar script em `scripts/oneoff/`.
- **Tela**:
  - pôr a prévia na chave do impacto;
  - calcular dinheiro no frontend;
  - cancelar sem modo;
  - decidir travas por papel no React.
- **Permissões**:
  - travar comprovante de cancelado para o Superadmin;
  - mudar quem exclui;
  - espalhar a regra de quem edita por endpoint;
  - reabrir Gastos Extras para ligar gasto ao cancelado.
- **Acréscimos e multa**:
  - editar acréscimo do cancelado apagando e recriando;
  - tirar a lista da multa da escala de hoje.

## Docs a atualizar

- **`docs/01`** (contratos; L1663-1674, L1734-1737):
  - §4.3: o `PATCH …/devolucao` e o `POST …/multas`; a linha de `_can_delete()` ganha o `PATCH …/devolucao`; uma
    linha para cada porta alterada do RBAC, com o papel e o 409, inclusive `PATCH /api/events/<id>`,
    `DELETE …/grupo/satelites/<sat>` e `POST /api/financeiro/pagamentos/set-status`; a tabela dos códigos 409.
  - Contratos dos payloads de evento, impacto, comissões, pagamentos, dashboard, pipeline, desempenho, clientes e
    gastos.
  - `PUT …/acrescimos` com `id?` no cancelado.
  - Catálogo de notificações: `evento.cancelado` e `evento.cancelado_escala`.
  - A categoria "Multa de cancelamento".
  - Tabela de modelos: as três tabelas novas.
  - Correção no lugar: `:770-771` (o cancelar do marcado deixa de dar 409).
  - O gate de `/events/cancelamentos` com o FINANCEIRO fica no `docs/01` da 1c.
- **`docs/02`** (telas; L1665-1671, L1731-1733):
  - O diálogo de cancelamento: todos os dias, só este dia com a passagem, cachê pago, multa, ensaio e avisos.
  - A tela do cancelado com "Alterar devolução" e os dados de venda.
  - Gastos Extras travado; Comissões com "No banco"; a Planilha; a DRE com a linha do retido; o marcado com duas
    saídas.
  - Correções no lugar: `:464-465` (o banner) e `:1458-1459` (o "estornos aparecem em qualquer mês" passa a valer
    só para o órfão).
  - O `:1749` e o painel do grupo sem o dia cancelado são do `docs/02` da 1c.
- **`docs/03`**: entrada no topo e linha no índice. A 224g passa a fechada (L1674).
- **`docs/04`** (invariantes; L1674-1704, L1726-1747):
  - **Comissão**:
    - comissão do cancelado = cheia × retido ÷ venda, com teto na cheia;
    - comissão paga ou no banco nunca é reescrita, e a diferença vai ao primeiro repasse aberto;
    - a taxa congelada não acompanha a padrão.
  - **DRE**: o retido entra na DRE e conta como venda no mês do cancelamento; a devolução nunca é gasto na DRE.
  - **BV**: BV pago nunca é reescrito nem escondido; o BV proporcional fica no mês do evento.
  - **Congelamento**: nada se recalcula da venda viva.
  - **Grupo**:
    - cancelar o principal cancela o grupo, e o dia cancelado sozinho fica no grupo;
    - a passagem muda o dono sem mudar valor nem data;
    - a comissão EducaManto vai à data do novo 1º dia;
    - a comissão segue a data de venda, e a DRE segue o evento que guarda a venda.
  - **Ensaio, cachê e multa**:
    - cachê pago impede o cancelamento;
    - o ensaio segue o show;
    - a multa é Gasto Extra do mês, vale para quem estava no ato e não mexe em comissão nem BV.
  - **Permissão**: só o Superadmin edita os dados de venda, por uma regra única.
  - **Avisos**: e-mail no ato, nenhum e-mail de remoção depois, e os dois sinos.
  - **Correções no lugar**: `:301-303`, `:336`, `:142`, `:299` (`_group_cost` só com satélites vivos), `:246` e o
    trecho de agrupamento (o principal pode mudar).
- **`docs/05`** (dívidas; L1705-1721, L1738, L1903-1906):
  - **Telas e Jinja**:
    - painel Jinja de estornos (o `set_commission_status` ganha só a guarda que recusa linha de evento cancelado);
    - tela Jinja de Comissões sem os filtros novos;
    - tela Jinja do evento cancelado com comissão 0 (P-28, escolha do `/speckit-plan`);
    - rótulo de impostos da DRE antiga;
    - histórico do desfazer da 267c gravado 3 h antes;
    - "pago" em lote (API e Jinja) sobre devolução recém-alterada, sem conferência de valor.
  - **Regras**:
    - estorno órfão de exclusão aparecendo em dois meses nos dias 1 a 5;
    - tipo de evento nulo fora da DRE;
    - parcelas nunca marcadas como recebidas;
    - réguas de `/admin/desempenho`;
    - desconto sem repasse futuro (1e-Q8 = B);
    - comissão paga × venda alterada (dono: 1e);
    - D20;
    - guarda de pago abaixo do devolvido em dia **vivo** do grupo;
    - resíduo da trava: um "pago" da Planilha que começou antes da linha nova da reconciliação não a vê (ela fica
      aberta e aparece na Planilha);
    - recibo órfão no 400 e no 409 do `POST /api/gastos`;
    - ensaio que fica no Google (falha ou trava) e volta no próximo sync como ensaio órfão.
  - **Ferramentas**:
    - skill `financeiro` sem a regra do retido;
    - verifies não versionados de `scripts/db/`.
  - **Riscar o que quita**:
    - ciclo do estorno da venda;
    - ramo `no_banco`;
    - cachê de satélite cancelado;
    - "cancelar" na dívida 69, porque a trava do Google no cancelamento entra; o "Cancelar ensaio" e a troca de
      tipo seguem na dívida.
- **`docs/00`** (decisão do `/speckit-plan`; o plano do backlog dizia que não mudava, L1748): §4 ganha a regra única
  do cancelado (só o Superadmin real corrige os dados de venda; quem passa no gate de hoje recebe 409 `cancelado`),
  e §6, a ordem de travas evento → dependentes, com o "relê depois de travar".
- **Fora dos `docs/`**:
  - A trava do Google no cancelamento entra (FR-015, P-26): `DEVELOPMENT.md:110-115` e `:151`, `CLAUDE.md` §4 e a
    docstring de `app/config.py:145-162`.
  - A docstring de `group_ops.py:1-32`: o principal pode mudar (L1738-1747).

## Premissas

Cada premissa diz de onde vem:
- **(premissa do plano)**: veio do plano, não do dono; vale porque o dono não se opôs (L2624-2625).
- **(decisão do dono: …)**: veio de uma resposta dele.
- **(leitura desta spec)**: é uma das leituras da Session 2026-10-15.

**Modelo e congelamento**

- P-1 Congelamento em três tabelas próprias, sem coluna em tabela existente e sem backfill. "Alterar devolução"
  não regrava o modo (premissa do plano, L2627-2630, L3419).
- P-2 Pago e devolvido são lidos ao vivo. Venda, cheia, beneficiário, vendedor, nota, imposto e BV cheio ficam
  congelados, e o BV a pagar é a proporção do retido (premissa do plano sobre a decisão do dono 1b-Q2,
  L2631-2632).
- P-3 A comissão cheia tem uma definição só. Cortesia, evento sem vendedor e venda virtual dão zero (premissa do
  plano, L2644-2646).
- P-4 Cancelado sem registro é `legado`; hoje não existe nenhum (premissa do plano, L2647-2648).

**Venda de vários dias**

- P-5 O dinheiro do grupo mora no principal. O pago do grupo é a soma de todos os dias; o custo ignora o dia
  cancelado, e o recebido o mantém (premissa do plano sobre a decisão do dono 1b-Q1 = C, L2649-2660).
- P-6 A passagem da venda segue as regras abaixo (premissa do plano sobre as decisões do dono Q5 = B, Q13, Q15 =
  A e Q18 = A, L2661-2680):
  - recebe o dia vivo mais cedo;
  - a comissão paga só troca de vínculo;
  - a comissão própria do novo principal fica fora da conta;
  - a EducaManto a pagar vai à data nova;
  - o ensaio fica com o dia e cai.
- P-7 O corte não vira desconto: o cheio cai na mesma proporção (premissa do plano, premissa 36 da 3b,
  L2681-2684).
- P-8 Quem cancela informa a venda nova (premissa do plano sobre a decisão do dono 3b-Q4 = A, L2685-2687,
  L3303-3306). A 3b-Q4 = A ("A", `3b-calculadora-desconto-e-dias.md:1817`) só decidiu que a proposta não tem
  preço por dia; o "é a comercial" de lá vale para quem pede (2a), não para quem decide.
- P-9 O corte de um dia não é cancelamento da venda. O principal segue vivo, e o retido do dia cai no **mês do
  evento** (premissa do plano, L2692-2707). O plano pediu objeção antes do specify, e nenhuma rodada respondeu.

**Comissão**

- P-10 Ciclo do ajuste (premissa do plano, L2711-2721):
  - a data da venda e a de liberação ficam no primeiro repasse aberto;
  - linha atualizada no lugar mantém a data;
  - "linha que abre ciclo" é um predicado único;
  - o dia 5 é constante única.
- P-11 O estorno órfão continua pelo resgate do mês corrente. O estorno da exclusão fica com o ciclo corrigido e
  com o `no_banco` contando como pago (premissa do plano, L2722-2726).
- P-12 O ajuste de linha liquidada vai a quem a recebeu, e a linha nova vai ao beneficiário congelado (premissa do
  plano, L2727-2729).
- P-13 O desconto de vendedor sem repasse futuro fica a pagar, à vista, sem baixa (premissa do plano, L2745-2751,
  fechada pela decisão do dono 1e-Q8 = B, `1e-comissao-acompanha-a-venda.md:1428`).
- P-14 "No banco" passa a aparecer em Comissões. Nenhum mês muda hoje (zero linhas); comunicar ao dono (premissa do
  plano, L2752-2753).

**BV, DRE, devolução e comprovante**

- P-15 BV na Planilha por regime: BV pago nunca some e proporcional zero some (premissa do plano sobre a decisão do
  dono de 30/09 e a 1b-Q2, L2754-2761).
- P-16 A DRE não tem fechamento de mês: corrigir devolução ou comprovante reescreve o mês do cancelamento. O filtro
  seguro contra tipo nulo vale só nos cancelados (premissa do plano, L2762-2767).
- P-17 Reconhecimento da devolução (premissa do plano, L2708-2710):
  - devolução = categoria + vínculo + aprovação;
  - "no banco" conta como paga;
  - o "desfazer pago" da Planilha continua.
- P-18 Comprovante de cancelado: 409 para quem não é Superadmin; o Superadmin recalcula na mesma transação (premissa
  do plano sobre as decisões do dono D36, 1b-Q2 e 1c-Q8, L2768-2772).
- P-19 Devolução pendente bloqueia o cancelamento, e só o "Alterar devolução" escreve na devolução do cancelado
  (premissa do plano, L2773-2774).

**Técnicas**

- P-20 Bloqueio que relê o banco, em ordem de id no grupo; estouro do registro único vira 409 (premissa do plano,
  L2775-2776).
- P-21 A prévia é consulta separada; `devolucao_sugerida` fica um ciclo; a trava de capacidade cobre o deploy
  cruzado (premissa do plano, L2777-2779).
- P-22 O histórico do cancelamento passa a gravar em UTC, e a data de Comissões é corrigida aqui (premissa do
  plano, L2780-2783).
- P-23 Entrega sozinha, sem a 1c, com backend e frontend no mesmo push (premissa do plano, L2788-2789).

**Completude**

- P-24 Cancelado sem dinheiro nenhum fica fora da contagem e da DRE; confirmada pelo `/speckit-plan` (premissa do
  plano, L2797-2805; leitura desta spec 4).
- P-25 Comprovante sem valor conta zero, e o impacto diz quantos são (`comprovantes_sem_valor?`); confirmada pelo
  `/speckit-plan` (premissa do plano, L2806-2808, L1969).
- P-26 A remoção do Google do não marcado vai depois do commit e com a trava, lida a cada chamada (chave ausente =
  travado); confirmada pelo `/speckit-plan` (premissa do plano, L856-865).
- P-27 Os três handlers Jinja de comprovante recusam o cancelado com aviso, em vez de virar dívida; confirmada pelo
  `/speckit-plan`, que estende a recusa à aba Comercial, à venda e aos três de reembolso, para todos os papéis
  (FR-047) (premissa do plano, L1215-1221).
- P-28 Na tela Jinja do evento cancelado, a comissão fica em 0, com dívida no `docs/05`; o `/speckit-plan` escolheu
  essa saída, e não ler o resumo pela metade (premissa do plano, L1079-1089).
- P-29 A marca da comissão própria do novo principal é um prefixo de nota por constante
  (`NOTA_COMISSAO_PROPRIA_DO_DIA`), que a reconciliação e a sincronização ignoram; escolha do `/speckit-plan`
  (premissa do plano, L1038-1045).

**Ensaio, elenco e multa**

- P-30 Cancelar ensaio é apagá-lo; evento do tipo Ensaio recebe 409 (premissa do plano, L2809-2813).
- P-31 "Quem marcou o ensaio" é a equipe de Ensaio, avisada só quando havia ensaio (premissa do plano sobre a
  decisão do dono 1b-Q11 = B, L2814-2816).
- P-32 Artista avisado (premissa do plano sobre as decisões do dono Q11 = B, 1c-Q10 e 1c-Q12 = A, L2817-2823):
  - escalado com talento;
  - sem a vaga de presença e sem quem recusou;
  - uma vez por pessoa;
  - no corte, só o elenco do dia.
- P-33 O detalhe do sino ao Casting é desenho do plano: um por dia, urgente a 7 dias, sem o Superadmin, com link
  (premissa do plano, L2824-2829, L5019-5020).
- P-34 Multa ao elenco: categoria, data do cancelamento no ato, **data do lançamento na multa tardia** e PIX vazio
  permitido (premissa do plano sobre as decisões do dono Q8–Q10 = A e 1c-Q7, L2830-2844, L4767-4769).
- P-35 "Cachê pago" é uma função só, pago ou no banco, que a 2a importa (premissa do plano sobre a decisão do dono
  1b-Q4 = B, L2845-2846).
- P-36 BV não pago sem recebedor ou PIX recusa o cancelamento (premissa do plano aplicando a regra da 3a,
  L2847-2857).

**Regras derivadas** (o plano pediu "se discordar, diga antes do specify"; L2859-2925)

- P-37 Dinheiro pago depois do cancelamento entra como comprovante, comissionado pelo mesmo %, e conta no mês do
  cancelamento (premissa do plano, L2863-2870). O plano pediu objeção explícita sobre comissionar a multa paga
  depois, e nenhuma rodada respondeu.
- P-38 O reembolso cobrado da cliente fica fora do retido e da devolução (premissa do plano sobre a decisão do dono
  1c-Q11 = C, L2871-2875).
- P-39 Devolução feita antes do cancelamento conta como devolvido (premissa do plano, L2876-2881).
- P-40 Cancelar não tem volta: o cancelado não se exclui e se recria à mão (premissa do plano, confirmada na
  revisão de 02/10, L2882-2891, L4056-4058).
- P-41 O mês do cancelamento é o do registro no sistema (premissa do plano, L2892-2895).
- P-42 O cachê do cancelado sai da Planilha e da DRE (premissa do plano: comportamento de hoje,
  `financeiro/routes.py:701`; L2901-2905, L4064-4065). A 1b-Q4 = B só impede cancelar com cachê pago.
- P-43 Na ficha da cliente, o cancelado sai de "Com evento" e de "Recorrentes", e o total vendido conta o retido
  (premissa do plano sobre a decisão do dono D33, L2906-2908).
- P-44 Só o Superadmin mexe nos dados de venda do cancelado; o Casting continua tirando escalados (premissa do
  plano sobre as decisões do dono 1c-Q8 = A e 1c-Q10, L2909-2918).
- P-45 A tela Jinja de Comissões fica fora (premissa do plano, L2919-2925).

**Divisão com a 1c, conta do BV e leituras desta spec**

- P-46 O gate do FINANCEIRO e o menu da página de Cancelamentos ficam na 1c (premissa do plano, L3404-3408;
  leitura desta spec 1).
- P-47 A regra de núcleo que recusa agrupar cancelado sobe aqui (premissa do plano, L3409-3412).
- P-48 Há uma conta só de proporção do BV, a da 305, reusada com teto no BV cheio (premissa do plano, L3271-3272;
  `quote_ops.bv_que_acompanha`).
- P-49 Leituras 2, 3, 5, 6, 8, 9, 10 e 11 da Session 2026-10-15 (leitura desta spec).
- P-50 A troca de vendedor no EducaManto muda só o recorte comercial; a comissão cheia e o beneficiário (o
  responsável) ficam (premissa do plano, L1178-1179, conferida "fiel" em L5025-5026; era a leitura 7).
- P-51 A comissão própria de um dia do grupo fica fora da conta também no "Cancelar todos os dias" e no corte, como
  na passagem (P-29). No espelho é uma linha só: a do 287, satélite do 288, R$ 137,50 paga. Fica paga e fora da
  reconciliação do principal. É derivada da 1b-Q3 = A ("a comissão própria não vira desconto"), que a R16 já cita
  como decisão que amarra a passagem; o checklist de 16/10 só a escreveu para o "todos" e o corte.

**Dependências** (conferidas na `main` em `d855d1a` e reconferidas em `6356b80`, com a 307)

- **303, em produção**:
  - *Reusa*: `situacao`, `desmarcar` (com o motivo novo "cancelado"), o banner, o dublê do Google, a guarda de
    ambiente e a contagem.
  - *Altera*: a recusa do marcado sai do cancelar e fica só na exclusão; o botão libera; o banner e as mensagens
    mudam; o cenário 12 do `verify_303` é reescrito.
  - *Encadeia*: a migration vem depois de `a7c3e91f4d28`, sem variável nova (L2931-2941, L3678-3679).
- **215b, em produção desde 14/10**:
  - no cancelado, a regra única roda antes da checagem de taxa e vendedor da 215b;
  - o Financeiro, que já fica fora do `/comercial` (gate de criar evento, anterior à 215b;
    `specs/215b-hotfix-taxa-e-vendedor/spec.md:38`), fica no 403;
  - `flags.can_edit_venda_cancelado` convive com `pode_mudar_taxa`;
  - a taxa padrão não muda nas Configurações até a 1e (L3084-3107, L3645-3649).
- **267c, em produção desde 14/10**:
  - `liquidar_periodo` já trava as linhas com `with_for_update`, o que fecha de vez a corrida do cenário 30 do
    lado da Planilha (L3181-3182); o bloqueio que relê do núcleo continua obrigatório (FR-013);
  - `commission_lines`, o tipo, o ciclo e o predicado entram sobre o item da Planilha já partido em aberto × pago;
  - o 42c garante que a comissão própria do satélite (287 × 288) não vira desconto nem pagamento em dobro
    (L3179-3195);
  - *ficam iguais*: o lote "pago" age só nas linhas abertas do item; o desfazer é só do Superadmin, com motivo.
    O item aberto de soma zero com linha de valor, que passa a aparecer (FR-031), entra no lote como qualquer
    item: "pago" liquida as linhas abertas dele, e nada sai do caixa, porque a soma é zero.
- **305, em produção desde 15/10**:
  - a conta única de proporção do BV;
  - o acompanhamento automático do BV (a B10 da 305: a venda que muda leva o BV junto, uma vez por gravação)
    segue igual no vivo, nos três escritores (`update_event_comercial`, a edição completa e o Jinja comercial);
    só ganha a releitura de "cancelado" depois da trava de cada um;
  - o acompanhamento automático do BV não roda em cancelado e não pode escalar o corte duas vezes;
  - o `PUT …/acrescimos` já casa por `id`;
  - marcar o BV pago na Planilha confere o valor esperado, que passa a ser o proporcional;
  - o gêmeo Jinja da aba Comercial passa a recusar cancelado;
  - a contagem "BV não pago sem recebedor ou PIX" é refeita;
  - o risco "dois BVs ao recriar do mesmo orçamento" fecha aqui (`specs/305-…/research.md` R3, R7, R9, R11;
    L3263-3290).
- **307, em produção desde 16/10**: a faixa de 24 e 25/12 na tabela de preços mexeu em `orcamento_evento_ops.py`,
  `orcamento/quote_ops.py` e `calendar/routes.py` só deslocando linhas que a 306 cita; a 306 não muda nada dela, e
  o `verify_307` roda de novo (§Verifies antigos).
- **1c, depois (não pode subir antes; L2952)**:
  - lê `paineis.cancelamentos`, `resumo` e os cancelados do período;
  - esta spec fixa os nomes que a 1c reusa: `pode_editar_venda_do_cancelado`, `can_edit_venda_cancelado`,
    `evento.cancelado_escala`, `group_ops.dias_vivos` e os códigos 409 (`CODIGO_*`), pela tabela única de nomes do
    `data-model.md` §6;
  - a condição na remoção pelo Casting sobe aqui;
  - arquivos em comum (`financeiro/routes.py`, `financeiro_read.py`, `agenda_write.py`,
    `EventosCancelamentosPage.tsx`, `lib/eventOps.ts`, `EventHeader.tsx`, `group_ops.py`), uma branch de cada vez
    (L2945-3056, L3381-3415).
- **1e, depois**:
  - reaproveita o primeiro repasse aberto, a linha de ajuste com linha original, a reconciliação idempotente, o
    predicado/tipo/ciclo/linhas e a guarda do cancelado na sincronização;
  - roda de novo os cenários 9, 38 e 42b;
  - a trava de linha paga dela tem de deixar passar a exclusão e a passagem (L3057-3179).
- **2a, depois**:
  - importa a régua do cachê pago, a recusa `ensaio` e o ponto de extensão (`cancel_ops.ao_cancelar`, que roda em
    todo cancelamento, FR-062);
  - o bloco "o que foi pedido" do diálogo é dela; esta entrega não deixa nada pronto dele (FR-023);
  - o corpo do cancelar não muda;
  - o aviso ao elenco sai daqui (L3201-3248).
- **2b, noite 7**:
  - `ensaios_so_deste`;
  - a linha do vendedor EducaManto na reconciliação por beneficiário;
  - `educamanto_comissao_vendedor` na lista da passagem (`group_ops.CAMPOS_DA_PASSAGEM`/`TABELAS_DA_PASSAGEM`);
  - roda de novo os cenários 11, 16c, 42c e 44 (L3320-3371, L5250-5302).
- **3b, noites 4 e 6**: respeita o cancelamento de vários dias; o vínculo do orçamento passa; a coluna do dia não
  passa; o cenário 27 de lá foi reescrito (L3291-3319).
- **6a**: as três colunas de canal entram na lista da passagem; o retrato do 42 roda de novo; a migration dela
  encadeia depois desta (L3255-3259, L3377-3379).
- **6b**: "Multa de cancelamento" (`SpecialExpense.CATEGORY_MULTA_CANCELAMENTO`) entra na lista de categorias. A 6b-Q1 = A tira a 6b da DRE (L3249-3254).
- **Outros**: 4a (o formulário passa com a venda) e 4b (a migration encadeia depois). A 5a-Q8 não muda nada aqui.

**Riscos aceitos** (do plano)

1. Nos dias 1 a 5, um PIX de repasse feito sem marcar a Planilha deixa um desconto novo dado como liquidado sem
   ter sido descontado (L2716-2719).
2. Desconto de vendedor sem repasse futuro fica a pagar para sempre, à vista (L2745-2751).
3. A DRE não tem fechamento de mês (L2766-2767).
4. A assimetria do tipo nulo no evento vivo fica como dívida (L2764-2765).
5. A tela Jinja de Comissões fica fora dos filtros (L2919-2925).
6. Na janela do deploy, o bundle antigo da tela de Comissões não conhece a linha "no banco", que fica sem
   tratamento; hoje são zero linhas (L3672-3674).
7. Na janela do deploy, a tela recarrega no 409 "já cancelado" (L3670-3677).
8. **Rollback assimétrico** depois do primeiro cancelamento real. Defeito se corrige para a frente, com `306b`
   (L3609-3621). O que não volta:
   - o código antigo zera a comissão do retido;
   - o código antigo toma o ajuste do corte de dia (a linha a pagar com `original_id`, ligada ao principal vivo)
     pela comissão do evento e a regrava com a cheia;
   - o código antigo volta a listar pelo cheio o BV não pago do cancelado, e a Planilha da 305 deixa marcá-lo pago
     por esse valor;
   - o código antigo volta a deixar excluir o cancelado vazio, inclusive pelo sync, e a exclusão leva o
     congelamento junto (CASCADE de `event_cancellations.event_id`);
   - o `downgrade` apaga o congelamento, e sem ele nada se refaz: por isso fica proibido com linha em
     `event_cancellations`;
   - ensaios apagados e e-mails enviados;
   - a venda que passou de dia.
9. O descartável do teste pós-deploy fica para sempre na página de Cancelamentos (L3663-3669).
10. A taxa padrão fica congelada nas Configurações até a 1e subir (L3104-3117).
11. Até a 1e, a comissão paga de venda viva não acompanha a venda, nem depois de um corte (L3075-3077).
12. O mês do cancelamento é o do registro, mesmo que a cliente tenha cancelado antes (L2892-2895).
13. O retido do dia cortado cai no mês do evento (L2700-2707).
14. Antes da 1c, a tela do cancelado continua editável, inclusive a escala (L3055-3056).
15. Presente 3D e tag NFC ficam com o antigo 1º dia (L3009-3014).
16. A cobrança da Home muda de regra, com zero casos hoje (L2697-2701).
17. Até a noite 7, todo ensaio vivo do dia cancelado cai (L5337-5339).
18. BV pago cheio antes do cancelamento fica como foi pago (L2754-2757).
19. A página de Cancelamentos fica sem leitor Financeiro até a 1c; não há usuário ativo com o papel (L3404-3407).

**Deploy** (L3623-3679)

- **Quando**: noite 2, sozinha, à noite, depois de 215b e 267c (que já estão na base). Backend e frontend vão no
  mesmo push. Antes do push, reproduzir o build num venv 3.11, porque o `startCommand` roda `flask db upgrade`.
- **Antes: contagem do dia em produção**, só leitura, por SSH. Ela conta:
  - cancelados;
  - cancelados sem venda nem comprovante (L3636);
  - comissões a pagar negativas com evento, "no banco" por mês e ciclos de soma zero;
  - devoluções com tipo nulo e devoluções pendentes ligadas;
  - BV em satélite;
  - marcados pela 303;
  - comprovantes sem valor e pago maior que a venda;
  - grupos com dia futuro, com principal fora do 1º dia ou cruzando o mês, e satélites com comissão própria;
  - eventos futuros com cachê pago;
  - usuários FINANCEIRO e ENSAIO ativos;
  - shows futuros com ensaio e os escalados deles;
  - escalados sem e-mail e talentos sem PIX;
  - BV não pago sem recebedor ou PIX.
- **O que o dono roda**: nada.
- **Depois: um evento descartável**:
  - título que diga que é teste, com contrato anexado e sem venda;
  - sem artista de verdade escalado;
  - sem ensaio ligado.

  Depois de cancelá-lo, abrir a DRE do mês nas duas telas, a Planilha do mês seguinte e Comissões. O `docs/03` só
  ganha "EM PRODUÇÃO" depois de uma sonda `/api/` devolver JSON.