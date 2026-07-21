# Implementation Plan: criar evento em React (152)

**Branch**: `152-criar-evento-react` | **Date**: 2026-07-21 | **Spec**: [spec.md](spec.md)

## Summary

Migra a criação de evento (`GET/POST /events/new`) para React + API JSON, no padrão de 146-151:
núcleo compartilhado (funções puras, sem `request`/`flash`/`current_user` dentro delas), reusado
por um wrapper Jinja fino (comportamento inalterado, incl. os campos de arquivo que ficam só no
Jinja) e por endpoints JSON novos. Diferença de escala: `create_event` tem ~500 linhas e ~9 grupos
de dados — o núcleo é decomposto em várias funções pequenas (Princípio II, máximo ~30 linhas cada),
uma por grupo (evento essencial, financeiro, elenco, orçamento, vínculos). Upload de arquivo
continua **fora** do contrato JSON desta fatia (nota fiscal/contrato/pagamento/reembolso/
observação-imagem) — a criação de `EventInvoice`/`EventReimbursement`/observação de texto-ou-link
já não depende de arquivo hoje; contrato e comprovantes de pagamento (que hoje só se criam SE há
arquivo) ficam inteiramente fora do núcleo, só no wrapper Jinja.

**Correção de design em relação à primeira leitura do plano**: o núcleo NÃO vai para um módulo
`ops` novo (diferente de 146-150). Investigação durante a implementação mostrou que os helpers que
`create_event` precisa (`_build_start_end`, `_ensure_coordinator`, `_ensure_sound_technician`,
`_lookup_sp_status`, `_fetch_travel_data`, `_talent_time_conflict`, `_compute_performer_caches`,
`_parse_client_pairs`, `_primary_client_id`) são reusados por VÁRIAS outras rotas dentro de
`routes.py` (edição de evento, venda, orçamento) — movê-los para um módulo novo obrigaria a tocar
~15 pontos de chamada fora do escopo desta fatia, ou duplicar lógica (proibido pelo Princípio I).
Mesma situação e mesma solução da feature 151: o núcleo fica como funções de módulo em
`app/calendar/routes.py` (prefixo `_`, sem `request`/`flash`), reusando os helpers locais
diretamente sem import cíclico; a API importa de `routes.py` (mesma direção `api → routes` já
usada para os gates e para 151).

## Technical Context

Igual à 146-151: Python/Flask + React (Vite/TS/TanStack Query/react-hook-form+zod); sem dependência
nova (react-hook-form e zod já instalados desde a Fundação, usados hoje só na `LoginPage`).
Verificação com test client Flask contra `manto_local`, Google mockado (`insert_event`), requests
fora de `app_context`.

**Lookups já JSON, reusados sem mudança** (Princípio I — não duplicar):
`/clientes/search` (client picker, feature 114) e `/formularios/respostas/search` (form response
picker, feature 118) já existem e devolvem JSON consumível direto pelo React — nenhum endpoint novo
para eles, só os componentes de busca no frontend.

**Sem lookup JSON hoje** (precisa de endpoint novo, GET, só leitura):
fichas de figurino, vendedores, talentos atribuíveis (hoje só passados como contexto de template) e
o prefill calculado a partir de um `OrcamentoHistory` (transporte, acréscimos, cachês por duração).

## Constitution Check

- **I (reutilizar)**: núcleo em funções de módulo dentro de `app/calendar/routes.py` (mesmo padrão
  de 151), reusando `_build_start_end`/`_ensure_coordinator`/`_ensure_sound_technician`/
  `_lookup_sp_status`/`_fetch_travel_data`/`_talent_time_conflict`/`_compute_performer_caches`/
  `_parse_client_pairs`/`_primary_client_id` já existentes, sem duplicar nada. Lookups já JSON
  (`/clientes/search`, `/formularios/respostas/search`) reaproveitados sem endpoint novo.
  `CLIENT_RELATION_TIPOS`/`ACRESCIMO_TIPO_BV`/`_CAN_CREATE` importados de `constants.py`, não
  redefinidos.
