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

  É assunto da limpeza de dados, à parte (Fora de escopo).
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
- **Valor simbólico**: abaixo de R$ 1,00. Hoje só existe R$ 0,01, usado para "segurar a data".
- **Valor a definir**: o evento salvo sem valor de propósito, porque o preço ainda não fechou.
- **Recebido**: a soma dos comprovantes de todos os eventos do grupo.
- **Saldo**: o valor de venda menos o recebido.
- **Sinal**: a metade do valor, paga no fechamento.
- **Data combinada**: a data de pagamento acertada com a cliente.
- **Vencimento do saldo**: a data combinada, se houver; senão, 2 dias antes do evento.
- **Compromisso interno**: evento da agenda que não é venda (ensaio, visita técnica, gravação),
  marcado com o laranja 🟧 ou 🟠 no começo do título.
- **Cobrança**: uma linha da Home para uma venda com saldo.

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

## Cenários e Verificação *(obrigatório)*

### História 1 — O grupo é cobrado como uma venda só (Prioridade: P1)

A comercial abre a Home e vê, em "Cobranças", uma linha por venda. No grupo, a linha é a do
principal, e o recebido soma os comprovantes de todos os eventos do grupo. O grupo 344, que hoje
aparece cobrando R$ 2.430 que a cliente já pagou num outro evento do grupo, sai da lista. A página
do evento mostra o mesmo número: o principal do 344 aparece quitado, e a mensagem de cobrança não
pede o que já foi pago.

**Por que esta prioridade**: é o erro que faz a comercial cobrar dinheiro que a cliente já pagou.

**Verificação**: cenários 7, 8 e 15 do `verify_299.py`.

**Cenários de aceite**:

1. **Dado** um grupo com valor de R$ 5.508 no principal, um comprovante de R$ 3.078 no principal e
   outro de R$ 3.078 no outro evento do grupo, **Quando** a Home abre, **Então** o grupo não aparece
   em Cobranças, porque já recebeu tudo.
2. **Dado** um grupo de R$ 10.000 com R$ 2.000 no principal e R$ 3.000 no outro evento, **Quando** a
   Home abre, **Então** aparece uma linha só: "Recebido R$ 5.000,00 de R$ 10.000,00 — falta
   R$ 5.000,00".
3. **Dado** um grupo, **Quando** a Home abre, **Então** os outros eventos do grupo não aparecem como
   linhas próprias, nem em Cobranças nem em "Evento sem valor de venda".
4. **Dado** um grupo com eventos em 20/06 e 21/06, **Quando** a linha é montada, **Então** a data da
   linha e o vencimento seguem o primeiro evento do grupo (20/06), qualquer que seja o principal.
5. **Dado** o grupo de R$ 10.000 do cenário 2, **Quando** alguém abre a página do evento principal,
   **Então** ela mostra "Recebido R$ 5.000,00 de R$ 10.000,00", o saldo de R$ 5.000,00 e uma mensagem
   de cobrança com esse saldo.
6. **Dado** o mesmo grupo, **Quando** alguém abre a página do outro evento do grupo, **Então** a
   cobrança mostra os números do grupo e aponta para o principal, onde a venda mora. Ela não mostra
   "Recebido R$ 3.000,00 de R$ 0,00".

---

### História 2 — A Home mostra o evento que ainda não tem valor (Prioridade: P1)

A comercial vê, no painel Comercial, a lista "Evento sem valor de venda": as vendas desde 01/06 que
estão sem valor, passadas e futuras. Cada linha mostra a cliente, a data do evento com a distância em
palavras ("em 12 dias", "aconteceu há 38 dias") e a ação "Pôr o valor", que abre o evento na aba
Comercial. Compromisso interno, cortesia, ensaio e os outros eventos de um grupo não aparecem.

**Por que esta prioridade**: hoje 6 vendas estão sem valor e não aparecem em lugar nenhum. Ficam
fora da cobrança e da comissão.

**Verificação**: cenários 2 a 4 do `verify_299.py`; estado vazio e celular na conferência de tela.

**Cenários de aceite**:

