# Feature 303 — Evento com venda que some do Google fica no sistema, a equipe vê, e o Superadmin o devolve ao Google

**Branch**: `303-sync-nao-apaga-venda` (da `main`) · **Created**: 2026-09-29 · **Status**: Rascunho ·
**Migration**: `a7c3e91f4d28` (aditiva: uma coluna e um índice parcial em `calendar_events`) ·
**Nível**: 1 (feature — agenda, notificações e portal) — constituição, Princípio VI

**Input**: plano do backlog de setembro (`docs/PLANO_BACKLOG_SETEMBRO.md`), decisões D1 (parte), D17,
D18, D21, D24 e D29, e as respostas do dono de 29 e 30/09.

**Esta é a primeira de três entregas.** Em 30/09 o dono dividiu o trabalho: esta feature para de
perder evento e não toca em dinheiro; a segunda entrega traz o cancelamento com devolução, a
comissão sobre o retido e a DRE; a terceira, o selo e o filtro de cancelados. O texto completo de
antes da divisão está congelado em `entregas-2-e-3-rascunho.md`, e a pesquisa em `pesquisa/`.

## O pedido, nas palavras do dono *(obrigatório)*

Em 22/09, sobre cancelamento: **"passa pelo sistema de verdade"** — evento com venda que some do
Google vira pedido para o dono decidir, em vez de ser apagado (D1). Em 29/09 o dono puxou a trava
para a onda 1 (D17), escolheu que o evento **fica na agenda, marcado, e segue contando na venda**
(D18), e acrescentou:

> "Acho que não deve ser apenas um aviso no sino. Deve ser algo mais marcante."
>
> "Normalmente quando um evento muda de data, enviamos mensagens no particular do WhatsApp
> perguntando se a pessoa tem disponibilidade de trocar. Acho que vale o aviso no portal de evento
> em confirmação — entre em contato com a produção."

O aviso marcante escolhido: **faixa no topo de todas as telas + sino**, para **Superadmin e
Comercial**; a decisão é só do Superadmin.

O sintoma, como a equipe vê: um evento vendido desaparece do sistema sem ninguém ter mandado apagar,
e com ele somem os comprovantes, o contrato e a escala. Em produção (29/09, só leitura):

- 5 eventos apagados por sumiço no Google desde 01/08 (2 em agosto, 3 em setembro).
- Em 17/09 foi o `(R&I) GABBY + PANDY + GATUNO` (1244), com venda e comissão: movido no Google de
  13 para 19/09 e depois tirado de lá. A comercial recriou o evento do zero em 24/09 (1336, 07/11)
  — o que estava preso ao 1244 não voltou.
- 56 eventos futuros têm R$ 172.447,24 em comprovantes anexados e estão expostos à mesma regra.
- "Solicitar exclusão" e "Cancelar" (feature 224) têm **zero** uso: a equipe cancela apagando no
  Google.

Há um segundo caminho de perda, menos visível: evento que **muda de mês** no Google. Em cada mês, a
limpeza apaga o evento gravado naquele mês (pela data do banco) que não está na lista do Google; ele
só escapa se o sync do mês de destino o encontrar antes, pelo id, e gravar a data nova.

- **Adiado para um mês posterior**: o mês antigo é limpo primeiro e apaga o evento; o mês novo o
  importa como evento novo, sem venda, comprovante nem escala.
- **Antecipado para um mês já passado**: o ciclo automático nunca busca esse mês — o evento é
  apagado e não volta. No "Limpar eventos fantasma", só escapa se o mês de destino já tiver outro
  evento no banco.

Esse caminho **aconteceu em produção em 10/09**: o evento 1275 (`(CORP) FLORES - JARDIM
ENCANTADO…`), de setembro, foi movido no Google para 22/10 às 21h28; seis minutos depois a limpeza
de setembro o apagou, e o sync de outubro o importou de novo como o evento 1287, **sem valor de
venda, sem vendedor e sem escala** — a comissão da venda original (R$ 63,45) foi cancelada junto. O
evento continua existindo no Google até hoje (sonda de 30/09).

E um terceiro, achado na verificação: o botão **"Sincronizar"** de um evento não confere se o evento
ainda existe. O Google devolve o evento apagado com a situação "cancelado" — nos casos sondados em
30/09, ainda com o título e as datas —, e o sistema o "sincroniza" como se estivesse vivo, sem
avisar. Quando o Google devolve só o mínimo (o que ele também pode fazer), o título vira "Sem
título", as datas se perdem, a escala é reconciliada pelo título e sai e-mail de remoção para
artista de verdade.

(Verificado contra o código em 29/09: `app/calendar/sync.py:51-79`, `app/calendar/routes.py:341-390,
2229-2236, 2247, 2294-2295, 4191-4208`, `app/api/admin_config_write.py:93-99`. Sonda e contagem de
30/09: `contagem_pre_deploy.py`, resultado em `research.md` R17.)

## Clarifications

### Session 2026-09-29

- Q: Quando o sync decide entre apagar e manter um SHOW que sumiu do Google, a vaga "Técnico de Som"
  que o sistema preenche sozinho conta como "alguém escalado"? → A: **Não conta no sync** — só conta
  quem a equipe escalou (inclusive a vaga "Técnico de Som (Presença)" quando designada, ou outro
  técnico no lugar do padrão). O botão Excluir da 224 continua como está.

As outras quatro respostas do clarify (base da comissão do cancelado, BV negociado, devolução vazia
e devolução alterável) e as quatro sobre relatórios (mês do retido, card e botão, imposto, retido
como venda) são da segunda e da terceira entrega e estão em `entregas-2-e-3-rascunho.md`.

### Session 2026-09-30 (pesquisa do plano)

- Q: Como dividir a entrega? → A: **Três entregas** — (1) a trava do sync, sem mexer em dinheiro;
  (2) o dinheiro do cancelamento; (3) sinalizar e filtrar cancelados. Cada uma com o seu deploy.
- Q: Enquanto a segunda entrega não sobe, o que o evento marcado oferece? → A: **Só "Devolver ao
  Google Agenda"** — o evento que foi cancelado de verdade fica marcado, com a faixa acesa, até a
  segunda entrega. Nenhum cancelamento sai com a regra velha.
- Q: Depois de cancelado, dá para corrigir comprovante esquecido ou BV negociado? → A: **Sim, só o
  Superadmin** — entra na segunda entrega.

### Session 2026-09-30 (checklists)

A revisão dos checklists (`checklists/integridade.md`, `ux.md`, `regressao.md`) achou três pontos de
regra de negócio, respondidos pelo dono:

- Q: Evento sem mais nada, mas com comissão já paga ao vendedor, é apagado quando some do Google? →
  A: **Apaga como hoje** — e o estorno da comissão contra o vendedor sai, como hoje. A comissão não
  entra no que segura o evento (FR-001).
- Q: SHOW sem mais nada, só com o técnico de som que o sistema pôs sozinho, mas com cachê lançado ou
  pago nessa vaga, é apagado? → A: o caso não acontece — nas palavras do dono, **"não é possível um
  evento com valores pagos sumir da agenda. Se foi pago é porque foi realizado. O único que nós
  podemos ter pago e ter sido cancelado é a comissão do vendedor"**. A regra de 29/09 fica como
  está: a vaga automática do técnico nunca conta (FR-001).
