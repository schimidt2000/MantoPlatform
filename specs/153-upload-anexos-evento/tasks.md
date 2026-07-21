# Tasks: Upload e Gestão de Anexos do Evento (153)

**Input**: `spec.md`, `plan.md`, `data-model.md`, `contracts/upload-endpoints.md`, `quickstart.md`
**Tests**: verificação funcional automatizada (`scripts/db/verify_153_upload_anexos.py`) contra
`manto_local`, por paridade API×Jinja — não TDD unitário (segue o padrão já estabelecido em
146-152). Uma tarefa por User Story estende o mesmo script.

## Phase 1: Setup

- [X] T001 Adicionar seção "Upload de arquivo (multipart/form-data)" em
  `specs/144-migracao-react-spa/contracts/api-conventions.md`, referenciando
  `specs/153-upload-anexos-evento/contracts/upload-endpoints.md` como o contrato desta fatia
  (convenção normativa para toda rota futura de upload — plan.md Design Decision 1).

## Phase 2: Foundational (bloqueia todas as User Stories)

**⚠️ CRÍTICO — nenhuma User Story pode começar antes desta fase.**

- [X] T002 Criar `_save_bounded_upload(file_storage, upload_dir, subpath, *, max_mb=10) ->
  str | None` em `app/calendar/routes.py` (mesmo comportamento hoje inline em 3 lugares:
  checar tamanho, `secure_filename`, `file.save`, devolver path público ou `None`).
- [X] T003 Refatorar `_handle_add_contract`, `_handle_add_payment` e
  `_handle_collect_reembolso` em `app/calendar/routes.py` para chamar `_save_bounded_upload`
  no lugar do bloco duplicado inline (comportamento idêntico — mesmo limite de 10 MB, mesmo
  diretório/subpath de cada um). Depende de T002.
- [X] T004 Refatorar `_save_nf_file` em `app/calendar/routes.py` para chamar
  `_save_bounded_upload(file_storage, UPLOAD_INVOICES, "invoices", max_mb=10)` por dentro,
  mantendo a assinatura externa (`file_storage -> str | None`) idêntica. Depende de T002.
- [X] T005 [P] Estender `apiFetch` em `frontend/packages/api-client/src/client.ts`: quando
  `options.body instanceof FormData`, não incluir o header `Content-Type` (deixa o `fetch`
  nativo gerar o boundary do multipart); comportamento JSON existente inalterado nos demais
  casos.
- [X] T006 Criar `scripts/db/verify_153_upload_anexos.py` (esqueleto): `create_app()`, helpers
  `check`/`make_user`/`drop_user`/`mk_event`, login via test client, sem asserts de fluxo
  ainda (cada User Story abaixo adiciona sua seção). Mesmo padrão de
  `scripts/db/verify_150_observacoes.py`.

**Checkpoint**: `_save_bounded_upload` funcionando e coberto pelos 3 refactors; `apiFetch`
pronto para multipart; esqueleto de verificação criado. A partir daqui as User Stories são
independentes entre si.

---

## Phase 3: User Story 1 — Nota fiscal e contrato do evento (P1) 🎯 MVP

**Goal**: anexar nota fiscal e contrato a um evento existente pela tela React; ver as listas já
anexadas; SUPERADMIN excluir/alternar "assinado" no contrato.

**Independent Test**: abrir um evento na tela React, anexar nota fiscal e contrato, recarregar
e ver ambos na lista com link de abrir/baixar; como SUPERADMIN, marcar assinado e excluir o
contrato.

### Backend

- [X] T007 [US1] `_add_invoice_record(event, *, amount, issue_date, file_storage) ->
  EventInvoice | None` em `app/calendar/routes.py`: rejeita (devolve `None`) só se
  amount/issue_date/arquivo vierem todos vazios; `status="emitida"`+`issued_at` se há arquivo
  (via `_save_nf_file`), senão `"a_emitir"`. Não mexe em notas existentes nem em
  `event.with_invoice`.
- [X] T008 [US1] `_add_contract_record(event, *, file_storage) -> EventContract | None`,
  `_delete_contract_record(contract) -> None`, `_toggle_contract_signed(contract) -> None`
  em `app/calendar/routes.py` — paridade com `_handle_add_contract`/`_handle_delete_contract`/
  `_handle_toggle_contract_signed` (usa `_save_bounded_upload` para o arquivo).