1. **Dado** um evento de 15/10/2026 sem valor e não cancelado, **Quando** a Home abre, **Então** ele
   aparece em "Evento sem valor de venda".
2. **Dado** um evento de 20/08/2026, que já aconteceu, com R$ 0,01, **Quando** a Home abre, **Então**
   ele aparece na lista com "R$ 0,01 (valor simbólico)" e não aparece em Cobranças.
3. **Dado** um evento de maio de 2026 sem valor, **Quando** a Home abre, **Então** ele não aparece.
4. **Dado** um evento sem valor que é cortesia, ensaio ou cancelado, ou cujo título começa com 🟧
   ou 🟠 (por exemplo, "🟧 VISITA TECNICA"), **Quando** a Home abre, **Então** ele não aparece.
5. **Dado** um grupo cujo principal tem valor, **Quando** a Home abre, **Então** os outros eventos do
   grupo não aparecem.
6. **Dado** um grupo cujo principal está sem valor, **Quando** a Home abre, **Então** aparece uma
   linha só, com o nome do grupo e quantos eventos ele tem.
7. **Dado** um evento da lista, **Quando** alguém põe o valor e a Home atualiza, **Então** a linha sai,
   com a mesma animação da 298.
8. **Dado** nenhum evento sem valor, **Quando** a Home abre, **Então** a lista diz "Todos os eventos
   têm valor de venda ✓".
9. **Dado** eventos sem valor que já aconteceram ou acontecem em 7, 8 e 31 dias, **Quando** a Home
   abre, **Então** o que já aconteceu e o de 7 dias ficam vermelhos, o de 8 dias amarelo e o de 31
   dias cinza.

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
2. **Dado** o cadastro sem valor e sem marcar "Valor a definir", **Quando** a comercial salva,
   **Então** o campo de valor mostra o que falta e recebe o foco. O botão Salvar nunca fica
   desabilitado.
3. **Dado** um evento sem valor, inclusive um que veio do Google Agenda, **Quando** alguém muda só o
   título pela edição completa, **Então** ele salva sem pedir valor.
4. **Dado** um evento sem valor, **Quando** alguém abre a aba Comercial, **Então** o valor de venda
   aparece como "A definir", e não como "R$ 0,00".
5. **Dado** um evento com valor a definir, **Quando** alguém põe o valor na aba Comercial, **Então**
   ele sai da lista "sem valor" e passa a ser cobrado normalmente.
6. **Dado** um evento de R$ 0,01, **Quando** alguém aplica os valores de um orçamento, **Então** o
   orçamento é aplicado como num evento sem valor.

---

### História 4 — Cobranças com vencimento e sem alarme falso (Prioridade: P2)

Cada venda com saldo aparece em "Cobranças" com o vencimento: a data combinada, se houver, qualquer
que seja a forma de pagamento; senão, 2 dias antes do evento. Diferença de centavos não aparece.
Venda de valor simbólico, cortesia e venda da Loja Virtual também não. A linha mostra a cliente, a
data do evento, o vencimento em palavras, "Recebido X de Y — falta Z" e um selo em português.

**Por que esta prioridade**: hoje 5 linhas são alarme falso por centavos, e 25 vendas com saldo
somem até a véspera.

**Verificação**: cenários 9 a 13 do `verify_299.py`.

**Cenários de aceite**:

1. **Dado** uma venda de R$ 4.000 à vista, com evento em 30/09, R$ 2.000 recebidos e sem data
   combinada, **Quando** a Home abre em 14/09, **Então** a linha aparece com "vence 28/09 · em 14
   dias" e "Recebido R$ 2.000,00 de R$ 4.000,00 — falta R$ 2.000,00".
2. **Dado** uma venda à vista com data combinada em 20/09 e evento em 30/09, **Quando** a Home abre,
   **Então** o saldo vence em 20/09, com a marca "data combinada".
3. **Dado** uma venda faturada com evento em 10/09, que já aconteceu, e data combinada em 10/10,
   **Quando** a Home abre em 14/09, **Então** a linha diz "vence em 26 dias", e não "atrasado".
