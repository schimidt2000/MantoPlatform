# Feature 339 — Mudança no evento avisa o Casting, e o teto do cachê acompanha

**Branch**: `339-evento-mudou-avisa-casting` (da `main`, worktree `C:\tmp\mp339`) · **Created**: 2026-11-09 ·
**Status**: Rascunho · **Migration**: aditiva (teto autorizado da vaga + "Ciente" por pessoa; desenho no
plano) · **Nível**: 1 (feature) — mais de um domínio (agenda/sync, casting, notificações) e migration

**Input**: pedido do dono, conversa de 09/11/2026, com o evento 1423 como caso real.

## O pedido, nas palavras do dono *(obrigatório)*

> "Um evento foi mudado […] Star Wars. Ele foi mudado para show. E isso acarreta em várias coisas,
> porque ele precisa de ensaio, os cachês mudam e tudo muda. Qual que é o problema? Ele foi mudado
> para show, porém, o limite de valores continuou sendo o mesmo e não teve um aviso explícito para o
> casting mexer nesse evento, porque precisa consultar a disponibilidade das pessoas, se elas estão
> disponíveis para ensaio."

> "Os valores, depois que eu defino — o superadmin foi lá e definiu um valor com 400 —, esse deve ser
> um novo teto a partir de agora. […] Ele trocou a pessoa que estava num personagem. Aí acabou
> perdendo o valor que estava antes. E aí ele não conseguiu colocar 400 de novo."

> "Diminuiu o número de personagens no evento. Na agenda está certo o nome, porém no sistema não está.
> Eu precisei clicar manualmente para remover a vaga. […] Se sumir algum nome da agenda, o que a gente
> tem que fazer é alertar o casting: precisa dispensar alguém nesse evento, essa vaga não existe mais."

> (depois da primeira versão da spec) "O Stormtrooper já foi retirado da agenda, e eu já retirei ele da
> produção ali no cachê. Por que que no título ainda tem dois Stormtroopers? Isso também precisa ser
> resolvido."

