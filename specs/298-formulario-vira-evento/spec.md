# Feature 298 — O formulário vira evento: a Home mostra só os formulários que ainda precisam de destino

**Branch**: `298-formulario-vira-evento` (da `main`) · **Created**: 2026-09-10 · **Status**: Rascunho ·
**Migration**: uma, aditiva (encerramento do formulário e sugestões descartadas) ·
**Nível**: 1 (feature) — constituição, Princípio VI

**Input**: pedido do dono: "Quero que todo formulário (pré-contrato de festa ou corporativo) que
chegou a partir de 01/06/2026 tenha um destino claro: virar evento na agenda, ou ser encerrado com
motivo (a cliente desistiu, preencheu repetido, preencheu errado). Os formulários anteriores a junho
são histórico e nunca aparecem como tarefa. Na Home, trocar os números soltos por uma lista
"Formulários sem evento na agenda", organizada e fácil de ler, em dois grupos: "a data informada
ainda vai chegar" e "a data informada já passou". Cada linha mostra a cliente, a data informada e há
quantos dias chegou. Formulários da mesma cliente (pelo telefone) aparecem numa linha só. Se a
cliente já tem evento em data igual ou próxima, o sistema sugere ligar. O botão "Criar evento" traz
tudo o que a cliente preencheu, e a comercial confere antes de salvar, porque o formulário pode estar
errado. Ao ligar o formulário a um evento, a ficha da cliente vem junto, e o aviso do sino some
sozinho. Siga o plano"

## O pedido, nas palavras do dono *(obrigatório)*

Contexto que o dono deu antes do pedido (conversa de 10/09/2026, plano aprovado):

- **Atendimento.** As clientes são atendidas no WhatsApp/Kommo, fora do sistema. Quando fecham,
  preenchem o formulário, que gera o contrato no Clicksign.
- **O esquecimento.** Historicamente, a cliente preenche o formulário e o vendedor esquece de colocar o
  evento na agenda. O formulário deve ajudar a montar o evento, mas não pode ser levado como regra,
  porque a cliente preenche errado, preenche mais de uma vez ou preenche e desiste.
- **O histórico.** Os formulários de 2023 a maio de 2026 foram importados de propósito, para existir
  histórico de clientes. O que foi lançado de fato no sistema começa em junho de 2026.
- **O sintoma.** A Home "mostra milhares de coisas para fazer, mas isso não é verdade". Em 10/09/2026 o
  cartão dizia 1.347 formulários sem evento. Desde 01/06 são 36: em 17 a data informada ainda vai
  chegar (11 nos próximos 16 dias) e em 19 ela já passou.

**Vocabulário desta feature** (vale para a spec e para os textos da tela):

- **Formulário**: o pré-contrato, de festa ou corporativo, que a cliente preencheu.
- **Evento**: a festa lançada na agenda.
- **Data informada**: a data que a cliente escreveu no formulário. Pode estar errada.
- **Destino**: o formulário virou evento, ou foi encerrado com motivo.
- Nunca "festa sem evento". O certo é "formulário sem evento na agenda".

## Clarifications

### Session 2026-09-10

- Q: Quando uma linha da lista de formulários deve aparecer em vermelho, amarelo ou cinza? → A:
  vermelho quando a data informada está a 7 dias ou menos; amarelo de 8 a 30 dias e em todo o grupo
  "a data informada já passou"; cinza acima de 30 dias ou com data suspeita.
- Q: Até que diferença de datas o sistema deve sugerir que o formulário é de um evento que a cliente
  já tem na agenda? → A: na lista, até 3 dias de diferença. No "Criar evento", aviso se a cliente já
  tem qualquer evento sem formulário ligado desde 01/06, para não duplicar (caso de mês trocado).
- Q: O que a tela Formulários deve mostrar nos cartões de filtro do topo depois desta mudança? → A:
  filtros por destino: "Sem destino (desde 01/06)", "Com evento", "Encerrados" e "Histórico (antes de
  01/06)". "Sem cliente" e "Vínculo ambíguo" deixam de ser filtros.
- Q: Quem pode encerrar um formulário com motivo e reabrir um formulário encerrado? → A: quem já liga
  formulário a evento hoje: COMERCIAL, FINANCEIRO e SUPERADMIN. Excluir continua só do SUPERADMIN.

### Session 2026-09-11

Respostas do dono às lacunas do checklist `checklists/revisao.md`:

- Q: Quando a cliente do formulário é diferente da cliente do evento ao qual ele foi ligado, o que a
  comercial pode fazer? → A: o evento não muda. A tela avisa as duas e oferece "usar a cliente do
  evento neste formulário", porque quem vale para cobrança e agenda é a do evento.
- Q: Descartar a sugestão "parece ser este evento" pode ser desfeito? → A: não, é definitivo. Se foi
  engano, a comercial liga à mão pela tela Formulários.
- Q: Quando um formulário encerrado é reaberto, o registro do encerramento fica guardado? → A: sim.
  Encerrar e reabrir ficam no histórico de ações do sistema (quem, quando, motivo). O formulário
  mostra só o estado atual.

Decisões do dono sobre o `/speckit-analyze` (mesmo dia):

- Q: Os formulários desde junho que já estão ligados a um evento com cliente, mas aparecem "sem
  cliente" (~69), são corrigidos de uma vez? → A: sim, por uma correção única que primeiro conta e
  depois aplica, com a mesma regra dos vínculos novos (FR-020).