4. **Dado** um saldo de R$ 0,50, **Quando** a Home abre, **Então** a venda não aparece.
5. **Dado** R$ 4.617,00 recebidos de R$ 9.235,00 (R$ 0,50 abaixo da metade), com evento a 20 dias,
   **Quando** a Home abre, **Então** a linha não diz "Sinal pendente": aparece o saldo, com o
   vencimento 2 dias antes do evento.
6. **Dado** uma venda sem nenhum comprovante e evento a 40 dias, **Quando** a Home abre, **Então** a
   linha diz "Sinal pendente".
7. **Dado** um evento de R$ 0,01, uma cortesia ou uma venda da Loja Virtual, **Quando** a Home abre,
   **Então** nenhum deles aparece em Cobranças.
8. **Dado** um saldo cujo vencimento já passou, **Quando** a Home abre, **Então** a linha tem o selo
   "Atrasado", em vermelho, com "venceu há N dias".
9. **Dado** uma venda sem cliente cadastrada, **Quando** a Home abre, **Então** a linha mostra o
   título do evento no lugar do nome.
10. **Dado** uma venda com cronograma de parcelas, **Quando** a Home abre, **Então** o vencimento é o
    da primeira parcela não recebida.
11. **Dado** saldos que vencem em 2, 3 e 31 dias, **Quando** a Home abre, **Então** o primeiro fica
    vermelho, o segundo amarelo e o terceiro cinza.

---

### História 5 — O total do topo conta só tarefa de verdade (Prioridade: P3)

No topo da Home, "N pendências no total" soma só as linhas vermelhas e amarelas das listas
comerciais (Cobranças, Sem valor e Formulários). As cinza, que são informação, não entram. Os painéis
de operação continuam contando como hoje. O card "Cobranças" mostra quanto dinheiro está em aberto.

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

---

### Casos de borda

- **Principal cortesia ou permuta**: o grupo inteiro fica fora das duas listas.
- **Principal de valor simbólico**: uma linha do grupo em "sem valor" e nenhuma em Cobranças.
- **Principal cancelado com outros eventos vivos** (dado antigo; hoje o sistema não deixa cancelar o
  principal de um grupo): o grupo sai das duas listas, porque a venda está cancelada.
- **Outro evento do grupo cancelado**: o comprovante dele continua contando no recebido, porque o
  dinheiro entrou. A data do grupo ignora eventos cancelados.
- **Grupo que atravessa 01/06**: vale a data do primeiro evento não cancelado do grupo.
- **Recebido acima do valor**: a venda sai de Cobranças, sem aviso. A conferência dos 21 casos é da
  limpeza de dados, à parte.
- **Comprovante antigo sem valor** (15 em produção): conta como R$ 0.
- **Data combinada que sobrou de outra forma de pagamento**: vale mesmo assim. A linha mostra
  "(data combinada)" para ela ficar visível e ser corrigida.
- **Comprovante anexado no cadastro de um evento com valor a definir**: o dinheiro fica guardado, e a
  linha em "sem valor" mostra "já recebeu R$ X".
- **Evento com pedido de exclusão pendente**: continua nas listas até ser excluído.
- **Venda lançada hoje sem comprovante do sinal**: já aparece como "Sinal pendente", em amarelo, e
  conta no total. O comprovante pode ser anexado no próprio cadastro.
- **Ensaio com título fora do padrão** ("🟧 - ENSAIO EDUCAMANTO"): fica fora pelo marcador laranja.
- **Venda cujo título começa com 🟧 ou 🟠 por engano**: fica fora das duas listas. É o custo aceito
  da regra do marcador; o título se corrige na agenda.
- **Deploy**: servidor e site ficam cerca de 1 minuto em versões diferentes. A tela aceita a resposta
  antiga, sem quebrar (como na 298).

## Requisitos *(obrigatório)*

### Requisitos funcionais

**Grupo como uma venda só**

- **FR-001**: Em Cobranças e em "Evento sem valor de venda", o sistema DEVE tratar o grupo como uma
  venda só. Cada grupo tem uma linha, a do principal. O valor é o do principal. O recebido é a soma
  dos comprovantes de todos os eventos do grupo, inclusive os que já estão hoje em outros eventos
  do grupo.
