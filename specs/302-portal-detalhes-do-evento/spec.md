# Feature 302 — O artista passa a ver quando o evento termina, quando é o ensaio e de onde sai

**Branch**: `302-portal-detalhes-do-evento` (da `main`) · **Created**: 2026-09-22 ·
**Status**: Rascunho · **Migration**: nenhuma · **Nível**: 1 (feature)

**Input**: pedido do dono (ver abaixo).

## O pedido, nas palavras do dono *(obrigatório)*

> "No portal do artista não aparece o horário final do evento. E eu queria pensar contigo quais
> informações aparecem hoje para o artista para refinarmos. Ou adicionar mais coisas ou retirar
> coisas que não são pertinentes. Como por exemplo o horário de saída, horário de maquiagem,
> local de saída. Horário de ensaio, local de ensaio."

O pedido tem duas metades: uma falta pontual (o horário final) e um convite a revisar a tela
inteira. O levantamento respondeu as duas, e o dono decidiu o escopo numa rodada de perguntas
antes desta spec (as decisões estão em Premissas).

### O que o artista vê hoje, em ordem, no card do evento

Título · `sexta-feira, 28 de jul, 20:00 · Local` · `amanhã`/`em 5 dias` · `Personagem: X` ·
[aviso de alteração + botão **Ciente**] · [`Falta responder este convite`] · cachê (+ deslocamento,
+ PAGO/A RECEBER) · [`Ver ficha de figurino`] · [`Avaliar este evento`, só no histórico].

Não existe tela de detalhe: **o card é tudo o que há**.

### O que o levantamento achou

**O horário final já chega ao navegador e é descartado.** O servidor manda `end_at`, o tipo do
frontend declara o campo, e nenhuma tela o desenha. Os **475** eventos do espelho (é o acervo
inteiro: de 02/01/2026 a 30/07/2027, nenhum cancelado) e os **64**
futuros têm horário final gravado, com duração real variada (4h em 21 eventos futuros, 3h em 19,
1h em 9) — não é um "+1h" automático.

**O ensaio é invisível justamente para quem vai ensaiar.** Um ensaio é um evento próprio,
pendurado no show. São **54** no espelho, **todos** com data, hora e local; **10 no futuro**, 8
deles num show que já tem elenco escalado (15 vagas de artista). Mas o elenco fica no show, nunca
no ensaio: **nenhum dos 98 eventos de ensaio tem gente escalada**. Como o portal lista escalações,
o ensaio nunca aparece. E ele costuma cair **2 a 4 dias antes** do show (o ensaio de 30/09 é do
show de 03/10), o que faz dele a informação mais urgente que o artista não tem.

**Maquiagem e saída existem, mas pararam de ser preenchidas.** Os campos estão no evento e o
e-mail de convite já imprime as duas linhas. Nos 475 eventos do espelho: maquiagem em **19**,
saída em **24**. Nos **64** eventos futuros: **zero**. O hábito existiu de maio a agosto/2026 e
cessou. Mostrar esses campos sem mexer no processo interno não mudaria nada na prática — por isso
a feature também avisa a produção.

**A tela chama de "Personagem" quem não é personagem.** 289 das 731 escalações com talento são
Coordenador (144), Técnico de Som (64 + 35 de presença), Maquiador (23), Foto/Vídeo (17) e
Transporte (5) — **40%** —, e as três telas do portal escrevem `Personagem: Coordenador`.

**A Agenda repete o Histórico inteiro, sem limite.** Abaixo de "Próximos eventos" a Agenda desenha
**todas** as apresentações passadas da pessoa, como cards completos. O artista mais ativo do
espelho tem **75**; a média é 4,7. Existe uma aba Histórico com os mesmos itens e mais os totais.

**O e-mail de convite manda o código do banco.** O local de maquiagem é gravado como `manto` ou
`local` (18 e 2 ocorrências), e o e-mail concatena o valor cru: o artista recebe
`Maquiagem: 14:00 — manto`.

## Clarifications

### Session 2026-09-22

- Q: O bloco "Antes do evento" deve aparecer também no card de Convites, onde a pessoa decide se
  aceita? → A: **Sim, também nos convites.** Hoje há 4 convites pendentes em eventos futuros e
  **2 deles são de eventos que já têm ensaio marcado** — a pessoa aceita sem saber que vai ter de
  ensaiar. Mesma consulta, mesmo bloco.
- Q: A produção deve ser avisada quando marca ensaio para um evento que ainda não tem ninguém
  escalado? → A: **Não.** Marcar ensaio antes de escalar é ordem normal de trabalho; avisar
  viraria ruído. O aviso interno cobre só logística faltante.
- Q: A ficha de figurino recusa com 403, confirmando a um estranho que o evento existe, contra o
  Princípio XIII. Trocar para 404 agora? → A: **Não — registrar como dívida.** Trocar mudaria a
  mensagem que o artista lê hoje e não tem relação com o pedido; só quem tem sessão de artista
  alcança o endpoint.
