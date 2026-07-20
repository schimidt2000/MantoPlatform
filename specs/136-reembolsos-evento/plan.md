# Implementation Plan: Reembolsos de Despesas do Evento (136)

**Branch**: `136-reembolsos-evento` | **Date**: 2026-07-17 | **Spec**: [spec.md](./spec.md)

## Summary

Nova tabela `EventReimbursement` + 3 ações no dispatch já existente de `event_detail`
(`add_reembolso`, `collect_reembolso`, `delete_reembolso`), reaproveitando ponto a ponto o
fluxo já existente de `EventPayment` (comprovante de pagamento): mesmo padrão de
formulário (valor + arquivo), mesma listagem, mesma restrição de exclusão a SUPERADMIN.
Checkbox opcional na criação do evento (mesmo padrão de `needs_rehearsal`). Painel
"Reembolsos pendentes" na home (mesmo padrão de "Cobranças pendentes"). Botão "💸 Cobrar
reembolsos" no menu de ferramentas (mesmo padrão de "💰 Cobrança" — `buildCobranca()` +
`copiar()`).

## Technical Context

**Stack**: o existente (Flask + SQLAlchemy + Jinja2 + JS vanilla). **Storage**: 1 tabela
nova, aditiva; 1 subpasta de upload nova (`instance/uploads/reembolsos`), mesmo padrão de
`UPLOAD_PAYMENTS`/`UPLOAD_CONTRACTS`.

**Arquivos**:

- `app/models.py` — `EventReimbursement`: `id`, `event_id` (FK), `description`
  (`String(200)`), `amount` (`Numeric(12,2)`, valor a cobrar), `invoice_file_path`
  (`String(300)`, nullable — nota fiscal do gasto original), `created_at`,
  `created_by_id` (FK User, nullable), `collected_at` (nullable — `None` = pendente),
  `collected_amount` (`Numeric(12,2)`, nullable), `receipt_file_path` (`String(300)`,
  nullable — comprovante do reembolso recebido), `collected_by_id` (FK User, nullable).
  Propriedade `is_collected` (`collected_at is not None`).
- `migrations/versions/<hash>_event_reimbursements.py` — cria `event_reimbursements`.
- `app/__init__.py` — `UPLOAD_REEMBOLSOS = os.path.join(_instance, "uploads",
  "reembolsos")` + `os.makedirs(...)`, mesmo padrão de `UPLOAD_PAYMENTS` (linhas 212-222).
- `app/calendar/routes.py`:
  - `_handle_add_reembolso(event, tz_sp)` — lê `reembolso_description`/
    `reembolso_amount` (obrigatórios) e `reembolso_invoice_file` (opcional, mesmo limite
    de 10MB de `_handle_add_payment`); cria `EventReimbursement`; loga em `EventLog`.
  - `_handle_collect_reembolso(event, tz_sp)` — lê `reembolso_id`,
    `reembolso_collected_amount` (obrigatório) e `reembolso_receipt_file` (obrigatório,
    mesmo limite 10MB) — mesma validação de `_handle_add_payment`; seta
    `collected_at=datetime.now(tz_sp)`, `collected_amount`, `receipt_file_path`,
    `collected_by_id=current_user.id`; loga em `EventLog`.
  - `_handle_delete_reembolso(event, tz_sp)` — `_is_superadmin()`-only, mesmo padrão de
    `_handle_delete_payment`; loga em `EventLog`.
  - As 3 entram em `_EVENT_ACTIONS` (dict já existente, linha ~1348).
  - `event_detail()`: query `reembolsos = EventReimbursement.query.filter_by(
    event_id=event.id).order_by(EventReimbursement.created_at.desc()).all()`;
    `reembolsos_pendentes_total = sum(r.amount for r in reembolsos if not r.is_collected)`;
    ambos passados ao template.
  - `create_event()`: lê checkbox `has_reembolso` + `reembolso_description`/
    `reembolso_amount`/`reembolso_invoice_file` (mesmo padrão de leitura de
    `needs_rehearsal`); se marcado e descrição+valor preenchidos, cria o
    `EventReimbursement` logo após o evento ser commitado (mesmo ponto onde
    `payment_files[]`/`payment_amounts[]` já são processados na criação, linha ~2973).
  - `_clear_event_side_tables()` (linha 168-180, feature 122) ganha
    `EventReimbursement.query.filter_by(event_id=event_id).delete()`.
- `app/templates/event_create.html` — checkbox "Este evento terá reembolso de despesas da
  cliente?" (mesmo padrão HTML de `needs_rehearsal`, linha 260-267) revelando (JS simples
  de mostrar/esconder, sem framework) um bloco com descrição + valor (`.brl-input`) + nota
  fiscal opcional — só preenchido se a comercial quiser já deixar registrado na criação
  (FR-001, "opcional — pular não impede criar o evento").
- `app/templates/event_detail.html` — novo painel "💸 Reembolsos", inserido logo após o
  painel "Comprovante de pagamento" (mesmo `grid-2`/mesmo `{% if eff_has_role('COMERCIAL',
  'SUPERADMIN') %}` que já engloba toda a seção "Dados da venda", linha 157-2058 — nenhum
  gate novo necessário):
  - Formulário "Adicionar reembolso" (descrição + valor + nota fiscal opcional) — mesmo
    layout do formulário "Comprovante de pagamento".
  - Lista de reembolsos: descrição, valor, badge Pendente/Cobrado (mesmo estilo
    `badge-gold`/`badge-green` de "Falta R$.../Quitado ✓"), link "Ver nota fiscal" quando
    houver. Cada pendente tem um botão "Marcar como cobrado" que revela um mini-formulário
    inline (mesmo toggle `f.style.display = ... 'flex' : 'none'` já usado no formulário de
    editar comprovante) com valor recebido (pré-preenchido com o valor a cobrar) +
    comprovante obrigatório. Cobrados mostram data + "Ver comprovante". SUPERADMIN vê
    "Excluir" (mesmo padrão do comprovante).
