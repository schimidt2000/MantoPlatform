# Feature 299 — Sem valor e cobranças: a Home cobra o grupo como uma venda só e mostra o evento que ainda não tem valor

**Branch**: `299-sem-valor-cobrancas` (da `main`) · **Created**: 2026-09-14 · **Status**: Rascunho ·
**Migration**: nenhuma prevista ("valor a definir" é o valor vazio — ver Premissas) ·
**Nível**: 1 (feature) — constituição, Princípio VI

**Input**: pedido do dono: "Pendências da Home: evento sem valor e cobranças. O grupo é uma venda
só. Em tudo que é comercial (sem valor e cobranças), um grupo de eventos conta como uma venda: o
valor é o do evento principal, e os comprovantes de TODOS os eventos do grupo se somam. Nova lista na
Home, 'Evento sem valor de venda'. Entram os eventos (ou grupos) a partir de 01/06/2026, passados e
futuros, não cancelados e fora de ensaio, com valor vazio, zero ou simbólico (R$ 0,01). Ficam de fora
a cortesia ou permuta marcada e o evento de grupo cujo principal tem valor. Em 10/09 seriam 9 (dos 28
sem valor, 19 eram de grupo com o principal valorado). 'Valor a definir' no cadastro do evento, no
lugar do valor obrigatório. O evento nasce na lista 'sem valor' e sai dela quando alguém põe o valor.
Ajustes nas cobranças, sem mudar a política: o saldo final continua vencendo 2 dias antes do evento;
se houver data combinada, vale a data, qualquer que seja a forma de pagamento; comprovante de
qualquer evento do grupo conta; diferença de centavos não é dívida; evento de valor simbólico sai das
cobranças e vai para 'sem valor'; cada linha mostra a data do evento e o nome da cliente; etiquetas
em português; todos continuam vendo todas. O total do topo da Home soma só tarefas de verdade. Visual
igual ao da 298: mesma escala de cor (vermelho, amarelo, cinza); cada linha diz quem, quando e uma
ação; poucas linhas e 'Mostrar todas'; conferido no computador e no celular. Casos reais para testar:
no grupo 344, a Home vê R$ 3.078 recebidos de R$ 5.508, mas o grupo recebeu R$ 6.156; há 4
comprovantes (R$ 9.955) anexados em eventos do grupo que não são o principal; nos grupos 184 e 288, o
grupo recebeu mais que o valor."

## O pedido, nas palavras do dono *(obrigatório)*

Contexto que o dono deu (conversa de 10/09/2026, plano aprovado; a feature A, a 298, está em produção
desde 14/09):

- **O fluxo.** A venda fecha no WhatsApp/Kommo, o evento vai para a agenda, e o valor e os
  comprovantes são lançados no evento. Evento lançado sem valor não aparece em lugar nenhum, e a
  cobrança da Home olha só o próprio evento, então erra nos grupos.
- **A política não muda.** Sinal de 50% no fechamento e o saldo até 2 dias antes do evento; havendo
  data combinada com a cliente, vale a data. Todos veem todas as cobranças.
- **O grupo.** Vários eventos da mesma venda (por exemplo, um show em dois dias). O valor de venda
  mora no principal; os outros eventos do grupo ficam sem valor de propósito. Os comprovantes podem
  estar em qualquer um deles.

Números da produção em 14/09/2026 (lidos só para consulta), desde 01/06:

- **Sem valor.** São 237 eventos não cancelados e fora de ensaio, e 29 deles estão sem valor (vazio,
  zero ou R$ 0,01). 19 são outros eventos de grupo cujo principal tem valor. Dos 10 que sobram, 4 não
  são venda: uma visita técnica, uma gravação de vozes e dois ensaios EducaManto com o título fora do
  padrão. Os 4 começam com o marcador laranja (🟧 ou 🟠) e não têm tipo nem cliente. Ficam **6
  vendas sem valor**: 2 já passaram, 1 é hoje e 3 ainda vão acontecer. 2 delas estão com R$ 0,01.
- **Cobranças.** A lista tem 15 linhas.
  - 2 são os eventos de R$ 0,01, que aparecem como "falta R$ 0,01".
  - 3 das 11 amarelas ("recebeu menos da metade") são clientes que pagaram o sinal com centavos a
    menos, até R$ 0,50 abaixo da metade.
  - Outras **25 vendas com saldo não aparecem**, porque a cliente já pagou metade e o evento está a
    mais de 2 dias. 7 delas são de eventos nos próximos 7 dias.
- **Grupos.** São 5 grupos com evento desde 01/06: 184, 288, 319, 344 e 364.
  - 4 comprovantes (R$ 9.955) estão em outros eventos do grupo, em 3 grupos: 184 (R$ 1.377), 288
    (R$ 5.500) e 344 (R$ 3.078).
  - No 344, a Home vê R$ 3.078 recebidos de R$ 5.508 e cobra R$ 2.430, mas o grupo recebeu
    R$ 6.156.
- **Recebido acima do valor**, somando o grupo: 21 vendas.
  - 5 são diferenças de centavos;
  - 10 ficam entre R$ 74 e R$ 276 acima;
  - 6 têm diferença grande: 85, 184, 288, 309, 319 e 344.

  É assunto da limpeza de dados, à parte (Fora de escopo), mas estes 6 são conferidos antes da
  publicação (ver "Antes da publicação").
- **Formas de pagamento.** 88 Pix dividido, 83 à vista, 13 cartão, 3 faturado, 2 parcelado com datas
  e 29 sem forma. A data combinada está preenchida em 4 vendas (2 faturado, 2 à vista).
- **Evento sem tipo.** Não serve para dizer "não é venda": o evento 395 não tem tipo e é uma venda de
  R$ 35.000, com cliente.

**Vocabulário desta feature** (vale para a spec e para os textos da tela):

- **Evento**: a festa na agenda.
- **Grupo**: eventos que são uma venda só. O **principal** guarda o valor de venda. Os **outros
  eventos do grupo** ficam sem valor de propósito.
- **Valor de venda**: o valor final cobrado da cliente ("Valor de venda final" no evento).
- **Sem valor**: valor vazio, zero ou simbólico.
- **A definir**: como aparece o evento com valor vazio ou zero (sem cortesia).
- **Valor simbólico**: acima de zero e abaixo de R$ 1,00. Hoje só existe R$ 0,01, usado para
  "segurar a data".
- **Valor a definir** (a marca): o evento salvo sem valor de propósito, porque o preço ainda não
  fechou.
- **Recebido**: a soma dos comprovantes de todos os eventos do grupo.
- **Saldo**: o valor de venda menos o recebido. É o que a cobrança pede, mesmo com cronograma de
  parcelas.
- **Sinal**: a metade do valor, paga no fechamento. Só vale quando não há data combinada nem
  cronograma de parcelas.
- **Data combinada**: a data de pagamento acertada com a cliente.
- **Vencimento do saldo**: a data combinada; senão, a primeira parcela ainda não coberta; senão, 2
  dias antes do evento. Nunca antes da data da venda.