- Q: Entre esta entrega e a segunda, quem segura o cachê e a comissão de um evento marcado que foi
  cancelado de verdade? → A: **o Superadmin**, conferindo a faixa antes de fechar a Planilha de
  Pagamentos — o Financeiro não vê a faixa (§Premissas).

## Cenários e Verificação *(obrigatório)*

As Histórias 4, 7 e 8 e a metade "cancelar e devolver o dinheiro" da História 3 foram para as
entregas seguintes; a numeração foi mantida para a pesquisa continuar legível.

### História 1 — Evento com dinheiro que some do Google continua no sistema (Prioridade: P1)

Alguém apaga no Google Agenda um evento que tem venda, comprovante, contrato, gente escalada ou que
faz parte de um grupo comercial. No próximo ciclo do sync, o evento **não** é apagado: continua na
agenda, com tudo o que estava preso a ele, e ganha a marca "Sumiu do Google Agenda" com a data em
que o sistema percebeu. Até a decisão, ele segue valendo como antes em venda, comissão, Planilha e
DRE.

**Por que esta prioridade**: é a única perda de dinheiro em curso no backlog; tudo o mais depende de
o registro existir.

**Verificação**: cenários 1, 1b, 3, 4, 5, 6, 7, 7a, 7b, 13, 13b, 13c, 14 e 15 do `verify_303.py`.

**Cenários de aceite**:

1. **Dado** um evento com valor de venda que não está mais no Google, **Quando** o sync roda,
   **Então** o evento continua no banco com venda, comprovantes, contrato e escala intactos, e
   está marcado "Sumiu do Google Agenda" com a data de hoje.
2. **Dado** um evento sem venda mas com um comprovante de pagamento, um contrato, uma pessoa
   escalada pela equipe, ou que é líder ou satélite de um grupo comercial, **Quando** some do Google
   e o sync roda, **Então** o evento continua no banco, marcado.
3. **Dado** um evento **vazio** (sem venda, comprovante, contrato, escalado nem grupo) que sumiu
   do Google — inclusive um SHOW cuja única pessoa é o técnico de som que o sistema pôs sozinho, e
   inclusive um evento cuja comissão já foi paga ao vendedor —, **Quando** o sync roda, **Então** ele
   é apagado como hoje (com o estorno da comissão contra o vendedor, como hoje).
4. **Dado** um evento marcado, **Quando** alguém da equipe o abre, **Então** vê a marca e o dia em
   que o sistema percebeu o sumiço; a marca não se confunde com uma "exclusão solicitada" por uma
   pessoa.
5. **Dado** um evento que não está mais no Google, marcado ou não, **Quando** alguém clica em
   "Sincronizar" nele, **Então** nada do evento muda (título, datas, escala) e a tela diz que ele
   não está mais no Google Agenda.

---

### História 2 — A equipe não tem como não ver (Prioridade: P1)

No mesmo ciclo em que o sistema percebe o sumiço, Superadmin e Comercial passam a ver, **em todas
as telas do sistema interno**, uma faixa fixa no topo, em destaque de alerta: quantos eventos
sumiram do Google e o acesso a cada um (título e data). A faixa não se dispensa: some sozinha
quando não houver mais evento marcado. Junto, cada Superadmin e cada Comercial recebe **um** aviso
no sino com o título, a data e o que está preso ao evento (venda, quanto já foi recebido, quantas
pessoas escaladas). O Comercial vê a faixa, o aviso e a marca, e pode contar ao Superadmin por que
o evento sumiu; o botão de decisão é só do Superadmin.

**Por que esta prioridade**: um aviso no sino se perde entre os outros; o evento marcado precisa de
decisão rápida porque o elenco está esperando (História 6).

**Verificação**: cenários 2, 2b e 17 do `verify_303.py` e a conferência de tela.

**Cenários de aceite**:

1. **Dado** um evento que acabou de ser marcado, **Quando** um Superadmin ou um Comercial abre
   qualquer tela do sistema interno, **Então** vê a faixa com "1 evento sumiu do Google Agenda" e o
   link para ele.
2. **Dado** o mesmo evento, **Quando** o ciclo do sync termina, **Então** cada Superadmin e cada
   Comercial tem exatamente uma notificação nova para ele no sino.
3. **Dado** um evento já marcado, **Quando** o sync roda de novo (e de novo), **Então** nenhuma
   notificação nova é criada e a faixa continua igual.
4. **Dado** que o último evento marcado foi resolvido, **Quando** qualquer tela é aberta, **Então**
   a faixa não aparece e o aviso do sino já está como lido.
5. **Dado** um usuário de outro papel (Figurino, Casting, Financeiro...), **Quando** abre o sistema,
   **Então** não vê a faixa.

---

### História 3 — O Superadmin devolve o evento ao Google (Prioridade: P1)

Na tela do evento marcado, o Superadmin vê o que está em jogo — venda, quanto a cliente já pagou,
comissão, BV, quem está escalado — e pode **devolver o evento ao Google Agenda**: o sistema o recria
no Google com o título, a data, o horário, o local e a descrição que estão no sistema agora, e tira
a marca; o evento volta a ser sincronizado normalmente. Antes de confirmar, a tela mostra o título e
a data que vão ao Google, e avisa se essa data já passou.

Se o evento foi cancelado de verdade, **nesta entrega ele fica marcado**: o "Cancelar e devolver o
dinheiro" do evento marcado chega na segunda entrega, e até lá o evento marcado não pode ser
cancelado nem excluído — a tela diz isso.

**Por que esta prioridade**: sem a saída, o evento que sumiu por engano fica preso na marca.

**Verificação**: cenários 10, 10a a 10i, 11 e 12 do `verify_303.py`.

**Cenários de aceite**:

1. **Dado** um evento marcado, **Quando** o Superadmin escolhe "Devolver ao Google Agenda" e
   confirma, **Então** o evento passa a existir no Google com título, data, horário, local e
   descrição atuais, a marca some, e o histórico registra quem devolveu e quando.
2. **Dado** um evento marcado que já tinha voltado ao Google sem o sistema ter percebido, **Quando**
   o Superadmin o devolve, **Então** nada é criado em dobro no Google, a marca some, e — se o evento
   foi editado no sistema enquanto estava marcado — o Google fica com os dados do sistema.
3. **Dado** que o Google recusa ou não responde, **Quando** o Superadmin devolve, **Então** a marca
   continua e a tela diz que não deu, sem mostrar erro técnico.
4. **Dado** um usuário que não é Superadmin, **Quando** tenta devolver ao Google, **Então** é
   recusado.
5. **Dado** um evento marcado, **Quando** qualquer pessoa tenta cancelá-lo ou excluí-lo, **Então** é
   recusada, com a explicação de que o cancelamento do evento marcado chega na entrega seguinte.

---

### História 5 — Evento que só mudou de data não vira sumiço (Prioridade: P2)

A comercial adia um evento no Google, inclusive para outro mês. O sistema não o trata como sumiço:
não apaga, não marca, não avisa. O evento chega à data nova **no mesmo registro**, com venda,
comprovantes e escala. Se um evento marcado voltar a aparecer no Google (o mesmo evento, não uma
cópia), a marca some sozinha e o histórico registra por quê.

