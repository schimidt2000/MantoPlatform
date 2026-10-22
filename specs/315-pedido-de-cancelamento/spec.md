# Feature 315 — O Comercial pede o cancelamento pelo sistema e o Superadmin é avisado e decide

**Branch**: `315-pedido-de-cancelamento` (da `main` em `7cc5e11e`) · **Created**: 2026-10-22 · **Status**: Rascunho ·
**Migration**: uma, aditiva (duas colunas nulas no evento: o alcance do pedido e a devolução combinada), escrita à
mão sobre o head `c5d2f7a9e306` · **Nível**: 1 (feature) — endpoint novo, kinds novos no sino, estado novo nas telas,
duas superfícies (ERP e portal); constituição, Princípio VI

**Input**: pedido do dono: "pode começar a 2a" / "Sim" (22/10/2026) — item **2a** do backlog de setembro
("Solicitar cancelamento" pelo sistema), pela ordem A do `ENCAVALAMENTO.md` (depois da 1b = 306 e da 1c = 312, ambas
em produção). Plano: `docs/backlog/2a-solicitar-cancelamento-pelo-sistema.md` (checkout principal; escrito em
01–02/10 contra `f6ad283`, respostas do dono de 13/10). Reconferência contra o HEAD: `pesquisa/reconferencia-2026-10-22.md`
— **vale ela onde diverge do plano**.

## O pedido, nas palavras do dono *(obrigatório)*

Decisões do `docs/PLANO_BACKLOG_SETEMBRO.md` que governam este item:

> **D1** — Cancelamento passa pelo sistema **de verdade**: […] "Solicitar cancelamento" com aviso no sino.
>
> **D18** — Evento com venda que some do Google: fica e avisa no sino; […] o Superadmin é avisado e decide (volta ao
> Google ou cancela pelo sistema).
>
> **D21** — "Não deve ser apenas um aviso no sino": faixa fixa no topo de todas as telas + sino, para Superadmin e
> Comercial; a decisão é só do Superadmin.
>
> **D27** — a tela de cancelar do Superadmin vem vazia: o que o Comercial informou aparece ao lado, e o Superadmin
> escolhe de propósito.

O sintoma, como a equipe o vive hoje (recontagem em produção, 22/10/2026): o botão "Solicitar exclusão" existe desde
07/08, mas **não chega a ninguém**. Em 07/10, às 07:38, uma pessoa do Comercial pediu pelo sistema o cancelamento do
evento 1350 (R&I de 12/12, com venda) e, seis minutos depois, apagou o evento no Google — a marca de "sumiu do
Google" da 303 o segurou. Quinze dias depois o pedido continua lá, sem decisão: não há aviso do pedido, e os 6 avisos
de "sumiu do Google" do sino estão todos sem leitura. É exatamente a porta que a D1 manda abrir: o Comercial pede, o
Superadmin fica sabendo e decide, e quem pediu fica sabendo da decisão.

## Clarifications

### Decisões do dono (palavras dele; não se reabrem)

As seis perguntas do plano, respondidas em 13/10/2026:

1. **Q1 = B, para Comercial e Superadmin** — o pedido pendente aparece também na faixa vermelha do topo: "Já está
   aparecendo uma faixa vermelha no topo. Mas eu gostaria que isso aparecesse apenas para comercial e superadmin, para
   não gerar pânico em todo o time."
2. **Q2 = B** — o pedido leva o motivo **e a devolução combinada completa** com a cliente (Tudo/Parte/Nada, valor,
   nome e PIX de quem recebe; num dia só de uma venda de vários dias, também o novo valor da venda): "Informação
   completa."
3. **Q3 = A** — o aviso do pedido vai aos Superadmins; a decisão volta a quem pediu: "Superadmin."
4. **Q4 = C** — enquanto o pedido espera: "A equipe vê 'cancelamento pedido'; os escalados veem 'evento em
   confirmação'."
5. **Q5 = D** — ninguém desiste do pedido sozinho; só o Superadmin fecha o pedido: "Somente superadmin."
6. **Q6 = C** — o motivo e quem pediu só para quem trata do cancelamento (Comercial, Financeiro e Superadmin): "Só
   quem trata o cancelamento."

