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

## Decisões do dono (09/11/2026)

| # | Pergunta | Decisão |
|---|---|---|
| D1 | De onde sai o teto novo quando o evento vira SHOW | **Tabela + orçamento**: recalcula sozinho pelo preço de show do mesmo perfil; se a Comercial vincular o orçamento novo do show, valem os tetos dele. Nunca abaixo do que o Superadmin autorizou |
| D2 | Cachê de quem já está escalado quando vira SHOW | **O Casting revisa**: o cachê não muda sozinho; o aviso lista quem está escalado e precisa ser revisto (cachê e disponibilidade para o ensaio) |
| D3 | Vaga a mais quando o título tem menos personagens | **Vazia sai, ocupada avisa**: vaga vazia daquele personagem sai sozinha (com histórico); se todas têm gente, nenhuma sai — o Casting é avisado para tirar alguém da escala |
| D4 | Como o aviso aparece | **Sino + faixa no evento até "Ciente"**, e o "Ciente" é **por pessoa**: o Matheus clicar não some para o Diogo, e vice-versa. Quando vira SHOW, o Ensaio também recebe |
| D5 | Valor que o Superadmin salva acima do teto | Vira o **teto da vaga** e não se perde quando a pessoa da vaga muda |

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
ensaio"), o teto de cada vaga é recalculado pelo preço de show do mesmo perfil, e cada pessoa do Casting
e do Ensaio recebe um aviso no sino e vê, no evento, uma faixa dizendo o que mudou, quem está escalado
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
4. **Dado** dois usuários de Casting e um de Ensaio, **Quando** o evento vira SHOW, **Então** cada um
   recebe uma notificação no sino e vê a faixa no evento; um usuário só de Comercial não recebe.
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
   nenhum e-mail de remoção é enviado, as duas vagas aparecem marcadas no evento e o Casting recebe o
   aviso.
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
- **Mudança de tipo sem SHOW** (CORP → R&I): sem recálculo e sem aviso, como hoje.

## Requisitos *(obrigatório)*

### Requisitos funcionais

**Teto autorizado (História 1)**

- **FR-001**: Quando o Superadmin salva numa vaga um cachê acima do teto efetivo dela, o sistema DEVE
  gravar esse valor como teto autorizado **da vaga**, com quem autorizou e quando.
- **FR-002**: O teto efetivo de uma vaga DEVE ser o maior entre (teto do orçamento/tabela + parcela do
  carrinho) e o teto autorizado — e NÃO DEVE depender do cachê da pessoa escalada.
- **FR-003**: Tirar ou trocar a pessoa de uma vaga NÃO DEVE alterar o teto autorizado.
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
  perfil, mesma duração do evento, mesmos adicionais).
- **FR-008**: Ao trocar o tipo de SHOW para outro, o sistema DEVE recalcular os tetos pela conta sem
  show.
- **FR-009**: Nenhum recálculo DEVE baixar o teto efetivo abaixo do teto autorizado pelo Superadmin
  (FR-002).
- **FR-010**: A troca de tipo NÃO DEVE alterar o cachê de ninguém.
- **FR-011**: Toda troca de tipo que entra ou sai de SHOW DEVE registrar no histórico do evento os tetos
  antigos e novos de cada vaga recalculada.
- **FR-012**: Toda troca de tipo que entra ou sai de SHOW DEVE avisar cada usuário de Casting e de Ensaio
  (sino + faixa), com: o que mudou, quem trocou, a lista de escalados (personagem, artista, cachê
  atual) e o pedido de conferir cachê e disponibilidade para o ensaio.
- **FR-013**: A resposta da troca para SHOW DEVE dizer à Comercial que os tetos foram recalculados pela
  tabela de show e que o orçamento do show, se existir, deve ser vinculado na aba Comercial.

**"Ciente" por pessoa (História 3)**

- **FR-014**: Cada aviso desta feature DEVE aparecer como faixa no evento para cada destinatário até que
  **essa pessoa** clique "Ciente"; o "Ciente" de uma pessoa NÃO DEVE afetar a faixa de outra.
- **FR-015**: Ler a notificação pelo sino NÃO DEVE apagar a faixa.
- **FR-016**: "Ciente" em aviso de outra pessoa DEVE responder 404, sem alterar nada.
- **FR-017**: Um aviso de vaga a mais DEVE deixar de ser pendente para todos quando a situação se
  resolve (o número de vagas volta a bater com o título), sem precisar de "Ciente".

**Vaga a mais (História 4)**

- **FR-018**: Sempre que o título do evento muda (sync do Google ou edição pela plataforma), o sistema
  DEVE comparar, por personagem, quantas vezes o título o pede com quantas vagas de personagem existem —
  em evento criado pela plataforma e em evento vindo do Google.
- **FR-019**: Havendo vaga a mais e vaga vazia daquele personagem, o sistema DEVE remover a vaga vazia
  (a dispensada primeiro, depois a mais recente) e registrar no histórico o motivo.
- **FR-020**: Havendo vaga a mais e todas ocupadas, o sistema NÃO DEVE remover nenhuma vaga nem mandar
  e-mail de remoção; DEVE marcar as vagas daquele personagem no evento e avisar o Casting (sino + faixa).
- **FR-021**: Quando o Casting tira alguém da escala de um personagem marcado como sobrando, a vaga que
  ficou vazia DEVE sair sozinha, com histórico.