- Q: O "Não é este" da sugestão, que descarta para sempre, pede confirmação? → A: sim, numa caixa
  curta.
- Q: Como a data suspeita barra o salvar? → A: o Salvar nunca fica desabilitado. Ao salvar sem
  confirmar, o campo mostra o que está errado e a tela leva até ele.
- Q: O verify pode chegar a criar evento no Google Agenda? → A: pode, desde que todo evento de teste
  traga "[TESTE verify 298] pode apagar" no título. O plano prefere, além disso, trocar a chamada ao
  Google por uma falsa dentro do verify, e aí nada é criado.
- Q: A saída da linha resolvida da Home precisa de animação? → A: sim. Se não for possível num caso,
  aceita-se sem animação.

## Cenários e Verificação *(obrigatório)*

### História 1 — A Home mostra só os formulários que precisam de destino (Prioridade: P1)

A comercial abre a Home e, no lugar de quatro números soltos, vê o painel "Formulários sem evento na
agenda". Ele tem só os formulários que chegaram a partir de 01/06/2026 e ainda não têm destino,
separados em dois grupos: "a data informada ainda vai chegar" e "a data informada já passou". Cada
linha mostra a cliente, a data informada com a distância em palavras ("em 2 dias", "passou há 6
dias"), há quantos dias o formulário chegou e uma ação. Ela sabe, de relance, qual formulário
resolver primeiro. O histórico importado não aparece como tarefa.

**Por que esta prioridade**: é o esquecimento que motivou a feature, e o número de hoje (1.347)
esconde as poucas dezenas que importam.

**Verificação**: cenários 1 a 4 e 13 do `verify_298.py`; estado vazio e tela estreita na conferência
de tela.

**Cenários de aceite**:

1. **Dado** um formulário que chegou em 15/05/2026 e não tem evento, **Quando** a comercial abre a
   Home, **Então** ele não aparece na lista nem em nenhuma contagem de pendência.
2. **Dado** um formulário que chegou em 20/08/2026 com data informada 25/09/2026 e sem evento,
   **Quando** a Home abre, **Então** ele aparece em "a data informada ainda vai chegar", com a
   cliente, "25/09 · em N dias" e "chegou há N dias".
3. **Dado** um formulário que chegou em 10/06/2026 com data informada 20/06/2026 e sem evento,
   **Quando** a Home abre, **Então** ele aparece em "a data informada já passou".
4. **Dado** um formulário corporativo que chegou em setembro e não tem evento, **Quando** a Home abre,
   **Então** ele aparece na lista como qualquer outro, identificado como corporativo.
5. **Dado** vários formulários em "ainda vai chegar", **Quando** a Home abre, **Então** o da data
   informada mais próxima vem primeiro, com a cor da urgência (FR-005). Com a mesma data informada,
   vem primeiro o que chegou por último.
6. **Dado** nenhum formulário sem destino, **Quando** a Home abre, **Então** o painel diz "Nenhum
   formulário esperando evento ✓", sem número vermelho.
7. **Dado** a pessoa logada como FINANCEIRO, **Quando** a Home abre, **Então** a ação principal da linha
   é "Abrir" (leva ao formulário na tela Formulários), e não "Criar evento".

---

### História 2 — Encerrar um formulário com motivo (Prioridade: P1)

Nem todo formulário vira evento: a cliente desiste, preenche duas vezes ou preenche errado. A
comercial encerra o formulário escolhendo o motivo (desistiu, repetido, preenchido errado, teste ou
outro, com uma frase). Ele sai da lista, continua guardado com o motivo, quem encerrou e quando, e
pode ser reaberto se foi engano. Encerrar e reabrir ficam no histórico de ações do sistema.

**Por que esta prioridade**: sem uma saída, a lista volta a acumular o que não é tarefa. Hoje só o
superadmin consegue tirar um formulário da fila, e apagando.

**Verificação**: cenários 6, 7, 10, 14a e 15 do `verify_298.py`.

**Cenários de aceite**:

1. **Dado** um formulário na lista, **Quando** a comercial o encerra como "a cliente desistiu",
   **Então** ele sai da lista e da contagem. Na tela Formulários, aparece como encerrado, com o
   motivo, quem encerrou e quando.
2. **Dado** um formulário encerrado por engano, **Quando** a comercial o reabre, **Então** ele volta
   para a lista no grupo certo. O aviso do sino não reacende, e o encerramento anterior continua no
   histórico de ações.
3. **Dado** um formulário já ligado a um evento que depois foi cancelado, **Quando** a Home abre,
   **Então** ele não volta para a lista: já teve destino.
4. **Dado** um formulário ligado a um evento que depois foi excluído da agenda, **Quando** a Home abre,
   **Então** ele volta para a lista, porque perdeu o destino.
5. **Dado** um formulário encerrado, **Quando** ele é ligado a um evento por qualquer caminho, **Então**
   o encerramento é desfeito e o destino passa a ser o evento.
6. **Dado** um formulário que já tem evento, **Quando** alguém tenta encerrá-lo, **Então** a ação é
   recusada com "Este formulário já tem destino".
7. **Dado** um formulário ligado a um evento, **Quando** a comercial o desvincula, **Então** ele volta
   para a lista, se chegou desde a data de início.

---

### História 3 — Formulários da mesma cliente numa linha só (Prioridade: P2)

Quando a mesma cliente (reconhecida pelo telefone) preencheu mais de um formulário sem destino, com a
mesma data ou não, a lista mostra uma linha só, marcada "preencheu 2 vezes". A linha representa o
formulário que chegou por último. Aberta a linha, a comercial vê os formulários lado a lado, escolhe
o que vale e encerra os outros como "repetido" com um clique.

**Por que esta prioridade**: 11 dos 36 formulários de hoje são de clientes que preencheram mais de uma
vez, 4 deles com outra data. Sem agrupar, a lista parece maior do que é e a comercial pode lançar o
mesmo evento duas vezes.

**Verificação**: cenário 5 do `verify_298.py`.

**Cenários de aceite**:

1. **Dado** dois formulários da mesma cliente, sem destino, com datas 24/09 e 26/09, **Quando** a Home
   abre, **Então** aparece uma linha só, com a marca "preencheu 2 vezes". Cliente, data, cor e "chegou
   há" são os do formulário que chegou por último.
2. **Dado** essa linha, **Quando** a comercial escolhe o de 26/09 como o que vale, **Então** o outro é
   encerrado como "repetido" e a linha passa a mostrar só o de 26/09.
3. **Dado** uma cliente que já tem um formulário ligado a um evento e preencheu outro, com outra data,
   **Quando** a Home abre, **Então** o novo aparece com a marca "já tem outro formulário com evento",
   e a comercial decide se é outra festa ou repetição.
4. **Dado** um formulário de festa e um corporativo da mesma cliente, sem destino, **Quando** a Home
   abre, **Então** eles aparecem juntos na mesma linha, cada um com o seu tipo.

---

### História 4 — "Parece ser este evento, é?" (Prioridade: P2)

Se a cliente do formulário (pelo telefone) já tem evento na agenda em data igual ou próxima, a linha
mostra a sugestão, e a comercial confirma com um clique ou descarta. O sistema nunca liga sozinho por
data aproximada.

**Por que esta prioridade**: hoje 7 dos 36 formulários são de clientes que já têm o evento na agenda,
com a data igual ou quase igual (26/09 no formulário e 27/09 na agenda), e ficam na fila para sempre
porque a regra automática exige a data exata.

**Verificação**: cenário 8 do `verify_298.py`.

**Cenários de aceite**:

1. **Dado** um formulário com data informada 26/09 e um evento da mesma cliente em 27/09 que ainda não
   está ligado a nenhum formulário, **Quando** a Home abre, **Então** a linha mostra "Parece ser o
   evento de 27/09 — ligar?".
2. **Dado** a sugestão, **Quando** a comercial confirma, **Então** o formulário é ligado ao evento e
   sai da lista.
3. **Dado** a sugestão, **Quando** a comercial clica em "Não é este" e confirma na caixa, **Então** a
   sugestão não volta para esse par formulário–evento. Se foi engano, a ligação à mão pela tela
   Formulários continua possível.
4. **Dado** dois eventos da cliente dentro da janela, **Quando** a Home abre, **Então** a sugestão é o
   de menor diferença de dias; empatados, o mais cedo.

---

### História 5 — Criar o evento a partir do formulário, conferindo (Prioridade: P2)

Na linha, o botão "Criar evento" abre o cadastro de evento já preenchido com o que a cliente escreveu,
nos dois formatos de formulário que existem desde junho (o do site e o da carga antiga do WhatsForm).
Cada campo que veio do formulário aparece marcado "do formulário". O que parece errado vem destacado
com o motivo e com o texto que a cliente escreveu. Nada é salvo sem a comercial confirmar.

**Por que esta prioridade**: hoje o botão aproveita só a data e a cliente, e a comercial redigita o
resto do formulário. É esse trabalho que faz o evento ficar para depois.

**Verificação**: cenários 11 e 12 do `verify_298.py`; conferência de tela.

**Cenários de aceite**:

1. **Dado** um formulário de festa completo, **Quando** a comercial clica em "Criar evento", **Então** o
   cadastro abre com data, início, fim, local, tipo, forma de pagamento e cliente preenchidos e
   marcados. Tema, espaço, aniversariante, personagens pedidos e observações contratuais aparecem nas
   observações do evento, com rótulo, e os personagens também como sugestão de elenco.
2. **Dado** um formulário com data informada em 2049, **Quando** o cadastro abre, **Então** a data vem
   destacada como suspeita, com o texto da cliente ao lado. O Salvar continua disponível. Ao salvar
   sem confirmar nem corrigir, o campo da data é marcado com a explicação e a tela leva até ele.
3. **Dado** um formulário com forma de pagamento que o cadastro não tem (por exemplo "cartão em 3x com
   15%" ou "boleto"), **Quando** o cadastro abre, **Então** a forma fica em branco com o texto da
   cliente ao lado, para a comercial escolher.
4. **Dado** um formulário corporativo, **Quando** o cadastro abre, **Então** o endereço é o do evento,
   nunca o da empresa, e o briefing está nas observações.
5. **Dado** o cadastro conferido, **Quando** a comercial salva, **Então** o evento é criado, o
   formulário fica ligado a ele e sai da lista.
6. **Dado** um formulário com data informada 12/06 e uma cliente que tem, em 13/07, um evento sem
   formulário ligado, **Quando** a comercial clica em "Criar evento", **Então** o cadastro avisa
   "esta cliente já tem um evento em 13/07 sem formulário — é o mesmo?" e oferece ligar a ele em vez
   de criar outro.
7. **Dado** um período escrito de forma ambígua ("3h ou 4h"), **Quando** o cadastro abre, **Então** o
   horário de fim fica em branco, com o texto da cliente ao lado.
8. **Dado** um formulário cuja cliente não tem ficha, **Quando** o cadastro abre, **Então** o sistema
   sugere a ficha com o mesmo telefone ou, se não houver, abre o cadastro rápido de cliente já
   preenchido com nome, telefone, e-mail e CPF/CNPJ.
9. **Dado** qualquer formulário, **Quando** o cadastro abre, **Então** valor de venda, vendedor e título
   não vêm preenchidos pelo formulário.

---

### História 6 — A cliente vem junto, e o aviso do sino some sozinho (Prioridade: P3)

Quando o formulário ganha destino, o sistema arruma o que hoje fica pendurado:
- a ficha da cliente acompanha o vínculo com o evento, nos dois sentidos;
- o aviso "nova resposta" some do sino de todo mundo;
- a Home se atualiza.

**Por que esta prioridade**: hoje 85 dos 178 formulários desde junho aparecem "sem cliente", quase
todos já ligados a um evento que tem cliente. E 35 avisos do sino continuam acesos sobre formulários
já resolvidos.

**Verificação**: cenários 9 e 14b do `verify_298.py`.

**Cenários de aceite**:

1. **Dado** um formulário sem cliente e um evento com cliente, **Quando** os dois são ligados (à mão,
   pela sugestão, pelo sistema ou pelo "Criar evento"), **Então** o formulário passa a ter a cliente
   do evento.
2. **Dado** um formulário com cliente e um evento sem cliente, **Quando** são ligados, **Então** o
   evento passa a ter a cliente do formulário.
3. **Dado** um formulário com cliente diferente da cliente do evento, **Quando** são ligados, **Então**
   o evento não muda. A tela mostra as duas clientes e oferece "usar a cliente do evento neste
   formulário".
4. **Dado** um aviso "nova resposta" não lido por cinco pessoas, **Quando** o formulário é ligado a um
   evento ou encerrado, **Então** o aviso some do sino das cinco.
5. **Dado** um formulário que o sistema já liga a um evento no momento em que ele chega, **Quando** a
   cliente envia, **Então** nenhum aviso "nova resposta" é emitido, porque ele já nasce com destino.

---

### Casos de borda

- **Formulário sem telefone válido**: não se agrupa com outros e não recebe sugestão de evento.
  Aparece sozinho na lista.
- **Data informada impossível** (antes do dia em que o formulário chegou, ou mais de dois anos à
  frente): aparece com a marca "data suspeita", no grupo que a data indicar, em cinza.
- **Mesma cliente com duas festas de verdade**: cada formulário ligado ao seu evento. O agrupamento só
  junta os formulários sem destino.
- **Formulário encerrado e a cliente preenche de novo**: o novo entra na lista normalmente.
- **Duas pessoas agem no mesmo formulário ao mesmo tempo**: a segunda recebe "Este formulário já tem
  destino" e a lista se atualiza. Nada é duplicado e nenhuma ação é perdida em silêncio.
- **Ligar um formulário que já tem evento a outro evento**: é recusado com a mesma mensagem. O
  vínculo nunca é trocado em silêncio.
- **Formulário anterior a 01/06**: continua na tela Formulários, pesquisável e ligável à mão, mas nunca
  vira tarefa.
- **Evento ligado é depois excluído, ou o formulário é desvinculado**: o formulário volta para a lista.
- **Evento ligado é depois cancelado**: não volta.
- **Aviso do sino já lido**: continua lido. Só os não lidos somem quando o formulário ganha destino.
  Reabrir um formulário não reacende o aviso.
- **Data de início do sistema vazia na configuração**: vale 01/06/2026.

## Requisitos *(obrigatório)*

### Requisitos funcionais

- **FR-001**: O sistema DEVE considerar como tarefa só os formulários que chegaram a partir da data de
  início do sistema (hoje 01/06/2026, a mesma que as cobranças já usam), contada no fuso de São Paulo.
  Os anteriores são histórico. Se a data de início estiver vazia na configuração, vale 01/06/2026.
- **FR-002**: O formulário DEVE estar "sem destino" quando não está ligado a nenhum evento e não foi
  encerrado. Ligado a um evento, mesmo que o evento seja cancelado depois, ou encerrado com motivo, ele
  tem destino.
  - Um formulário encerrado nunca tem evento: ligá-lo a um evento desfaz o encerramento.
  - Desvincular o formulário ou excluir o evento devolve o formulário a "sem destino".
- **FR-003**: A Home DEVE mostrar, para quem hoje vê o cartão de formulários, o painel "Formulários sem
  evento na agenda".
  - Os formulários sem destino (FR-001 e FR-002) ficam em dois grupos: "a data informada ainda vai
    chegar" (data mais próxima primeiro) e "a data informada já passou" (a que passou mais
    recentemente primeiro). Com a mesma data informada, vem primeiro o que chegou por último.
  - O painel substitui os quatro números atuais.
- **FR-004**: Cada linha DEVE mostrar:
  - a cliente (nome da ficha, ou o nome escrito no formulário);
  - o tipo, escrito "Festa" ou "Corporativo";
  - a data informada e a distância em palavras ("hoje", "amanhã", "em N dias", "passou há N dias");
  - há quantos dias o formulário chegou;
  - a ação principal: "Criar evento" para quem pode criar evento (COMERCIAL e SUPERADMIN) e "Abrir"
    para os demais (FINANCEIRO);
  - a ação secundária "Encerrar".
  - As marcas que se aplicarem aparecem nesta ordem fixa: "data suspeita", "preencheu N vezes", "já
    tem outro formulário com evento". A sugestão de evento vem numa faixa própria, logo abaixo.
  - Na linha que junta formulários da mesma cliente, cliente, data, cor e "chegou há" são os do
    formulário que chegou por último, e todos aparecem ao abrir a linha.
- **FR-005**: O painel DEVE ser próprio, logo depois do painel "Comercial" da Home, no mesmo padrão
  visual das outras listas. Cada grupo mostra 6 linhas e "Mostrar todas" para o resto. Organizado e
  fácil de ler de relance.
  - **Vermelho**: a data informada está de 0 (hoje) a 7 dias à frente.
  - **Amarelo**: está entre 8 e 30 dias, e todo o grupo "a data informada já passou".
  - **Cinza**: acima de 30 dias, ou com data suspeita.
  - A urgência nunca é dita só pela cor: a distância em palavras (FR-004) vai junto.
  - O painel só abre sozinho quando há linha vermelha. O "urgentes" do topo da Home conta os
    formulários das linhas vermelhas.
  - Sem pendência, o painel diz "Nenhum formulário esperando evento ✓".
  - A linha resolvida (ligada, encerrada ou escolhida entre repetidos) sai da lista com uma transição
    curta. Não há animação para quem desligou animações no sistema, nem onde a transição não for
    possível (decisão do dono).
  - Em tela estreita a linha quebra em duas, sem rolagem horizontal, com a ação principal sempre
    visível.
- **FR-006**: O contador de pendências do topo da Home e o contador do painel DEVEM contar os
  formulários sem destino desde a data de início. O histórico sai da soma.
- **FR-007**: Quem pode tratar formulários DEVE poder encerrar um formulário sem evento, com um motivo:
  - motivos fixos: "a cliente desistiu", "repetido", "preenchido errado", "teste" e "outro", este
    com uma frase obrigatória (até 300 caracteres);
  - o sistema guarda o motivo, quem encerrou e quando;
  - formulário que já tem evento não pode ser encerrado, nem formulário do histórico (que chegou antes
    da data de início);
  - a lista de motivos e os seus textos vêm de um lugar só: a tela mostra o que o sistema manda.
- **FR-008**: Um formulário encerrado DEVE continuar guardado e visível na tela Formulários com o motivo,
  e DEVE poder ser reaberto. Reaberto, volta a ser "sem destino", sem reacender o aviso do sino.
  Encerrar e reabrir DEVEM ficar no histórico de ações do sistema (quem, quando, motivo). O formulário
  mostra só o estado atual.
- **FR-009**: Formulários sem destino da mesma cliente, reconhecida pelo telefone, com a data igual ou
  não e de qualquer tipo, DEVEM aparecer numa linha só. A comercial DEVE poder escolher qual vale, e os
  demais são encerrados como "repetido" numa ação. Formulário sem telefone válido não se agrupa.
- **FR-010**: Se a cliente do formulário (pelo telefone) já tem evento na agenda a até 3 dias da data
  informada, para mais ou para menos, o sistema DEVE sugerir o vínculo na linha.
  - Só entram eventos sem formulário ligado, não cancelados, fora de ensaio e que não sejam satélite de
    um grupo (evento agrupado sob outro principal).
  - Com mais de um candidato, vale o de menor diferença de dias; empatados, o mais cedo.
  - A sugestão só vale quando a comercial confirma.
  - Uma sugestão descartada não volta para o mesmo par. O descarte é definitivo, e a ligação à mão
    continua possível. "Não é este" pede confirmação numa caixa curta, e descartar duas vezes o mesmo
    par não cria nada duplicado.
- **FR-011**: A regra automática de hoje (liga sozinho quando a data é exata e o telefone confirma)
  DEVE continuar como está. O vínculo automático passa a ter os mesmos efeitos de qualquer vínculo
  (FR-015 e FR-016). Formulário encerrado nunca é ligado automaticamente.
- **FR-012**: "Criar evento" a partir do formulário DEVE abrir o cadastro de evento preenchido, nos dois
  formatos de formulário que existem desde 01/06 (o do site e o da carga antiga do WhatsForm):
  - **Campos do evento**: data, início, fim, local, tipo, forma de pagamento e cliente. No
    corporativo, o local é o endereço do evento, nunca o da empresa.
  - **Observações do evento, com rótulo**: tema, espaço, aniversariante e idade, personagens pedidos,
    briefing (corporativo), observações contratuais e assessoria. Os personagens também entram como
    sugestão de elenco.
  - **A cliente**: a ficha ligada ao formulário; senão, a ficha com o mesmo telefone, como sugestão;
    senão, o cadastro rápido de cliente já preenchido com nome, telefone, e-mail e CPF/CNPJ.
  - **Não vêm do formulário**: valor de venda, vendedor e título. **Ficam só no formulário**: CPF,
    e-mail, endereço da contratante ou da empresa, razão social, CNPJ e representante.
  - Cada campo vindo do formulário DEVE aparecer com a marca "do formulário". A marca é informativa:
    salvar exige só os campos obrigatórios de sempre, exceto a data suspeita, que exige confirmação
    explícita. O botão Salvar nunca fica desabilitado por isso. Ao salvar sem confirmar, o campo da
    data é marcado com a explicação e a tela leva até ele.
- **FR-013**: No cadastro vindo do formulário, o sistema DEVE destacar com o motivo o que parece errado,
  mostrando o texto que a cliente escreveu:
  - data informada antes do dia em que o formulário chegou, ou mais de dois anos à frente;
  - hora ausente;
  - período que não dá para ler sem ambiguidade, ou que contradiz a hora: o fim fica em branco;
  - forma de pagamento sem correspondente no cadastro, deixada em branco;
  - tipo de contratação que o cadastro não reconhece, deixado em branco;
  - endereço sem número ou sem CEP;
  - a cliente (pelo telefone) já tem algum evento desde a data de início do sistema sem formulário
    ligado, em qualquer data. O aviso mostra a data desse evento e oferece ligar a ele em vez de criar outro.
- **FR-014**: Nada vindo do formulário DEVE ser gravado no evento sem a comercial salvar o cadastro.
- **FR-015**: Ao ligar um formulário a um evento, por qualquer caminho, o sistema DEVE:
  - dar ao formulário a cliente do evento, se o formulário não tem cliente;
  - dar ao evento a cliente do formulário, se o evento não tem cliente;
  - quando as duas existem e divergem, não mudar o evento, mostrar as duas e oferecer "usar a cliente
    do evento neste formulário".
  - **Divergem** quer dizer que a cliente do formulário não é nenhuma das clientes do evento.
  - A divergência aparece logo depois do vínculo nos caminhos da tela Formulários, da sugestão e do
    "Ligar a este evento" do cadastro. Em qualquer caminho, fica visível no detalhe do formulário até
    ser resolvida.
- **FR-016**: Quando o formulário ganha destino (ligado a evento ou encerrado), o aviso "nova resposta"
  daquele formulário DEVE sumir do sino de todos os destinatários que ainda não o tinham lido.
  - Formulário que já chega ligado a um evento pela regra automática não gera aviso.
  - Reabrir não reacende o aviso.
- **FR-017**: A tela Formulários DEVE continuar dando acesso a todos os formulários, histórico
  incluído, com os cartões de filtro organizados por destino.
  - Os cartões são "Sem destino (desde 01/06)", "Com evento", "Encerrados" e "Histórico (antes de
    01/06)". Eles somam o total.
  - O cartão "Sem destino" DEVE mostrar o mesmo número do painel da Home (fonte única).
  - "Sem cliente" e "Vínculo ambíguo" deixam de ser filtros: o primeiro se resolve pela FR-015, o
    segundo vira a sugestão da FR-010.
  - Quando um cartão tem mais formulários do que a lista mostra (200), a tela avisa "mostrando os 200
    mais recentes — use a busca".
  - A busca por nome, telefone ou data continua alcançando todos os formulários.