- **Compromisso interno**: evento da agenda que não é venda (ensaio, visita técnica, gravação),
  marcado com o laranja 🟧 ou 🟠 no começo do título.
- **Venda da Loja Virtual**: venda feita e paga na loja de interações virtuais (tipo "Virtual"). Ela
  já chega paga e nunca tem comprovante no evento.
- **Data de início**: a data a partir da qual o sistema cobra (`release_date` das configurações;
  hoje 01/06/2026, e 01/06/2026 quando estiver vazia).
- **Cobrança**: uma linha da Home para uma venda com saldo.
- **Para agir**: linha vermelha ou amarela. A cinza é só informação.

## Clarifications

### Session 2026-09-14

Respostas do dono às perguntas do `/speckit-specify`:

- Q: Além das duas listas da Home, onde mais vale o recebido do grupo? → A: também na página do
  evento: recebido, "Quitado", saldo e mensagem de cobrança. O "a receber" do Financeiro e os
  relatórios financeiros ficam como estão.
- Q: Como o sistema reconhece o evento que não é venda? → A: pelo marcador laranja no começo do
  título (🟧 ou 🟠), como os ensaios já usam.
- Q: O que conta no total do topo da Home? → A: só as linhas vermelhas e amarelas de todas as listas.
  As cinza são informação e não entram.

Respostas do dono no `/speckit-clarify`:

- Q: A regra "o total soma só as linhas vermelhas e amarelas" vale também para os painéis de operação
  da Home, ou só para as listas comerciais? → A: só para as listas comerciais (Cobranças, Sem valor
  e Formulários). Os painéis de operação (Escalar elenco, Figurino, Oficina, Ensaio, Contas do mês)
  continuam contando todas as linhas, como hoje.
- Q: Quando uma cobrança deve aparecer em vermelho, amarelo ou cinza? → A: vermelho quando o saldo
  venceu ou vence em até 2 dias (o prazo da política); amarelo de 3 a 30 dias, ou sinal pendente;
  cinza acima de 30 dias.
- Q: Na lista "Evento sem valor de venda", quando uma linha deve aparecer em vermelho, amarelo ou
  cinza? → A: a régua da 298, mais larga que a das cobranças: vermelho quando o evento já aconteceu
  ou acontece em até 7 dias; amarelo de 8 a 30 dias; cinza acima de 30 dias. Motivo do dono: "se está
  sem valor de venda, precisa ter o quanto antes".
- Q: Depois que a venda é lançada, quanto tempo a comercial tem para anexar o comprovante do sinal
  antes de a linha virar "Sinal pendente"? → A: nenhum. Vale na hora, como hoje: sem comprovante de
  pelo menos metade do valor, a linha já diz "Sinal pendente".

Respostas do dono no `/speckit-plan`, sobre as decisões que a pesquisa de desenho levantou:

- Q: As listas "Cobranças" e "Evento sem valor de venda" ficam em dois painéis ou num painel
  Comercial só? → A: dois painéis, "Cobranças" e "Sem valor", cada um com o nome do seu card no topo.
- Q: Com data combinada e cronograma de parcelas, qual data vale como vencimento? → A: a data
  combinada. As parcelas só contam quando não há data combinada.
- Q: Venda com data combinada (faturada para 30 dias, por exemplo) aparece como "Sinal pendente"
  sem comprovante? → A: não. A data combinada substitui a regra da metade.
- Q: Evento lançado com "valor a definir" que ganha valor semanas depois: em que mês entra a
  comissão? → A: no mês em que o valor entra. A data da venda continua a do cadastro nos
  relatórios; só o ciclo da comissão anda, do jeito que a EducaManto já adia comissão.

Respostas do dono no `/speckit-checklist` (`checklists/revisao.md`):

- Q: Uma cliente não pagou nem o sinal: onde a venda aparece em Cobranças, e com que cor? → A: sobe
  com as urgentes. A lista fica em ordem de cor (vermelho, amarelo, cinza) e, dentro da cor, pelo
  vencimento. A venda sem sinal é amarela e aparece antes de todas as cinza. Se o prazo já venceu ou
  vence em até 2 dias, fica vermelha, com o selo do prazo e a nota "sem sinal".
- Q: Os cards "Cobranças" e "Sem valor" mostram quantas linhas? → A: só as para agir (vermelhas e
  amarelas), e a soma dos cards bate com o total do topo. O painel aberto mostra todas.
- Q: Valor abaixo de R$ 1,00 sem a marca "Valor a definir": o cadastro aceita? → A: não. O campo
  aponta e pede a marca. O evento que já está com R$ 0,01 continua salvando outras mudanças sem
  ninguém mexer no valor.
- Q: Conferir os casos de dado que podem enganar as listas antes de publicar? → A: sim. Antes do
  deploy, a lista do grupo 344 e das vendas com comprovante sem valor é levantada (só leitura) e
  conferida pelo dono.

## Cenários e Verificação *(obrigatório)*

### História 1 — O grupo é cobrado como uma venda só (Prioridade: P1)

A comercial abre a Home e vê, em "Cobranças", uma linha por venda. No grupo, a linha é a do
principal, e o recebido soma os comprovantes de todos os eventos do grupo. O grupo 344, que hoje
aparece cobrando R$ 2.430 que foram pagos num outro evento do grupo, sai da lista (os dois
comprovantes dele são conferidos antes da publicação). A página do evento mostra o mesmo número: o
principal do 344 aparece quitado, e a mensagem de cobrança não pede o que já foi pago.

**Por que esta prioridade**: é o erro que faz a comercial cobrar dinheiro que a cliente já pagou.

**Verificação**: cenários 7, 8 e 15 do `verify_299.py`.

**Cenários de aceite**:

1. **Dado** um grupo com valor de R$ 5.508 no principal, um comprovante de R$ 3.078 no principal e
   outro de R$ 3.078 no outro evento do grupo, **Quando** a Home abre, **Então** o grupo não aparece
   em Cobranças, porque já recebeu tudo.
2. **Dado** um grupo de R$ 10.000 com R$ 2.000 no principal e R$ 3.000 no outro evento, **Quando** a
   Home abre, **Então** aparece uma linha só, com a marca "grupo de 2 eventos" e "Recebido
   R$ 5.000,00 de R$ 10.000,00 — falta R$ 5.000,00".
3. **Dado** um grupo, **Quando** a Home abre, **Então** os outros eventos do grupo não aparecem como
   linhas próprias, nem em Cobranças nem em "Evento sem valor de venda".
4. **Dado** um grupo com eventos em 20/06 e 21/06, **Quando** a linha é montada, **Então** a data da
   linha e o vencimento seguem o primeiro evento do grupo (20/06), qualquer que seja o principal.
5. **Dado** o grupo de R$ 10.000 do cenário 2, **Quando** alguém abre a página do evento principal,
   **Então** ela mostra "Recebido R$ 5.000,00 de R$ 10.000,00", o saldo de R$ 5.000,00 e uma mensagem
   de cobrança com esse saldo.
