# Feature Specification: confirmar evento / logística (149)

**Feature Branch**: `149-agenda-confirmar-logistica`

**Created**: 2026-07-21

**Status**: Draft

**Input**: US4 da escrita da agenda (migração 144, US2). Casting/figurino já migrado (146/147/148).
Esta fatia migra duas ações de **nível-evento** hoje despachadas pelo POST único de
`/events/<id>`: **confirmar/desconfirmar o evento** (`toggle_confirmado`) e **salvar logística**
(`save_logistics` — maquiagem, saída, "precisa ensaio", com as notificações por e-mail que já
disparam hoje). Fora de escopo: `assign_tech_presence` (só em eventos ENSAIO, que o React não
renderiza) e todas as ações que dependem de upload de arquivo (contrato, pagamento, reembolso).

## Contexto

Continuação direta de 146/147/148, **mesmo padrão strangler-fig**: o núcleo de cada ação é
extraído para um módulo compartilhado (parâmetros explícitos, sem `request.form`/`flash`/
`current_user`), reusado por dois adaptadores finos — o handler Jinja e o endpoint JSON (Princípio
I, uma só implementação da regra). Diferente do casting (que opera sobre um cargo), estas duas
ações operam sobre o **evento**:

- **confirmar** (`toggle_confirmado`, feature 116): liga/desliga `confirmed_at`/`confirmed_by`,
  registra `EventLog`. É o registro persistido de que o evento foi confirmado (≠ do botão que só
  copia a mensagem de WhatsApp). RBAC = **Comercial ou Superadmin**.
- **logística** (`save_logistics`): edita horário/local de maquiagem, horário/local de saída e o
  flag "precisa ensaio". Quando um campo de logística muda, **notifica por e-mail** os talentos com
  cargo aceito; quando "precisa ensaio" liga (transição de desligado→ligado), **alerta a equipe de
  ENSAIO** por e-mail. RBAC = mesmo gate de edição do evento (`_CAN_EDIT_EVENT` =
  casting/figurino/comercial/financeiro/superadmin), como o POST Jinja que a despacha.

Hoje o React (feature 145) já mostra o badge **"Confirmado"** como **somente-leitura** e **não
mostra** a logística. Esta fatia torna o badge um **toggle** e cria a **seção de Logística
editável** na `EventDetailPage`.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Confirmar / desconfirmar o evento (Priority: P1)

Do detalhe do evento em React, o Comercial (ou superadmin) marca o evento como confirmado — e pode
desfazer. O estado persiste (`confirmed_at`/`confirmed_by`) e entra no log, exatamente como o toggle
do Jinja.

**Independent Test**: confirmar um evento não-confirmado pela tela React e conferir que
`confirmed_at`/`confirmed_by` ficam preenchidos e há um `EventLog` idêntico ao do Jinja; clicar de
novo desfaz (volta a `None`); a tela atualiza sem reload.

**Acceptance Scenarios**:

1. **Given** um evento não confirmado, **When** o Comercial confirma, **Then** `confirmed_at` e
   `confirmed_by` ficam preenchidos, há log "Marcou o evento como confirmado" e o badge passa a
   "Confirmado" — igual ao Jinja.
2. **Given** um evento já confirmado, **When** o Comercial clica de novo, **Then** `confirmed_at`/
   `confirmed_by` voltam a `None`, há log "Desfez a confirmação do evento".
3. **Given** um usuário sem papel Comercial/Superadmin (ex.: só Financeiro/Ensaio), **When** tenta
   confirmar, **Then** recebe 403 e nada muda — paridade com o Jinja, que bloqueia com flash de erro
   sem alterar estado.
4. **Given** o botão, **When** clicado, **Then** dá feedback imediato e um clique a mais não gera
   registro duplicado (Princípio V).

---

### User Story 2 - Salvar logística do evento (Priority: P2)

Do detalhe do evento em React, quem pode editar o evento define horário/local de maquiagem, horário/
local de saída e "precisa ensaio". Ao salvar, as mesmas notificações de hoje disparam: talentos com
cargo aceito são avisados das mudanças de logística, e a equipe de ENSAIO é alertada quando "precisa
ensaio" liga.

**Independent Test**: alterar campos de logística pela tela React e confirmar que os campos do
evento ficam idênticos ao resultado do form Jinja, que há as mesmas notificações (mockadas na
verificação), e que "precisa ensaio" ligando dispara o alerta de ENSAIO só na transição desligado→
ligado — a tela atualiza sem reload.

**Acceptance Scenarios**:

1. **Given** o editor de logística, **When** o usuário salva novos horário/local de maquiagem/saída,
   **Then** os campos do evento ficam idênticos ao que o form Jinja gravaria (incluindo o local
   "outro" que usa o campo custom), e as mudanças relevantes viram notificação aos cargos aceitos.
2. **Given** "precisa ensaio" desligado, **When** o usuário liga e salva, **Then** o alerta de
   ENSAIO é disparado uma vez; salvar de novo com ele já ligado NÃO redispara (paridade com a
   transição do Jinja).
3. **Given** um usuário fora de `_CAN_EDIT_EVENT` (ex.: só Ensaio/Vendas), **When** tenta salvar
   logística, **Then** recebe 403 — igual ao POST Jinja de `/events/<id>`.

