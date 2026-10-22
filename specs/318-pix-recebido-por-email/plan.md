# Plano de implementação: 318 — PIX recebido ligado à venda

**Branch**: `318-pix-recebido-por-email` | **Data**: 2026-10-22 | **Spec**: [spec.md](./spec.md)

**Input**: `/specs/318-pix-recebido-por-email/spec.md` · Pesquisa: [research.md](./research.md) · Dados:
[data-model.md](./data-model.md) · Contrato: [contracts/api-318.md](./contracts/api-318.md) · Roteiro:
[quickstart.md](./quickstart.md)

## Resumo

Uma thread de fundo (`pix-email`, 15 min, uma rodada entre os 3 workers) lê por IMAP, só leitura, os avisos "Pix
recebido" do Inter na caixa joao@mantoproducoes (a Prime chega pelo filtro criado em 22/10), guarda cada aviso uma vez
em `pix_recebidos` e roda a regra de vínculo de `app/financeiro/pix_ops.py` contra as vendas abertas da cobrança. O
óbvio vira pagamento pelo núcleo de comprovante que já existe (`gravar_comprovante_no_grupo`), agora aceitando "sem
arquivo" quando a origem é PIX; o duvidoso vai para a fila "É esta?" (tela nova "PIX recebidos" + linha na Home +
sino); o resto é ignorado. Cada pagamento ganha a conta que recebeu. O comprovante manual pergunta "é do PIX que já
entrou?" antes de dobrar. Nada é implementado antes do `verify_318.py`; nada é ligado em produção antes do
`ensaio_318.py` dar zero ligação automática errada.

## Contexto técnico

**Linguagem/Versão**: Python 3.11 (Flask + SQLAlchemy); TypeScript + React 18 (Vite)

**Dependências principais**: só biblioteca padrão nova (`imaplib`, `email`, `difflib`, `unicodedata`) — nada no
`requirements.txt`; React/TanStack Query/`@manto/ui` (`Combobox`)/`@manto/money` no front

**Armazenamento**: PostgreSQL; migration aditiva à mão sobre o head `c5d2f7a9e306` (ver "Ordem de merge")

**Verificação**: `verify_318.py` contra `manto_local` (IMAP injetado, e-mails sintéticos); `ensaio_318.py` (caixa
real só leitura + `manto_local` com rollback); `npm run typecheck`; `ruff check`; tela aberta

**Plataforma-alvo**: web — Render; telas internas em desktop

**Metas de desempenho**: rodada ≤ 10 s com ≈ 30 avisos novos (IMAP `SINCE` 3 dias + ≤ 1 consulta de vendas por rodada,
`vendas_desde` já faz o eager load); a rodada não segura o worker (thread daemon)

**Restrições**: só leitura na caixa (EXAMINE + BODY.PEEK); nenhum número de conta no repositório; nenhuma env
obrigatória nova; `manto_local` nasce desligado (`_suppress_mail`)

**Escala/escopo**: 2 tabelas novas, 3 colunas + 1 NOT NULL relaxado em `event_payments`, 5 colunas em
`site_settings`, 1 linha em `import_state` (criada em tempo de execução), 7 endpoints novos + 1 alterado, 1 página nova,
3 componentes alterados, 3 kinds no sino, 1 thread

## Constitution Check

| Princípio / seção | Como o plano cumpre |
|---|---|
| I. Reutilizar | IMAP e thread do 219 (`imap_client.py`, `_start_email_bounce_sweep`, `ImportState` + claim do `bounce_ops`); núcleo de comprovante `gravar_comprovante_no_grupo`; universo e saldo de `cobranca_ops` (`vendas_desde`, `VendaResumo`, `sinal_pendente`); `contratante_name`; `strip_accents_lower` (`app/utils.py:15`); sino `notificacoes_ops.emitir(destinatarios=…)`; padrão de sugestão da 298 (`SugestaoDeEventoFaixa`); `Combobox` + `useAgendaSearch` para "Outra venda…"; `LinhaDaHome`/`SectorPanel` na Home |
| II. Padrões | type hints e docstrings pt-BR; constantes em `app/constants.py` (`PIX_*`); TS estrito; `ruff check` nos tocados, `ruff format` só nos novos |
| III. Camadas | `pix_ops.py` (regra, puro), `pix_email_ops.py` (rodada: IMAP → parser → `pix_ops` → gravação), `app/api/pix_read.py`/`pix_write.py` só RBAC + serialização, importados em `app/api/__init__.py` |
| IV. Não quebrar | migration aditiva; `file_path` nullable só para origem PIX e todos os leitores conferidos (tabela abaixo); `gravar_comprovante_no_grupo` mantém o contrato atual para `arquivo` presente; recebido continua = soma de `event_payments` |
| V. UI/UX | TanStack Query, loading nos botões, toasts pt-BR, confirmação no "Não é esta"/"Desfazer" (`ConfirmDialog`) |
| VI. Esteira Nível 1 | specify → clarify → plan → checklist → tasks → analyze; implement só com ordem do dono |
| VII. Living Spec | spec com as decisões; docs ao fechar |
| VIII. Verify antes do núcleo | `verify_318.py` na Foundational (29 cenários da spec) |
| IX. Dinheiro BRL | `Numeric(12,2)`/`Decimal`; parser converte "2.200,00" → `Decimal("2200.00")`; front com `@manto/money` |
| X. Mobile-first público | não toca superfície pública |
| XI. Framer Motion | cartões da fila entram/saem com `motion` (molde do `SugestaoDeEventoFaixa`) |
| XII. Combobox | "Outra venda…" com `Combobox` + busca no servidor (≥ 2 letras) |
| XIII. RBAC | gates por endpoint em [contracts](./contracts/api-318.md); linhas novas em `docs/01` §4.3 (1914-1944) |
| XIV. Config / externo | `PIX_EMAIL_SWEEP_ENABLED` com default real (`"false" if _suppress_mail() else "true"`), `PIX_EMAIL_SWEEP_INTERVAL=900`; interruptor de tela nasce `False`; só leitura em serviço externo (sem trava de escrita a criar) |
| Stack | migration à mão, `down_revision` = head da main no momento do merge; sem Jinja novo (só um `{% if %}` defensivo no template vivo) |
| Operação e Deploy | não toca `startCommand`; migration aditiva (o relaxamento de NOT NULL não reescreve dados); ensaio no dump fresco |