- **FR-002**: A data de um grupo DEVE ser a do primeiro evento não cancelado do grupo. Ela vale para
  o corte de 01/06, para "já aconteceu ou ainda vai acontecer", para o vencimento de 2 dias antes e
  para a data mostrada na linha.
- **FR-003**: O recebido do grupo DEVE valer também na página do evento. No principal, "Recebido X
  de Y", "Quitado", o saldo e a mensagem de cobrança somam os comprovantes de todos os eventos do
  grupo. Num outro evento do grupo, a cobrança mostra os números do grupo e aponta para o principal.
  O "a receber" do Financeiro e os relatórios financeiros continuam contando por evento.
- **FR-004**: Os outros eventos do grupo DEVEM continuar aceitando comprovante. O comprovante conta
  para o grupo (FR-001 e FR-003), sem mover nada de lugar.

**Evento sem valor de venda**

- **FR-005**: A Home DEVE ter a lista "Evento sem valor de venda". Ela reúne os eventos, ou grupos,
  com data a partir de 01/06/2026, passados e futuros, cujo valor está vazio, zero ou é simbólico
  (abaixo de R$ 1,00).
- **FR-006**: DEVEM ficar fora da lista:
  - os cancelados;
  - os ensaios (tipo "Ensaio");
  - os compromissos internos: todo evento cujo título começa com o marcador laranja (🟧 ou 🟠),
    o que inclui os ensaios de título fora do padrão;
  - a cortesia ou permuta;
  - os outros eventos de um grupo, e o grupo cujo principal é cortesia;
  - as vendas da Loja Virtual.
- **FR-007**: Cada linha DEVE mostrar:
  - a cliente; sem cliente, o título do evento; no grupo, o nome do grupo e quantos eventos ele tem;
  - a data do evento, com a distância em palavras;
  - "a definir" ou o valor simbólico ("R$ 0,01 (valor simbólico)");
  - o recebido, quando houver comprovante;
  - a ação "Pôr o valor", que abre o evento na aba Comercial.
- **FR-008**: A lista DEVE ter dois grupos, como a 298. "Ainda vai acontecer" vem com o mais próximo
  primeiro. "Já aconteceu" vem com o mais recente primeiro.
- **FR-009**: A cor DEVE seguir a régua da 298, com a urgência também em palavras. Ela é mais larga
  que a das cobranças (FR-026) porque o valor que falta precisa entrar o quanto antes:
  - vermelho: o evento já aconteceu ou acontece em até 7 dias;
  - amarelo: de 8 a 30 dias;
  - cinza: mais de 30 dias.
- **FR-010**: A linha DEVE sair da lista quando o evento ganha valor de venda de R$ 1,00 ou mais, é
  marcado como cortesia, é cancelado ou entra num grupo cujo principal tem valor. A saída tem a mesma
  animação da 298.
- **FR-011**: Sem nenhum evento na lista, ela DEVE dizer "Todos os eventos têm valor de venda ✓".

**Valor a definir**

- **FR-012**: O cadastro e a edição completa do evento DEVEM oferecer a marca "Valor a definir".
  Marcada, o evento salva sem valor de venda e sem valor antes do desconto. Desmarcada, o valor
  continua obrigatório, como hoje.
- **FR-013**: O evento que já está sem valor, inclusive o importado do Google Agenda, DEVE abrir a
  edição completa com "Valor a definir" marcado e salvar outras mudanças sem pedir valor.
- **FR-014**: Salvar sem valor e sem a marca DEVE apontar o campo de valor, com a explicação e o foco.
  O botão Salvar nunca fica desabilitado (constituição, Princípio V).
- **FR-015**: Na aba Comercial, o valor vazio DEVE aparecer como "A definir", e não como "R$ 0,00". O
  valor simbólico aparece como está, com a marca "valor simbólico".
- **FR-016**: O vendedor DEVE continuar obrigatório no cadastro, com ou sem valor.
- **FR-017**: A data da venda DEVE continuar a informada no cadastro, que por padrão é o dia do
  cadastro. Pôr o valor depois não a troca.
