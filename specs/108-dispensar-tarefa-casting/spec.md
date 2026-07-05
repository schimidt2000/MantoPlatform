# Feature Specification: Dispensar Tarefa de Casting Pendente

**Feature Branch**: `108-dispensar-tarefa-casting`

**Created**: 2026-07-03

**Status**: Draft

**Input**: User description: "As tarefas pendentes podem ser marcadas por um super admin para serem removidas. Só para entender o contexto: Esse evento já ocorreu e alguns personagens ou não foram necessários ou não existem de verdade. Se eu excluo na página do evento, volta com o sync do google agenda. Então quero que esses cargos possam ser removidos das tarefas pendentes por um super admin."

## Contexto

A lista "Tarefas pendentes" da home mostra, na seção Casting, todo `EventRole` sem talento
atribuído para eventos futuros ao corte de liberação. Alguns desses cargos, meses depois,
ficam obsoletos: o evento já aconteceu (a data de corte de tarefas não avança sozinha) ou o
personagem listado no título do Google Agenda nunca existiu de verdade / não foi necessário.

Hoje a única ação disponível é excluir o cargo na página do evento — mas a sincronização
periódica com o Google Agenda relê o título do evento, vê o nome do personagem ainda lá e
recria o cargo, trazendo a tarefa pendente de volta. Não há como "resolver" esses casos sem
que voltem.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Super admin dispensa uma tarefa de casting obsoleta (Priority: P1)

Um super admin abre "Tarefas pendentes" na home e vê um cargo de casting de um evento que já
passou (ou que nunca precisou de talento). Ele dispensa esse cargo diretamente na lista. O
cargo some da lista de pendências e para de contar nos números de "pendentes"/"total" do
setor — sem precisar abrir a página do evento. Na próxima sincronização com o Google Agenda,
o cargo dispensado **não volta** a aparecer como pendente, mesmo que o nome do personagem
continue no título do evento.

**Why this priority**: é o pedido central — resolve o incômodo relatado (tarefa fantasma que
sempre volta) sem exigir mudança na agenda do Google nem no fluxo de sincronização existente.

**Independent Test**: como super admin, dispensar um cargo de casting pendente na lista da
home; confirmar que ele some da lista e dos contadores; rodar a sincronização do evento e
confirmar que o cargo continua dispensado (não reaparece como pendente).

**Acceptance Scenarios**:

1. **Given** um cargo de casting pendente (sem talento) listado na home, **When** o super
   admin escolhe dispensá-lo, **Then** o sistema pede confirmação antes de agir.
2. **Given** a confirmação, **When** o cargo é dispensado, **Then** ele desaparece
   imediatamente da lista de "Tarefas pendentes" e os contadores do setor (pendentes e
   total/feito) refletem a mudança.
3. **Given** um cargo dispensado, **When** a sincronização com o Google Agenda roda de novo
   (o nome do personagem continua no título do evento), **Then** o cargo permanece dispensado
   e não volta a aparecer como pendente.
4. **Given** um usuário que não é super admin, **When** olha a lista de tarefas pendentes,
   **Then** não tem a opção de dispensar nenhum cargo.

---

### User Story 2 - Super admin reverte uma dispensa feita por engano (Priority: P2)

O super admin percebe que dispensou um cargo por engano (ou o evento foi remarcado e o
personagem passou a ser necessário de novo). Ele encontra os cargos dispensados daquele setor
e restaura um deles, que volta a aparecer como pendente normalmente.

**Why this priority**: evita que a dispensa vire uma ação sem volta que gera insegurança para
usar a feature — mas o valor central (US1) já é entregável sem ela.

**Independent Test**: dispensar um cargo, localizar a lista de dispensados, restaurá-lo, e
confirmar que ele volta a aparecer em "Tarefas pendentes" com os contadores atualizados.

**Acceptance Scenarios**:

1. **Given** um ou mais cargos dispensados no setor de Casting, **When** o super admin abre a
   lista de dispensados, **Then** vê cada cargo com o evento, quem dispensou e quando.
