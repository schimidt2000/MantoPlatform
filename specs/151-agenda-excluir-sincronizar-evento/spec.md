# Feature Specification: excluir e sincronizar evento em React (151)

**Feature Branch**: `151-agenda-excluir-sincronizar-evento`

**Created**: 2026-07-21

**Status**: Draft

**Input**: Continuação da escrita da agenda (migração 144, US2). Casting (146-148), confirmar/
logística (149) e observações (150) já migrados. Esta fatia migra as duas **ações de nível-evento
sem upload** que ainda faltam em React: **excluir o evento** (`POST /events/<id>/delete`) e
**sincronizar um evento com o Google Calendar** (`POST /events/<id>/sync`). Fora de escopo: criar
evento (form grande, fatia própria), ações de upload (contrato/pagamento/reembolso/imagem de
observação — adiadas) e `assign_tech_presence`/rotas de ENSAIO (React não renderiza o painel de
ensaio).

## Contexto

Mesmo padrão strangler-fig de 146-150. Diferença: os núcleos de exclusão e sincronização dependem
de helpers pesados que vivem em `app/calendar/routes.py` (`_delete_event` → Google Calendar,
`_log_sync`, `fetch_single_event`, `sync_events`). Mover esses helpers para um módulo `ops` inverteria
a direção de dependência da constituição (`routes → ops`). Por isso o **núcleo compartilhado destas
duas ações fica como função de módulo em `routes.py`** (não em um `ops` novo), reusado pelo wrapper
Jinja e pelo endpoint JSON — a API já importa de `routes.py` para gates (ex.: `_CAN_EDIT_EVENT`),
então `api → routes` é a direção já existente. Uma só implementação da regra (Princípio I), sem
ciclo de import.

- **excluir** (`delete_calendar_event`): remove o evento do banco e do Google. RBAC =
  **`_CAN_DELETE` = Comercial ou Superadmin**. Guarda: se o evento é **líder de grupo**
  (`is_group_leader`), a exclusão é **recusada** (é preciso desagrupar os satélites antes). Registra
  um log de sincronização (`manual_deleted`). Falha do Google não trava a exclusão local.
- **sincronizar** (`sync_single_event`): rebusca o evento no Google Calendar e reaplica no banco.
  RBAC = **qualquer autenticado** (`@login_required`, sem gate de papel). Erros previstos: evento
  **sem `google_event_id`** e evento **não encontrado** no Google.

Hoje o React (145) mostra o detalhe do evento mas **não** oferece excluir nem sincronizar. Esta
fatia adiciona um botão **Sincronizar com Google** (qualquer autenticado) e um botão **Excluir
evento** (só `can_delete`), ambos com feedback e confirmação para o destrutivo.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Excluir o evento (Priority: P1)

Do detalhe do evento em React, o Comercial (ou superadmin) exclui o evento; ele some do banco e do
Google, e a tela volta para a agenda. Um evento líder de grupo não pode ser excluído sem desagrupar
antes.

**Independent Test**: excluir um evento não-agrupado pela tela React e conferir que a linha some do
banco (mesmo efeito do POST Jinja), que há o log `manual_deleted`, e que a tela navega para a agenda;
tentar excluir um líder de grupo e conferir que é recusado (nada muda), igual ao Jinja.

**Acceptance Scenarios**:

1. **Given** um evento não-agrupado, **When** o Comercial confirma a exclusão, **Then** a linha é
   removida do banco (e do Google), há log `manual_deleted` e a tela volta à agenda — igual ao Jinja.
2. **Given** um evento **líder de grupo**, **When** o Comercial tenta excluir, **Then** a exclusão é
   recusada com mensagem clara e nada muda — paridade com o Jinja (flash de erro, sem exclusão).
3. **Given** um usuário sem Comercial/Superadmin (ex.: só Financeiro/Ensaio/Casting), **When** tenta
   excluir, **Then** recebe 403 e nada muda — paridade com o gate `_CAN_DELETE` do Jinja.
4. **Given** o botão de excluir, **When** clicado, **Then** pede confirmação antes (ação destrutiva),
   dá feedback imediato e não dispara duas exclusões (Princípio V).

---

### User Story 2 - Sincronizar o evento com o Google (Priority: P2)

Do detalhe do evento em React, qualquer usuário autenticado rebusca o evento no Google Calendar e
reaplica no banco; a tela atualiza sem reload.

**Independent Test**: sincronizar um evento pela tela React (com o Google mockado na verificação) e
conferir que o mesmo núcleo de sincronização é chamado que no Jinja, que a tela recebe o evento
atualizado, e que os erros previstos (sem `google_event_id`; não encontrado no Google) retornam
mensagem amigável — paridade com os flashes do Jinja.

**Acceptance Scenarios**:

1. **Given** um evento com `google_event_id`, **When** o usuário sincroniza, **Then** o núcleo de
   sincronização roda (mesmo caminho do Jinja) e a tela recebe o evento atualizado sem reload.