- [X] T009 [US1] `POST /api/events/<id>/invoices` em `app/api/agenda_write.py` (gate
  `_CAN_EDIT_EVENT`, multipart `amount`/`issue_date`/`file`, 400 se os três vazios, 201 com
  `_event_detail_json`). Depende de T007.
- [X] T010 [US1] `POST /api/events/<id>/contracts`, `DELETE /api/contracts/<id>` (SUPERADMIN),
  `POST /api/contracts/<id>/toggle-signed` (SUPERADMIN) em `app/api/agenda_write.py`. Depende
  de T008.
- [X] T011 [US1] Em `app/api/agenda_read.py` (`serialize_event_detail`), adicionar
  `data["notas_fiscais"]` (`id`/`amount`/`issue_date`/`status`/`file`) no bloco
  `show_comercial` (mesma visibilidade de `data["contratos"]`, já existente e sem mudança de
  shape).

### Frontend

- [X] T012 [P] [US1] Criar `frontend/apps/internal/src/lib/eventAttachments.ts` com
  `useAddInvoice`, `useAddContract`, `useDeleteContract`, `useToggleContractSigned` (mesmo
  padrão de `eventOps.ts`: `useMutation` + `body: FormData` + `onSuccess →
  queryClient.setQueryData(["event", id], updated)`).
- [X] T013 [P] [US1] Em `frontend/apps/internal/src/lib/agenda.ts`, adicionar o tipo
  `notas_fiscais?: {id, amount, issue_date, status, file}[]` a `EventoDetalhe`.
- [X] T014 [US1] Em `frontend/apps/internal/src/pages/EventDetailPage.tsx`: componente
  `NotasFiscais` (lista + form de adicionar: `MoneyInput` de valor, `<input type="date">`,
  `<input type="file">`) e componente `Contratos` (lista com link `assetUrl(file_path)`,
  badge "assinado"/"pendente", botões excluir/alternar visíveis só quando
  `data.flags.is_superadmin` — conferir o nome exato da flag em `EventoDetalhe["flags"]` antes
  de usar — + form de adicionar). Ambos dentro da seção "Financeiro"/comercial já renderizada
  condicionalmente a `show_comercial`. Depende de T012, T013.
- [X] T015 [US1] Estender `scripts/db/verify_153_upload_anexos.py`: paridade API×Jinja para
  adicionar nota fiscal (com e sem arquivo, caso "todos vazios" rejeitado), adicionar/excluir/
  alternar-assinado contrato (incl. 403 para não-SUPERADMIN), arquivo > 10 MB rejeitado.

**Checkpoint**: US1 completa e testável isoladamente — nota fiscal e contrato 100% geridos
pela tela React.

---

## Phase 4: User Story 2 — Comprovante de pagamento de cachê (P2)

**Goal**: registrar pagamento com comprovante pela tela React; ver comprovantes com link;
SUPERADMIN editar valor/excluir.

**Independent Test**: anexar comprovante com valor, ver na lista com link; como SUPERADMIN,
editar o valor e depois excluir, confirmando que some da lista.

### Backend

- [X] T016 [US2] `_add_payment_record(event, *, amount, file_storage) -> EventPayment | None`,
  `_edit_payment_amount(payment, *, amount) -> None`, `_delete_payment_record(payment) ->
  None` em `app/calendar/routes.py` — paridade com `_handle_add_payment`/
  `_handle_edit_payment`/`_handle_delete_payment` (usa `_save_bounded_upload`).
- [X] T017 [US2] `POST /api/events/<id>/payments`, `PATCH /api/payments/<id>` (SUPERADMIN,
  JSON `{"amount"}`), `DELETE /api/payments/<id>` (SUPERADMIN) em `app/api/agenda_write.py`.
  Depende de T016.
- [X] T018 [US2] Em `app/api/agenda_read.py`, adicionar `file_path` a cada item de
  `data["pagamentos"]["items"]` (bloco `show_financeiro`, já existente).

### Frontend