2. **Given** um cargo na lista de dispensados, **When** o super admin escolhe restaurá-lo,
   **Then** ele volta a contar como pendente na lista principal de tarefas.

---

### Edge Cases

- Dispensar um cargo que, entre a abertura da página e o clique, já foi preenchido por outro
  usuário (recebeu talento): a ação não deve fazer sentido nesse estado — cargo com talento
  não é mais uma tarefa pendente de casting.
- Evento excluído depois que um de seus cargos foi dispensado: a exclusão do evento remove
  também os cargos associados (comportamento já existente) — nada de especial a preservar.
- Cargo dispensado cujo personagem foi removido do título do evento numa edição futura: a
  sincronização já apaga cargos cujo personagem some do título (comportamento existente);
  isso vale igualmente para cargos dispensados.
- Clique duplo no botão de dispensar: não pode gerar erro nem dispensar duas vezes de forma
  incoerente (idempotente).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O sistema DEVE permitir que um usuário com papel de super admin dispense um
  cargo de casting pendente (sem talento atribuído) diretamente na lista de tarefas
  pendentes.
- **FR-002**: Dispensar um cargo DEVE exigir confirmação explícita antes de efetivar (ação
  não é imediatamente destrutiva de dados, mas muda o que a equipe vê como pendente).
- **FR-003**: Um cargo dispensado NÃO PODE aparecer na lista de tarefas pendentes de casting
  nem ser contado nos números de pendentes/total do setor.
- **FR-004**: A sincronização periódica com o Google Agenda NÃO PODE reverter a dispensa: um
  cargo dispensado permanece dispensado mesmo que o personagem continue no título do evento
  em sincronizações futuras.
- **FR-005**: O sistema DEVE registrar quem dispensou o cargo e quando, para consulta
  posterior.
- **FR-006**: Usuários sem papel de super admin NÃO PODEM ver a opção de dispensar nem
  acionar a ação diretamente.
- **FR-007**: O super admin DEVE conseguir ver os cargos dispensados de um evento/setor e
  reverter (restaurar) uma dispensa, fazendo o cargo voltar a contar como pendente.
- **FR-008**: A ação de dispensar/restaurar NÃO PODE alterar o cargo em si além do estado de
  dispensa (nome do personagem, evento e demais dados do cargo permanecem intactos).
- **FR-009**: Dispensar um cargo que já tenha talento atribuído (não é mais uma tarefa
  pendente) NÃO É uma operação válida desta feature — a ação só se aplica a cargos ainda sem
  talento.

### Key Entities

- **Cargo do evento (EventRole)**: ganha um estado de "dispensado" (com registro de quem e
  quando), além dos atributos já existentes (evento, nome do personagem, talento atribuído).
  Um cargo dispensado continua existindo no sistema — apenas para de contar como tarefa
  pendente de casting — e pode ser revertido.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Um super admin consegue dispensar um cargo de casting obsoleto em até 2 cliques
  a partir da lista de tarefas pendentes (sem precisar abrir a página do evento).
- **SC-002**: 100% dos cargos dispensados somem da lista de pendentes e dos contadores
  imediatamente após a ação.
- **SC-003**: Após uma sincronização do evento cujo cargo foi dispensado, o cargo continua
  fora da lista de pendentes em 100% dos casos testados.
- **SC-004**: Uma dispensa feita por engano é revertida em até 2 cliques, sem perda de nenhum
  outro dado do cargo.
- **SC-005**: Nenhum usuário sem papel de super admin consegue localizar ou acionar a ação de
  dispensar em nenhuma tela do sistema.

## Assumptions

- "Super admin" = papel `SUPERADMIN` já existente no sistema (RBAC atual).
- Escopo desta feature é a seção de Casting da lista de tarefas pendentes (cargos sem
  talento), que foi o caso relatado. Outras seções (figurino, ensaio, presença) não são
  tocadas nesta feature.
- Dispensar é reversível (US2) — não é uma exclusão permanente; o cargo e seu histórico
  continuam no banco.
- Não há necessidade de capturar um motivo/comentário obrigatório ao dispensar — quem e
  quando já bastam para o registro de auditoria pedido.
