# Feature Specification: Atualizar "Já Trabalhou com a Manto" Automaticamente

**Feature Branch**: `115-atualizar-ja-trabalhou`

**Created**: 2026-07-07

**Status**: Draft

**Input**: User description: "Na página do banco de talentos tem o filtro automático se a pessoa já trabalhou na Manto. O que eu quero é que se uma pessoa realiza um evento, atualizamos essa condição e ela passa a ser filtrada da forma correta."

## Contexto

O banco de talentos tem o filtro "Já trabalhou com a Manto?", ligado por padrão. Hoje ele
depende de um campo respondido pela própria pessoa no cadastro (ou editado manualmente por
Casting/superadmin) — `worked_before`. Se alguém se cadastra antes de nunca ter trabalhado
(responde "Não" ou deixa em branco) e depois é escalada e realiza um evento de verdade, esse
campo nunca é atualizado sozinho: a pessoa continua não aparecendo no filtro padrão mesmo já
tendo trabalhado com a Manto.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Talento passa a ser filtrado como "já trabalhou" após realizar um evento (Priority: P1)

Uma pessoa cadastrada como "ainda não trabalhou" é escalada para um personagem, o evento
acontece, e a partir daí ela aparece corretamente no filtro padrão "Já trabalhou com a
Manto?" do banco de talentos, sem que ninguém precise editar a ficha dela na mão.

**Why this priority**: é o pedido central — hoje o filtro mente sobre quem já trabalhou de
verdade, e a correção é sempre manual.

**Independent Test**: escalar um talento marcado como "não trabalhou" para um evento com
data no passado (ou aguardar o evento passar), confirmar que a ficha passa a mostrar "Sim"
e que ele aparece na lista filtrada por "já trabalhou".

**Acceptance Scenarios**:

1. **Given** um talento marcado "Não"/sem resposta em "já trabalhou", **When** ele é
   escalado (com talento atribuído) para um evento que já aconteceu, **Then** a ficha dele
   passa a mostrar "Sim" automaticamente.
2. **Given** um talento já marcado "Sim", **When** ele realiza mais eventos, **Then** nada
   muda (a condição não regride nem duplica esforço).
3. **Given** um talento escalado para um evento que ainda **não** aconteceu, **Then** a
   condição não muda até o evento passar.
4. **Given** um talento cujo convite para o evento foi **recusado**, **Then** esse evento
   não conta como "trabalhou" para ele.
5. **Given** um talento escalado apenas em ensaios (evento do tipo Ensaio, não um show de
   verdade), **Then** isso sozinho não conta como "já trabalhou".
6. **Given** a atualização automática, **When** o super admin ou Casting edita manualmente o
   campo na ficha do talento, **Then** a edição manual continua funcionando como hoje (a
   automação só liga o "Sim" — nunca desliga por conta própria nem trava o campo).

## Requirements *(mandatory)*

- **FR-001**: O sistema DEVE marcar automaticamente "já trabalhou com a Manto" para todo
  talento que tenha sido escalado (talento atribuído a um cargo) em pelo menos um evento
  real (não ensaio) cuja data já passou, e cujo convite não tenha sido recusado.
- **FR-002**: A atualização automática NUNCA PODE mudar a condição de "Sim" para "Não" —
  só liga, nunca desliga (evita apagar informação histórica ou uma correção manual).
- **FR-003**: A verificação e atualização DEVEM rodar automaticamente em segundo plano, sem
  exigir nenhuma ação do usuário nem botão para "recalcular".
- **FR-004**: A atualização DEVE valer tanto para eventos que já aconteceram há tempo quanto
  para os que acabaram de terminar — a defasagem entre o evento acabar e a ficha refletir
  isso deve ser pequena (minutos, não dias).
- **FR-005**: A edição manual do campo (Casting/superadmin, na ficha do talento) continua
  disponível e não é substituída pela automação.
- **FR-006**: O filtro "Já trabalhou com a Manto?" da lista de talentos continua funcionando
  exatamente como hoje (lê o mesmo campo) — a mudança é só garantir que o campo reflita a
  realidade.

### Key Entities

- **Talento**: campo existente "já trabalhou com a Manto" passa a ser mantido também pelo
  sistema, além do autorrelato no cadastro e da edição manual.
- **Cargo do evento**: a atribuição de um talento a um cargo, num evento real e já
  realizado, com convite não recusado, é o que dispara a atualização.

## Success Criteria *(mandatory)*

- **SC-001**: 100% dos talentos escalados e com evento real já realizado (convite não
  recusado) aparecem como "já trabalhou" em até alguns minutos após o evento terminar.
- **SC-002**: Nenhum talento tem sua condição revertida de "Sim" para "Não" pela automação.
- **SC-003**: Ensaios e convites recusados não disparam a marcação sozinhos.

## Assumptions

- "Realizar um evento" = ter talento atribuído a um cargo (personagem ou de apoio) num
  evento cujo tipo não é Ensaio, com convite não recusado, e cuja data/hora já passou.
- A automação roda dentro do ciclo já existente de sincronização periódica da agenda (a
  cada poucos minutos) — sem exigir uma tela ou botão novo.
- Convite sem registro (`invite_status` vazio) conta como trabalhado, já que nem todo fluxo
  antigo passa por convite explícito — só o status "recusado" é motivo para não contar.