**Por que esta prioridade**: adiamento é rotina; sem isto, a faixa acenderia a cada adiamento e o
adiamento para outro mês continuaria destruindo o evento.

**Verificação**: cenários 8, 9 e 13d do `verify_303.py`.

**Cenários de aceite**:

1. **Dado** um evento de setembro que foi movido no Google para novembro, **Quando** o sync roda,
   **Então** o evento continua no banco, com a data de novembro, a mesma venda e os mesmos
   comprovantes, sem marca, sem faixa e sem notificação.
2. **Dado** um evento marcado, **Quando** o sync volta a encontrá-lo no Google, **Então** a marca
   some, a faixa deixa de contá-lo, e o histórico do evento diz que ele reapareceu.
3. **Dado** um evento que sumiu, reapareceu e sumiu de novo, **Quando** o sync roda, **Então** há um
   aviso novo no sino para o segundo sumiço.

---

### História 6 — O elenco sabe que o evento está em confirmação (Prioridade: P2)

Quem está escalado continua vendo o evento marcado no portal do artista, com o aviso **"Evento em
confirmação — entre em contato com a produção"**. É o complemento da mensagem que a produção já
manda no WhatsApp: o artista não perde um evento que existe, e não vai às cegas a um que pode não
acontecer. Quando o Superadmin devolve ao Google (ou o evento reaparece), o aviso some.

Marcar e desmarcar, por si, não mandam e-mail nem mensagem ao elenco: o artista fica sabendo pelo
aviso no portal e pela mensagem que a produção manda à parte. O que o sync já manda hoje continua:
quando o evento reaparece no Google com data, horário ou local diferentes dos do sistema, o elenco
com convite aceito recebe o e-mail de alteração de sempre.

**Por que esta prioridade**: o caso 1246 (Merida + Cavalo) mostrou o custo de o elenco ir a um
evento que mudou — multa mais cachê.

**Verificação**: cenários 24 e 24b do `verify_303.py` e a conferência do portal em 375×812 e 320 px.

**Cenários de aceite**:

1. **Dado** um evento marcado com um artista escalado, **Quando** o artista abre o portal,
   **Então** vê o evento com o aviso "Evento em confirmação — entre em contato com a produção", na
   agenda, nos convites e no histórico.
2. **Dado** o mesmo evento devolvido ao Google, **Quando** o artista abre o portal, **Então** vê o
   evento sem o aviso.
3. **Dado** um artista que não está escalado no evento, **Quando** abre o portal, **Então** não vê
   nada do evento.
4. **Dado** um evento cancelado que terminou nos últimos 7 dias, **Quando** o artista abre o portal
   ou tenta avaliar, **Então** o evento não aparece como "a avaliar" e a nota é recusada.

---

### Casos de borda

- **Recriado à mão no Google (id novo)** — o caso do 1244: o sistema importa o evento novo como
  hoje e o antigo continua marcado. Não há fusão automática. A tela do evento marcado orienta, em
  passos: (1) acertar no evento antigo a data, o horário e o local que valem agora — a devolução usa
  o que está no sistema; (2) esvaziar o evento recriado — tirar dele a venda, os comprovantes, o
  contrato e a escala lançados em duplicidade — e só então apagá-lo no Google: vazio, o sistema o
  remove na sincronização seguinte. Apagado ainda com algo dentro, ele também fica marcado, e
  marcado não pode ser excluído; a saída, nesse caso, é devolvê-lo ao Google, esvaziá-lo e apagar de
  novo; (3) só então devolver o antigo ao Google — é ele que guarda os comprovantes, o contrato e a
  escala.
- **Evento marcado editado no sistema**: só título, data, horário, local e descrição escrevem no
  Google (aba Comercial, escala e clientes não). Enquanto marcado, a edição salva no sistema e
  **não** é escrita no Google — a devolução recria o evento com os dados atuais —, sem aviso de
  falha e sem desfazer troca de tipo. A tela do evento diz isso a quem edita. Se, antes da
  devolução, o evento reaparecer sozinho no Google, vale o Google e a edição se perde (FR-006).
- **Evento marcado que reaparece sozinho no Google** (na mesma data, em outra data ou em outro mês):
  a marca sai e o evento recebe os dados do Google no mesmo passo, como em qualquer sincronização —
  inclusive por cima do título, da data, do horário, do local e da descrição editados no sistema
  enquanto ele estava marcado (FR-008). Quando o evento volta sozinho, vale o Google; quando o
  Superadmin devolve, vale o sistema (FR-043). Consequências, como hoje: o elenco com convite aceito
  é avisado da mudança de data; e, em evento que nasceu no Google, a vaga de personagem criada
  enquanto marcado que não está no título do Google é apagada, com e-mail de remoção. Risco aceito
  (padrão da verificação de 29/09, item 12: vale o Google, como hoje), registrado no `docs/04`.
- **Evento marcado que fica vazio** (a equipe tira a venda, os comprovantes, o contrato e a escala
  enquanto ele está marcado): a marca não é reavaliada — a limpeza pula evento marcado e a FR-045
  continua valendo; a FR-007 vale só para evento ainda não marcado. Ele sai como qualquer marcado: o
  Superadmin devolve ao Google e, já sem a marca, exclui pelo botão da 224, que o tira do Google
  também.
- **Evento marcado cuja data passa**: continua valendo como qualquer evento não cancelado (FR-005; a
  marca não muda nada além do que esta spec lista) — entra no histórico do portal com o aviso, conta
  como trabalhado e aceita avaliação. Se o evento não aconteceu, a correção vem com o cancelamento,
  na segunda entrega; o "já trabalhou com a Manto" ligado nesse meio-tempo não se desliga sozinho
  (dívida no `docs/05`).
- **Solicitação de exclusão (224) em evento marcado**: nada muda nos dois endpoints — o Comercial
  continua podendo solicitar a exclusão (o motivo fica no histórico; é um jeito de contar ao
  Superadmin por que o evento saiu do Google) e o Superadmin continua podendo recusar o pedido;
  nenhum dos dois toca a marca, a faixa nem o aviso. "Aprovar" o pedido é cancelar ou excluir, que a
  FR-045 recusa: enquanto o evento estiver marcado, o botão "Analisar e decidir" do banner da
  solicitação fica desabilitado com o mesmo motivo do item "Excluir ou cancelar". O banner da
  solicitação continua aparecendo, abaixo do banner da marca; a situação mostrada nas listas é
  "sumiu do Google" (FR-033) e volta a "exclusão solicitada" quando a marca sai.
- **Botão "Sincronizar" do evento marcado**: continua existindo; confere o próprio evento no Google
  e, se ele não está lá, não altera nada e diz isso. Se o evento voltou, tira a marca e sincroniza.
  O link "Editar no Google Agenda" não aparece enquanto o evento está marcado.
- **Evento já devolvido ou já resolvido em outra aba**: o segundo clique em "Devolver" não cria nada
  de novo; a tela atualiza e mostra o evento sem a marca.
- **O Google cria o evento, mas a resposta se perde** (tempo esgotado): a marca continua e a
  mensagem manda conferir na Agenda se o evento apareceu antes de tentar de novo — se apareceu,
  apagá-lo lá e devolver de novo. O evento criado sem par no sistema seria importado como evento
  novo e vazio, que a limpeza remove depois de apagado — risco registrado.