---

### Edge Cases

- **Notificações por e-mail**: salvar logística pode disparar e-mails reais (aos cargos aceitos e à
  equipe de ENSAIO). A migração mantém exatamente o mesmo comportamento — mesmos gatilhos, nem
  duplicado nem omitido. A verificação mocka os envios (nada de e-mail real contra `manto_local`).
- **Transição de "precisa ensaio"**: o alerta de ENSAIO só dispara quando o flag passa de desligado
  para ligado (não em todo save). A paridade preserva essa condição exata.
- **Local "outro"**: o local de maquiagem tem a opção "outro" que lê um campo custom — a API precisa
  aceitar o mesmo par (seleção + valor custom) e resolver para o mesmo valor final.
- **Confirmar não é edição de evento**: confirmar tem RBAC própria (Comercial/Superadmin), mais
  estreita que `_CAN_EDIT_EVENT`. Um Financeiro pode editar o evento mas NÃO confirmar — a paridade
  preserva os dois gates distintos.
- **Clique duplo em confirmar**: o toggle é idempotente do ponto de vista do usuário; o front bloqueia
  o clique enquanto pendente e um clique a mais não gera log espúrio relevante (Princípio V).
- **Coexistência**: Jinja (`app.`) e React (`beta`) gravam no mesmo banco; um só caminho de lógica
  (núcleo compartilhado) evita divergência.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Cada ação (confirmar/desconfirmar, salvar logística) MUST ter um endpoint JSON
  dedicado que executa a MESMA lógica já existente, reusando um núcleo compartilhado — não
  reimplementando (Princípio I).
- **FR-002**: Cada ação MUST produzir exatamente o mesmo estado no banco que o fluxo Jinja
  equivalente (mesmos campos em `calendar_events`, mesmo `EventLog`), verificado contra
  `manto_local`.
- **FR-003**: A RBAC de cada ação MUST ser idêntica à atual, aplicada no servidor: confirmar =
  Comercial ou Superadmin; logística = `_CAN_EDIT_EVENT` (como o POST Jinja que a despacha).
- **FR-004**: As notificações de logística MUST continuar disparando exatamente como hoje — aviso
  aos cargos aceitos nas mudanças de logística e alerta de ENSAIO só na transição desligado→ligado
  de "precisa ensaio" — sem duplicar nem omitir.
- **FR-005**: Ao concluir, a API MUST devolver o evento atualizado no formato de leitura da 145
  (`serialize_event_detail`), respeitando o RBAC de serialização, para a tela re-renderizar sem
  reload. O serializer MUST passar a expor os campos de logística e `confirmed_by`, além dos flags
  necessários para a tela decidir quais controles mostrar.
- **FR-006**: Nenhum botão MUST ficar "morto" ao clique; toda ação dá feedback imediato e um clique
  a mais NUNCA gera registro duplicado (Princípio V).
- **FR-007**: As ações no `event_detail.html` Jinja MUST continuar funcionando inalteradas durante
  toda a transição (coexistência, mesmo banco).
- **FR-008**: A seção de Logística e o toggle de confirmação em React MUST cumprir o Princípio VIII
  (mobile-first) quando exibidos — sem rolagem horizontal em 320–430px, alvos de toque ≥44px.

### Key Entities

Sem entidade nova. Escrita sobre `CalendarEvent` (`confirmed_at`/`confirmed_by_id`; `makeup_time`/
`makeup_location`, `departure_time`/`departure_location`, `needs_rehearsal`) e `EventLog` já
existentes. Nenhuma mudança de schema.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Para cada ação, o estado do banco após executá-la pela API é indistinguível do estado
  após executá-la pelo fluxo Jinja, para os mesmos dados — verificado campo a campo contra
  `manto_local`.
- **SC-002**: As notificações de logística disparam exatamente nos mesmos gatilhos que hoje — zero
  duplicado, zero perdido; o alerta de ENSAIO só na transição de "precisa ensaio".
- **SC-003**: Nenhuma dessas ações no app Jinja regride durante a migração.
- **SC-004**: Um clique repetido em confirmar nunca gera um segundo registro relevante.

## Assumptions

- **Reuso via extração**: o núcleo de cada ação é extraído para um módulo compartilhado recebendo
  parâmetros explícitos; o handler Jinja e o endpoint JSON viram adaptadores finos. UMA
  implementação da regra (o nome do módulo — ex.: `event_ops` — é decisão do plano).
- **Endpoints REST por ação**: `POST /api/events/<id>/confirm` (toggle) e
  `PATCH /api/events/<id>/logistics`. Nomes finais no plano.
- A verificação isola/mocka os envios de e-mail (não dispara e-mail real contra `manto_local`);
  requests do test client fora de `app_context`.
- Fora de escopo: `assign_tech_presence` (só em eventos ENSAIO, que o React não renderiza) e todas
  as ações com upload de arquivo (contrato, pagamento, reembolso) — dependem da fundação de upload
  (`POST /api/uploads`) que a 144 reserva para outra fatia; e o resto do evento (venda/comercial,
  agrupamento, criar/excluir evento) — fatias seguintes.
- Continuação natural do bloco de detalhe do evento em React: depois desta fatia, confirmar e
  logística deixam de ser "somente-leitura"/ausentes na tela React.