**O que aconteceu no evento 1423** (sexta 13/11, 15h–19h, "STORMTROOPERS + STORMTROOPERS + DARTH VADER
+ ANAKIN + LUKE + YODA + PRINCESA LEIA", criado pela plataforma, ligado ao orçamento #2757 de R&I):

1. A Comercial trocou o tipo de R&I para SHOW. O sistema criou as vagas de som e ligou "precisa ensaio",
   e mais nada: o teto das vagas ficou em R$ 325 (base 3h R$ 275 + noturno R$ 50, preço de receptivo) e
   ninguém do Casting nem do Ensaio foi avisado. A Comercial fez um orçamento novo do show (#2898: 6
   personagens, 4 cantores) e mudou a venda, mas o evento continuou ligado ao #2757 — e, mesmo trocando
   o vínculo, o sistema hoje não sobe teto que já existe.
2. O Superadmin salvou R$ 400 nas 7 vagas. O valor só valia como teto porque estava no cachê **da
   pessoa**; quando o Casting trocou o Darth Vader de artista, o cachê zerou, o teto voltou a R$ 325 e o
   artista novo entrou com R$ 0. O Superadmin teve de salvar os R$ 400 de novo.
3. O cliente passou de dois Stormtroopers para um. Em evento criado pela plataforma o sync do Google não
   olha as vagas; e mesmo em evento vindo do Google ele só confere se o nome aparece no título, não
   quantas vezes. A vaga a mais ficou até o Superadmin removê-la à mão.
4. Removida a vaga, o título continuou com dois STORMTROOPERS — no sistema, no Google Agenda (o sync
   das 19h43 de 09/11 leu os dois) e no ensaio marcado logo depois, que copia o título do evento.
   Remover vaga nunca alterou o título.

## Decisões do dono (09/11/2026)

| # | Pergunta | Decisão |
|---|---|---|
| D1 | De onde sai o teto novo quando o evento vira SHOW | **Tabela + orçamento**: recalcula sozinho pelo preço de show do mesmo perfil; se a Comercial vincular o orçamento novo do show, valem os tetos dele. Nunca abaixo do que o Superadmin autorizou |
| D2 | Cachê de quem já está escalado quando vira SHOW | **O Casting revisa**: o cachê não muda sozinho; o aviso lista quem está escalado e precisa ser revisto (cachê e disponibilidade para o ensaio) |
| D3 | Vaga a mais quando o título tem menos personagens | **Vazia sai, ocupada avisa**: vaga vazia daquele personagem sai sozinha (com histórico); se todas têm gente, nenhuma sai — o Casting é avisado para tirar alguém da escala |
| D4 | Como o aviso aparece | **Sino + faixa no evento até "Ciente"**, e o "Ciente" é **por pessoa**: o Matheus clicar não some para o Diogo, e vice-versa. Quando vira SHOW, o Ensaio também recebe |
| D5 | Valor que o Superadmin salva acima do teto | Vira o **teto da vaga** e não se perde quando a pessoa da vaga muda |

## Clarifications

### Session 2026-11-09

- Q: Num evento vindo do Google, quando um personagem some por inteiro do título e a vaga dele tem
  artista escalado, o que o sync faz com a vaga? → A: Marca e avisa — a vaga fica, ninguém recebe
  e-mail, e o Casting tira a pessoa da escala (mesma regra da vaga a mais; FR-023).
- Q: Os Superadmins também recebem os avisos (sino + faixa, com "Ciente" próprio)? → A: Sim — Casting,
  Ensaio (troca de tipo com SHOW) e Superadmin; quem fez a mudança não recebe o próprio aviso (FR-012,
  FR-020, FR-033).

## Cenários e Verificação *(obrigatório)*

### História 1 — Valor autorizado pelo Superadmin vira o teto da vaga (Prioridade: P1)

O Superadmin salva um cachê acima do teto numa vaga. A partir daí esse valor é o teto daquela vaga: se
o Casting tira a pessoa e escala outra, consegue salvar o mesmo valor de novo sem pedir ao Superadmin.

**Por que esta prioridade**: é o bloqueio que parou o Casting no dia (artista entrou com R$ 0) e é a
peça que as outras histórias usam ("nunca abaixo do autorizado").

**Verificação**: cenários 1–4 do `verify_339.py`.

**Cenários de aceite**:

1. **Dado** uma vaga com teto R$ 325 e um artista escalado, **Quando** o Superadmin salva R$ 400,
   **Então** a vaga passa a ter teto autorizado R$ 400, com quem autorizou e quando no histórico.
2. **Dado** essa vaga, **Quando** o Casting tira o artista e escala outro com R$ 400, **Então** o valor
   salvo é R$ 400 (não volta para R$ 325) e o log não diz "acima do cap — autorizado pelo admin".
3. **Dado** essa vaga, **Quando** o Casting tenta R$ 450, **Então** o valor volta para R$ 400 e a tela
   avisa que passou do limite, como hoje.
4. **Dado** um teto autorizado de R$ 4.000 salvo por engano, **Quando** o Superadmin salva R$ 400 na
   mesma vaga, **Então** o teto autorizado passa a ser R$ 400 (o último valor do Superadmin manda).

---

### História 2 — Virar SHOW sobe os tetos e avisa Casting e Ensaio (Prioridade: P1)

A Comercial troca o tipo de um evento para SHOW. Além do que já acontece (vagas de som, "precisa
ensaio"), o teto de cada vaga é recalculado pelo preço de show do mesmo perfil, e cada pessoa do Casting,
do Ensaio e Superadmin recebe um aviso no sino e vê, no evento, uma faixa dizendo o que mudou, quem está escalado
com cachê a rever e que é preciso confirmar a disponibilidade para o ensaio.

**Por que esta prioridade**: é o problema central do pedido — o evento mudou e ninguém que escala ficou
sabendo, e o teto impedia pagar o cachê de show.

**Verificação**: cenários 5–9 do `verify_339.py`.

**Cenários de aceite**:

1. **Dado** um evento R&I ligado a um orçamento sem show, com vagas de boneco e de cara-limpa e teto
   de receptivo, **Quando** a Comercial troca o tipo para SHOW, **Então** cada vaga desse orçamento
   ganha o teto da mesma conta com show (mesmo perfil, mesma duração, mesmos adicionais), e o histórico
   do evento registra os tetos antigo e novo.
2. **Dado** uma vaga com teto autorizado pelo Superadmin acima do teto de show recalculado, **Quando**
   o evento vira SHOW, **Então** o teto efetivo dela continua o autorizado.
3. **Dado** artistas escalados com cachê de receptivo, **Quando** o evento vira SHOW, **Então** nenhum
   cachê muda, e o aviso lista cada escalado (personagem, artista, cachê atual).
4. **Dado** dois usuários de Casting, um de Ensaio e um Superadmin, **Quando** a Comercial troca o
   evento para SHOW, **Então** cada um recebe uma notificação no sino e vê a faixa no evento; um usuário
   só de Comercial não recebe, e quem fez a troca também não.
5. **Dado** o evento de volta de SHOW para R&I, **Quando** a troca é salva, **Então** os tetos voltam à
   conta de receptivo (nunca abaixo do autorizado pelo Superadmin) e Casting e Ensaio também são
   avisados.

---

### História 3 — "Ciente" por pessoa (Prioridade: P1)

A faixa do aviso fica no evento até a pessoa clicar "Ciente". O "Ciente" de uma pessoa não some com a
faixa de ninguém mais: o Matheus e o Diogo, ambos do Casting, confirmam cada um por si.

**Por que esta prioridade**: sem isso, o primeiro que clicar esconde o aviso dos outros — foi um pedido
explícito do dono.

**Verificação**: cenários 10–12 do `verify_339.py`.

**Cenários de aceite**:

1. **Dado** um aviso pendente para Matheus e Diogo, **Quando** o Matheus clica "Ciente", **Então** a
   faixa some para o Matheus e continua para o Diogo.
2. **Dado** o aviso pendente, **Quando** a pessoa abre a notificação pelo sino, **Então** a faixa
   continua no evento até ela clicar "Ciente".
3. **Dado** o aviso de outra pessoa, **Quando** alguém tenta dar "Ciente" nele, **Então** a resposta é
   404 e nada muda (deve falhar).

---

### História 4 — Vaga a mais quando o título passa a ter menos personagens (Prioridade: P2)

O título do evento (no Google Agenda ou editado pela plataforma) passa a pedir menos vezes um
personagem do que há vagas dele. Se houver vaga vazia daquele personagem, ela sai sozinha e o histórico
registra. Se todas estiverem ocupadas, nenhuma sai: as vagas daquele personagem ficam marcadas ("o título
pede 1, há 2"), o Casting recebe o aviso e, quando tira alguém da escala, a vaga que ficou vazia sai
sozinha. Vale para evento criado pela plataforma e para evento vindo do Google.

**Por que esta prioridade**: hoje se resolve à mão (o Superadmin removeu a vaga); importante, mas o
estrago maior era o teto e o silêncio.

**Verificação**: cenários 13–18 do `verify_339.py`.

**Cenários de aceite**:

1. **Dado** um evento com 2 vagas de STORMTROOPERS, uma vazia, **Quando** o título passa a ter um
   STORMTROOPERS só, **Então** a vaga vazia sai e o histórico diz por quê ("STORMTROOPERS: o título
   pede 1, havia 2").
2. **Dado** as 2 vagas ocupadas, **Quando** o título passa a ter um só, **Então** nenhuma vaga sai,
   nenhum e-mail de remoção é enviado, as duas vagas aparecem marcadas no evento e o Casting e o
   Superadmin recebem o aviso.
3. **Dado** essa situação, **Quando** o Casting tira um dos dois artistas da escala, **Então** a vaga que
   ficou vazia sai sozinha, a marca some e o aviso deixa de ser pendente para todos.
4. **Dado** um evento vindo do Google com um personagem que sumiu por inteiro do título e a vaga dele
   ocupada, **Quando** o sync roda, **Então** a vaga não é apagada (hoje é, com e-mail ao artista): fica
   marcada e o Casting é avisado.
5. **Dado** a mesma situação ainda não resolvida, **Quando** o sync roda de novo, **Então** nenhum aviso
   novo é criado (um aviso por mudança do título, não por rodada).
6. **Dado** um título com nome reservado (Coordenador, Técnico de Som…) ou um evento de ENSAIO,
   **Quando** o sync roda, **Então** a regra de hoje vale (equipe de apoio não é personagem; ENSAIO
   segue limpando o elenco).

---

### História 5 — Orçamento novo do show atualiza os tetos (Prioridade: P2)

Quando a Comercial vincula ao evento um orçamento novo (como o #2898 do caso), os tetos das vagas que
casam com o orçamento passam a ser os dele, e não só "onde não havia teto". Depois de trocar o tipo
para SHOW, a resposta lembra a Comercial de vincular o orçamento do show se ele existir.

**Por que esta prioridade**: o recálculo pela tabela (História 2) já resolve o grosso; o orçamento
novo afina o que a tabela não sabe (quem canta).

**Verificação**: cenários 19–21 do `verify_339.py`.

**Cenários de aceite**:

1. **Dado** um evento SHOW com teto de tabela e o Luke vendido como cantor no orçamento novo, **Quando**
   a Comercial vincula o orçamento novo, **Então** o teto do Luke passa a ser o de cantor com show, e o
   histórico registra antigo e novo.
2. **Dado** uma vaga com teto autorizado pelo Superadmin acima do teto do orçamento novo, **Quando** o
   vínculo é trocado, **Então** o teto efetivo continua o autorizado.
3. **Dado** a troca de tipo para SHOW num evento com orçamento ligado, **Quando** a Comercial salva,
   **Então** o aviso da resposta diz que os tetos foram recalculados pela tabela de show e que o
   orçamento do show, se houver, deve ser vinculado na aba Comercial.

---

### História 6 — O título acompanha as vagas, e o ensaio acompanha o título (Prioridade: P1)

Quem remove uma vaga de personagem no sistema (à mão ou pela regra da História 4) vê o título do evento
perder uma ocorrência daquele nome — no sistema e no Google Agenda. Quem acrescenta uma vaga de
personagem vê o nome entrar no título. E o ensaio ainda não realizado do evento passa a ter o título
novo, para quem ensaia não trabalhar com o elenco antigo.

**Por que esta prioridade**: foi o que o dono viu no dia seguinte ao caso — o Superadmin removeu a vaga
de Stormtrooper, mas o título no sistema e no Google continuou com dois, e o ensaio marcado depois
copiou os dois. O sistema copia o título do Google a cada rodada do sync, e remover vaga nunca tocou no
título: os dois lados ficam divergentes até alguém editar à mão.

**Verificação**: cenários 23–27 do `verify_339.py`.

**Cenários de aceite**:

1. **Dado** um evento com título "STORMTROOPERS + STORMTROOPERS + DARTH VADER" e duas vagas de
   Stormtroopers, **Quando** alguém remove uma das vagas, **Então** o título passa a ser
   "STORMTROOPERS + DARTH VADER" (com o prefixo do tipo), no sistema e no Google Agenda, e o histórico
   registra a mudança.
2. **Dado** esse evento, **Quando** o Casting acrescenta uma vaga de personagem "YODA", **Então** "YODA"
   entra no fim do título, no sistema e no Google Agenda.
3. **Dado** um ensaio ainda não realizado ligado ao evento, **Quando** o título do evento muda (por
   qualquer uma das portas acima, pela edição do evento ou pelo sync), **Então** o título do ensaio
   passa a ser "🟧 ENSAIO — <título novo>", no sistema e no Google Agenda.
4. **Dado** uma vaga cujo nome não aparece no título (nome diferente do que foi digitado no título),
   **Quando** ela é removida, **Então** o título não muda e o histórico diz que o nome não foi
   encontrado no título.
5. **Dado** o título já com um STORMTROOPERS e duas vagas (uma marcada como sobrando), **Quando** o
   Casting remove a vaga sobrando, **Então** o título continua com um STORMTROOPERS (não perde o
   segundo).
6. **Dado** o Google recusando a atualização, **Quando** a vaga é removida, **Então** a vaga sai mesmo
   assim e a tela avisa que o título no Google Agenda precisa ser corrigido à mão.

### Casos de borda

- **Evento sem orçamento e sem teto**: virar SHOW não cria teto; o aviso ao Casting e ao Ensaio sai
  igual (o problema do silêncio existe com ou sem orçamento).
- **Vaga com teto que não veio de orçamento** (definido à mão): o recálculo não mexe nela; o aviso diz
  que o teto daquela vaga não foi recalculado.
- **Personagem do orçamento que não casa com nenhuma vaga** (nome diferente): segue a regra de hoje —
  entra no relatório de "não casados", sem criar vaga.
- **Carrinho de transporte (239)**: a parcela do veículo continua somando por cima do teto recalculado
  ou autorizado, no mesmo `max` de hoje — sem catraca.
- **Vaga de presença do som**: nunca tem valor nem teto; fica fora do recálculo e do aviso de cachê.
- **Evento cancelado**: nada disso roda (a regra da 312 já recusa escrita no cancelado).
- **Troca de tipo desfeita porque o Google recusou o título** (409 `EventTypeChangeBlocked`): nem
  recálculo nem aviso.
- **Duas vagas vazias e o título pede uma a menos**: sai uma só (a vaga dispensada primeiro, depois a
  mais recente).
- **Título pede MAIS vezes um personagem do que há vagas**: fora de escopo (ver abaixo).
- **Vaga criada à mão com nome diferente do título** (ex.: vaga "Vader", título "DARTH VADER"): como a
  regra da História 4 olha só o que **saiu** do título (antigo × novo), essa vaga nunca é tomada por
  "vaga a mais" por causa da grafia.
- **A própria reescrita do título pelo sistema (História 6)** não pode disparar a regra da História 4
  sobre a vaga que acabou de sair — o título novo já bate com as vagas.
- **Ensaio já realizado** (data passada) não tem o título trocado: é registro do que aconteceu.
- **Superadmin salva valor em vaga sem teto de orçamento**: não há limite a ultrapassar, então nada é
  autorizado nem gravado como teto.
- **Cachê já salvo acima do teto rebaixado** (o evento deixou de ser SHOW): o cachê fica (FR-010) e o
  card mostra a nota que já existe para valor acima do limite ("Cachê autorizado acima do limite deste
  evento."); o Casting consegue manter esse valor para a mesma pessoa (piso do FR-002), não para outra.
- **Evento cancelado com aviso pendente**: os avisos desta feature deixam de ser pendentes para todos
  (a tela do cancelado só se consulta — feature 312).
- **Evento marcado "Sumiu do Google Agenda"** (303): o ajuste do título fica só no sistema, sem aviso de
  falha — vai ao Google quando o Superadmin devolver o evento (mesma regra da troca de tipo).
- **Mudança de tipo sem SHOW** (CORP → R&I): sem recálculo e sem aviso, como hoje.

## Requisitos *(obrigatório)*

### Requisitos funcionais

**Teto autorizado (História 1)**

- **FR-001**: Quando o Superadmin salva numa vaga um cachê acima do teto efetivo dela, o sistema DEVE
  gravar esse valor como teto autorizado **da vaga**, com quem autorizou e quando.
- **FR-002**: O teto efetivo de uma vaga DEVE ser o maior entre (teto do orçamento/tabela + parcela do
  carrinho), o teto autorizado e o cachê já salvo da pessoa atual (este último é a regra da 238: quem
  reabre o card não vê o cachê de hoje rebaixado). O teto autorizado NÃO DEVE depender do cachê da
  pessoa — é ele que sobrevive quando o cachê se perde.
- **FR-003**: Tirar ou trocar a pessoa de uma vaga NÃO DEVE alterar o teto autorizado; salvar a vaga sem
  pessoa ou com cachê vazio também não.
- **FR-004**: Quando o Superadmin salva um valor menor que o teto autorizado vigente, o teto autorizado
  DEVE passar a ser esse valor (ou deixar de existir, se o valor não passar do teto do orçamento).
- **FR-005**: Vagas que hoje já têm cachê salvo acima do teto (regra da 238) DEVEM ter esse valor como
  teto autorizado depois da migração, para que nada mude para quem escala (13 vagas em 3 eventos
  futuros em 09/11).
- **FR-006**: O teto autorizado DEVE aparecer só para o Superadmin, na mesma linha do teto de hoje
  ("autorizado por <nome> em dd/mm"); para o Casting o número continua invisível (decisão da 215).

**Virar SHOW (História 2)**

- **FR-007**: Ao trocar o tipo de um evento para SHOW, o sistema DEVE recalcular o teto de cada vaga
  que veio do orçamento ligado pela mesma conta da criação, com show em todos os personagens (mesmo
  perfil, mesma duração do evento, mesmos adicionais). A vaga de Técnico de Som criada pela troca
  recebe o teto da tabela de som, como na criação de um SHOW a partir de orçamento; a de presença nunca
  tem teto.
- **FR-008**: Ao trocar o tipo de SHOW para outro, o sistema DEVE recalcular os tetos pela conta sem
  show.
- **FR-009**: Nenhum recálculo DEVE baixar o teto efetivo abaixo do teto autorizado pelo Superadmin
  (FR-002).
- **FR-010**: A troca de tipo NÃO DEVE alterar o cachê de ninguém.
- **FR-011**: Toda troca de tipo que entra ou sai de SHOW DEVE registrar no histórico do evento os tetos
  antigos e novos de cada vaga recalculada.
- **FR-012**: Toda troca de tipo que entra ou sai de SHOW DEVE avisar cada usuário de Casting, de Ensaio
  e Superadmin (sino + faixa), com: o que mudou, quem trocou, a lista de escalados (personagem e
  artista; o cachê atual só para quem já vê cachê no elenco — o Ensaio não vê) e o pedido de conferir
  cachê e disponibilidade para o ensaio.
- **FR-013**: A resposta da troca para SHOW DEVE dizer à Comercial que os tetos foram recalculados pela
  tabela de show e que o orçamento do show, se existir, deve ser vinculado na aba Comercial.

**"Ciente" por pessoa (História 3)**

- **FR-014**: Cada aviso desta feature DEVE aparecer como faixa no evento para cada destinatário até que
  **essa pessoa** clique "Ciente"; o "Ciente" de uma pessoa NÃO DEVE afetar a faixa de outra.
- **FR-015**: Ler a notificação pelo sino NÃO DEVE apagar a faixa.
- **FR-016**: "Ciente" em aviso de outra pessoa DEVE responder 404, sem alterar nada.
- **FR-017**: Um aviso de vaga a mais DEVE deixar de ser pendente para todos quando a situação se
  resolve (o número de vagas volta a bater com o título), sem precisar de "Ciente".
- **FR-033**: Quem fez a mudança (a troca de tipo ou a edição do título pela plataforma) NÃO DEVE
  receber o próprio aviso. Mudança vinda do Google (sync) avisa todos os destinatários.

**Vaga a mais (História 4)**

- **FR-018**: Sempre que o título do evento muda (sync do Google ou edição pela plataforma), o sistema
  DEVE comparar o título antigo com o novo e, para cada personagem que perdeu ocorrências, conferir se
  há mais vagas daquele personagem do que o título novo pede — em evento criado pela plataforma e em
  evento vindo do Google. Só o que **saiu** do título conta: diferença antiga de grafia entre vaga e
  título não dispara nada.
- **FR-019**: Havendo vaga a mais e vaga vazia daquele personagem, o sistema DEVE remover a vaga vazia
  (a dispensada primeiro, depois a mais recente) e registrar no histórico o motivo.
- **FR-020**: Se, depois de removidas as vagas vazias (FR-019), ainda sobrar vaga daquele personagem —
  todas ocupadas —, o sistema NÃO DEVE remover nenhuma delas nem mandar e-mail de remoção; DEVE marcar
  as vagas ocupadas daquele personagem e avisar cada usuário de Casting e Superadmin (sino + faixa).
- **FR-021**: Quando o Casting tira alguém da escala de um personagem marcado como sobrando, a vaga que
  ficou vazia DEVE sair sozinha, com histórico.
- **FR-022**: O sync que roda de novo sobre a mesma situação NÃO DEVE criar aviso repetido.
- **FR-023**: O sync do Google NÃO DEVE mais apagar vaga ocupada de personagem que sumiu do título
  (comportamento de hoje, com e-mail ao artista): passa pela mesma regra do FR-020 (confirmado pelo
  dono no clarify de 09/11). Vaga vazia desse personagem segue saindo sozinha (FR-019).
- **FR-024**: Nomes reservados de equipe e o evento de ENSAIO mantêm a regra de hoje.

**Orçamento novo (História 5)**

- **FR-025**: Ao vincular ou trocar o orçamento de um evento, o teto das vagas que casam com ele DEVE
  passar a ser o do orçamento (hoje só entra "onde não havia teto"), respeitando o FR-009.
- **FR-026**: A troca de vínculo DEVE registrar no histórico os tetos antigos e novos.

**Título acompanha as vagas (História 6)**

- **FR-027**: Ao remover uma vaga de personagem pelo sistema, se depois da remoção o título pedir aquele
  nome mais vezes do que há vagas dele, o sistema DEVE tirar do título uma ocorrência (a última), manter
  o prefixo do tipo, gravar no sistema e enviar ao Google Agenda. Remoção causada pelo próprio título
  (FR-019, FR-021) ou de vaga marcada como sobrando já deixa título e vagas iguais, e por isso não
  reescreve nada — o nome nunca sai duas vezes.
- **FR-028**: Ao acrescentar uma vaga de personagem pelo sistema, se depois da inclusão houver mais vagas
  daquele nome do que o título pede, o sistema DEVE acrescentar o nome ao fim do título, no sistema e no
  Google Agenda. Vaga de equipe de apoio (nomes reservados) nunca entra no título (regra da 239). A
  edição completa do evento ("Editar", que traz título e elenco juntos) não passa por esta regra: o
  título do formulário vale.
- **FR-029**: Vaga cujo nome não está no título não altera o título; o histórico DEVE dizer que o nome
  não foi encontrado.
- **FR-030**: Sempre que o título de um evento muda (FR-027, FR-028, edição do evento ou sync), os
  ensaios dele ainda não realizados (não cancelados e com início depois de agora, hora de São Paulo)
  DEVEM passar a ter "🟧 ENSAIO — <título novo>", no sistema e no Google Agenda.
- **FR-031**: Falha do Google ao atualizar o título NÃO DEVE desfazer a remoção ou a inclusão da vaga;
  DEVE voltar como aviso na tela ("Não foi possível atualizar o título no Google Agenda. Corrija o
  título por lá.") e ficar no histórico.
- **FR-032**: A reescrita do título feita pelo próprio sistema NÃO DEVE disparar a regra de vaga a mais
  (FR-018) nem e-mail ao elenco.

**E-mail ao Ensaio**

- **FR-034**: Ao virar SHOW pela plataforma, a equipe de Ensaio DEVE receber o mesmo e-mail que já recebe
  quando o sync encontra um SHOW novo no Google (hoje a troca pela plataforma liga "precisa ensaio" sem
  esse e-mail). Sair de SHOW não manda e-mail.

### Textos (Princípio XV — superfície interna)

| Onde | Texto |
|---|---|
| Sino, entrou em SHOW | Título "Evento virou SHOW: <título>" · corpo "<dd/mm HH:MM> · Confira a disponibilidade do elenco para o ensaio e revise os cachês." |
| Sino, saiu de SHOW | Título "Evento deixou de ser SHOW: <título>" · corpo "<dd/mm HH:MM> · Os ensaios foram cancelados. Revise os cachês do elenco." |
| Faixa, entrou em SHOW | "Este evento virou SHOW em <dd/mm>, por <nome>. Confira com cada artista a disponibilidade para o ensaio e revise os cachês: o limite subiu para o valor de show." + lista + botão "Ciente" |
| Faixa, saiu de SHOW | "Este evento deixou de ser SHOW em <dd/mm>, por <nome>. Os ensaios foram cancelados e o limite de cachê voltou ao valor sem show. Revise os cachês do elenco." + lista + "Ciente" |
| Sino, vaga a mais | Título "Vaga a mais: <título>" · corpo "<PERSONAGEM>: o título pede <n>, há <m> vagas ocupadas. Remova alguém da escala." — com o nome saindo inteiro do título: "<PERSONAGEM> saiu do título; há <m> vagas ocupadas. Remova da escala quem não vai mais." ("1 vaga ocupada" no singular) |
| Faixa, vaga a mais | "<PERSONAGEM>: o título do evento pede <n>, há <m> vagas ocupadas. Remova alguém da escala; a vaga que ficar vazia sai sozinha." — saindo inteiro: "<PERSONAGEM> saiu do título do evento, e há <m> vagas ocupadas. Remova da escala quem não vai mais; a vaga que ficar vazia sai sozinha." + "Ciente" |
| Card da vaga marcada | "O título pede <n> — remova alguém da escala." — saindo inteiro: "Saiu do título — remova o artista da escala." |
| Linha do teto (só Superadmin) | "… · autorizado por <nome> em <dd/mm>" ou "… · autorizado antes da 339" |
| Aviso da resposta (troca para SHOW com orçamento) | "Os limites de cachê foram recalculados pela tabela de show. Se houver orçamento do show, vincule-o na aba Comercial." |
| Aviso da resposta (falha do Google no título) | "Não foi possível atualizar o título no Google Agenda. Corrija o título por lá." |
| Erro do "Ciente" | "Não foi possível registrar. Tente novamente." |

O Casting nunca lê "teto" nem o número (decisão da 215): para ele é "limite".

### Entidades

- **Vaga do evento (`EventRole`)**: ganha o **teto autorizado** (valor, quem autorizou, quando), separado
  do teto do orçamento (`cache_cap`) e do cachê da pessoa (`cache_value`). Modelo em `app/models.py`,
  migration à mão, aditiva, com o preenchimento do FR-005.
- **Aviso do evento**: uma notificação (feature 272) por destinatário, com o tipo do fato (troca de tipo
  com SHOW; vaga a mais) e o "Ciente" daquela pessoa — separado do "lida" do sino (FR-015). Se cabe em
  coluna nova da notificação ou em tabela própria, o plano decide.
- **Marca de vaga a mais**: derivada da comparação título × vagas (FR-018) — de preferência calculada,
  sem coluna; o plano decide.

### RBAC

- `POST /api/roles/<id>/assign` — papéis de hoje (`_can_edit_event`); só `SUPERADMIN` grava teto
  autorizado (FR-001, FR-004).
- `PATCH /api/events/<id>` e `PATCH /api/events/<id>/basico` — papéis de hoje (troca de tipo:
  Comercial e Superadmin); passam a recalcular tetos e emitir avisos.
- `PATCH /api/events/<id>/orcamento` — papéis de hoje; passa a reescrever tetos (FR-025).
- Remover e acrescentar vaga (`DELETE` da vaga e `POST` de vaga nova em `app/api/agenda_write.py`) —
  papéis de hoje; passam a reescrever o título e o dos ensaios (FR-027, FR-028, FR-030).
- **Novo** endpoint de "Ciente" — sem gate de papel, escopo por dono (`current_user`), 404 para aviso
  alheio (padrão do §4 do `docs/00` para notificações). Linha na tabela de `docs/01` §4.3.
- Serialização do detail do evento: a faixa só traz os avisos pendentes **da pessoa que pediu**; o teto
  autorizado só sai para o Superadmin.

## Verificação (`verify_339.py`) *(obrigatório — Princípio VIII)*

Arquivo: `specs/339-evento-mudou-avisa-casting/verify_339.py`, contra `manto_local` (`DATABASE_URL` de
`.local-db-url`, `FLASK_ENV=development`, `MANTO_SEM_THREADS=1`). Login só por `POST /api/auth/login`;
escrita conferida por conexão separada; limpeza no `finally`. Google, e-mail e threads travados ou
mockados: **nenhuma vaga com `character_name` inventado em evento real** (o sync apagaria e mandaria
e-mail a gente de verdade — `CLAUDE.md` §4); o evento de teste é descartável, `source="platform"`, e o
sync é exercitado chamando a reconciliação com um título montado, sem Google.

| # | Cenário | O que prova | Deve falhar? |
|---|---|---|---|
| 1 | Superadmin salva R$ 400 numa vaga com teto R$ 325 | teto autorizado gravado, com autor e data | não |
| 2 | Casting tira o artista e escala outro com R$ 400 | salva R$ 400 | não |
| 3 | Casting tenta R$ 450 | volta para R$ 400 | não |
| 4 | Superadmin corrige para valor menor | teto autorizado acompanha o último valor | não |
| 5 | R&I → SHOW com orçamento sem show | tetos de show por perfil (Técnico de Som com teto de som); cachês intactos; histórico com antigo/novo; aviso do FR-013 na resposta | não |
| 6 | R&I → SHOW com vaga autorizada acima do teto de show | teto efetivo segue o autorizado | não |
| 7 | R&I → SHOW feita pela Comercial | 1 notificação por usuário de Casting, de Ensaio e Superadmin; faixa no detalhe de cada um; e-mail ao Ensaio enviado (falso) | não |
| 8 | Usuário só de Comercial e o autor da troca | não recebem o aviso | não |
| 9 | SHOW → R&I | tetos de receptivo (piso no autorizado) e aviso | não |
| 10 | Casting A dá "Ciente" | faixa some para A, fica para B | não |
| 11 | A abre a notificação pelo sino sem "Ciente" | faixa continua | não |
| 12 | A dá "Ciente" no aviso de B | 404, nada muda | **sim** |
| 13 | Título 2 → 1 com uma vaga vazia | vaga vazia sai, histórico registra | não |
| 14 | Título 2 → 1 com as duas ocupadas | nada sai, nenhum e-mail, vagas marcadas, aviso ao Casting | não |
| 15 | Casting tira um artista da escala nessa situação | vaga vazia sai, marca some, aviso deixa de ser pendente | não |
| 16 | Mesma reconciliação de novo | nenhum aviso repetido | não |
| 17 | Evento vindo do Google, personagem some por inteiro, vaga ocupada | vaga fica, sem e-mail, marcada | não |
| 18 | Nome reservado e ENSAIO | regra de hoje | não |
| 19 | Vincular orçamento novo com cantor | teto de cantor com show | não |
| 20 | Vincular orçamento novo com autorizado acima | teto efetivo segue o autorizado | não |
| 21 | Casting tenta gravar teto autorizado | valor rebaixado, nenhum teto autorizado gravado | **sim** |
| 22 | Vaga criada à mão com grafia diferente do título + título muda em outro personagem | a vaga de grafia diferente não é tocada | não |
| 23 | Remove uma de duas vagas de STORMTROOPERS | título perde uma ocorrência (prefixo mantido); push ao Google chamado com o título novo | não |
| 24 | Acrescenta vaga de personagem YODA | YODA no fim do título; vaga de Coordenador não entra | não |
| 25 | Título do evento muda com ensaio futuro e ensaio passado | só o futuro recebe "🟧 ENSAIO — <título novo>" | não |
| 26 | Remove vaga cujo nome não está no título | título igual, histórico diz "não encontrado" | não |
| 27 | Google recusa o título novo | vaga removida mesmo assim, aviso na resposta, nada de regra de vaga a mais | não |
| 27b | Remove a vaga marcada como sobrando (título já com um) | título não perde a segunda ocorrência | não |
| 28 | limpeza | evento, vagas, avisos e usuários descartáveis apagados (`roles.clear()` antes do usuário) | — |

Conferência de tela (skill `manto-conferir-tela`): detalhe do evento como Casting (faixa, "Ciente", vaga
marcada como sobrando, card de casting depois da troca de pessoa), como Ensaio (faixa) e como Superadmin
(linha do teto autorizado); sino nos três. Tela interna — desktop e celular (o Casting usa o celular).

## Critérios de sucesso *(obrigatório)*

- **SC-001**: Quando um evento vira SHOW (ou deixa de ser), 100% das pessoas de Casting, de Ensaio e
  Superadmin (menos quem fez a troca) recebem o aviso, sem ninguém precisar contar a elas.
- **SC-002**: Depois que o Superadmin autoriza um valor numa vaga, o Casting consegue salvar esse valor
  para qualquer artista daquela vaga, sem pedir de novo — zero casos de "artista entrou com R$ 0" por
  troca de pessoa.
- **SC-003**: Num evento que virou SHOW, o Casting consegue salvar o cachê de show da tabela sem
  intervenção do Superadmin.
- **SC-004**: Toda vaga a mais por mudança no título é removida sozinha (se vazia) ou fica marcada com
  aviso ao Casting (se ocupada) — nenhuma passa em silêncio, e nenhum artista recebe e-mail de remoção
  sem alguém do Casting ter tirado ele da escala.
- **SC-005**: O "Ciente" de uma pessoa nunca esconde o aviso de outra.
- **SC-006**: Depois de remover ou acrescentar uma vaga de personagem, o título no sistema, no Google
  Agenda e no ensaio futuro bate com as vagas na próxima vez que alguém abre a agenda — sem edição à
  mão.

## Fora de escopo

- **Personagem que entra no título** (o título pede mais vezes do que há vagas): sem vaga nova e sem
  aviso nesta feature. Hoje o sync cria a vaga em evento vindo do Google; em evento da plataforma, a vaga
  nasce pelo "Editar". Se virar dor, é a próxima.
- **Mudar cachê de quem já está escalado** (D2): o sistema não sobe nem baixa cachê sozinho.
- **Avisar o artista** de que o evento virou SHOW ou de que precisa ensaiar: o aviso desta feature é
  interno (equipe). O e-mail de "evento mudou" de hoje (data, hora, local, cachê) segue como está.
- **Aviso no celular (Web Push, 332)** e WhatsApp automático para a equipe.
- **Remontar o título inteiro a partir das vagas**: a História 6 tira ou acrescenta **uma ocorrência**
  por vaga, sem reescrever o resto (a ordem e a grafia que a Comercial digitou ficam).
- **Proteger o "Editar" de formulário desatualizado** (aberto antes de uma mudança no Google e salvo
  depois, devolvendo o título velho): suspeita no caso 1423, sem prova. Se acontecer de novo, é outra
  feature.
- **Mostrar o número do teto ao Casting** (decisão da 215 continua).

## Docs a atualizar

`docs/01` §2 (`event_roles`, aviso/"Ciente") e §4.3 (endpoint de "Ciente" e as portas alteradas);
`docs/02` (detalhe do evento: faixa, vaga a mais, linha do teto autorizado; sino); `docs/03` (entrada
no topo, com o caso do evento 1423); `docs/04` §Agenda (troca de tipo, reconciliação título × vagas,
teto efetivo, título ↔ vagas ↔ ensaio); `docs/05` se o "personagem que entra no título" ficar como
dívida.

## Premissas

- **Destinatários** (clarify de 09/11): Casting e Superadmin em todos os avisos; Ensaio também na troca
  de tipo com SHOW; o autor da mudança fica de fora (FR-033). O "Ver como" não troca a caixa (regra da
  272: a caixa é da pessoa).
- **"Mesmo perfil" para o recálculo** = o personagem do orçamento ligado, com a flag de show ligada:
  boneco → boneco com show, cara-limpa → cara-limpa com show, cantor e especiais pela sua tabela; o
  coordenador vai para a coluna de show. Quem canta só a tabela não sabe — por isso o orçamento novo
  (História 5) prevalece quando vinculado.
- **"Teto autorizado" acompanha o último valor que o Superadmin salvou** acima do teto do orçamento
  (corrige erro de digitação sem nova tela).
- **Comparação título × vagas** usa o mesmo nome normalizado do sync (sem prefixo de tipo, sem nomes de
  equipe) e conta repetições.
- **O caso do evento 1423** já foi resolvido à mão (vaga removida, R$ 400 salvos); a migração do FR-005
  transforma os R$ 400 dele em teto autorizado. O título dele continuou com dois STORMTROOPERS porque
  remover a vaga não toca no título (a História 6 resolve daqui para frente): a rodada do sync de
  09/11 às 19h43 (Brasília), sem erro, leu no Google o título com os dois, e o ensaio 1496, criado
  depois da remoção da vaga, copiou os dois. A 339 não corrige o passado: o título do 1423 e o do
  ensaio 1496 se corrigem à mão, uma vez.
- **Rótulo de vaga ↔ título**: o nome da vaga casa com o segmento do título pela normalização do sync
  (sem caixa, sem acento, sem espaços nas pontas). A ocorrência retirada é a última; a acrescentada vai
  no fim, em maiúsculas, como os títulos gerados pela plataforma.
- Horário do aviso e do histórico em hora de São Paulo (`now_sp()`), como as notificações da 272.
