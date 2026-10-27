# Tasks: 318 — PIX recebido ligado à venda

**Input**: `spec.md`, `plan.md`, `research.md`, `data-model.md`, `contracts/api-318.md`, `quickstart.md`

**Verificação (Princípio VIII)**: `specs/318-pix-recebido-por-email/verify_318.py` (cenários 1–29 da spec) é escrito na
Foundational, antes do núcleo, e nasce falhando pelos motivos certos. `ensaio_318.py` antes de ligar em produção.

**Implementação só com ordem do dono.** Nada de commit até lá.

## Phase 1: Setup

- [x] T001 Constantes em `app/constants.py`: `PIX_ORIGEM_EMAIL_INTER`, `PIX_ESTADOS` (novo, ligado_auto,
      ligado_confirmado, para_conferir, sem_venda, conta_propria, ignorado, nao_entendido), `PIX_TIPO_SUGESTAO`,
      `PIX_TOLERANCIA_VALOR=Decimal("0.01")`, `PIX_REAVALIAR_DIAS=7`, `PIX_REPASSE_FAIXA=(Decimal("0.88"), Decimal("1"))`,
      `PIX_REPASSE_MAX_VENDAS=3`, `PIX_REPASSE_PRIME_DIAS=3`, `PIX_NOME_STOPWORDS`, `PIX_NOME_SEMELHANCA=0.85`,
      `PIX_SAUDE_PARADA_MIN=60`, `EVENT_PAYMENT_ORIGEM_*`
- [x] T002 Config em `app/config.py`: `PIX_EMAIL_SWEEP_ENABLED` (default `"false" if _suppress_mail() else "true"`),
      `PIX_EMAIL_SWEEP_INTERVAL=900`, `PIX_EMAIL_LOOKBACK_DAYS=3` (comentário do porquê, molde do bounce `:271-281`)

## Phase 2: Foundational (bloqueia as histórias)

- [x] T003 Modelos em `app/models.py` conforme `data-model.md`: `ContaRecebimento`, `PixRecebido`;
      `EventPayment.file_path` nullable + `conta_id` + `origem` (+ CHECK); `SiteSetting` +5 colunas (docstrings com o
      porquê)
- [x] T004 Migration manual `migrations/versions/<rev>_pix_recebido_por_email.py` (`down_revision="c5d2f7a9e306"`;
      semente das 4 contas sem número; downgrade documentado); aplicar no `manto_local`; ensaio no dump fresco
      (`flask db upgrade && python seed.py`, downgrade, upgrade)
- [x] T005 [P] Parser puro `app/financeiro/pix_aviso.py`: `ler_aviso_inter(raw: bytes) -> AvisoPix | AvisoDesconhecido`
      (HTML → texto, regex de PIX e de devolução, `titular_lido`, valor `Decimal`, `Date` → parede SP, `Message-ID`,
      `autenticado` por `Authentication-Results` dkim=pass @inter.co)
- [x] T006 [P] `app/integracoes/imap_client.py`: `fetch_messages(username, password, *, sender, subject, since_days,
      limit) -> list[bytes]` (EXAMINE + BODY.PEEK, reaproveita `_all_mail_folder`; `fetch_bounce_messages` intacta)
- [x] T007 **`specs/318-pix-recebido-por-email/verify_318.py`** — 29 cenários da spec (e-mails sintéticos com nomes
      fictícios; IMAP injetado; login só pela API; escrita por conexão separada; cenários 12/21/26 DEVEM falhar;
      limpeza no `finally`) — escrito AGORA e falhando nos cenários não construídos

**Checkpoint**: migration no `manto_local`, parser e IMAP prontos, verify falhando pelos motivos certos.

## Phase 3: História 1 — O PIX óbvio entra sozinho (P1) 🎯 MVP

**Verificação**: cenários 1–6, 23–25, 27b do `verify_318.py`.

- [x] T008 [US1] `app/calendar/cancel_ops.py`: `gravar_comprovante_no_grupo(actor: User | None, …, origem=…,
      conta_id=…)`; ajudante `_quem(actor)` nos pontos `:2940` e `:2983-2986` de `reaplicar_por_dinheiro`
- [x] T009 [US1] `app/calendar/routes.py:1137` `_add_payment_record(…, sem_arquivo=False, origem=…, conta_id=…)`
- [x] T010 [US1] `app/financeiro/pix_ops.py`: normalização de nome (sobre `app/utils.strip_accents_lower`), candidatas
      (`cobranca_ops.vendas_desde(corte_dia_sp())`, `situacao == "com_saldo"`), valores fortes, "já pagou antes",
      decisão auto/para_conferir/sem_venda, `ligar(pix, venda, actor=None)` pelo núcleo + `EventLog` "Sistema (PIX ·
      conta)", conciliação com comprovante manual igual (FR-011)
