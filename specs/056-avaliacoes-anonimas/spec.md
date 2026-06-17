# Feature Specification: Avaliações anônimas + função no evento

**Feature Branch**: `056-avaliacoes-anonimas`

**Created**: 2026-06-17

**Status**: Draft

**Input**: User description: "Preciso de um botão na .../talents/avaliacoes — para todos os outros usuários que têm acesso a essa página, todos comentários devem ser anônimos. Somente super admin deve poder ver quem fez o comentário de fato. Porém, deve ter um botão na página para poder ativar o modo anônimo, assim não aparece nem pro admin. E gostaria de deixar claro para a pessoa no portal que as avaliações deixadas serão anônimas. Também quero que ao lado do nome da pessoa, quando não anônimo, apareça qual era a função da pessoa no evento."

## Contexto

A página de resumo de avaliações (`/talents/avaliacoes`) hoje mostra, em cada comentário,
o **nome do talento** que avaliou. O cliente quer proteger a identidade de quem avalia:
por padrão, os nomes ficam **anônimos** para quase todos; apenas o **super admin** vê quem
escreveu. Além disso, deve existir um **modo anônimo total** (ativável por um botão na
página) que esconde a autoria até do super admin. No **portal do talento**, deve ficar
**claro** que as avaliações são anônimas. E, quando a autoria está visível (super admin,
sem modo total), deve aparecer ao lado do nome a **função que a pessoa teve no evento**.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Comentários anônimos por padrão; só super admin vê o autor (Priority: P1) 🎯 MVP

Como empresa, quero que os nomes de quem avalia fiquem ocultos para todos os usuários da
página de avaliações, exceto o super admin, para proteger a identidade de quem dá feedback.

**Why this priority**: É o coração do pedido — privacidade da autoria. Sem isso a feature
não existe.

**Independent Test**: Abrir `/talents/avaliacoes` com um usuário não-super-admin (ex.:
casting) e confirmar que todos os comentários aparecem como "Anônimo"; abrir com super
admin e confirmar que os nomes reais aparecem.

**Acceptance Scenarios**:

1. **Given** um usuário com acesso à página que **não** é super admin, **When** vê a lista
   de comentários/pontos de atenção, **Then** todos aparecem como "Anônimo" (sem nome,
   sem qualquer identificador da pessoa).
2. **Given** um **super admin**, **When** vê a lista, **Then** os nomes reais dos autores
   aparecem (modo anônimo total desligado).
3. **Given** qualquer recorte (filtros de período/categoria/evento), **When** aplicado,
   **Then** a regra de anonimato vale igualmente em comentários, pontos de atenção e em
   qualquer lugar que antes exibia o nome do autor.

---

### User Story 2 - Botão de modo anônimo total (esconde até do super admin) (Priority: P1)

Como super admin, quero um botão na página de avaliações para ativar o **modo anônimo
total**, de forma que nem eu consiga ver quem escreveu, garantindo anonimato pleno quando
necessário.

**Why this priority**: Pedido explícito e indivisível do controle de privacidade. Depende
da US1 (mecanismo de exibição do autor).

**Independent Test**: Como super admin, ativar o modo anônimo total pelo botão; confirmar
que os comentários passam a aparecer como "Anônimo" mesmo para o super admin; desativar e
confirmar que os nomes voltam.

**Acceptance Scenarios**:

1. **Given** o super admin na página, **When** ativa o modo anônimo total pelo botão,
   **Then** todos os comentários passam a aparecer como "Anônimo" para **todos**, inclusive
   o super admin.
2. **Given** o modo anônimo total ativo, **When** o super admin desativa pelo botão,
   **Then** os nomes reais voltam a aparecer para o super admin (e seguem ocultos para os
   demais).
3. **Given** o estado do modo (ligado/desligado), **When** a página é recarregada ou
   acessada por outra pessoa, **Then** o estado é o mesmo (a configuração é persistente e
   única para todo o sistema).
4. **Given** um usuário que **não** é super admin, **When** vê a página, **Then** o botão de
   modo anônimo total **não** está disponível para ele (apenas super admin controla).

---

### User Story 3 - Aviso de anonimato no portal do talento (Priority: P2)

Como talento avaliando um evento pelo portal, quero ver claramente que minha avaliação será
anônima, para me sentir seguro ao dar feedback honesto.

**Why this priority**: Aumenta a honestidade e a confiança no feedback; complementa a
privacidade, mas é independente da exibição interna (US1/US2).

**Independent Test**: Abrir a tela de avaliar um evento no portal e confirmar que há uma
mensagem clara de que a avaliação é anônima.

**Acceptance Scenarios**:

1. **Given** o talento na tela de avaliação do portal (nota geral e/ou detalhada), **When** a
   tela é exibida, **Then** há um aviso claro, em português, de que as avaliações são
   anônimas.
2. **Given** o aviso, **When** lido, **Then** a linguagem é amigável e sem jargão técnico.

---

### User Story 4 - Função no evento ao lado do nome (quando não anônimo) (Priority: P3)

Como super admin vendo a autoria, quero ver ao lado do nome a **função/papel que a pessoa
teve no evento** avaliado, para contextualizar de que ponto de vista veio o feedback.

**Why this priority**: Enriquecimento de contexto; só faz sentido quando o nome está
visível, portanto depende da US1.

**Independent Test**: Como super admin (modo total desligado), abrir um comentário de um
talento que teve um papel no evento e confirmar que a função aparece ao lado do nome.

**Acceptance Scenarios**:

1. **Given** um comentário com autoria visível (super admin, modo total desligado), **When**
   exibido, **Then** ao lado do nome aparece a função/papel que aquela pessoa teve **naquele
   evento**.
2. **Given** um comentário exibido como "Anônimo", **When** exibido, **Then** a função
   **não** aparece (não pode servir para reidentificar a pessoa).
3. **Given** um autor sem função registrada naquele evento, **When** exibido, **Then** mostra
   só o nome, sem função (sem erro/placeholder confuso).

---

### Edge Cases

- **Reidentificação**: quando anônimo, nenhum dado que identifique a pessoa pode aparecer
  (nem nome, nem função, nem link para o perfil do talento).
- **Modo total + super admin**: prevalece o anonimato total — super admin também vê
  "Anônimo".
- **Função ausente**: autor sem papel cadastrado no evento → exibe só o nome.
- **Mais de uma função no mesmo evento**: exibir as funções de forma legível (ex.:
  separadas por vírgula) sem poluir.
- **Avaliação de categoria sobre outra pessoa (subject)**: o anonimato se aplica a **quem
  avaliou** (autor); a regra de exibição da pessoa avaliada (subject) segue o que já existe
  hoje, sem regressão.
- **Toggle por usuário sem permissão**: tentativa de ativar/desativar o modo total por quem
  não é super admin é recusada.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Na página de avaliações, o sistema MUST exibir todos os autores de
  comentários como **"Anônimo"** para qualquer usuário que **não** seja super admin.
- **FR-002**: O sistema MUST permitir que o **super admin** veja o nome real do autor de
  cada comentário, **exceto** quando o modo anônimo total estiver ativo.
- **FR-003**: O sistema MUST oferecer, na página de avaliações, um **botão/controle** para
  ativar e desativar o **modo anônimo total**, disponível **somente** para super admin.
- **FR-004**: Quando o modo anônimo total estiver ativo, o sistema MUST exibir todos os
  autores como "Anônimo" para **todos os usuários, inclusive o super admin**.
- **FR-005**: O estado do modo anônimo total MUST ser **persistente e único para todo o
  sistema** (vale para todos os acessos até ser alterado).
- **FR-006**: O sistema MUST garantir que, quando um comentário é anônimo, **nenhum dado**
  que identifique a pessoa seja exibido (nome, função, link de perfil) — anonimato real, não
  apenas ocultação visual de um campo.
- **FR-007**: No **portal do talento**, nas telas de avaliação de evento, o sistema MUST
  exibir um **aviso claro, em pt-BR**, de que as avaliações são anônimas.
- **FR-008**: Quando a autoria está visível (super admin, modo total desligado), o sistema
  MUST exibir ao lado do nome a **função/papel** que a pessoa teve **naquele evento**.
- **FR-009**: Quando o autor não tiver função registrada no evento, o sistema MUST exibir
  apenas o nome, sem função e sem erro.
- **FR-010**: A mudança do modo anônimo total MUST registrar quem alterou e quando
  (auditoria), reaproveitando o mecanismo de log já existente no projeto.
- **FR-011**: O acesso à página de avaliações MUST permanecer restrito aos perfis que já a
  acessam hoje (sem ampliar nem reduzir o acesso por conta desta feature).

### Key Entities

- **Avaliação de evento (existente)**: feedback submetido por um talento sobre um evento
  (nota, comentário, subcategorias). O **autor** é o talento que avaliou. Esta feature não
  muda os dados da avaliação; muda **como a autoria é exibida**.
- **Configuração do sistema (existente)**: ganha um indicador de **modo anônimo total**
  (ligado/desligado), único para todo o sistema.
- **Função no evento (existente)**: papel/personagem que um talento teve em um evento; usado
  para exibir a função ao lado do nome quando a autoria está visível.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% dos comentários aparecem como "Anônimo" para usuários não-super-admin.
- **SC-002**: Com o modo anônimo total **ativo**, 100% dos comentários aparecem como
  "Anônimo" inclusive para o super admin.
- **SC-003**: Com o modo total **desligado**, o super admin vê o nome real em 100% dos
  comentários cujo autor é conhecido, com a função do evento ao lado quando houver.
- **SC-004**: Nenhum dado identificável (nome, função, link de perfil) aparece em
  comentários anônimos — verificável inspecionando a página em cada perfil de acesso.
- **SC-005**: O talento, ao avaliar pelo portal, vê o aviso de anonimato em 100% das telas
  de avaliação.
- **SC-006**: O estado do modo total persiste entre acessos e usuários (uma fonte única de
  verdade).

## Assumptions

- "Todos os outros usuários que têm acesso a essa página" = os perfis que hoje acessam
  `/talents/avaliacoes` (atualmente SUPERADMIN e CASTING). A regra: super admin vê o autor
  (salvo modo total); os demais sempre veem "Anônimo".
- O **modo anônimo total** é um **interruptor único e global** do sistema (não por
  comentário), condizente com "um botão na página". Apenas super admin pode alterná-lo.
- O "autor" do comentário é o **talento** que enviou a avaliação. O anonimato protege o
  autor; a exibição de uma eventual **pessoa avaliada** (subject de subcategoria) segue o
  comportamento atual, sem mudança.
- A "função no evento" é o **papel/personagem** que o talento teve no evento avaliado
  (já registrado no sistema). Quando houver mais de um, são exibidos juntos.
- O aviso de anonimato no portal é **informativo** (texto), nas telas de avaliação já
  existentes — sem mudar o fluxo de envio.
- Não há mudança nas notas, médias e indicadores já calculados — apenas na **exibição da
  autoria** e no **aviso** do portal.