- **Evento de dia inteiro** devolvido ao Google volta como dia inteiro, não como bloco de 24 horas.
- **Evento sem data ou com data inválida** não pode ser devolvido: a tela manda acertar a data antes.
- **Escala criada enquanto o evento estava marcado**: depois da devolução, o sync não pode apagar
  vaga de personagem que não está no título nem mandar e-mail de remoção por isso. A proteção vale
  só para a devolução: se o evento reaparece sozinho, vale o Google (item acima).
- **Evento no passado** que some do Google (percebido pelo "Limpar eventos fantasma" de
  `/admin/sync`): mesma regra — tem dinheiro, fica e avisa; devolver ao Google vale mesmo no passado.
  A contagem de 30/09 (só leitura, contra o Google real) achou **zero** eventos passados fora do
  Google: os 380 eventos de janeiro a agosto estão todos lá. Por isso a primeira rodada do "Limpar
  eventos fantasma" não precisa de regra especial (sem sino, sem e-mail de mudança de data). A
  contagem se repete no dia do deploy. Se qualquer das três linhas deixar de ser zero (eventos
  passados com dinheiro fora do Google; eventos que mudariam de data com elenco de convite aceito;
  inconclusivos), o deploy sobe do mesmo jeito — o ciclo automático não percorre mês passado — e o
  "Limpar eventos fantasma" **não é rodado** até o dono decidir, com a lista, entre rodar com a
  regra normal (cada evento é marcado e avisa) ou resolver os eventos da lista à mão antes. Esta
  entrega não tem "primeira rodada sem sino"; se o dono quiser isso, vira a correção 303b.
- **Evento cancelado** ausente do Google: continua ignorado, como hoje (foi tirado de lá de
  propósito). Evento marcado que venha a ser cancelado deixa de contar como marcado em todo lugar.
- **Venda virtual**: segue a regra própria de hoje (nunca apagada, divergência registrada) — ver
  Fora de escopo.
- **Ensaio** (evento-filho) que some do Google: não tem venda; segue a regra de evento vazio. O
  pai marcado não arrasta o ensaio, e a devolução do pai não recria ensaio apagado — a tela avisa.
  A FR-045 não cobre a exclusão de ensaio, que tem caminho próprio: na prática ensaio não fica
  marcado (não tem venda, comprovante, contrato nem escala).
- **Evento vazio com ensaio ligado** que some do Google: é apagado junto com o ensaio, sem erro
  (hoje a exclusão estoura quando o ensaio tem histórico, e se repetiria a cada ciclo). A correção
  mora na função única de exclusão (a limpeza e o Excluir da 224 passam por ela) e vale para toda
  exclusão: o Excluir manual de evento vazio cujo ensaio tem histórico deixa de estourar, e toda
  exclusão apaga os avisos do sino daquele evento (hoje só o aviso novo usa essa entidade). Gate,
  regra de vazio, recusa do líder de grupo e remoção no Google não mudam. O ensaio sai por ser filho
  do evento apagado, sem consulta própria ao Google — exceção declarada à FR-002. Se ele continuar
  vivo na Agenda, o sync seguinte o importa de novo como ensaio solto: sem o pai, sem o histórico e
  sem os materiais (dívida no `docs/05`; a contagem pré-deploy lista os pais vazios com ensaio).
- **Google fora do ar ou recusando a consulta** no meio do ciclo: o evento cuja ausência não foi
  confirmada não é apagado nem marcado naquele ciclo — na dúvida, o evento fica. Depois da primeira
  consulta sem resposta, o sistema para de consultar naquela rodada, para não travar o ciclo.
- **Lista do mês incompleta**: a busca do mês não pagina (uma chamada, até 2.500 itens); a
  confirmação individual da FR-002 é o que impede apagar evento vivo que ficou fora da página.
- **Evento que existe no Google mas nunca vem na lista do mês** (série recorrente, página cortada):
  não é apagado nem marcado; se nada mudou, o sistema não o ressincroniza a cada ciclo — só registra.
- **Evento movido para outro calendário** no Google responde como ausente e segue a mesma regra (com
  dinheiro, fica e é marcado; vazio, é apagado): a tela diz "não está mais no Google Agenda", nunca
  "foi apagado".