- **FR-018**: Toda ação desta feature (encerrar, reabrir, escolher entre repetidos, confirmar e
  descartar sugestão, usar a cliente do evento, criar evento) DEVE dar retorno visível enquanto
  acontece e ao terminar, e não pode criar registro duplicado com clique repetido.
  - Ação sobre um formulário cujo destino mudou nesse meio-tempo é recusada com "Este formulário já
    tem destino", e a lista se atualiza.
  - Ligar um formulário que já tem evento é recusado, nunca troca o vínculo em silêncio. Vale para
    todos os caminhos: tela Formulários, sugestão, criar evento, aba Comercial e edição do evento.
  - Reabrir um formulário que outra pessoa já reabriu responde "Este formulário não está mais
    encerrado".
  - A linha some na hora da Home de quem agiu; das outras pessoas, na próxima atualização da Home.
- **FR-019**: Na entrega, os avisos "nova resposta" já acesos sobre formulários com destino DEVEM ser
  marcados como lidos numa correção única, contada antes de executar.
- **FR-020**: Na entrega, os formulários chegados desde a data de início que já estão ligados a um
  evento com cliente, mas continuam sem cliente, DEVEM receber a cliente do evento (mesma regra da
  FR-015), numa correção única, contada antes de executar.

### Entidades *(se houver dados)*