- Q: O e-mail de convite e a mensagem de WhatsApp também escrevem "Personagem" para quem é
  Coordenador ou Técnico de Som. Consertar junto? → A: **Sim, as três superfícies.** O e-mail é o
  primeiro contato do artista com a escalação — consertar só o portal deixaria o defeito onde ele
  é mais lido.

## Cenários e Verificação *(obrigatório)*

### História 1 — O artista vê quando o evento termina (Prioridade: P1) 🎯 MVP

O artista abre a Agenda e o card diz `sexta-feira, 28 de jul, 20:00 às 23:00 · Local`. Ele sabe se
dá para marcar outro compromisso no mesmo dia sem perguntar a ninguém.

**Por que esta prioridade**: é o pedido literal do dono, vale sozinho e o dado já está no
navegador — nenhum outro requisito precisa existir para esta história entregar.

**Verificação**: cenários 1 e 4b do `verify_302.py` — o payload das três listas já traz início
**e** fim (e continua trazendo); quem exibe a faixa são a Agenda e os Convites, e isso se confere
na tela.

**Cenários de aceite**:

1. **Dado** um evento com início 20:00 e fim 23:00, **Quando** o artista abre a Agenda, **Então** o
   card mostra a faixa `20:00 às 23:00`.
2. **Dado** um evento sem horário final gravado, **Quando** o artista abre a Agenda, **Então** o
   card mostra só o horário de início, sem sobra de texto nem traço solto.
3. **Dado** o mesmo evento, **Quando** o artista abre a aba Convites, **Então** a faixa horária
   aparece do mesmo jeito que na Agenda. Na aba Histórico a linha continua mostrando só a data,
   como hoje.
4. **Dado** um evento que começa às 20:00 e termina à 00:00 **do dia seguinte**, **Quando** o
   artista abre o card, **Então** a faixa deixa claro que o fim é no outro dia — não fica
   `20:00 às 00:00`, que se lê como vinte horas de trabalho.

---

### História 2 — O artista descobre o ensaio pelo portal (Prioridade: P1)

O artista está escalado num show que tem ensaio marcado para três dias antes. Ele abre o card do
show, toca em **Antes do evento** e lê a data, a hora e o endereço do ensaio. Hoje ele só descobre por
WhatsApp, ou não descobre.

**Por que esta prioridade**: é a maior lacuna achada, o dado está 100% preenchido, e a informação
é a mais urgente das quatro — o ensaio acontece **antes** do evento.

**Verificação**: cenários 2, 3, 4c, 6c, 7, 11 e 12 do `verify_302.py`.

**Cenários de aceite**:

1. **Dado** um show com ensaio marcado e o artista escalado no show, **Quando** ele abre o card do
   show, **Então** encontra data, hora e local do ensaio no bloco de detalhes.
2. **Dado** um show com **dois** ensaios marcados, **Quando** ele abre o card, **Então** vê os
   dois — nenhum é escondido.
3. **Dado** um show já realizado, **Quando** ele olha o histórico, **Então** o ensaio **não**
   aparece: quem já se apresentou não precisa mais se preparar.
4. **Dado** um ensaio que não foi vinculado a nenhum show, **Quando** o artista abre a Agenda,
   **Então** esse ensaio não aparece em card nenhum.
5. **Dado** um convite pendente para um show que já tem ensaio marcado, **Quando** o artista abre
   a aba Convites, **Então** vê o ensaio **antes** de decidir se aceita — hoje ele aceita sem
   saber que vai ter de ensaiar, e é o caso de 2 dos 4 convites pendentes.
6. **Dado** um show de 3 de outubro cujo ensaio foi no dia 30 de setembro, **Quando** o artista
   abre o card no dia 1º de outubro, **Então** o ensaio já passado não ocupa mais o bloco de
   preparação.

---

### História 3 — O artista vê de onde sai, a que horas, e onde é a maquiagem (Prioridade: P2)

No mesmo bloco de detalhes, quando a produção preencheu, o artista lê `Saída 15:30 — Manto
Produções` e `Maquiagem 14:00 — Manto Produções`. O local vem escrito por extenso, nunca como
código.

**Por que esta prioridade**: o dado existe e já vai no e-mail, mas hoje está vazio em 100% dos
eventos futuros — o valor só se realiza junto com a História 4.

**Verificação**: cenários 4 e 5 do `verify_302.py`.

**Cenários de aceite**:

1. **Dado** um evento com saída e maquiagem preenchidas, **Quando** o artista abre o card,
   **Então** as duas linhas aparecem no bloco de detalhes.
2. **Dado** um evento em que o local da maquiagem foi escolhido como "Manto Produções", **Quando**
   o artista lê a linha, **Então** ela diz `Manto Produções` — nunca `manto`.
3. **Dado** um evento sem ensaio, sem maquiagem e sem saída, **Quando** o artista abre o card,
   **Então** **não existe** bloco de detalhes: o card fica do tamanho de hoje.