- **O mesmo evento some, reaparece e some de novo**: cada sumiço é um aviso novo.
- **Dois processos percebem o mesmo sumiço ao mesmo tempo** (ciclo automático e "Limpar eventos
  fantasma"): uma marca só, um aviso só.
- **Convite pendente de evento marcado**: aparece no portal com o mesmo aviso, e os botões de
  aceitar e recusar continuam.
- **"Ver como"**: a faixa segue o papel simulado (Superadmin vendo como Figurino não vê a faixa; o
  aviso continua no sino dele, que é da pessoa).

## Requisitos *(obrigatório)*

Os números pulam: FR-013 a FR-021 e FR-026 a FR-038 estão em `entregas-2-e-3-rascunho.md`.

### Requisitos funcionais

**Trava do sync**

- **FR-001**: O sync NÃO DEVE apagar evento que some do Google Agenda quando o evento tem valor de
  venda, algum comprovante de pagamento, contrato, alguém escalado pela equipe, ou pertence a um
  grupo comercial (líder ou satélite). A vaga "Técnico de Som" que o sistema preenche sozinho com o
  técnico padrão em todo SHOW NÃO conta como escalado; contam a vaga "Técnico de Som (Presença)"
  quando alguém é designado e qualquer técnico posto no lugar do padrão. Comissão já paga ao
  vendedor não segura o evento: apagado, ele gera o estorno contra o vendedor, como hoje.
- **FR-002**: Antes de tratar um evento como sumido, o sistema DEVE confirmar a ausência consultando
  aquele evento no Google. Evento que existe no Google com outra data — em qualquer mês — é mudança
  de data: não é apagado, não é marcado, não gera aviso, e chega à data nova no mesmo registro,
  inclusive quando o mês de destino já passou ou está fora do horizonte do ciclo. A regra vale para
  todo evento, vazio ou não, exceto venda virtual e evento cancelado, que o sync não atualiza.
- **FR-003**: A ausência só está confirmada quando o Google responde que o evento não existe ou que
  está apagado. Qualquer outra resposta é inconclusiva — erro, tempo esgotado, falta de credencial,
  falha ao renovar o acesso — e o sistema NÃO DEVE apagar nem marcar aquele evento naquele ciclo.
- **FR-004**: O evento preservado DEVE ficar marcado "Sumiu do Google Agenda", com a data em que o
  sistema percebeu, visível na tela do evento e nas visões da agenda interna, e distinguível de uma
  exclusão solicitada por uma pessoa.
- **FR-005**: Enquanto marcado, o evento DEVE continuar valendo como antes em venda, comissão,
  Planilha de Pagamentos e DRE.
- **FR-006**: A marca DEVE sumir sozinha quando o sync volta a encontrar o mesmo evento no Google. A
  conferência dos eventos marcados é feita pelo próprio evento a cada ciclo, não pela lista do mês
  (um marcado de setembro deixa de ser listado depois de 01/10). Quando a marca sai sozinha, o
  evento é sincronizado como qualquer outro: valem os dados do Google, inclusive por cima do que foi
  editado no sistema enquanto ele estava marcado (FR-008). Para fazer valer os dados do sistema, o
  caminho é a devolução (FR-043).
- **FR-007**: Evento vazio que some do Google DEVE continuar sendo apagado como hoje, depois da
  confirmação da FR-002, inclusive quando tem ensaio ligado.
- **FR-008**: Enquanto o evento estiver marcado, o sistema NÃO DEVE escrever edições no Google: a
  edição salva no sistema sem aviso de falha e sem desfazer troca de tipo, e a marca continua.
- **FR-039**: O "Sincronizar" de um evento DEVE conferir o próprio evento no Google antes de
  qualquer mudança, para todo evento: ausência confirmada → nada é alterado (nem evento, nem
  escala), nada é apagado nem marcado, e a resposta diz que o evento não está mais no Google Agenda;
  resposta inconclusiva → nada é alterado; evento presente → sincroniza como hoje e, se estava
  marcado, a marca é retirada.
- **FR-040**: Depois da primeira consulta individual sem resposta do Google (rede, erro do serviço
  ou credencial), o sistema DEVE tratar como inconclusivos, sem consultar, os demais eventos daquela
  rodada — a limpeza de um mês, ou a reconferência dos marcados. A rodada seguinte (o mês seguinte)
  volta a consultar: a lista daquele mês é a nova sonda do Google. Recusa que chega na hora para um
  evento só (acesso negado, limite de uso) deixa aquele evento inconclusivo e não interrompe os
  demais.
- **FR-041**: Evento presente no Google cujos dados não mudaram NÃO DEVE ser ressincronizado a cada
  ciclo só por ter ficado fora da lista do mês; cada um é registrado na auditoria
  (`presente_fora_da_lista`), uma vez por evento e dia.
- **FR-042**: O "Limpar eventos fantasma" DEVE informar, por mês, quantos eventos foram removidos,
  quantos foram mantidos e marcados, quantos tiveram a data atualizada, quantos voltaram a ser
  encontrados e quantos ficaram sem confirmação do Google ou com falha. O resumo de cada ciclo
  automático (o registro do ciclo em `/admin/logs`) DEVE trazer, antes da lista de meses (que é
  cortada nos oito primeiros), os totais do ciclo: marcados, com data atualizada, de volta ao
  Google, sem confirmação e com falha. Evento com falha faz o ciclo sair como erro; evento sem
  confirmação não. O evento que fica sem confirmação ciclo após ciclo não tem aviso próprio nesta
  entrega — dívida no `docs/05`.

**Aviso**

- **FR-009**: Enquanto existir ao menos um evento marcado, Superadmin e Comercial DEVEM ver, em
  todas as telas do sistema interno (tudo o que abre dentro do menu lateral; login e folhas de
  impressão ficam de fora), uma faixa fixa no topo, em destaque de alerta, com a quantidade de
  eventos marcados e o acesso a cada um (título e data). A faixa não pode ser dispensada e some
  sozinha quando não houver mais evento marcado. Outros papéis não a veem. Evento cancelado nunca é
  contado.
- **FR-010**: No ciclo em que marca o evento, o sistema DEVE criar uma notificação no sino para cada
  Superadmin e cada Comercial, com título, data, valor de venda, total recebido, número de pessoas
  escaladas, a menção ao contrato quando houver, e o link para o evento — legíveis no painel do sino
  sem abrir o aviso —, uma única vez por sumiço, nunca repetida a cada ciclo. Marca e
  aviso nascem juntos: nunca marca sem aviso, nunca aviso sem marca. Quando a marca sai, o aviso
  fica como lido.

**Decisão**

- **FR-011**: O Superadmin DEVE ver, na tela do evento marcado, o que está em jogo antes de decidir:
  venda, total pago pela cliente, comissão (dita como estimativa quando for), BV e escalados, e,
  quando houver, contrato, comprovantes e grupo comercial; no satélite, que a venda é do grupo e
  está no evento principal — o botão de devolver continua no satélite, porque a devolução é por
  evento.
- **FR-012**: O Superadmin DEVE poder devolver o evento marcado ao Google Agenda: o sistema confirma
  que o evento continua ausente, recria-o no Google com título, data, horário, local e descrição
  atuais (dia inteiro continua dia inteiro, sem convidados), passa a sincronizá-lo pelo evento novo
  e retira a marca. Antes de confirmar, a tela DEVE mostrar o título e a data que vão ao Google e
  avisar quando a data já passou. Se o Google recusar ou não responder, a marca continua e a tela
  diz que não deu, sem erro técnico; evento sem data válida é recusado antes de qualquer chamada.
- **FR-043**: Se, na hora de devolver, o evento já estiver de volta no Google, o sistema NÃO DEVE
  criar outro: retira a marca e, quando os dados do sistema diferem dos do Google (o evento foi
  editado enquanto marcado), grava no Google os dados do sistema antes de retirar a marca.
- **FR-044**: Depois de devolvido, o sync NÃO DEVE apagar vaga de personagem criada no sistema que
  não está no título, nem mandar e-mail de remoção por isso. O histórico do evento registra quando o
  elenco passa a ser mantido só pelo sistema.
- **FR-045**: Enquanto marcado, o evento NÃO DEVE poder ser cancelado nem excluído, por nenhum
  papel e por nenhum caminho (a API e a rota antiga de exclusão): o servidor recusa e a tela explica
  que o cancelamento do evento marcado chega na entrega seguinte. Solicitar exclusão e recusar a
  solicitação (224) continuam como hoje. (A segunda entrega substitui esta regra pelo "Cancelar e
  devolver o dinheiro".)

**Portal do artista**

- **FR-022**: O elenco escalado DEVE ver o evento marcado no portal com o aviso "Evento em confirmação
  — entre em contato com a produção", na agenda, nos convites e no histórico; o aviso some quando a
  marca some. O evento cancelado sai da agenda, dos convites e do histórico do portal, como hoje, e
  também DEVE sair da avaliação pós-evento (hoje um cancelado que terminou nos últimos 7 dias acende
  o "Avaliar" e aceita nota).

**Situação, rastro e travas**

- **FR-033 (parte)**: O servidor DEVE devolver, no resumo do evento da agenda e da busca e no detalhe,
  uma situação única com precedência **cancelado > sumiu do Google > exclusão solicitada**; a marca
  nunca aparece em evento cancelado, em nenhuma tela nem no portal. O resto da FR-033 (o selo do
  cancelado nas listas) é da terceira entrega.
- **FR-023**: Marcar, avisar, devolver ao Google e desmarcar (sozinho ou por decisão) DEVEM ficar no
  histórico do evento e na auditoria, com o motivo — no caso da marca, o que está preso ao evento;
  no caso do evento vazio apagado, o que o Google respondeu e a constatação de que nada estava
  preso.
- **FR-024**: A escrita no Google Agenda desta feature (devolver ao Google) DEVE nascer travada fora
  da produção (Princípio XIV), por uma trava própria de escrita de evento; com a trava ligada, a
  devolução não faz nenhuma chamada ao Google — nem a consulta ao id antigo, nem a criação, nem a
  regravação do ramo "já tinha voltado" — e a tela diz por quê. A trava cobre só a devolução: a
  sincronização, a limpeza (lista do mês e consulta individual) e o "Sincronizar" continuam lendo o
  Google real no ambiente local, e criar, editar, excluir e cancelar evento continuam escrevendo. As
  escritas antigas sem trava viram dívida no `docs/05`.
- **FR-025 (parte)**: Os textos que descrevem a limpeza por sumiço DEVEM dizer o que acontece de
  fato: a documentação da função de limpeza e a do módulo do ciclo automático (que hoje afirma fazer
  "a mesma" operação do botão "Sincronizar agora", que não limpa), a confirmação e a mensagem do
  "Limpar eventos fantasma", e o trecho do `docs/04` sobre a limpeza. Os textos de cancelamento e
  estorno são da segunda entrega.

### Entidades *(se houver dados)*

- **Evento (`CalendarEvent`)**: ganha a coluna `google_missing_since` (data e hora em que o sistema
  percebeu o sumiço, horário de São Paulo; vazia = não marcado) e duas leituras derivadas: "está
  marcado" (marca preenchida **e** não cancelado) e a situação única. Reusar os campos do pedido de
  exclusão da 224 quebra: o Comercial sobrescreveria a marca ao pedir exclusão; "Recusar" zeraria a
  marca e o sync marcaria e avisaria de novo, em ciclo; o autor do pedido é chave para usuário e não
  existe usuário "Sistema". A marca não toca `cancelled_at`: é isso que faz a FR-005 valer sem mexer
  no financeiro.
- **Notificação (`Notification`, feature 272)**: um tipo novo de aviso, `evento.sumiu_google`,
  endereçado a Superadmins e Comerciais, sem tabela nova.

### RBAC *(obrigatório se houver endpoint novo ou alterado)*

- `GET /api/events/sumidos-google` (novo) — SUPERADMIN ou COMERCIAL **pelo papel efetivo** (respeita
  o "Ver como"); os demais recebem a faixa vazia com `pode_ver: false`, sem erro.
- `POST /api/events/<id>/devolver-ao-google` (novo) — SUPERADMIN, pelo gate de excluir/cancelar da
  224 (papel real).
- `POST /api/events/<id>/sync` (existente) — segue sem gate de papel; passa a poder retirar a marca
  quando o Google confirma que o evento voltou, e a recusar quando ele não está lá.
- `POST /api/events/<id>/cancelar` e `DELETE /api/events/<id>` (existentes) — papéis inalterados;
  recusam evento marcado (FR-045). A rota antiga `POST /events/<id>/delete` (só pelo backend direto,
  SUPERADMIN) recusa evento marcado pela mesma regra.
- `POST` e `DELETE /api/events/<id>/solicitar-exclusao` (existentes) — sem mudança: valem para
  evento marcado e não alteram a marca.
- `POST /api/admin/sync/run` (existente) — papéis inalterados (SUPERADMIN); resposta com os números
  novos.
- A marca vai no payload de detalhe e da agenda para quem já pode ver o evento, inclusive o
  revendedor EducaManto, sem motivo, autor nem dinheiro; o botão de devolver só aparece por flag do
  servidor (o frontend não decide RBAC).
- Portal: o aviso vai só nos eventos em que o talento está escalado (portão "é o dono do recurso").
- Os dois endpoints novos entram no inventário (`docs/01` §3.3) e os gates na tabela do §4.3. A rota
  `sumidos-google` não colide com `/events/<id>`, que só aceita número.

## Verificação (`verify_303.py`) *(obrigatório — Princípio VIII)*

Arquivo: `specs/303-sync-nao-apaga-venda/verify_303.py`, contra `manto_local` (`DATABASE_URL` de
`.local-db-url`, `FLASK_ENV=development`, `MANTO_SEM_THREADS=1`). Login só por
`POST /api/auth/login`; escrita conferida por conexão separada; limpeza no `finally`. **O Google é
substituído por um dublê que falha fechado** (lista do mês, consulta de um evento, criação, edição e
remoção): o `manto_local` tem o token real da empresa, e nenhum cenário pode ler ou escrever na
agenda de verdade. Os eventos de teste vivem em meses isolados, sem evento real; um disjuntor de
rede acusa qualquer chamada que escape. Os cenários 1 e 7 rodam nos quatro modos de apagado do dublê
(cancelado com dados completos, cancelado mínimo, "não encontrado" e "removido"), para os três
jeitos de "ausente" passarem pela limpeza.

| # | Cenário | O que prova | Deve falhar? |
|---|---|---|---|
| 0 | Chão: travas de e-mail e de escrita no Google ligadas; dublê instalado; meses isolados vazios; backend local desligado | o verify não roda em ambiente que escreve fora | — |
| 1 | Evento com venda ausente da lista e da consulta do Google; sync do mês | fica no banco, marcado, com venda, comprovante e escala intactos; histórico e auditoria com o que estava preso; nenhum e-mail ao elenco; a agenda (mês, dia e busca) devolve a situação "sumiu do Google" e o detalhe devolve a data da marca e o link do Google nulo | não |
| 1b | Evento passado com venda; "Limpar eventos fantasma" | fica e é marcado; a resposta traz os números novos; COMERCIAL chamando a limpeza é recusado | **sim** (o COMERCIAL) |
| 2 | Mesmo evento do 1; sync de novo, duas vezes | uma notificação por Superadmin e por Comercial, nenhuma nova; FIGURINO sem notificação | não |
| 2b | Corrida: enquanto a limpeza consulta o evento no dublê, outra conexão grava a marca nele (o outro processo chegou antes) | a limpeza não marca de novo: o carimbo é o da outra conexão; nenhum histórico de sumiço, nenhuma linha de auditoria de sumiço e nenhuma notificação nascem dessa rodada; o evento não conta como falha | não |
| 3 | Sem venda, com comprovante (inclusive de valor nulo) | fica e é marcado | não |
| 4 | Sem venda, com contrato | fica e é marcado | não |
| 5 | Sem venda, com escalado (vaga que o sistema criou, com talento descartável) | fica e é marcado | não |
| 6 | Satélite e líder de grupo comercial, sem mais nada próprio | ficam e são marcados | não |
| 7 | Evento vazio sumido; SHOW só com o técnico de som automático | apagados como hoje; auditoria com a resposta do Google e o retrato vazio | não |
| 7a | SHOW com a vaga de Presença designada; SHOW com outro técnico no lugar do padrão | ficam e são marcados | não |
| 7b | Evento vazio com ensaio ligado que tem histórico: sumido do Google; e a variante excluída pelo `DELETE /api/events/<id>` como Superadmin | apagado sem erro, com o ensaio, nos dois caminhos | não |
| 8 | Evento movido no Google para um mês posterior; variantes: antecipado para mês passado, movido para fora do horizonte, presente sem nenhuma mudança (inclusive com "+ Coordenador" no título do Google, de dia inteiro e sem descrição, em dois ciclos seguidos) | mesmo registro, data nova, venda intacta, sem marca e sem notificação; o sem mudança não é ressincronizado | não |
| 9 | Evento marcado volta à lista do mês; marcado de mês passado volta e é achado pelo próprio id; marcado e editado no sistema volta com a data em outro mês; marcado que voltou e alguém clica em "Sincronizar"; some de novo | marca some, aviso lido, histórico diz por quê (no "Sincronizar", com o nome de quem clicou); o que volta com outra data fica no mesmo registro, com os dados do Google; nenhum e-mail ao elenco na desmarca sem mudança de dados; no segundo sumiço, aviso novo | não |
| 13d | A consulta ao Google falha na reconferência dos marcados, com candidatos em meses seguintes | houve a consulta; nenhuma marca é retirada; os meses listam, sincronizam e limpam | não |
| 10 | Superadmin devolve ao Google (criação no dublê), depois de editar título e data do evento marcado | uma criação com os dados atuais; id novo; marca some; a faixa deixa de contá-lo; histórico com quem e quando; aviso lido; venda, comprovantes, contrato e escala intactos | não |
| 10a | Devolver com a trava de escrita ligada | recusado com a explicação; nenhuma leitura nem escrita no dublê | **sim** |
| 10b | Evento de dia inteiro | recriado como dia inteiro | não |
| 10c | O evento já tinha voltado ao Google; variante editado enquanto marcado, com vaga de personagem criada fora do título | nenhuma criação; marca some; na variante, o Google recebe os dados do sistema e, no sync seguinte, a vaga continua, sem e-mail de remoção | não |
| 10d | O Google recusa a criação | marca e id intactos; mensagem sem o erro técnico; auditoria da falha | **sim** |
| 10e | A consulta ao Google é inconclusiva | nada criado; marca e id intactos | **sim** |
| 10f | Segundo clique em devolver no mesmo evento | recusado como "não está marcado"; nenhuma criação nova | **sim** |
| 10g | Sync logo depois da devolução; evento com vaga de personagem fora do título | uma linha só com o id novo, sem marca, sem e-mail de remoção; a vaga continua (na `main`, sem a regra, ela seria apagada) | não |
| 10h | Evento devolvido com ensaio-filho | o ensaio continua ligado, intocado; uma criação só | não |
| 10i | Devolver evento não marcado, cancelado, inexistente, sem data | recusados, cada um com o seu motivo; nenhuma chamada ao dublê | **sim** |
| 11 | COMERCIAL real tenta devolver ao Google | recusado; nada muda; o Superadmin consegue na mesma rota | **sim** |
| 12 | Cancelar e excluir evento marcado, como Superadmin — pela API e pela rota antiga `POST /events/<id>/delete`, direto no backend; satélite marcado sem mais nada; solicitar exclusão de evento marcado, como Comercial | cancelar e excluir recusados; registro, marca e aviso intactos; a solicitação continua aceita e não altera a marca | **sim** |
| 13 | Consulta ao Google falha depois de a lista responder (erro do serviço, tempo esgotado, credencial ausente, falha ao renovar), cada uma com o controle "o mesmo evento com ausência confirmada é marcado"; acesso negado e limite de uso no primeiro candidato; dois meses seguidos com a falha no primeiro; e a lista inteira falha | nada apagado nem marcado; depois da primeira falha, os demais daquele mês não são consultados; com acesso negado ou limite de uso, os demais continuam sendo consultados; o mês seguinte volta a consultar | não |
| 13b | A gravação do aviso do sino falha uma vez durante a marca de um evento, com outros candidatos no mesmo mês | esse evento fica sem marca e sem notificação e conta como falha (a limpeza do mês sai com erro); os demais são processados; na rodada seguinte ele é marcado, com um aviso por destinatário | não |
| 13c | Erro de banco no meio da sincronização de um mês, com outro mês depois | o mês seguinte sincroniza e limpa (na `main`, depois de um erro de banco todos os meses seguintes falham); nenhuma marca fica sem aviso | não |
| 14 | Editar evento marcado (título e data; troca de tipo para SHOW e de volta); "Sincronizar" de evento marcado e de evento não marcado, ausentes do Google | edição salva sem escrever no Google e sem aviso de falha; marca continua; o Sincronizar não altera título, datas nem escala, não manda e-mail de remoção e responde que o evento não está no Google, tanto com a resposta completa do Google (na `main`, responde "sincronizado") quanto com a mínima (na `main`, o título vira "Sem título") | não |
| 15 | Evento cancelado e venda virtual ausentes do Google | comportamento de hoje, sem marca e sem consulta individual | não |
| 17 | Faixa: Superadmin e Comercial reais com 1 marcado; Figurino, Financeiro e revendedor; "Ver como"; depois de resolvido (o evento reaparece no Google); dois marcados, com o núcleo chamado com limite 1 | quem vê recebe 1 com id, título e data, sem dinheiro; os demais recebem vazio sem erro; resolvido → vazio; com limite 1, total 2 e um item, o mais urgente | **sim** (Figurino não pode ver) |
| 18 | Configuração da trava de escrita: banco local, banco remoto, e as duas variáveis | local travado por padrão; remoto liberado; cada variável faz o que diz | não |
| 24 | Portal: talento escalado e talento de fora, com o evento marcado; convite pendente; depois de devolvido | escalado vê o aviso nas três listas e ainda consegue aceitar; de fora não vê nada; devolvido → sem aviso | **sim** (o de fora) |
| 24b | Avaliação de evento cancelado que terminou há 2 dias | fora de "a avaliar"; nota recusada e não gravada (na `main`, é aceita) | **sim** |
| 41 | Limpeza | registros descartáveis apagados (`roles.clear()` antes do usuário); nenhuma chamada de rede escapou do dublê | — |

Os números 16, 19 a 23 e 26 a 40 são das entregas seguintes.

Conferência de tela: a faixa em duas telas quaisquer como Superadmin e como Comercial (e ausente
como Figurino), continuando visível ao rolar e ao navegar, com a régua de abas do evento logo abaixo
dela; a lista da faixa com dois eventos; a tela do evento marcado como Superadmin (o que está em
jogo, o botão de devolver, o diálogo com título e data, a mensagem da trava local) e como Comercial
(marca, sem botão); a agenda com o selo do marcado; o sino; o `/admin/sync` com a mensagem nova; o
portal em 375×812 e 320 px com o aviso.

Portões além do verify: rodar o `verify_205.py` depois da História 1 (a venda virtual continua
poupada e nenhum evento do espelho é apagado nem consultado no Google); e, depois do deploy, o teste
do "Devolver ao Google" em produção com um evento descartável, porque a trava impede exercitá-lo
contra o Google real antes.

## Critérios de sucesso *(obrigatório)*

- **SC-001**: Depois do deploy, nenhum evento com venda, comprovante, contrato, gente escalada pela
  equipe ou grupo é apagado por sumiço no Google — conferível na auditoria (toda
  exclusão automática posterior ao deploy traz o retrato do evento, e o retrato é vazio).
- **SC-002**: Evento adiado ou antecipado no Google para outro mês chega à data nova com a mesma
  venda e os mesmos comprovantes em 100% dos casos, sem faixa nem aviso.
- **SC-003**: Todo sumiço de evento com dinheiro aparece na faixa e no sino de Superadmin e Comercial
  no mesmo ciclo do sync em que foi percebido (até 10 minutos).
- **SC-004**: A partir da faixa, o Superadmin devolve o evento ao Google sem sair da tela do evento.
- **SC-005**: Nenhum clique em "Sincronizar" altera um evento que não está no Google.

## Fora de escopo

- **Segunda entrega (o dinheiro do cancelamento)**: "Cancelar e devolver o dinheiro" do evento
  marcado; devolução Tudo/Parte/Nada; comissão sobre o retido; BV negociado; imposto sobre o retido;
  correção de comprovante e BV depois de cancelado; Gastos Extras; o retido na DRE e nos números do
  comercial; a tela do evento cancelado. Texto em `entregas-2-e-3-rascunho.md`.
- **Terceira entrega (sinalizar e filtrar cancelados)**: selo e "Mostrar cancelados" na agenda e nas
  listas, card de cancelamentos, página de Cancelamentos para o Financeiro.
- "Solicitar cancelamento" pelo Comercial com aviso (o resto da D1): onda 2 do backlog.
- Fundir automaticamente um evento recriado à mão no Google (id novo) com o evento marcado.
- Venda virtual: continua com a regra própria (FR-029b da feature de virtuais), sem a marca nova.
- Nada além dos critérios da FR-001 segura o evento. **Saem com o evento vazio quando ele é
  apagado**, como hoje: reembolso, nota fiscal, parcelas previstas, presente 3D, observações e
  anexos, vínculo com clientes, acréscimos, avaliações, histórico, vagas sem talento (com o teto do
  orçamento e a ficha de figurino) e ensaios ligados (com histórico e materiais). **São só
  desvinculados, não apagados**, como hoje: o formulário da cliente (volta para a fila "sem
  evento"), o gasto extra, a produção de figurino e a tag NFC; o orçamento continua no histórico de
  orçamentos, sem o vínculo. O plano só conta quantos eventos vazios têm reembolso, nota ou presente
  3D.
- Paginar a lista do mês; tratar série recorrente do Google; travar as escritas antigas no Google;
  teto de consultas por execução da limpeza; aviso próprio para o evento que fica sem confirmação do
  Google ciclo após ciclo: dívidas no `docs/05`.
- Lembrete recorrente enquanto a marca estiver aberta (a faixa já é permanente) e o lembrete diário
  de convite de evento marcado (continua saindo; dívida).
- Mudar quem pode excluir ou cancelar, ou o que conta como vazio no botão Excluir da 224.

## Docs a atualizar

`docs/01` §3.3 (os dois endpoints novos e o que muda nos existentes) e §4.3 (os gates: a faixa, a
devolução, o `/sync` podendo retirar a marca — e a linha de `_can_delete()`, que hoje diz COMERCIAL
e SUPERADMIN e é só SUPERADMIN), o
contrato dos payloads (agenda, evento, portal, admin/sync) e as travas de ambiente; `docs/02` (faixa
global, tela do evento marcado, agenda com o selo, `/admin/sync`, portal com o aviso); `docs/03`
(entrada no topo + índice, com a contagem do dia do deploy); `docs/04` (invariantes: o sync nunca
apaga evento com dinheiro; ausência só vale confirmada; mudança de data não é sumiço; "marcado" é
marca preenchida e não cancelado; evento marcado que reaparece sozinho: vale o Google — só a
devolução faz valer o sistema; todo elemento fixo no topo soma a altura da faixa; relógio de cada
carimbo); `docs/05` (riscar a dívida 49; registrar as dívidas de Fora de escopo e as listadas em
`research.md` §"O que fica registrado como dívida" — o relógio do `EventLog` vale para os três
registros de `cancel_ops`: solicitar, recusar e cancelar); `docs/PLANO_EXTRACAO_CALENDAR.md` (o
núcleo novo tira a limpeza do corte "consulta/sync"; a injeção `delete_event_row` prevista para
`cleanup_stale_events` deixa de valer como descrita; e a nota de que o `verify_151` "continua
funcionando" passa a ser falsa); `DEVELOPMENT.md`, `CLAUDE.md` §4 e a skill `manto-verify` (a trava
nova cobre só a devolução). Também: `docs/01` §2 (a coluna `google_missing_since` e o índice parcial
na linha de `calendar_events`) e o head `a7c3e91f4d28` no cabeçalho do `docs/01`; `docs/00` §1 (a
frase das escritas no Google — "só nos fluxos explícitos de criar/editar/excluir evento" — ganha a
devolução ao Google), o cabeçalho (o head citado ali está velho: trocar pela remissão ao `docs/01`)
e o roteiro "Mexer no sync do Google" (passa a citar `app/calendar/sumico_ops.py`); `docs/04`, além
da limpeza: a tabela de arquivos do domínio (ganha `sumico_ops.py`), o "Fluxo: exclusão" (recusa do
evento marcado; ensaio-filho com histórico e avisos do sino limpos em toda exclusão; a armadilha que
descreve um `flash()` em `_delete_event` que já não existe) e o fluxo do "Sincronizar" de um evento
(confere antes de mexer), que hoje não está descrito; `docs/05` §9.1 (a linha da fatia A deixa de
listar `_cleanup_stale_events`). O `docs/01` não inventaria os endpoints da 224 — a lacuna vira
dívida, não tarefa desta feature.

## Premissas

- "Com dinheiro" é a regra que a 224 usa para decidir entre excluir e cancelar (venda, comprovante,
  contrato, escalado), **mais** pertencer a um grupo comercial — o satélite é dia de uma venda que
  mora no líder, e apagá-lo perde a escala daquele dia —, **menos** a vaga de técnico de som que o
  sistema preenche sozinho em SHOW (decisão do dono, 29/09, reafirmada em 30/09: valor pago significa
  evento realizado, que não some da agenda), e contando comprovante pela existência, não pelo valor.
  Comissão já paga não entra: o evento sem mais nada é apagado e o estorno sai contra o vendedor,
  como hoje (30/09). A regra do botão Excluir da 224 não muda.
- Entre esta entrega e a segunda, o evento marcado que foi cancelado de verdade continua valendo
  como qualquer evento (FR-005): a comissão da venda segue no ciclo do mês, o cachê do elenco
  aparece na Planilha de Pagamentos quando a data passa (e como pendente no Histórico do portal), e
  a venda soma na DRE. O sistema não segura nada disso sozinho, e o Financeiro não vê a faixa (só
  Superadmin e Comercial). Quem segura é o Superadmin: antes de fechar a Planilha de Pagamentos,
  confere os eventos da faixa e retém à mão o que for de evento cancelado de verdade; o acerto
  definitivo vem com a segunda entrega. (Procedimento confirmado pelo dono em 30/09 —
  §Clarifications.)
- O aviso vai a Superadmins e Comerciais (D21); quem tem os dois papéis recebe um só.
- Devolver ao Google recria o evento sem convidados; os convites por e-mail do sistema não são
  reenviados.
- Caminhos que limpam por sumiço (verificado em 29/09): o ciclo automático (a cada 10 min), do mês
  corrente até +6 meses ou até o último evento do banco +1 mês; o "Limpar eventos fantasma" de
  `/admin/sync` (Superadmin), que percorre em ordem os meses que têm algum evento no banco, passados
  inclusive; e a rota antiga `/agenda?force_sync=1`, que só responde chamando o backend direto.
  "Sincronizar agora" e o "Sincronizar" de um evento não limpam. A regra vale em todo caminho que
  limpa.
- O carimbo da marca é horário de São Paulo, como o do cancelamento; o histórico do evento usa o
  relógio que a tela já converte.
- A contagem de eventos passados fora do Google foi feita em 30/09 (zero) e se repete no dia do
  deploy.
- O Google responde por um evento apagado com a situação "cancelado" e, nos casos sondados, com os
  dados completos; "não encontrado" e a resposta mínima também são tratados como ausência.
- Até o deploy, vale a orientação à equipe de não apagar no Google evento com venda.
