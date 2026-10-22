<!-- ADAPTADO PARA A MANTO (2026-09-08) — reaplicar após qualquer atualização do Spec Kit; para este
     arquivo o hash em .specify/integrations/speckit.manifest.json deixa de conferir de propósito. -->
# Plano de implementação: Feature 317 — contrato da ClickSign ligado à venda e "Cobrar contrato"

**Branch**: `317-contratos-clicksign` | **Data**: 2026-10-22 | **Spec**: [spec.md](./spec.md)

**Input**: `/specs/317-contratos-clicksign/spec.md`

**Nota**: preenchido pelo `/speckit-plan`. A constituição (`.specify/memory/constitution.md`,
v3+) é lida em tempo de execução — o Constitution Check abaixo é o que ela cobra.

## Resumo

A Manto passa a ler a conta da ClickSign pela API v3 (Portão 0 aprovado: 765 envelopes visíveis, 235 desde 01/06). Uma
**sincronização incremental** (`filter[modified]` desde o último marco) guarda cada envelope em `clicksign_documentos`,
classifica (cliente/artista/outro), lê data + telefone + tema do nome e **liga sozinho** à venda quando há um candidato
só; o resto vai para "A conferir". Ao assinar, o PDF assinado vira `EventContract` marcado. A sincronização roda a cada
30 min (thread com claim), ao chegar um aviso da ClickSign (webhook HMAC que só dispara, nunca decide) e pelo comando
retroativo. A situação da venda (assinado / aguardando / vencido / recusado / sem contrato / marcado à mão) aparece no
evento e num painel "Contratos" da Home, com "Cobrar contrato" que copia a mensagem pelo canal do signatário e registra
quem cobrou. Detalhes: [research.md](./research.md), [data-model.md](./data-model.md), [contracts/api.md](./contracts/api.md).

## Contexto técnico

**Linguagem/Versão**: Python 3.11 (Flask + SQLAlchemy) no backend; TypeScript + React 18 (Vite)
no frontend

**Dependências principais**: Flask, SQLAlchemy, Alembic (migrations à mão); `requests` 2.32.5 (já no
`requirements.txt:33`), `hmac`/`hashlib` (stdlib); React, TanStack Query, Tailwind, `@manto/ui`, `@manto/api-client`

**Armazenamento**: PostgreSQL — 3 tabelas novas + 6 colunas em `site_settings`; PDFs assinados no disco persistente
(`UPLOAD_CONTRACTS`, `contracts/`)

**Verificação**: `specs/317-contratos-clicksign/verify_317.py` contra `manto_local` com dublê da ClickSign e disjuntor
de rede em `socket.socket.connect`; `cd frontend && npm run typecheck`; tela aberta (skill `manto-conferir-tela`)

**Plataforma-alvo**: web — Render (`manto-backend` gunicorn `--workers 3 --worker-class gthread`)

**Tipo de projeto**: SPA desacoplada (API JSON + React)

**Metas de desempenho**: assinatura refletida em ≤ 5 min (aviso) e ≤ 30 min (periódica); retroativo de 235 envelopes em
≤ 5 min respeitando 50 req/10 s; painel da Home sem consulta por linha (lote como `vendas_desde`)

**Restrições**: nenhuma chamada à ClickSign de cópia local (`_suppress_clicksign`); token só em env; o aviso nunca decide;
rotas novas sob `/api/` (sem mudança em `BACKEND_PREFIXES`); campos novos opcionais no TS; sem Jinja

**Escala/escopo**: 3 tabelas, 6 colunas, 5 endpoints de escrita/leitura novos + 1 webhook, 2 comandos CLI, 1 thread;
telas: Home (painel novo), evento (menu ⋯, aba Comercial, chip do Resumo, diálogo "Ligar contrato")

## Constitution Check

*GATE: aprovado antes da Phase 0; reavaliado após a Phase 1.* — **Aprovado nas duas passagens.**