4. **Dado** que a produção muda o horário de saída depois do aceite, **Quando** o artista abre o
   portal, **Então** ele encontra o aviso de alteração que já existe hoje, dizendo o que mudou.
5. **Dado** um evento em que a produção **digitou um endereço** no local da maquiagem em vez de
   escolher um dos dois presets, **Quando** o artista abre o card, **Então** lê o endereço como
   foi escrito. (Hoje o banco só tem os dois presets — este é o valor que um dia vai existir e que
   ninguém teria testado.)

---

### História 4 — A produção descobre que deixou o elenco no escuro (Prioridade: P2)

Quem cuida do evento abre a página dele e é avisado, na própria seção de logística, que há gente
escalada e nem saída nem maquiagem definidas. O aviso apaga quando a logística é salva.

**Por que esta prioridade**: sem ela, as Histórias 3 mostra linha vazia para todo mundo. É o que
transforma a feature em mudança real em vez de campo bonito e vazio.

**Verificação**: cenário 13 do `verify_302.py` (o único que escreve — confere por conexão
separada).

**Cenários de aceite**:

1. **Dado** um evento futuro com pelo menos uma pessoa escalada e nenhuma logística preenchida,
   **Quando** alguém da produção abre a página do evento, **Então** vê o aviso.
2. **Dado** o mesmo evento, **Quando** a logística é salva, **Então** o aviso some.
3. **Dado** um evento futuro **sem** ninguém escalado, **Quando** alguém abre a página, **Então**
   não há aviso — não há quem avisar.
4. **Dado** um evento que já passou, **Quando** alguém abre a página, **Então** não há aviso.

---

### História 5 — A tela para de chamar todo mundo de personagem (Prioridade: P3)

Quem é Coordenador, Técnico de Som, Maquiador, Foto/Vídeo ou Transporte lê **Função:** no lugar de
**Personagem:**, nas três telas onde a linha aparece.

**Por que esta prioridade**: atinge 40% das escalações e é correção de texto, mas não impede
ninguém de trabalhar. Cresceu por decisão do dono: vale também para o **e-mail de convite** e a
**mensagem de WhatsApp**, que são o que o artista lê primeiro.

**Verificação**: cenários 6 e 6b do `verify_302.py`.

**Cenários de aceite**:

1. **Dado** uma escalação de personagem, **Quando** o artista abre qualquer das três telas,
   **Então** lê `Personagem: <nome>`.
2. **Dado** uma escalação de Coordenador, **Quando** ele abre qualquer das três telas, **Então**
   lê `Função: Coordenador`.
3. **Dado** a mesma escalação, **Quando** o casting envia o e-mail de convite ou copia a mensagem
   de WhatsApp, **Então** as duas também dizem `Função`, e a mensagem de WhatsApp para de
   escrever `Local: manto`.

---

### História 6 — A Agenda deixa de repetir o histórico inteiro (Prioridade: P3)

A Agenda passa a ser só "Próximos eventos". Quem quer o passado abre a aba Histórico, que já tem
os mesmos itens, os totais e o contador de eventos a avaliar.

**Por que esta prioridade**: melhora a leitura para todo mundo e muito para quem tem muitas
apresentações, mas não desbloqueia nada.

**Isto desfaz metade da feature 229**, de propósito. A 229 pôs o link de avaliar também na seção
Histórico da Agenda porque *"as duas listas se chamam Histórico, então ela não tinha por que
procurar a segunda"*. A causa era a **duplicação de nome**; esta feature ataca a causa em vez do
sintoma: com uma lista só chamada Histórico, o contador vermelho na barra inferior volta a ser
caminho não-ambíguo. O link continua existindo na aba Histórico. A reversão tem de ir por escrito
em `docs/03`, referenciando a 229, e a promessa correspondente sai da linha do `docs/02`.

**Verificação**: cenário 8 do `verify_302.py` + conferência de tela.

**Cenários de aceite**:

1. **Dado** um artista com 75 apresentações passadas, **Quando** ele abre a Agenda, **Então** vê
   apenas os próximos eventos.
2. **Dado** o mesmo artista, **Quando** ele abre a aba Histórico, **Então** encontra as 75, com os
   totais de recebido e a receber.
3. **Dado** um evento passado ainda não avaliado, **Quando** ele olha a barra inferior, **Então**
   o contador da aba Histórico continua apontando que há avaliação pendente.

---

### História 7 — A ficha de figurino diz de que evento é (Prioridade: P3)

O artista abre a ficha e lê, no topo, o nome e a data do evento. Hoje a ficha abre sem nenhuma
referência — quem tem duas escalações na semana não sabe qual está vendo.

**Por que esta prioridade**: vão pequeno, correção barata, mas fora do pedido original.

**Verificação**: conferência de tela (não há mudança de regra a provar por API além do horário
final no payload da ficha).

**Cenários de aceite**:

