# Feature Specification: Calendário não trava mais ao abrir

**Feature Branch**: `001-calendario-sem-travar`

**Created**: 2026-05-29

**Status**: Draft

**Input**: User description: "não quero que o calendário trave mais ao abrir"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Abrir o calendário é instantâneo (Priority: P1)

Um usuário (casting, comercial, etc.) abre a tela de agenda para consultar os eventos
do mês. A página aparece imediatamente com os eventos, sem ficar "rodando"/travada
esperando uma atualização externa terminar.

**Why this priority**: É a dor principal relatada. Hoje, abrir certos meses trava a
página por vários segundos porque o carregamento espera uma sincronização com serviço
externo terminar antes de mostrar qualquer coisa. Resolver isso entrega valor imediato
em todas as aberturas de calendário.

**Independent Test**: Abrir a agenda em um mês qualquer (inclusive meses passados ou
"desatualizados") e confirmar que os eventos aparecem rápido, sem espera perceptível.

**Acceptance Scenarios**:

1. **Given** um mês cujos dados não são atualizados há horas, **When** o usuário abre a
   agenda desse mês, **Then** os eventos salvos aparecem imediatamente, sem travar.
2. **Given** o serviço externo de calendário está lento ou indisponível, **When** o
   usuário abre a agenda, **Then** a página ainda carrega normalmente com os dados salvos.
3. **Given** o usuário navega entre meses (anterior/próximo), **When** troca de mês,
   **Then** cada troca é instantânea.

---

### User Story 2 - Saber se os dados estão atualizados (Priority: P2)

Como os dados passam a vir do que está salvo (e não de uma busca ao vivo), o usuário
precisa enxergar há quanto tempo aquele mês foi atualizado pela última vez, para confiar
no que está vendo.

**Why this priority**: Remove o medo de "estar olhando algo desatualizado". Transparência
substitui a sincronização-ao-abrir que causava a lentidão.

**Independent Test**: Abrir a agenda e verificar que há um indicador visível de "última
atualização" (ex.: "atualizado há 4 min" / "há 1 dia" / "nunca atualizado").

**Acceptance Scenarios**:

1. **Given** o mês foi atualizado recentemente, **When** o usuário abre a agenda,
   **Then** vê um indicador como "atualizado há X minutos".
2. **Given** o mês está muito desatualizado, **When** o usuário abre a agenda,
   **Then** o indicador deixa isso evidente (ex.: destaque de "desatualizado há 1 dia").

---

### User Story 3 - Atualizar sob demanda em 1 clique (Priority: P2)

Quando o usuário realmente precisa do dado mais recente na hora (ex.: acabou de criar um
evento no Google Calendar), ele pode forçar a atualização daquele mês com um clique,
aceitando esperar alguns segundos por ser uma ação deliberada.

**Why this priority**: Garante que ninguém fica "preso" a dados antigos. É a válvula de
escape que torna seguro parar de sincronizar automaticamente ao abrir.

**Independent Test**: Clicar em "Atualizar agora" na agenda e confirmar que, ao concluir,
os eventos refletem o estado mais recente da origem e o indicador de frescor zera.

**Acceptance Scenarios**:

1. **Given** um evento foi criado/alterado na origem há instantes, **When** o usuário
   clica em "Atualizar agora", **Then** o evento aparece/atualiza na tela ao concluir.
2. **Given** a atualização manual está em andamento, **When** o usuário aguarda,
   **Then** há feedback visual de que a atualização está acontecendo.

---

### Edge Cases

- **Mês nunca atualizado e sem eventos salvos**: a agenda mostra o estado vazio e indica
  claramente "nunca atualizado", oferecendo a ação de atualizar.
- **Atualização automática em segundo plano atrasada ou falhando**: o usuário percebe pelo
  indicador de frescor e pode forçar a atualização manual.
- **Evento recém-criado na origem**: pode não aparecer até a próxima atualização automática
  (dentro da janela definida) ou até o usuário clicar em "Atualizar agora".
- **Atualização manual falha** (origem indisponível): a página continua mostrando os dados
  salvos e exibe uma mensagem amigável de erro.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Ao abrir qualquer mês ou visão do calendário, o sistema MUST exibir os
  eventos a partir dos dados já armazenados, sem aguardar resposta de serviço externo.
- **FR-002**: O tempo de carregamento da agenda MUST ser consistente, independentemente
  de quão atualizado está o mês ou da disponibilidade do serviço externo.
- **FR-003**: A agenda MUST exibir, de forma visível, há quanto tempo os dados daquele
  mês foram atualizados pela última vez (incluindo o estado "nunca atualizado").
- **FR-004**: Usuários MUST conseguir disparar manualmente, em no máximo 1 clique, a
  atualização imediata do mês exibido.
- **FR-005**: Ao concluir a atualização manual, o sistema MUST refletir na tela o estado
  mais recente da origem e atualizar o indicador de frescor.
- **FR-006**: A atualização automática em segundo plano MUST continuar funcionando (não
  pode regredir), mantendo os dados frescos sem ação do usuário.
- **FR-007**: Quando não há dados salvos para o mês, o sistema MUST deixar claro o estado
  vazio e oferecer a ação de atualizar.
- **FR-008**: A atualização manual MUST tratar falha da origem sem quebrar a página,
  mantendo os dados salvos e exibindo mensagem amigável.

### Key Entities *(include if feature involves data)*

- **Frescor do mês**: informação de quando cada mês foi atualizado pela última vez, usada
  para exibir o indicador e decidir o destaque de "desatualizado". (Já existe no sistema.)

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Abrir o calendário em qualquer mês (inclusive passados e desatualizados)
  carrega em menos de 1 segundo em uso normal.
- **SC-002**: 100% das aberturas de calendário independem de resposta de serviço externo —
  zero travamentos causados por lentidão de rede ao abrir.
- **SC-003**: O usuário identifica em 1 olhada se os dados estão atualizados.
- **SC-004**: O usuário obtém os dados mais recentes sob demanda em no máximo 1 clique.
- **SC-005**: Sem ação do usuário, a defasagem máxima dos dados permanece dentro da janela
  de atualização automática (≤ 10 minutos).

## Assumptions

- A atualização automática em segundo plano (já existente) roda periodicamente e passa a
  ser a fonte primária de frescor dos dados.
- Eventos passados raramente mudam na origem; é aceitável priorizar velocidade de abertura
  sobre frescor em tempo real, desde que exista atualização manual sob demanda.
- O sistema já registra o momento da última atualização de cada mês; esse registro será
  reutilizado para o indicador de frescor.
- É aceitável que um evento recém-criado na origem leve até ~10 minutos para aparecer
  automaticamente, já que o usuário pode forçar a atualização imediata quando necessário.
- A ação "Atualizar agora" pode levar alguns segundos por ser uma operação deliberada.