- **Formulário** (resposta de formulário existente): ganha o registro do encerramento (motivo, frase
  livre quando "outro", quem encerrou, quando). Modelo em `app/models.py`, migration à mão, aditiva.
- **Sugestão descartada** (nova): o par formulário–evento que a comercial disse "não é este"
  (FR-010), com quem e quando.
- **Evento**: sem mudança de estrutura. Recebe a cliente do formulário quando não tem (FR-015).
- **Cliente**: sem mudança de estrutura. É a ponte da História 3 (telefone) e da FR-015.
- **Aviso do sino** (notificação existente): sem mudança de estrutura. Some quando o formulário ganha
  destino (FR-016).
- **Histórico de ações** (registro de auditoria existente): recebe encerrar e reabrir (FR-008).
- **Data de início do sistema** (configuração existente): é o corte da FR-001.

### RBAC *(obrigatório se houver endpoint novo ou alterado)*

- **Resumo da Home (alterado)**: mesmos papéis de hoje para o bloco de formulários — COMERCIAL,
  FINANCEIRO e SUPERADMIN. A Home respeita o "Ver como" do superadmin.
- **Encerrar, reabrir, escolher entre repetidos, confirmar e descartar sugestão, usar a cliente do
  evento (novos)**: COMERCIAL, FINANCEIRO e SUPERADMIN, os mesmos que hoje podem ligar um formulário a
  um evento.
