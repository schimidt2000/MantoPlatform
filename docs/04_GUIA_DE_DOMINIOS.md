# 04 — Guia de Domínios

> **O que este documento é:** fluxos, invariantes e armadilhas de cada domínio — o conhecimento que
> hoje só existe espalhado em comentários e na cabeça de quem escreveu. É o que você lê **depois** do
> `docs/00_MAPA_DO_SISTEMA.md` e **antes** do código.
>
> **O que ele não é:** schema (está em `docs/01` §2), inventário de endpoints (`docs/01` §3), tabela
> de gates de RBAC (`docs/01` §4.3) nem fluxo de tela (`docs/02`). Onde o 01/02 já documenta bem,
> aqui há só a referência.
>
> Origem: auditoria de leitura de 2026-08-06 sobre ~44k linhas de Python e ~46k de TypeScript.
> Última revisão: **2026-08-06**.

---

## 0. Os três estágios de arquitetura

Toda estranheza deste backend se explica por uma migração Jinja → API+SPA em andamento. Cada domínio
está num destes estágios — saber qual poupa meia hora de leitura:

| Estágio | Como é | Domínios |
|---|---|---|
| **3 — nasceu desacoplado** | só `*_ops.py` puro + endpoints JSON. Sem blueprint Jinja | `impressoes3d/`, `marketing/` |
| **2 — extraiu ops, manteve Jinja** | `*_ops.py` + blueprint Jinja legado + API, os três vivos | `gastos/`, `clientes/`, `revisao/`, `orcamento/`, `educamanto/`, `formularios/`, `figurino/` |
| **1 — não extraiu** | a regra ainda mora no arquivo de rotas | `financeiro/`, `talents/`, auto-vínculo de `formularios/`, parser de Drive de `figurino/` |

**Todos os blueprints Jinja continuam registrados** (`app/__init__.py:525-542`). Onde há duplicação,
não é código morto: são **duas superfícies vivas com regras diferentes**, alcançáveis batendo direto
no host do Flask.

Convenção que se repete e vale reconhecer: docstring de módulo abrindo com *"Funções puras (sem
`request`/`render_template`/`flash`)"* — 20 arquivos declaram esse contrato e o cumprem. A única
exceção é `virtuais_ops.py:28`, que importa `current_app` para ler config (aceitável — não é
`request`).

---

## 1. Agenda e Eventos

**8.228 linhas.** O domínio mais importante e o de pior distribuição de qualidade.

### Arquivos

| Arquivo | Linhas | O que é |
|---|---|---|
| `app/calendar/routes.py` | 3.910 | ⚠️ **não é um módulo de rotas** — é a camada de ops do domínio disfarçada de Blueprint |
| `app/calendar/event_ops.py` | 1.111 | núcleo de nível-evento (34 funções) |
| `app/calendar/casting_ops.py` | 306 | **padrão-ouro do repositório** — 8 funções, 100% documentadas, zero `request` |
| `app/calendar/observation_ops.py` | 84 | o upload fica no adaptador; o núcleo recebe `file_path` pronto |
| `app/calendar/service.py` | 297 | camada fina sobre a Google Calendar API — **único arquivo que fala com o Google**, zero regra de negócio |
| `app/calendar/sync.py` | 150 | moldura do sync; excelente docstring de módulo |
| `app/api/agenda_read.py` | 766 | fonte única do formato JSON de leitura (sem rotas) |
| `app/api/agenda_write.py` | 1.437 | 41 rotas, 56 funções, **zero sem docstring** — melhor arquivo do domínio |
| `app/api/agenda.py` | 167 | 8 rotas de leitura |

**Mapa de `routes.py` por faixa de linha** (o arquivo não tem docstring nem índice):
`63-323` helpers de mês/sync/exclusão · `325-348` **OAuth Google (as únicas 2 rotas vivas)** ·
`349-474` views `/agenda` (mortas) · `475-1583` os 23 handlers `_handle_*` + record helpers
financeiros · `1585-1610` o dict `_EVENT_ACTIONS` · `1613-1921` `event_detail` (305 l.) ·
`1922-1953` parsers de título · `1954-2148` conflito/notificação/tipo virtual · `2149-2296`
`sync_events` · `2297-2474` talentos que trabalharam, ViaCEP, Google Maps · `2475-2680` ensaio ·
`2682-2967` precificação de orçamento e opções de formulário · `2969-3492` núcleo de criação ·
`3494-3628` wrapper Jinja de criação · `3629-3910` materiais, sync/delete flows, observações.

Constantes no topo (`:46-61`): `CALENDAR_ID`, `TZ`, os conjuntos `_CAN_ENSAIO`/`_CAN_CREATE`/
`_CAN_EDIT_EVENT`/`_CAN_DELETE`, `SOUND_TECH_TALENT_ID = 42` (técnico de som padrão de SHOW) e
`PRESENCE_CHARACTER`.

### Fluxo: sincronização Google → Manto

Entradas: thread interna a cada 600s (`app/__init__.py:215` → `_claim_auto_sync`, lock atômico em
`SiteSetting.calendar_auto_sync_at` para não rodar em todos os workers gunicorn), `sync_worker.py`,
botão do admin (`app/admin/routes.py:414`, `app/api/admin_config_write.py:77`) e sync de um evento só
(`routes.py:3723`). Todas convergem em **`sync_events(items)` (`routes.py:2149`, 146 linhas, sem
docstring)**.