1. **Dado** um artista com ficha de figurino num evento, **Quando** ele abre a ficha, **Então** lê
   o nome do evento e a data no topo.

---

### Casos de borda

- **Evento sem nada preenchido** (sem ensaio, sem maquiagem, sem saída): o bloco de detalhes não
  existe. É o caso da maioria hoje, e é o que mantém o card enxuto.
- **Ensaio sem show**: ensaio não vinculado a nenhum evento não aparece para ninguém. São 44 no
  espelho, **nenhum deles futuro** — o vínculo está sendo feito hoje. Se voltar a falhar, o artista
  deixa de ver o ensaio em silêncio; o cenário 12 existe para que essa falha tenha nome.
- **Ensaio em show sem elenco**: dos 10 ensaios futuros, 2 estão em shows sem ninguém escalado —
  ninguém os verá, e está certo assim. Marcar ensaio antes de escalar é ordem normal de trabalho,
  e o aviso interno **não** cobre esse caso (decisão do dono, ver Clarifications).
- **Local da maquiagem escolhido como o preset "local"**: para o artista, a linha diz
  **"No local do evento"** (FR-007). O formulário interno segue chamando a opção de "Local do
  evento" — é texto de `<select>` para quem preenche, e não se mexe nele. A linha precisa dizer algo que o artista
  entenda sem abrir outra tela, já que o endereço do evento está no próprio card.
- **Mudança depois do aceite — e a armadilha do PRIMEIRO preenchimento.** Quando a produção
  **altera** maquiagem, saída ou o horário final, o aviso com o botão **Ciente** já dispara hoje, e
  tem de continuar disparando. Mas quando ela preenche pela **primeira vez** — que é exatamente o
  caso que esta feature cria, porque nenhum dos 64 eventos futuros tem logística — o sistema fica
  **calado**: o aviso só nasce quando o valor anterior existia. O artista descobre na próxima vez
  que abrir o portal, sem ser avisado. Está fora do escopo desta entrega, e está aqui escrito para
  ninguém prometer o contrário.
- **Logística pela metade**: o campo de local de saída já vem preenchido com "Manto Produções" no
  formulário interno, então há 7 eventos com local e **sem** horário (e 1 assim na maquiagem).
  Nesses casos não nasce linha nenhuma (FR-006a).
- **Evento cancelado**: continua fora do portal, com ensaio e tudo.
- **Escalação recusada**: continua fora, como hoje.
- **Evento que deixa de ser show**: ao trocar o tipo, o sistema apaga os ensaios pendurados. Hoje
  isso é invisível; com a feature, o bloco do artista some sem aviso. Não é regressão desta
  entrega — é comportamento existente que passa a ter consequência visível, e por isso precisa
  ficar escrito.
- **Ensaio marcado depois do aceite**: marcar ensaio **não** dispara o aviso de alteração hoje
  (diferente de mexer em maquiagem, saída ou horário, que disparam). O artista vê o ensaio na
  próxima vez que abrir o portal, sem ser avisado. Fora de escopo desta entrega, registrado.

## Requisitos *(obrigatório)*

### Requisitos funcionais

- **FR-001**: O portal DEVE mostrar o horário de término junto do horário de início **em toda tela
  que já mostra o horário de início** — hoje, Agenda e Convites. O Histórico mostra só a data
  (`28/07/2026 · Local`), sem hora nenhuma: lá não há "horário final faltando", e acrescentar a
  faixa significaria acrescentar também o **início**, que ninguém pediu e que o evento já passado
  não ajuda a preparar. O Histórico mantém o formato compacto.
- **FR-002**: Quando o evento não tiver horário de término, o portal DEVE mostrar apenas o início,
  sem rótulo, traço ou espaço órfão.
- **FR-002a**: Quando o evento **terminar em outro dia**, a faixa DEVE deixar isso explícito — não
  basta `20:00 às 00:00`, que se lê como evento de vinte horas. São 34 eventos assim no espelho,
  4 deles futuros (o mais próximo é 24/10/2026, das 20:00 às 00:00), e nenhum tem elenco ainda
  porque o casting fecha perto da data: é um defeito que **não aparece hoje e aparece sozinho**.
- **FR-003**: O portal DEVE mostrar, para cada evento futuro ou com convite pendente, os ensaios
  marcados para aquele evento, com data, horário e local de cada um.
- **FR-004**: O portal DEVE mostrar **todos** os ensaios do evento, não apenas o primeiro.
- **FR-004a**: O ensaio que **já aconteceu** NÃO DEVE continuar ocupando o bloco de preparação de
  um evento que ainda vai acontecer. Essa janela existe **sempre**, por construção: o ensaio cai 2
  a 4 dias antes do show, então todo show passa por um período em que o ensaio é passado e ele é
  futuro.
- **FR-005**: O portal NÃO DEVE mostrar ensaio nos itens do histórico.
- **FR-006**: O portal DEVE mostrar o horário e o local de saída, e o horário e o local da
  maquiagem, quando a produção os tiver preenchido.