E as respostas de outros itens que este segue: **1b-Q1 = C** (numa venda de vários dias cancela-se um dia sem
desagrupar, a venda diminui), **1b-Q4 = B** (evento com cachê já pago ao elenco não se cancela), **1b-Q5 = B** (o 1º
dia cancelado sozinho passa a venda ao próximo dia que fica), **1b-Q8 a Q10 = A** (a multa ao elenco é o Superadmin
quem informa, ao cancelar), **1b-Q11 = B** (o cancelamento avisa os escalados), **1c-Q3 = C** (o ensaio sai junto com
o show), **1c-Q4** (o cancelado some da agenda), **1c-Q9 = A** (motivo e autor do cancelamento com a mesma régua da
Q6), **1c-Q10** (ao cancelar, o Casting é chamado a tirar e avisar os escalados), **1c-Q12 = A** (o e-mail do
cancelamento continua ao lado do WhatsApp). Todas já construídas pela 306/312 — esta entrega não as repete.

### Session 2026-10-22 (`/speckit-specify`) — leituras fixadas por esta spec, não palavras do dono

Premissas contestáveis (vêm do plano ou da reconferência); o dono só precisa dizer se discorda.

1. **A D35 caiu com a 306**: o evento marcado como "sumiu do Google" já se cancela pelo sistema. Pedido nele é aceito
   e não mexe na marca; "Devolver ao Google" não decide o pedido (o Superadmin que devolveu recusa, se for o caso).
2. **Ensaio não recebe pedido** (premissa P27 do plano): o ensaio sai junto quando o show é cancelado (1c-Q3 = C) e
   se desmarca direto pela equipe de Ensaio, Casting ou Superadmin; o Comercial vê o item desabilitado com a frase.
3. **Evento com cachê já pago ao elenco não recebe pedido** (P26, pela 1b-Q4 = B), em qualquer dia que o pedido
   alcance; o item aparece desabilitado com a frase do cancelar.
4. **A devolução combinada segue a forma do cancelar da 306**: Tudo/Parte/Nada sem opção marcada; valor em Parte;
   nome e PIX obrigatórios em Tudo e Parte; num dia só (outro dia da venda, ou o 1º dia com "só este dia"), só Parte
   ou Nada e o novo valor da venda, obrigatório. **Venda virtual** (Loja de Interações) leva só o motivo: o
   cancelamento dela faz o estorno sozinho e não pergunta devolução. O pedido confere a forma, não o dinheiro (máximo
   e mínimo a devolver são conferidos pelo Superadmin no cancelar).
5. **Quem vê a devolução combinada** (P20): modo e valor, quem já vê a venda do evento (Comercial, Financeiro,
   Superadmin); nome e PIX de quem recebe, só Superadmin, Financeiro e quem fez o pedido — a mesma régua do PIX do
   cancelado. Nunca no sino, na faixa, no selo, no resumo da agenda nem no portal.
6. **O pedido que já existe no dia do deploy** (o 1350) continua pendente, com o rótulo novo, sem alcance e "sem
   devolução informada"; aparece na faixa, na fila e no quadro do evento, **sem** aviso retroativo no sino (P21) — o
   dono decide pela fila.
7. **Excluir um evento vazio com pedido** responde a quem pediu ("Evento excluído"), sem link (o evento não existe
   mais); o sync do Google não responde (P18).
8. **Quem age não recebe a própria resposta** (P24): o Superadmin que pede recebe o aviso do pedido como os demais;
   quem decide sendo o autor não recebe a resposta.
9. **O selo "Cancelamento pedido" aparece onde o selo de situação já aparece** (agenda Mês, Dia, Lista e busca, e as
   listas que já mostram situação do evento: ficha da cliente, formulários, figurino, tags 3D) — ele nunca leva motivo
   nem autor, então não fere a Q6.
10. **A recusa passa por confirmação, com motivo opcional** (P6) — hoje um clique errado some com o pedido.
11. **O texto do diálogo de cancelar "Aparece para quem abre o evento."** (sobre o motivo do cancelamento) foi
    superado pela 1c-Q9 = A e é corrigido aqui, já que este item mexe no diálogo.
12. **O caminho velho de pedir continua por um deploy**, aceitando só o motivo (o bundle velho não manda devolução):
    nasce um pedido "sem devolução informada", como os de antes. A remoção fica registrada no `docs/05`.

## Cenários e Verificação *(obrigatório)*

Semente comum do `verify_315.py`: o harness da 306 importado como módulo (Google falso que falha fechado, disjuntor de
rede, e-mail falso), usuários descartáveis por papel (Comercial ×2, Superadmin ×2, Financeiro, Casting, Revendedor
EducaManto, Ensaio), eventos descartáveis em meses isolados, conexão separada para conferir o que foi gravado; nunca
`EventRole` com personagem inventado. Primeira rodada contra a `main` guardada em `verify_315_primeira_falha.txt`.

### História 1 — O Comercial pede o cancelamento com o que combinou com a cliente (Prioridade: P1)

