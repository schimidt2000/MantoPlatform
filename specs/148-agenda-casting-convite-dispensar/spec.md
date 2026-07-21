# Feature Specification: convite / dispensar / restaurar / figurino (148)

**Feature Branch**: `148-agenda-casting-convite-dispensar`

**Created**: 2026-07-21

**Status**: Draft

**Input**: US3 da escrita de casting (spec 146). As três primeiras fatias de escrita já foram
mergeadas: US1 = escalar talento (146), US2 = adicionar/remover cargo (147). Esta fecha a
paridade de casting migrando as ações menores sobre um cargo: **reenviar convite**,
**dispensar** um cargo obsoleto e **restaurá-lo**, e **marcar figurino** como separado.

## Contexto

Continuação direta de 146/147, mesmo padrão de escrita: **núcleo único em
`app/calendar/casting_ops.py`** (parâmetros explícitos, sem `request.form`/`flash`/
`current_user`), reusado por dois adaptadores finos — o handler Jinja e o endpoint JSON. Nenhuma
lógica reimplementada (Princípio I). São quatro toggles simples, mas cada um tem RBAC e efeito
próprios que a paridade precisa preservar:

- **convite** (`send_invite`): marca `invite_status=pending`, registra log e **envia e-mail de
  convite** ao talento. RBAC = mesmo gate de edição do evento (`_CAN_EDIT_EVENT`, como o Jinja).
- **figurino** (`figurino_done`): marca `figurino_done_at`, registra log. RBAC = **mesmo gate de
  edição do evento** (`_CAN_EDIT_EVENT` = casting/figurino/comercial/financeiro/superadmin): no
  Jinja o toggle é despachado pelo POST de `/events/<id>`, que já gateia por quem pode editar o
  evento — não só Figurino. A UI React surfaceia o botão ao público natural (Figurino/superadmin),
  subconjunto do permitido — não regride nada.
- **dispensar** (`dismiss`): marca `dismissed_at`/`dismissed_by` num cargo **sem talento**, para
  ele parar de contar como tarefa pendente **sem excluir** — assim o sync do Google nunca o
  recria (feature 108). RBAC = **só superadmin**.
- **restaurar** (`restore`): limpa `dismissed_at`, o cargo volta a contar como pendente. RBAC =
  **só superadmin**.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Reenviar convite (Priority: P1)

Do detalhe do evento em React, o casting reenvia o convite de um cargo já com talento (ex.: o
talento não respondeu). O estado volta a `pending`, é registrado no log e o e-mail é enviado —
exatamente como o botão "enviar convite" do Jinja.

**Independent Test**: reenviar o convite de um cargo com talento pela tela React e confirmar que
`invite_status` fica `pending`, há um `EventLog` idêntico ao do Jinja e um único e-mail é
disparado — a tela atualiza sem reload.

**Acceptance Scenarios**:

1. **Given** um cargo com talento, **When** o casting reenvia o convite, **Then** `invite_status`
   fica `pending`, o log fica igual ao do Jinja e um único convite é enviado.
2. **Given** um cargo sem talento, **When** se tenta reenviar, **Then** nada acontece (igual ao
   Jinja, que só reenvia se há `talent_id`).
3. **Given** o botão, **When** clicado, **Then** dá feedback imediato e um clique a mais não gera
   convite/registro duplicado (Princípio V).

---

### User Story 2 - Dispensar e restaurar cargo (Priority: P2)

O superadmin dispensa um cargo obsoleto (sem talento) para ele parar de aparecer como tarefa
pendente, e pode restaurá-lo depois. A regra da feature 108 é preservada: dispensado ≠ excluído,
então o sync do Google nunca o recria enquanto dispensado.

**Acceptance Scenarios**:

1. **Given** um cargo sem talento, **When** o superadmin o dispensa, **Then** `dismissed_at`/
   `dismissed_by` ficam preenchidos, há log, e o cargo deixa de contar como pendente — igual ao
   Jinja.
2. **Given** um cargo **com talento**, **When** se tenta dispensar, **Then** é bloqueado (só
   cargos sem talento podem ser dispensados) — igual ao Jinja.
3. **Given** um cargo dispensado, **When** o superadmin o restaura, **Then** `dismissed_at` volta
   a `None` e ele conta como pendente de novo.
4. **Given** um não-superadmin, **When** tenta dispensar/restaurar, **Then** recebe 403.

---

### User Story 3 - Marcar figurino separado (Priority: P3)

O Figurino (ou superadmin) marca o figurino de um cargo como separado. Marca `figurino_done_at`,
registra log — igual ao toggle atual do Jinja. RBAC própria de Figurino, não de casting.