Para cada item, quatro caminhos:
1. **evento virtual local** → só sinaliza divergência e pula (nunca é atualizado nem apagado);
2. **não existe** → cria + `EventLog` + coordenador padrão + técnico de som se SHOW + geocode ViaCEP
   + estimativa de rota;
3. **existe** → detecta mudança de data/hora/local, sobrescreve campos, notifica talentos
   confirmados, re-garante o técnico de som;
4. depois: `source == 'platform'` → commit e **early-return preservando o elenco**; título começando
   com `🟧 ENSAIO` → **apaga todos os roles**; senão → reconcilia os personagens do título contra os
   `EventRole` existentes, renomeando com prefixo antigo para preservar casting/figurino e disparando
   `send_removal_email` para quem sumiu do título.

Ao final, `_mark_talents_worked()`. Em seguida `_cleanup_stale_events` (`routes.py:245`) apaga os
eventos do mês que sumiram do Google — só é seguro porque roda apenas quando o fetch respondeu com
sucesso, e nunca toca evento virtual.

### Fluxo: criação de evento (Manto → Google)

`POST /api/events` (`agenda_write.py:528`) → `_build_create_event_data` → `_validate_event_core`
(`routes.py:2969`) → **`insert_event` no Google** → `_create_event_core` (`routes.py:3283`) → linha do
evento, vínculos de cliente, pré-contrato, roles a partir dos personagens, cargos padrão, reembolso,
observações, `EventLog`, `AuditLog`, `_sync_commission_payment`, commit, notificação de ensaio,
checagem de conflito (avisos não bloqueantes).

⚠️ **O Google é chamado ANTES do banco e não há compensação.** Se `_create_event_core` estourar,
sobra um evento órfão no Google Calendar que o próximo sync importa como evento novo — sem venda, sem
cliente, sem elenco, indistinguível de um evento criado direto no Google.

### Fluxo: exclusão

`DELETE /api/events/<id>` → `_delete_event_flow` (`routes.py:3743`) → recusa líder de grupo →
`AuditLog 'manual_deleted'` → `_delete_event(also_from_google=True)` → `_clear_event_side_tables` +
tratamento de comissão (pendente vira `cancelado`; paga gera estorno negativo) → delete no Google
(falha não trava) → delete local.

### Invariantes

1. **O título do evento no Google é a fonte de verdade do elenco.** `parse_characters`
   (`routes.py:1935`) separa por `+` e remove o prefixo `(TIPO)`.
   Ex.: `(R&I) HOMEM ARANHA + MARIO` → `['HOMEM ARANHA', 'MARIO']`.
2. `parse_event_type` extrai o tipo do prefixo entre parênteses; título iniciado por `🟧 ENSAIO`
   força `event_type = 'ENSAIO'`.
3. `start_at`/`end_at` são **naive em horário de São Paulo** (`service.py:203-207`) — o Postgres usa
   `TIMESTAMP WITHOUT TIME ZONE` e converteria aware para UTC. **Nunca gravar aware.** Exceção
   isolada: `SiteSetting.calendar_sync_cache` usa `utcnow` (`routes.py:88`, `:101`).
4. Evento com fim < início cruza a meia-noite → fim vai para o dia seguinte (`_build_start_end`,
   `routes.py:63`).
5. `source == 'platform'` protege o elenco do sync; roles com `role_type == 'extra'` (Coordenador,
   Maquiador, Técnico) nunca são tocados; `parent_event_id` nunca é sobrescrito pelo Google.
6. Evento de venda virtual é **intocável** pelo sync — nem atualizado, nem apagado; só gera log
   `virtual_divergente`.
7. `group_leader_id` (grupo comercial) ≠ `parent_event_id` (show ↔ ensaio). Satélite tem os campos
   comerciais zerados (`_apply_satellite`, `routes.py:1424`).
8. `EventLog`, `EventContract`, `EventPayment`, `EventRating`, `ClientFeedback` e
   `EventReimbursement` **não têm cascade** — sem `_clear_event_side_tables` (`routes.py:189`) o
   delete estoura violação de FK.
9. Falha do Google **nunca** bloqueia escrita local (`event_ops.py:404`, `routes.py:238`, `:2629`) —
   vira aviso.
10. `cache_cap` em `EventRole` é **teto** vindo do orçamento: `casting_ops.py:68` trunca para
    não-superadmin e gera nota de auditoria quando ultrapassado.

### Armadilhas

- **Renomear qualquer `_helper` de `routes.py` quebra a API em silêncio.** 39 símbolos privados são
  importados por 10 módulos, e os imports são **tardios** (dentro das funções) — não aparecem em
  análise estática de topo.
- **Comissão diverge entre Jinja e React.** O handler Jinja chama `_sync_commission_payment` ao salvar
  dados comerciais (`routes.py:914`); `event_ops.update_event_comercial` (`:490`) e
  `update_event_core` (`:299`) gravam `sale_value`/`seller_id` e **não chamam**. Evento criado sem
  venda e preenchido depois pelo React **nunca gera linha de comissão** —
  `_resync_pending_commissions` só reconcilia linhas já existentes.
- **Agrupar/desagrupar só existe no Jinja morto**, mas `_delete_event_flow` recusa líder de grupo e
  não há endpoint de desagrupar: evento agrupado é **inexcluível pelo produto**.
