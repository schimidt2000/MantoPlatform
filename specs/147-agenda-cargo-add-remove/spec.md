# Feature Specification: Agenda/Eventos — adicionar/remover cargo em React

**Feature Branch**: `147-agenda-cargo-add-remove`

**Created**: 2026-07-21

**Status**: Draft

**Input**: US2 da escrita de casting (segue a feature 146): migrar as ações **adicionar cargo**
(`add_role`) e **remover cargo** (`delete_role`) do POST de `/events/<id>` para endpoints REST,
reusando o padrão de extração de handler estabelecido na 146. Coexistência com o Jinja; mesmo
banco; verificação por paridade.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Adicionar um cargo ao evento (Priority: P1) 🎯 MVP

Do detalhe do evento em React, o casting adiciona um cargo novo (um personagem/função), com ou
sem talento já escalado.

**Independent Test**: adicionar um cargo pela tela React cria a mesma linha em `event_roles`
que o fluxo Jinja (nome, tipo, e — se informado — talento + convite), com o mesmo `EventLog`.

**Acceptance Scenarios**:

1. **Given** um evento, **When** o casting adiciona um cargo só com o nome do personagem,
   **Then** cria a linha (sem talento) igual ao Jinja e a tela atualiza sem reload.
2. **Given** o mesmo, **When** adiciona já com talento + cachê, **Then** cria com
   `invite_status=pending`, dispara um convite (um só), igual ao Jinja.
3. **Given** o botão de adicionar, **When** clicado, **Then** dá feedback imediato e um clique
   a mais não cria cargo duplicado (Princípio V).

### User Story 2 - Remover um cargo (Priority: P2)

Remover um cargo do evento. Cargo com convite `accepted` só o superadmin remove (regra atual).

**Acceptance Scenarios**:

1. **Given** um cargo sem convite aceito, **When** o casting remove, **Then** a linha some e um
   `EventLog` de remoção é criado — igual ao Jinja.
2. **Given** um cargo com convite `accepted`, **When** um não-superadmin tenta remover, **Then**
   é bloqueado (mesma regra de hoje).

### Edge Cases

- **Bug latente corrigido**: o handler Jinja `_handle_delete_role` faz `filter_by(id=role_id)`
  com `role_id` string — quebra em `manto_local` (psycopg3), passa em produção (psycopg2). A
  extração converte para `int` explicitamente (regra permanente do projeto).
- **Nome vazio**: adicionar sem nome de personagem é rejeitado (como hoje — o handler ignora).
- **Envio duplicado**: um clique a mais em adicionar não cria 2 cargos (feedback de pending).
- **Coexistência**: as ações Jinja de add/remove seguem funcionando; ambas gravam no mesmo banco.

## Requirements *(mandatory)*

- **FR-001**: Adicionar e remover cargo MUST ter endpoints dedicados que reusam o núcleo
  extraído dos handlers atuais (Princípio I) — sem reimplementar.
- **FR-002**: Cada ação MUST produzir o mesmo estado no banco que o fluxo Jinja (linhas em
  `event_roles` + `EventLog`), verificado contra `manto_local`.
- **FR-003**: A RBAC MUST ser idêntica à atual: adicionar segue o gate de edição do evento
  (`_CAN_EDIT_EVENT`); remover exige CASTING/SUPERADMIN, e cargo com convite aceito só
  superadmin remove.
- **FR-004**: Nenhum botão fica morto; um clique a mais não cria cargo duplicado (Princípio V).
- **FR-005**: Ao concluir, a API MUST devolver o evento atualizado (`serialize_event_detail`)
  para a tela re-renderizar sem reload.
- **FR-006**: As ações de add/remove no Jinja MUST continuar funcionando inalteradas
  (coexistência).
- **FR-007**: O parsing de cachê no adicionar MUST usar a fonte única `parse_brl` (Princípio
  VII), harmonizando com o resto (o handler antigo usava `int()` — passa a aceitar decimais
  pt-BR, mudança estritamente mais permissiva).

## Success Criteria *(mandatory)*

- **SC-001**: Adicionar/remover pela API deixa `event_roles`+`EventLog` no mesmo estado que
  pelo Jinja, para a mesma entrada.
- **SC-002**: Remoção de cargo com convite aceito por não-superadmin é bloqueada em ambos os
  caminhos.
- **SC-003**: Nenhuma ação de add/remove no Jinja regride.
- **SC-004**: Clique repetido em adicionar nunca cria um segundo cargo.

## Assumptions

- Segue o padrão da feature 146: núcleo em `app/calendar/casting_ops.py`, handlers Jinja viram
  wrappers finos, endpoints em `app/api/agenda_write.py`, verificação por paridade com e-mail
  mockado.
- `figurino_done`, convite avulso e dispensar/restaurar ficam para a fatia seguinte (US3).
