# Feature Specification: Presença do técnico de som é tarefa do ensaio (não do casting)

**Feature Branch**: `047-presenca-ensaio`

**Created**: 2026-06-15

**Status**: Draft

**Input**: User description: "A presença deve ser preenchida pelo setor de ensaio e gerar a task
para eles, não para o casting."

## Contexto

Em eventos SHOW, o sistema cria automaticamente a vaga **"Técnico de Som (Presença)"** — quem vai
presencialmente ao evento. Quem define essa pessoa é a **equipe de ensaio** (a tela do evento já
restringe esse campo ao ensaio). Mas, como a vaga é uma "função sem pessoa atribuída", ela cai na
lista de **tarefas pendentes do casting** na home. Resultado: o casting vê uma cobrança que não é
dele, e o ensaio não vê a tarefa que é dele.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Presença pendente aparece para o ensaio (Priority: P1)

Um show sem técnico de presença definido aparece como tarefa **do setor de ensaio** na home.

**Acceptance Scenarios**:

1. **Given** um show futuro sem técnico de presença, **When** alguém do ensaio abre a home,
   **Then** vê "Falta definir presença" para esse show, com link para o evento.
2. **Given** o técnico de presença definido, **Then** a tarefa some da lista do ensaio.

---

### User Story 2 - Presença NÃO é tarefa do casting (Priority: P1)

A vaga de presença não aparece mais entre as tarefas pendentes do casting, nem conta nas
estatísticas de casting.

**Acceptance Scenarios**:

1. **Given** um show com presença em aberto, **When** o casting abre a home, **Then** a vaga de
   presença NÃO aparece na lista do casting.
2. **Given** as estatísticas de casting (X/Y), **Then** elas não contam a vaga de presença.

---

### Edge Cases

- O técnico de som "PIX" (pré-atribuído ao Nivaldo) continua como está — não é tarefa de ninguém.
- Show já realizado não gera tarefa de presença (a presença só importa para shows futuros).
- Definir a presença continua sendo possível apenas para a equipe de ensaio (e super admin), como
  já é hoje.
- A vaga de presença continua aparecendo na tela do evento, na seção do ensaio.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: A vaga "Técnico de Som (Presença)" sem pessoa MUST gerar tarefa para o setor de
  ensaio (não para o casting).
- **FR-002**: A vaga de presença MUST ser excluída das tarefas pendentes do casting e das
  estatísticas de casting (total/concluídas).
- **FR-003**: A tarefa de presença do ensaio MUST listar apenas shows futuros sem presença
  definida, com link para o evento.
- **FR-004**: Definir a presença MUST permanecer restrito ao setor de ensaio (e super admin), como
  já é hoje.

### Key Entities

- **Vaga de presença** — função "Técnico de Som (Presença)" do evento, sem pessoa = pendência do
  ensaio.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 0 vagas de presença aparecendo nas tarefas do casting.
- **SC-002**: 100% dos shows futuros sem presença aparecem na lista do ensaio.
- **SC-003**: Estatística de casting deixa de contabilizar a vaga de presença.

## Assumptions

- A função é identificada pelo nome "Técnico de Som (Presença)" (padrão já criado nos shows).
- "Futuro" para a tarefa de presença = show ainda não aconteceu (horário de Brasília).
- Sem mudança de banco.
