# Feature Specification: Evento que cruza a meia-noite (termina no dia seguinte)

**Feature Branch**: `071-evento-cruza-meia-noite`

**Created**: 2026-06-22

**Status**: Draft

**Input**: "Ao criar um evento pelo sistema, às vezes o evento começa 20h e termina 00:30 do dia
seguinte. Hoje não dá para fazer pelo sistema; como paliativo eu criava pela agenda do Google e
esperava a sincronização. Gostaria de criar assim pelo próprio sistema."

## Contexto

Na criação de evento (e de ensaio), o horário de início e fim são combinados com **a mesma data**.
Se o fim for menor que o início (ex.: início 20:00, fim 00:30), o sistema rejeita com "Horário de
fim deve ser após o início". Por isso eventos que **viram a noite** não podem ser criados pelo
sistema — o usuário recorre à agenda do Google e espera a sincronização.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Criar evento que termina no dia seguinte (Priority: P1) 🎯 MVP

Como comercial, quero criar um evento que começa às 20:00 e termina às 00:30 do dia seguinte
direto pelo sistema, sem precisar usar a agenda do Google.

**Why this priority**: É o pedido central; hoje é impossível pelo sistema.

**Independent Test**: Criar um evento com início 20:00 e fim 00:30; o evento é salvo com término no
**dia seguinte** (duração 4h30) e aparece corretamente na agenda.

**Acceptance Scenarios**:

1. **Given** a tela de criar evento, **When** informo início 20:00 e fim 00:30, **Then** o evento é
   criado com fim no **dia seguinte** (sem erro), com duração de 4h30.
2. **Given** início 20:00 e fim 00:30, **When** a tela está aberta, **Then** vejo um aviso de que o
   evento **termina no dia seguinte**.
3. **Given** início 14:00 e fim 18:00 (mesmo dia), **When** crio, **Then** o comportamento é o de
   sempre (mesma data, sem virar a noite).

### User Story 2 - Mesmo comportamento para ensaios (Priority: P2)

Como equipe de ensaio, quero o mesmo tratamento ao **criar/editar ensaios** que cruzam a meia-noite.

**Acceptance Scenarios**:

1. **Given** criar/editar ensaio com fim menor que o início, **When** salvo, **Then** o ensaio
   termina no dia seguinte (sem erro).

### Edge Cases

- **Fim igual ao início** (ex.: 20:00 e 20:00): continua **bloqueado** (evento de duração zero é
  erro; não é "virar a noite").
- **Mesmo dia (fim > início)**: inalterado.
- **Sincronização com a agenda**: o evento criado deve refletir início e fim em dias diferentes,
  consistente com o que a agenda do Google faz.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Ao criar um evento, se o horário de **fim for menor** que o de início, o sistema MUST
  interpretar o fim como sendo **no dia seguinte** (evento cruza a meia-noite), salvando início e
  fim com datas corretas.
- **FR-002**: O sistema MUST manter o comportamento atual quando o fim é **maior** que o início
  (mesmo dia).
- **FR-003**: O sistema MUST continuar **rejeitando** quando início e fim são **iguais** (duração
  zero), com mensagem clara.
- **FR-004**: A tela de criação MUST **avisar** o usuário, de forma sutil, quando o evento termina
  no dia seguinte.
- **FR-005**: O mesmo tratamento (fim < início ⇒ dia seguinte) MUST valer para **criar e editar
  ensaios**.
- **FR-006**: O evento criado MUST refletir corretamente na agenda integrada (início e fim em dias
  diferentes), como já acontece quando criado pela agenda do Google.

### Key Entities

- **Evento / Ensaio (existentes)**: têm início e fim (data + hora). Passa a ser permitido fim no dia
  seguinte do início.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: É possível criar pelo sistema um evento 20:00→00:30 com término no dia seguinte
  (duração 4h30), sem recorrer à agenda do Google.
- **SC-002**: Eventos do mesmo dia continuam funcionando exatamente como antes.
- **SC-003**: Início igual ao fim continua sendo rejeitado.
- **SC-004**: Criar/editar ensaios que viram a noite também funciona.

## Assumptions

- Não há eventos com mais de 24h pela tela (o fim sempre cai no dia seguinte do início, no máximo).
- A duração máxima implícita ao virar a noite é < 24h (ex.: início 20:00, fim 19:00 viraria 23h —
  raro, mas tratado como dia seguinte; não é objetivo bloquear esse caso).
- Mudança de interpretação de horário; sem mudança de modelo nem migration.