| Princípio / seção | Como o plano cumpre (ou por que não se aplica) |
|---|---|
| I. Reutilizar antes de criar | `cobranca_ops` (`principal_da_venda`, `group_events`, `escopo_do_evento`, `cor_por_distancia`, `vendas_desde`), `vendas_ops.contratante_name`, `normalize_phone`, `formularios_ops._event_client_phones`/`_field_value_by_key`, `pre_evento_ops` sinônimo de tema, `_save_bounded_upload`/`save_file`, molde 310 (cliente, webhook, claim, segredo `_anterior`), molde 298 (sugestão + descarte), `LinhaDaHome`/`GrupoDeLinhas`/`SectorPanel`, `KebabMenu`, `copyToClipboard`, `ConfirmDialog` |
| II. Padrões de código | type hints/docstrings pt-BR; TS estrito; constantes em `app/constants.py`; `ruff check` nos tocados; `ruff format` só nos novos |
| III. Camadas / API First | núcleo puro `app/contratos/contratos_ops.py` (nome, classificação, candidatos, vigente, situação, cor); I/O em `app/contratos/sincronizar_ops.py`; HTTP em `app/integracoes/clicksign_client.py` (sem Flask); `app/api/contratos_read.py`/`contratos_write.py`/`clicksign_webhook.py` só RBAC + serialização, importados em `app/api/__init__.py`; nada em `BACKEND_PREFIXES` (tudo sob `/api`) |
| IV. Não quebrar o que funciona | aditiva; `contract_status_map` e o chip do Resumo mantêm o comportamento quando a integração está desligada; agenda_read/dashboard só ganham chaves; `_clear_event_side_tables` e `TABELAS_DA_PASSAGEM` atualizados; `verify_306`/`verify_312` revisados |
| V. UI/UX com feedback | `useMutation` + invalidação de `["dashboard"]`/`["event", id]`; `loading` nos botões; aviso `aria-live` do `EventHeader`; erros `mensagemDaApi` |
| VI. Esteira (Nível 1) | worktree `C:\tmp\mp317`, sem hook na árvore principal; specify → clarify → plan → checklist → tasks → analyze → implement → converge |
| VII. Living Spec | spec ajustada no plan (aviso não é guardado; desvínculo como entidade) |
| VIII. Verify antes do núcleo | `verify_317.py` (26 cenários da spec) na fase Foundational, primeira rodada salva falhando pelos motivos certos |
| IX. Dinheiro BRL | não toca dinheiro |
| X. Mobile-first público | não toca superfície pública; Home conferida a 375 px mesmo assim |
| XI. Framer Motion | linhas da Home com a saída animada do `GrupoDeLinhas`; faixa "A conferir" no molde `SugestaoDeEventoFaixa` |
| XII. Combobox / Maps | diálogo "Ligar contrato" lista ≤ ~15 documentos a conferir; acima de 10 usa o Combobox de `@manto/ui` |
| XIII. RBAC declarado | `contracts/api.md`; linhas novas em `docs/01` §4.3; cenários 16–17 devem falhar |
| XIV. Config / efeito externo | `CLICKSIGN_ACCESS_TOKEN` (default `""`, `sync: false`), `CLICKSIGN_API_BASE` (default real), `CLICKSIGN_SYNC_INTERVAL=1800`, `CLICKSIGN_SYNC_ENABLED=true`; `_suppress_clicksign()` no MESMO commit do cliente; sem token → desligada com log na subida e `docs/05` |
| Stack | migration à mão, `down_revision = c5d2f7a9e306` (reencadear se a 310 entrar antes); sem Jinja; sem segredo no código nem no banco (o segredo do aviso é revogável e o aviso não decide — R-05) |
| Operação e Deploy | não toca `startCommand`; aditiva (sem ensaio destrutivo); deploy à noite; pós-deploy: env no Render → `flask clicksign-webhook --registrar` → `flask clicksign-sincronizar` dry-run → `--aplicar` (quickstart §3) |