6. **Dado** o mesmo grupo, **Quando** alguém abre a página do outro evento do grupo, **Então** a
   cobrança mostra os números do grupo e aponta para o principal, onde a venda mora. Ela não mostra
   "Recebido R$ 3.000,00 de R$ 0,00" e não oferece a mensagem de cobrança.
7. **Dado** uma venda em que faltam R$ 0,50, **Quando** alguém abre a página do evento, **Então**
   ela aparece como "Quitado", sem mensagem de cobrança.

---

### História 2 — A Home mostra o evento que ainda não tem valor (Prioridade: P1)

A comercial vê, no painel "Sem valor", a lista "Evento sem valor de venda": as vendas desde a data de
início que estão sem valor, passadas e futuras. Cada linha mostra a cliente, a data do evento com a
distância em palavras ("hoje", "em 12 dias", "aconteceu há 38 dias") e a ação "Pôr o valor", que
abre o evento na aba Comercial. Compromisso interno, cortesia, ensaio, venda da Loja Virtual e os
outros eventos de um grupo não aparecem.

**Por que esta prioridade**: hoje 6 vendas estão sem valor e não aparecem em lugar nenhum. Ficam
fora da cobrança e da comissão.

**Verificação**: cenários 2 a 4 do `verify_299.py`; estado vazio e celular na conferência de tela.

**Cenários de aceite**:

1. **Dado** um evento de 15/10/2026 sem valor e não cancelado, **Quando** a Home abre, **Então** ele
   aparece em "Evento sem valor de venda", como "a definir".
2. **Dado** um evento de 20/08/2026, que já aconteceu, com R$ 0,01, **Quando** a Home abre, **Então**
   ele aparece na lista com "R$ 0,01 (valor simbólico)" e não aparece em Cobranças.
3. **Dado** um evento de maio de 2026 sem valor, **Quando** a Home abre, **Então** ele não aparece.
4. **Dado** um evento sem valor que é cortesia, ensaio, venda da Loja Virtual ou cancelado, ou cujo
   título começa com 🟧 ou 🟠 (por exemplo, "🟧 VISITA TECNICA"), **Quando** a Home abre, **Então**
   ele não aparece.
5. **Dado** um grupo cujo principal tem valor, **Quando** a Home abre, **Então** os outros eventos do
   grupo não aparecem.
6. **Dado** um grupo cujo principal está sem valor, **Quando** a Home abre, **Então** aparece uma
   linha só, com a cliente e a marca "grupo de N eventos".
7. **Dado** um evento da lista, **Quando** alguém põe o valor e volta para a Home, **Então** a linha
   já saiu, com a mesma animação da 298, sem precisar recarregar a página.
8. **Dado** nenhum evento sem valor, **Quando** a Home abre, **Então** a lista diz "Todos os eventos
   têm valor de venda ✓".
9. **Dado** eventos sem valor que já aconteceram ou acontecem em 7, 8 e 31 dias, **Quando** a Home
   abre, **Então** o que já aconteceu e o de 7 dias ficam vermelhos, o de 8 dias amarelo e o de 31
   dias cinza.
10. **Dado** um evento sem valor que acontece hoje, **Quando** a Home abre, **Então** ele fica em
    "Ainda vai acontecer", vermelho, com "hoje".
11. **Dado** um evento com valor R$ 0,00 gravado, sem cortesia, **Quando** a Home abre, **Então** ele
    aparece como "a definir", igual ao vazio.

---

### História 3 — Lançar o evento com "valor a definir" (Prioridade: P2)

A comercial lança o evento na agenda antes de o preço fechar. No cadastro, em vez de inventar
R$ 0,01, ela marca "Valor a definir". O evento salva sem valor, a aba Comercial mostra "A definir"
e ele entra na lista "sem valor" até alguém pôr o valor.

**Por que esta prioridade**: é o que acaba com o R$ 0,01. Depende da História 2 para o evento
aparecer.

**Verificação**: cenários 5 e 6 do `verify_299.py`; cadastro e aba Comercial na conferência de tela.

**Cenários de aceite**:

1. **Dado** o cadastro com "Valor a definir" marcado e o resto preenchido, **Quando** a comercial
   salva, **Então** o evento é criado sem valor e aparece em "Evento sem valor de venda".