- **Dados do formulário para o cadastro de evento (novo)**: quem pode criar evento, hoje COMERCIAL e
  SUPERADMIN.
- **Excluir formulário**: continua só SUPERADMIN.
- Os endpoints da tela Formulários continuam usando o papel real, não o "Ver como" (dívida 3.5, fora de
  escopo).
- Todas as linhas entram na tabela de `docs/01` §4.3 (Princípio XIII).

## Verificação (`verify_298.py`) *(obrigatório — Princípio VIII)*

Arquivo: `specs/298-formulario-vira-evento/verify_298.py`, contra `manto_local` (`DATABASE_URL` de
`.local-db-url`, `FLASK_ENV=development`, `MANTO_SEM_THREADS=1`). Login só por `POST /api/auth/login`;
escrita conferida por conexão separada; limpeza no `finally`. Formulários, clientes e eventos de teste
são semeados direto no banco, com prefixo próprio. Nenhum evento é criado nem apagado no Google
Agenda: dentro do processo do verify, a chamada ao Google é trocada por uma falsa, que falha se for
chamada. Todo evento de teste leva no título "[TESTE verify 298] pode apagar". O verify roda com a
data de início do sistema real do `manto_local`. Nunca semear `EventRole` com personagem inventado.

| # | Cenário | O que prova | Deve falhar? |
|---|---|---|---|
| 1 | Formulário chegado antes da data de início, sem evento (inclusive às 23h de 31/05, horário de SP); data de início vazia na configuração | fora do painel e de toda contagem; com a data vazia vale 01/06/2026 | não |
| 2 | Formulário desde junho, data informada futura, sem evento; dois com a mesma data e chegadas diferentes; FINANCEIRO logado | no grupo "ainda vai chegar", com cliente, tipo "Festa", data, distância e dias desde a chegada; com a mesma data, o que chegou por último vem primeiro; FINANCEIRO recebe `pode_criar_evento=false` | não |
| 3 | Formulário desde junho, data informada passada, sem evento | no grupo "já passou" | não |
| 4 | Formulário corporativo sem evento | aparece, identificado como "Corporativo" | não |
| 5 | Dois formulários do mesmo telefone, datas e tipos diferentes; um terceiro do mesmo telefone já ligado a evento | uma linha só, representada pelo último, com a marca "já tem outro formulário com evento"; escolher um encerra o outro como "repetido" | não |
| 6 | Encerrar com motivo | sai do painel; motivo, autor e data gravados (conexão separada); aviso some; ação no histórico | não |
| 7 | Reabrir | volta ao painel; o aviso não reacende; reabertura no histórico | não |
| 8 | Cliente com eventos a −1, +1 e +2 dias da data informada | sugere o de −1 (empate → o mais cedo); confirmar liga; descartar não volta; descartar de novo responde sem duplicar | não |
| 9 | Ligar formulário sem cliente a evento com cliente, e formulário com cliente divergente | ganha a cliente do evento; na divergência o evento não muda e "usar a cliente do evento" troca a do formulário; aviso some para todos | não |
| 10 | Evento ligado cancelado × excluído × encerrado que é ligado × desvincular (tela e aba Comercial) × encerrar formulário do histórico | cancelado: não volta; excluído e desvinculado: voltam; ligar desfaz o encerramento; o histórico não se encerra | não |
| 11 | Dados do formulário para o cadastro de evento, nos dois formatos e no corporativo | trazem os campos da FR-012; corporativo com o endereço do evento e o briefing; sem valor, vendedor e título | não |
| 12 | Data em 2049, pagamento "Boleto", período ambíguo, sem hora, endereço sem número e sem CEP, tipo não reconhecido, e cliente com evento sem formulário a 30 dias | todos os alertas da FR-013 presentes, com o texto da cliente e a data do evento existente | não |
| 13 | Contagens da tela Formulários | as quatro partições somam o total; "Sem destino" = número do painel da Home; a contagem traz a data do corte | não |
| 14a | Sync depois de encerrar; ligar formulário já ligado a outro evento pela tela, pela aba Comercial, pela edição do evento e pelo `POST /api/events` (Google trocado por uma chamada falsa) | o sync não religa o encerrado; os quatro caminhos recusam com "Este formulário já tem destino" sem trocar o primeiro vínculo; nada chega ao Google | não |
| 14b | Formulário que chega já ligado; os dois comandos de correção (avisos antigos e clientes dos já ligados) | nenhum aviso emitido; sem `--execute` só contam; com `--execute` aplicam (conexão separada) | não |
| 15 | CASTING tenta encerrar um formulário; FINANCEIRO pede os dados para o cadastro de evento | ambos recebem exatamente 403 e o formulário continua intacto (conexão separada); como controle, COMERCIAL recebe 200 no mesmo formulário | **sim** |
| 16 | Limpeza | usuários, formulários, eventos, avisos e registros de teste apagados (`roles.clear()` antes do usuário) | — |