## Estrutura do projeto

### Documentação (esta feature)

```text
specs/317-contratos-clicksign/
├── spec.md · plan.md · research.md · data-model.md · quickstart.md
├── contracts/api.md
├── checklists/
├── tasks.md
└── verify_317.py
```

### Código

```text
migrations/versions/<rev>_contratos_clicksign.py   # 3 tabelas + 6 colunas (data-model.md)
app/models.py                                       # ClicksignDocumento, ClicksignDesvinculo, ClicksignCobranca; SiteSetting
app/constants.py                                    # situações, tipos, vínculos, régua do contrato, textos de bloqueio
app/config.py                                       # _suppress_clicksign + envs CLICKSIGN_*
app/integracoes/clicksign_client.py                 # NOVO — HTTP puro (molde infinitepay_client da 310)
app/contratos/__init__.py
app/contratos/contratos_ops.py                      # NOVO — núcleo puro
app/contratos/sincronizar_ops.py                    # NOVO — sincronização, vínculo, anexo do PDF, claim, cobrança
app/api/contratos_read.py                           # NOVO — GET /api/contratos/a-conferir
app/api/contratos_write.py                          # NOVO — cobranca, ligar, desligar, descartar
app/api/clicksign_webhook.py                        # NOVO — aviso HMAC
app/api/__init__.py                                 # 3 imports
app/api/agenda_read.py                              # bloco `contrato` + fragmentos em `mensagens`
app/api/dashboard_service.py                        # `comercial.contratos` via _bloco
app/__init__.py                                     # _start_clicksign_sync (atrás de MANTO_SEM_THREADS)
app/cli.py                                          # clicksign-sincronizar, clicksign-webhook
app/calendar/routes.py                              # _clear_event_side_tables: documento volta a a_conferir; cobranças/desvínculos por CASCADE
app/calendar/group_ops.py                           # TABELAS_DA_PASSAGEM / _ROTULO_DA_PASSAGEM + ClicksignDocumento
render.yaml                                         # CLICKSIGN_ACCESS_TOKEN sync:false
frontend/apps/internal/src/lib/types.ts             # ContratosResumo (opcional em ComercialSummary)
frontend/apps/internal/src/lib/agenda.ts            # EventoDetalhe.contrato?, EventMensagens.contrato_*?
frontend/apps/internal/src/lib/contratos.ts         # NOVO — hooks (cobrar, ligar, desligar, descartar, a-conferir)
frontend/apps/internal/src/lib/eventDetail.ts       # buildCobrancaContratoMsg (+ exporta saudacao)
frontend/apps/internal/src/components/EventDetail/EventHeader.tsx       # item "📝 Cobrar contrato"
frontend/apps/internal/src/components/EventDetail/ContratoClickSign.tsx # NOVO — situação, a conferir, desligar, ligar
frontend/apps/internal/src/components/EventDetail/FinanceiroSection.tsx # monta o bloco novo acima do "Contrato assinado"
frontend/apps/internal/src/components/EventDetail/ResumoSection.tsx     # chip pela situação nova (fallback antigo)
frontend/apps/internal/src/components/home/PainelContratos.tsx          # NOVO
frontend/apps/internal/src/pages/DashboardPage.tsx  # SectionKey "contratos", card, painel, "Tudo em dia"
specs/312-cancelado-fora-das-listas/verify_312.py   # nada a classificar (prefixo /api/contratos/ fora); conferir
specs/306-dinheiro-do-cancelamento/verify_306.py    # tabelas novas no retrato da passagem e na limpeza
```

**Decisão de estrutura**: domínio novo `app/contratos/` porque o contrato da ClickSign não é dinheiro (`financeiro/`) nem
agenda pura (`calendar/`, que tem regra própria — `docs/00` §7); o núcleo puro separado da sincronização deixa o verify
testar parser/vínculo/situação sem rede. O cliente HTTP mora em `app/integracoes/` como o da 310.