- **FR-018**: O valor simbólico DEVE contar como "sem venda" também em dois pontos da aba Comercial:
  em "Aplicar valores do orçamento" e no aviso "importado do Google sem venda". Assim a comercial
  consegue pôr o valor pelo orçamento.

**Cobranças**

- **FR-019**: Entram em Cobranças as vendas (evento ou grupo) com data a partir de 01/06/2026, não
  canceladas, fora de ensaio e de compromisso interno, com valor de venda de R$ 1,00 ou mais e saldo
  de R$ 1,00 ou mais. Ficam fora a cortesia ou permuta, a Loja Virtual, os outros eventos de grupo e
  o valor simbólico.
- **FR-020**: Toda venda com saldo DEVE aparecer, com o vencimento do saldo. Isso inclui a que já
  recebeu metade e está a mais de 2 dias do evento, que hoje fica escondida.
- **FR-021**: O vencimento do saldo DEVE ser a data combinada, quando preenchida, qualquer que seja a
  forma de pagamento. Sem data combinada, vence 2 dias antes da data do evento ou do grupo. Com
  cronograma de parcelas, vence na primeira parcela não recebida.
- **FR-022**: A linha DEVE dizer "Sinal pendente" quando o recebido for menor que a metade do valor
  menos R$ 1,00. Vale desde o dia em que a venda é lançada, sem prazo para o comprovante chegar,
  porque a política é sinal no fechamento.
- **FR-023**: Diferença menor que R$ 1,00 NÃO é dívida: não gera linha nem "Sinal pendente".
- **FR-024**: Cada linha DEVE mostrar:
  - a cliente (a Contratante; senão, a primeira cliente; senão, o título do evento);
  - a data do evento;
  - o vencimento, com a distância em palavras ("vence hoje", "vence em 3 dias", "venceu há 5 dias")
    e a marca "(data combinada)" quando for o caso;
  - "Recebido R$ X de R$ Y — falta R$ Z";
  - o selo;
  - a ação "Abrir cobrança", que abre o evento na aba Comercial.
- **FR-025**: Os selos DEVEM estar em português: "Atrasado", "Vence hoje", "Vence em N dias" e "Sinal
  pendente". Nenhum código em inglês ou cru aparece na tela.
- **FR-026**: A cor DEVE usar as três cores da 298, com os limites das cobranças:
  - vermelho: vencido, ou vence em até 2 dias;
  - amarelo: vence de 3 a 30 dias, ou sinal pendente;
  - cinza: vence em mais de 30 dias.

  A ordem é pelo vencimento, o mais antigo primeiro.
- **FR-027**: Quem vê o painel Comercial (COMERCIAL, FINANCEIRO e SUPERADMIN) DEVE continuar vendo
  todas as cobranças.

**Home**

- **FR-028**: As duas listas DEVEM ficar no painel Comercial. Cada uma tem contador, 6 linhas e
  "Mostrar todas". O topo ganha os cards "Sem valor" e "Cobranças", e card e painel usam o mesmo nome.
- **FR-029**: "N pendências no total", no topo, DEVE somar:
  - das listas comerciais (Cobranças, Sem valor e os Formulários da 298), só as linhas vermelhas e
    amarelas; as cinza são informação e não entram;
  - dos painéis de operação (Escalar elenco, Figurino, Oficina, Ensaio, Contas do mês), todas as
    linhas, como hoje.

  O "R$ X em aberto" do card Cobranças soma o saldo de todas as linhas de Cobranças.
- **FR-030**: A Home DEVE ser conferida no computador e no celular (375 px), sem rolagem horizontal.

### Entidades *(se houver dados)*

Nenhuma entidade nova e nenhuma migration. A feature usa as que existem:

- **Evento**: valor de venda, cortesia, forma de pagamento, data combinada, título e grupo
  (principal e outros eventos).
- **Comprovante**.
- **Parcela** do cronograma.

### RBAC *(obrigatório se houver endpoint novo ou alterado)*

- `GET /api/dashboard`: o bloco comercial ganha a lista "sem valor", as cobranças mudam de regra e o
  total do topo muda de conta. Papéis: COMERCIAL, FINANCEIRO e SUPERADMIN, sem mudança. A linha em
  `docs/01` §4.3 é atualizada.