A cliente desistiu. Quem vende abre o evento, escolhe "Solicitar cancelamento", escreve o motivo e informa a
devolução combinada (Tudo, Parte ou Nada; valor; nome e PIX de quem recebe). Numa venda de vários dias, no 1º dia,
escolhe se o pedido vale para todos os dias ou só para aquele. O pedido fica gravado, o evento continua valendo em
tudo até a decisão, e cada Superadmin recebe o aviso no sino na hora.

**Por que esta prioridade**: é a porta que não existe; sem ela a equipe continua apagando no Google ou mandando
WhatsApp, e o pedido real de 07/10 está parado há quinze dias.

**Verificação**: cenários 1–9 do `verify_315.py`.

**Cenários de aceite**:

1. **Dado** um evento com venda e o Comercial logado, **Quando** ele pede o cancelamento com motivo e devolução
   "Parte, R$ 600, nome e PIX", **Então** o pedido fica gravado com quem pediu, quando, o motivo e a devolução
   combinada, e cada Superadmin ativo recebe um aviso no sino com a data do evento, a venda, o recebido, os
   escalados, o motivo e quem pediu — sem nome nem PIX da cliente.
2. **Dado** o evento é daqui a 7 dias ou menos, **Quando** o pedido é feito, **Então** o aviso chega como urgente.
3. **Dado** o Comercial escolheu "Tudo" ou "Parte", **Quando** deixa nome ou PIX em branco, **Então** o pedido não é
   aceito e a tela diz o que falta.
4. **Dado** o 1º dia de uma venda de três dias, **Quando** o Comercial pede sem escolher o alcance, **Então** o
   pedido não é aceito; **quando** escolhe "Só este dia", **Então** precisa informar o novo valor da venda e só Parte
   ou Nada; o alcance fica gravado e não muda se o 1º dia mudar depois.
5. **Dado** já existe pedido pendente no evento, **Quando** outro Comercial pede, **Então** recebe "Já existe um
   pedido de <nome>" e nada é sobrescrito nem avisado de novo.
6. **Dado** um ensaio, ou um evento com cachê já pago ao elenco, **Quando** o Comercial abre o menu, **Então** o item
   está desabilitado com a frase do motivo; e o servidor recusa o pedido com o mesmo código se chamado direto.
7. **Dado** um evento marcado como "sumiu do Google", **Quando** o Comercial pede, **Então** o pedido é aceito e a
   marca não muda.
8. **Dado** qualquer pedido, **Then** nenhuma chamada ao Google e nenhum e-mail acontecem.

---

### História 2 — Todo mundo sabe que o evento está em dúvida, e só quem trata lê o porquê (Prioridade: P1)

Enquanto o pedido espera, quem abre o evento vê "Cancelamento pedido — aguardando o Superadmin", com a data e o
alcance; motivo e quem pediu só Comercial, Financeiro e Superadmin leem. A faixa vermelha do topo diz "1 pedido de
cancelamento aguarda decisão" para Comercial e Superadmin; a agenda mostra o selo "Cancelamento pedido" para a equipe
interna; o elenco escalado vê "Evento em confirmação — entre em contato com a produção" no portal.

**Por que esta prioridade**: é o que faz o Superadmin não perder o pedido (o sino sozinho já mostrou que não basta —
0 de 6 avisos lidos) e o que impede Casting e Figurino de prepararem um evento que talvez caia, sem expor o que a
cliente contou.

**Verificação**: cenários 10–17.

**Cenários de aceite**:

1. **Dado** um pedido pendente, **Quando** um Comercial ou Superadmin abre qualquer tela, **Então** a faixa vermelha
   mostra a frase dos pedidos com link para o evento (vários pedidos: lista com um link por evento), sem motivo, autor
   nem dinheiro; **quando** é Casting, Figurino, Financeiro ou o revendedor, **Então** a faixa não aparece por causa do
   pedido.
2. **Dado** o mesmo pedido, **Quando** Casting, Figurino, Ensaio, Artista 3D ou o revendedor abrem o evento, **Então**
   veem só "Cancelamento pedido — aguardando o Superadmin", a data e o alcance — o servidor não manda motivo, autor,
   nome nem PIX (também ao Superadmin em "Ver como" desses papéis).
3. **Dado** o mesmo pedido, **Quando** um Comercial que não pediu abre o evento, **Então** lê o motivo, quem pediu e
   o modo e valor da devolução, mas não o nome nem o PIX da cliente; quem pediu, o Financeiro e o Superadmin leem tudo.
4. **Dado** o evento na agenda (Mês, Dia, Lista, busca), **Then** aparece o selo "Cancelamento pedido" com a data do
   pedido no tooltip, para toda a equipe interna.
