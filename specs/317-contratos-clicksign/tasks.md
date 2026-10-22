---
description: "Tasks da feature 317 — contrato da ClickSign ligado à venda e Cobrar contrato"
---
# Tasks: Feature 317 — contrato da ClickSign ligado à venda e "Cobrar contrato"

**Input**: `specs/317-contratos-clicksign/` — spec.md, plan.md, research.md, data-model.md, contracts/api.md, quickstart.md

**Verificação (OBRIGATÓRIA — Princípio VIII)**: `specs/317-contratos-clicksign/verify_317.py` contra `manto_local`, com
dublê da ClickSign e disjuntor de rede; escrito na Foundational, falhando pelos motivos certos; primeira rodada salva em
`verify_317_primeira_falha.txt`.

**Ambiente de todo comando que chama `create_app()`**: `$env:DATABASE_URL = (Get-Content .local-db-url -Raw).Trim();
$env:FLASK_ENV = 'development'; $env:MANTO_SEM_THREADS = '1'; $env:PYTHONUTF8 = '1'` e o Python
`C:\Users\schim\Desktop\Manto_Platform\.venv\Scripts\python.exe`, a partir de `C:\tmp\mp317`.

## Formato: `[ID] [P?] [Story] Descrição`

---

## Phase 1: Setup

- [X] T001 Constantes em `app/constants.py`: tipos (`CLICKSIGN_TIPO_CLIENTE/ARTISTA/OUTRO`), vínculos
      (`ligado/a_conferir/descartado/fora`), origens, motivos de "a conferir", situações
      (`assinado/assinado_manual/aguardando/vencido/recusado/sem_contrato`), rótulos pt-BR, motivos de bloqueio do
      botão (textos da spec, História 2 cenário 3), régua do prazo (`CONTRATO_PRAZO_VERMELHO_ATE_DIAS=1`,
      `CONTRATO_PRAZO_AMARELO_ATE_DIAS=3`), `CONTRATO_SEM_CONTRATO_JANELA_DIAS=30`, autor `"ClickSign (automático)"`
- [X] T002 Config em `app/config.py`: `_suppress_clicksign()` no molde de `_suppress_calendar_*` (envs
      `CLICKSIGN_SUPPRESS_CALLS`, `CLICKSIGN_ALLOW_LOCAL_CALLS`; banco local → travado) e `CLICKSIGN_SUPPRESS_CALLS =
      _suppress_clicksign()`, `CLICKSIGN_ACCESS_TOKEN = os.getenv(..., "").strip()`, `CLICKSIGN_API_BASE` (default
      `https://app.clicksign.com/api/v3`), `CLICKSIGN_SYNC_INTERVAL` (1800), `CLICKSIGN_SYNC_ENABLED` (true),
      `CLICKSIGN_AVISO_SINCRONO` (false); `render.yaml` ganha `CLICKSIGN_ACCESS_TOKEN` com `sync: false`
- [X] T003 [P] Cliente HTTP `app/integracoes/clicksign_client.py` (sem Flask; molde `infinitepay_client.py` da 310):
      exceções `ClicksignError/Indisponivel/Recusou/Travada`, `TIMEOUT=(10, 30)`, `_get/_post/_delete(..., travada=True,
      token, base)`, respeito a `X-Rate-Limit-Remaining` (< 5 → dorme até o reset), funções `listar_envelopes(*,
      modificado_desde, modificado_ate, criado_desde, criado_ate, status, pagina)`, `signatarios(envelope_id)`,
      `eventos(envelope_id)`, `documentos(envelope_id)`, `documento(envelope_id, document_id)`, `baixar(url)` (S3, sem
      token), `listar_webhooks()`, `criar_webhook(url, eventos)`, `remover_webhook(id)`; mesmo commit da T002 (XIV)

---

## Phase 2: Foundational (bloqueia as histórias)

