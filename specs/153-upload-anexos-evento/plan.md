# Implementation Plan: Upload e Gestão de Anexos do Evento (153)

**Branch**: `153-upload-anexos-evento` | **Date**: 2026-07-21 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/153-upload-anexos-evento/spec.md`

## Summary

Fecha a US2 (Agenda e Eventos) migrando para React + API JSON os cinco fluxos de anexo de
arquivo que as features 149-152 deixaram só no Jinja: nota fiscal (`EventInvoice`), contrato
(`EventContract`), comprovante de pagamento de cachê (`EventPayment`, incl. editar/excluir por
SUPERADMIN), comprovante de reembolso em duas etapas (`EventReimbursement` — gasto original e
recebimento) e observação com imagem (`EventObservation`, `obs_type="image"`). Levantamento do
código atual (não só do pedido) mostrou que o gap real é maior do que "só falta o upload":
nota fiscal não é lida em NENHUM lugar da API/tela React hoje; contrato já é lido pela API mas
nunca é exibido na tela; pagamentos/reembolsos são exibidos mas sem o arquivo (sem link para
abrir/baixar); reembolso não tem nenhum endpoint de escrita ainda (só é criado hoje dentro do
`POST /api/events` da feature 152, sempre sem arquivo). Levantamento mais profundo (lendo o dispatcher `_EVENT_ACTIONS` completo
em `routes.py`, não só os handlers óbvios de "adicionar") também revelou três ações de gestão
já existentes no Jinja que a primeira leitura do spec tinha descartado por engano: excluir
contrato, marcar/desmarcar contrato como assinado, e excluir reembolso — todas SUPERADMIN,
todas incorporadas nesta fatia (spec.md corrigido: FR-014/FR-015, US1 cenário 5, US3 cenário
5). Este plano cobre leitura completa + escrita (incl. as exclusões que já existem hoje) para
os cinco fluxos.

**Padrão novo introduzido nesta fatia**: até aqui toda rota de API é JSON puro
(`api-conventions.md`). Upload de arquivo exige `multipart/form-data`, que não existe em
nenhuma rota `/api/*` ainda — a seção "Contrato de API" abaixo estende `api-conventions.md`
com a convenção multipart, mantendo os mesmos envelopes de sucesso/erro já em vigor.

## Technical Context

Igual à 146-152: Python/Flask + React (Vite/TS/TanStack Query). Sem dependência nova — upload
usa `<input type="file">` nativo + `FormData`, sem lib de upload (dropzone etc. seria excesso
para um único arquivo por ação, YAGNI).

Verificação com test client Flask contra `manto_local`, requests fora de `app_context`,
multipart montado com `data={...}, content_type="multipart/form-data"` no test client
(`io.BytesIO` para o conteúdo do arquivo).

**Armazenamento de arquivo**: inalterado — mesmos diretórios de sempre
(`UPLOAD_INVOICES`/`UPLOAD_CONTRACTS`/`UPLOAD_PAYMENTS`/`UPLOAD_EVENT_OBS`, já configurados em
`app/__init__.py`, `USE_S3=false`, volume Railway em produção).

## Constitution Check

- **I (reutilizar)**: `_save_nf_file` (já existe, 10 MB, usado por nota fiscal e comprovante de
  gasto do reembolso) reaproveitado sem mudança de assinatura. Novo helper único
  `_save_bounded_upload(file_storage, upload_dir, subpath, *, max_mb=10)` extrai o bloco de
  "checar tamanho + `secure_filename` + salvar" hoje duplicado 3× inline
  (`_handle_add_contract`, `_handle_add_payment`, `_handle_collect_reembolso`) — as três
  passam a chamar o helper (refatoração comportamento-preservado, coberta pela verificação de
  paridade). `_save_file_upload` (20 MB, observação-imagem) continua como está, sem mudança.
  `_event_detail_json`/`serialize_event_detail` (já existentes) reaproveitados para toda
  resposta de sucesso — nenhum novo formato de payload.
- **II (padrões de código)**: cada núcleo novo é uma função pequena e testável (evento →
  registro), separada do parsing de `request`/arquivo. Type hints/docstrings em todas.
- **III (API first)**: 7 endpoints novos + 1 estendido, 100% JSON no envelope de resposta
  (corpo da requisição é `multipart/form-data`, não o corpo da resposta); Jinja continua
  existindo em paralelo, sem remoção nesta fatia.
- **IV (não quebrar)**: paridade de banco verificada contra `manto_local` para os 5 fluxos +
  refatoração do helper de upload; POST/PATCH/DELETE Jinja seguem exatamente como hoje.
- **V (feedback)**: erro 400 (arquivo/valor faltando) mostrado inline no formulário (mesmo
  padrão já usado em `AddObservationForm` — texto vermelho abaixo do form, sem apagar o que o
  usuário já preencheu); toda ação com `useMutation` usa `loading={mutation.isPending}` no
  `Button` (`@manto/ui`); exclusão de comprovante de pagamento mantém `window.confirm(...)`
  (mesmo padrão já usado para excluir observação/cargo/evento — não existe componente de
  Dialog no `@manto/ui` ainda, introduzir um seria escopo fora desta fatia).
- **VII (monetário)**: valor de pagamento/reembolso usa `<MoneyInput/>` de `@manto/money`
  (mesmo componente já usado no formulário de criação de evento).
- **VIII (mobile-first)**: novos formulários (inputs de arquivo, valor, texto) conferidos em
  320–430px — `<input type="file">` nativo já é utilizável em mobile sem CSS extra.
- **IX (movimento)**: nenhuma transição nova necessária — os novos blocos são listas/formulários
  simples dentro de `Section`/`Card` já existentes, mesmo padrão de `Pagamentos`/`Reembolsos`
  atuais (sem animação hoje).

Duas violações justificadas — ver Complexity Tracking: núcleo em `routes.py` (mesma exceção de
146-152) e extensão de `api_add_observation` para aceitar dois content-types.

## Project Structure

```text
app/calendar/routes.py             # + _save_bounded_upload (novo, substitui 3 blocos inline)
                                    # + núcleo: _add_invoice_record, _add_contract_record,
                                    #   _delete_contract_record, _toggle_contract_signed,
                                    #   _add_payment_record, _edit_payment_amount,
                                    #   _delete_payment_record, _add_reimbursement_record,
                                    #   _collect_reimbursement_record, _delete_reimbursement_record
                                    #   (funções de módulo, prefixo _, mesma exceção de 151/152 —
                                    #   reusam _save_nf_file/_save_bounded_upload/
                                    #   _save_file_upload já locais)
                                    # + _handle_add_contract/_handle_add_payment/
                                    #   _handle_collect_reembolso passam a chamar
                                    #   _save_bounded_upload (refactor comportamento-preservado)
app/api/agenda_read.py             # serialize_event_detail: + data["notas_fiscais"] (novo);
                                    # + file_path em data["contratos"] já existente (nome do
                                    #   campo já existe, só falta expor no novo bloco de escrita
                                    #   — leitura já cobre); + file_path em pagamentos.items;
                                    # + invoice_file_path/receipt_file_path/collected_amount em
                                    #   reembolsos.items
app/api/agenda_write.py            # + POST /api/events/<id>/invoices        (multipart)
                                    # + POST /api/events/<id>/contracts       (multipart)
                                    # + DELETE /api/contracts/<id>            (sem corpo, SUPERADMIN)
                                    # + POST /api/contracts/<id>/toggle-signed (sem corpo, SUPERADMIN)
                                    # + POST /api/events/<id>/payments        (multipart)
                                    # + PATCH /api/payments/<id>              (JSON — só valor)
                                    # + DELETE /api/payments/<id>             (sem corpo)
                                    # + POST /api/events/<id>/reimbursements  (multipart, arquivo opcional)
                                    # + POST /api/reimbursements/<id>/collect (multipart)
                                    # + DELETE /api/reimbursements/<id>       (sem corpo, SUPERADMIN)
                                    # ~ POST /api/events/<id>/observations    (aceita multipart
                                    #   quando obs_type=="image", mantém JSON p/ text/link)
specs/144-migracao-react-spa/contracts/api-conventions.md  # + seção "Upload de arquivo
                                    #   (multipart/form-data)" — convenção normativa nova
frontend/apps/internal/src/
├── lib/agenda.ts                  # + tipos: notas_fiscais, file_path em pagamentos/reembolsos
├── lib/eventAttachments.ts        # NOVO — useAddInvoice, useAddContract, useDeleteContract,
│                                   #   useToggleContractSigned, useAddPayment, useEditPayment,
│                                   #   useDeletePayment, useAddReimbursement,
│                                   #   useCollectReimbursement, useDeleteReimbursement (mesmo
│                                   #   padrão de eventOps.ts: setQueryData(["event", id],
│                                   #   updated) no onSuccess)
├── lib/observations.ts            # + useAddImageObservation (multipart; useAddObservation
│                                   #   existente para texto/link fica inalterado)
packages/api-client/src/client.ts  # + apiFetch aceita body: FormData (detecta e NÃO força
│                                   #   Content-Type — o browser define o boundary sozinho)
pages/EventDetailPage.tsx          # + NotasFiscais, Contratos (novo bloco — hoje não
│                                   #   renderizado apesar de já vir da API), link de
│                                   #   abrir/baixar em Pagamentos/Reembolsos, formulários de
│                                   #   adicionar (arquivo) em cada Section, editar/excluir
│                                   #   pagamento (SUPERADMIN), marcar reembolso como cobrado,
│                                   #   observação de imagem no AddObservationForm
scripts/db/verify_153_upload_anexos.py  # NOVO: paridade API×Jinja multipart, 5 fluxos + refactor
```

## Design Decisions

1. **Convenção multipart** (nova seção em `api-conventions.md`): endpoints que recebem arquivo
   usam `Content-Type: multipart/form-data`; campos não-arquivo vão como campos de formulário
   (`request.form`, não JSON) junto do arquivo (`request.files`); a RESPOSTA continua sendo o
   mesmo envelope JSON de sempre (sucesso: objeto/lista; erro: `{"error": {"message",
   "fields"}}`, mesmos códigos 400/401/403/404). Endpoint que edita/apaga sem arquivo (`PATCH
   /api/payments/<id>`, `DELETE /api/payments/<id>`) continua JSON puro — só quem recebe
   arquivo muda de content-type. Campos de valor monetário em `FormData` vão como número puro
   em string (`String(value)`, ex. `"1234.56"`, mesma convenção do valor cru já usado no corpo
   JSON — Princípio VII), nunca formatado em BRL; o backend faz `Decimal(raw)` direto
   (`_decimal_from_form`, novo helper em `agenda_write.py`), não `parse_brl` (que espera o
   formato BRL "1.234,56" do Jinja e quebraria com esse formato).

2. **`_save_bounded_upload`** (novo, `routes.py`): generaliza o bloco duplicado 3× (checar
   tamanho ≤ N MB, `secure_filename`, `file.save(...)`, devolver path público ou `None`).
   `_save_nf_file` continua existindo com sua própria assinatura (chamado por nota fiscal e
   comprovante de gasto do reembolso) — não é fundido no helper genérico para não mexer numa
   função já usada em 3 pontos de código existentes fora do escopo desta fatia (criação/edição
   de evento); ele passa a chamar `_save_bounded_upload` por dentro, mesmo comportamento.

3. **Núcleo por fluxo** (funções de módulo em `routes.py`, prefixo `_`, mesma exceção
   "core-in-routes" de 151/152 — reusam `_save_nf_file`/`_save_bounded_upload`/
   `_save_file_upload` e os gates locais):
   - `_add_invoice_record(event, *, amount, issue_date, file_storage) -> EventInvoice | None`:
     mesma regra de "nova nota" já usada na reconciliação do form de venda (linha ~750 de
     `routes.py`) — rejeita só se amount/issue_date/arquivo vierem TODOS vazios; status
     `"emitida"` se há arquivo, senão `"a_emitir"`. NÃO mexe em notas existentes nem no
     `with_invoice` do evento — ação puramente aditiva (edição completa da "venda" continua
     Jinja-only, fora de escopo, ver spec Assumptions).
   - `_add_contract_record(event, *, file_storage) -> EventContract | None`: só arquivo
     (paridade exata com `_handle_add_contract` — amount/is_signed não são coletados nessa
     ação nem hoje no Jinja; só existem no fluxo de criação de evento, feature 152, fora
     desta fatia).
   - `_delete_contract_record(contract) -> None` / `_toggle_contract_signed(contract) ->
     None`: paridade com `_handle_delete_contract`/`_handle_toggle_contract_signed` — gate
     SUPERADMIN no endpoint, núcleo não sabe de `current_user` (mesmo padrão do item
     seguinte, pagamento).
   - `_add_payment_record(event, *, amount, file_storage) -> EventPayment | None`: exige
     ambos (paridade com `_handle_add_payment`).
   - `_edit_payment_amount(payment, *, amount) -> None` / `_delete_payment_record(payment) ->
     None`: paridade com `_handle_edit_payment`/`_handle_delete_payment` — gate SUPERADMIN
     fica no endpoint (mesmo padrão de `_is_superadmin()` já usado nos outros gates de
     `agenda_write.py`), núcleo não sabe de `current_user`.
   - `_add_reimbursement_record(event, *, description, amount, file_storage, created_by_id) ->
     EventReimbursement | None`: paridade com `_handle_add_reembolso` (arquivo opcional).
   - `_collect_reimbursement_record(reimbursement, *, collected_amount, file_storage,
     collected_by_id) -> bool`: paridade com `_handle_collect_reembolso` — `False` se já
     `is_collected` ou faltar arquivo/valor (mesmas duas validações de hoje).
   - `_delete_reimbursement_record(reimbursement) -> None`: paridade com
     `_handle_delete_reembolso` — gate SUPERADMIN no endpoint.
   - Todas devolvem `None`/`False` em vez de `flash()` — o wrapper Jinja mantém seu próprio
     `flash` como já faz hoje (essas funções NÃO substituem os `_handle_*` existentes, eles
     continuam iguais); o núcleo aqui é criado só para a API reusar a mesma regra de
     validação/gravação sem duplicá-la — ver item 4.

4. **Por que os `_handle_*` do Jinja não viram wrappers finos desta vez**: diferente de
   146-152 (onde a view Jinja inteira virava wrapper do núcleo), aqui os `_handle_*` continuam
   como estão porque cada um já é pequeno (~15-25 linhas) e teria custo de refatoração
   desproporcional ao ganho — o núcleo novo (`_add_payment_record` etc.) é chamado hoje só
   pela API; a *validação* (campos obrigatórios) e a *gravação* (criar o registro) são as
   partes que o núcleo compartilharia, mas extrair isso dos `_handle_*` exigiria também mudar
   onde o `flash()`/redirect acontece, tocando um fluxo que funciona e não está no escopo desta
   fatia. Trade-off aceito conscientemente: pequena duplicação de _regra_ (ex.: "amount e
   arquivo são obrigatórios") entre `_handle_add_payment` e `_add_payment_record`, cada uma
   com ~3 linhas — parity check automatizada (`verify_153`) garante que as duas concordam.

5. **`api_add_observation` aceita dois content-types**: quando `request.content_type` começa
   com `multipart/`, lê `obs_type`/`content`/`label` de `request.form` e arquivo de
   `request.files.get("image")` (novo caminho, só para `obs_type == "image"`); caso contrário
   mantém o `request.get_json()` de hoje (texto/link, sem mudança de contrato para quem já usa
   JSON). Endpoint único, sem duplicar rota — Princípio I.

6. **Endpoints REST** (`agenda_write.py`, gate entre parênteses):
   - `POST /api/events/<id>/invoices` (`_CAN_EDIT_EVENT`, mesmo gate da edição do evento):
     multipart `amount`, `issue_date` (`YYYY-MM-DD`), `file` — todos opcionais, rejeita 400 se
     os três vierem vazios.
   - `POST /api/events/<id>/contracts` (`_CAN_EDIT_EVENT`): multipart `file` (obrigatório) →
     400 `{"file": "Selecione o arquivo do contrato"}` se ausente/vazio.
   - `DELETE /api/contracts/<id>` (SUPERADMIN): sem corpo, 200 com o evento atualizado.
   - `POST /api/contracts/<id>/toggle-signed` (SUPERADMIN): sem corpo, inverte `is_signed`,
     200 com o evento atualizado.
   - `POST /api/events/<id>/payments` (`_CAN_EDIT_EVENT`): multipart `amount`, `file`, ambos
     obrigatórios.
   - `PATCH /api/payments/<id>` (SUPERADMIN): JSON `{"amount": number}`.
   - `DELETE /api/payments/<id>` (SUPERADMIN): sem corpo, 200 com o evento atualizado (mesmo
     padrão de `_event_detail_json`).
   - `POST /api/events/<id>/reimbursements` (`_CAN_EDIT_EVENT`): multipart `description`,
     `amount` obrigatórios, `file` opcional.
   - `POST /api/reimbursements/<id>/collect` (`_CAN_EDIT_EVENT`): multipart
     `collected_amount`, `file`, ambos obrigatórios; 400 se já `is_collected` (checado DEPOIS
     do gate).
   - `DELETE /api/reimbursements/<id>` (SUPERADMIN): sem corpo, 200 com o evento atualizado.

   **Correção durante a implementação**: `_handle_add_contract`/`_handle_add_payment`/
   `_handle_add_reembolso`/`_handle_collect_reembolso` não checam papel por dentro — mas o
   dispatcher `event_detail` (Jinja) gateia TODO POST daquela rota por `_CAN_EDIT_EVENT` antes
   de despachar para qualquer `_handle_*` (`app/calendar/routes.py`, linha do `if not
   _can_edit and not _can_tech: abort(403)`). Esse é o gate efetivo real — a primeira leitura
   deste plano, olhando só os handlers isoladamente, tinha concluído erradamente "sem gate" para
   os quatro. Corrigido nos quatro endpoints correspondentes.
   - `POST /api/events/<id>/observations` (inalterado no gate — `@login_required`, sem papel):
     `obs_type=image` exige `file`.
   - Todos devolvem `_event_detail_json(event)` no sucesso (200), igual aos endpoints de
     observação/logística/confirm já existentes — o frontend já sabe substituir o cache
     inteiro do evento com essa resposta.

7. **Frontend — `apiFetch` aceita `FormData`**: hoje `apiFetch` sempre define
   `Content-Type: application/json`, o que quebra multipart (o browser precisa gerar o
   `boundary` sozinho no header). Ajuste mínimo: se `options.body instanceof FormData`, não
   inclui o header `Content-Type` (deixa o `fetch` nativo definir); caso contrário,
   comportamento idêntico ao de hoje. Único ponto de mudança (Princípio I — toda tela usa o
   mesmo `apiFetch`).

8. **Frontend — telas**: cada novo bloco (`NotasFiscais`, `Contratos`, form de pagamento,
   form de reembolso, form de imagem em observação) segue exatamente o padrão visual já
   estabelecido em `Pagamentos`/`Reembolsos`/`AddObservationForm` (mesmo `Section`, mesmas
   classes Tailwind, `<input type="file">` nativo sem componente de upload dedicado — YAGNI
   para um único arquivo por ação). Link de abrir/baixar usa `assetUrl(path)` (já existe,
   usado hoje em `obs.image_url`). Edição de valor do pagamento: input inline + botão
   "Salvar" (mesmo padrão dos outros pequenos forms desta tela, sem modal).

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|---------------------------------------|
| Núcleo em `routes.py` (não em módulo `ops` novo) | `_save_nf_file`/`_save_file_upload`/gates locais são reusados por outras rotas dentro de `routes.py` | Mover para módulo novo duplicaria os helpers de upload ou exigiria tocar pontos de chamada fora de escopo — mesma situação já aprovada em 146-152 |
| `_handle_*` do Jinja NÃO viram wrappers finos do núcleo novo (diferente de 146-152) | Cada `_handle_*` já é pequeno e funcional; extrair validação+gravação para o núcleo exigiria também mover onde `flash()`/redirect acontece, tocando fluxo fora de escopo | Fazer o wrapper fino duplicaria o risco de regressão no Jinja para um ganho pequeno (regra de ~3 linhas); parity check automatizada cobre a divergência residual |
| `api_add_observation` aceita dois content-types no mesmo endpoint | Evita duplicar rota/regra de negócio (Princípio I) só para suportar imagem | Endpoint separado (`/observations/image`) duplicaria o gate e a resposta; mudar o endpoint existente para multipart-only quebraria o cliente JSON já em produção |
