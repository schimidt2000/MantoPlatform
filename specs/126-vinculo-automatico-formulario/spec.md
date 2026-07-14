# Feature Specification: Vínculo Automático de Formulário a Evento da Agenda

**Feature Branch**: `126-vinculo-automatico-formulario`

**Created**: 2026-07-13

**Status**: Draft

**Input**: "Já aconteceu na história de uma cliente preencher o formulário e dar uma
sumida, e chegar no dia antes da festa e falar 'e aí, tudo certo pro nosso evento?'.
Quando uma cliente preencher um formulário, associar automaticamente a um evento se ele
existir na agenda. Podemos associar por data e depois pela cliente associada. Precisamos
deixar isso muito robusto."

## Contexto

Hoje, uma resposta de formulário de pré-contrato só fica ligada a um evento da agenda de
duas formas manuais: (1) alguém cria o evento em `/events/new` e escolhe a resposta na
busca, ou (2) ninguém faz nada e a resposta fica solta, sem vínculo. Quando o evento já
existe na agenda ANTES da cliente preencher o formulário (o caso mais comum — o evento
foi negociado e agendado, e o formulário é só a formalização dos dados), não existe
nenhum mecanismo que conecte os dois automaticamente. O time só descobre que uma cliente
"sumiu" depois de preencher o formulário quando alguém abre a resposta manualmente e
percebe a falta de retorno — às vezes tarde demais, como no caso relatado (véspera do
evento).

Esta feature cria essa ponte automaticamente, mas de forma conservadora: só vincula
sozinha quando tem certeza razoável; quando não tem, evita adivinhar e chama a atenção de
alguém para revisar — nunca finge que está tudo certo quando não está.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Vínculo automático por data (Priority: P1)

Uma cliente preenche o formulário público informando a data do evento. Se existir
exatamente um evento real (não ensaio) na agenda naquela data, a resposta é vinculada a
ele automaticamente, sem qualquer ação manual — o time vê a resposta já conectada ao
evento correto assim que olha a agenda ou a resposta.

**Why this priority**: é o núcleo do pedido e cobre a maioria dos casos reais (a
esmagadora maioria dos dias tem no máximo um evento agendado) — sozinho já evita a
maior parte do cenário relatado.

**Independent Test**: criar um evento futuro numa data X; preencher o formulário público
informando a data X; conferir que a resposta aparece já vinculada a esse evento, sem
nenhuma ação manual.

**Acceptance Scenarios**:

1. **Given** um evento real (não ensaio) cadastrado numa data, **When** uma resposta de
   formulário chega informando a mesma data, **Then** a resposta é vinculada
   automaticamente a esse evento.
2. **Given** nenhum evento cadastrado na data informada pela resposta, **When** a
   resposta é enviada, **Then** ela permanece sem vínculo automático (nada é inventado).
3. **Given** um evento do tipo ensaio na data informada, **When** a resposta é
   enviada, **Then** o ensaio NÃO é usado como vínculo (ensaio não é o evento comercial).

---

### User Story 2 - Desambiguação por cliente quando a data não resolve sozinha (Priority: P2)

Existem dois ou mais eventos na mesma data (ou nenhum evento na data informada), mas o
telefone de quem preencheu o formulário já está associado a um cliente que, por sua vez,
já está associado a um dos eventos candidatos. Nesse caso, o sistema usa essa segunda
informação para decidir com segurança.

**Why this priority**: cobre os casos em que só a data não é suficiente (dias com mais
de um evento) — depende da User Story 1 já existir, mas resolve os casos que ela sozinha
deixaria sem vínculo.

**Independent Test**: criar dois eventos na mesma data; associar um cliente a um deles;
preencher o formulário com o telefone desse cliente e a mesma data; conferir que a
resposta é vinculada ao evento certo (o que já tinha aquele cliente), não a qualquer um
dos dois.

**Acceptance Scenarios**:

1. **Given** dois eventos na mesma data, um já associado a um cliente cujo telefone bate
   com o da resposta, **When** a resposta chega, **Then** ela é vinculada ao evento que
   já tinha aquele cliente associado.
2. **Given** dois eventos na mesma data e nenhum deles tem cliente associado que bata com
   o telefone da resposta, **When** a resposta chega, **Then** ela NÃO é vinculada
   automaticamente a nenhum dos dois — fica marcada para revisão manual (User Story 3).
