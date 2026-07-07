# Feature Specification: Botão "Editar no Google Agenda"

**Feature Branch**: `117-editar-evento-google`

**Created**: 2026-07-07

**Status**: Draft

**Input**: User description: "Faça o botão de editar evento, que leve para a página do evento no Google Calendar. Botão apenas visível para comercial e superadmin."

## Contexto

O sistema deliberadamente não permite editar data, horário e local do evento principal
pelo Manto — essas informações vêm do Google Agenda e a sincronização periódica sempre
sobrescreve o banco local com o que está no Google, sem checar edição local (decisão
consciente registrada em conversa: Google é a fonte da verdade para esses campos). Hoje,
para editar essas informações, o usuário precisa abrir o Google Agenda por fora e procurar
o evento manualmente. Falta um atalho direto da página do evento no Manto para a página
daquele evento específico no Google Agenda.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Ir direto para o evento no Google Agenda (Priority: P1)

Um usuário comercial ou super admin abre a página de um evento no Manto, clica em "Editar no
Google Agenda" e é levado, numa aba nova, direto para aquele evento específico no site do
Google Calendar — sem precisar procurar pela data manualmente.

**Independent Test**: abrir um evento já sincronizado com o Google, clicar no botão, conferir
que abre o Google Calendar já na tela daquele evento (mesmo título/data/horário).

**Acceptance Scenarios**:

1. **Given** um evento com origem no Google Agenda (tem `google_event_id`), **When** o botão
   está disponível, **Then** clicar nele abre, em nova aba, a página daquele evento
   específico no Google Calendar.
2. **Given** um usuário sem papel comercial nem super admin, **When** abre a página do
   evento, **Then** não vê o botão.
3. **Given** um evento recém-criado que ainda não passou por uma sincronização completa
   (link do Google ainda não capturado), **Then** o botão não aparece até o link estar
   disponível — sem quebrar a página nem levar a um link errado.
4. **Given** o usuário não está logado numa conta Google no navegador, **When** abre o link,
   **Then** o próprio Google pede login antes de mostrar o evento (comportamento do Google,
   fora do controle do Manto).

## Requirements *(mandatory)*

- **FR-001**: A página do evento DEVE ter um botão "Editar no Google Agenda" que abre, em
  nova aba, a página daquele evento específico no site do Google Calendar.
- **FR-002**: O botão DEVE ser visível apenas para os papéis COMERCIAL e SUPERADMIN.
- **FR-003**: O botão só PODE aparecer quando o sistema já tem o link direto daquele evento
  (capturado da sincronização com o Google); sem o link, o botão fica oculto.
- **FR-004**: O acesso de edição de fato no Google (login e permissão na agenda) é
  responsabilidade do Google e da configuração de compartilhamento da agenda — fora do
  escopo deste sistema.
- **FR-005**: A mudança NÃO PODE alterar o comportamento atual de sincronização (Google
  continua sendo a fonte da verdade; nenhuma escrita nova do Manto para o Google).

### Key Entities

- **Evento (CalendarEvent)**: ganha o link direto da página do evento no Google Calendar,
  capturado junto com os demais dados na sincronização já existente.

## Success Criteria *(mandatory)*

- **SC-001**: Usuário comercial/super admin chega à edição do evento no Google em 1 clique
  a partir da página do evento no Manto.
- **SC-002**: 100% dos eventos sincronizados após esta feature exibem o botão; eventos ainda
  não sincronizados não mostram um link quebrado.
- **SC-003**: Nenhum outro papel enxerga ou aciona o botão.

## Assumptions

- O link fica disponível progressivamente: eventos passam a exibir o botão a partir da
  primeira sincronização depois desta mudança (automática, a cada poucos minutos, ou via
  botão "Sincronizar" já existente na página do evento) — sem precisar de uma migração de
  dados retroativa forçada.
- "Editar" aqui significa apenas levar o usuário até a tela do evento no Google — a
  permissão de fato para editar lá depende do compartilhamento da agenda no Google, não do
  Manto.