Conferência de tela (Browser pane):
- **Home**: painel com e sem pendências, em tela de computador e estreita, com linha repetida,
  sugestão e movimento reduzido, e como FINANCEIRO;
- **tela Formulários**: um formulário encerrado e reaberto, e a divergência de cliente;
- **cadastro de evento** aberto a partir de um formulário de festa do site, um da carga WhatsForm e
  um corporativo, incluindo a data suspeita que exige confirmação (Salvar sem confirmar marca o campo
  e leva até ele).

## Critérios de sucesso *(obrigatório)*

- **SC-001**: A pendência de formulários na Home passa a refletir só o que chegou desde 01/06/2026. Com
  os dados de 10/09, cai de 1.347 para no máximo 36.
- **SC-002**: Em 100% das aberturas da Home com pendência, a primeira linha do painel é a linha cuja data
  informada é a mais próxima ainda por vir (ou, se não houver, a que passou mais recentemente), com
  nome e data visíveis sem abrir nada. Numa linha que junta formulários da mesma cliente, vale a data
  do formulário que chegou por último (FR-004).
- **SC-003**: Todo formulário chegado desde 01/06/2026 está em uma de três situações: ligado a evento,
  encerrado com motivo, ou visível no painel. Nenhum fica fora das três.
- **SC-004**: Formulário ligado a evento com cliente fica com cliente em 100% dos casos, inclusive os já
  ligados hoje, pela correção da FR-020. "Sem cliente" deixa de ser tarefa; hoje são 85 desde junho,
  cerca de 69 deles já ligados a evento com cliente.