- `app/templates/event_detail.html` (bloco `page_actions`, dentro do mesmo
  `eff_has_role('COMERCIAL', 'SUPERADMIN')` que já contém `#btn-cobranca`) — novo botão
  `#btn-cobranca-reembolso`, mesmo padrão visual de desabilitado
  (`{% if not reembolsos_pendentes_total %}disabled...{% endif %}`); no script já existente
  do arquivo, `DATA` ganha `reembolsoTotal`/`reembolsoLinhas` (uma linha por reembolso
  pendente: descrição + valor), nova função `buildCobrancaReembolso()` (mesmo estilo de
  `buildCobranca()`) e wiring no `DOMContentLoaded` já existente
  (`copiar(buildCobrancaReembolso(), btn)`).
- `app/__init__.py` (home route) — nova query gated por `show_comercial` (mesmo bloco de
  `pending_payments`, linha ~604-674): `EventReimbursement.query.filter_by(collected_at=
  None).join(CalendarEvent).order_by(CalendarEvent.start_at.asc().nulls_last(),
  EventReimbursement.created_at.asc()).all()`, sem filtro de `task_cutoff` (reembolso
  pendente continua relevante mesmo se o evento já passou — Edge Case do spec). Passado
  como `reembolsos_pendentes=...`.
- `app/templates/home.html` — novo bloco "Reembolsos pendentes" dentro do
  `sector-panel` Comercial (mesmo `task-row`/estilo de "Cobranças pendentes", linha
  533-565), somado a `_total_comercial` e incluído na condição combinada de estado vazio.

**Testing**: verificação funcional vs `manto_local` — criar evento com reembolso marcado
na criação (aparece pendente); adicionar reembolso manual num evento existente (mais de
um por evento); marcar como cobrado (valor + comprovante) e conferir que some da home e do
botão de cobrança daquele evento; botão de cobrança desabilitado sem pendências, habilitado
com pendências e texto copiado bate com o esperado; SUPERADMIN exclui, não-SUPERADMIN não
consegue; excluir evento com reembolso registrado não quebra; permissão igual à das demais
ferramentas comerciais do evento.

## Constitution Check

| Princípio | Avaliação |
|---|---|
| I. Reutilizar | ✅ Todo o desenho é uma releitura de 4 padrões já existentes e testados: `EventPayment` (add/collect/delete + upload), `needs_rehearsal` (checkbox na criação), "Cobranças pendentes" (bloco de pendência na home) e `buildCobranca()`/`copiar()` (botão de cobrança no menu de ferramentas). Nenhum mecanismo novo é inventado. |
| III. Permissões | ✅ Reembolsos vivem dentro do mesmo bloco `eff_has_role('COMERCIAL', 'SUPERADMIN')` que já engloba "Dados da venda" — nenhuma regra de acesso nova; exclusão restrita a SUPERADMIN, mesma restrição já aplicada a `delete_payment`/`edit_payment`. |
| IV. Não quebrar | ✅ Aditivo — tabela nova, 3 ações novas no dispatch existente, 1 checkbox a mais na criação, 1 painel a mais no evento, 1 bloco a mais na home, 1 botão a mais no menu. `_clear_event_side_tables` ganha uma linha (mesmo padrão da feature 122) para não quebrar exclusão de evento. |
| V. UI/UX | ✅ Botão de cobrança segue o mesmo padrão de desabilitado com explicação (feature 129/Cobrança); marcar como cobrado usa o guard global de feedback ao clicar (feature 124) por ser `<form>` comum; estado vazio explícito na home (FR-009) e na lista do evento. |
| VI. Planejar | ✅ Este plano, escrito depois de mapear os 6 pontos de reaproveitamento (modelo, checkbox de criação, bloco de pendência da home, botão de cobrança, upload de arquivo financeiro, gating de permissão) antes de qualquer código. |
| VIII. Mobile-first | N/A — telas internas (evento, home, criação de evento), mesmo critério já usado nas demais telas internas desta sessão. |

**Gate: PASS.**

## Decisões

1. **`collected_amount` separado de `amount`**: o valor a cobrar (registrado na criação
   do reembolso) e o valor efetivamente recebido (confirmado na cobrança) são campos
   distintos — replica o pedido explícito do usuário ("da mesma forma que funciona a
   parte de adicionar pagamentos", que sempre pede o valor de novo no momento do
   recebimento) e permite que o valor recebido divirja do valor originalmente registrado
   sem perder o histórico de quanto era esperado.
2. **Sem caminho de reverter "cobrado" → "pendente" pela interface**: não foi pedido
   (spec, Assumptions) e o próprio fluxo de comprovante de pagamento, que serve de
   referência direta, também não tem esse caminho — mantém a superfície nova do mesmo
   tamanho da referência que ela copia.
3. **Reembolsos pendentes na home sem filtro de data**: ao contrário de "Cobranças
   pendentes" (que olha só eventos a partir de `task_cutoff`), um reembolso continua
   sendo uma dívida da cliente mesmo depois do evento já ter passado — filtrar por data
   esconderia pendências reais (Edge Case do spec).
4. **Upload de nota fiscal/comprovante segue o padrão de `EventPayment`/`EventContract`
   (`secure_filename` + `file.save()` direto), não `app/storage.py::save_file()`**: é o
   padrão já estabelecido para documentos financeiros do evento (contratos, comprovantes
   de pagamento) — manter os arquivos financeiros do evento todos na mesma convenção,
   em vez de introduzir uma terceira forma de salvar arquivo no mesmo módulo.