5. **Dado** um artista escalado no evento, **Quando** abre o portal (Agenda, Convites, Histórico), **Then** vê
   "Evento em confirmação — entre em contato com a produção", também se o evento já passou; nunca o motivo.
6. **Dado** um pedido de todos os dias numa venda de vários dias, **Then** todos os dias da venda aparecem com o selo
   e o aviso do portal; um pedido de um dia só marca só aquele dia.
7. **Dado** o pedido pendente, **Then** o evento continua aceitando tudo (escalar, convidar, figurino, avaliação,
   venda) e aparece em todas as listas.

---

### História 3 — O Superadmin decide, e quem pediu fica sabendo (Prioridade: P1)

O Superadmin abre o evento pelo aviso, pela faixa ou pela fila "Cancelamentos". Ele pode **cancelar** — o diálogo de
cancelar abre vazio, com o que o Comercial pediu ao lado, só leitura —, **recusar** (com confirmação e motivo
opcional) ou, se o evento estiver vazio, **excluir**. Em qualquer saída, o pedido fecha, o aviso do pedido fica como
lido, os sinais da espera somem e quem pediu recebe uma resposta no sino. Ninguém mais fecha o pedido — nem quem pediu.

**Por que esta prioridade**: sem a decisão chegar a quem pediu, o Comercial não sabe se diz à cliente que está
cancelado; sem fechar o pedido em cada dia cancelado, sobra pedido aberto em evento que já caiu.

**Verificação**: cenários 18–28.

**Cenários de aceite**:

1. **Dado** um pedido pendente, **Quando** o Superadmin clica "Recusar pedido", **Then** abre uma confirmação com
   motivo opcional; confirmada, o pedido fecha, quem pediu recebe "Pedido recusado — <título>: <motivo>", o aviso dos
   Superadmins fica lido, e selo, frase da faixa e aviso do portal somem.
2. **Dado** o pedido, **Quando** quem pediu (ou outro Comercial) tenta recusar ou desistir, **Then** é recusado (403)
   e nada muda.
3. **Dado** o pedido, **Quando** o Superadmin abre "Analisar e decidir", **Then** o diálogo de cancelar vem com o modo
   de devolução, o alcance e as multas sem nada marcado, e mostra acima o que o Comercial pediu (motivo, alcance,
   devolução completa) só para leitura.
4. **Dado** o Superadmin cancela o evento, **Then** o pedido fecha e quem pediu recebe "Evento cancelado — <título>
   (dd/mm)", com link para a tela do cancelado; num dia só, "Dia dd/mm cancelado — <título>: a venda segue nos outros
   dias" ou, no 1º dia, "…: a venda passou para o dia dd/mm".
5. **Dado** uma venda de três dias com um pedido de todos os dias no 1º dia e outro pedido só do 3º dia, **Quando** o
   Superadmin cancela todos os dias, **Then** os dois pedidos fecham e cada autor recebe a sua resposta (uma por
   pedido); **quando** ele cancela só o 2º dia, **Then** os dois pedidos continuam pendentes.
6. **Dado** um evento vazio com pedido, **Quando** o Superadmin o exclui, **Then** quem pediu recebe "Evento
   excluído — <título>", sem link, e nenhum aviso do pedido fica no sino.
7. **Dado** dois Superadmins decidindo o mesmo pedido ao mesmo tempo, **Then** só uma decisão vale, a outra recebe
   "o pedido já foi decidido" e quem pediu recebe uma só resposta.
8. **Dado** o evento marcado com pedido, **Quando** o Superadmin o devolve ao Google, **Then** a marca sai e o pedido
   continua pendente.

### Casos de borda

- **O pedido do 1350**, feito antes do deploy: aparece na fila, no quadro do evento, na faixa e no selo, sem alcance e
  "sem devolução informada"; nenhum aviso retroativo nasce.
- **Autor sem acesso** (desligado depois de pedir) ou apagado: a decisão segue; a resposta simplesmente não sai.
- **O Superadmin pede** (pela API ou em "Ver como: Comercial"): o pedido é aceito e o aviso vai a todos os
  Superadmins, inclusive a ele; se ele mesmo decidir, não recebe a resposta.
- **Venda virtual**: o pedido leva só o motivo; o cancelamento faz o estorno.
- **Pedido no 1º dia "só este dia" e o 1º dia é cancelado**: os pedidos dos outros dias seguem pendentes, com o
  alcance gravado, inclusive o do dia que vira o 1º.
- **Deploy cruzado**: tela velha × servidor novo — pedir e recusar pelo caminho velho continuam (sem devolução);
  a faixa velha ignora os pedidos; o selo velho não desenha nada. Tela nova × servidor velho — o pedido mostra o erro
  e não finge que gravou; a faixa nova sem a chave dos pedidos mostra só a do sumiço.