- **Acréscimos tipados (`EventAcrescimo`), notas fiscais (`EventInvoice`) e parcelas
  (`EventInstallment`) só têm implementação de ESCRITA no handler Jinja** `_handle_update_comercial`
  (`routes.py:712`). A API lê esses dados mas não os grava.
- `flash()` aparece dentro de `_delete_event` (`routes.py:241`), chamado por `_cleanup_stale_events`
  dentro do cron (sem request context). Hoje não estoura porque o cron passa
  `also_from_google=False` e o `flash` está dentro desse `if` — **qualquer mudança nessa condicional
  derruba o sync em background**.
- `_compute_performer_caches` (`routes.py:2682`, 134 l.) é **precificação de orçamento** morando no
  módulo de calendário; `app/orcamento/pricing.py:13` aponta de volta para ela. Preço de cachê não
  está onde se procura.
- Código morto puro: `travel_estimate` (`routes.py:2424`, perdeu o decorator, sem chamador — a
  estimativa que roda é `_fetch_travel_data`, `:2377`) e `_is_outside_sp` (`:2365`).
- **Docstrings mentem sobre o Jinja.** `agenda.py:3`, `agenda_write.py:4`, `casting_ops.py:3`,
  `event_ops.py:4` e `observation_ops.py:4` afirmam que existem "DOIS adaptadores finos" e que "as
  views Jinja seguem intactas". Não seguem: estão inalcançáveis. Não planeje refactor confiando nisso.

---

## 2. Financeiro

**Arquivos:** `routes.py` (1.690), `comissoes_ops.py` (405), `vendas_ops.py` (352),
`app/api/financeiro_read.py` (738), `financeiro_write.py` (532).

`routes.py` **não é um arquivo de rotas**: é o núcleo de cálculo do sistema com 3 views Jinja
penduradas, e é importado por `app/api/financeiro_read.py`, `financeiro_write.py`,
`app/calendar/routes.py` e `app/financeiro/vendas_ops.py`.

### A regra de comissão, completa (`routes.py:120-150`)

Nunca esteve escrita em lugar nenhum. São 9 ramos, em ordem:

1. Sem `sale_value` → **0**.
2. Venda da Loja Virtual (`event_type == 'VIRTUAL'`) → **0**, e a linha `CommissionPayment` **nem
   nasce** (`:155-160`). Provisionar comissão para uma venda que se fecha sozinha reservaria caixa
   para um beneficiário inexistente.
3. Beneficiário: evento EducaManto (título começa com `(EDU`) com responsável configurado em
   `SiteSetting.educamanto_seller_id` → o responsável; senão → o vendedor do evento
   (`_commission_beneficiary`, `:107`).
4. Beneficiário com `receives_commission = False` → **0**.
5. **Base EducaManto**: 5% (`EDUCAMANTO_COMMISSION_RATE`, `:30`) sobre o **LUCRO** = venda − BV −
   cachês. **Base comum**: 2,5% (`DEFAULT_COMMISSION`, `:27`) ou override do evento, sobre
   venda − BV. **BV sempre sai da base** porque é repasse a terceiro, não receita.
6. Base negativa vira 0; arredondamento `ROUND_HALF_UP` em 2 casas.
7. **Ciclo de pagamento**: comissão comum entra pelo mês da **venda** (`sale_date`); comissão
   EducaManto entra pelo mês da **realização** (`payable_from = event.start_at.date()`, `:184`).
   `coalesce(payable_from, sale_date)` (`:1029`) é a expressão canônica do "mês da comissão".
8. Comissão já **paga** nunca é reescrita (`:198`) — é histórico.
9. Se o evento é líder de grupo, o custo somado inclui os satélites (`_group_cost`, `:79`).

**Estorno** = `CommissionPayment` com `amount` negativo e `event_id` nulo. Herda o `sale_date` da
venda original, por isso `_pending_reversals_query` (`comissoes_ops.py:206`) o lista **sem filtro de
mês** — senão um estorno de março sumiria da tela em abril.

### A cascata da DRE Gerencial (`_compute_drg`, `routes.py:351`)

Nesta ordem, e **cada exclusão tem razão**:

`receita_bruta` (só eventos não-permuta e **não-satélite**, para não contar a venda do grupo duas
vezes) → `− impostos` (`DEFAULT_TAX_RATE = 16%`, só sobre eventos `with_invoice`) → `receita_liquida`
→ `− CPV` (cachês do grupo + BV) → `lucro_bruto` → `− marketing` (o cachê das permutas entra **aqui**,
fora do CPV, para não distorcer a margem) → `− comissões` → `− pessoal` → `EBITDA` → `− gastos
extras` → `− gastos recorrentes` → `resultado_liquido`.

- **Regime: competência pela data do evento** (`start_at`), não pela venda nem pelo recebimento.
  Recebimentos previstos (`:602-621`) são informativos de caixa e **não** alteram receita reconhecida.
- **Fator R** (`:481-484`): folha ÷ faturamento; acima de 28% a empresa fica no Anexo III (rótulo 6%),
  abaixo cai para o Anexo V (rótulo 15,5%). São **rótulos de exibição**, não entram em conta.