- [X] T004 Modelos em `app/models.py`: `ClicksignDocumento` (com `anexo_pendente`), `ClicksignDesvinculo`,
      `ClicksignCobranca` e as 7 colunas novas de `SiteSetting` (com `clicksign_sync_pendente`), conforme `data-model.md` (índice parcial também no `__table_args__`; docstrings com o porquê)
- [X] T005 Migration manual `migrations/versions/<rev>_contratos_clicksign.py` (`down_revision = "c5d2f7a9e306"`,
      aditiva, upgrade/downgrade completos); `flask db upgrade` no `manto_local`; `flask db heads` com uma cabeça só
- [X] T006 Núcleo puro `app/contratos/__init__.py` + `app/contratos/contratos_ops.py`: `normalizar_nome` (NFC, sem
      `.pdf`, sem ` (N)`), `ler_nome(nome) -> NomeLido(data, telefone, email, tema, razao)` aceitando `DD-MM-AAAA`,
      `DDMMAAAA`, `DMMAAAA`, festa e corporativo; `classificar(nome) -> tipo`; `canal_do_signatario(communicate_events)`;
      `vigente(documentos)`; `situacao_da_venda(vigente, assinado_manual) -> Situacao`; `cor_do_contrato(situacao,
      prazo, data_evento, hoje)`; `selo_do_contrato`; `venda_entra(principal, corte)` (cortesia entra);
      `escolher_candidato(lido, candidatos) -> (event_id | None, motivo)` com desempate pelo tema — sem I/O
- [X] T007 **`specs/317-contratos-clicksign/verify_317.py`** — os 26 cenários da spec, molde `verify_299.py`/
      `verify_313.py`: disjuntor em `socket.socket.connect` e `socket.create_connection` ANTES de importar o app (anota
      escapes); dublê `ContaClickSign` que substitui as funções de `clicksign_client` com envelopes/sinais/eventos/arquivo
      em memória; `CLICKSIGN_AVISO_SINCRONO=1`; semeadura `_evento/_cliente/_formulario` com prefixo próprio; login só
      por `POST /api/auth/login`; escrita conferida por conexão separada; limpeza no `finally`. Rodar e salvar
      `verify_317_primeira_falha.txt` (falham os cenários do núcleo ainda não construído; 1–2 e 8 já passam com a T006)

**Checkpoint**: migração aplicada, núcleo puro pronto, verify falhando pelos motivos certos.

---

## Phase 3: História 1 — O contrato aparece ligado à venda certa, sozinho (P1) 🎯 MVP

**Verificação**: cenários 1–8, 12–15, 23–25 em PASS.

- [X] T008 [US1] `app/contratos/sincronizar_ops.py`: `candidatos_da_venda(lido)` (vendas vivas — `venda_entra`, que
      filtra ENSAIO/🟧/loja virtual de `vendas_desde` e mantém cortesia — com qualquer dia do grupo na data; telefones em
      LOTE de `CalendarEvent.client`, contratantes `EventClient` e `FormResponse.contact_phone` ligado, comparados pela
      chave DDD + últimos 8 dígitos; tema por `pre_evento_ops`), respeitando `clicksign_desvinculos` e cancelado;
      `aplicar_envelope(env, cliente)` = upsert por `envelope_id`, signatário/canal na 1ª vez, eventos só quando
      `closed`/`canceled` (assinado_em, recusado), vínculo só para documento novo ou `a_conferir` automático; vigente e
      assinado-à-mão pelo grupo inteiro (`group_events`), excluindo os `contrato_anexo_id`
- [X] T009 [US1] `sincronizar_ops.anexar_assinado(doc)`: só com `anexo_pendente`; busca `links.files.signed`, baixa,
      embrulha em `FileStorage(io.BytesIO(...))` e usa `routes._add_contract_record(event, file_storage=…,
      is_signed=True)` no evento ligado; `EventLog` com autor automático; sucesso ou recusa do arquivo (None → log) zera
      `anexo_pendente`; falha de rede mantém para a próxima passada; excluir o anexo não reanexa