3. **Given** nenhum evento na data informada, mas o telefone da resposta já pertence a um
   cliente com exatamente um evento futuro associado, **When** a resposta chega, **Then**
   ela é vinculada a esse evento (a data informada pode estar errada/for a de sincronia,
   mas a identidade da cliente resolve o caso).
4. **Given** um evento que bate pela data, mas cujo cliente já associado tem um telefone
   diferente do telefone da resposta, **When** a resposta chega, **Then** o vínculo
   automático NÃO é feito — o conflito entre os dois sinais vai para revisão manual em vez
   de arriscar um vínculo errado.

---

### User Story 3 - Aviso quando ninguém pode ter certeza sozinho (Priority: P2)

Quando a associação automática não consegue decidir com segurança (ambiguidade ou
conflito entre os sinais), a resposta aparece destacada num aviso na home para alguém do
comercial revisar e associar manualmente — a mesma robustez de "nunca deixar passar" que
motivou o pedido, só que reconhecendo os limites do que dá para automatizar sozinho.

**Why this priority**: é o que efetivamente cumpre "deixar isso muito robusto" — uma
automação que erra vinculando o evento errado é pior do que nenhuma automação; o aviso é
a rede de segurança que evita isso.

**Independent Test**: gerar um caso ambíguo (dois eventos na mesma data, nenhum
associável por cliente); conferir que a resposta aparece no aviso de revisão da home, e
que segue disponível para associação manual normalmente.

**Acceptance Scenarios**:

1. **Given** uma resposta cujo vínculo automático ficou ambíguo/conflitante, **When** um
   usuário comercial abre a home, **Then** vê essa resposta destacada num aviso
   específico de revisão, distinto do aviso já existente de "resposta sem cliente".
2. **Given** essa resposta em revisão, **When** alguém a associa manualmente a um evento,
   **Then** ela some do aviso de revisão (como já acontece hoje com associação manual).

---

### User Story 4 - Corrigir um vínculo automático errado (Priority: P3)

Se, apesar dos cuidados, um vínculo automático acabar errado (situação rara, mas
possível), alguém do comercial consegue desfazer esse vínculo e associar manualmente ao
evento certo, do mesmo jeito que já é possível desfazer um vínculo de cliente.

**Why this priority**: é uma rede de segurança final — importante para robustez, mas só
é usada em exceções, depois que a maior parte dos casos (US1-US3) já está coberta.

**Independent Test**: numa resposta com vínculo automático a um evento, desfazer esse
vínculo pela tela de detalhe e confirmar que ela volta ao estado "sem evento", disponível
para associação manual novamente.

**Acceptance Scenarios**:

1. **Given** uma resposta vinculada automaticamente a um evento, **When** um usuário
   comercial desfaz esse vínculo, **Then** a resposta volta a ficar sem evento associado,
   sem apagar nenhum outro dado da resposta.

### Edge Cases

- Uma resposta chega para um evento que já tem OUTRA resposta de formulário vinculada
  (ex.: a cliente preencheu duas vezes por engano): a segunda vinculação não pode
  duplicar/confundir o vínculo já existente — vira caso de revisão manual em vez de
  sobrescrever silenciosamente.
- O evento associável fica marcado como "cortesia/permuta" ou "sem valor": não muda a
  lógica de vínculo — o vínculo é sobre identificar o evento certo, não sobre o tipo dele.
- Um evento é criado na agenda DEPOIS de uma resposta já ter chegado sem conseguir vínculo
  algum: a resposta não fica órfã para sempre — o sistema tenta de novo automaticamente
  quando a agenda muda (mesmo mecanismo que já verifica a agenda periodicamente).
- Respostas que já existiam antes desta feature entrar no ar e nunca foram vinculadas:
  passam pela mesma tentativa de vínculo automático uma vez, ao lançar a feature (não
  ficam de fora só por serem antigas).
- Um evento satélite (agrupado sob um evento principal) não deve ser tratado como um
  candidato de vínculo independente — segue a mesma regra que já existe hoje para outras
  tarefas do sistema relacionadas a eventos agrupados.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Ao receber uma resposta de formulário com data de evento informada, o
  sistema DEVE tentar vinculá-la automaticamente a um evento real (não ensaio, não
  satélite) da agenda que caia exatamente nessa data.
- **FR-002**: Se exatamente um evento real for encontrado na data informada, o vínculo
  DEVE ser feito automaticamente, sem exigir nenhuma ação manual.