- **Custo de pessoal** (`_salary_cost`, `:327`): mês cheio → soma real dos `SalaryPayment` se já
  gerados; período fracionado ou mês não gerado → pro-rata do salário vigente ÷ 30. Salários com
  `payment_type == 'comissao'` são excluídos, senão a comissão contaria duas vezes.
- O dashboard calcula três visões: realizado (eventos ocorridos, com custo fixo), projetado (futuros,
  **sem** custo fixo) e total (`:459-462`).

### Planilha de Pagamentos (`pagamentos()`, `routes.py:1120`)

Une 6 fontes num único `items[]` com formato comum (`type`, `id`, `date`, `amount`, `status`,
`pix_key`, `is_future`): cachês de `EventRole`, salários, desembolsos de gastos, BV, comissões
agregadas por vendedor e contas recorrentes. Duas sutilezas: gastos com `paid_at_creation=True`
**nunca** entram (`:1139`); lançamento recorrente com status `registrado` (débito automático /
assinatura) nunca vira pendência (`:1075-1081`).

### Armadilhas

- ✅ **Feature 267 fechou os quatro defeitos abaixo.** Hoje a comissão exibida no evento vem de
  `comissoes_ops.comissao_exibida_do_evento` (linha real → regra canônica → 0 se cancelado), a
  mesma função na API e no Jinja; e a liquidação, das quatro cópias, vem de
  `comissoes_ops.liquidar_periodo`, que usa a **mesma** expressão de ciclo que monta o item. O que
  segue documentado é o estado ANTERIOR — mantido porque explica o porquê das funções existirem.
- **A comissão tem 4 implementações divergentes.** `routes.py:120` (a completa),
  `app/api/agenda_read.py:245` (`_compute_kpi` — desconta BV mas ignora EducaManto, Loja Virtual e
  `receives_commission`, e usa **2%** de padrão), `app/calendar/routes.py:1752` (idem) e o filtro SQL
  de `comissoes_ops.py:183`. **A tela de detalhe do evento pode mostrar um número que o Financeiro
  nunca vai pagar.**
- **O "mês da comissão" muda conforme quem pergunta** — e isso é um **bug ativo**: a montagem do item
  usa `coalesce(payable_from, sale_date)` (`:1029`) mas a marcação de pago filtra só por `sale_date`
  (`:1245-1247` e `app/api/financeiro_write.py:213-215`). Comissão EducaManto vendida em janeiro com
  evento em março aparece no ciclo de março e, ao ser marcada como paga, atualiza **0 linhas**: o
  botão clica e nada acontece.
- **`set_payment_status` está duplicada linha a linha** entre `routes.py:1206` (108 l.) e
  `app/api/financeiro_write.py:52` (139 l.) — mesma árvore de 6 tipos de item, mesmos textos de
  auditoria com "(API)" no fim. E o docstring de `financeiro_write.py:3` afirma o contrário
  ("Reusa, sem duplicar…").
- **A view Jinja `comissoes()` (`:1603`) não aplica o filtro `_sem_loja_virtual`** que a API aplica
  (`comissoes_ops.py:166`): a tela Jinja lista comissões de Loja Virtual que a tela React esconde.
- **Dois relógios no mesmo módulo:** `dashboard()` usa `datetime.now(TZ_SP).date()` (`:412`) enquanto
  `set_payment_status` grava `paid_at = date.today()` (`:1251`) e `comissoes()` usa `date.today()`
  (`:1607`). Em produção (UTC), depois das 21h de Brasília a data sai um dia à frente.
- **Constantes fiscais moram no meio do arquivo de rotas** (`:258-261`: `DEFAULT_TAX_RATE`,
  `DEFAULT_FATOR_R`, `FATOR_R_RATE_LOW/HIGH`), longe de `app/constants.py`, e nada diz de onde vem o
  corte de 28% nem quando revisar.

### Invariantes que valem para todo relatório financeiro

1. **Satélites nunca são linha própria.** Venda e comissão vivem só no líder; os cachês entram via
   `_group_cost`. Esquecer o filtro `not e.is_satellite` conta a venda várias vezes.
2. **Permuta/cortesia não gera receita, mas gera custo** — o cachê sai do CPV e entra em Marketing.
3. **BV é repasse a terceiro**, nunca receita.
4. **Loja Virtual não comissiona.**
5. **Comissão paga é histórico** — nunca reescrita por recálculo.

---

## 3. Gastos — o modelo a copiar

`gastos_ops.py` (879) + `routes.py` (507). **É a referência do padrão routes-finas + ops**: ops puro e
completo, rotas finas, API importando o mesmo ops. O docstring do módulo documenta até a dívida
pendente (o re-export de `ensure_recurring_entries`).

- **Gastos extras** (`SpecialExpense`): criar → aprovar/rejeitar (`:283`, `:295`).
  `paid_at_creation=True` marca gasto quitado no ato (PIX direto) e o exclui da planilha. Pode ser
  vinculado a evento (`link_expense_to_event`, `:325`) e então vira custo do evento.
- **Contas recorrentes** (`RecurringExpense` + `RecurringExpenseEntry`): `debito_automatico` e
  `assinatura` geram lançamento `registrado` automaticamente (`ensure_recurring_entries`, `:445` —
  geração preguiçosa idempotente, protegida por `UNIQUE(recurring_id, month_ref)`); `variavel` espera
  alguém preencher o valor e vira alerta na home a partir do vencimento (`recurring_alerts`, `:482`).