- [X] T010 [US1] `sincronizar_ops.sincronizar(*, desde=None, ate=None, aplicar=True)`: pagina `filter[modified]` (50),
      claim atômico em `site_settings.clicksign_sync_at` (janela curta para aviso, intervalo para a periódica), cursor
      `clicksign_sync_cursor` com folga de 10 min, devolve contagens; trava via `current_app.config` → `travada`; aviso
      que perde o claim marca `clicksign_sync_pendente` e a passada em curso repete antes de soltar
- [X] T011 [US1] Aviso `app/api/clicksign_webhook.py`: `POST /api/webhooks/clicksign`, `limiter 60/min`, corpo ≤ 64 KB
      por `request.stream.read`, HMAC-SHA256 do corpo bruto contra segredo atual/anterior com `hmac.compare_digest`,
      inválido → 404; válido → 200 e `sincronizar` em thread (`app_context`, rollback, `session.remove`) ou na hora com
      `CLICKSIGN_AVISO_SINCRONO`; import em `app/api/__init__.py`
- [X] T012 [US1] Situação no detalhe: `app/api/agenda_read.py` — bloco `contrato` logo após `data["cobranca"]`
      (`:1167`) a partir de `venda_do_evento` (`contracts/api.md`), `pode_cobrar`/`pode_conferir` por `can_confirm` e
      `somente_consulta`; `_serialize_mensagens` ganha `contrato_canal`/`contrato_prazo`
- [X] T013 [US1] Integridade: `app/calendar/routes.py` `_clear_event_side_tables` devolve documentos `ligado` do evento a
      `a_conferir` (`event_id` nulo, motivo `venda_excluida`); `app/calendar/group_ops.py` `TABELAS_DA_PASSAGEM` +
      `_ROTULO_DA_PASSAGEM` com `ClicksignDocumento`, `ClicksignDesvinculo` e `ClicksignCobranca`;
      `app/calendar/sumico_ops.py` `preso_ao_evento` (`:178-203`) conta documento ligado como "não vazio" (o sumiço do
      Google não apaga o evento); `verify_306.py` (retrato da passagem e limpeza) conferido; `verify_312` segue verde (as
      rotas `/api/contratos/` estão fora de `PREFIXOS_DA_TELA` de propósito: a trava é no núcleo)
- [ ] T014 [US1] `app/financeiro/vendas_ops.py` `contract_status_map` + `CONTRACT_STATUS_LABELS`: com integração
      ligada, as seis situações da venda (FR-019), e a venda sem documento cai na regra antiga do `EventContract`;
      frontend `lib/vendas.ts` (`ContractStatus`) e `pages/VendasPipelinePage.tsx` (`CONTRACT_TONE`) ampliados com
      fallback para valor desconhecido; desligada, como hoje
- [ ] T015 [P] [US1] Frontend tipos/hook: `frontend/apps/internal/src/lib/agenda.ts` (`EventoDetalhe.contrato?`,
      `EventMensagens.contrato_canal?/contrato_prazo?`) e `lib/contratos.ts` novo (tipos `ContratoDaVenda`, hooks
      `useCobrarContrato`, `useLigarContrato`, `useDesligarContrato`, `useDescartarContrato`, `useContratosAConferir`,
      invalidando `["event", id]` e `["dashboard"]`)