- **FR-022**: O sync que roda de novo sobre a mesma situação NÃO DEVE criar aviso repetido.
- **FR-023**: O sync do Google NÃO DEVE mais apagar vaga ocupada de personagem que sumiu do título
  (comportamento de hoje, com e-mail ao artista): passa pela mesma regra do FR-020.
- **FR-024**: Nomes reservados de equipe e o evento de ENSAIO mantêm a regra de hoje.

**Orçamento novo (História 5)**

- **FR-025**: Ao vincular ou trocar o orçamento de um evento, o teto das vagas que casam com ele DEVE
  passar a ser o do orçamento (hoje só entra "onde não havia teto"), respeitando o FR-009.
- **FR-026**: A troca de vínculo DEVE registrar no histórico os tetos antigos e novos.

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
| 5 | R&I → SHOW com orçamento sem show | tetos de show por perfil; cachês intactos; histórico com antigo/novo | não |
| 6 | R&I → SHOW com vaga autorizada acima do teto de show | teto efetivo segue o autorizado | não |
| 7 | R&I → SHOW | 1 notificação por usuário de Casting e de Ensaio, com a lista de escalados | não |
| 8 | Usuário só de Comercial | não recebe o aviso | não |
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
| 22 | limpeza | evento, vagas, avisos e usuários descartáveis apagados (`roles.clear()` antes do usuário) | — |

Conferência de tela (skill `manto-conferir-tela`): detalhe do evento como Casting (faixa, "Ciente", vaga
marcada como sobrando, card de casting depois da troca de pessoa), como Ensaio (faixa) e como Superadmin
(linha do teto autorizado); sino nos três. Tela interna — desktop e celular (o Casting usa o celular).

## Critérios de sucesso *(obrigatório)*

- **SC-001**: Quando um evento vira SHOW (ou deixa de ser), 100% das pessoas de Casting e de Ensaio
  recebem o aviso, sem ninguém precisar contar a elas.
- **SC-002**: Depois que o Superadmin autoriza um valor numa vaga, o Casting consegue salvar esse valor
  para qualquer artista daquela vaga, sem pedir de novo — zero casos de "artista entrou com R$ 0" por
  troca de pessoa.
- **SC-003**: Num evento que virou SHOW, o Casting consegue salvar o cachê de show da tabela sem
  intervenção do Superadmin.
- **SC-004**: Toda vaga a mais por mudança no título é removida sozinha (se vazia) ou fica marcada com
  aviso ao Casting (se ocupada) — nenhuma passa em silêncio, e nenhum artista recebe e-mail de remoção
  sem alguém do Casting ter tirado ele da escala.
- **SC-005**: O "Ciente" de uma pessoa nunca esconde o aviso de outra.

## Fora de escopo

- **Personagem que entra no título** (o título pede mais vezes do que há vagas): sem vaga nova e sem
  aviso nesta feature. Hoje o sync cria a vaga em evento vindo do Google; em evento da plataforma, a vaga
  nasce pelo "Editar". Se virar dor, é a próxima.
- **Mudar cachê de quem já está escalado** (D2): o sistema não sobe nem baixa cachê sozinho.
- **Avisar o artista** de que o evento virou SHOW ou de que precisa ensaiar: o aviso desta feature é
  interno (equipe). O e-mail de "evento mudou" de hoje (data, hora, local, cachê) segue como está.
- **Aviso no celular (Web Push, 332)** e WhatsApp automático para a equipe.
- **Reescrever o título a partir das vagas** quando uma vaga é removida pela plataforma.
- **Mostrar o número do teto ao Casting** (decisão da 215 continua).

## Docs a atualizar

`docs/01` §2 (`event_roles`, aviso/"Ciente") e §4.3 (endpoint de "Ciente" e as portas alteradas);
`docs/02` (detalhe do evento: faixa, vaga a mais, linha do teto autorizado; sino); `docs/03` (entrada
no topo, com o caso do evento 1423); `docs/04` §Agenda (troca de tipo, reconciliação título × vagas,
teto efetivo); `docs/05` se o "personagem que entra no título" ficar como dívida.

## Premissas

- **Destinatários**: Casting em todos os avisos; Ensaio também na troca de tipo com SHOW. O Superadmin
  não recebe no sino (é quem autoriza e costuma ser quem mudou), mas vê o evento como hoje. Ajustável
  no `/speckit-clarify`.
- **"Mesmo perfil" para o recálculo** = o personagem do orçamento ligado, com a flag de show ligada:
  boneco → boneco com show, cara-limpa → cara-limpa com show, cantor e especiais pela sua tabela; o
  coordenador vai para a coluna de show. Quem canta só a tabela não sabe — por isso o orçamento novo
  (História 5) prevalece quando vinculado.
- **"Teto autorizado" acompanha o último valor que o Superadmin salvou** acima do teto do orçamento
  (corrige erro de digitação sem nova tela).
- **Comparação título × vagas** usa o mesmo nome normalizado do sync (sem prefixo de tipo, sem nomes de
  equipe) e conta repetições.
- **O caso do evento 1423** já foi resolvido à mão (vaga removida, R$ 400 salvos); a migração do FR-005
  transforma os R$ 400 dele em teto autorizado. O título dele ainda tem dois STORMTROOPERS no sistema
  (e o ensaio criado em 09/11 copiou os dois): título pedindo mais do que há vagas está fora de escopo,
  então nada é marcado — mas o título deve ser corrigido no Google para não confundir a equipe.
- Horário do aviso e do histórico em hora de São Paulo (`now_sp()`), como as notificações da 272.