- Vencimento: dia do mês **clampado no último dia** (`_clamp_day`, `:417` — dia 31 num mês de 30 vira
  30) ou, para frequência semanal, a primeira ocorrência do dia da semana dentro do mês ∩ vigência
  (`_weekly_first_date`, `:423`).

⚠️ Usa `date.today()` em ~10 pontos, não `now_sp()`.

---

## 4. Loja de Interações Virtuais (feature 205)

`app/marketing/virtuais_ops.py` (2.325 linhas, 9 seções). **É o melhor código documentado do
repositório** — os docstrings explicam consistentemente o *porquê*. É também um balde por camada: ~6
responsabilidades técnicas distintas num arquivo (ver `docs/05`).

### O fluxo da venda, ponta a ponta

**`reservar()` (`:775`) — a ordem das etapas é a regra:** duplo clique (mesmo `client_token` devolve o
pedido existente) → valida ficha → confere limites anti-abuso → **trava o slot** (`_travar_slot`,
`:747`, `SELECT … FOR UPDATE`) → grava o pedido → **commit** → **só então** fala com a InfinitePay
(`_gerar_link_pagamento`, `:898`). Falar com a operadora antes de travar deixaria a janela aberta
durante a chamada HTTP; travar durante a chamada seguraria uma linha do banco por segundos. Se a
operadora falhar, a reserva é desfeita e o horário volta (`:889-893`).

**Anti-abuso (`_checar_limites`, `:705`):** (a) um telefone não pode ter duas reservas ativas — mas o
erro carrega `existing_order_token` para a família **retomar** o próprio pedido, não bater numa
parede; (b) teto por `origin_hash` (hash de IP+UA, nunca persistido cru, `hash_origem`, `:610`).

**Soft lock de 15 min** (`VIRTUAL_SOFT_LOCK_MINUTES`), contado da criação, dentro da transação que
trava o slot.

**Webhook (`processar_notificacao_pagamento`, `:1513`) — a invariante mais importante da feature: o
corpo do aviso não decide nada.** A InfinitePay **não assina webhooks**, então o payload só identifica
o pedido; quem autoriza é a reconsulta em `ipc.consultar_pagamento`. Sequência: grava
`VirtualPaymentNotification` (a UNIQUE em `transaction_nsu` barra reentrega) → reconsulta → confere
valor (pago < total → recusado) → trava o slot e confere se ainda é desta família → efetiva ou abre
devolução. **Responde 200 sempre**: 400 faria a operadora reenviar em loop, e reenviar não conserta
duplicata nem conflito.

**`efetivar_pedido()` (`:1218`)** — idempotente na entrada (`:1231`). Cria `CalendarEvent`, pré-escala
talento+figurino (`_pre_escalar`, `:1194`), marca o slot como vendido, baixa estoque de gravado, cria
`VirtualMediaDelivery` com prazo, injeta o presente 3D **na mesma fila que a equipe já opera**
(`_injetar_presente_3d`, `:1316` → `impressoes3d_ops.add_event_gift`) e dispara o aviso. Se o Google
falhar, o evento nasce com `google_event_id = 'virtual-local-<nsu>'` (`GOOGLE_ID_LOCAL_PREFIX`,
`:535`) para a venda existir na agenda mesmo assim.

**`expirar_reservas()` (`:1031`) — antes de liberar um horário vencido, reconsulta a cobrança.** "Não
sei" (operadora indisponível) nunca vira "não pago": o horário fica retido por 3 tentativas (minutos
0, 1, 2). Esgotadas, libera e marca `expired_unverified=True` — e esse flag muda o motivo da devolução
depois (`_abrir_devolucao`, `:1341`), porque quem liga reclamando precisa ouvir "a operadora não
confirmou a tempo", não "sua reserva venceu".

**`claim_sweep()` (`:971`)** — UPDATE condicional atômico em `site_settings.virtual_sweep_at`: só um
worker do gunicorn ganha o ciclo. `ciclo_de_varredura()` (`:1000`) roda as 3 rotinas com try/except
**por rotina**, para uma caída não esconder as outras duas.

**Avisos (`_enviar_aviso`, `:1381`):** a trava de "no máximo um por pedido e tipo" é o **banco** —
grava `VirtualOrderNotification` antes de disparar e deixa a `UNIQUE(order_id, kind)` decidir.

### Regras de ouro do módulo

- Tudo em `Decimal` de reais aqui dentro; **centavos só existem em
  `app/integracoes/infinitepay_client.py`**, que distingue `InfinitePayIndisponivel` ("não sei") de
  `InfinitePayError` ("falhou") — é essa distinção que permite tratar "não sei" como "segura o
  horário".
- A feature usa **exclusivamente `now_sp()`** (importado como `agora`). Misturar com `utcnow()` faria
  sumir os horários das próximas 3h da lista.

---

## 5. Portal do Artista — o padrão a propagar

`app/talent_portal/` (2.333 linhas em 5 arquivos). **É a parte mais bem construída do repositório.**