- [X] T019 [P] [US2] Em `frontend/apps/internal/src/lib/eventAttachments.ts`, adicionar
  `useAddPayment`, `useEditPayment`, `useDeletePayment` (mesmo padrão de T012).
- [X] T020 [P] [US2] Em `frontend/apps/internal/src/lib/agenda.ts`, adicionar `file_path:
  string` ao tipo do item de `pagamentos.items`.
- [X] T021 [US2] Em `EventDetailPage.tsx`: link `assetUrl(file_path)` em cada item de
  `Pagamentos`; form de adicionar (valor + arquivo); para SUPERADMIN, input de edição de valor
  + botão salvar, e botão excluir com `window.confirm(...)` (mesmo padrão de
  `ObservationItem`). Depende de T019, T020.
- [X] T022 [US2] Estender `verify_153_upload_anexos.py`: paridade para adicionar (com/sem
  valor ou arquivo → 400), editar (SUPERADMIN vs. 403 outro papel), excluir pagamento.

**Checkpoint**: US2 completa e testável isoladamente, sem dependência de US1.

---

## Phase 5: User Story 3 — Comprovante de reembolso (P3)

**Goal**: registrar reembolso com comprovante do gasto original; marcar como cobrado com
comprovante de recebimento; SUPERADMIN excluir.

**Independent Test**: registrar reembolso com comprovante, ver pendente na lista; marcar como
cobrado anexando comprovante de recebimento, ver "cobrado"; excluir como SUPERADMIN.

### Backend

- [X] T023 [US3] `_add_reimbursement_record(event, *, description, amount, file_storage,
  created_by_id) -> EventReimbursement | None`, `_collect_reimbursement_record(reimbursement,
  *, collected_amount, file_storage, collected_by_id) -> bool`,
  `_delete_reimbursement_record(reimbursement) -> None` em `app/calendar/routes.py` —
  paridade com `_handle_add_reembolso`/`_handle_collect_reembolso`/
  `_handle_delete_reembolso` (usa `_save_nf_file` para o comprovante do gasto original,
  `_save_bounded_upload` para o de recebimento).
- [X] T024 [US3] `POST /api/events/<id>/reimbursements`, `POST
  /api/reimbursements/<id>/collect`, `DELETE /api/reimbursements/<id>` (SUPERADMIN) em
  `app/api/agenda_write.py`. Depende de T023.
- [X] T025 [US3] Em `app/api/agenda_read.py`, adicionar `invoice_file_path`,
  `collected_amount`, `receipt_file_path` a cada item de `data["reembolsos"]["items"]`
  (bloco `show_financeiro`, já existente).

### Frontend

- [X] T026 [P] [US3] Em `eventAttachments.ts`, adicionar `useAddReimbursement`,
  `useCollectReimbursement`, `useDeleteReimbursement`.
- [X] T027 [P] [US3] Em `agenda.ts`, adicionar `invoice_file_path`, `collected_amount`,
  `receipt_file_path` ao tipo do item de `reembolsos.items`.
- [X] T028 [US3] Em `EventDetailPage.tsx`: form de adicionar reembolso (descrição, valor,
  arquivo opcional); por item, link do comprovante do gasto quando existir; form de "marcar
  como cobrado" (valor recebido + arquivo, some quando já `is_collected`) com link do
  comprovante de recebimento; botão excluir (SUPERADMIN, `window.confirm`). Depende de T026,
  T027.
- [X] T029 [US3] Estender `verify_153_upload_anexos.py`: paridade para adicionar (com/sem
  comprovante), marcar cobrado (arquivo obrigatório, 400 se já cobrado), excluir
  (SUPERADMIN vs. 403).

**Checkpoint**: US3 completa e testável isoladamente.

---

## Phase 6: User Story 4 — Observação do evento com imagem (P4)

**Goal**: criar observação de imagem pela tela React, fechando a última lacuna da feature 150.

**Independent Test**: na tela do evento, adicionar observação tipo imagem com arquivo válido;
ver a imagem na lista de observações.

### Backend