- **SC-005**: Os formulários que já têm evento da mesma cliente em data igual ou próxima recebem a
  sugestão de vínculo. Hoje são 7.
- **SC-006**: Dos 7 campos do evento que o formulário cobre (data, início, fim, local, tipo, forma de
  pagamento e cliente), todos chegam preenchidos, exceto os que a cliente não informou ou que o sistema
  marcou como suspeitos.
- **SC-007**: Nenhum aviso "nova resposta" fica aceso sobre formulário que já tem destino. Hoje são 35.
- **SC-008**: O total de pendências do topo da Home deixa de somar o histórico de formulários. Hoje diz
  cerca de 1.363.

## Fora de escopo

- **Feature seguinte (plano aprovado, "B")**:
  - evento sem valor de venda como pendência;
  - "valor a definir" no cadastro;
  - grupo de eventos contado como uma venda só;
  - ajustes das cobranças.
- **Canais de lembrete**: aviso repetido no sino, e-mail, WhatsApp ou notificação no celular. O
  lembrete desta feature é a própria Home.
- **Evento sem formulário como pendência.** Há clientes que se recusam a preencher.
- **Acompanhamento do atendimento** antes do formulário (contatada, orçamento enviado, perdida). Isso
  vive no WhatsApp/Kommo.
- **O formulário público**, que a cliente preenche, não muda.
- **A regra automática de vínculo por data exata** continua como está (FR-011).
- **Desfazer o descarte de uma sugestão.**
- **Limpeza única de dados antigos**: datas impossíveis e formulários do histórico. Fica à parte, com
  o OK do dono.