- **II (padrões de código)**: `create_event` (~500 linhas, 1 função) é decomposto em ~10 funções
  pequenas e testáveis no núcleo — nenhuma delas orquestra HTTP. Type hints/docstrings em todas.
- **III (API first)**: os 3 endpoints novos são 100% JSON; a view Jinja continua existindo (ainda
  não é hora de removê-la — coexistência), mas vira wrapper fino sobre o mesmo núcleo.
- **IV (não quebrar)**: paridade de banco verificada contra `manto_local`; POST Jinja segue 302
  inalterado; nenhuma tabela/comportamento muda para quem ainda usa o Jinja.
- **V (feedback)**: `react-hook-form` + `zod` no formulário React, erros de campo mapeados de
  `fields` (resposta 400) sem apagar o que foi digitado; botão de criar desabilita + mostra
  "Criando..." enquanto pendente; toasts de erro amigáveis (nunca a mensagem crua do Google).
- **VII (monetário)**: todos os campos de valor usam `<MoneyInput/>` de `@manto/money` (já existe,
  usado nos KPIs da `EventDetailPage`) — fonte única, nenhuma formatação nova.
- **VIII (mobile-first)**: tela nova conferida em 320–430px (formulário longo — testar scroll
  vertical, não horizontal).
- **IX (movimento)**: transições de abrir/fechar seções do formulário (ex.: bloco de cortesia/
  permuta escondendo os campos financeiros) via Framer Motion, respeitando `useReducedMotion()`.

Uma violação justificada — ver Complexity Tracking: núcleo em `routes.py` (não em módulo `ops`
dedicado), mesma exceção já aprovada em 151, agora por acoplamento a helpers multi-uso em vez de
helpers do Google.

## Project Structure

```text
app/calendar/routes.py             # + núcleo como funções de módulo (prefixo _): validação +
                                    #   gravação, decomposto por grupo (evento essencial,
                                    #   financeiro/acréscimos, elenco/pré-escala, coordenador/som,
                                    #   prefill de orçamento, clientes/pré-contrato/reembolso/
                                    #   observações). Funções puras (sem request/flash). create_event
                                    #   vira wrapper fino sobre esse núcleo.
app/api/agenda.py                  # + GET /api/events/new/options (fichas/vendedores/talentos/
                                    #   tipos de relação de cliente)
                                    # + GET /api/events/new/prefill?orcamento_id=<id>
app/api/agenda_write.py            # + POST /api/events (cria; 201 serialize_event_detail; 400
                                    #   fields; 502 falha do Google)
frontend/apps/internal/src/
├── lib/eventCreate.ts             # NOVO — useEventCreateOptions, useOrcamentoPrefill,
│                                   #   useCreateEvent (react-hook-form + zod no componente)
├── components/ClientPicker.tsx    # NOVO — busca/seleciona clientes (consome /clientes/search)
├── components/FormResponsePicker.tsx  # NOVO — busca/seleciona pré-contrato (consome
│                                   #   /formularios/respostas/search)
└── pages/EventCreatePage.tsx      # NOVO — formulário completo (US1-US5), seções expansíveis
App.tsx                            # + rota /events/new
AgendaPage.tsx                     # + botão/link "Novo evento" → /events/new
scripts/db/verify_152_criar_evento.py  # NOVO: paridade API×Jinja, Google mockado
```

## Design Decisions