- `POST /api/events` e `PATCH /api/events/<id>`: a validação do valor muda (valor a definir). Os
  papéis continuam os de hoje.
- A leitura do evento (a cobrança da aba Comercial) passa a somar o grupo (FR-003). Os papéis que veem
  a parte comercial continuam os de hoje.

## Verificação (`verify_299.py`) *(obrigatório — Princípio VIII)*

Arquivo: `specs/299-sem-valor-cobrancas/verify_299.py`, contra `manto_local` (`DATABASE_URL` de
`.local-db-url`, `FLASK_ENV=development`, `MANTO_SEM_THREADS=1`). Login só por
`POST /api/auth/login`; escrita conferida por conexão separada; limpeza no `finally`. Evento de teste
com "[TESTE verify 299] pode apagar" no título, e a chamada ao Google trocada por uma falsa (como na
298).

| # | Cenário | O que prova | Deve falhar? |
|---|---|---|---|
| 1 | Evento de maio sem valor e com saldo | fica fora das duas listas | não |
| 2 | Vazio, zero, R$ 0,01 e R$ 0,99 contra R$ 1,00; eventos a 7, 8 e 31 dias | os quatro primeiros entram em "sem valor" e R$ 1,00 não; 7 dias vermelho, 8 amarelo, 31 cinza | não |
| 3 | Cancelado, ensaio, cortesia, título com 🟧 e com 🟠, Loja Virtual | nenhum entra em "sem valor" | não |
| 4 | Grupo: principal com valor; principal sem valor; principal cortesia | outros eventos fora; uma linha do grupo; grupo fora | não |
| 5 | Valor a definir | cadastro com a marca cria sem valor e o evento entra na lista; sem valor e sem marca → 400 no campo; pôr o valor pela aba Comercial tira da lista | não |
| 6 | Evento sem valor na edição completa; orçamento num evento de R$ 0,01 | a edição salva o título; o orçamento é aplicado | não |
| 7 | Caso 344 (3.078 + 3.078 de 5.508) e grupo de 10.000 (2.000 + 3.000) | o 344 sai de Cobranças; o outro vira uma linha, "falta R$ 5.000,00" | não |
| 8 | Grupo com eventos em 20/06 e 21/06 | a data do grupo é 20/06 e o vencimento 18/06 | não |
| 9 | Vencimento | 2 dias antes; data combinada à vista; data combinada depois do evento; parcela | não |
| 10 | Centavos e sinal | saldo de R$ 0,50 fora; sinal R$ 0,50 abaixo da metade não é "Sinal pendente"; venda lançada hoje sem comprovante já é "Sinal pendente" | não |
| 11 | Metade paga e evento a 20 dias | aparece, com vencimento (hoje fica escondida) | não |
| 12 | R$ 0,01, cortesia com valor (dado antigo), Loja Virtual | nenhum em Cobranças | não |
| 13 | Conteúdo e cor da linha | cliente ou título, data do evento e vencimento; nenhum selo em inglês; vence em 2 dias vermelho, em 3 amarelo, em 31 cinza | não |
| 14 | Total do topo | das listas comerciais, só vermelhas e amarelas; painéis de operação como hoje; "R$ X em aberto" soma todas as cobranças | não |
| 15 | Página do evento no grupo | o principal soma o grupo (recebido, saldo, mensagem); o outro evento mostra o grupo e aponta o principal | não |
| 16 | CASTING abre a Home; FINANCEIRO tenta criar evento | sem bloco comercial; 403 | **sim** |
| 17 | Limpeza | eventos e comprovantes de teste apagados | — |

Conferência de tela:
- a Home no computador e no celular (375 × 812), com as duas listas, as cores, o estado vazio e
  "Mostrar todas";
- o cadastro com "Valor a definir";
- a aba Comercial com "A definir";
- a página do principal e a de outro evento de um grupo.

## Critérios de sucesso *(obrigatório)*

- **SC-001**: Depois do deploy, a lista "Evento sem valor de venda" mostra as vendas sem valor desde
  01/06 e nenhum compromisso interno. Em 14/09/2026 seriam 6, menos as que ganharem valor até lá.