### Pontos de encaixe conferidos (HEAD `5781993c`)

- Venda: `cobranca_ops.principal_da_venda` (`app/financeiro/cobranca_ops.py:250`), `escopo_do_evento` (`:588`),
  `vendas_desde` (`:433`, já inclui cortesia; contrato **não** usa `motivo_fora_da_venda` para cortesia),
  `cor_por_distancia` (`:360`); constantes `FORM_COR_*` (`app/constants.py:404-406`), `COR_*` (`:430-432`).
- Detalhe: `agenda_read.py` — `show_comercial` (`:172`), `can_confirm` (`:185`), cancelado zera (`:231-243`), `venda_do_evento`
  (`:1166`) → bloco `contrato` logo após `data["cobranca"]` (`:1167`); `_serialize_mensagens` (`:785`) ganha parâmetro.
- Home: `dashboard_service._painel_comercial` (`:558-591`) com `_bloco("contratos", …)` reaproveitando `vendas`;
  `corte_dia_sp` (`app/formularios/formularios_ops.py:86`).
- Telefones: `Client.phone` (`models.py:1942`), `EventClient` (`:1902`), `FormResponse.contact_phone` (`:2018`),
  `_event_client_phones` (`formularios_ops.py:873`), `normalize_phone` (`app/clientes/importer.py:43`, não confere DDI
  55 em 12–13 dígitos), tema por `pre_evento_ops.py:47`.
- Arquivo: `_save_bounded_upload` (`app/calendar/routes.py:665`, recebe `FileStorage` → embrulhar bytes em
  `FileStorage(io.BytesIO(...))`), `EventLog` (`models.py:624`, `actor_name` NOT NULL).
- Threads: `app/__init__.py:927-957`, molde `_start_invite_reminders` (`:494-542`), claim `invite_reminders._claim_rodada`
  (`app/calendar/invite_reminders.py:130`).
- CLI: `app/cli.py` `register_commands` (`:12`), molde `formularios-cliente-do-evento` (`--execute`) — aqui `--aplicar`.
- Frontend: `EventHeader.tsx` bloco `if (mensagens)` (`:294-320`, fora do `!cancelado`: o item trava por conta própria),
  soma `pendente` (`:380`), `KebabMenu` usa `label` como key (rótulo único); `PainelCobrancas.tsx` (molde da linha);
  `DashboardPage.tsx` `SectionKey` (`:818`), `computeSectionStats` (`:911`), grade (`:1378-1429`), "Tudo em dia"
  (`:1471`); `SugestaoDeEventoFaixa.tsx` (molde da faixa); `eventAttachments.ts` não invalida `["dashboard"]`.

## Riscos e mitigação

| Risco | Mitigação |
|---|---|
| A 310 entra antes e as duas migrations partem de `c5d2f7a9e306` | reencadear `down_revision` no merge; `flask db heads` no portão |
| A 310 também mexe em `app/config.py`, `app/__init__.py` (limiter), `SiteSetting` | conflitos textuais pequenos; resolver no merge; o limiter da main (`get_remote_address`) basta para o aviso |
| Aviso perdido no deploy | periódica de 30 min + cursor com folga de 10 min |
| Nome do envelope muda no fluxo da ClickSign | tudo cai em "A conferir" (visível); `docs/04` registra a dependência |
| Telefone do signatário ≠ titular | "A conferir" com motivo `telefone_diverge`; cobrança usa o canal do signatário |
| `manto_local` defasado (~30/09) | re-dump antes do verify final; verify semeia o que precisa com prefixo próprio |
| Disjuntor da 310 não pega `requests` | travar `socket.socket.connect` (e `create_connection`) antes de importar o app |

## Rastreamento de complexidade

Sem violação a justificar.
