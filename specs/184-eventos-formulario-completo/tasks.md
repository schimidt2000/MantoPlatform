---

description: "Task list template for feature implementation"
---

# Tasks: Reconstrução do Formulário de Cadastro/Edição de Eventos

**Input**: Design documents from `/specs/184-eventos-formulario-completo/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/api-events.md, quickstart.md

**Tests**: Verificação funcional automatizada (script contra `manto_local`) e Playwright são
exigidos pela constituição do projeto (Portões de Qualidade) — incluídos como tarefas próprias.

**Organization**: Tarefas agrupadas por user story (spec.md). US1 é o corpo principal (os 7
blocos); US4 e US5 são recortes de comportamento **dentro** dos componentes que a US1 cria (o
cadastro rápido de cliente vive em `ClienteBlock`/`ClientPicker`; a auto-geração de título e a
calculadora de desconto vivem em `ElencoBlock`/`ValoresBlock`) — por isso aparecem como tarefas
de verificação dedicadas em vez de implementação duplicada, mantendo rastreabilidade por story
sem duplicar código.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Pode rodar em paralelo (arquivos diferentes, sem dependência)
- **[Story]**: A qual user story a tarefa pertence (US1..US5)
- Caminhos de arquivo exatos em cada descrição

## Path Conventions (Web app — backend Flask + frontend React)

- Backend: `app/calendar/event_ops.py`, `app/api/agenda_write.py`
- Frontend: `frontend/apps/internal/src/lib/eventCreate.ts`,
  `frontend/apps/internal/src/components/ClientPicker.tsx`,
  `frontend/apps/internal/src/components/EventFormBlocks/*.tsx`,
  `frontend/apps/internal/src/components/PendingAttachmentsPanel.tsx`,
  `frontend/apps/internal/src/pages/EventCreatePage.tsx`,
  `frontend/apps/internal/src/pages/EventEditPage.tsx`,
  `frontend/apps/internal/src/pages/EventDetailPage.tsx`, `App.tsx`
- Verificação: `scripts/db/verify_184_eventos_formulario_completo.py`

---

## Phase 1: Setup

- [ ] T001 Confirmar `manto_local` acessível e migrations no head (`python -m flask db heads`
  via `.\scripts\db\run-local.ps1`) — esta feature não adiciona colunas/tabelas novas

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Nenhuma tarefa bloqueante compartilhada além do Setup — a extensão `is_signed` (US1)
e o endpoint de edição (US3) tocam arquivos backend diferentes o suficiente para não conflitarem
entre si; os componentes de bloco (US1) são a única base física que US3/US4/US5 reaproveitam, e
isso já está refletido na ordem das fases abaixo.

**Checkpoint**: Nenhuma tarefa nesta fase — prosseguir direto para a Phase 3.

---

## Phase 3: User Story 1 - Cadastro de evento com paridade total de campos (Priority: P1) 🎯 MVP

**Goal**: `/events/new` cobre os 7 blocos completos (cliente/pré-contrato, dados do evento,
elenco, valores, pagamento+comprovantes, contrato, observações com foto), com os anexos
enviados em uma segunda fase após o evento ser criado.

**Independent Test**: Preencher um evento do zero cobrindo os 7 blocos (incluindo comprovante,
contrato e observação com foto) e confirmar que tudo fica vinculado ao evento criado.

### Backend for User Story 1

- [ ] T002 [US1] Adicionar parâmetro multipart opcional `is_signed` (default `false`) em
  `POST /events/<id>/contracts` — rota em `app/api/agenda_write.py`, aplicado na criação do
  `EventContract` (helper `_add_contract_record` em `app/calendar/routes.py`, reaproveitado sem
  mudar sua assinatura pública para outros chamadores)

### Implementation for User Story 1

- [ ] T003 [US1] Atualizar `frontend/apps/internal/src/components/ClientPicker.tsx`: adicionar
  "+ Cadastrar novo cliente" (mini-form inline: nome completo, telefone com DDD, empresa opcional,
  botão "Salvar e adicionar") usando `useQuickCreateClient()` (`lib/clientes.ts`, já existe)
- [ ] T004 [US1] Criar `frontend/apps/internal/src/components/EventFormBlocks/ClienteBlock.tsx`
  (Bloco 1): compõe `ClientPicker` (T003) + `FormResponsePicker`
- [ ] T005 [US1] Criar
  `frontend/apps/internal/src/components/EventFormBlocks/DadosEventoBlock.tsx` (Bloco 2):
  data/início/fim/tipo/local/descrição; ensaio sempre marcado e travado quando `event_type ===
  "SHOW"` com texto explicativo; aviso "termina no dia seguinte" quando fim &lt; início; toggle de
  reembolso com descrição/valor/nota fiscal do gasto (opcional)
- [ ] T006 [US1] Criar `frontend/apps/internal/src/components/EventFormBlocks/ElencoBlock.tsx`
  (Bloco 3): linhas dinâmicas de personagem (nome, figurino, talento, maquiagem, cantor(a)),
  coordenador pré-escalado (com texto de ajuda "vaga aberta ao casting"), botão "Gerar título
  automaticamente" (`(TIPO) NOME1 + NOME2`, para de sobrescrever após edição manual do título)
- [ ] T007 [US1] Criar `frontend/apps/internal/src/components/EventFormBlocks/ValoresBlock.tsx`
  (Bloco 4): toggle cortesia/permuta, valor antes do desconto + valor de venda com % de desconto
  calculado em tempo real, transporte, acréscimo, toggle nota fiscal, vendedor, data da venda
- [ ] T008 [US1] Criar `frontend/apps/internal/src/components/EventFormBlocks/PagamentoBlock.tsx`
  (Bloco 5): pills de forma de pagamento (À vista/Dividido no PIX/Faturado/Cartão), parcelas
  (2-12)/vencimento condicionais, lista local de comprovantes pendentes (arquivo + valor R$
  opcional + remover, "+ Adicionar comprovante") — PDF/JPG/PNG até 20 MB
- [ ] T009 [US1] Criar `frontend/apps/internal/src/components/EventFormBlocks/ContratoBlock.tsx`
  (Bloco 6): `FileUpload` (`@manto/ui`) para o contrato (PDF/PNG/JPG até 20 MB) + checkbox
  "Contrato já assinado"
- [ ] T010 [US1] Criar
  `frontend/apps/internal/src/components/EventFormBlocks/ObservacoesBlock.tsx` (Bloco 7):
  atalhos "+ Texto"/"+ Foto"/"+ Link", cada observação com rótulo opcional
- [ ] T011 [US1] Criar `frontend/apps/internal/src/components/PendingAttachmentsPanel.tsx`:
  lista de status por anexo pendente após a criação do evento (enviando/enviado/falhou), com
  "Tentar novamente" por item
- [ ] T012 [US1] Atualizar `frontend/apps/internal/src/lib/eventCreate.ts`: remover
  `has_reembolso`/`reembolso_description`/`reembolso_amount` do payload de criação (reembolso
  passa a ser criado na fase 2), `CharacterInput` ganha `role_id: number | null` opcional,
  `ObservationInput` ganha o tipo `"image"` com `file`
- [ ] T013 [US1] Reescrever `frontend/apps/internal/src/pages/EventCreatePage.tsx`: monta os 7
  blocos (T004–T010); ao submeter, roda a fase 1 (`POST /api/events`, hook `useCreateEvent()`
  já existente) e, com sucesso, a fase 2 (loop pelos anexos pendentes usando os hooks já
  existentes em `lib/eventAttachments.ts` — `useAddPayment`, `useAddContract`,
  `useAddReimbursement`, `useAddObservation`), exibindo `PendingAttachmentsPanel` (T011) até
  todos os anexos resolverem; só navega para `/events/:id` depois
- [ ] T014 [US1] Verificar em preview: criar um evento cobrindo os 7 blocos (cliente novo,
  personagens, valores, pagamento com 2 comprovantes, contrato assinado, observação com foto) —
  itens 1–9 de `quickstart.md`

**Checkpoint**: Criação de evento com paridade total de campos, funcional e testável
isoladamente (MVP).

---

## Phase 4: User Story 2 - Validação em tempo real com auto-scroll ao primeiro erro (Priority: P1)

**Goal**: Qualquer campo obrigatório/inválido é destacado ao perder o foco; ao tentar salvar com
erros, a tela rola suavemente até o primeiro campo problemático, com foco nele.

**Independent Test**: Submeter o formulário vazio e confirmar o banner de erro + o scroll
automático até o primeiro campo inválido.

### Implementation for User Story 2

- [ ] T015 [US2] Configurar `useForm` com `mode: "onBlur"` em
  `frontend/apps/internal/src/pages/EventCreatePage.tsx`; aplicar estilo de borda vermelha
  espessa + mensagem de erro nos campos dos blocos criados na Phase 3 (via prop `error`/classe
  condicional compartilhada entre os `EventFormBlocks/*`)
- [ ] T016 [US2] Implementar `FIELD_ORDER` (ordem visual dos 7 blocos) + varredura de
  `formState.errors` ao falhar `handleSubmit`, chamando `setFocus(nome)` (react-hook-form) e
  `scrollIntoView({behavior:"smooth", block:"center"})` no container do primeiro campo inválido,
  em `EventCreatePage.tsx`
- [ ] T017 [US2] Implementar validação client-side dos blocos de lista (elenco, clientes,
  comprovantes, observações — não cobertos por `react-hook-form`) como `blockErrors`, integrada
  à mesma varredura/scroll de T016
- [ ] T018 [US2] Implementar banner de erro fixo no topo e no rodapé do formulário
  ("Existem campos obrigatórios não preenchidos. Verifique os destaques em vermelho."), visível
  só após uma tentativa de envio bloqueada
- [ ] T019 [US2] Verificar: submeter o formulário vazio e confirmar banner + scroll suave + foco
  no primeiro campo; corrigir o campo e confirmar que o destaque some sem precisar reenviar —
  item 8 de `quickstart.md`

**Checkpoint**: US1 + US2 juntas entregam a criação completa com validação rigorosa.

---

## Phase 5: User Story 3 - Edição unificada de um evento existente (Priority: P2)

**Goal**: `/events/:id/edit` reaproveita os mesmos 7 blocos da criação, pré-preenchidos com os
dados atuais do evento, salvando por um novo endpoint de atualização em bloco; anexos usam os
endpoints já existentes (o evento já tem id).

**Independent Test**: Abrir `/events/:id/edit` de um evento com dados variados, alterar um campo
de cada bloco, salvar, reabrir e confirmar a persistência.

### Backend for User Story 3

- [ ] T020 [US3] Implementar `update_event_core(event, ...)` em `app/calendar/event_ops.py`:
  título, tipo, data/horários, local, descrição, ensaio, valores, pagamento, vendedor, data da
  venda, coordenador, pré-contrato vinculado — reaproveita `_validate_event_core` (import local
  de `app/calendar/routes.py`, mesmo padrão já usado por `save_logistics`/`toggle_confirmed`)
- [ ] T021 [US3] Implementar a reconciliação de elenco por `role_id` dentro de
  `update_event_core()` (`app/calendar/event_ops.py`): update de linhas existentes, insert de
  linhas novas, delete de linhas removidas — recusando a operação inteira (nada salvo) se alguma
  removida tiver `invite_status == "accepted"` e o ator não for SUPERADMIN
- [ ] T022 [US3] Implementar a substituição completa de `EventClient` dentro de
  `update_event_core()` (`app/calendar/event_ops.py`), reaproveitando a lógica de
  `_create_client_links` e recalculando `CalendarEvent.client_id` (cliente primário)
- [ ] T023 [US3] Adicionar endpoint `PATCH /api/events/<int:event_id>` em
  `app/api/agenda_write.py` (RBAC: `_can_create_event()` — COMERCIAL/SUPERADMIN; 400 de
  validação, 409 de convite aceito, 404 de evento inexistente) — ver `contracts/api-events.md`

### Implementation for User Story 3

- [ ] T024 [US3] Atualizar `frontend/apps/internal/src/lib/eventCreate.ts`: hook
  `useUpdateEvent(eventId)` (`useMutation`, `PATCH /api/events/:id`, invalida `["event", eventId]`
  e `["agenda"]`/`["agenda-dia"]`)
- [ ] T025 [US3] Criar `frontend/apps/internal/src/pages/EventEditPage.tsx`: carrega o evento via
  `GET /api/events/:id` (hook já existente da tela de detalhe), popula os 7 blocos
  (`EventFormBlocks/*` da Phase 3) com os valores atuais, salva via `useUpdateEvent()` (T024);
  anexos (comprovantes/contrato/reembolso/observações) usam diretamente os hooks já existentes de
  `lib/eventAttachments.ts` (mesmo padrão de `EventDetailPage.tsx`, sem fase 2 — o evento já
  existe)
- [ ] T026 [US3] Adicionar a rota `/events/:id/edit` em `frontend/apps/internal/src/App.tsx`
- [ ] T027 [US3] Adicionar botão "Editar" no `actions` do `PageHeader` de
  `frontend/apps/internal/src/pages/EventDetailPage.tsx`, visível quando
  `data.flags.can_edit_event`, linkando para `/events/${id}/edit`

### Verification for User Story 3

- [ ] T028 [US3] Escrever `scripts/db/verify_184_eventos_formulario_completo.py` (test client
  Flask, requests fora de `app_context`, contra `manto_local`) cobrindo: `PATCH
  /api/events/<id>` (200 sucesso, 400 validação, 409 personagem com convite aceito, 403 RBAC),
  `POST /events/<id>/contracts` com `is_signed=true`
- [ ] T029 [US3] Rodar a verificação funcional contra `manto_local` e confirmar 100% de sucesso
- [ ] T030 [US3] Verificar em preview: editar um evento existente cobrindo todos os blocos,
  incluindo tentar remover um personagem com convite aceito sem ser SUPERADMIN — itens 10–12 de
  `quickstart.md`

**Checkpoint**: Criação e edição funcionais de forma unificada e independentemente testáveis.

---

## Phase 6: User Story 4 - Cadastro rápido de cliente inline (Priority: P2)

**Goal**: Confirmar que o cadastro rápido de cliente (implementado dentro de T003/T004) funciona
como uma peça independente do restante do formulário.

**Independent Test**: Em qualquer ponto do formulário, cadastrar um cliente novo sem sair da tela.

- [ ] T031 [US4] Verificar isoladamente: buscar um telefone que não existe, clicar
  "+ Cadastrar novo cliente", preencher nome+telefone, salvar, e confirmar (a) o cliente aparece
  selecionado automaticamente, (b) submeter com nome ou telefone vazio destaca os campos sem
  fechar o mini-formulário, (c) reaproveitamento por telefone já existente não duplica o cliente

**Checkpoint**: Cadastro rápido de cliente validado como incremento independente.

---

## Phase 7: User Story 5 - Auto-geração de título e calculadora de desconto (Priority: P3)

**Goal**: Confirmar que as duas conveniências (implementadas dentro de T006/T007) funcionam
corretamente de forma isolada.

**Independent Test**: Gerar o título a partir de dois personagens e do tipo; digitar valores e ver
o percentual de desconto.

- [ ] T032 [US5] Verificar isoladamente: gerar título com 2+ personagens e tipo selecionado
  (formato `(TIPO) NOME1 + NOME2`); editar o título manualmente e confirmar que ele para de ser
  sobrescrito ao adicionar mais personagens; digitar valor antes do desconto e valor de venda e
  confirmar o percentual atualizado a cada tecla

**Checkpoint**: Todas as 5 user stories funcionais de forma independente.

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Portões de qualidade da constituição, validação end-to-end e entrega.

- [ ] T033 Rodar `npx tsc --noEmit` em `frontend/apps/internal` e corrigir quaisquer erros de tipo
- [ ] T034 Rodar `npm run build` (`vite build`) em `frontend/apps/internal` e corrigir quaisquer
  erros
- [ ] T035 [P] Escrever `frontend/apps/internal/e2e/event-form.spec.ts` (Playwright): criação
  completa (7 blocos + anexos), edição, validação com auto-scroll (submissão vazia e com erros
  específicos)
- [ ] T036 Rodar a suíte Playwright contra `manto_local` e corrigir falhas
- [ ] T037 [P] Adicionar entrada em `docs/changelog.html` descrevendo a entrega (linguagem
  simples) e republicar no link já existente
- [ ] T038 Commit atômico final e merge em `main` (sem push — não solicitado nesta feature)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: sem dependências.
- **Foundational (Phase 2)**: vazia.
- **US1 (Phase 3)**: depende só do Setup — é o corpo físico que as demais stories reaproveitam.
- **US2 (Phase 4)**: depende dos componentes de bloco existirem (Phase 3) — validação é uma
  camada sobre os mesmos campos, não uma feature isolável de arquivo.
- **US3 (Phase 5)**: depende dos componentes de bloco existirem (Phase 3, reaproveitados
  ipsis litteris); o backend (T020–T023) é independente e pode ser feito em paralelo à Phase 3
  do frontend.
- **US4 (Phase 6)**: depende de T003/T004 (Phase 3) já estarem implementados — é só a
  verificação dedicada.
- **US5 (Phase 7)**: depende de T006/T007 (Phase 3) já estarem implementados — é só a
  verificação dedicada.
- **Polish (Phase 8)**: depende de todas as stories desejadas estarem completas.

### Parallel Opportunities

- T002 (backend `is_signed`) pode rodar em paralelo a toda a Phase 3 do frontend (arquivos
  diferentes).
- T020–T023 (backend da US3) podem rodar em paralelo à Phase 3/4 do frontend (arquivos
  diferentes) — só a Phase 5 do frontend (T024–T027) depende deles.
- T005–T010 (os 7 componentes de bloco, exceto T004/T006 que dependem de T003) são arquivos
  independentes entre si e podem ser escritos em paralelo.
- T035 (Playwright) e T037 (changelog) são `[P]`.

---

## Implementation Strategy

### MVP First (User Story 1 + 2)

1. Completar Phase 1 (Setup).
2. Completar Phase 3 (US1) — criação com os 7 blocos.
3. Completar Phase 4 (US2) — validação rigorosa por cima dos mesmos blocos.
4. **PARAR e VALIDAR**: criar um evento completo e um incompleto, conferir paridade e validação.

### Entrega Incremental

1. Setup → US1 (criação completa) → validar.
2. + US2 (validação/auto-scroll) → validar.
3. + US3 (edição unificada, inclui endpoint novo) → validar (inclui verificação funcional).
4. + US4/US5 (cadastro rápido de cliente, auto-título/desconto — já entregues dentro de US1,
   apenas confirmados isoladamente aqui).
5. Polish (tsc, build, Playwright, changelog, commit/merge).

## Notes

- `[P]` = arquivos diferentes, sem dependência.
- Migrations: nenhuma nesta feature (sem coluna/tabela nova).
- Commits atômicos por grupo lógico de tarefas, mesmo padrão já usado neste repositório.