- **O evento com pedido é cancelado pelo caminho velho de cancelar** (sem passar pelo pedido): o pedido fecha do mesmo
  jeito (o fecho mora no cancelamento, não no botão).
- **Pedido em evento passado sem cachê pago**: aceito; o portal mostra "Evento em confirmação" no Histórico.

## Requisitos *(obrigatório)*

### Requisitos funcionais

**Pedir**

- **FR-001**: Comercial e Superadmin DEVEM poder pedir o cancelamento de um evento não cancelado pelo item
  "Solicitar cancelamento" da tela do evento (o atual "Solicitar exclusão"), com o texto "Pede ao Superadmin que
  cancele este evento — ele recebe o aviso no sino".
- **FR-002**: O pedido DEVE exigir motivo (texto de várias linhas).
- **FR-003**: O pedido DEVE exigir a devolução combinada completa (Q2 = B), na forma do cancelar da 306: modo
  Tudo/Parte/Nada sem opção marcada; valor em Parte; nome e PIX de quem recebe em Tudo e Parte; num dia só, só Parte ou
  Nada e o novo valor da venda (obrigatório). Venda virtual: só o motivo (premissa 4). O pedido confere a forma, não o
  dinheiro.
- **FR-004**: Numa venda de vários dias, o pedido no 1º dia (com outro dia vivo) DEVE exigir a escolha, sem opção
  marcada, entre "Todos os N dias da venda" e "Só este dia — a venda passa para o dia dd/mm"; em outro dia, vale só
  para ele. O alcance DEVE ser gravado com o pedido e não mudar quando o 1º dia mudar.
- **FR-005**: O pedido DEVE ser recusado, sem gravar nada nem avisar ninguém, quando: o evento está cancelado; é
  ensaio; algum dia que ele alcança tem cachê pago ao elenco (a mesma régua do cancelar); já existe pedido pendente
  (nunca sobrescreve — o segundo recebe "Já existe um pedido de <nome>"). Para ensaio e cachê pago, a tela DEVE mostrar
  o item desabilitado com a frase do servidor.
- **FR-006**: Evento marcado como "sumiu do Google" DEVE aceitar pedido sem mudar a marca; "Devolver ao Google" NÃO
  DEVE fechar o pedido.
- **FR-007**: Pedir e recusar NÃO DEVEM chamar o Google nem mandar e-mail.
- **FR-008**: Na mesma gravação do pedido, cada Superadmin ativo DEVE receber um aviso no sino (urgente se o evento é
  em 7 dias ou menos) com a data, a venda, o recebido, os escalados (sem a vaga automática do técnico de som), o
  alcance, o motivo e quem pediu — nunca nome nem PIX. Pedido novo depois de uma recusa gera aviso novo.
- **FR-009**: Pedido e recusa DEVEM ficar no histórico do evento e na auditoria (com modo e valor da devolução, nunca
  nome nem PIX), com a hora certa.

**Ver enquanto espera**

- **FR-010**: Toda a equipe interna que abre o evento DEVE ver "Cancelamento pedido — aguardando o Superadmin", a data
  e o alcance; motivo e quem pediu DEVEM sair do servidor só para Comercial, Financeiro e Superadmin pelo papel em uso
  (Q6 = C), no detalhe do evento e na fila da página de Cancelamentos.
- **FR-011**: Da devolução combinada, modo e valor DEVEM sair só para Comercial, Financeiro e Superadmin; nome e PIX
  só para Superadmin, Financeiro e quem fez o pedido (premissa 5).
- **FR-012**: A faixa vermelha do topo DEVE mostrar, sempre que houver pedido pendente e só para Comercial e
  Superadmin, "1 pedido de cancelamento aguarda decisão" / "N pedidos de cancelamento aguardam decisão": um pedido →
  link para o evento; vários → lista com um link por evento; sem motivo, autor nem dinheiro; a frase do sumiço
  continua igual; a altura da faixa não muda; no celular as frases encurtam.
- **FR-013**: O selo "Cancelamento pedido" (tooltip com a data do pedido) DEVE aparecer para a equipe interna onde o
  selo de situação do evento já aparece (premissa 9).
- **FR-014**: O elenco escalado DEVE ver "Evento em confirmação — entre em contato com a produção" no portal (Agenda,
  Convites, Histórico) enquanto houver pedido pendente, também em evento passado; nunca o motivo.
- **FR-015**: O pedido de todos os dias DEVE marcar (selo e portal) todos os dias vivos da venda; o pedido de um dia
  só marca só aquele dia.
- **FR-016**: O pedido pendente NÃO DEVE trancar o evento nem tirá-lo de lista nenhuma.