- [x] T011 [US1] `app/financeiro/pix_email_ops.py`: `claim_sweep` (ImportState `pix_email`), `rodada()` (interruptor +
      `ativo_desde`, IMAP → parser → ingest idempotente → `nao_entendido`/`ignorado`/`conta_propria` → `pix_ops`),
      reavaliação de `sem_venda` ≤ 7 dias com trava da linha, registro de erro em `site_settings`
- [x] T012 [US1] `app/__init__.py`: `_start_pix_email_sweep(app)` (molde `_start_email_bounce_sweep`, nome
      "pix-email"), dentro do bloco `MANTO_SEM_THREADS`
- [x] T013 [US1] `app/notificacoes/notificacoes_ops.py`: kinds `pix.ligado`, `pix.para_conferir`,
      `pix.repasse_infinitepay` no catálogo + `DESTINATARIOS_POR_KIND`; `notificar_pix_*` com `destinatarios=[seller]`
- [x] T014 [US1] `app/api/agenda_read.py:1188-1197`: serializar `origem`, `conta`, `pix`; `lib/agenda.ts:680`
      `file_path: string | null` + campos
- [x] T015 [P] [US1] `FinanceiroSection.tsx` `PagamentoItem`: pagamento de PIX (sem "Ver comprovante"; "PIX · conta ·
      data hora · de nome"; selo automático/confirmado); `app/templates/event_detail.html:2080` `{% if p.file_path %}`

**Checkpoint**: cenários 1–6, 23–25, 27b verdes.

## Phase 4: História 2 — "É esta?" (P1)

**Verificação**: cenários 7–12.

- [x] T016 [US2] `pix_ops`: `confirmar(pix_id, event_id(s), usuario)`, `descartar`, `nao_e_venda` (trava da linha,
      409 `ja_decidido`/`venda_indisponivel`), marcar notificações lidas por entidade; "Outra venda…" recebe qualquer
      evento da busca da agenda (`useAgendaSearch` devolve dias satélite e cancelados): normalizar com
      `cobranca_ops.principal_da_venda` e exigir que a venda esteja no universo da cobrança com saldo
- [x] T017 [US2] `app/api/pix_read.py` (`GET /api/pix`, `GET /api/pix/saude`) e `app/api/pix_write.py` (confirmar,
      descartar, nao-e-venda) com `RBAC:` no topo e gates do contrato; import em `app/api/__init__.py`
- [x] T018 [P] [US2] `frontend/apps/internal/src/lib/pix.ts` (tipos + hooks TanStack Query)
- [x] T019 [US2] `pages/PixRecebidosPage.tsx` + `components/pix/CartaoPix.tsx` (sugestões com selos de motivo; "É esta",
      "Não é esta" com `ConfirmDialog`, "Outra venda…" com `Combobox` + `useAgendaSearch`, "Não é de venda"; `motion`)
- [x] T020 [US2] Rota `/pix` em `App.tsx` e item "PIX recebidos" na seção **Comercial** de `lib/navigation.tsx` (a seção Financeiro só aparece para
      FINANCEIRO/SUPERADMIN; o filtro por item já esconde seção vazia, `navigation.tsx:523-533`)
      (visível a COMERCIAL/FINANCEIRO/SUPERADMIN)
- [x] T021 [US2] Home: bloco `pix_para_conferir` em `app/api/dashboard_service.py` (gate `show_comercial`) e linha com
      atalho em `DashboardPage.tsx`

**Checkpoint**: cenários 7–12 verdes; tela aberta da fila.

## Phase 5: História 3 — Nada conta em dobro (P1)

**Verificação**: cenários 13–16.

- [x] T022 [US3] `cancel_ops.gravar_comprovante_no_grupo`: ação `"anexar"` (arquivo no pagamento de PIX sem arquivo)
- [x] T023 [US3] `app/api/agenda_write.py:2145`: 409 `possivel_duplicata`, `anexar_a`, `forcar_novo`
- [x] T024 [US3] `FinanceiroSection.tsx` `PagamentosPanel` + `lib/eventAttachments.ts`: diálogo "Esse comprovante é do
      PIX…?" (Sim, anexar / Não, é outro); "Anexar comprovante" no item de PIX

**Checkpoint**: cenários 13–16 verdes.

## Phase 6: História 4 — Conta que recebeu (P2)

**Verificação**: cenários 17–18.

- [x] T025 [US4] `pix_ops.resumo_por_conta(meses)` + `GET /api/pix/resumo-por-conta` (FINANCEIRO/SUPERADMIN)
- [x] T026 [US4] Campo opcional "Conta que recebeu" no comprovante manual (`agenda_write` `conta_id`; `PagamentosPanel`)
- [x] T027 [P] [US4] `components/pix/ResumoPorConta.tsx` na página de PIX (só com a chave no payload)

## Phase 7: História 5 — "Prime Dreams" no MEI (P2)

**Verificação**: cenários 19–22.

- [x] T028 [US5] `pix_ops`: par do repasse da Prime (conta ou `titular_lido`, 3 dias, soma de até 3) → `conta_propria`;
      sobra → `para_conferir` `repasse_infinitepay` com grupos de 1–3 vendas `cartao` na faixa 88–100%
- [x] T029 [US5] `confirmar` de repasse: um pagamento por venda pelo saldo (valor cobrado), taxa no `motivo`,
      `pagamentos_extra`; gate FINANCEIRO/SUPERADMIN; desfazer de todos
- [x] T030 [US5] `CartaoPix`: variante de repasse (marcar 1–3 vendas, soma e taxa)

## Phase 8: História 6 — Leitura que não para calada (P2)

**Verificação**: cenários 23–25 (parte de saúde) e 28.

- [x] T031 [US6] `GET/PATCH /api/pix/config` (SUPERADMIN): interruptor (grava `ativo_desde`), pagadores próprios,
      número das contas
- [x] T032 [US6] `components/pix/SaudeDaLeitura.tsx` (faixa de alerta) e `components/pix/ConfigPix.tsx` (só Superadmin)
- [x] T033 [US6] `POST /api/pix/<id>/desfazer` (FINANCEIRO/SUPERADMIN) e botão "Desfazer" na aba "Ligados" e no item de
      PIX do evento (cenários 26–27)

## Phase 9: Ensaio e acabamento

- [x] T034 `specs/318-pix-recebido-por-email/ensaio_318.py` (caixa real só leitura desde 01/06, `manto_local` com
      rollback, gabarito por argumento, só contagens); rodar; critério auto errado = 0 (SC-001) e fração automática
      (SC-002) anotadas
- [x] T035 `verify_318.py` inteiro verde; mutações acusadas (tirar o DKIM, tirar a trava do PIX, deixar o valor ±1)
- [x] T036 `cd frontend && npm run typecheck`; `ruff check` nos tocados; `ruff format` nos novos
- [x] T037 Tela aberta (skill `manto-conferir-tela`): `/pix` (fila, ligados, resumo, saúde, config),
      Home, página do evento (PIX sem arquivo, duplicata, conta)
- [x] T038 Revisão adversarial do diff (dinheiro dobrado, RBAC, thread sem contexto, `file_path NULL` em todo leitor)
- [x] T039 `/speckit-converge`
- [x] T040 Docs: `docs/01` (tabelas, colunas, endpoints, RBAC §4.3 linhas 1914-1944, thread, config), `docs/02`
      (telas), `docs/03` (entrada no topo, com a saída do ensaio sem nomes), `docs/04` (invariante do recebido e
      padrão "liga sozinho / É esta?"), `docs/05` (dívidas criadas)
- [x] T041 Antes do merge: re-encadear `down_revision` no head da `main` (310/315 podem ter entrado)

## Dependências

Setup → Foundational → US1 → (US2, US3 em paralelo de arquivos distintos, exceto `FinanceiroSection.tsx`: US3 depois de
US1-T015) → US4, US5 (US5 depende de US2 para o `confirmar`) → US6 → Ensaio e acabamento.

## Converge (22/10/2026)

Conferido contra o código (FR-001 a FR-019): tudo entregue, com três desvios conscientes do plano:

- **"Desfazer" mora só na aba "Ligados" de `/pix`** (não no item de PIX da página do evento): a página do evento
  não recebe o papel Financeiro nas `flags`, e o pagamento ligado a PIX recusa "Excluir" com 409
  `pagamento_de_pix`, que manda para lá.
- **Conciliação com comprovante manual nunca liga sozinha** (revisão adversarial): vira "É esta?" com "é o
  comprovante já anexado" / "é outro pagamento". A spec (FR-011) dizia "concilia"; agora concilia **na
  confirmação**.
- **Repasse da InfinitePay grava a conta "InfinitePay Prime"** (onde o cliente pagou), não o MEI do repasse —
  senão o total do MEI sairia inflado pela taxa.

Revisão adversarial (T038): 13 achados, todos corrigidos no commit `fix(318): achados da revisão adversarial`, com
os cenários 30–35 do verify. Mutações (T035): DKIM, conciliação de outra conta, nome de um termo, duplicata no
núcleo e repasse da Comercial acusadas; a de "conciliação automática" é segurada também pela reconferência sob a
trava em `_ligar_uma` (duas proteções para o mesmo caso).