| Arquivo | O que é |
|---|---|
| `portal_ops.py` (592) | agenda, convites, figurino, perfil, portfólio. `EDITABLE_TEXT_FIELDS`/`EDITABLE_DATE_FIELDS` (`:29`,`:53`) são a allowlist do que o talento pode editar de si mesmo |
| `portal_rating_ops.py` (453) | janelas de avaliação: `RATING_WINDOW=7d`, `RATING_EDIT_WINDOW=30d`, `COMMENT_REQUIRED_BELOW=4`, `SHOW_KEYWORDS` (decide sub-notas pelo **título** do evento) |
| `portal_account_ops.py` (266) | credenciais. `PASSWORD_RULES` (`:36`) é a fonte única de força de senha; `request_password_reset` (`:144`) é silencioso por design (anti-enumeração) |
| `portal_links.py` (51) | 40 linhas quase todas docstring de segurança |
| `routes.py` (974) | ⚠️ Jinja legado — **1 rota viva** (ver `docs/05`) |

### As 7 práticas a copiar

1. **Docstring de topo declara o modelo de RBAC em uma frase.** Ex. (`portal_agenda.py:4`): *"RBAC =
   'é o dono do recurso': toda consulta já filtra por `talent_id` da sessão (nunca aceita um id de
   talento vindo do cliente)"*. Seis linhas e o leitor sabe o modelo do arquivo inteiro.
2. **View = 5 a 10 linhas**: resolve o sujeito, chama o ops, traduz exceção, `jsonify`
   (`portal_ratings.py:59-75`).
3. **Exceção tipada com `.field`/`.status` + um tradutor de 3 linhas por módulo** (`_rating_error`,
   `portal_ratings.py:28`). Erro de validação chega no formulário React já apontado no campo certo,
   sem `if` na view.
4. **Ops puro recebe o sujeito já resolvido.** Quando precisa de algo do request (URL de reset, envio
   de e-mail), recebe **callback** — é assim que o módulo fica puro sem perder o envio.
5. **Constantes documentadas com `#:` no topo** (`portal_rating_ops.py:36-55`) viram a documentação
   das regras de negócio sem custar arquivo extra.
6. **Docstring de topo registra a divergência deliberada** (`portal_ops.py:138-142` explica por que
   `get_agenda` não é reusado pelo Jinja). Poupa o próximo agente de "consertar" o intencional.
7. **Contrato de endpoint no formato de `app/api/maps_read.py:21-34`** — linha `RBAC:` +
   `Query params:` + `Returns:` com o shape literal. É a **única** docstring de contrato completa do
   repositório e o molde que os outros 287 endpoints deveriam copiar.

### Segurança registrada em `portal_links.py:4-8`

**Nunca** `url_for(_external=True)` para link de reset de senha: `ProxyFix(x_host=1)` deixa o
atacante escolher o `Host` e receber um e-mail legítimo da Manto apontando para o servidor dele. A
base sai sempre da config.

---

## 6. Demais domínios

| Domínio | O que saber |
|---|---|
| **Talentos** | `talent_ops.py` (525) e `rating_ops.py` (496) existem e são bons, mas a view Jinja os ignora e faz query direta (`list_talents`, 153 l.). Pior cobertura de docstring dos domínios auditados (26/52). `get_talent_profile` (`talent_ops.py:202`) existe e **não é usada** pela view. Importação vem de Google Sheets (`importer.py`), dedupe pelo UNIQUE de `Talent.cpf` |
| **Figurino** | Fichas com peças, foto e impressão por evento. O sync com o Drive (`sync_drive_stream`, `routes.py:400`) é um endpoint **SSE** que emite progresso item a item; o parser do Google Doc mora em routes (`_sync_extract_name`:280, `_sync_extract_pieces`:312, `_sync_save_photo`:351) |
| **Clientes** | `client_ops.py` (310) — padrão ops+routes respeitado |
| **Revisão de mídia** | Material expira em **7 dias** (`EXPIRY_DAYS`, `review_ops.py:27`); `cleanup_expired_review_files()` remove o **arquivo** mas preserva registro e comentários (`file_removed=True`) — o histórico nunca se perde. Ao substituir material, a versão anterior vira snapshot (`snapshot_current_version`, `:203`) e os comentários ficam presos à versão em que foram feitos |
| **Formulários** | Auto-vínculo resposta → evento (`_attempt_auto_link`, `formularios_ops.py:582` — o `routes.py` Jinja foi removido na fase 3) é a regra mais sutil do domínio: (1) exatamente um evento real na data, sem contradição de telefone; (2) telefone que resolve empate, ou aponta para um único evento futuro. **Nunca força vínculo ambíguo** — marca para revisão manual. Roda também no ciclo de sync da agenda (`calendar/sync.py:91`), para cobrir o caso do evento só existir depois da resposta. Desde a **266** há um irmão para cliente (`attempt_auto_link_client`): telefone que bate com exatamente uma ficha (`Client.phone` é UNIQUE) grava `client_id` + `client_link_source='auto_phone'`. ⚠️ Ele roda **só no envio**, nunca no `retry_auto_link_pending` — o filtro de lá é `event_link_locked`, que não sabe nada sobre cliente, e religaria a cada ciclo o vínculo que a comercial desfez |
| **Impressões 3D** | `impressoes3d_ops.py` (573) — estágio 3, 100% de type hints, 1 função sem docstring em 24. Consumido por outros domínios (a loja virtual injeta presentes aqui). O pacote não se chama `3d_impressions` porque identificador Python não começa com dígito (documentado no `__init__.py`) |
| **Marketing** | `marketing_ops.py` (566): calendário editorial, metas de frequência (`goal_health`, `:440`, compara o intervalo alvo com o último post publicado) e ponte para o módulo de Revisão (`attach_review_space`, `:317`). Desde a 204b a relação post↔tema é **N:N** via `marketing_post_temas` |
| **Orçamento** | `calculate_quote` (`quote_ops.py:58`) tem **470 linhas** — a maior função do repositório. Produz as 4 faixas de duração. Regras não óbvias: adicional noturno de R$50 por artista/coordenador a partir das 19h aplicado **pré-markup** (`:33`, `:50`); markup diferente para show e receptivo; maquiador com tabela progressiva; transporte com adicional fora de SP proporcional a colaboradores × km. **Ponto positivo:** `compute_show_pricing` (`pricing.py:9`) é explicitamente uma fonte única extraída de duplicação anterior — o padrão certo |
| **EducaManto** | Calculadora de pacotes educacionais: pessoas no transporte derivadas do pacote+elenco (`pricing_ops.py:70`), transporte por km/pessoas/dias (`:96`), arredondamento para cima na centena (`_ceil100`, `:141`). Conecta-se ao Financeiro pela regra de comissão EducaManto (§2, ramo 5) |
| **Feedback** | Avaliação da **cliente** sobre a equipe, via link público com `CalendarEvent.feedback_token`. **Não confundir** com `EventRating`, que é a avaliação do **artista** sobre o evento, feita com login pelo portal |
| **RH** | `app/rh/routes.py` são 33 linhas de casca Jinja; a lógica está em `app/api/rh_read.py`. É o único consumidor do RBAC por `has_permission` — e `rh.view` nunca é semeado (ver `docs/00` §4) |

