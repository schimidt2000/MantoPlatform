# Feature Specification: Avaliar evento só depois que ele ACABOU

**Feature Branch**: `039-avaliar-so-apos-fim`

**Created**: 2026-06-12

**Status**: Draft

**Input**: User description: "Esse evento estava aparecendo pra avaliar antes mesmo de ter começado.
Só deve aparecer para avaliar o evento quando ele tiver ACABADO." (print: evento de 09/06/2026
15:00–17:00 aparecendo em 'Avalie seus eventos' às 14:54 do mesmo dia)

## Contexto

No portal do talento, o destaque **"Avalie seus eventos"** mostrou um evento que ainda nem havia
começado (faltavam ~3 horas). Causa: as comparações de "evento já terminou/é futuro" no portal usam
o relógio **UTC**, enquanto os horários dos eventos são gravados em **horário de Brasília** — tudo no
portal "anda" 3 horas adiantado. O mesmo desvio afeta as listas de próximos eventos e histórico, e a
janela de edição de avaliações.

Além disso, a tela de avaliação aceita envio mesmo antes do fim do evento se acessada direto pela URL
(não há trava no servidor).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Avaliação só aparece após o término (Priority: P1)

O talento só vê o evento em "Avalie seus eventos" depois que o horário de término do evento passou
(horário de Brasília).

**Why this priority**: é o bug reportado; avaliar antes do evento gera dados sem sentido.

**Independent Test**: com um evento terminando às 17:00, conferir que às 16:59 ele NÃO aparece para
avaliar e que depois das 17:00 aparece.

**Acceptance Scenarios**:

1. **Given** um evento de hoje das 15:00 às 17:00, **When** o talento abre o portal às 14:54, **Then**
   o evento NÃO aparece em "Avalie seus eventos".
2. **Given** o mesmo evento, **When** o talento abre o portal após as 17:00, **Then** o evento aparece
   para avaliar (dentro da janela de 7 dias já existente).
3. **Given** um evento sem horário de término cadastrado, **When** o início já passou, **Then** vale o
   comportamento atual (início como referência).

---

### User Story 2 - Trava no servidor (Priority: P1)

Mesmo com o link direto da tela de avaliação, o sistema recusa abrir/enviar avaliação de evento que
ainda não terminou.

**Acceptance Scenarios**:

1. **Given** um evento que ainda não terminou, **When** o talento acessa a URL de avaliação, **Then**
   é redirecionado com aviso claro de que a avaliação abre após o término.
2. **Given** um evento que ainda não terminou, **When** um envio de avaliação chega ao servidor,
   **Then** ele é recusado (nada é gravado).

---

### User Story 3 - Horário de Brasília em todo o portal (Priority: P2)

Todas as classificações de tempo do portal (próximos eventos, histórico, janela de edição de
avaliação) usam o horário de Brasília — um evento só vira "passado" quando realmente passou.

**Acceptance Scenarios**:

1. **Given** um evento que começa daqui a 2 horas, **When** o talento abre o portal, **Then** ele
   está em "Próximos eventos" (hoje, com o desvio de 3h, ele pode sumir de lá antes da hora).
2. **Given** um evento que acabou há minutos, **When** o talento abre o histórico, **Then** o evento
   já consta como passado.

---

### Edge Cases

- **Evento em andamento** (começou, não terminou): não aparece para avaliar; envio é recusado.
- **Evento sem término**: usa o início como referência (regra atual mantida).
- **Janelas existentes preservadas**: avaliar até 7 dias após o fim; editar até 30 dias — apenas o
  relógio de referência muda para Brasília.
- **Registros de data/hora internos** (aceite de termos, data de envio/edição da avaliação) não mudam.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O destaque "Avalie seus eventos" MUST listar apenas eventos cujo término (ou início, se
  sem término) já passou no horário de Brasília.
- **FR-002**: A tela de avaliação MUST recusar abrir e gravar avaliações de eventos não terminados
  (horário de Brasília), com aviso amigável.
- **FR-003**: As listas do portal (próximos, histórico, resumo financeiro do portal) e a janela de
  edição de avaliação MUST usar o horário de Brasília como referência.
- **FR-004**: As janelas atuais MUST ser preservadas: avaliar em até 7 dias após o término; editar em
  até 30 dias.

### Key Entities

- **Evento** — início/término gravados em horário de Brasília; define quando a avaliação abre.
- **Avaliação** — só pode existir para evento terminado.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 0 eventos não terminados aparecem em "Avalie seus eventos".
- **SC-002**: 0 avaliações gravadas antes do término do evento (mesmo por URL direta).
- **SC-003**: Eventos que começam nas próximas 3 horas continuam listados em "Próximos eventos" até a
  hora de início real.

## Assumptions

- "Acabado" = horário de término do evento já passou em Brasília; sem término cadastrado, vale o
  início (regra que o sistema já usa como fallback).
- Carimbos internos de data/hora (aceite de termos, envio/edição de avaliação, reset de senha)
  permanecem como estão — o ajuste é só nas comparações com horários de eventos.
- Sem mudança de banco.