- **FR-006a**: O que decide se a linha existe é o **horário**, não o local. Local sem horário é
  resíduo do formulário interno — o campo de local de saída já nasce preenchido com "Manto
  Produções", e 7 eventos do espelho têm esse local sem horário nenhum (mais 1 na maquiagem).
  Mostrar "Saída: Manto Produções" sem hora é ruído que se parece com informação.
- **FR-007**: O local da maquiagem DEVE ser apresentado ao artista em linguagem corrente
  (`Manto Produções`, `No local do evento` ou o endereço escrito pela produção), nunca como o
  código guardado no sistema.
- **FR-008**: A mesma tradução DEVE valer para o e-mail de convite, que hoje envia o código —
  uma fonte só, para as duas saídas nunca divergirem.
- **FR-009**: As informações de ensaio, maquiagem e saída DEVEM ficar num bloco secundário do
  card, chamado **Antes do evento**, recolhido por padrão, e o bloco NÃO DEVE existir quando não
  houver nenhuma delas.
- **FR-009a**: O mesmo bloco DEVE aparecer no card de **Convites**, onde a pessoa decide se
  aceita: hoje 2 dos 4 convites pendentes são de eventos que já têm ensaio marcado, e a pessoa
  aceita sem saber disso.
- **FR-009b**: O bloco NÃO DEVE aparecer nos itens do histórico — preparação é para o que ainda
  vai acontecer.
- **FR-009c**: Dentro do bloco, os itens DEVEM aparecer na **ordem cronológica real** — ensaio
  (dias antes), maquiagem, saída —, que é a sequência em que a pessoa vai vivê-los. Qualquer outra
  ordem obriga quem lê a remontar a sequência de cabeça, que é o trabalho que a feature quer
  poupar.
- **FR-009d**: O bloco tem **um** nome visível na tela e o texto DEVE ser o mesmo em toda a
  feature — "Antes do evento" é o nome do bloco **e** o rótulo do controle que o abre. Não há
  segundo nome.
- **FR-009e**: O controle que abre o bloco DEVE ter alvo de toque de no mínimo 44px e rótulo que
  um leitor de tela consiga anunciar (o que abre, e se está aberto ou fechado). O bloco, aberto,
  NÃO DEVE empurrar o cachê para fora da primeira tela em 375×812.
- **FR-010**: Nenhuma tela nova e nenhum endereço novo de navegação DEVEM ser criados para isso.
- **FR-011**: O portal DEVE rotular a linha da escalação como **Função** quando a vaga não for de
  personagem, e como **Personagem** quando for, nas três telas em que a linha aparece.
- **FR-012**: A decisão de qual rótulo usar DEVE vir do servidor — a tela não deduz a natureza da
  vaga a partir do nome dela.
- **FR-012a**: O **e-mail de convite** e a **mensagem de WhatsApp** copiada pelo casting DEVEM
  usar o mesmo critério: são as duas superfícies que o artista lê **antes** do portal, e hoje as
  duas escrevem "Personagem: Coordenador".
- **FR-012b**: A mensagem de WhatsApp DEVE também parar de imprimir o código do local de
  maquiagem — hoje ela manda `Local: manto`, o mesmo defeito do e-mail (FR-007/FR-008), na
  terceira superfície.
- **FR-013**: A tela Agenda NÃO DEVE mais listar as apresentações passadas; a aba Histórico
  continua sendo o lugar delas, com os totais e o contador de avaliações pendentes intactos.
- **FR-013a**: O servidor DEVE continuar entregando a lista de passados na Agenda **nesta
  entrega**, mesmo com a tela não a usando. O site e a API são dois serviços que sobem separados:
  há uma janela de servidor novo com tela velha, e a tela velha quebra em branco se a lista
  sumir. Parar de entregá-la é passo do ciclo seguinte, registrado como dívida.
- **FR-013b**: Pela mesma razão, ao contrário: a tela DEVE tolerar a ausência dos campos novos —
  na janela de tela nova com servidor velho, o card se comporta como hoje em vez de quebrar.
- **FR-014**: A ficha de figurino DEVE mostrar o nome e a data do evento a que pertence.
- **FR-015**: A página interna do evento DEVE avisar quem cuida do evento quando houver pelo menos
  uma pessoa escalada, o evento ainda não tiver acontecido e nem saída nem maquiagem estiverem
  preenchidas; o aviso DEVE desaparecer assim que a logística for salva.
- **FR-016**: Nenhuma mudança DEVE alterar quem pode ver o quê: o portal continua entregando
  apenas dados da pessoa autenticada, e as permissões internas ficam como estão.

### Entidades *(se houver dados)*

Nenhuma entidade nova e **nenhuma migration**. A feature usa o que já existe:

- **Evento** (`CalendarEvent`): `end_at`, `makeup_time`, `makeup_location`, `departure_time`,
  `departure_location` e o vínculo `parent_event_id` que liga o ensaio ao show.
