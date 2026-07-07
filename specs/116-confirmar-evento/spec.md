# Feature Specification: Marcar Evento como Confirmado

**Feature Branch**: `116-confirmar-evento`

**Created**: 2026-07-07

**Status**: Draft

**Input**: User description: "Preciso de um simples botão em cada evento que eu marco como confirmado o evento. Pode ficar ao lado do botão de confirmar."

## Contexto

A página do evento já tem o botão "✅ Confirmar dados do evento" (feature 083), que só
**copia** uma mensagem de WhatsApp para o comercial enviar ao cliente — não guarda nada no
sistema. Falta um jeito de **registrar** que o evento foi de fato confirmado (cliente
respondeu, comparecimento certo), para consultar depois quem confirmou e quando.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Marcar o evento como confirmado (Priority: P1)

O comercial (ou super admin), depois de confirmar com o cliente, clica num botão simples ao
lado de "Confirmar dados do evento" e o evento passa a mostrar que está confirmado — com
quem confirmou e quando.

**Independent Test**: abrir um evento não confirmado, clicar no botão, ver o status mudar
para confirmado com nome/data; recarregar a página e conferir que persiste.

**Acceptance Scenarios**:

1. **Given** um evento ainda não confirmado, **When** o usuário clica no botão, **Then** o
   evento passa a exibir "Confirmado" com o nome de quem confirmou e a data/hora.
2. **Given** um evento confirmado, **When** a página é recarregada ou reaberta depois,
   **Then** o status de confirmado continua aparecendo (persiste).
3. **Given** um evento confirmado por engano, **When** o usuário aciona a opção de desfazer,
   **Then** o evento volta ao estado "não confirmado".
4. **Given** um usuário sem papel comercial/super admin, **When** abre a página do evento,
   **Then** não vê o botão de marcar confirmado.

## Requirements *(mandatory)*

- **FR-001**: O sistema DEVE permitir marcar um evento como confirmado através de um botão
  na página do evento, posicionado ao lado do botão "Confirmar dados do evento".
- **FR-002**: O sistema DEVE registrar quem confirmou e quando, exibindo essa informação na
  página do evento.
- **FR-003**: O sistema DEVE permitir desfazer a confirmação (marcar como não confirmado de
  novo), para corrigir cliques por engano.
- **FR-004**: Ação restrita aos papéis COMERCIAL e SUPERADMIN — mesmo grupo que já vê o
  botão de confirmar dados hoje.
- **FR-005**: A ação DEVE ficar registrada no histórico de log do evento (auditoria).

### Key Entities

- **Evento**: ganha um estado de confirmação (confirmado ou não), com quem confirmou e
  quando — independente da mensagem de WhatsApp copiada pelo botão já existente.

## Success Criteria *(mandatory)*

- **SC-001**: Marcar um evento como confirmado leva 1 clique.
- **SC-002**: 100% dos eventos confirmados mostram corretamente quem confirmou e quando,
  mesmo após reabrir a página.
- **SC-003**: Usuários fora do papel comercial/super admin não veem nem acionam o botão.

## Assumptions

- Escopo é a página do evento (onde já fica o botão de confirmar dados) — não inclui um
  indicador na lista/agenda, que fica para uma próxima iteração se for pedido.
- "Confirmado" é um estado simples (sim/não com autor e data) — não exige motivo nem
  aprovação de terceiros.