## Decisões de desenho

### Ator do sistema (R-09)
`gravar_comprovante_no_grupo(..., actor: User | None)`: com `None`, `adicionar` em evento cancelado continua recusado
(candidatas já excluem cancelada), e os dois pontos que leem `actor.roles`/`actor.name` em `reaplicar_por_dinheiro`
(`cancel_ops.py:2940`, `2983-2986`) passam por um ajudante `_quem(actor) -> (nome, papel)` que devolve
`("Sistema", "Sistema")` — o padrão de `sumico_ops.py:243-253` e da sincronização (`routes.py:2371-2378`). O
`EventLog` do PIX é gravado direto (`actor_name="Sistema (PIX · <conta>)"`, `actor_role="Sistema"`) no automático e
com o usuário real na confirmação; `_log_anexo` (dependente de `current_user`) não é usado na thread.

### Pagamento sem arquivo
`_add_payment_record(event, *, amount, file_storage, sem_arquivo=False)`: com `sem_arquivo=True` cria o
`EventPayment` com `file_path=None`; o caminho com arquivo não muda. Só `pix_ops` chama com `sem_arquivo=True`.
Leitores de `file_path` conferidos pela pesquisa de código:

| Leitor | Ajuste |
|---|---|
| `app/api/agenda_read.py:1188-1197` (serializa `pagamentos.items`) | acrescenta `origem`, `conta`, `pix` (resumo); `file_path` já passa `null` |
| `frontend/apps/internal/src/lib/agenda.ts:680` | `file_path: string \| null` + campos novos |
| `components/EventDetail/FinanceiroSection.tsx:185` (`PagamentoItem`) | sem arquivo: esconde "Ver comprovante", mostra "PIX · <conta> · <data hora> · de <nome>" e "Anexar comprovante" |
| `app/templates/event_detail.html:2080` (Jinja vivo) | `{% if p.file_path %}…{% else %}PIX{% endif %}` |
| `app/api/audit_agent.py:128-137`, `scripts/auditor/collect.py:71,150,170,626` | já seguros (`IS NOT NULL` / `sem_anexo`) |
| `cancel_ops.py:3039` | já protegido |

### Anexar comprovante a pagamento de PIX
`gravar_comprovante_no_grupo` ganha a ação `"anexar"` (comprovante existente + arquivo): salva o arquivo e preenche
`file_path` do pagamento de origem PIX sem arquivo. O `POST /api/events/<id>/payments` ganha `anexar_a` (id) e
`forcar_novo` (bool) e, sem nenhum dos dois, devolve 409 `possivel_duplicata` quando há no grupo pagamento
`origem='pix_email'` sem arquivo com o mesmo valor (contrato).

### Universo de candidatas
`cobranca_ops.vendas_desde(corte_dia_sp())` — o mesmo universo de `listar_cobrancas` (`dashboard_service.py:574`) —,
filtrado por `situacao == "com_saldo"`. Parcelas: `principal.installments` com `received=False` (nenhum código marca
`received`; ver Rastreamento). Vendedor: `principal.seller`. Repasse da InfinitePay: `principal.payment_method ==
"cartao"`.

### Claim e saúde
Claim por `ImportState(key="pix_email")` com o mesmo `UPDATE … WHERE last_checked_at < limiar` de
`bounce_ops.claim_sweep`, copiado (15 linhas) para `pix_email_ops` em vez de generalizar o do 219 — não mexer no que
roda (Princípio IV). Saúde: `ImportState.last_checked_at` /
`last_import_count` + `site_settings.pix_email_ultimo_erro(_em)` + contagens de `pix_recebidos` (lidos, `nao_entendido`,
contas vistas) nos últimos 7 dias. Aviso que o parser não entende vira linha `estado='nao_entendido'` (só
`message_id`, remetente, assunto, data) — idempotente e contável.