- **Escalação** (`EventRole`): `role_type` (`character` | `extra`), que decide o rótulo.
- **Ensaio**: é um Evento com tipo `ENSAIO` apontando para o show pelo `parent_event_id`. O
  horário é o do ensaio, o local é o do ensaio.

### RBAC *(obrigatório se houver endpoint novo ou alterado)*

**Nenhum endpoint novo e nenhum portão alterado.** Três endpoints existentes mudam de payload:

- `GET /api/portal/agenda` — portão inalterado: talento autenticado, "é o dono do recurso"
  (Princípio XIII). **Só ganha campos** — nenhuma chave sai, inclusive a lista de passados, que
  continua sendo entregue mesmo com a tela parando de usá-la (FR-013a).
- `GET /api/portal/historico` — portão inalterado. Ganha os mesmos campos de rótulo e horário.
- `GET /api/portal/events/<id>/figurino` — portão inalterado e **payload inalterado**: `title` e
  `start_at` já saem, e a tela é que não os desenha. O módulo ganha a declaração de RBAC de topo
  que hoje **falta** — é o único dos cinco módulos do portal sem ela.

O aviso interno (FR-015) é calculado a partir de dados que a página do evento já entrega a quem
já pode abri-la — não cria endpoint nem afrouxa portão.

## Verificação (`verify_302.py`) *(obrigatório — Princípio VIII)*

Arquivo: `specs/302-portal-detalhes-do-evento/verify_302.py`, contra `manto_local`
(`DATABASE_URL` de `.local-db-url`, `FLASK_ENV=development`, `MANTO_SEM_THREADS=1`). Login só por
`POST /api/portal/auth/login` (portal) e `POST /api/auth/login` (interno); escrita conferida por
conexão separada; limpeza no `finally`.

| # | Cenário | O que prova | Deve falhar? |
|---|---|---|---|
| 1 | Evento com início e fim | o payload das três listas traz os dois horários (FR-001) | não |
| 2 | Show com um ensaio | o bloco traz data, hora e local do ensaio (FR-003) | não |
| 3 | Show com **dois** ensaios | a lista traz os dois — prova que não foi limitado a um (FR-004) | não |
| 4 | Evento sem ensaio, sem maquiagem e sem saída | o bloco de detalhes vem vazio/ausente (FR-009) | não |
| 4b | Evento que termina no dia seguinte | a faixa horária deixa o outro dia explícito (FR-002a) | não |
| 4c | Show futuro cujo ensaio já aconteceu | o ensaio passado não vem no bloco (FR-004a) | não |
| 5 | Local da maquiagem gravado como `manto` | o payload devolve `Manto Produções`, nunca o código (FR-007) | não |
| 5b | Local da maquiagem com endereço digitado à mão | o payload devolve o endereço como escrito (FR-007) | não |
| 6 | Escalação de Coordenador | o payload diz que a vaga não é de personagem (FR-011/FR-012) | não |
| 6b | Corpo do e-mail de convite de um Coordenador | diz "Função", não "Personagem", e o local da maquiagem sai traduzido (FR-012a) | não |
| 6c | Convite pendente num evento com ensaio | o item de convites pendentes traz o bloco de preparação (FR-009a) | não |
| 7 | Show passado com ensaio | o item do histórico **não** traz ensaio (FR-005) | não |
| 8 | Agenda × Histórico | o Histórico continua trazendo todos os passados com os totais intactos, **e** a Agenda continua entregando a lista de passados no payload (FR-013a — a tela é que para de usá-la; quem prova o sumiço da seção é a conferência de tela) | não |
| 8b | Local de saída preenchido e horário vazio | não vira linha nenhuma no bloco (FR-006a) | não |
| 9 | Talento A pede a agenda | não recebe escalação, ensaio, cachê nem logística do talento B | **sim** |
| 9b | Requisição **sem sessão** a `GET /api/portal/agenda` e à ficha de figurino | 401 nas duas — o portão é o que sustenta todo o resto | **sim** |
| 10 | Talento pede ficha de figurino de evento em que não está escalado | continua recusado | **sim** |
| 11 | Evento cancelado com ensaio | continua fora da agenda | não |
| 12 | Ensaio sem vínculo com show | não aparece em card nenhum (caso de borda) | não |
| 13 | Evento futuro com elenco e sem logística | o aviso interno acende; salva a logística e ele apaga (FR-015) — **conferido por conexão separada** | não |
| 13b | Contagem de consultas da agenda com 3 e com 5 escalações | o número **não cresce** com o número de escalações — o bloco custa uma consulta para a agenda inteira | não |
| 14 | limpeza | descartáveis apagados (`roles.clear()` antes do usuário) **e eventos reais do espelho restaurados** — a vaga assumida volta a `talent_id` nulo e os campos de logística ao valor original. Este verify toca linha de produção, não só linha criada por ele | — |