---

## 7. Núcleo transversal do backend

| Arquivo | Papel | Nota |
|---|---|---|
| `app/__init__.py` (662) | factory + infra de request | `create_app()` ocupa 341-662 e acumula 13 responsabilidades |
| `app/models.py` (2.577) | fonte única de schema, 68 tabelas | sem docstring de módulo nem índice; banners de seção só a partir da linha 1162 |
| `app/constants.py` (260) | apesar do nome, 88% constantes de features; RBAC na linha 231 | contém 2 funções de negócio: `event_requires_client` (`:17`) e `now_sp` (`:114`) |
| `app/config.py` (192) | `Config` → `Development`/`Production` por `FLASK_ENV` | `_db_url()` converte `postgres://` → `postgresql://`; `_suppress_mail()` (`:21-39`) impede e-mail real quando o banco é local; `_resolve_secret_key()` (`:42-82`) nunca usa chave fraca em produção |
| `app/storage.py` (376) | abstração de arquivo (local ou S3/R2 por `USE_S3`) | **exemplar em documentação.** `save_file` (`:160`) comprime imagem (máx 1200px, JPEG q85) e grava com nome UUID |
| `app/api_utils.py` (50) | envelope de erro + `api_login_required` | curto e perfeito |
| `app/money.py` (118) | `format_brl`/`parse_brl` | puro de propósito (sem Flask/DB), para poder ser importado no factory |
| `app/utils.py` (84) | `unaccent_lower_sql` (busca sem acento sem extensão), `json_for_script` (anti-XSS), `audit()` | ⚠️ `audit()` **não comita** — quem chama comita |
| `app/maps.py` (124) | Distance Matrix + Places | a chave nunca sai do servidor |
| `app/email_service.py` (707) | Flask-Mail + HTML por helpers | `send_async` (`:21-58`) empacota objetos ORM como `(classe, pk)` e recarrega dentro da thread — sem isso a sessão estoura |

**As 7 threads de background** repetem o mesmo esqueleto: talent-sync, calendar-sync,
review-cleanup, virtual-sweep, **email-bounce** (feature 219), **invite-reminders** (231) e
**backup-drive** (264) — as três últimas não constavam nesta contagem até a feature 266.
A diferença que importa: **calendar-sync, virtual-sweep, email-bounce e invite-reminders fazem
claim atômico** entre workers gunicorn; **talent-sync e review-cleanup não**. Review-cleanup
justifica (é idempotente); talent-sync não justifica nada, e `app/talents/importer.py` lê
`ImportState.last_row` no início (`:179`) e grava no fim (`:343`) sem lock — dois workers
processam as mesmas linhas da planilha.

`invite_reminders.py` é o **molde para qualquer aviso por data** (janela de horário, máximo de
lembretes, claim atômico); nenhuma das 7 toca cobrança de cliente — ver a spec da feature 267.

**E-mail local é bloqueado por config, não por banco.** `SiteSetting.email_notifications_enabled` vem
ligado na cópia local do banco de produção; a trava real é `MAIL_SUPPRESS_SEND`
(`config.py:21-39`), checada antes (`email_service.py:538`).

---

## 8. Frontend

### Pacotes compartilhados

- **`@manto/api-client`** — `apiFetch<T>` é a **única porta** para `/api/*`: manda
  `credentials: "include"`, **omite `Content-Type` de propósito quando o body é FormData** (senão o
  boundary do multipart quebra) e traduz o envelope de erro em `ApiRequestError` com `.status` e
  `.fields`. `assetUrl(path)` detecta `http(s)://` e **não** prefixa, porque fotos legadas importadas
  do Drive já guardam URL absoluta (`client.ts:44-51`).
  **`createQueryClient()` define `staleTime: 30_000` e `refetchOnWindowFocus: false`** — é por isso
  que invalidação faltante **não se conserta sozinha**: o dado errado fica na tela.