1. **Núcleo em `app/calendar/routes.py`** — funções de módulo (prefixo `_`, puras, sem `request`/
   `flash`/`current_user`), cada uma cobrindo uma User Story, colocadas perto de `create_event`:
   - `_build_event_create_options() -> dict` (US1/US3): fichas de figurino, vendedores, talentos
     atribuíveis, `CLIENT_RELATION_TIPOS`. Reusa as mesmas queries de hoje em `create_event` (GET).
   - `_build_orcamento_prefill(orcamento_id: int | None) -> dict` (US4): mesmo cálculo de hoje
     (chama `_lookup_sp_status`/transporte, acréscimo legado, `_compute_performer_caches`); `{}` se
     id ausente/inválido.
   - `_validate_event_core(data: dict) -> dict[str, str]` (US1/US2): título, data, horários
     (usa `_build_start_end`), financeiro (respeitando cortesia/permuta), vendedor, parcelamento —
     devolve mapa campo→mensagem (vazio = válido). Substitui a lista de `errors` do Jinja por um
     mapa, para o React destacar o campo exato (Princípio V); o wrapper Jinja converte o mapa em
     lista para manter o flash atual inalterado.
   - `_create_event_row(data: dict, *, google_event_id: str, gc_title: str) -> CalendarEvent` (US1/
     US2): monta e grava `CalendarEvent` (sem elenco/vínculos ainda), incl. `EventInvoice` quando
     `with_invoice` (sem arquivo — já é opcional hoje), acréscimos tipados (`EventAcrescimo`),
     detecção fora-de-SP (`_lookup_sp_status`/`_fetch_travel_data`).
   - `_create_roles_from_input(event, characters: list[dict], *, orc_caches, dur_idx,
     figurino_by_name, valid_talent_ids) -> list[tuple[int, str]]` (US3): cria `EventRole` por
     personagem (auto-match de figurino, pré-escala sem duplicar talento), devolve
     `assigned_now` para o aviso de conflito pós-commit.
   - `_apply_default_roles(event, *, event_type, came_from_orcamento, coordinator_talent_id,
     valid_talent_ids)` (US3): chama `_ensure_coordinator`/`_ensure_sound_technician` (SHOW), mesma
     regra condicional de hoje.
   - `_create_client_links(event, client_pairs: list[tuple[int, str]])` (US5): `EventClient` +
     `_primary_client_id`.
   - `_link_form_response(form_response_id: int | None, event_id: int)` (US5).
   - `_create_reembolso_entry(event, *, description, amount, invoice_file_path=None,
     created_by_id)` (US5): `invoice_file_path` sempre `None` vindo da API; o wrapper Jinja passa o
     caminho salvo por `_save_nf_file`.
   - `_create_observations_from_input(event, observations: list[dict])` (US5): grava texto/link;
     entradas `obs_type == "image"` são ignoradas nesta fatia (paridade com o padrão da 150) — o
     wrapper Jinja continua salvando a imagem ANTES de chamar esta função (fora do núcleo) e passa o
     `file_path` já resolvido dentro do próprio item da lista quando existir.
   - `_check_talent_conflicts(assigned_now, start, end, event_id, talents) -> list[str]` (US3):
     mesmo aviso não-bloqueante pós-commit de hoje (usa `_talent_time_conflict`).
   - `_create_event_core(data: dict, *, google_event_id, gc_title, actor_name, actor_id) ->
     tuple[CalendarEvent, list[str]]`: orquestrador único que chama as funções acima em sequência
     (evento → clientes/pré-contrato → acréscimos/nota fiscal/fora-SP → elenco/pré-escala →
     coordenador/som → reembolso → observações → `EventLog` + `_sync_commission_payment` + commit →
     `_notify_ensaio_team` se `needs_rehearsal` → `_check_talent_conflicts`), devolvendo o evento e
     os avisos de conflito. É o único ponto que o wrapper Jinja e o endpoint API chamam — mesmo
     formato de entrada única que `_delete_event_flow`/`_sync_single_event_flow` (151).
2. **Wrapper Jinja** (`create_event`): GET monta o contexto chamando `build_create_options` +
   `build_orcamento_prefill`; POST faz o parsing de `request.form`/`request.files` (incl. os campos
   de arquivo que ficam só aqui: nota fiscal, contrato, comprovantes, reembolso, imagem de
   observação), chama as funções do núcleo na mesma ordem de hoje, e mantém exatamente os mesmos
   flashes/redirects/re-render de erro. Falha do Google continua abortando antes de qualquer
   gravação (`insert_event` é chamado pelo wrapper, que passa `google_event_id`/`gc_title` prontos
   para `create_event_record` — o núcleo não sabe nada de Google).