**Os dois pontos em que este verify passa verde sem testar nada** — ambos obrigatórios de tratar:

1. **Cenário 13** escreve a logística. `save_logistics` comita, mas conferir pela sessão do app
   encontra o valor no autoflush mesmo se o commit sumir numa refatoração. **Conexão separada** —
   é literalmente o defeito do hotfix 257.
2. **Cenário 3** precisa de **arranjo próprio**: o caso de dois ensaios existe no espelho, mas é
   **um único show** (52 pais têm um ensaio, 1 tem dois). Depender dessa linha é depender de dado
   de produção que pode sumir; o cenário semeia os dois ensaios. Sem isso, a asserção "traz os
   dois" passa com um item e não prova nada.

**Semear ensaio é escrita direta no banco, nunca pelo endpoint.** `POST /api/events/<id>/ensaios`
cria o evento **no Google Agenda da empresa** — as travas de ambiente cobrem e-mail e convite, não
isto. O cenário insere o evento-filho direto, com `google_event_id` descartável, e apaga no
`finally`.

**Nunca semear `EventRole` com `character_name` inventado** — o sync do Google apaga a role e manda
e-mail de remoção para gente de verdade. Assumir role existente com `talent_id IS NULL`.

**Conferência de tela** (obrigatória, `tsc` limpo não prova card): portal em **viewport mobile
375×812**, logado como um talento que tenha um evento futuro **com ensaio** — Agenda (faixa
horária, bloco de detalhes recolhido, ausência da seção Histórico), Convites (**com o bloco**,
FR-009a), Histórico (rótulo de função, sem bloco) e ficha de figurino (nome e data do evento). E a
página interna de um evento futuro com elenco e sem logística, para ver o aviso, mais a mensagem
de convite copiada de um cargo, para ver "Função" e o local traduzido.

## Critérios de sucesso *(obrigatório)*

- **SC-001**: O artista descobre a que horas o evento termina sem perguntar a ninguém — hoje isso
  é impossível pelo portal, em 100% dos eventos.
- **SC-002**: O artista escalado num show com ensaio marcado encontra data, hora e local do ensaio
  no portal. Hoje encontra em 0% dos casos; com a feature, nos **8** ensaios futuros do espelho cujo
  show tem elenco.
- **SC-003**: Um artista sem ensaio e sem logística vê o card do mesmo tamanho de hoje — a adição
  não cobra nada de quem não tem o que ler.
- **SC-004**: Nenhum artista lê `manto` como local — nem na tela, nem no e-mail de convite, nem na
  mensagem de WhatsApp.
- **SC-005**: Nenhuma das 289 escalações que não são de personagem é chamada de "Personagem", em
  nenhuma das três superfícies que o artista lê (portal, e-mail de convite, WhatsApp).
- **SC-005a**: Quem recebe um convite para um evento que já tem ensaio marcado consegue ver isso
  **antes** de aceitar — hoje, em 2 dos 4 convites pendentes, não consegue.
- **SC-006**: A Agenda mostra apenas os próximos eventos; o artista com 75 apresentações passadas
  deixa de rolar 75 cards para chegar ao fim da tela, e continua encontrando as 75 na aba
  Histórico.
- **SC-007**: Quem cuida de um evento futuro com elenco escalado e sem logística é avisado disso
  ao abrir a página do evento — hoje, em 11 eventos, ninguém é.
- **SC-008**: Nenhum artista passa a ver dado de outro artista: as consultas do portal continuam
  partindo do talento da sessão.
- **SC-009**: A Agenda não fica mais lenta por causa da informação nova: o trabalho do servidor
  **não cresce com o número de escalações** da pessoa. Conferível sem abrir código — a contagem de
  consultas de uma agenda com 3 escalações tem de ser igual à de uma com 5.

## Fora de escopo

- **Tela de detalhe do evento no portal** e qualquer endereço novo de navegação — decisão do dono:
  o bloco fica dentro do card.
- **Horário de chegada, ponto de encontro, call time, briefing e horário individual por talento** —
  não existem no sistema; criá-los é outra feature, com migration.
- **A observação do ensaio**: o campo existe, mas hoje guarda endereço (23 dos 40 seguem o padrão
  automático "Evento em: <local do show>", e os outros 17 também são endereços). Mostrá-la poria um
  segundo endereço, às vezes o do show, dentro do bloco do ensaio.
- **Escalar o elenco no próprio ensaio** — mudaria o modelo de convites e pagamento; o ensaio
  continua sendo informação do show.
- **Notificação empurrada (sino/e-mail) para a logística faltante** — o aviso desta feature é
  passivo, na página do evento. Empurrar exige um gatilho ("quando?") e é decisão à parte.
- **Contato da produção, descrição do evento e endereço estruturado** no portal — não pedidos.
- **Mexer no formulário interno de logística** além do aviso: os campos e o fluxo de salvar ficam
  como estão.