- **`@manto/money`** — `formatBRL` devolve `"1.234,56"` **sem prefixo R$**. `MoneyInput` guarda valor
  numérico cru no state e string mascarada na tela; ⚠️ renderiza `<input>` **sem classe nenhuma** (o
  pacote não depende de `@manto/ui`), então o call site precisa vestir o campo.
- **`@manto/ui`** — 21 arquivos. Componentes e helpers com docstrings boas, **mas sem README/catálogo**
  (não existe nenhum `.md` em `frontend/`). Duas regras de acessibilidade que só existem em comentário
  e valem como regra do projeto: **`text-gold` reprova AA (3.25:1) — use `text-gold-ink` para texto**
  (`badge.tsx:19-21`); **`text-line` é token de borda de 1px, invisível como ícone (1.2:1) — use
  `text-muted`** (`portal/StarRating.tsx:46-49`).

### Invariantes do frontend

1. **Horário de parede.** Para preencher `<input type=date/time>` ou comparar datas, **recorte a
   string** (`lib/horaLocal.ts`: `dataDeIsoLocal`, `horaDeIsoLocal`, `hojeYmd`).
2. **RBAC é do servidor.** Ou o payload traz a chave (bloco ausente = seção não renderiza), ou traz
   `flags.<nome>`. Filtro de UI é conveniência, nunca fonte de verdade.
3. **Papel efetivo.** Com "Ver como" ativo, o SUPERADMIN conta **só** com o papel simulado
   (`agenda_read.py:127-133`; `navigation.tsx:66`). `useImpersonate` chama `invalidateQueries()` sem
   argumento — invalida tudo, de propósito.
4. **Escrita de evento devolve o `EventoDetalhe` inteiro.** `useEventMutation`
   (`lib/eventDetail.ts:14-23`) grava a resposta com `setQueryData(["event", eventId])` — a tela
   re-renderiza sem refetch e sem merge no cliente. **Todo hook novo de escrita de evento deve seguir
   isso.**
5. Arquivo do Flask sempre via `assetUrl()`; dinheiro sempre via `formatBRL`.

### Armadilhas já pagas (registradas no código)

- Modal centralizado: **flex, nunca `translate`** (`dialog.tsx:45-58`) — o Framer escreve `transform`
  inline e vence a classe; o bug atingiu 11 telas.
- O grid de duas colunas do detalhe do evento precisa de `[&>*]:min-w-0`, senão o card de casting
  estoura a viewport do celular (`EventDetailPage.tsx:24-31`).
- `AccordionRow.summary` **não pode conter elemento interativo** — ele é renderizado dentro do
  `<button>` de expandir; use `actions` (`accordion-row.tsx:7-14`).
- **Invalidação por prefixo do TanStack Query só alcança chaves FILHAS**: `["gastos-recorrentes"]`
  não invalida `["gastos-recorrentes-historico", id]`.
- **`/api/financeiro/pagamentos/set-status` é poliforme**: escreve em `CommissionPayment`,
  `RecurringExpenseEntry`, `SalaryPayment` ou `Role` conforme `item_type`. Qualquer mutação sobre ele
  precisa invalidar os **quatro** domínios de cache.
- `VideoPlayer` existe duas vezes com propósitos distintos (`apps/public` = catálogo MP4/Drive/Vimeo;
  `internal/components/revisao` = player com scrubber e marcadores de comentário). **Não é
  duplicação.**

### Onde mexer para X

| Quero | Faço |
|---|---|
| Tela nova no ERP | rota em `internal/src/App.tsx` + item em `lib/navigation.tsx` (com `isVisible`) + módulo em `lib/` + página em `pages/` |
| Campo novo no evento | tipo em `lib/agenda.ts` (`EventoDetalhe`) + seção em `components/EventDetail/` + mutação via `useEventMutation` |
| Componente compartilhado | `packages/ui/src/components/` + **export nomeado em `packages/ui/src/index.ts`** |

---

## 9. O que esta auditoria NÃO cobriu

Declarado explicitamente para você não confundir ausência com inexistência:

- **`app/admin/`, `app/auth/`, `app/cadastro/`, `app/catalogo/`, `app/cli.py`, `app/drive_migration.py`**
  não foram auditados em profundidade. Aparecem aqui só onde outro domínio os cita.
- **`migrations/`** (115 arquivos): só se verificou a cadeia de revisões e o head. O conteúdo das
  migrations não foi lido.
- **`seed.py`, `sync_worker.py`, `run.py`, `reset_beta.py`** e os scripts na raiz do repositório: não
  auditados.
- **`specs/`**: não auditado.
- **Testes e2e Playwright** de `apps/internal` e `apps/public`: existência registrada, conteúdo não
  auditado. `apps/portal` **não tem nenhum teste**.
- **Templates Jinja** (`app/templates/`): contabilizados por tamanho e alcançabilidade, não lidos.
- **Cobertura de segurança**: não houve revisão de segurança dedicada. Os pontos de segurança citados
  (allowlist de `/uploads`, `portal_links.py`, webhook não assinado, `origin_hash`) apareceram como
  subproduto da leitura, não de uma varredura sistemática.