- **"Ver como" na tela Formulários** (dívida 3.5 do `docs/05`).

## Docs a atualizar

- `docs/01`: contrato dos endpoints novos e alterados, schema do encerramento e das sugestões
  descartadas, head da migration e tabela de RBAC em §4.3.
- `docs/02`: a Home (painel novo), a tela Formulários e o cadastro de evento vindo do formulário.
- `docs/03`: entrada no topo.
- `docs/04`: invariante "todo formulário desde a data de início tem destino"; corte pela data de
  chegada.
- `docs/05`: registrar a limpeza de dados pendente e o limite do agrupamento (celular antigo sem o 9º
  dígito não agrupa).

## Premissas

- **Corte.** É a "data de início do sistema" já configurada, que as cobranças usam, hoje 01/06/2026.
  Mudou lá, muda aqui. Conta a data de CHEGADA do formulário (decisão do dono), no fuso de São Paulo.
- **Cores.** Decididas no `/speckit-clarify` de 10/09 (FR-005). Com os dados de 10/09, a Home teria 2
  linhas vermelhas.
- **Data próxima.** Decidida no `/speckit-clarify` de 10/09: até 3 dias no painel (FR-010), e aviso de
  qualquer evento sem formulário da cliente ao criar (FR-013).
- **"Há quantos dias chegou"**: em dias corridos, no fuso de São Paulo.
- **Quem trata.** Decidido no `/speckit-clarify` de 10/09: quem hoje vê e liga formulários
  (COMERCIAL, FINANCEIRO, SUPERADMIN) também encerra e reabre. Excluir continua só do SUPERADMIN. Não
  há usuário FINANCEIRO em produção hoje.
- **Encerrar é reversível.** Não apaga nada.
- **Agrupamento** pelo telefone normalizado que o formulário já guarda. Sem telefone válido, não agrupa.
- **Os números citados** são da produção em 10/09/2026, lidos em modo somente leitura, e servem de
  referência para os critérios de sucesso.