3. **Endpoints REST**:
   - `GET /api/events/new/options` (`agenda.py`, `@api_login_required`, gate `_CAN_CREATE`) →
     `build_create_options()`.
   - `GET /api/events/new/prefill?orcamento_id=<id>` (`agenda.py`, mesmo gate) →
     `build_orcamento_prefill(...)`; `{}` se ausente/inválido (nunca erro).
   - `POST /api/events` (`agenda_write.py`, mesmo gate): corpo JSON com os mesmos grupos de campos
     do Jinja (sem nenhum campo de arquivo). `validate_event_core` → se não vazio, `json_error(...,
     400, fields=...)`. Válido → chama `insert_event` (Google); falha → `json_error("Não foi
     possível criar o evento na Agenda do Google agora...", 502)`. Sucesso → roda as funções do
     núcleo na mesma ordem do wrapper Jinja (sem os blocos de arquivo), commit, devolve `201` com
     `serialize_event_detail` do evento novo + `warnings` (conflitos de talento, se houver) no
     corpo, no mesmo formato de leitura da 145.
4. **Frontend**:
   - `lib/eventCreate.ts`: `useEventCreateOptions()` (GET, staleTime longo — dados mudam pouco),
     `useOrcamentoPrefill(orcamentoId)` (GET, `enabled: !!orcamentoId`), `useCreateEvent()`
     (POST `/api/events`, `onSuccess` → `navigate("/events/:id")` + invalida `["agenda"]`).
   - `EventCreatePage.tsx`: formulário com `react-hook-form` + schema `zod` (campos essenciais
     sempre visíveis; bloco financeiro colapsa quando cortesia/permuta ligado — Framer Motion;
     lista dinâmica de personagens; seleção de duração quando `orcamento_id` na URL). Erros de
     campo vêm do 400 (`fields`) e são mapeados para `setError` do react-hook-form.
   - `ClientPicker.tsx`/`FormResponsePicker.tsx`: componentes de busca com debounce, consumindo os
     endpoints Jinja já-JSON existentes (`/clientes/search`, `/formularios/respostas/search`) — sem
     endpoint `/api/*` novo para eles (Princípio I).
   - Rota `/events/new` (`App.tsx`) + link "Novo evento" na `AgendaPage`.
5. **Verificação** (`verify_152_criar_evento.py`): mocka `insert_event`; cobre as 5 User Stories por
   paridade — cria o mesmo evento via API e via Jinja com o mesmo input (exceto arquivos) e compara
   linha a linha `CalendarEvent`/`EventRole`/`EventClient`/`EventAcrescimo`/`EventInvoice`/
   `EventReimbursement`/`EventObservation`; cobre os erros de validação (título/data/horário/
   financeiro/vendedor/parcelamento), falha do Google (nada grava), talento duplicado/conflito,
   `orcamento_id` inválido, observação de imagem descartada. Jinja 302; API 200/201/400/403/502.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|---------------------------------------|
| Núcleo em `routes.py` (não em módulo `ops` novo, diferente de 146-150) | `_build_start_end`, `_ensure_coordinator`, `_ensure_sound_technician`, `_lookup_sp_status`, `_fetch_travel_data`, `_talent_time_conflict`, `_compute_performer_caches`, `_parse_client_pairs`, `_primary_client_id` são reusados por outras rotas dentro de `routes.py` (edição de evento, venda, orçamento) | Mover para um módulo `ops` obrigaria a tocar ~15 pontos de chamada fora do escopo desta fatia (risco de regressão em telas não relacionadas) ou duplicar a lógica (proibido pelo Princípio I) — mesma situação e mesma solução já aprovada em 151 |
