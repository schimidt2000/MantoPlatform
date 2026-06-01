# Feature Specification: Local de saída configurável + logística no convite

**Feature Branch**: `007-logistica-saida`

**Created**: 2026-05-30

**Status**: Draft

**Input**: User description: "Na logística de saída do evento, poder mudar de onde será a saída
— por padrão 'Manto Produções', mas permitir outros endereços. E verificar se essas
informações estão indo para a pessoa ao convidar."

## Contexto

Na logística do evento, hoje só se define o **horário** de saída — o local é fixo ("saída da
Manto"). Às vezes a saída acontece de outro endereço. Além disso, ao convidar um talento, o
e-mail de convite **não inclui** as informações de logística (saída/maquiagem); elas só
aparecem no portal. O usuário quer (1) poder escolher o local de saída e (2) garantir que a
logística chegue ao talento no convite.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Definir o local de saída (Priority: P1)

Ao preencher a logística de um evento, além do horário, dá para definir **de onde** será a
saída. Por padrão vem "Manto Produções"; é possível trocar por outro endereço.

**Why this priority**: É o pedido central — saídas nem sempre são da Manto.

**Independent Test**: Editar a logística, deixar o padrão e salvar (fica "Manto Produções");
depois trocar para outro endereço e salvar (fica o endereço digitado).

**Acceptance Scenarios**:

1. **Given** a logística de um evento, **When** o usuário a abre, **Then** o local de saída vem
   preenchido com "Manto Produções" por padrão.
2. **Given** o usuário troca o local para outro endereço e salva, **When** reabre o evento,
   **Then** o local de saída mostra o endereço digitado.
3. **Given** o local de saída foi alterado em um evento com talentos confirmados, **When** salva,
   **Then** os talentos confirmados são notificados da mudança (como já ocorre com horário).

---

### User Story 2 - Logística chega ao talento no convite (Priority: P1)

Ao convidar um talento, o e-mail de convite passa a incluir as informações de logística
disponíveis — horário e local de saída, e horário/local de maquiagem — para que a pessoa receba
tudo já no convite, não só no portal.

**Why this priority**: O usuário relatou a dúvida de "se está indo"; hoje **não vai** — a
logística não aparece no convite.

**Independent Test**: Convidar um talento para um evento que tem saída e maquiagem definidas e
confirmar que o e-mail recebido lista essas informações.

**Acceptance Scenarios**:

1. **Given** um evento com horário e local de saída definidos, **When** o talento é convidado,
   **Then** o e-mail de convite mostra o horário e o local de saída.
2. **Given** um evento com maquiagem definida, **When** o talento é convidado, **Then** o e-mail
   inclui horário e local de maquiagem.
3. **Given** um evento sem logística preenchida, **When** o talento é convidado, **Then** o
   e-mail é enviado normalmente, apenas sem as linhas de logística (sem campos vazios).

---

### Edge Cases

- **Local de saída vazio**: trata-se como o padrão "Manto Produções" (nunca fica em branco).
- **Convite enviado antes de definir a logística**: o e-mail sai sem logística; quando a
  logística muda depois, vale a notificação de alteração já existente.
- **Eventos antigos sem local de saída**: assumem o padrão "Manto Produções" ao exibir.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: A logística do evento MUST permitir definir o **local de saída**, além do horário.
- **FR-002**: O local de saída MUST ter "Manto Produções" como valor padrão.
- **FR-003**: O usuário MUST poder substituir o local de saída por qualquer outro endereço.
- **FR-004**: Alterar o local de saída em evento com talentos confirmados MUST notificá-los, no
  mesmo fluxo das demais mudanças de logística.
- **FR-005**: O e-mail de convite MUST incluir as informações de logística disponíveis: horário
  e local de saída, e horário e local de maquiagem.
- **FR-006**: Quando uma informação de logística não estiver definida, o e-mail NÃO MUST exibir a
  linha correspondente (sem campos vazios).
- **FR-007**: O local de saída exibido MUST cair no padrão "Manto Produções" quando estiver vazio.

### Key Entities *(include if feature involves data)*

- **Evento** (já existe): ganha o **local de saída** (texto), além do horário de saída que já
  existe. Maquiagem (horário/local) já existe.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: O usuário define um local de saída diferente do padrão em no máximo 1 campo editável.
- **SC-002**: 100% dos convites de eventos com logística definida incluem essas informações no e-mail.
- **SC-003**: 0 convites com linhas de logística vazias.
- **SC-004**: O local de saída nunca aparece em branco (mínimo: "Manto Produções").

## Assumptions

- "Manto Produções" como padrão refere-se ao endereço base da empresa já usado para cálculo de
  rota; o texto exibido por padrão é "Manto Produções".
- O local de saída é um texto livre (endereço), análogo ao local de maquiagem.
- A notificação de mudança de logística reutiliza o mecanismo já existente (talentos confirmados).
- A logística incluída no convite cobre saída (horário + local) e maquiagem (horário + local),
  que são os campos de logística existentes hoje.