- **FR-003**: Se mais de um evento real for encontrado na mesma data, ou nenhum evento
  for encontrado na data informada, o sistema DEVE tentar um segundo critério: localizar
  um cliente já cadastrado cujo telefone bata com o da resposta, e verificar se esse
  cliente já está associado a algum dos eventos candidatos (ou a um único evento futuro,
  quando não há candidato por data).
- **FR-004**: O vínculo automático só pode ser feito quando os sinais disponíveis (data e
  cliente) não se contradizem. Havendo conflito ou ambiguidade que os critérios acima não
  resolvam, o sistema NÃO PODE adivinhar — a resposta permanece sem vínculo automático.
- **FR-005**: Toda resposta que não conseguiu vínculo automático por ambiguidade/conflito
  (não pela simples ausência de evento na data) DEVE aparecer num aviso de revisão
  visível para o time comercial, distinto do aviso já existente de "resposta sem
  cliente".
- **FR-006**: A tentativa de vínculo automático DEVE ser repetida para respostas ainda
  sem evento sempre que a agenda for atualizada (para cobrir o caso em que o evento é
  criado depois da resposta ter chegado).
- **FR-007**: Ao entrar em uso, a feature DEVE tentar vincular automaticamente, uma
  única vez, as respostas que já existiam e ainda não tinham nenhum evento associado.
- **FR-008**: Um usuário comercial DEVE poder desfazer um vínculo automático (ou manual)
  de evento numa resposta, do mesmo jeito que já é possível desfazer o vínculo com um
  cliente.
- **FR-009**: Um vínculo automático bem-sucedido DEVE registrar, de forma consultável,
  que a associação foi feita automaticamente e por qual critério (data e/ou cliente) —
  para que alguém revisando depois entenda por que aquele vínculo existe.
- **FR-010**: O comportamento de associação manual já existente (buscar e escolher um
  evento/uma resposta) continua funcionando exatamente como hoje, em paralelo ao vínculo
  automático — a automação complementa, não substitui, o fluxo manual.

### Key Entities

- **Resposta de formulário** (`FormResponse`, já existente): ganha um vínculo automático
  de evento quando os critérios acima permitem, mantendo a possibilidade de vínculo
  manual e de desfazer o vínculo.
- **Evento da agenda** (já existente): passa a ser candidato de vínculo automático
  quando é um evento real (não ensaio, não satélite) numa data compatível com uma
  resposta pendente.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Uma resposta enviada para a data de um evento único na agenda aparece
  vinculada a esse evento imediatamente, sem intervenção manual.
- **SC-002**: Zero vínculos automáticos incorretos em cenários de ambiguidade/conflito —
  nesses casos, a resposta vai para revisão manual em vez de um vínculo adivinhado.
- **SC-003**: 100% das respostas que ficam sem vínculo automático por ambiguidade
  aparecem no aviso de revisão da home.
- **SC-004**: Uma resposta que não encontrou vínculo no envio, mas cujo evento é criado
  depois, acaba vinculada automaticamente sem precisar que alguém volte à resposta.
- **SC-005**: 100% do estoque de respostas antigas sem vínculo passa pela tentativa
  automática uma vez, ao lançar a feature.
- **SC-006**: Um vínculo automático incorreto pode ser desfeito por um usuário comercial
  em poucos cliques, sem perder nenhum outro dado da resposta.

## Assumptions

- "Evento real" exclui ensaios e eventos satélites (agrupados sob um evento principal) —
  mesma exclusão já usada hoje em outras tarefas automáticas do sistema relacionadas à
  agenda.
- O critério de desempate por "cliente já associada" usa o telefone normalizado da
  resposta para encontrar um cliente já cadastrado, e a associação desse cliente a
  eventos já existente no sistema (não cria cliente novo como parte desta feature — isso
  já é possível pelo fluxo manual existente).
- A tentativa periódica de vínculo (para eventos criados depois da resposta) usa o mesmo
  processo que já mantém a agenda sincronizada periodicamente — não é um mecanismo
  novo e separado de verificação.
- O aviso de revisão de vínculo ambíguo é uma seção nova, mas segue o mesmo padrão visual
  e de acesso (time comercial) do aviso já existente de "resposta sem cliente" na home.
- Cortesia/permuta e "sem valor" no evento não influenciam a lógica de vínculo — são
  atributos independentes de qual evento é o correto.