- **Parar de entregar a lista de passados no payload da Agenda** — proibido nesta entrega
  (FR-013a); é passo do ciclo seguinte.
- **Avisar o elenco quando um ensaio é marcado** — marcar ensaio não dispara o aviso de alteração
  hoje. Candidato a correção posterior.
- **Consertar a cópia de formatador de horário do app interno** — refatoração lateral; vira dívida
  registrada.
- **Trocar o 403 da ficha de figurino por 404** — decisão do dono: vira dívida registrada, não
  mudança silenciosa de mensagem.
- **Acrescentar o bloco de Saída à mensagem de WhatsApp** — a mensagem tem Maquiagem e não tem
  Saída. Esta entrega corrige o que a mensagem **escreve errado** (rótulo e código de local), não
  o que ela deixa de dizer.

## Docs a atualizar

`docs/01` — contrato de `GET /api/portal/agenda` e de `GET /api/portal/events/<id>/figurino`.

`docs/02` §C — linhas `/portal/agenda` (a seção Histórico sai; **desfazer a promessa do link de
avaliar herdada da 229**), `/portal/convites` (ganha o bloco de preparação), `/portal/historico` e
`/portal/eventos/:id/figurino`; e a seção do detalhe de evento interno (o aviso de logística e a
mensagem de convite copiada).

`docs/03` — entrada nova no topo + linha na tabela do índice, referenciando a **229** (o link de
avaliar) e a **230** (a lista não-recusada), porque correção é entrada nova, nunca edição da
antiga.

`docs/05` — as dívidas que esta entrega cria ou nomeia:
1. parar de entregar a lista de passados na Agenda, um ciclo de deploy depois (FR-013a);
2. a observação do ensaio, a reabrir quando o campo for usado como observação e não como endereço;
3. a tradução do local de maquiagem existindo em Python e em TypeScript;
4. a ficha de figurino recusando com 403 onde o Princípio XIII manda 404;
5. o formatador de horário duplicado entre o portal e o app interno;
6. marcar ensaio não avisar o elenco;
7. o **primeiro** preenchimento de logística não disparar o aviso de alteração (só a mudança de um
   valor que já existia dispara) — ver Casos de borda;
8. a documentação que ainda descreve um portal Jinja que não existe mais: `docs/02` §C.1 lista as
   rotas como registradas, `docs/04` §5 dá o arquivo como tendo 974 linhas (tem 82), e cinco
   docstrings do portal citam a "view Jinja legada".

`docs/00` e `docs/04` não mudam: nem topologia, nem RBAC, nem invariante de domínio.

## Premissas

Decisões do dono, tomadas numa rodada de perguntas antes desta spec:

1. O horário final vai na **linha principal** do card, junto do início — é o pedido literal e não
   pode ficar escondido atrás de um toque.
2. Ensaio, maquiagem e saída vão num **bloco secundário** — "como descrição ou mais detalhes",
   nas palavras do dono; o nome na tela é **Antes do evento** —, dentro do card, "para
   não ficar poluído". Sem tela nova.
3. "Personagem" vira "Função" para vaga que não é de personagem.
4. O bloco Histórico **sai** da Agenda.
5. A ficha de figurino passa a mostrar nome e data do evento.
6. Maquiagem/saída: expor no portal **e** avisar a produção quando faltarem.

Premissas técnicas assumidas onde o pedido não disse:

7. **A maquiagem é mostrada a todo o elenco**, não só a quem tem a marca de "precisa de
   maquiagem": essa marca está preenchida em 27 de 731 escalações, e usá-la como filtro esconderia
   a informação de quase todos. É também o que o e-mail de convite já faz.
8. **O ensaio aparece em convites pendentes e eventos futuros**, não no histórico — preparação é
   para o que ainda vai acontecer.
9. **A tradução do local da maquiagem mora no servidor.** O payload carrega a frase pronta; a tela
   não interpreta código.
10. O efeito visível no dia da publicação é pequeno: hoje só **9 talentos** têm escalação futura no
    espelho, porque o casting fecha perto da data. O ganho cresce com o calendário.

11. **A linha de maquiagem mostra "Manto Produções" sem o endereço**, por simetria com a linha de
    saída, que também mostra só o nome. Anexar o endereço só na maquiagem faria as duas parecerem
    lugares diferentes, quando são o mesmo. O ensaio continua mostrando endereço completo porque
    é o que está gravado nele. É ajuste de uma linha se o dono quiser o contrário.

**Ponto de conformidade registrado como dívida, não corrigido aqui** (decisão do dono): o pedido
de ficha de figurino de um evento em que o talento não está escalado é recusado com **403** e a
mensagem "Você não está escalado neste evento", o que confirma a um estranho que o evento existe;
o Princípio XIII manda **404**. Trocar mudaria o texto que o artista lê hoje e não tem relação com
o pedido, e só quem tem sessão de artista alcança o endpoint. Vai para `docs/05` com o motivo.