- **SC-002**: Nenhum grupo aparece cobrando valor já pago em outro evento do grupo, e o grupo 344 sai
  de Cobranças.
- **SC-003**: Para todo grupo, a Home e a página do evento principal mostram o mesmo recebido e o
  mesmo saldo.
- **SC-004**: Nenhuma linha de cobrança nasce de diferença menor que R$ 1,00. Hoje são 5.
- **SC-005**: Toda venda com saldo de R$ 1,00 ou mais desde 01/06 aparece em Cobranças, com o
  vencimento. Hoje 25 ficam escondidas.
- **SC-006**: Nenhum texto em inglês nem código cru nas duas listas.
- **SC-007**: Da linha "sem valor" ao valor salvo em até 2 cliques, mais a digitação.
- **SC-008**: Nenhum evento novo de R$ 0,01 depois do deploy: quem não tem o preço usa "Valor a
  definir".
- **SC-009**: O total do topo não conta nenhuma linha cinza das listas comerciais, e os painéis de
  operação contam como antes.
- **SC-010**: A Home no celular (375 px) não tem rolagem horizontal.

## Fora de escopo

- **Limpeza única de dados**, à parte e com o OK do dono:
  - os 21 recebidos acima do valor, entre eles 85, 184, 288, 309, 319 e 344;
  - os 15 comprovantes antigos sem valor;
  - os 24 comprovantes lançados sem valor em maio e junho;
  - as datas impossíveis dos formulários.
- **Mover para o principal os comprovantes dos outros eventos do grupo.** A soma é na leitura.
- **Relatórios financeiros**: "a receber" do Financeiro, funil de vendas, indicadores, DRE, comissão
  e Auditoria de Input continuam contando por evento, e o R$ 0,01 segue contando como venda neles.
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

- `docs/01`: o contrato do bloco comercial de `GET /api/dashboard`, a validação do valor em
  `POST/PATCH /api/events`, a cobrança da leitura do evento e o §4.3.
- `docs/02`: a Home (painel Comercial com as duas listas e o total do topo), o cadastro e a edição
  com "Valor a definir", e a aba Comercial com "A definir" e a cobrança do grupo.
- `docs/03`: entrada no topo.
- `docs/04`: os invariantes. O grupo é uma venda só na cobrança; o que é "sem valor"; o marcador
  laranja do compromisso interno; o vencimento do saldo; a folga de centavos.
- `docs/05`:
  - a trava do sync;
  - "parcelado" contra "parcelado_datas";
  - a Auditoria de Input e o "a receber" do Financeiro, que seguem outra conta.
- `specs/051-task-venda-pendente/spec.md`: marcada como superada pela 299.

## Premissas

- **"Valor a definir" é o valor vazio.** Não há estado novo gravado; a marca no cadastro só evita o
  esquecimento.
- **Valor simbólico é abaixo de R$ 1,00**, e hoje só existe R$ 0,01. A folga de centavos usa o mesmo
  limite: diferença abaixo de R$ 1,00.
- **O corte é 01/06/2026**, o mesmo das cobranças e dos formulários. Em produção, o `release_date` é
  01/06/2026 (conferido em 14/09).
- **A política comercial não muda**: sinal de 50% no fechamento e saldo até 2 dias antes. A data
  combinada vale sobre os 2 dias antes.
- **Comprovante de outro evento do grupo que foi cancelado continua contando**, porque o dinheiro
  entrou. A devolução, se houve, é gasto.
- **Recebido acima do valor não gera aviso** nesta feature.
- **Comprovante antigo sem valor conta como R$ 0.**
- **Os limites de cor foram decididos pelo dono no `/speckit-clarify`**, e as duas listas usam réguas
  diferentes de propósito:
  - cobranças (FR-026): o vermelho segue o prazo da política, 2 dias;
  - sem valor (FR-009): a régua da 298, com vermelho até 7 dias, porque o valor precisa entrar logo.
- **Servidor e site sobem com cerca de 1 minuto de diferença**: os campos novos são opcionais na tela.
- **O modelo visual é o painel da 298**: dois grupos, 6 linhas, "Mostrar todas" e animação de saída.