**Acceptance Scenarios**:

1. **Given** um cargo com talento, **When** o Figurino marca o figurino, **Then** `figurino_done`
   passa a verdadeiro, há log, e a tela atualiza sem reload.
2. **Given** um usuário sem permissão de editar o evento (ex.: só Ensaio/Vendas), **When** tenta
   marcar, **Then** recebe 403 — igual ao POST Jinja de `/events/<id>`.

---

### Edge Cases

- **E-mail do convite**: reenviar dispara **um** e-mail real de convite. A migração mantém
  exatamente o mesmo comportamento (nem duplicado, nem omitido). A verificação mocka o envio.
- **Sync × dispensa**: um cargo dispensado não é recriado pelo sync (feature 108). Dispensar/
  restaurar pela API preserva isso (só mexe em `dismissed_at`, mesma coluna do Jinja).
- **Clique duplo**: reenviar convite / marcar figurino são idempotentes do ponto de vista do
  usuário — um clique a mais não gera segundo registro/e-mail relevante (Princípio V).
- **Coexistência**: Jinja (`app.`) e React (`beta`) gravam no mesmo banco; um só caminho de
  lógica (núcleo compartilhado) evita divergência.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Cada ação (reenviar convite, dispensar, restaurar, marcar figurino) MUST ter um
  endpoint JSON dedicado que executa a MESMA lógica já existente, reusando o núcleo compartilhado
  — não reimplementando (Princípio I).
- **FR-002**: Cada ação MUST produzir exatamente o mesmo estado no banco que o fluxo Jinja
  equivalente (mesmos campos em `event_roles`, mesmo `EventLog`), verificado contra `manto_local`.
- **FR-003**: A RBAC de cada ação MUST ser idêntica à atual, aplicada no servidor: convite e
  figurino = gate de edição do evento (`_CAN_EDIT_EVENT`, como o POST Jinja que os despacha);
  dispensar/restaurar = só superadmin (e dispensar só cargo sem talento).
- **FR-004**: Nenhum botão MUST ficar "morto" ao clique; toda ação dá feedback imediato e um
  clique a mais NUNCA gera registro/convite duplicado (Princípio V).
- **FR-005**: Ao concluir, a API MUST devolver o evento atualizado no formato de leitura da 145
  (`serialize_event_detail`), respeitando o RBAC de serialização, para a tela re-renderizar sem
  reload. O serializer MUST expor o estado de dispensa do cargo (`dismissed`) para a tela decidir
  entre dispensar/restaurar.
- **FR-006**: O e-mail de convite MUST continuar sendo enviado exatamente como hoje — sem
  duplicar nem omitir.
- **FR-007**: As ações no `event_detail.html` Jinja MUST continuar funcionando inalteradas
  durante toda a transição (coexistência, mesmo banco).

### Key Entities

Sem entidade nova. Escrita sobre `EventRole` (`invite_status`, `figurino_done_at`,
`dismissed_at`/`dismissed_by`) e `EventLog` já existentes. Nenhuma mudança de schema.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Para cada ação, o estado do banco após executá-la pela API é indistinguível do
  estado após executá-la pelo fluxo Jinja, para os mesmos dados — verificado campo a campo contra
  `manto_local`.
- **SC-002**: Reenviar convite envia exatamente um e-mail, como hoje — zero duplicado, zero
  perdido.
- **SC-003**: Nenhuma dessas ações no app Jinja regride durante a migração.
- **SC-004**: Um clique repetido nunca gera um segundo registro/e-mail relevante.

## Assumptions

- **Reuso via extração**: o núcleo de cada ação é extraído para `casting_ops` recebendo
  parâmetros explícitos; o handler Jinja e o endpoint JSON viram adaptadores finos. UMA
  implementação da regra.
- **Endpoints REST por ação**: `POST /api/roles/<id>/invite`, `POST /api/roles/<id>/dismiss`,
  `POST /api/roles/<id>/restore`, `POST /api/roles/<id>/figurino-done`. Nomes finais no plano.
- `figurino_done` é tecnicamente uma ação de Figurino, mas hoje é despachada pelo POST do evento
  e herda o gate `_CAN_EDIT_EVENT` — a paridade preserva esse gate (não o restringe a Figurino).
- A verificação isola/mocka o envio de e-mail (não dispara e-mail real contra `manto_local`).
- Fora de escopo: tudo o mais do evento (venda/pagamentos, contrato, logística, confirmação,
  agrupamento, criar/excluir evento, ensaio, sync manual) — fatias seguintes.
- Fecha a paridade de casting; com ela, o bloco de elenco do evento em React cobre todas as ações
  de casting/figurino do Jinja.