2. **Given** um evento **sem** `google_event_id`, **When** o usuário tenta sincronizar, **Then**
   recebe uma mensagem amigável e nada muda — paridade com o flash de erro do Jinja.
3. **Given** um evento que o Google não encontra, **When** o usuário sincroniza, **Then** recebe uma
   mensagem amigável e nada muda — paridade com o Jinja.

---

### Edge Cases

- **Líder de grupo**: a única condição que recusa a exclusão. A paridade preserva a checagem exata
  (`is_group_leader`) e a mensagem de "desagrupe antes".
- **Falha do Google na exclusão**: a exclusão local prossegue mesmo se o Google falhar (o Jinja
  registra um aviso; a API não expõe o aviso mas também não trava). Comportamento preservado.
- **Efeitos colaterais da exclusão**: limpeza das tabelas sem cascade e tratamento de comissões
  (cancelar pendente / estornar paga) já vivem em `_delete_event` — reusados intactos.
- **Sincronização é destrutiva sobre os campos do evento**: reaplica o que vier do Google. É a mesma
  operação de hoje; a migração não muda o comportamento, só o gatilho (botão React além do Jinja).
- **RBAC distinta**: excluir tem gate próprio (Comercial/SA), sincronizar não tem gate de papel. A
  paridade preserva os dois.
- **Coexistência**: Jinja (`app.`) e React (`beta`) no mesmo banco; um só núcleo por ação evita
  divergência. Os POSTs Jinja seguem 302 inalterados.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Excluir e sincronizar MUST ter endpoints JSON dedicados que executam a MESMA lógica já
  existente, reusando um núcleo compartilhado (função de módulo em `routes.py`) — não
  reimplementando (Princípio I).
- **FR-002**: Cada ação MUST produzir exatamente o mesmo efeito que o fluxo Jinja equivalente
  (exclusão: linha removida + log `manual_deleted` + efeitos de `_delete_event`; sincronização:
  mesmo `sync_events`), verificado contra `manto_local`.
- **FR-003**: A RBAC MUST ser idêntica: excluir = `_CAN_DELETE` (Comercial/Superadmin); sincronizar
  = qualquer autenticado. Aplicada no servidor.
- **FR-004**: A exclusão de um evento **líder de grupo** MUST ser recusada (nada muda), com resposta
  de erro clara — paridade com o Jinja.
- **FR-005**: A sincronização MUST retornar o evento atualizado no formato de leitura da 145
  (`serialize_event_detail`) para a tela re-renderizar sem reload; a exclusão MUST responder sucesso
  simples (o evento deixou de existir) e a tela React MUST navegar de volta à agenda e invalidar a
  lista.
- **FR-006**: O serializer MUST expor o flag `can_delete` (Comercial/Superadmin) para a tela decidir
  mostrar o botão de excluir.
- **FR-007**: O botão de excluir MUST pedir confirmação antes (ação destrutiva) e nenhum botão MUST
  ficar "morto" ao clique; um clique a mais NUNCA gera efeito duplicado (Princípio V).
- **FR-008**: As duas ações no Jinja MUST continuar funcionando inalteradas durante a transição
  (coexistência, mesmo banco).
- **FR-009**: Os controles em React MUST cumprir o Princípio VIII (mobile-first) quando exibidos.

### Key Entities

Sem entidade nova. Exclusão sobre `CalendarEvent` (+ tabelas relacionadas já tratadas por
`_delete_event`) e `SyncLog`/`EventLog` conforme hoje; sincronização reusa `sync_events`. Nenhuma
mudança de schema.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Após excluir pela API, o estado do banco é indistinguível de excluir pelo Jinja (linha
  ausente, log `manual_deleted`, comissões tratadas) — verificado contra `manto_local`.
- **SC-002**: Sincronizar pela API chama o mesmo núcleo de sincronização que o Jinja; os dois erros
  previstos retornam mensagem amigável equivalente ao flash.
- **SC-003**: Um líder de grupo nunca é excluído por nenhum dos dois caminhos.
- **SC-004**: Nenhuma das duas ações no app Jinja regride durante a migração.

## Assumptions

- **Núcleo em `routes.py`** (não em um `ops` novo): justificado pelo acoplamento aos helpers Google
  (`_delete_event`, `fetch_single_event`, `sync_events`, `_log_sync`) que vivem em `routes.py`;
  mover invertia a direção `routes → ops` da constituição. `api → routes` já é a direção usada para
  gates. Nomes finais no plano.
- **Endpoints REST**: `DELETE /api/events/<id>` (excluir; 409 se líder de grupo) e
  `POST /api/events/<id>/sync` (sincronizar). Nomes finais no plano.
- **Verificação** mocka o Google (a exclusão não chama o Google real; a sincronização mocka
  `fetch_single_event`/`sync_events` e verifica que ambos os caminhos os invocam). Requests fora de
  `app_context`.
- Continuação natural do detalhe do evento em React: depois desta fatia, faltam em Jinja apenas criar
  evento e as ações de upload (fatias seguintes).