2. **Dado** o cadastro sem valor, ou com valor abaixo de R$ 1,00, e sem marcar "Valor a definir",
   **Quando** a comercial salva, **Então** o campo de valor mostra o que falta ("Informe o valor de
   venda ou marque 'Valor a definir'") e recebe o foco. O botão Salvar nunca fica desabilitado.
3. **Dado** um evento sem valor, inclusive um que veio do Google Agenda, **Quando** alguém muda só o
   título pela edição completa, **Então** ele salva sem pedir valor (o vendedor continua sendo
   pedido, como hoje).
4. **Dado** um evento sem valor, **Quando** alguém abre a aba Comercial, **Então** o valor de venda
   aparece como "A definir", e não como "R$ 0,00".
5. **Dado** um evento com valor a definir, **Quando** alguém põe o valor na aba Comercial, **Então**
   ele sai da lista "sem valor" e passa a ser cobrado normalmente.
6. **Dado** um evento de R$ 0,01, **Quando** alguém aplica os valores de um orçamento, **Então** o
   orçamento é aplicado como num evento sem valor.
7. **Dado** um evento com data da venda em agosto e valor a definir, **Quando** alguém põe o valor em
   setembro, **Então** a data da venda continua em agosto e a comissão entra no ciclo de setembro.
8. **Dado** um evento que já está com R$ 0,01, **Quando** alguém muda só o título pela edição
   completa, **Então** ele salva, e o R$ 0,01 continua. **Quando** alguém troca o valor por R$ 0,50,
   **Então** o campo pede o valor de verdade ou a marca.

---

### História 4 — Cobranças com vencimento e sem alarme falso (Prioridade: P2)

Cada venda com saldo aparece em "Cobranças" com o vencimento: a data combinada, se houver, qualquer
que seja a forma de pagamento; senão, a parcela ainda não coberta; senão, 2 dias antes do evento.
Diferença de centavos não aparece. Venda de valor simbólico, cortesia e venda da Loja Virtual também
não. A linha mostra a cliente, a data do evento, o vencimento, "Recebido X de Y — falta Z" e um selo
em português. A lista fica em ordem de cor e, dentro da cor, pelo vencimento.

**Por que esta prioridade**: hoje 5 linhas são alarme falso por centavos, e 25 vendas com saldo
somem até a véspera.

**Verificação**: cenários 9 a 13 do `verify_299.py`.

**Cenários de aceite**:

1. **Dado** uma venda de R$ 4.000 à vista, com evento em 30/09, R$ 2.000 recebidos e sem data
   combinada, **Quando** a Home abre em 14/09, **Então** a linha tem o selo "Vence em 14 dias", mostra
   "vence 28/09" e "Recebido R$ 2.000,00 de R$ 4.000,00 — falta R$ 2.000,00".
2. **Dado** uma venda à vista com data combinada em 20/09 e evento em 30/09, **Quando** a Home abre,
   **Então** o saldo vence em 20/09, com a marca "(data combinada)".
3. **Dado** uma venda faturada com evento em 10/09, que já aconteceu, e data combinada em 10/10,
   **Quando** a Home abre em 14/09, **Então** a linha tem o selo "Vence em 26 dias", e não
   "Atrasado".
4. **Dado** um saldo de R$ 0,50, **Quando** a Home abre, **Então** a venda não aparece.
5. **Dado** R$ 4.617,00 recebidos de R$ 9.235,00 (R$ 0,50 abaixo da metade), com evento a 20 dias,
   **Quando** a Home abre, **Então** a linha não diz "Sinal pendente": aparece o saldo, com o
   vencimento 2 dias antes do evento.
6. **Dado** uma venda sem nenhum comprovante e evento a 40 dias, **Quando** a Home abre, **Então** a
   linha diz "Sinal pendente", em amarelo, e aparece antes de todas as linhas cinza.
7. **Dado** um evento de R$ 0,01, uma cortesia ou uma venda da Loja Virtual, **Quando** a Home abre,
   **Então** nenhum deles aparece em Cobranças.
8. **Dado** um saldo cujo vencimento já passou, **Quando** a Home abre, **Então** a linha tem o selo
   "Atrasado", em vermelho, e mostra "venceu há N dias".
9. **Dado** uma venda sem cliente cadastrada, **Quando** a Home abre, **Então** a linha mostra o
   título do evento no lugar do nome.
10. **Dado** uma venda com cronograma de parcelas, **Quando** a Home abre, **Então** o vencimento é o
    da primeira parcela que os comprovantes do grupo ainda não cobrem.
11. **Dado** saldos que vencem em 2, 3 e 31 dias, **Quando** a Home abre, **Então** o primeiro fica
    vermelho, o segundo amarelo e o terceiro cinza.
12. **Dado** uma venda faturada sem comprovante, com data combinada daqui a 30 dias, **Quando** a Home
    abre, **Então** a linha tem o selo "Vence em 30 dias", e não "Sinal pendente".
13. **Dado** uma venda com data combinada em 20/10 e parcela não coberta em 05/10, **Quando** a Home
    abre, **Então** o vencimento é 20/10, com a marca "(data combinada)".
14. **Dado** uma venda sem sinal cujo saldo vence amanhã, **Quando** a Home abre, **Então** a linha
    fica vermelha, com o selo "Vence em 1 dia" e a nota "sem sinal".
15. **Dado** uma venda fechada hoje para um evento amanhã, sem comprovante, **Quando** a Home abre,
    **Então** o saldo vence hoje (nunca antes da data da venda): selo "Vence hoje", em vermelho, com a
    nota "sem sinal".
16. **Dado** uma venda de R$ 3.000 em três parcelas de R$ 1.000 (a primeira já vencida) e um
    comprovante de R$ 1.000 no outro evento do grupo, **Quando** a Home abre, **Então** o vencimento
    é o da segunda parcela, e a linha não fica "Atrasado".

---

### História 5 — O total do topo conta só tarefa de verdade (Prioridade: P3)

No topo da Home, "N pendências no total" soma só as linhas vermelhas e amarelas das listas
comerciais (Cobranças, Sem valor e Formulários). As cinza, que são informação, não entram. Os painéis
de operação continuam contando como hoje. Cada card comercial mostra o mesmo número que soma no
total, e o card "Cobranças" mostra também quanto dinheiro está em aberto.

**Por que esta prioridade**: o topo é o primeiro número que a equipe vê; se ele mente, ninguém
confia no resto.

**Verificação**: cenário 14 do `verify_299.py`.

**Cenários de aceite**:

1. **Dado** linhas das três cores em Cobranças, Sem valor e Formulários, **Quando** o topo é montado,
   **Então** "N pendências no total" soma só as vermelhas e as amarelas dessas três listas.
2. **Dado** um elenco a escalar para daqui a 5 dias (linha neutra no painel Escalar elenco),
   **Quando** o topo é montado, **Então** ele continua contando no total, como hoje.
3. **Dado** cobranças com saldo, **Quando** o topo é montado, **Então** "R$ X em aberto" soma o saldo
   de todas as linhas de Cobranças, inclusive as cinza.
4. **Dado** um painel com 3 linhas vermelhas, 2 amarelas e 4 cinza, **Quando** o topo é montado,
   **Então** o card mostra 5, e o painel aberto mostra as 9 linhas.

---

### Casos de borda

- **Principal cortesia ou permuta**: o grupo inteiro fica fora das duas listas.
- **Principal de valor simbólico**: uma linha do grupo em "sem valor" e nenhuma em Cobranças.
- **Principal cancelado com outros eventos vivos** (dado antigo; hoje o sistema não deixa cancelar o
  principal de um grupo): o grupo sai das duas listas, porque a venda está cancelada.
- **Principal apagado pela sincronização do Google** (a trava que evitaria isso está fora de
  escopo): os outros eventos deixam de ser grupo e aparecem, um a um, em "Sem valor", para alguém
  refazer a venda. Os comprovantes que estavam no principal apagado se perdem com ele, como hoje.
- **Outro evento do grupo cancelado**: o comprovante dele continua contando no recebido, porque o
  dinheiro entrou. A data do grupo ignora eventos cancelados.
- **Compromisso interno agrupado** (uma visita técnica no mesmo grupo do show): o grupo continua
  sendo cobrado pelo principal, e a data do grupo ignora o compromisso interno. As exclusões (ensaio,
  marcador, cortesia, Loja Virtual) valem pelo principal.
- **Grupo que atravessa 01/06**: vale a data do primeiro evento não cancelado do grupo.
- **Venda fechada depois do prazo** (evento amanhã, ou evento que já aconteceu): o saldo vence na
  data da venda, nunca antes. A linha nasce "Vence hoje", e não "Atrasado".
- **Recebido acima do valor**: a venda sai de Cobranças, sem aviso. A conferência dos 21 casos é da
  limpeza de dados, à parte; os 6 casos grandes são conferidos antes da publicação.
- **Comprovante sem valor** (os 15 antigos e os de maio e junho): conta como R$ 0. As vendas desde a
  data de início com esse comprovante são listadas e conferidas antes da publicação.
- **Data combinada que sobrou de outra forma de pagamento**: vale mesmo assim. A linha mostra
  "(data combinada)" para ela ficar visível e ser corrigida.
- **Parcelas que somam mais ou menos que o valor de venda**: a cobrança pede o saldo (valor menos
  recebido); as parcelas só dão a data.
- **Comprovante anexado no cadastro de um evento com valor a definir**: o dinheiro fica guardado, e a
  linha em "sem valor" mostra "já recebeu R$ X".
- **Evento com pedido de exclusão pendente**: continua nas listas até ser excluído.
- **Ensaio com título fora do padrão** ("🟧 - ENSAIO EDUCAMANTO"): fica fora pelo marcador laranja.
- **Venda cujo título começa com 🟧 ou 🟠 por engano**: fica fora das duas listas. É o custo aceito
  da regra do marcador; o título se corrige na agenda.
- **Venda lançada hoje sem comprovante do sinal**: já aparece como "Sinal pendente" e conta no total;
  fica amarela, ou vermelha com a nota "sem sinal" quando o saldo vence em até 2 dias. O comprovante
  pode ser anexado no próprio cadastro.
- **Outro evento do grupo aberto pela edição completa**: "Valor a definir" aparece marcado e travado,
  com o link para o principal; salvar não grava nada da venda nesse evento, e o vendedor não é pedido.
- **Evento de R$ 0,01 aberto pela edição completa**: abre com o valor à mostra e "Valor a definir"
  desmarcado; uma troca de título não apaga nem recusa o R$ 0,01.
- **Marcar "Valor a definir" num evento que já tinha valor**: a tela avisa, no próprio lugar, que o
  valor será apagado e a comissão a pagar, cancelada. A comissão já paga não muda.
- **Painel que não carrega**: aparece "Não foi possível carregar as cobranças" (ou "os eventos sem
  valor") com "Tentar de novo", e nunca o "✓" de lista vazia.
- **Deploy**: servidor e site ficam em versões diferentes por alguns instantes.
  - Quem estiver com a Home antiga aberta continua vendo o painel "Comercial" de hoje, já com as
    contas novas, até recarregar a página, sem erro.
  - O site novo contra o servidor antigo não quebra: as listas novas só aparecem quando o servidor
    as manda.
  - Um evento salvo com "Valor a definir" bem no minuto da troca é recusado sem gravar nada, e basta
    salvar de novo.

## Requisitos *(obrigatório)*

### Requisitos funcionais

**Grupo como uma venda só**

- **FR-001**: Em Cobranças e em "Evento sem valor de venda", o sistema DEVE tratar o grupo como uma
  venda só. Cada grupo tem uma linha, a do principal. O valor é o do principal. O recebido é a soma
  dos comprovantes de todos os eventos do grupo, inclusive os que já estão hoje em outros eventos
  do grupo e os de eventos cancelados.
- **FR-002**: A data de um grupo DEVE ser a do primeiro evento do grupo que não está cancelado e não
  é compromisso interno. Ela vale para o corte, para "já aconteceu ou ainda vai acontecer", para o
  vencimento de 2 dias antes e para a data mostrada na linha.
- **FR-003**: O recebido do grupo DEVE valer também na página do evento:
  - No principal (ou no evento avulso), "Recebido X de Y", "Quitado", o saldo e a mensagem de
    cobrança somam os comprovantes de todos os eventos do grupo. A folga do FR-023 vale aqui também:
    faltando menos de R$ 1,00, aparece "Quitado".
  - A mensagem de cobrança para copiar só é oferecida no principal ou no evento avulso, a partir do
    vencimento, e nunca em cortesia, valor simbólico ou evento sem valor.
  - Num outro evento do grupo, a cobrança mostra os números do grupo, aponta para o principal e não
    oferece a mensagem.
  - O "a receber" do Financeiro e os relatórios financeiros continuam contando por evento.
- **FR-004**: Os outros eventos do grupo DEVEM continuar aceitando comprovante. O comprovante conta
  para o grupo (FR-001 e FR-003), sem mover nada de lugar.

**Evento sem valor de venda**

- **FR-005**: A Home DEVE ter a lista "Evento sem valor de venda". Ela reúne os eventos, ou grupos,
  com data a partir da data de início, passados e futuros, cujo valor está vazio, zero ou é
  simbólico.
- **FR-006**: DEVEM ficar fora da lista, sempre pelo principal:
  - os cancelados;
  - os ensaios (tipo "Ensaio");
  - os compromissos internos: todo evento cujo título começa com o marcador laranja (🟧 ou 🟠),
    o que inclui os ensaios de título fora do padrão;
  - a cortesia ou permuta;
  - as vendas da Loja Virtual, que já chegam pagas;
  - os outros eventos de um grupo, que nunca viram linha própria.
- **FR-007**: Cada linha DEVE mostrar:
  - a cliente, pela ordem do FR-024; no grupo, também a marca "grupo de N eventos", contando os não
    cancelados;
  - a data do evento, com a distância em palavras;
  - "a definir" (valor vazio ou zero) ou o valor simbólico ("R$ 0,01 (valor simbólico)");
  - "já recebeu R$ X", quando houver comprovante;
  - a ação "Pôr o valor", que abre o evento na aba Comercial. Quem não edita a venda pela aba
    Comercial (o FINANCEIRO) vê "Abrir", como na 298; dentro da aba, ele continua podendo aplicar um
    orçamento, como hoje (FR-018).
- **FR-008**: A lista DEVE ter dois grupos, como a 298. "Ainda vai acontecer" inclui o evento de
  hoje e vem com o mais próximo primeiro. "Já aconteceu" vem com o mais recente primeiro.
- **FR-009**: A cor DEVE seguir a régua da 298, mais larga que a das cobranças (FR-026) porque o
  valor que falta precisa entrar o quanto antes:
  - vermelho: o evento já aconteceu ou acontece em até 7 dias;
  - amarelo: de 8 a 30 dias;
  - cinza: mais de 30 dias.

  A cor nunca é o único sinal: a linha sempre diz a distância em palavras ("hoje", "em 5 dias",
  "aconteceu há 38 dias") ao lado da data.
- **FR-010**: A linha DEVE sair da lista quando o evento ganha valor de venda de R$ 1,00 ou mais, é
  marcado como cortesia, é cancelado ou entra num grupo cujo principal tem valor. Em Cobranças, a
  linha sai do mesmo jeito quando a venda fica quitada. A saída tem a mesma animação da 298 e
  acontece quando a pessoa volta para a Home, sem precisar recarregar a página.
- **FR-011**: Sem nenhum evento na lista, ela DEVE dizer "Todos os eventos têm valor de venda ✓".

**Valor a definir**

- **FR-012**: O cadastro e a edição completa do evento DEVEM oferecer a marca "Valor a definir".
  Marcada, o evento salva sem valor de venda e sem valor antes do desconto. Desmarcada, o valor
  continua obrigatório e precisa ser de R$ 1,00 ou mais. A cortesia vence a marca: as duas não ficam
  marcadas ao mesmo tempo.
- **FR-013**: O evento com valor vazio ou zero, inclusive o importado do Google Agenda, DEVE abrir a
  edição completa com "Valor a definir" marcado e salvar outras mudanças sem pedir valor. O evento de
  valor simbólico abre desmarcado e salva outras mudanças sem ninguém mexer no valor. Trocar o valor
  por outro abaixo de R$ 1,00 é recusado (FR-014).
- **FR-014**: Salvar sem valor, ou com um valor novo abaixo de R$ 1,00, e sem a marca DEVE apontar os
  campos de valor, com a explicação ("Informe o valor de venda ou marque 'Valor a definir'") e o
  foco. O botão Salvar nunca fica desabilitado (constituição, Princípio V). Na aba Comercial vale a
  mesma regra para o valor novo entre R$ 0,01 e R$ 0,99; o valor vazio continua aceito (a definir).
- **FR-015**: Na aba Comercial, o valor vazio ou zero DEVE aparecer como "A definir", e não como
  "R$ 0,00". O valor simbólico aparece como está, com a marca "valor simbólico". O quadrinho "Venda"
  do resultado, que é a base do lucro, continua mostrando o número (R$ 0,00), porque é indicador
  financeiro.
- **FR-016**: O vendedor DEVE continuar obrigatório no cadastro e na edição completa, com ou sem
  valor, inclusive no evento importado do Google. A exceção é o outro evento de um grupo, onde nada
  da venda é gravado.
- **FR-017**: A data da venda DEVE continuar a informada no cadastro, que por padrão é o dia do
  cadastro. Pôr o valor depois não a troca, nem uma edição que deixe o campo vazio. O evento
  importado do Google, que não tem data da venda, ganha como data o dia em que o valor é posto, como
  hoje.
- **FR-018**: O valor simbólico DEVE contar como "sem venda" também em dois pontos da aba Comercial:
  em "Aplicar valores do orçamento" e no aviso "importado do Google sem venda". Assim a comercial
  consegue pôr o valor pelo orçamento. Quem aplica o orçamento continua sendo quem aplica hoje
  (COMERCIAL, FINANCEIRO e SUPERADMIN), e a cortesia continua recusada.
- **FR-031**: Uma comissão DEVE entrar no ciclo de pagamento do mês em que o valor foi posto, e nunca
  num mês já fechado, quando nasce num mês posterior ao da data da venda. Isso inclui a venda que
  passa de sem valor (vazio, zero ou simbólico) para valor real num mês posterior. A data da venda
  não muda. Uma comissão já paga nunca é paga de novo nem alterada, inclusive quando alguém marca
  "Valor a definir" e depois repõe o valor. A comissão de R$ 0,00 de uma venda simbólica não conta
  como paga: quando o valor real entra, nasce a comissão de verdade, no mês do valor. A regra vale para as comissões que nascerem ou mudarem
  depois da publicação; as que já existem não mudam.

**Cobranças**

- **FR-019**: Entram em Cobranças as vendas (evento ou grupo) com data a partir da data de início, com
  valor de venda de R$ 1,00 ou mais e saldo de R$ 1,00 ou mais. Ficam fora, pelo principal, as
  canceladas, os ensaios, os compromissos internos, a cortesia ou permuta, a Loja Virtual, os outros
  eventos de grupo e o valor simbólico.
- **FR-020**: Toda venda com saldo DEVE aparecer, com o vencimento do saldo. Isso inclui a que já
  recebeu metade e está a mais de 2 dias do evento, que hoje fica escondida.
- **FR-021**: O vencimento do saldo DEVE seguir esta ordem:
  1. a data combinada, quando preenchida, qualquer que seja a forma de pagamento;
  2. sem data combinada e com cronograma de parcelas, a primeira parcela do principal que o recebido
     do grupo ainda não cobre, somando as parcelas pela ordem das datas;
  3. senão, 2 dias antes da data do evento ou do grupo.

  Em nenhum caso o vencimento dos itens 2 e 3 fica antes da data da venda: se a regra der uma data
  anterior, vale a data da venda.
- **FR-022**: A venda DEVE ter o sinal pendente quando o recebido for menor que a metade do valor
  menos R$ 1,00. Vale desde o dia em que a venda é lançada, sem prazo para o comprovante chegar,
  porque a política é sinal no fechamento. Não vale quando a venda tem data combinada nem quando tem
  cronograma de parcelas: as datas acertadas substituem a regra da metade.
- **FR-023**: Diferença menor que R$ 1,00 NÃO é dívida: não gera linha nem sinal pendente, e na
  página do evento aparece como "Quitado".
- **FR-024**: Cada linha DEVE mostrar:
  - a cliente (a Contratante; senão, a primeira cliente; senão, o título do evento), e no grupo a
    marca "grupo de N eventos";
  - a data do evento;
  - a data do vencimento ("vence 28/09"), com a marca "(data combinada)" quando for o caso;
  - "Recebido R$ X de R$ Y — falta R$ Z";
  - o selo (FR-025) e, quando for o caso, a nota "sem sinal";
  - a ação "Abrir cobrança", que abre o evento na aba Comercial.
- **FR-025**: Os selos DEVEM estar em português e carregam a distância em palavras:
  - "Atrasado" (o vencimento passou; a linha diz também "venceu há N dias");
  - "Vence hoje";
  - "Vence em N dias" ("Vence em 1 dia" no singular);
  - "Sinal pendente".

  Nenhum código em inglês ou cru aparece na tela.
- **FR-026**: A cor e o selo DEVEM seguir esta ordem:
  1. vermelho, quando o saldo venceu ou vence em até 2 dias. O selo é o do prazo ("Atrasado", "Vence
     hoje" ou "Vence em N dias") e, com o sinal pendente, a linha ganha a nota "sem sinal";
  2. amarelo com o selo "Sinal pendente", quando o sinal está pendente e o saldo vence em mais de 2
     dias;
  3. amarelo, quando vence de 3 a 30 dias;
  4. cinza, quando vence em mais de 30 dias.

  A lista fica em ordem de cor (vermelho, amarelo, cinza) e, dentro da cor, pelo vencimento mais
  antigo primeiro.
- **FR-027**: Quem vê os painéis "Cobranças" e "Sem valor" (COMERCIAL, FINANCEIRO e SUPERADMIN) DEVE
  continuar vendo todas as cobranças.

**Home**

- **FR-028**: As duas listas DEVEM ficar em dois painéis, "Cobranças" e "Sem valor", no lugar do
  painel "Comercial" de hoje.
  - "Cobranças" é uma lista só; "Sem valor" tem os dois grupos do FR-008.
  - Cada lista, ou cada grupo, mostra 6 linhas e "Mostrar todas".
  - O contador do painel aberto mostra todas as linhas.
  - O topo ganha os cards "Cobranças" e "Sem valor", cada um com o mesmo nome do seu painel, e clicar
    no card abre o painel.
  - O número do card comercial é o de linhas para agir (vermelhas e amarelas).
- **FR-029**: "N pendências no total", no topo, DEVE somar:
  - das listas comerciais (Cobranças, Sem valor e os Formulários da 298), só as linhas vermelhas e
    amarelas, que são o mesmo número mostrado em cada card; as cinza são informação e não entram;
  - dos painéis de operação (Escalar elenco, Figurino, Oficina, Ensaio, Contas do mês), todas as
    linhas, como hoje.

  O "R$ X em aberto" do card Cobranças soma o saldo de todas as linhas de Cobranças.
- **FR-030**: A Home DEVE ser conferida no computador e no celular (375 px), sem rolagem horizontal.
  No celular, a linha pode ocupar várias linhas de texto, mas nada do que aparece no computador é
  escondido, e a ação fica visível.
- **FR-032**: Estados sem dados e com erro:
  - Cobranças sem nenhuma venda com saldo DEVE dizer "Nenhuma cobrança em aberto ✓", e o card
    mostra "Em dia ✓".
  - Um painel cuja lista não carregou DEVE dizer "Não foi possível carregar as cobranças" (ou "os
    eventos sem valor"), com "Tentar de novo". Nunca mostra o "✓" nem esconde o painel em silêncio.

### Entidades *(se houver dados)*

Nenhuma entidade nova e nenhuma migration. A feature usa as que existem:

- **Evento**: valor de venda, cortesia, forma de pagamento, data combinada, título e grupo
  (principal e outros eventos).
- **Comprovante**.
- **Parcela** do cronograma.
- **Comissão**: o ciclo pelo `payable_from`, que já existe.

### RBAC *(obrigatório se houver endpoint novo ou alterado)*

- `GET /api/dashboard`: o bloco comercial ganha a lista "sem valor", as cobranças mudam de regra e o
  total do topo muda de conta.
  - Papéis: COMERCIAL, FINANCEIRO e SUPERADMIN, pelo papel efetivo (respeita o "Ver como"), sem
    mudança.
  - O `docs/01` §4.3 ganha a linha dessa rota, que ainda não existe.
- `POST /api/events` e `PATCH /api/events/<id>`: a validação do valor muda (valor a definir;
  abaixo de R$ 1,00 recusado sem a marca), e o outro evento de grupo não grava a venda. Os papéis
  continuam COMERCIAL e SUPERADMIN.
- `GET /api/events/<id>` (e as escritas que devolvem o detalhe): a cobrança passa a somar o grupo
  (FR-003). A parte comercial continua visível para COMERCIAL, FINANCEIRO e SUPERADMIN.
- `PATCH /api/events/<id>/orcamento`: o valor simbólico passa a contar como "sem venda" (FR-018). Os
  papéis continuam COMERCIAL, FINANCEIRO e SUPERADMIN.

## Verificação (`verify_299.py`) *(obrigatório — Princípio VIII)*

Arquivo: `specs/299-sem-valor-cobrancas/verify_299.py`, contra `manto_local` (`DATABASE_URL` de
`.local-db-url`, `FLASK_ENV=development`, `MANTO_SEM_THREADS=1`). Login só por
`POST /api/auth/login`; escrita conferida por conexão separada; limpeza no `finally`. Evento de teste
com "[TESTE verify 299] pode apagar" no título, e a chamada ao Google trocada por uma falsa (como na
298).

| # | Cenário | O que prova | Deve falhar? |
|---|---|---|---|
| 1 | Evento de maio sem valor; evento de maio com valor e saldo; grupo que atravessa 01/06 | nenhum aparece nas listas; o grupo vale pela data do primeiro evento | não |
| 2 | Vazio, zero, R$ 0,01 e R$ 0,99 contra R$ 1,00; eventos hoje, a 7, 8 e 31 dias e já passados | os quatro primeiros entram em "sem valor" (vazio e zero como a definir) e R$ 1,00 não; o de hoje em "ainda vai acontecer"; 7 dias vermelho, 8 amarelo, 31 cinza; ordem dos dois grupos | não |
| 3 | Cancelado, ensaio, cortesia, título com 🟧 e com 🟠, Loja Virtual; visita técnica agrupada com um show | nenhum entra em "sem valor"; o grupo é cobrado pelo principal e a data ignora a visita | não |
| 4 | Grupo: principal com valor; principal sem valor; principal cortesia | outros eventos fora; uma linha do grupo com "grupo de N eventos" e "já recebeu"; grupo fora | não |
| 5 | Valor a definir | cadastro com a marca cria sem valor e o evento entra na lista; sem valor, ou abaixo de R$ 1,00, sem marca → 400 no campo; vendedor continua obrigatório; pôr o valor pela aba Comercial tira da lista e mantém a data da venda; valor posto num mês depois do da data da venda → comissão no ciclo do mês do valor; comissão já paga não é paga de novo | não |
| 6 | Edição completa e orçamento | evento sem valor salva o título; evento de R$ 0,01 salva o título mantendo o valor e recusa R$ 0,50; outro evento de grupo salva sem gravar a venda; orçamento aplicado sobre R$ 0,01 | não |
| 7 | Caso 344 (3.078 + 3.078 de 5.508) e grupo de 10.000 (2.000 + 3.000) | o 344 sai de Cobranças; o outro vira uma linha, "falta R$ 5.000,00" | não |
| 8 | Grupo com eventos em 20/06 e 21/06 e um cancelado em 19/06 com comprovante | a data do grupo é 20/06, o vencimento 18/06, e o comprovante do cancelado conta | não |
| 9 | Vencimento | 2 dias antes; data combinada à vista; data combinada depois do evento; parcela; data combinada vence a parcela; parcela coberta por comprovante de outro evento; venda fechada hoje para evento amanhã vence hoje | não |
| 10 | Centavos e sinal | saldo de R$ 0,50 fora; sinal R$ 0,50 abaixo da metade não é sinal pendente; venda lançada hoje sem comprovante já tem sinal pendente; faturada com data combinada e parcelada com cronograma, sem comprovante, não têm sinal pendente | não |
| 11 | Metade paga e evento a 20 dias | aparece, com vencimento (hoje fica escondida) | não |
| 12 | R$ 0,01, cortesia com valor (dado antigo), Loja Virtual, 🟧 com valor e saldo, ensaio com valor, cancelado com saldo | nenhum em Cobranças | não |
| 13 | Conteúdo, cor e ordem da linha | cliente ou título, data do evento, vencimento e marca de grupo; selos só em português; 2 dias vermelho, 3 amarelo, 31 cinza; sem sinal vencendo amanhã vermelho com "sem sinal"; sem sinal a 40 dias amarelo antes das cinza; chaves antigas presentes para o site antigo | não |
| 14 | Total do topo e cards | das listas comerciais, só vermelhas e amarelas, igual ao número de cada card; painéis de operação como hoje; "R$ X em aberto" soma todas as cobranças | não |
| 15 | Página do evento no grupo | o principal soma o grupo (recebido, saldo, mensagem); o outro evento mostra o grupo, aponta o principal e não oferece a mensagem; faltando R$ 0,50, "Quitado" | não |
| 16 | CASTING abre a Home e o detalhe; FINANCEIRO tenta criar e editar evento | sem bloco comercial e sem cobrança no detalhe; 403 nos dois; controle: FINANCEIRO vê a mesma cobrança e aplica orçamento | **sim** |
| 17 | Limpeza | eventos, comprovantes e comissões de teste apagados | — |

Conferência de tela:
- a Home no computador e no celular (375 × 812), com os dois painéis, as cores, os estados vazios e
  "Mostrar todas";
- a linha "sem valor" vista como FINANCEIRO, com "Abrir";
- o cadastro com "Valor a definir" e o foco no campo;
- a aba Comercial com "A definir";
- a página do principal e a de outro evento de um grupo;
- o painel de Formulários da 298, igual ao de antes.

## Antes da publicação

Decisão do dono (14/09): antes do deploy, levantar, só lendo a produção, a lista dos casos de dado
que podem enganar as listas, com o efeito de cada um nas Cobranças. O dono confere e corrige o que
precisar antes de publicar:
- o grupo 344 (dois comprovantes de R$ 3.078) e os outros 5 casos grandes de recebido acima do
  valor (85, 184, 288, 309, 319);
- as vendas desde a data de início com comprovante sem valor.

A equipe comercial e o financeiro são avisados no dia: Cobranças cresce (as vendas com metade paga
passam a aparecer) e o total do topo cai (as linhas cinza deixam de contar). O texto do aviso fica
pronto no `quickstart.md`; o dono decide quem envia.

## Critérios de sucesso *(obrigatório)*

- **SC-001**: Na conferência depois do deploy, a lista "Evento sem valor de venda" tem exatamente as
  vendas sem valor desde a data de início que não são compromisso interno, cortesia, cancelado, Loja
  Virtual nem outro evento de grupo. A conferência usa a mesma consulta que, em 14/09, deu 6.
- **SC-002**: Nenhum grupo aparece cobrando valor já pago em outro evento do grupo, e o grupo 344 sai
  de Cobranças (depois de conferido).
- **SC-003**: Para todo grupo, a Home e a página do evento principal mostram o mesmo recebido e o
  mesmo saldo.
- **SC-004**: Nenhuma linha de cobrança nasce de diferença menor que R$ 1,00, e nenhuma venda recebe
  sinal pendente por diferença menor que R$ 1,00. Em 14/09 eram 2 linhas de R$ 0,01 (que vão para
  "sem valor") e 3 sinais com centavos a menos (que continuam em Cobranças, sem o sinal pendente).
- **SC-005**: Toda venda com saldo de R$ 1,00 ou mais desde a data de início aparece em Cobranças,
  com o vencimento, exceto as que o FR-019 exclui. Hoje 25 ficam escondidas.
- **SC-006**: Nenhum texto em inglês nem código cru nas duas listas.
- **SC-007**: Da linha "sem valor" ao valor salvo em até 2 cliques, mais a digitação.
- **SC-008**: Depois do deploy, nenhum evento novo é gravado com valor entre R$ 0,01 e R$ 0,99: o
  cadastro, a edição e a aba Comercial recusam. A conferência é uma consulta 30 dias depois da
  publicação.
- **SC-009**: A soma dos cards comerciais é igual à parte comercial do total do topo, nenhuma linha
  cinza das listas comerciais conta, e os painéis de operação contam como antes.
- **SC-010**: A Home no celular (375 px) não tem rolagem horizontal.
- **SC-011**: Durante o deploy, a Home não fica em branco nem com o site antigo aberto contra o
  servidor novo nem com o site novo contra o servidor antigo.

## Fora de escopo

- **Limpeza única de dados**, à parte e com o OK do dono:
  - os 21 recebidos acima do valor (os 6 grandes são conferidos antes da publicação);
  - os 15 comprovantes antigos sem valor;
  - os 24 comprovantes lançados sem valor em maio e junho;
  - as datas impossíveis dos formulários.
- **Mover para o principal os comprovantes dos outros eventos do grupo.** A soma é na leitura.
- **Relatórios financeiros**: "a receber" do Financeiro, funil de vendas, indicadores, DRE, comissão
  e Auditoria de Input continuam contando por evento, e o R$ 0,01 segue contando como venda neles. Na
  comissão, a única mudança é o ciclo do FR-031.
- **Comissões que já existem**: as nascidas antes da publicação não mudam de ciclo.
- **Cobrança automática** à cliente (WhatsApp ou e-mail) e o botão "Copiar cobrança" na Home.
- **Outras mudanças de cadastro e permissão**:
  - vendedora ver só as próprias cobranças;
  - separar cortesia de permuta;
  - "Pagamento futuro" no cadastro;
  - unificar "parcelado" e "parcelado_datas".
- **A trava que impediria o sync do Google Agenda de apagar o principal de um grupo.** Vira dívida
  no `docs/05`.
- **A spec 051**, uma lista "SEM VALOR" que nunca foi entregue, fica superada por esta.

## Docs a atualizar

- `docs/01`:
  - o contrato do bloco comercial de `GET /api/dashboard`;
  - a validação do valor em `POST/PATCH /api/events`;
  - a cobrança da leitura do evento;
  - a regra do orçamento sobre o valor simbólico;
  - o §4.3, com as linhas do dashboard e do orçamento.
- `docs/02`:
  - a Home: os painéis "Cobranças" e "Sem valor", os cards, o total do topo e os estados vazio e de
    erro;
  - o cadastro e a edição com "Valor a definir";
  - a aba Comercial com "A definir" e a cobrança do grupo.
- `docs/03`: entrada no topo.
- `docs/04`: os invariantes:
  - o grupo é uma venda só na cobrança;
  - o que é "sem valor";
  - o marcador laranja do compromisso interno;
  - o vencimento do saldo (nunca antes da data da venda);
  - a folga de centavos;
  - o ciclo da comissão tardia.
- `docs/05`:
  - a trava do sync;
  - "parcelado" contra "parcelado_datas";
  - a Auditoria de Input e o "a receber" do Financeiro, que seguem outra conta;
  - a remoção futura dos campos antigos da lista de cobranças.
- `specs/051-task-venda-pendente/spec.md`: marcada como superada pela 299.

## Premissas

- **"Valor a definir" é o valor vazio.** Não há estado novo gravado; a marca no cadastro só evita o
  esquecimento.
- **Valor simbólico é acima de zero e abaixo de R$ 1,00**, e hoje só existe R$ 0,01. A folga de
  centavos usa o mesmo limite: diferença abaixo de R$ 1,00.
- **O corte é a data de início do sistema**, a mesma das cobranças e dos formulários. Em produção ela
  é 01/06/2026 (conferido em 14/09), e vale 01/06/2026 se a configuração estiver vazia.
- **A política comercial não muda**: sinal de 50% no fechamento e saldo até 2 dias antes. A data
  combinada vale sobre os 2 dias antes.
- **Comprovante de outro evento do grupo que foi cancelado continua contando**, porque o dinheiro
  entrou. A devolução, se houve, é gasto.
- **Recebido acima do valor não gera aviso** nesta feature.
- **Comprovante sem valor conta como R$ 0.**
- **A venda da Loja Virtual fica fora das duas listas** porque já é paga na própria loja e nunca tem
  comprovante no evento: sem a exclusão, apareceria cobrando o valor inteiro. Hoje não há nenhuma
  desde 01/06; a regra é proteção.
- **Os limites de cor foram decididos pelo dono no `/speckit-clarify`**, e as duas listas usam réguas
  diferentes de propósito:
  - cobranças (FR-026): o vermelho segue o prazo da política, 2 dias;
  - sem valor (FR-009): a régua da 298, com vermelho até 7 dias, porque o valor precisa entrar logo.
- **Servidor e site sobem com alguns instantes de diferença**, e o site antigo pode ficar aberto
  mais tempo: os campos antigos continuam, e os campos novos são opcionais na tela.
- **O modelo visual é o painel da 298**: grupos com 6 linhas, "Mostrar todas" e animação de saída.