**Decidir**

- **FR-017**: Só o Superadmin, pelo papel real, DEVE poder fechar um pedido; recusar DEVE passar por confirmação com
  motivo opcional e responder a quem pediu com o motivo. Quem pediu e os outros Comerciais NÃO DEVEM poder recusar nem
  desistir (Q5 = D).
- **FR-018**: "Analisar e decidir" DEVE abrir o diálogo de cancelar da 306 sem nada marcado (D27) e mostrar, só para
  leitura e sem botão de copiar, o que o pedido trouxe (motivo, alcance, devolução completa).
- **FR-019**: Todo cancelamento DEVE fechar o pedido de cada dia que encerra (o aviso do pedido fica lido, quem pediu
  recebe uma resposta por pedido, com o que caiu e, no 1º dia sozinho, para onde foi a venda); o pedido de um dia que
  não caiu continua pendente.
- **FR-020**: Excluir um evento vazio com pedido DEVE fechar o pedido e responder a quem pediu, sem link; o sync do
  Google não responde.
- **FR-021**: Em qualquer saída (recusar, cancelar, excluir), o aviso do pedido DEVE ficar lido (não apagado, salvo na
  exclusão) e selo, frase da faixa e aviso do portal DEVEM sumir sem passo extra.
- **FR-022**: Decisões e pedidos ao mesmo tempo DEVEM ter um vencedor só: o outro recebe uma recusa clara ("já existe
  um pedido" / "o pedido já foi decidido") e nenhum aviso nem resposta em dobro.
- **FR-023**: Quem decide sendo o autor do pedido NÃO DEVE receber a resposta; autor sem acesso não recebe resposta, e
  a decisão segue.

**Nomes, páginas e compatibilidade**

- **FR-024**: Os rótulos DEVEM passar a dizer "Cancelamento pedido" (no lugar de "Exclusão solicitada") e a página e
  as duas entradas de menu "Exclusões e cancelamentos" DEVEM virar "Cancelamentos"; a fila "Aguardando decisão" DEVE
  mostrar o alcance e a devolução combinada (pela régua do FR-011) e o link "Decidir".
- **FR-025**: O caminho velho de pedir e recusar DEVE continuar funcionando por um deploy, aceitando só o motivo (o
  pedido nasce "sem devolução informada"); a remoção DEVE ficar registrada no `docs/05`.
- **FR-026**: O pedido existente antes do deploy DEVE continuar pendente e aparecer na fila, no quadro, na faixa e no
  selo, sem alcance e "sem devolução informada", sem aviso retroativo (premissa 6).
- **FR-027**: O texto do diálogo de cancelar sobre o motivo do cancelamento DEVE dizer a régua da 1c-Q9 (só
  Comercial, Financeiro e Superadmin leem).

### Entidades

- **Evento (`CalendarEvent`)** — o pedido continua morando no evento, nas três colunas da 224 (quando, quem, motivo),
  mais **duas**, aditivas e nulas: o **alcance** do pedido (todos os dias / só este dia; nulo = sem pedido ou pedido de
  antes do deploy) e a **devolução combinada** (modo, valor, nome, PIX, novo valor da venda; texto com JSON, padrão da
  casa). Zeradas nas saídas que gravam (recusar, cancelar) e somem com a linha na exclusão. Sem tabela nova.
- **Aviso no sino** — dois kinds novos: o pedido (aos Superadmins) e a decisão (só a quem pediu).

### RBAC *(obrigatório — endpoints novos e alterados)*

- `POST /api/events/<id>/pedido-cancelamento` (nome do plan) — pedir: Comercial e Superadmin, papel real (o gate de
  hoje do "Solicitar exclusão"); 404 → 403 → 409 cancelado (trava da 312) → 400 campos → 409 ensaio / cachê pago /
  pedido pendente.
- `DELETE /api/events/<id>/pedido-cancelamento` — recusar: só Superadmin, papel real; todo outro papel, inclusive o
  autor, 403; sem pedido, 409.
- `POST`/`DELETE /api/events/<id>/solicitar-exclusao` — alias das duas acima por um deploy (corpo velho só com motivo).
- `GET /api/events/<id>` — o bloco do pedido com o corte da Q6 (motivo e autor por `show_comercial`) e da premissa 5
  (nome e PIX por Superadmin/Financeiro/autor); chave opcional do bloqueio (ensaio, cachê pago) para o menu.
- `GET /api/events/cancelamentos` — gate de hoje (Superadmin e Financeiro, papel real); os pendentes com o mesmo corte.
- `GET /api/events/sumidos-google` — gate de hoje da faixa (Comercial ou Superadmin, papel efetivo); chave opcional
  nova dos pedidos, sem motivo, autor nem dinheiro.
- `POST /api/events/<id>/cancelar` e `DELETE /api/events/<id>` — gates sem mudança; passam a fechar o pedido e
  responder a quem pediu.
- Portal — `em_confirmacao` (campo que já existe) passa a valer também para o pedido; o talento não alcança os
  endpoints do pedido.

Linhas na tabela de `docs/01` §4.3.

## Verificação (`verify_315.py`) *(obrigatório — Princípio VIII)*

Arquivo: `specs/315-pedido-de-cancelamento/verify_315.py`, contra `manto_local` (`DATABASE_URL` de `.local-db-url`,
`FLASK_ENV=development`, `MANTO_SEM_THREADS=1`). Login só por `POST /api/auth/login`; escrita conferida por conexão
separada; Google falso e e-mail falso do harness da 306 (falham fechado); limpeza no `finally`.

| # | Cenário | O que prova | Deve falhar? |
|---|---|---|---|
| 1 | Comercial pede com motivo e devolução Parte completa | grava as cinco colunas; histórico e auditoria sem nome/PIX; um aviso por Superadmin ativo, na mesma transação, com o retrato | não |
| 2 | evento em ≤ 7 dias × em 30 dias | aviso urgente × informativo | não |
| 3 | campos: motivo vazio; modo ausente; Parte sem valor; Tudo/Parte sem nome ou PIX; venda virtual só com motivo | 400 com o campo certo; virtual aceito sem devolução | parcial |
| 4 | venda de vários dias: 1º dia sem alcance; "só este dia" sem novo valor ou com Tudo; outro dia | 400 alcance/venda_nova/modo; alcance gravado; satélite vale só para ele | parcial |
| 5 | segundo pedido no mesmo evento, e dois pedidos ao mesmo tempo | 409 "já existe um pedido de <nome>"; um aviso só | **sim** |
| 6 | ensaio; evento com cachê pago (no próprio dia e num dia que o pedido de todos alcança) | 409 ensaio / cache_pago; nada gravado; o detalhe traz o bloqueio com a frase | **sim** |
| 7 | evento marcado (303) | pedido aceito; marca intacta; devolver ao Google não fecha o pedido | não |
| 8 | pedir e recusar | zero chamadas ao Google, zero e-mails | não |
| 9 | evento cancelado | 409 cancelado, nada gravado | **sim** |
| 10 | detalhe por papel (Comercial autor, Comercial colega, Financeiro, Superadmin, Casting, Revendedor, SA "Ver como Casting") | motivo/autor só ao trio; nome/PIX só a SA, Financeiro e autor; prova por mutação do corte | **sim** (leitura) |
| 11 | fila de Cancelamentos (Superadmin, Financeiro; SA "Ver como Casting"); Comercial | o mesmo corte; Comercial 403 | **sim** |
| 12 | faixa: Comercial e SA × Casting, Financeiro, Revendedor | chave dos pedidos com total e itens sem motivo/autor/dinheiro; os outros `pode_ver: false`; a frase do sumiço não muda | não |
| 13 | selo: resumo da agenda (Mês, Dia, busca) e listas com situação | `exclusao_solicitada` no evento com pedido; some na decisão | não |
| 14 | portal: escalado no evento com pedido (futuro e passado) | `em_confirmacao` nas três listas, sem motivo | não |
| 15 | venda de vários dias com pedido de todos os dias | todos os dias com selo e `em_confirmacao`; pedido de um dia só marca só ele | não |
| 16 | pedido não tranca | escalar, convidar, figurino e editar venda seguem aceitos | não |
| 17 | contrato velho | `POST`/`DELETE /solicitar-exclusao` com só `{motivo}` funcionam; pedido "sem devolução" | não |
| 18 | recusar (Superadmin) com motivo | pedido fechado; resposta só ao autor com o motivo; avisos do pedido lidos; selo/faixa/portal limpos | não |
| 19 | recusar pelo autor, por outro Comercial, pelo SA em "Ver como Comercial" | 403 para os dois primeiros (nada muda); o SA real recusa | **sim** |
| 20 | cancelar evento sem grupo com pedido | pedido fechado no fecho; resposta "cancelado" com link; avisos lidos | não |
| 21 | venda de três dias: pedido de todos no 1º + pedido do 3º; cancelar todos; cancelar só o 2º; cancelar só o 1º | uma resposta por pedido; o do dia que não caiu fica; 1º sozinho diz para onde foi a venda | não |
| 22 | excluir evento vazio com pedido | resposta "excluído" sem link; nenhum aviso do pedido sobra | não |
| 23 | duas decisões ao mesmo tempo (recusar × recusar; recusar × cancelar) | uma vence; a outra 409 "já decidido"; uma resposta só | **sim** |
| 24 | autor sem acesso; SA que pede e decide | decisão segue sem resposta; SA não recebe a própria resposta | não |
| 25 | pedido de antes do deploy (semente: só as três colunas) | aparece na fila, no detalhe, na faixa e no selo; sem aviso retroativo; decisão funciona | não |
| 26 | Q5 = D | não existe caminho para o autor desistir | **sim** |
| 27 | regressão | `verify_306`, `verify_312` (incluindo a classificação da rota nova), `verify_303` (cenário 12), `verify_311`/`verify_302` do portal | — |
| 28 | limpeza | usuários, eventos e avisos descartáveis apagados (`roles.clear()` antes do usuário) | — |

Conferência de tela (Browser pane, skill `manto-conferir-tela`): o diálogo de pedir (venda simples, venda de vários
dias, venda virtual, ensaio e cachê pago desabilitados), o quadro do pedido por papel, a faixa com uma e com duas
frases (e em 375 px), o selo no Mês/Dia/busca, o diálogo de cancelar com o pedido acima, a recusa com confirmação, a
fila "Cancelamentos" e o sino; o portal (Agenda, Convites, Histórico) em 375×812.

## Critérios de sucesso *(obrigatório)*

- **SC-001**: Todo pedido novo chega a cada Superadmin ativo no sino no mesmo instante em que é gravado — nenhum
  pedido sem aviso (hoje: o único pedido real está há quinze dias sem ninguém saber).
- **SC-002**: Todo pedido pendente aparece na faixa vermelha de Comercial e Superadmin, em qualquer tela, em até um
  minuto (na hora para quem pediu e quem decide).
- **SC-003**: Nenhuma resposta do sistema entrega motivo, autor, nome ou PIX do pedido a quem não trata do
  cancelamento — zero vazamentos nos cenários de leitura, inclusive com "Ver como".
- **SC-004**: Quem pediu recebe exatamente uma resposta por pedido (recusado, cancelado ou excluído), e nenhum pedido
  pendente sobrevive à decisão de qualquer dia que ele alcança.
- **SC-005**: O pedido nunca escreve no Google nem manda e-mail (zero chamadas nos cenários).
- **SC-006**: O pedido real de 07/10 (1350) passa a aparecer na faixa e na fila no deploy, para o dono decidir.

## Fora de escopo

- O cancelamento em si — devolução, retido, comissão, BV, multa, avisos ao elenco e ao Casting (306/312).
- Quem cancela e o que conta como "vazio" para excluir (303/306).
- Dar a quem pediu um jeito de desistir (Q5 = D) ou um lembrete periódico no sino.
- Abrir a fila "Cancelamentos" ou a prévia do cancelamento ao Comercial.
- Pré-preencher o diálogo de cancelar com o que o pedido trouxe (D27).
- O Jinja legado (o botão "Excluir evento" da tela antiga já recusa o Comercial no servidor; código velho não se limpa
  de passagem).
- Tirar o caminho velho `/solicitar-exclusao` (fica para o deploy seguinte, registrado no `docs/05`).

## Docs a atualizar

`docs/01` (cabeçalho e head; §2.2 as duas colunas; §3.3 os endpoints do pedido e o alias; §3.13.5 os dois kinds;
§3.15 o `em_confirmacao`; o contrato da faixa; §4.3 RBAC), `docs/02` (menu, quadro, diálogos, faixa, selo, página
"Cancelamentos", sino, portal), `docs/03` (entrada no topo + índice), `docs/04` (fluxo do pedido; invariantes: pedido
pendente nunca sobrevive à decisão, só o Superadmin o fecha, todo pedido tem aviso na mesma transação, o alcance é
gravado, pedido não tranca), `docs/05` (quitar a parte do pedido da dívida 76; registrar o alias a remover e o que o
converge achar).

## Premissas

- Os 3 Superadmins, 3 Comerciais e 0 Financeiros ativos de hoje (22/10) dão a escala: o pedido é raro (2 cancelamentos
  em outubro), e os dois kinds novos não mudam o volume do sino.
- Nenhuma venda de vários dias futura existe hoje (22/10): o alcance nasce quase sem uso, mas a regra vale desde já
  porque o cancelamento da 306 já cancela um dia só.
- Nenhum evento futuro tem cachê pago hoje; a recusa de cachê pago pesa sobretudo em pedido de evento passado.
- O nome técnico do pedido no código não pode colidir com o corpo do cancelar da 306 (que já se chama "pedido de
  cancelamento" no núcleo) — decisão do plan.