- [X] T030 [US4] Em `app/api/agenda_write.py`, estender `api_add_observation`: se
  `request.content_type` começa com `"multipart/"`, ler `obs_type`/`content`/`label` de
  `request.form` e arquivo de `request.files.get("image")` (salvo via `_save_file_upload`,
  `UPLOAD_EVENT_OBS`, `"event_obs"` — mesma função/limite já usados por
  `add_observation` no Jinja); caso contrário mantém `request.get_json()` como hoje. 400 se
  `obs_type == "image"` sem arquivo.

### Frontend

- [X] T031 [US4] Em `frontend/apps/internal/src/lib/observations.ts`, adicionar
  `useAddImageObservation` (multipart, mesmo padrão `setQueryData` de `useAddObservation`).
- [X] T032 [US4] Em `EventDetailPage.tsx` (`AddObservationForm`): adicionar opção "Imagem" ao
  seletor de tipo, trocando o campo de conteúdo por `<input type="file">` quando selecionada;
  usa `useAddImageObservation`. Depende de T031.
- [X] T033 [US4] Estender `verify_153_upload_anexos.py`: adicionar observação de imagem via
  API (com e sem arquivo → 400) e confirmar paridade com o resultado do Jinja
  (`add_observation` view); confirmar que texto/link via JSON continuam funcionando
  inalterados (regressão da mudança de content-type em T030).

**Checkpoint**: todas as 4 User Stories completas — US2 (Agenda e Eventos) fechada a 100%.

---

## Phase 7: Polish & Cross-Cutting

- [X] T034 Rodar `scripts/db/verify_153_upload_anexos.py` completo contra `manto_local` e
  corrigir qualquer falha antes de prosseguir.
- [X] T035 [P] `ruff check` nos arquivos Python tocados (`app/calendar/routes.py`,
  `app/api/agenda_write.py`, `app/api/agenda_read.py`) e `ruff format` em
  `scripts/db/verify_153_upload_anexos.py` (arquivo novo).
  Docstrings/type hints em todas as funções novas.
- [X] T036 [P] `npx tsc --noEmit` e `npm run build` em `frontend/` (workspace `internal` +
  pacotes `api-client`/`ui`/`money`) sem erros.
- [X] T037 Conferir viewport mobile (320–430px) dos novos formulários/listas em
  `EventDetailPage.tsx` (`<input type="file">`, botões de ação, links de download — sem
  rolagem horizontal).
- [X] T038 Adicionar entrada em `docs/changelog.html` descrevendo a feature (linguagem
  simples, o que mudou) e republicar no link já existente (Princípio de autonomia do
  CLAUDE.md).
- [X] T039 Commit atômico + merge de `153-upload-anexos-evento` em `main` (stage explícito,
  nunca `git add -A`), seguido de push — só depois de T034-T038 passarem.

## Dependencies

- **Setup (T001)** → não bloqueia código, mas deve vir antes das outras fases por ordem lógica
  de documentação.
- **Foundational (T002-T006)** → bloqueia TODAS as User Stories (T007 em diante).
- **US1 (T007-T015)**, **US2 (T016-T022)**, **US3 (T023-T029)**, **US4 (T030-T033)** → cada
  uma independente das outras após a fase Foundational; podem ser implementadas em qualquer
  ordem ou em paralelo (arquivos não colidem entre si, exceto `EventDetailPage.tsx` e
  `agenda_write.py`/`agenda_read.py`, editados por todas — evitar rodar em paralelo real,
  mas não há dependência lógica de uma story sobre outra).
- **Polish (T034-T039)** → depende de todas as User Stories que forem implementadas nesta
  execução.

## Parallel Example (dentro da fase Foundational)

```
T002 → T003, T004 (sequenciais, mesmo arquivo routes.py)
T005 [P] (arquivo diferente — pode rodar junto com T002-T004)
T006 [P] (arquivo novo — pode rodar junto com T002-T005)
```

## Implementation Strategy

**MVP = User Story 1** (nota fiscal + contrato): maior gap real hoje (nota fiscal não existe
em nenhuma forma na tela React; contrato é lido mas nunca exibido) — fecha o bloqueio mais
comum para a equipe comercial abandonar a tela antiga. US2-US4 entregam valor incremental,
qualquer uma pode parar aqui sem quebrar as anteriores.