### Concorrência e papel real
`confirmar`/`descartar`/`nao_e_venda`/`desfazer` e a reavaliação da rodada travam a linha do PIX
(`with_for_update`, molde `destino_ops.confirmar_sugestao`) e reconferem o estado (409 `ja_decidido`). Gates de
escrita usam os papéis reais de `current_user` (como `agenda_write`); a contagem da Home segue o papel em uso
(`_effective_has_role`).

### Par do repasse da Prime antes do cadastro do número
O PIX lido da caixa Prime é reconhecido como "Prime" pela conta cadastrada **ou**, enquanto o número não estiver
cadastrado, pela saudação "Olá, PRIME" do aviso (campo `titular_lido` no parser). Sem par, o repasse vai para "para
conferir" de repasse — nunca liga.

### Ordem de merge
A 310 (`e8b4a1c7d310`) e a 315 também partem de `c5d2f7a9e306`. A migration da 318 nasce com `down_revision =
"c5d2f7a9e306"` e é **re-encadeada no head da main no momento do merge** (tarefa explícita); nenhuma toca as mesmas
tabelas/colunas da 318 (310: `site_settings` colunas `virtuais_*`/`infinitepay_*` — sem colisão de nome).

## Estrutura do projeto

### Documentação

```text
specs/318-pix-recebido-por-email/
├── spec.md · plan.md · research.md · data-model.md · quickstart.md
├── contracts/api-318.md
├── checklists/requirements.md (+ /speckit-checklist)
├── tasks.md                     # /speckit-tasks
├── verify_318.py                # antes do núcleo
└── ensaio_318.py                # antes de ligar
```

### Código

```text
app/models.py                                  # ContaRecebimento, PixRecebido; EventPayment +conta_id +origem, file_path nullable; SiteSetting +5
migrations/versions/<rev>_pix_recebido_por_email.py
app/constants.py                               # PIX_ESTADOS, PIX_ORIGEM, tolerâncias, janela de 7 dias, stopwords
app/config.py                                  # PIX_EMAIL_SWEEP_ENABLED / _INTERVAL / _LOOKBACK_DAYS
app/integracoes/imap_client.py                 # + fetch_messages(username, password, *, sender, subject, since_days, limit)
app/financeiro/pix_aviso.py                    # parser puro ler_aviso_inter(bytes) -> AvisoPix | Desconhecido
app/financeiro/pix_ops.py                      # regra de vínculo, confirmar/descartar/nao_e_venda/desfazer, resumo por conta
app/financeiro/pix_email_ops.py                # claim, rodada (IMAP → parser → ingest → vincular), saúde
app/calendar/cancel_ops.py                     # actor None; ação "anexar"; origem/conta
app/calendar/routes.py                         # _add_payment_record(sem_arquivo=…)
app/notificacoes/notificacoes_ops.py           # kinds pix.para_conferir, pix.ligado, pix.repasse_infinitepay
app/__init__.py                                # _start_pix_email_sweep (molde do bounce), no bloco MANTO_SEM_THREADS
app/api/pix_read.py, app/api/pix_write.py      # novos; import em app/api/__init__.py
app/api/agenda_write.py                        # POST payments: possivel_duplicata, anexar_a, forcar_novo, conta_id
app/api/agenda_read.py                         # serializa origem/conta/pix
app/api/dashboard_service.py                   # bloco pix_para_conferir (show_comercial)
app/templates/event_detail.html                # {% if p.file_path %}
frontend/apps/internal/src/lib/pix.ts          # hooks (TanStack Query)
frontend/apps/internal/src/pages/PixRecebidosPage.tsx
frontend/apps/internal/src/components/pix/*    # CartaoPix (sugestões + botões), ResumoPorConta, SaudeDaLeitura, ConfigPix
frontend/apps/internal/src/App.tsx, lib/navigation.tsx   # rota /pix + item de menu
frontend/apps/internal/src/components/EventDetail/FinanceiroSection.tsx  # PagamentoItem + possível duplicata + conta
frontend/apps/internal/src/lib/agenda.ts, lib/eventAttachments.ts
frontend/apps/internal/src/pages/DashboardPage.tsx      # linha "PIX para conferir"
```

**Decisão de estrutura**: domínio `financeiro` (a regra é de cobrança/recebido); o leitor de e-mail fica em
`integracoes`; o núcleo de comprovante continua em `calendar/cancel_ops.py` (dono da trava do grupo). Parser separado
de `pix_ops` para ser testado sem banco.

## Rastreamento de complexidade

| Violação | Por que é necessária | Alternativa mais simples rejeitada porque |
|---|---|---|
| `EventPayment.file_path` passa a aceitar NULL | pagamento provado pelo aviso do banco, sem arquivo | gerar PDF falso do aviso; somar PIX fora de `event_payments` (6 cópias da soma a mudar) |
| `EventInstallment.received` nunca é marcado pelo sistema | a regra usa parcelas "não recebidas" como alvo de valor | marcar `received` aqui é mudança de outro domínio (comercial); a regra trata parcela já coberta pelo recebido como coberta (mesma lógica de `vencimento_do_saldo`) |