- [ ] T016 [US1] `frontend/apps/internal/src/components/EventDetail/ContratoClickSign.tsx` novo (Panel "Situação do
      contrato": badge da situação, nome do documento, prazo/assinado em, canal, outros documentos) montado em
      `FinanceiroSection.tsx` acima do "Contrato assinado"; chip do `ResumoSection.tsx` pela situação nova com fallback
- [ ] T017 [US1] Rodar `verify_317` (1–8, 12–15, 23–25 PASS; o 25 inclui agrupar/desagrupar e sumiço do Google) + `npm run typecheck`; commit `feat(317): …`

**Checkpoint**: o contrato aparece e é assinado na página do evento sem clique.

---

## Phase 4: História 2 — A comercial vê quem cobrar e cobra em um clique (P1)

**Verificação**: cenários 9–11, 16–17 em PASS.

- [X] T018 [US2] `contratos_ops`: `listas_da_home(vendas, documentos, cobrancas, hoje)` → `para_cobrar`, `vencidos`,
      `sem_contrato` (≤ 30 dias), `a_conferir`, `ja_aconteceu`, `resumo` (molde `resumo_por_cor`); `pode_cobrar` +
      `motivo_bloqueio`
- [X] T019 [US2] `app/api/dashboard_service.py` `_painel_comercial`: `"contratos": None` no dict inicial (a volta cedo
      quando `vendas_desde` falha mostra AvisoDeFalha, não some) e `bloco["contratos"] = _bloco("contratos", …)` com
      `vendas` já carregadas e documentos/cobranças em lote (sem consulta por linha); `mensagem` (characters/date_line/
      location) por linha reaproveitando a montagem de `_serialize_mensagens` em lote
- [X] T020 [US2] `app/contratos/sincronizar_ops.registrar_cobranca(doc_id, usuario)` + `app/api/contratos_write.py`
      `POST /api/contratos/<id>/cobranca` (COMERCIAL/SA; 409 `nao_cobravel`); comentário `RBAC:` no topo; import em
      `app/api/__init__.py`
- [ ] T021 [P] [US2] `frontend/apps/internal/src/lib/eventDetail.ts`: exporta `saudacao` e cria
      `buildCobrancaContratoMsg(m, canal, prazo)` (WhatsApp × e-mail; texto da spec/plano); `lib/types.ts`
      `ComercialSummary.contratos?: ContratosResumo | null`
- [ ] T022 [US2] `copyToClipboard` sai de `EventHeader.tsx:194` para `lib/clipboard.ts` (Home e evento usam o mesmo);
      `EventHeader.tsx`: item "📝 Cobrar contrato" no bloco `if (mensagens)` (rótulo único; no cancelado o bloco inteiro
      já some — `can_confirm` zerado), `disabled` + `title` pelo `motivo_bloqueio`, copia e chama `useCobrarContrato`;
      entra na soma `pendente`; `lib/eventAttachments.ts`: os hooks de contrato passam a invalidar `["dashboard"]`
- [ ] T023 [US2] `components/home/PainelContratos.tsx` novo (molde `PainelCobrancas`: `LinhaDaHome`, `GrupoDeLinhas`,
      `AvisoDeFalha`, botão "Cobrar contrato" que copia e registra, "Cobrado por X em DD/MM", "Abrir evento") e
      `DashboardPage.tsx` (`SectionKey "contratos"` depois de `comercial`, card em `computeSectionStats`, painel na grade,
      `para_agir` somado em `totalPendencias` do "Tudo em dia ✓" de `:1165`); aviso "Integração com a ClickSign
      desligada" só para Superadmin quando `integracao_ligada` é falso; tipo próprio para a `mensagem` da linha
- [ ] T024 [US2] Rodar `verify_317` (9–11, 16–17 PASS) + typecheck; tela aberta (Home 375 px, COMERCIAL × FINANCEIRO;
      menu ⋯); commit

**Checkpoint**: histórias 1 e 2 entregam o pedido central.

---

## Phase 5: História 3 — "É esse mesmo?" (P2)

**Verificação**: cenários 18–20 em PASS.

- [X] T025 [US3] `sincronizar_ops`: `ligar(doc_id, event_id, usuario)` (FOR UPDATE no documento e no evento, principal,
      `recusar_se_cancelado_para_ligar`), `desligar` (grava `ClicksignDesvinculo`), `descartar`; erros com código
      (`ja_ligado`, `nao_ligado`, `tipo_fora`, `alterado`)
- [X] T026 [US3] `app/api/contratos_write.py` (`ligar/desligar/descartar`) e `app/api/contratos_read.py`
      (`GET /api/contratos/a-conferir`, COMERCIAL/FINANCEIRO/SA); `a_conferir` próximos no bloco `contrato` do detalhe
- [ ] T027 [US3] Frontend: faixa "A conferir" (molde `SugestaoDeEventoFaixa`, `ConfirmDialog` no descartar) nas linhas da
      Home e no `ContratoClickSign.tsx`; botão "Desligar" no documento ligado; diálogo "Ligar contrato da ClickSign" na
      página do evento (lista a conferir; Combobox acima de 10)
- [ ] T028 [US3] Rodar `verify_317` (18–20 PASS) + typecheck + tela; commit

---

## Phase 6: História 4 — Retroativo desde junho (P2)

**Verificação**: cenário 21 em PASS.

- [X] T029 [US4] `app/cli.py`: `flask clicksign-sincronizar [--desde] [--aplicar]` (sem `--aplicar` → rollback e
      contagens: ligaria, a conferir, artista, outros, PDFs a anexar, anexos antigos que passam a assinado) e
      `flask clicksign-webhook --listar | --registrar <url> | --remover <id> [--aplicar]` (grava `clicksign_webhook_id` e
      o segredo; rotação com `_anterior` 24 h)
- [X] T030 [US4] Ensaio só leitura contra a ClickSign real (quickstart §2) com `CLICKSIGN_ALLOW_LOCAL_CALLS=true`, sem
      `--aplicar`; anotar números em `research.md`; commit

---

## Phase 7: História 5 — Aviso perdido não deixa contrato a cobrar (P3)

**Verificação**: cenário 22 em PASS.

- [X] T031 [US5] `app/__init__.py`: `_start_clicksign_sync(app)` (molde `_start_invite_reminders`; só com token e
      `CLICKSIGN_SYNC_ENABLED`; atrás de `MANTO_SEM_THREADS`; **dorme 60 s antes de tocar o banco** — o `startCommand`
      roda `flask db upgrade && python seed.py` sem `MANTO_SEM_THREADS` e as colunas novas ainda não existem nesse
      processo) + log na subida quando a integração está desligada, lido só da config (nunca do `SiteSetting`) (XIV)
- [ ] T032 [US5] Rodar `verify_317` inteiro (26/26); commit

---

## Phase 8: Polimento e transversais

- [ ] T033 `cd frontend && npm run typecheck` (três SPAs); `ruff check` nos tocados; `ruff format` nos novos
- [ ] T034 Tela aberta de verdade (skill `manto-conferir-tela`) nas telas da spec; prints
- [ ] T035 `verify_299`, `verify_312` e `verify_306` (cenários de passagem/limpeza) de novo, sem regressão
- [ ] T036 Docs: `docs/01` (integração, tabelas, endpoints, §4.3 RBAC, env/trava, comandos; corrige :203/:638),
      `docs/02` (painel e bloco; corrige :2080), `docs/03` (entrada no topo + índice), `docs/04` (contrato é da venda;
      vigente; aviso não decide; dependência do nome no fluxo), `docs/05` (colunas `clicksign_*` inertes; dívidas novas)
- [ ] T037 `/speckit-converge` e portões finais; merge e deploy só quando o dono pedir (quickstart §3)

---

## Dependências e ordem

- T001–T003 → T004–T007 (bloqueiam tudo) → US1 (T008–T017) → US2 (T018–T024) → US3 (T025–T028) → US4 (T029–T030) →
  US5 (T031–T032) → Polimento
- T003 e T015/T021 podem andar em paralelo com o backend da mesma fase (arquivos diferentes)
- US2 depende do bloco `contrato` da US1 (T012); US3 e US4 dependem de T008–T010

## Estratégia

- MVP = US1 + US2 (o pedido central). US3–US5 completam a confiança e a operação; entram no mesmo deploy.
- Commit por grupo lógico (`feat(317): …`), sempre por caminho; nunca `git add -A`.
