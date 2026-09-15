---
description: "Tasks da feature 299 — Sem valor e cobranças"
---
<!-- ADAPTADO PARA A MANTO (2026-09-08) — reaplicar após qualquer atualização do Spec Kit; para este
     arquivo o hash em .specify/integrations/speckit.manifest.json deixa de conferir de propósito. -->
# Tasks: Feature 299 — Sem valor e cobranças

**Input**: artefatos em `/specs/299-sem-valor-cobrancas/`

**Pré-requisitos**:
- [plan.md](./plan.md);
- [spec.md](./spec.md), com as histórias e a seção "Verificação" (17 cenários; o 16 deve falhar);
- [research.md](./research.md) (R1–R47) e [data-model.md](./data-model.md);
- os contratos:
  - [dashboard-comercial.md](./contracts/dashboard-comercial.md);
  - [evento-cobranca.md](./contracts/evento-cobranca.md);
  - [api-eventos-valor.md](./contracts/api-eventos-valor.md);
- a revisão [checklists/revisao.md](./checklists/revisao.md).

**Revisão**: criticado em 14/09 por dois revisores independentes (cobertura e executabilidade).
Foram 34 achados, todos aplicados; as duas decisões de desenho novas estão em R42–R44. O
`/speckit-analyze` (14/09) achou 16 pontos; as duas respostas do dono e a correção do painel
comercial estão em R45–R47.

**Verificação (OBRIGATÓRIA — Princípio VIII)**: `specs/299-sem-valor-cobrancas/verify_299.py` contra
`manto_local`. Ele é escrito na fase Foundational, ANTES do núcleo, falha pelos motivos certos e passa
ao fim de cada história. Não existe pytest nem `tests/`.

**Organização**: por história da spec (US1–US5). O núcleo de cobrança (R1–R10, R30–R38) é
compartilhado e fica na fase Foundational.

## Formato: `[ID] [P?] [Story] Descrição`

- **[P]**: pode rodar em paralelo (arquivos diferentes, sem dependência de tarefa aberta da mesma fase)
- **[Story]**: história a que a tarefa pertence (US1…US5)

## Regras que valem para TODA tarefa

- **Python.**
  - Type hints e docstring Google em toda função; funções de ~30 linhas no máximo; constantes em
    `app/constants.py`.
  - `except` sempre com log (`# noqa: BLE001 — <motivo>`).
  - `ruff check` nos arquivos tocados; `ruff format` só em `app/financeiro/cobranca_ops.py`.
- **Núcleo em `app/financeiro/cobranca_ops.py`.**
  - Não usa `flask.request`; recebe `hoje` e `corte` por argumento; não comita.
  - Dinheiro sempre em `Decimal`, com `quantize(Decimal("0.01"), ROUND_HALF_UP)`. `float` só na
    serialização.
  - Quem usa o núcleo chama pelo módulo (`from app.financeiro import cobranca_ops`;
    `cobranca_ops.vendas_desde(...)`), para o verify poder trocar a função.
- **Endpoint.** Só valida o papel (função no início da view), chama o núcleo e serializa. Erro sempre
  no envelope `json_error`. Nenhum gate muda nesta feature.
- **Compatibilidade de deploy** (R26, SC-011):
  - chave antiga nunca some nem muda de tipo (`pending_payments`, `severity`, `sale`, `received`,
    `saldo`, `due_date`, `cobranca.outstanding/due/enabled`, `pagamentos.items/received_total`);
  - **todo campo novo é opcional no TS** e lido com fallback;
  - no TS, `undefined` (servidor antigo: não desenha) é diferente de `null` (erro: desenha o aviso).
- **React.**
  - TS estrito, sem `any`; Tailwind e `@manto/ui`, sem `style={{}}`.
  - Dinheiro só por `formatBRL`/`MoneyInput` de `@manto/money`.
  - Datas puras com `formatShortDate`/`diaMes`, nunca `new Date(iso)`. A distância em palavras vem
    dos dias calculados pelo servidor.
  - Texto com dinheiro nunca dentro de `MetricBadge`, que não quebra linha.
  - Movimento com `useReducedMotion`.
  - Todo botão de ação muda de estado enquanto envia; Salvar nunca desabilitado por validação.
- **Script contra o `manto_local`.** `$env:DATABASE_URL = (Get-Content .local-db-url -Raw).Trim();
  $env:FLASK_ENV = 'development'; $env:MANTO_SEM_THREADS = '1'; $env:PYTHONUTF8 = '1'`.
- **Google Agenda.** Nenhuma tarefa nem o verify escrevem no Google (R27).
- **Commits** por caminho (nunca `git add -A`), com mensagem por arquivo (`git commit -F`):
  `feat(299):`, `docs(299):`.

---

## Phase 1: Setup

- [x] T001 Commitar `specs/299-sem-valor-cobrancas/tasks.md` na branch `299-sem-valor-cobrancas`
  (`docs(299): tarefas`). Os outros artefatos já estão commitados. *(Feito em `1a2876b`.)*
- [x] T002 Acrescentar em `app/constants.py`, logo depois do bloco `FORM_COR_*` (`:404-405`), as
  constantes da 299, cada bloco com o porquê (research R2):
  - `VALOR_MINIMO_DE_VENDA = Decimal("1.00")` e `FOLGA_COBRANCA = Decimal("1.00")`, dois nomes de
    propósito;
  - `SALDO_VENCE_DIAS_ANTES = 2`;
  - `MARCADORES_COMPROMISSO_INTERNO = ("🟧", "🟠")`;
  - `COBRANCA_COR_VERMELHO_ATE_DIAS = 2` e `COBRANCA_COR_AMARELO_ATE_DIAS = 30`;
  - `SELO_ATRASADO = "Atrasado"`, `SELO_VENCE_HOJE = "Vence hoje"`,
    `SELO_SINAL_PENDENTE = "Sinal pendente"` e `NOTA_SEM_SINAL = "sem sinal"`;
  - `MOTIVO_FORA_CANCELADO`, `_ENSAIO`, `_COMPROMISSO_INTERNO`, `_CORTESIA` e `_LOJA_VIRTUAL`.

  Importar `Decimal` se o módulo ainda não importa.
- [x] T003 Rodar `specs/299-sem-valor-cobrancas/dados_pre_deploy_299.py` (já versionado, só leitura)
  contra o `manto_local`, para garantir que ele roda antes de ser usado na produção (T045). Ele não
  depende de código da 299. *(Rodado em 14/09, e de novo depois de a consulta do SC-001 passar a
  usar a data do grupo: 31 no `manto_local`.)*

---

## Phase 2: Foundational (bloqueia as histórias)

**⚠️ CRITICAL**: nenhuma história começa antes desta fase terminar.

- [x] T004 Escrever `specs/299-sem-valor-cobrancas/verify_299.py` **agora, antes do núcleo**, com os 17
  cenários da tabela da spec e os nomes congelados nos três contratos.

  **Esqueleto**: o de `specs/298-formulario-vira-evento/verify_298.py` (`:45-155, 742-781`):
  - `setdefault` das variáveis; `create_app()`; `TESTING = True`; `limiter.enabled = False`;
  - `_no_banco()` por conexão externa;
  - `cenario()` com `rollback`;
  - três usuários descartáveis (COMERCIAL, FINANCEIRO e CASTING) com `set_password`, e login só por
    `POST /api/auth/login`;
  - requisições fora do `app_context`;
  - `main()` confere `MAIL_SUPPRESS_SEND`, limpa sobras, prepara, roda e limpa no `finally`.

  **Google falso** (R27), instalado antes de qualquer requisição:
  - `app.calendar.routes.insert_event` devolve `{"id": "v299-gc-N"}` e conta;
  - `app.calendar.routes.update_event` e `app.calendar.service.update_event` devolvem `{}` e contam;
  - `app.calendar.service.insert_event` e `app.calendar.service.load_credentials` levantam
    `RuntimeError("verify 299: Google real")`;
  - a saída imprime as contagens.

  **Preparação**:
  - conferir que `SiteSetting.release_date == date(2026, 6, 1)`; senão, falha explícita "corte do
    espelho diferente de 01/06";
  - `hoje = now_sp().date()` e `start_at` como hora de parede de SP às 15h;
  - datas relativas (hoje ± N); datas absolutas só nos cenários 1 e 8.

  **Semeio direto no banco**:
  - `google_event_id = f"v299-{nome}"` (sem `_`, que é coringa no `LIKE`);
  - título `f"{marcador}{nome} [TESTE verify 299] pode apagar"`, com o marcador (`🟧 `, `🟠 `) só
    onde o cenário exige;
  - **Loja Virtual**: `event_type = "VIRTUAL"` (`EVENT_TYPE_VIRTUAL`, `app/constants.py:306`), porque
    `is_loja_virtual` olha só o tipo (`vendas_ops.py:197-205`). O título é livre;
  - grupos com `group_leader_id` nos satélites e `group_name` no principal, sem aninhar e sem
    ensaio, e os campos comerciais do satélite `NULL`;
  - `EventPayment` com `file_path="v299/fake.pdf"`;
  - `Client`/`EventClient` com nome `v299-…` e telefone único;
  - `CommissionPayment` semeado direto quando o cenário pede (5g, 5h);
  - **nunca** `EventRole` à mão. No `POST /api/events`, `event_type` "R&I", `characters: []` e
    `needs_rehearsal: false`.

  **Oráculo**:
  - a linha semeada é achada pelo `event_id` em `comercial.pending_payments`,
    `comercial.sem_valor.a_acontecer/ja_aconteceu`, `cobranca` e `pagamentos` do detalhe;
  - dinheiro comparado como `Decimal(str(v))`;
  - escrita conferida por `_no_banco()`.

  **Cenários**; o 16 é o que DEVE ser recusado:
  - **1** — Corte:
    - eventos de maio sem valor e com valor e saldo, fora das duas listas;
    - principal em 02/06 com satélite **vivo** em 31/05: fora das duas listas, pela data do grupo;
    - controle: principal em 02/06 com satélite **cancelado** em 31/05, que aparece com
      `data_evento == "2026-06-02"`.
  - **2** — O que é "sem valor":
    - vazio, 0, 0,01 e 0,99 entram, com `a_definir` no vazio e no zero e `valor_simbolico` no 0,01
      e no 0,99; o de 1,00 não entra;
    - eventos hoje, −5, +7, +8 e +31 dias: o de hoje em `a_acontecer`; `a_acontecer` do mais
      próximo para o mais distante e `ja_aconteceu` do mais recente para o mais antigo; −5 e +7
      vermelhos, +8 amarelo, +31 cinza.
  - **3** — Quem fica fora de "sem valor":
    - cancelado, `event_type` ENSAIO sem marcador, cortesia, `🟧 VISITA…` e `🟠 GRAVACAO…` sem tipo,
      e VIRTUAL, todos fora;
    - uma visita técnica `🟧` agrupada a um show sem valor: o grupo aparece pelo principal, com a
      data do show;
    - controle: um evento com `deletion_requested_at` aparece.
  - **4** — Grupos em "sem valor":
    - GA, principal com valor: nenhum evento do grupo aparece;
    - GB, principal sem valor: uma linha, com `grupo_comercial.eventos == 2` e `recebido`;
    - GC, principal cortesia: fora;
    - GD, principal de 0,01: aparece em "sem valor" e não em Cobranças.
  - **5** — Valor a definir:
    - (a) `POST /api/events` com `valor_a_definir: true` → 201, valores `NULL` no banco e
      `sale_date == hoje`; o evento entra em "sem valor". O `GET /api/events/<id>` → 200, com
      `cobranca.outstanding == 0`, `cobranca.sem_valor is True` e `enabled is False`;
    - (b) sem a marca, com valor `null` e depois com 0,50 → 400 com `sale_value` em `error.fields`,
      sem chamada ao Google e sem evento novo;
    - (c) com a marca e sem `seller_id` → 400 em `seller_id`;
    - (d) `PATCH /api/events/<id>/comercial` com o corpo **completo** e valor 1.500 → sai de "sem
      valor" e entra em Cobranças com "Sinal pendente"; `sale_date` mantida;
    - (e) evento **cadastrado** no mês anterior (`created_at = utcnow() − 35 dias`), com `sale_date`
      no mês anterior e valor posto agora pelo `/comercial` → `CommissionPayment.payable_from ==
      hoje` (R45);
    - (e') depois do (e), um segundo `PATCH /comercial` (outra forma de pagamento) mantém o
      `payable_from`;
    - (f) comissão real já paga, valor apagado e reposto → nenhuma linha nova;
    - (g) evento de 0,01 cadastrado e vendido no mês anterior, com linha `a_pagar` de 0,00 → `PATCH
      /comercial` com 1.500 → a linha passa a ter `payable_from == hoje` e `amount` recalculado;
    - (h) o mesmo com a linha de 0,00 já `pago` → nasce uma linha `a_pagar` nova com
      `payable_from == hoje`, e a paga fica intacta;
    - (h') depois do (h), um segundo `PATCH /comercial` e uma chamada a
      `_resync_pending_commissions()` não criam linha: continuam uma `a_pagar` e a paga de 0,00;
    - (i) `PATCH /comercial` com 0,50 num evento sem valor → 400 no campo; com o valor vazio → 200;
    - (j) controle do R45: `POST /api/events` hoje, com `sale_date` no mês anterior, valor 1.500 e o
      mesmo vendedor do (e) → a comissão nasce com `payable_from is None` (ciclo pela data da venda,
      como hoje).
  - **6** — Edição e orçamento:
    - (a) evento `source='google_calendar'` sem valor: `PATCH /api/events/<id>` com o título novo, a
      marca e `seller_id` → 200;
    - (b) dois eventos de 0,01, um com bruto 0,01 e outro com bruto `NULL`: `PATCH` só com o título e
      os mesmos valores → 200 nos dois; trocar o líquido para 0,50 → 400;
    - (c) satélite: `PATCH` com título e campos comerciais, e sem `seller_id` → 200, e o banco sem
      campo comercial gravado;
    - (d) evento de 0,01 com `OrcamentoHistory` do **COMERCIAL** (receita do `verify_273.py:122-135`,
      `client_name` `v299-…`), chamado pelo COMERCIAL com `PATCH /api/events/<id>/orcamento`,
      `aplicar_valores_duracao: 2` e `aplicar_equipe: false` → `relatorio_orcamento.valores == 2` e
      `sale_value == 4200.00`.
  - **7** — Grupo em Cobranças:
    - réplica do 344: fora de Cobranças;
    - grupo de 10.000 com 2.000 + 3.000: uma linha, `received 5000.00`, `saldo 5000.00`, e o
      satélite não aparece.
  - **8** — Data do grupo: principal 21/06, satélite 20/06 e satélite cancelado 19/06 com comprovante
    de 500 → `data_evento == "2026-06-20"`, `vencimento == "2026-06-18"`, `received 2500.00`, selo
    "Atrasado".
  - **9** — Vencimento:
    - (a) à vista sem data combinada;
    - (b) à vista com data combinada;
    - (c) faturado com evento passado e data combinada futura → "Vence em 26 dias";
    - (d) parcelas;
    - (e) data combinada vence a parcela;
    - (f) parcela coberta por comprovante de outro evento do grupo → vence a próxima;
    - (g) venda de hoje, evento amanhã, sem comprovante → `selo == "Vence hoje"`,
      `severidade == "vermelho"` e `nota == "sem sinal"`.
  - **10** — Centavos e sinal:
    - saldo de 0,50 fora;
    - 9.235 com 4.617 recebidos: sem sinal pendente;
    - venda de hoje sem comprovante: com sinal pendente;
    - faturada com data combinada e parcelada com cronograma, sem comprovante: sem sinal pendente.
  - **11** — Metade paga e evento a 20 dias: aparece, vence em 18 dias, amarela.
  - **12** — Fora de Cobranças: 0,01; cortesia com valor 800 (dado antigo); `event_type` VIRTUAL 150;
    🟧 com valor e saldo; ensaio com valor; cancelado com saldo.
  - **13** — Conteúdo, cor e ordem:
    - cliente: Contratante, depois a 1ª cliente, depois o título;
    - `selo` só no conjunto em português;
    - `severidade` 2 / 3 / 31 → vermelho / amarelo / cinza;
    - sem sinal vencendo amanhã → `selo == "Vence em 1 dia"` e `nota == "sem sinal"`;
    - sem sinal a 40 dias → `selo == "Sinal pendente"`, amarelo, antes de toda linha cinza;
    - `severity` pelo mapa: vencido → `atrasado`, vermelho → `urgent`, amarelo → `warn`,
      cinza → `info`;
    - chaves antigas presentes.
  - **14** — Total, cards e falha:
    - `cobrancas_resumo.por_cor` e `sem_valor.por_cor` batem com a contagem de cores das linhas;
    - `para_agir` = vermelho + amarelo nas duas listas;
    - `formularios.para_agir` = linhas vermelhas e amarelas de `a_chegar` + `ja_passou`;
    - `total_em_aberto` = a soma `Decimal` dos saldos;
    - os blocos de operação continuam com as mesmas chaves de antes;
    - **falha** (R44, R47): trocar `app.financeiro.cobranca_ops.vendas_desde` por uma função que
      levanta erro e conferir que `comercial is not None`, `cobrancas_resumo is None`,
      `sem_valor is None`, `pending_payments == []` e `formularios` intacto; repetir trocando
      `cobranca_ops.listar_cobrancas`, com o mesmo resultado (restaurar as funções depois).
  - **15** — Página do grupo:
    - `GET /api/events/<principal 10k>`: `cobranca.recebido == 5000.00`, `outstanding == 5000.00`,
      `mensagens.cobranca_amount == "R$ 5.000,00"`, e `pagamentos.outros_do_grupo` com o satélite
      (`total 3000.00`, `quantidade 1`);
    - `GET` no satélite: `cobranca.escopo == "grupo_outro"`, os números do grupo,
      `enabled is False` e `event.group.leader.id ==` o principal;
    - venda faltando 0,50: `quitado is True` e `enabled is False`;
    - evento cortesia: `cobranca.sem_valor is False` e `enabled is False`.
  - **16** (DEVE falhar):
    - CASTING: `GET /api/dashboard` → `comercial is None`; `GET /api/events/<id>` sem `cobranca` e
      sem `venda`;
    - FINANCEIRO: `POST /api/events` e `PATCH /api/events/<id>` → exatamente 403, sem chamada ao
      Google e nada gravado;
    - controles: FINANCEIRO vê a linha do grupo 10k no dashboard; e um `OrcamentoHistory` **do
      FINANCEIRO**, num evento avulso diferente (não satélite, sem vínculo anterior), aplicado pelo
      FINANCEIRO → 200.
  - **17** — Limpeza no `finally`, dentro do `app_context`:
    1. `rollback`;
    2. `ids` = eventos com `google_event_id LIKE 'v299-%'`;
    3. zerar `group_leader_id`, `parent_event_id` e `orcamento_history_id`;
    4. DELETE, nesta ordem: `commission_payments`, `event_payments`, `event_installments`,
       `event_clients`, `event_roles`, `event_acrescimos`, `event_logs`, `event_observations`,
       `event_reimbursements`, `event_invoices` e `event_contracts`;
    5. DELETE dos eventos; `sync_logs` `LIKE 'v299-%'`; `orcamento_history` e `clients` `v299-%`;
    6. usuários (`roles.clear()` antes);
    7. commit e conferência externa de zero sobras.

  Rodar agora e guardar a saída em `specs/299-sem-valor-cobrancas/verify_299_primeira_falha.txt`. Tem
  de falhar pelos motivos certos (bloco `sem_valor` ausente, soma por evento, selos em inglês, 400
  ausente, `outros_do_grupo` ausente), nunca por erro de semeio.
- [x] T005 Em `app/calendar/event_ops.py`, perto de `resolver_data_da_venda` (`:652-684`), criar três
  predicados puros:
  - `sem_valor_de_venda(valor: Decimal | None) -> bool`: vazio, zero ou abaixo de
    `VALOR_MINIMO_DE_VENDA`;
  - `valor_a_definir(valor) -> bool`: vazio ou zero;
  - `valor_simbolico(valor) -> bool`: entre 0 e `VALOR_MINIMO_DE_VENDA`.

  São documentados como a fonte única do limite e usados pelo núcleo, pelo orçamento, pela
  validação e pela leitura do evento.
- [x] T006 Criar `app/financeiro/cobranca_ops.py` (novo; `ruff format`), puro, documentado ("uma
  venda = evento avulso ou grupo pelo principal; fonte única da Home e da página do evento").

  **Imports**: `contratante_name`, `is_loja_virtual` e `NON_SALE_EVENT_TYPE` de
  `app/financeiro/vendas_ops.py` (`:81-93, :197-205, :41`); `group_events` de
  `app/calendar/group_ops.py` (`:64-75`); os predicados do T005 de `app/calendar/event_ops.py`. A
  cortesia é `bool(principal.is_cortesia_permuta)`, o mesmo campo que `_is_permuta` lê, sem
  importar o blueprint `app/financeiro/routes.py`.

  **Primitivas**:
  - `comprovantes_por_evento(ids) -> dict[int, tuple[Decimal, int]]`: `SUM(coalesce(amount, 0))` e
    `COUNT(id)`, com `GROUP BY event_id` e `Decimal(str(x))`;
  - `recebido_da_venda(eventos, mapa) -> Decimal`: soma todos os eventos do grupo, cancelados
    inclusive;
  - `principal_da_venda(event)`: `group_leader` ou o próprio evento;
  - `data_do_grupo(eventos)`: o menor `start_at.date()` entre os não cancelados e sem marcador;
  - `motivo_fora_da_venda(principal)`, na ordem cancelado → ensaio (`event_type ==
    NON_SALE_EVENT_TYPE`, com `None` = não é ensaio) → marcador (`title.lstrip().startswith(
    MARCADORES_COMPROMISSO_INTERNO)`) → cortesia → Loja Virtual.

  **`vencimento_do_saldo(principal, data_grupo, recebido) -> tuple[date | None, str | None]`**
  (R7, R33, R34):
  - `payment_due_date` → `"data_combinada"`;
  - senão, com `installments`, a 1ª parcela cuja soma acumulada, pela ordem de `due_date`, passa do
    recebido → `"parcela"`;
  - senão, `data_grupo − SALDO_VENCE_DIAS_ANTES` → `"politica"`;
  - nos dois últimos, `max(data, principal.sale_date)` quando houver `sale_date`.

  **`@dataclass(frozen=True) VendaResumo`**, com os campos do `data-model.md` mais `mapa`
  (comprovantes por evento, para a página). Propriedades:
  - `saldo` (`None` sem valor);
  - `sem_valor`, `a_definir` e `valor_simbolico`, **fora cortesia** (`False` quando
    `motivo_fora == "cortesia"`);
  - `sinal_pendente`: sem data combinada, sem cronograma e `recebido < valor/2 − FOLGA`;
  - `eventos_vivos` e `situacao`.

  `resumir_venda(principal, mapa) -> VendaResumo`, sem I/O.

  **Régua, selo e ordem** (a regra explícita do FR-026; o R30 substitui a precedência do R9):
  - `cor_por_distancia(dias, *, vermelho_ate, amarelo_ate)`, com o passado vermelho;
  - `cor_da_cobranca(v, hoje)`: vermelho se `dias ≤ 2`; senão amarelo se `sinal_pendente` ou dias de
    3 a 30; senão cinza;
  - `selo_da_cobranca(v, hoje)`:
    - vermelho → "Atrasado" (`dias < 0`), "Vence hoje" (0) ou "Vence em N dias" ("Vence em 1 dia");
    - amarelo com sinal pendente → "Sinal pendente";
    - demais → "Vence em N dias";
  - `nota_da_cobranca(v, hoje)`: "sem sinal" só no vermelho com sinal pendente; senão `None`;
  - `chave_de_ordem(v, hoje)`: ordem da cor (vermelho 0, amarelo 1, cinza 2), vencimento, data do
    grupo, id.

  **Lote da Home** (R10), `vendas_desde(corte) -> list[VendaResumo]`:
  - uma consulta de principais (`group_leader_id IS NULL`, `cancelled_at IS NULL`,
    `start_at >= combine(corte, time.min)`), com `selectinload(satellites)`,
    `selectinload(event_clients).joinedload(EventClient.client)`, `joinedload(client)` e
    `selectinload(installments)`;
  - mais `comprovantes_por_evento` sobre todos os ids;
  - no Python, reconferir `data_do_grupo >= corte`.
  - Nenhum `group_events` nem `is_group_leader` por linha.

  **Listas**:
  - `listar_cobrancas(vendas, hoje) -> list[dict]`;
  - `listar_sem_valor(vendas, hoje) -> dict` (`por_cor`, `para_agir`, `a_acontecer`,
    `ja_aconteceu`);
  - `resumo_por_cor(linhas) -> dict` (`por_cor`, `para_agir`);
  - todas com os campos dos contratos, e `float` só aqui.

  **Página**:
  - `resumo_da_venda_do_evento(event) -> VendaResumo` (usa `group_events` do principal e uma
    chamada a `comprovantes_por_evento`);
  - `pode_copiar_cobranca(resumo, event, hoje) -> bool` (R16);
  - `outros_do_grupo(resumo, evento_aberto_id) -> list[dict]` (`event_id`, `event_title`,
    `start_at`, `total`, `quantidade` dos eventos do grupo **exceto o aberto**; no satélite, isso
    inclui o principal).

  Toda função de ~30 linhas no máximo.

**Checkpoint**: constantes, predicados e núcleo prontos. O `verify_299.py` falha pelos motivos
certos, com a saída guardada.

---

## Phase 3: História 1 — O grupo é cobrado como uma venda só (P1) 🎯 MVP

**Objetivo**: Cobranças e página do evento somam o grupo; uma linha por venda.

**Verificação da história**: cenários 7, 8 e 15 do `verify_299.py` em PASS; página do principal e do
satélite abertas.

- [x] T007 [US1] Em `app/api/dashboard_service.py`:
  - **extrair** `_pode_criar_evento(user, impersonate, is_superadmin: bool) -> bool` da expressão
    inline de `_painel_formularios` (`:589-591`), que passa a usá-la;
  - trocar `compute_comercial_pending`/`serialize_comercial_pending`/`_SEVERITY_ORDER` (`:267-361`)
    por uma closure `_painel_comercial()` dentro de `build_dashboard_summary`, com acesso a `user`,
    `impersonate` e `is_superadmin`;
  - em `_painel_comercial`, `hoje = now_sp().date()`; `dashboard_cutoff` e `_base_filters` ficam
    intactos;
  - **um `try` próprio** (R44, R47), com `rollback` e log como o `_bloco`, cobre juntos:
    `corte = corte_dia_sp()` (import tardio `from app.formularios.formularios_ops import
    corte_dia_sp`, como o `destino_ops` em `:581`), `vendas = cobranca_ops.vendas_desde(corte)` e
    `linhas = cobranca_ops.listar_cobrancas(vendas, hoje)`:
    - na falha de qualquer um dos três, devolve `{"corte": <iso ou None>, "pode_editar_venda",
      "pending_payments": [], "cobrancas_resumo": None, "sem_valor": None}`. Nunca
      `comercial: null` para quem tem `show_comercial`: o `_bloco("comercial")` de fora fica só como
      rede para defeito no próprio envelope;
    - no sucesso, `pending_payments = linhas`, com as chaves antigas mais as novas do contrato,
      `severity` pelo mapa e a ordem do R30;
    - `cobrancas_resumo = {**resumo_por_cor(linhas), "total_em_aberto": soma Decimal}`, num `_bloco`
      interno; na falha dele, `None`, e `pending_payments` continua lista;
  - atualizar a docstring de `build_dashboard_summary` (`:495-506`) e o comentário do gate
    (`:575-576`); o gate não muda.
- [x] T008 [US1] Em `app/api/agenda_read.py`:
  - `_compute_cobranca` (`:401-421`) vira um adaptador de `cobranca_ops.resumo_da_venda_do_evento`,
    com o hoje de SP (`now_sp().date()`);
  - chaves antigas:
    - `outstanding = max(resumo.saldo or Decimal("0"), Decimal("0"))` (`saldo` é `None` sem valor);
    - `due`;
    - `enabled` (`pode_copiar_cobranca`);
  - novas: `valor`, `recebido`, `quitado`, `sem_valor` e `valor_simbolico` (os dois já fora cortesia
    pelo núcleo), `sinal_pendente`, `vencimento_origem`, `escopo` (`"evento"`, `"grupo_principal"`,
    `"grupo_outro"`) e `grupo_tamanho`;
  - `pagamentos` (`:990-1001`): `items` e `received_total` sem mudança, mais
    `outros_do_grupo = cobranca_ops.outros_do_grupo(resumo, event.id)`;
  - `_serialize_mensagens` (`:635-661`) continua lendo `outstanding`/`due`; conferir que a mensagem
    sai com o saldo do grupo.
- [x] T009 [US1] Em `frontend/apps/internal/src/lib/agenda.ts`, acrescentar como opcionais:
  - em `cobranca?` (`:450`), os campos novos;
  - em `pagamentos?` (`:469-472`), `outros_do_grupo?`;
  - em `venda?` (`:414-439`), `sem_valor?`, `a_definir?` e `valor_simbolico?`.

  Nenhum tipo existente muda.
- [x] T010 [US1] Em `frontend/apps/internal/src/components/EventDetail/FinanceiroSection.tsx`, no
  `PagamentosPanel` (`:207-285`), seguindo `contracts/evento-cobranca.md` (depois do T009):
  - **principal ou avulso**: "Recebido {recebido} de {valor} — falta {outstanding}"; "Quitado" por
    `cobranca.quitado`; e "Inclui R$ X em comprovantes de outros eventos do grupo", com links;
  - **outro evento do grupo**: "Este evento é parte do grupo {nome}. A venda está no {principal}"
    (link por `event.group.leader`), mais "Recebido no grupo …" e "neste evento: R$ W";
  - **sem valor**: "Recebido R$ X · valor de venda a definir";
  - **sem os campos novos**: o texto de hoje.
- [x] T011 [US1] Depois do T009, em
  `frontend/apps/internal/src/components/EventDetail/ResumoSection.tsx` (`:368-376`), o chip
  "Recebimento":
  - sem valor → "valor a definir";
  - outro evento do grupo → "no principal";
  - senão, `cobranca.quitado`, com fallback para `outstanding <= 0`.

  Em `EventHeader.tsx` (`:225-259`), o menu "Cobrança" no satélite recebe o título "A cobrança
  deste grupo está no evento principal".

**Checkpoint**: grupo somado na Home (mesmo com a tela antiga, pelas chaves antigas) e na página;
cenários 7, 8 e 15 verdes.

---

## Phase 4: História 2 — A Home mostra o evento que ainda não tem valor (P1)

**Objetivo**: painel "Sem valor" com as vendas sem valor desde a data de início.

**Verificação da história**: cenários 2, 3 e 4 em PASS; painel aberto no computador, a 375 px e como
FINANCEIRO.

- [x] T012 [US2] Em `app/api/dashboard_service.py`, em `_painel_comercial`:
  - acrescentar `sem_valor = cobranca_ops.listar_sem_valor(vendas, hoje)`, num `_bloco("sem_valor")`
    interno (na falha, `sem_valor = None`);
  - acrescentar `pode_editar_venda = _pode_criar_evento(user, impersonate, is_superadmin)`, a
    função extraída no T007.
- [x] T013 [P] [US2] Criar `frontend/apps/internal/src/lib/homeListas.ts` (novo), puro, **copiando**
  de `DashboardPage.tsx` (que só muda no T014):
  - `Severidade`;
  - os mapas de tom (`red`/`gold`/`neutral`) e de fundo (`bg-red-50`/`bg-gold-50`), de `:431-444`;
  - `diaMes`;
  - `distanciaDaData(dias, { passado = "passou", futuro })`, de `:459-466`, que devolve "hoje",
    "amanhã", "em N dias" ou `${passado} há N dia(s)`, e com `futuro: "vence"` "vence hoje"/"vence
    em N dias".

  O comportamento para os formulários da 298 fica idêntico.
- [x] T014 [US2] Em `frontend/apps/internal/src/pages/DashboardPage.tsx`, depois do T013, sem mudar
  comportamento nem texto:
  - trocar os locais de `:431-466` pelos imports de `homeListas.ts`;
  - extrair `frontend/apps/internal/src/components/home/GrupoDeLinhas.tsx` (novo): o
    `GrupoFormularios` de `:643-692` com a linha por parâmetro (`titulo?`, `itens`, `chave`,
    `children`), mantendo `AnimatePresence`, `exit`, `useReducedMotion`, `LIMITE_LINHAS_PAINEL = 6`
    e um `BotaoMostrarTodas` único (hoje duplicado em `:236-242` e `:681-689`);
  - extrair `frontend/apps/internal/src/components/home/LinhaDaHome.tsx` (novo): a casca da linha de
    `:504-546` (`severidade`, `cabecalho`, `detalhe?`, `acoes`, `children?`), que desce para duas
    linhas no celular;
  - `FormulariosPanel` e `ListaTruncada` passam a usar essas peças.
- [x] T015 [US2] Em `frontend/apps/internal/src/lib/types.ts`, depois do T013:
  - `PendingPayment` (`:67-77`) ganha os campos novos, todos opcionais;
  - nascem `LinhaSemValor`, `SemValorSummary`, `CobrancasResumo` e `ComercialSummary`, com
    `pending_payments`, `cobrancas_resumo?: CobrancasResumo | null`,
    `sem_valor?: SemValorSummary | null`, `corte?` e `pode_editar_venda?`;
  - `DashboardSummary.comercial` usa `ComercialSummary`;
  - `LinhaFormulario.severidade` usa `Severidade`, de `homeListas.ts`;
  - `FormulariosSummary` ganha `para_agir?`.
- [x] T016 [US2] Criar `frontend/apps/internal/src/components/home/PainelSemValor.tsx` (novo), com
  `GrupoDeLinhas` e `LinhaDaHome`:
  - dois grupos: "Ainda vai acontecer (N)", com hoje incluído, e "Já aconteceu (N)", na ordem do
    servidor, 6 linhas por grupo;
  - **linha**:
    - o nome (`cliente ?? titulo`) e a marca "grupo de N eventos";
    - `formatShortDate(data_evento)` e a distância, com `passado: "aconteceu"`, no tom de
      `severidade`;
    - "a definir" (`a_definir`) ou "R$ 0,01 (valor simbólico)" (`valor_simbolico`, por `formatBRL`);
    - "já recebeu R$ X" quando `recebido > 0`;
    - a ação "Pôr o valor", levando a `/events/<event_id>?aba=comercial&editar=venda` (R46,
      SC-007); com `pode_editar_venda === false`, "Abrir", levando a
      `/events/<event_id>?aba=comercial`;
  - estados:
    - vazio: "Todos os eventos têm valor de venda ✓";
    - erro (`sem_valor === null`): "Não foi possível carregar os eventos sem valor", com "Tentar de
      novo" (`refetch` do dashboard).
- [x] T017 [US2] Em `frontend/apps/internal/src/pages/DashboardPage.tsx`:
  - `SectionKey` (`:820-829`) ganha `sem_valor`;
  - um `SectorPanel` "Sem valor" com o `PainelSemValor`, e o card "Sem valor";
  - `comercial.sem_valor === undefined` (servidor antigo) → sem painel e sem card;
  - `=== null` (erro) → painel e card presentes, em estado de erro.
- [x] T018 [US2] Invalidar `['dashboard']` por prefixo (R23, FR-010) em:
  - `useUpdateEventComercial` e `useUpdateEventBasics`, pelo parâmetro `invalidar`
    (`frontend/apps/internal/src/lib/eventInline.ts:76, :98-100`);
  - `useSetEventOrcamento` (`:142-147`);
  - `invalidarComercial` (`frontend/apps/internal/src/lib/eventOps.ts:238-244`), o que cobre
    parcelas, acréscimos e nota fiscal;
  - `useCancelarEvento` (`eventOps.ts:139-144`);
  - os hooks de comprovante: adicionar, editar e excluir
    (`frontend/apps/internal/src/lib/eventAttachments.ts:107-124`);
  - `useCreateEvent` e `useUpdateEvent` (`frontend/apps/internal/src/lib/eventCreate.ts:190-222`);
  - o fim da fase 2 de anexos em `frontend/apps/internal/src/pages/EventCreatePage.tsx:316-324`.

**Checkpoint**: painel "Sem valor" funcional, com a linha saindo ao voltar para a Home; cenários 2, 3
e 4 verdes.

---

## Phase 5: História 3 — Lançar o evento com "valor a definir" (P2)

**Objetivo**: cadastro e edição com a marca; valor abaixo de R$ 1,00 recusado também na aba
Comercial; "A definir" na aba; orçamento sobre o R$ 0,01; comissão tardia no mês do valor.

**Verificação da história**: cenários 5 e 6 em PASS; cadastro, edição e aba Comercial abertos.

- [x] T019 [US3] Em `app/calendar/event_ops.py`:
  - **`aplicar_valor_a_definir(data: dict) -> None`**: com `data.get("valor_a_definir")` e sem
    cortesia, `sale_value = sale_value_gross = None`;
  - **`resolver_data_da_venda(..., a_definir: bool = False)`** (`:652-684`), estendida (R21) sem
    mudar a cortesia (que continua sem data, docstring `:664`):
    - na criação, com `a_definir` e sem data informada, devolve hoje (SP);
    - na edição, com `a_definir` e `data_atual`, devolve `data_atual` antes do ramo
      `not venda → None`;
  - **`update_event_core`** (`:687-792`):
    - passa `a_definir=bool(data.get("valor_a_definir"))` ao resolvedor (`:763`);
    - quando `event.is_satellite`, não grava nenhum campo comercial (a lista de
      `group_ops.SATELLITE_FIELDS_CLEARED`, `group_ops.py:47-52`), com um comentário apontando o
      `/comercial`, que já recusa satélite.
- [x] T020 [US3] Em `app/calendar/routes.py`:
  - `_validate_event_core` (`:3222`; blocos de valor e vendedor em `:3264-3271`) ganha os
    parâmetros opcionais `valor_atual=None`, `bruto_atual=None` e `satelite=False`;
  - pula os erros de valor quando `data.get("valor_a_definir")` ou `satelite`;
  - fora disso, **por campo**, recusa valor menor que `VALOR_MINIMO_DE_VENDA`, inclusive nulo e 0,
    com a mensagem "Informe o valor de venda ou marque “Valor a definir”.";
  - **exceto** quando o valor enviado daquele campo é igual ao gravado (`valor_atual` para
    `sale_value`, `bruto_atual` para `sale_value_gross`) e o líquido gravado é simbólico. Assim o
    bruto `NULL` ou 0 de um evento de 0,01 passa na troca de título (R32);
  - pula o erro de vendedor só quando `satelite`;
  - em `_create_event_row` (`:3348`), passar
    `a_definir=bool(data.get("valor_a_definir")) and not data.get("is_cortesia_permuta")` ao
    `resolver_data_da_venda`;
  - a criação Jinja (`:4008`) e o `/basico` chamam sem os parâmetros novos.
- [x] T021 [US3] Em `app/api/agenda_write.py`:
  - `_build_create_event_data` (`:696-730`) e `_build_update_event_data` (`:854-878`) repassam
    `"valor_a_definir": bool(body.get("valor_a_definir"))` e chamam
    `event_ops.aplicar_valor_a_definir`;
  - `api_update_event` (`:883-955`) passa `valor_atual=event.sale_value`,
    `bruto_atual=event.sale_value_gross` e `satelite=event.is_satellite` ao `_validate_event_core`;
  - `api_update_event_comercial` (`:1010-1065`) aplica a regra do R43 antes de gravar:
    - valor vazio é aceito (a definir);
    - valor entre 0,01 e 0,99 é recusado com 400 em `sale_value`/`sale_value_gross`, salvo quando é
      igual ao gravado;
  - a ordem guarda → validação → Google (`:753-802`) não muda (o cenário 14a da 298 depende dela).
- [x] T022 [P] [US3] Em `app/calendar/orcamento_evento_ops.py`, em `aplicar_valores_do_orcamento`
  (`:284`) e na mensagem `valores_ignorados` (`:404`), trocar a checagem `event.sale_value` por
  `not event_ops.sem_valor_de_venda(event.sale_value)`. A trava de cortesia continua antes, porque o
  `verify_273.py:430-444` a exige.
- [x] T023 [P] [US3] Em `app/api/agenda_read.py`, no bloco `venda` (`:916-950`), acrescentar
  `sem_valor`, `a_definir` e `valor_simbolico` pelos predicados do T005, fora cortesia.
- [x] T024 [P] [US3] Em `app/financeiro/comissoes_ops.py`, `_sync_commission_payment` (`:689-747`),
  aplicar o R22/R38/R42 à comissão **comum**, sem mudar a assinatura. A detecção é pelo valor da
  linha, porque o histórico do evento some com o `flush` dos chamadores (`event_ops.py:786`,
  `orcamento_evento_ops.py:401`). A docstring registra o porquê: nunca cair em mês já fechado.
  - **"O valor chegou depois"** (R45), numa função pequena e documentada,
    `_valor_chegou_depois(event, hoje) -> bool`: o evento foi cadastrado num mês anterior ao
    corrente de SP **e** a `sale_date` também está num mês anterior. O `created_at` é UTC ingênuo
    (`default=datetime.utcnow`, `models.py:257`): converter para `TZ_SP` (`constants.py:287`) antes
    de comparar o mês. Sem `sale_date`, `False`.
  - **Linha nova** com o valor chegando depois: `payable_from = hoje`. A venda lançada agora com a
    data de um mês anterior (cadastro no mês corrente) fica com `payable_from` `NULL`, como hoje.
  - **Linha `a_pagar` com `amount` 0,00** (do valor simbólico) que passa a ter valor real nessa
    condição: `amount` recalculado e `payable_from = hoje`.
  - **Linha `pago`/`no_banco` com `amount` 0,00**: não conta como `existing`, e o corte vai **na
    própria consulta** (`:698-700`): excluir `status in ('pago', 'no_banco')` com `amount == 0` e
    ordenar por `CommissionPayment.id.desc()`. Testar depois do `.first()` sem ordem pegaria a
    linha paga de novo a cada sincronização (inclusive a do `_resync_pending_commissions`, que roda
    em telas de leitura, `financeiro_read.py:566, :670`) e criaria uma `a_pagar` por vez. Nasce uma
    linha `a_pagar` nova (`payable_from = hoje` na condição do R45), e a paga fica intacta.
  - **Linha paga com valor real**: nunca muda nem se duplica.
  - **Sincronização seguinte**: não reescreve para `None` um `payable_from` já gravado (hoje
    reescreve em `:736`).
  - **EducaManto**: sem mudança.
- [x] T025 [P] [US3] Em `frontend/apps/internal/src/lib/eventFormSchema.ts`:
  - campos ocultos em `DEFAULT_EVENT_FORM_VALUES` (`:75-95`): `valor_a_definir: z.boolean()`,
    `valor_original: z.number().nullable()`, `valor_original_bruto: z.number().nullable()` e
    `satelite: z.boolean()`;
  - refines (`:28-35`), por campo: aceita `is_cortesia_permuta || valor_a_definir || satelite ||
    valor >= 1 || (valor_original simbólico && valor === original do campo)`, com a mesma mensagem
    do servidor;
  - o vendedor (`:22`) passa a `satelite || seller_id !== ""`;
  - `FIELD_ORDER` e `SERVER_FIELD_MAP` sem mudança.
- [x] T026 [P] [US3] Em `frontend/apps/internal/src/lib/eventCreate.ts` (`:119-177`), em
  `EventCreateInput`/`EventUpdateInput`: `sale_value` e `sale_value_gross` passam a `number | null`,
  e entra `valor_a_definir?: boolean`.
- [x] T027 [US3] Depois do T025, em
  `frontend/apps/internal/src/components/EventFormBlocks/ValoresBlock.tsx` e `PagamentoBlock.tsx`:
  - **marca**: botão de alternar "Valor a definir" (`aria-pressed`), no padrão da cortesia
    (`ValoresBlock.tsx:29-46`) e excludente com ela;
  - **valores**: escondidos pelo mesmo `AnimatePresence` (`:48-86`), com a condição `!cortesia &&
    !aDefinir`, e o texto "O evento fica em “Sem valor”, na Home, até alguém pôr o valor." (o nome
    do painel e do card da Home);
  - **aviso** no lugar ao marcar com valor ≥ R$ 1,00: "O valor de R$ X será apagado e a comissão a
    pagar, cancelada.";
  - **foco**: os dois `MoneyInput` (`:60-74`) passam por `Controller`, com `id="sale_value_gross"` /
    `id="sale_value"` e `ref`;
  - **satélite** (props `satelite` e `principal`): a marca fica marcada e travada; vendedor, data da
    venda (`ValoresBlock.tsx:121-145`) e forma de pagamento (`PagamentoBlock.tsx`) ficam escondidos,
    com "A venda deste grupo mora no evento principal" e o link.
- [x] T028 [US3] Em `frontend/apps/internal/src/pages/EventCreatePage.tsx`:
  - corpo (`:408-413`): `sale_value: cortesia ? 0 : aDefinir ? null : valor`, o mesmo para o
    `gross`, e `valor_a_definir: !cortesia && aDefinir`;
  - `onError` (`:481-493`): depois do `setError`, focar e rolar até o primeiro campo de
    `error.fields`, pela ordem de `FIELD_ORDER`.
- [x] T029 [US3] Em `frontend/apps/internal/src/pages/EventEditPage.tsx`:
  - hidratação (`:107-138`, em especial `:125-127`):
    - `valor_a_definir = !cortesia && (sale_value == null || sale_value === 0)`;
    - `valor_original = sale_value` e `valor_original_bruto = sale_value_gross`;
    - com o líquido simbólico, o bruto é hidratado como está (sem `?? 0`) e a marca abre desmarcada;
    - `satelite = data.event.is_satellite`, e `principal = data.event.group?.leader` passado ao
      `ValoresBlock`;
  - corpo (`:245-250`) como no cadastro;
  - `onError` (`:306-319`) com o mesmo foco.
- [x] T030 [US3] Em `frontend/apps/internal/src/components/EventDetail/ComercialSection.tsx`:
  - `VendaPanel` (`:756-828`):
    - `venda.a_definir` → "A definir";
    - `valor_simbolico` → o valor com o `Badge` "valor simbólico";
    - satélite → "Valor de venda: no evento principal", com link;
    - o quadrinho "Venda" (`:105`) sem mudança (R29);
  - `VendaForm` (`:185-376`): o 400 do `/comercial` (R43) aparece no campo de valor, com o texto do
    servidor;
  - **aberto pela Home** (R46, SC-007): o `VendaPanel` lê `editar=venda` da URL (`useSearchParams`,
    como a aba em `EventDetailPage.tsx:186-205`) e começa em edição quando `canEdit`. O `VendaForm`
    recebe `focarValor` e foca "Valor de venda final" (`sale_value`, `:231`; o `MoneyInput` repassa
    `ref`). É ele que tira o evento de "Sem valor": o form não deriva o líquido do bruto (R46). Ao
    salvar ou cancelar, o `editar` sai da URL com `replace`. Sem `canEdit` (FINANCEIRO, satélite),
    o parâmetro é ignorado;
  - `OrcamentoPanel` (`:511-512, 530`):
    `semVenda = venda.sem_valor ?? (!venda.sale_value && !venda.is_cortesia_permuta)`.

**Checkpoint**: "Valor a definir" de ponta a ponta; R$ 0,01 recusado no evento novo e na aba
Comercial e preservado no antigo; orçamento sobre o simbólico; comissão tardia no mês do valor;
cenários 5 e 6 verdes.

---

## Phase 6: História 4 — Cobranças com vencimento e sem alarme falso (P2)

**Objetivo**: painel "Cobranças" novo, com vencimento, selos em português, cor e ordem.

**Verificação da história**: cenários 9 a 13 em PASS; painel aberto no computador e a 375 px.

- [x] T031 [US4] Criar `frontend/apps/internal/src/components/home/PainelCobrancas.tsx` (novo), com
  `GrupoDeLinhas` (uma lista só, sem título) e `LinhaDaHome`:
  - **cabeçalho**:
    - o nome (`cliente ?? titulo ?? event_title`) e a marca "grupo de N eventos";
    - "evento {formatShortDate(data_evento)}";
    - o `selo` do servidor no tom de `severidade` e, quando houver, a `nota` ("sem sinal") ao lado,
      como texto;
  - **detalhe**:
    - "vence {diaMes(vencimento)}", mais " (data combinada)" quando `vencimento_origem ===
      "data_combinada"`, e "venceu há N dias" no atrasado;
    - "Recebido R$ X de R$ Y — falta R$ Z" (`formatBRL`, quebrando linha no celular);
  - **ação**: "Abrir cobrança" → `/events/<event_id>?aba=comercial`;
  - **estados**:
    - vazio (`cobrancas_resumo` presente, sem linha): "Nenhuma cobrança em aberto ✓";
    - erro (`cobrancas_resumo === null`): "Não foi possível carregar as cobranças", com "Tentar de
      novo";
    - servidor antigo (`cobrancas_resumo === undefined`): a lista sem estado de erro; linha sem
      `severidade` fica cinza e sem selo.
- [x] T032 [US4] Em `frontend/apps/internal/src/pages/DashboardPage.tsx`:
  - apagar a `PendingPaymentRow` e os mapas `SEVERITY_TONE` e `SEVERITY_ROW_BG` (`:333-376`), que
    tinham estilo inline e texto em inglês;
  - `SEVERIDADES_URGENTES` (`:349`) fica até o T034, que reescreve o `urgent` (`:916`);
  - o painel `comercial` (`:1256-1276`) passa a usar o `PainelCobrancas`, e o título do `SectorPanel`
    muda de "Comercial" para "Cobranças" (o card já se chama assim, `:914`).

**Checkpoint**: Cobranças com vencimento, selos em português, ordem por cor e as vendas antes
escondidas; cenários 9 a 13 verdes.

---

## Phase 7: História 5 — O total do topo conta só tarefa de verdade (P3)

**Objetivo**: cards e total comerciais contam só o que é para agir.

**Verificação da história**: cenário 14 em PASS; topo conferido na tela.

- [x] T033 [P] [US5] Em `app/formularios/destino_ops.py`, em `listar_sem_destino` (`:570-594`),
  acrescentar `para_agir` (as linhas vermelhas e amarelas de `a_chegar` e `ja_passou`), de forma
  aditiva. O `verify_298` continua 17/17.
- [x] T034 [US5] Em `frontend/apps/internal/src/pages/DashboardPage.tsx`, `computeSectionStats`
  (`:839-960`):
  - `SectionStat` (`:831-833`) ganha `noTotal`;
  - nas listas comerciais (`comercial`, `sem_valor`, `formularios`), o **número do card** e o
    `noTotal` = `para_agir`;
  - nos painéis de operação, `noTotal = count`, como hoje;
  - `totalPendencias` (`:1004`) passa a somar `noTotal`;
  - `urgent`:
    - Cobranças e Sem valor = linhas vermelhas (`severidade === "vermelho"`, com fallback para
      `severity` em atrasado/vencido/urgent);
    - Formulários **fica como hoje** (formulários das linhas vermelhas, `:925-929`);
    - depois, apagar `SEVERIDADES_URGENTES`;
  - detalhe do card Cobranças: `formatBRL(cobrancas_resumo.total_em_aberto)`; "Em dia ✓" só com
    `cobrancas_resumo` presente e nenhuma linha;
  - card Sem valor: "Em dia ✓" só com `sem_valor` presente e as duas listas vazias. Nos dois cards,
    só linhas cinza → número 0, sem ✓ (FR-032);
  - **o ✓ do card**: hoje o `HomeOverview` (`frontend/apps/internal/src/components/HomeOverview.tsx:35,
    :72-75`) mostra "Em dia ✓" sempre que `count === 0`, o que poria o ✓ no card em erro e no card só
    com linhas cinza. `HomeOverviewItem` ganha `emDia?: boolean` (ausente = `count === 0`, e os
    painéis de operação não mudam); os cards comerciais passam `emDia` = lista presente e vazia;
  - **erro** (`cobrancas_resumo === null` ou `sem_valor === null`): card com o detalhe "Não
    carregou", sem ✓, com número e `noTotal` 0;
  - **servidor antigo** (sem `para_agir`): card e `noTotal` = `count`; sem `total_em_aberto`, a soma
    de hoje.

**Checkpoint**: topo coerente com os cards; cenário 14 verde.

---

## Phase 8: Polimento, portões e documentação

- [x] T035 Rodar o `verify_299.py` até **17/17**, guardando a saída em `verify_299_saida.txt`. Rodar
  de novo:
  - `verify_298.py`: 17/17;
  - `verify_273.py`: a cortesia continua sem receber valores;
  - `verify_174.py`: `pending_payments` continua lista.
- [x] T036 `cd frontend && npm run typecheck` limpo (três SPAs) e `ruff check` nos Python tocados
  (lista no `quickstart.md` §2); `ruff format` só em `app/financeiro/cobranca_ops.py`.
- [x] T037 Tela aberta de verdade (skill `manto-conferir-tela`), seguindo o `quickstart.md` §3:
  - **Home**, no computador e a 375 px:
    - os dois painéis, cores, selos, estados vazio e de erro;
    - o card em erro, forçando a falha no `manto_local`;
    - movimento reduzido;
  - **topo**: soma dos cards comerciais + `count` dos painéis de operação == "N pendências no total",
    e uma linha cinza semeada não muda o total;
  - **FINANCEIRO** vê "Abrir";
  - **2 cliques** (SC-007): da linha "sem valor", "Pôr o valor" abre a aba já em edição, com o foco
    no valor de venda final; digitar e "Salvar venda", e o corpo do `PATCH /comercial` leva
    `sale_value` preenchido. Como FINANCEIRO, "Abrir" abre só para leitura;
  - **saída da linha** (FR-010; História 2, cenário 7): depois de salvar o valor, voltar para a Home
    e ver a linha sair com a animação, e sem animação com movimento reduzido. No harness, o stub do
    dashboard devolve a lista sem a linha depois do `PATCH`;
  - **janela de deploy** (SC-011):
    - o bundle novo com um payload de servidor antigo (sem `sem_valor`, `cobrancas_resumo`,
      `para_agir` nem os campos novos da linha): a Home sem erro, Cobranças com as linhas cinza e
      sem selo (contrato, "Servidor antigo"), sem o painel "Sem valor";
    - a `DashboardPage.tsx` da `main` (cópia temporária no harness, por `git show main:…`) com o
      payload novo do `test_client`: o painel "Comercial" de hoje, sem erro. No fim, a cópia é
      movida para o scratchpad;
  - **painel de Formulários da 298** igual ao de antes. Só o número do card muda de unidade (agora
    linhas para agir), e isso fica registrado no `quickstart.md` §3;
  - **cadastro** com a marca e o foco;
  - **edição**: de um evento importado; de um de R$ 0,01; de um satélite, salvando só o título sem
    escolher vendedor;
  - **aba Comercial** do principal e do satélite, com o 400 do valor simbólico no `VendaForm`.
- [x] T038 [P] `docs/01_SISTEMA_E_BANCO.md`:
  - §3.2, a nota "Feature 299" apontando para `contracts/dashboard-comercial.md`;
  - o contrato do detalhe do evento (`cobranca`, `venda`, `pagamentos`);
  - a validação do valor em `POST/PATCH /api/events` e no `PATCH /comercial`;
  - a regra do orçamento;
  - §4.3, as linhas **novas** de `/api/dashboard` e do orçamento;
  - a nota `:1393-1397`, tirando "eventos sem valor" das lacunas.
- [x] T039 [P] `docs/02_MAPA_DE_PAGINAS_E_UX.md`:
  - a Home: os painéis "Cobranças" e "Sem valor", os cards, o total do topo e os estados;
  - o cadastro e a edição com "Valor a definir";
  - a aba Comercial com "A definir", o valor simbólico recusado e a cobrança do grupo.
- [x] T040 [P] `docs/04_GUIA_DE_DOMINIOS.md`: os invariantes do `data-model.md`:
  - o grupo é uma venda só na cobrança;
  - as duas definições de "sem valor";
  - o marcador laranja;
  - o vencimento, nunca antes da data da venda;
  - a folga de centavos;
  - a comissão tardia e a comissão de R$ 0,00.

  Corrigir também o trecho `:153-154`, que diz que agrupar existe só no Jinja.
- [x] T041 [P] `docs/05_DIVIDA_TECNICA.md`:
  - remover num deploy futuro `severity` e o formato antigo de `pending_payments`;
  - a cópia Jinja da cobrança (`calendar/routes.py:1833-1850`);
  - `list_closed_sales` com `event_type != 'ENSAIO'` descartando a venda sem tipo;
  - as somas por evento (`received_map`, `total_recebido`, "a receber") que ficam;
  - a trava do sync do Google, que apaga o principal;
  - `parcelado` contra `parcelado_datas`;
  - a Auditoria de Input com outra definição de "sem valor";
  - `dashboard_cutoff` em UTC com `release_date` vazio (`dashboard_service.py:19-23`), enquanto as
    listas comerciais usam `corte_dia_sp`;
  - a consulta do SC-008, 30 dias depois do deploy.
- [x] T042 [P] Marcar `specs/051-task-venda-pendente/spec.md` como superada pela 299, com uma linha
  no topo.
- [x] T043 `docs/03_HISTORICO_MUTACOES.md`: a entrada 299 no topo e a linha no índice, com:
  - a motivação e as decisões do dono (17 respostas: 7 no specify e no clarify, 4 no plan, 4 no
    checklist e 2 no analyze);
  - o que mudou;
  - as pegadinhas: o `NULL` do `event_type`, o bundle antigo sem ErrorBoundary, o Google pela
    edição completa, a comissão de R$ 0,00 "paga", e o 344 e os comprovantes duplicados;
  - a verificação;
  - "Antes do deploy".

  Atualizar o cabeçalho. Commit `docs(299): documentação viva`, por caminho.
- [X] T044 `/speckit-converge`; o que ele apontar vira tarefa nova no fim deste arquivo. *(Rodado
  em 15/09: 10 achados, T046–T055 na Phase 9.)*
- [ ] T045 **Antes do deploy** (decisão do dono, R41):
  - rodar o levantamento no `manto-backend`, só leitura:
    `ssh -i ~/.ssh/render_manto_ed25519 srv-da8o06on74is73ehf4q0@ssh.oregon.render.com 'cd
    /opt/render/project/src && MANTO_SEM_THREADS=1 PYTHONPATH=$PWD .venv/bin/python -' <
    specs/299-sem-valor-cobrancas/dados_pre_deploy_299.py`;
  - entregar a lista ao dono, que confere e corrige;
  - deploy só quando o dono pedir, fora do horário, com o aviso à equipe (`quickstart.md` §0);
  - depois do deploy, comparar os ids da consulta do SC-001 (no mesmo script, pela data do grupo, como a Home) com
    `comercial.sem_valor` em produção (`quickstart.md` §4) e registrar a consulta do SC-008 para 30
    dias depois.

---

## Dependências e ordem

- Setup (T001–T003) → Foundational (T004–T006), que bloqueia tudo → histórias:
  - US1 (T007–T011) e US2 (T012–T018), as duas P1;
  - US3 (T019–T030) e US4 (T031–T032), as duas P2;
  - US5 (T033–T034), P3.
- Depois das histórias, Polimento (T035–T045).
- **Dentro de cada história**: núcleo e servidor antes da tela; o verify em PASS no fim.
- **Dependências entre histórias**:
  - US4 reusa as peças de lista extraídas na US2 (T013–T015): fazer a US2 antes do T031;
  - US5 depende dos `para_agir` do servidor (T007, T012, T033) e dos tipos (T015);
  - US3 é independente das telas da Home.
- **Mesmo arquivo em sequência**:
  - `dashboard_service.py`: T007 → T012;
  - `DashboardPage.tsx`: T014 → T017 → T032 → T034;
  - `agenda_read.py`: T008 → T023;
  - `event_ops.py`: T005 → T019;
  - `routes.py`: T020;
  - `agenda.ts`: T009, antes de T010 e T011;
  - `homeListas.ts`: T013, antes de T014 e T015;
  - `eventFormSchema.ts`: T025, antes de T027 e T029.

## Paralelismo possível

- **T010 ‖ T011**, depois do T009.
- **T014 ‖ T015**, depois do T013.
- **T022 ‖ T023 ‖ T024 ‖ T025 ‖ T026**: arquivos diferentes, todos da US3.
- **T033** a qualquer momento depois da Foundational.
- **T038 ‖ T039 ‖ T040 ‖ T041 ‖ T042**: um documento cada.

## Estratégia

- **MVP**: Setup + Foundational + US1. O grupo passa a ser somado na Home, que funciona até com a
  tela antiga, graças às chaves antigas, e na página do evento. Isso já tira da lista o 344 e as
  cobranças de dinheiro já pago.
- **Incremental**: US2 (o painel "Sem valor") → US3 ("Valor a definir") → US4 (o painel "Cobranças"
  novo) → US5 (o total). Cada uma com o seu commit `feat(299): …` e os cenários do verify em verde.
- **Publicação**: um deploy só, com a feature inteira, fora do horário e depois da conferência de
  dados do T045.

## Phase 9: Convergence

- [X] T046 CRITICAL — Pôr type hints nos parâmetros que a 299 acrescentou a `_validate_event_core`
  (`valor_atual: Decimal | None = None`, `bruto_atual: Decimal | None = None`) em
  `app/calendar/routes.py:3222-3224` per Constitution II (contradicts)
- [X] T047 CRITICAL — Tirar da view `api_update_event_comercial` (`app/api/agenda_write.py:1076-1084`)
  a regra do valor da aba Comercial (o `if not data["is_cortesia_permuta"]` e o `vazio_aceito=True`)
  para uma função do núcleo em `app/calendar/event_ops.py`, deixando a view só chamar e serializar;
  o `verify_299` (5i e 6) continua 17/17 per Constitution III (contradicts)
- [X] T048 Em `_sync_commission_payment` (`app/financeiro/comissoes_ops.py:742-753`), ignorar a linha
  de R$ 0,00 já paga só quando a comissão calculada agora é maior que zero (calcular o `amount` antes
  da consulta): hoje toda linha de R$ 0,00 paga é ignorada, e uma venda real com comissão de R$ 0,00
  ganharia uma linha `a_pagar` nova a cada pagamento; os cenários 5g, 5h e 5h' do `verify_299`
  continuam verdes per FR-031 (partial)
- [X] T049 Invalidar `['dashboard']` no `onSuccess` de `useDeleteEvent`
  (`frontend/apps/internal/src/lib/eventOps.ts:65-77`), para o evento excluído sair de "Cobranças" e
  "Sem valor" ao voltar para a Home per FR-010 (partial)
- [X] T050 No outro evento do grupo, usar o título do principal (`grupo.leader.title`) como texto do
  link de "A venda está no …" em
  `frontend/apps/internal/src/components/EventDetail/FinanceiroSection.tsx:250-257` per
  contracts/evento-cobranca.md (partial)
- [X] T051 Corrigir o rodapé do painel "Sem valor"
  (`frontend/apps/internal/src/components/home/PainelSemValor.tsx:106`), que diz "fora cortesia e
  compromisso interno" e omite ensaio, Loja Virtual, cancelados e os outros eventos do grupo: listar
  todas as exclusões ou tirar o texto per FR-006 (partial)
- [X] T052 Decidir o detalhe do card "Sem valor" ("N eventos sem valor desde …",
  `frontend/apps/internal/src/pages/DashboardPage.tsx:789`), que nenhum requisito pede: manter e
  registrar no `docs/02` (Home) ou tirar per FR-028 (unrequested) *(Mantido: espelha o "N formulários
  sem evento desde DD/MM" do card de Formulários da 298; registrado no `docs/02`.)*
- [X] T053 Na edição completa, não gravar 0 por cima do bruto `NULL`:
  `frontend/apps/internal/src/pages/EventEditPage.tsx:139` hidrata `sale_value_gross ?? 0`, e uma
  troca só de título grava 0; mandar `null` quando o bruto gravado é `NULL` e ninguém mexeu nele per
  T029 (partial)
- [X] T054 Somar o `total_em_aberto` em `Decimal` a partir das vendas (`venda.saldo`), e não do `saldo`
  já serializado em `float` (`app/financeiro/cobranca_ops.py:513`) per plan: dinheiro em Decimal até a
  serialização (partial)
- [X] T055 Marcar como desatualizada a armadilha "Comissão diverge entre Jinja e React" do
  `docs/04_GUIA_DE_DOMINIOS.md:166-170`: hoje `update_event_core` e `update_event_comercial` chamam a
  sincronização da comissão (`app/calendar/event_ops.py:887-897, :1071-1073`), e o texto contradiz o
  invariante 12 logo acima per Docs a atualizar: docs/04 (partial)

## Phase 10: Convergence

- [X] T056 Tratar a cortesia na página do evento: tirar o "— falta R$ 0,00" que hoje aparece em toda
  cortesia (`frontend/apps/internal/src/components/EventDetail/FinanceiroSection.tsx:275-283`, com
  `quitado` falso e `outstanding` 0), e decidir o "Quitado" da cortesia antiga com valor, que a 299
  tirou (`app/financeiro/cobranca_ops.py:159`, `and not self.cortesia`); registrar a cortesia em
  `contracts/evento-cobranca.md` (Tela) e em `data-model.md` (`quitada`) per contracts/evento-cobranca.md
  + FR-023 (partial) *(Dono: seguir a sugestão — a cortesia diz "cortesia ou permuta", sem "falta" nem
  "Quitado"; chave `cobranca.cortesia` nova.)*
- [X] T057 Alinhar o FR-007 e o FR-018 ("dentro dela, ele continua podendo aplicar um orçamento, como
  hoje") com a tela: o `OrcamentoPanel`
  (`frontend/apps/internal/src/components/EventDetail/ComercialSection.tsx:531-534`) só abre com
  `can_edit_core` (COMERCIAL ou SUPERADMIN, `app/api/agenda_read.py:179`), como na `main`, e o
  FINANCEIRO só aplica pela API. Corrigir `spec.md`, `docs/02` e o contrato para o que a tela faz, ou,
  com o OK do dono, abrir o painel pelo mesmo gate de `_can_manage_sale` per FR-007/FR-018
  (contradicts) *(Dono: deixar como está — abrir só o painel daria uma busca que falha; FR-007,
  FR-018 e `docs/02` corrigidos.)*
- [X] T058 No 400 do `PATCH /comercial`, marcar o campo que o servidor nomeou (bruto ou valor final)
  e levar o foco até ele, como a edição completa faz com `primeiroCampoDoErro`; hoje o erro cai
  sempre no valor final (`frontend/apps/internal/src/components/EventDetail/ComercialSection.tsx:223-266`)
  per FR-014 (partial)
- [X] T059 Invalidar `['dashboard']` em `useSetEventClients`
  (`frontend/apps/internal/src/lib/eventInline.ts:117-119`), para o nome da cliente da linha de
  "Cobranças" e "Sem valor" trocar ao voltar para a Home per FR-010 (partial)
- [X] T060 Em `_ciclo_da_comissao_comum` (`app/financeiro/comissoes_ops.py:713-730`), não herdar a
  data de realização da EducaManto quando o evento sai desse ramo (título sem "(EDU", responsável
  EducaManto desligado): no ramo comum, só a data que a 299 gravou (valor que chegou depois) fica;
  antes da 299 ela voltava a `NULL` per R22/T024 "EducaManto: sem mudança" (unrequested)
- [X] T061 Restringir à comissão comum o corte da linha de R$ 0,00 já paga
  (`_comissao_existente`, `app/financeiro/comissoes_ops.py`): na EducaManto, uma linha paga em zero
  por lucro zero, com o lucro corrigido depois, faria nascer uma `a_pagar` com a data do evento,
  talvez num mês já fechado; ou registrar a regra larga no `docs/04` com o OK do dono per
  R42/T024 (unrequested) *(Dono: cortesia nunca comissiona — travado em `should_have`, cenário 15;
  e a EducaManto fica fora do corte.)*
- [X] T062 Corrigir o `contracts/evento-cobranca.md`: `vencimento_origem` pode ser `null` (evento sem
  data do grupo; `:29`, e também `data-model.md:29`), e `grupo_tamanho` é 0 no avulso cancelado, não
  "1 no avulso" (`:31`) per contracts/evento-cobranca.md (partial)
- [X] T063 Levar as regras das T047 e T048 para os artefatos: o bloco R42 de
  `contracts/api-eventos-valor.md` (`:46-52`) e do `research.md` (`:545-553`) ganha "só quando a
  comissão calculada é maior que zero", e o `data-model.md` (`:91-92`) passa a apontar a regra do
  `/comercial` em `event_ops.erros_do_valor_na_aba_comercial` per Constitution VII (partial)

## Phase 11: Convergence

- [ ] T064 No outro evento de um grupo cujo principal está sem valor, mostrar "Recebido no grupo R$ X
  · valor de venda a definir" no lugar de "de R$ 0,00 — falta R$ 0,00" (ramo `grupo_outro` de
  `ResumoDoRecebido`, `frontend/apps/internal/src/components/EventDetail/FinanceiroSection.tsx:263-268`,
  que só trata a cortesia); acrescentar a variante ao `contracts/evento-cobranca.md` (Tela) e ao
  `docs/02` per US1/AC6 + contracts/evento-cobranca.md (partial)
- [ ] T065 No principal sem valor, mostrar também "Inclui R$ X em comprovantes de outros eventos do
  grupo" (`<OutrosDoGrupo>` no ramo `sem_valor` de `ResumoDoRecebido`, `FinanceiroSection.tsx:284`),
  como os ramos normal e de cortesia fazem per contracts/evento-cobranca.md (partial)
- [ ] T066 Em `update_event_comercial` (`app/calendar/event_ops.py:1084-1086`), manter a data da venda
  já gravada quando o valor fica vazio (passar `a_definir` ao `resolver_data_da_venda`, fora a
  cortesia), para nenhuma edição da aba Comercial apagar a data per FR-017 (partial)
- [ ] T067 Trocar a adivinhação de `_data_herdada_da_educamanto` (`app/financeiro/comissoes_ops.py`,
  data do evento + troca de vendedor) por uma marca explícita: quando `_ciclo_da_comissao_comum` grava
  `payable_from = hoje` (valor que chegou depois), registrar isso na linha (por exemplo, uma nota
  constante em `notes`), e no ramo comum manter a data gravada só com essa marca; sem ela, a data veio
  da EducaManto e volta a `NULL`. Cobre o falso positivo (valor posto no dia do evento, depois troca de
  vendedor) e o falso negativo (responsável EducaManto = vendedor) per FR-031 + contracts/api-eventos-valor.md
  (contradicts)
- [ ] T068 Levar para o FR-031 a regra "cortesia nunca comissiona, mesmo a antiga com valor gravado"
  (Session 2026-09-15) e corrigir o "Fora de escopo" (`specs/299-sem-valor-cobrancas/spec.md:723-724`,
  "Na comissão, a única mudança é o ciclo do FR-031") per Session 2026-09-15 (contradicts)
- [ ] T069 Corrigir no `docs/02_MAPA_DE_PAGINAS_E_UX.md` a frase `:464` ("Só quem pode gerir a venda
  (`_can_manage_sale`) vê os botões" — são COMERCIAL e SUPERADMIN, `can_edit_core`; o FINANCEIRO vê o
  painel só para leitura) e o parêntese `:471` ("badge Quitado quando recebido ≥ venda" — agora é o
  recebido do grupo, com a folga de R$ 1,00, e nunca na cortesia) per Docs a atualizar: docs/02
  (contradicts)
- [ ] T070 Acrescentar `cortesia` à lista de chaves novas de `cobranca` no `docs/01_SISTEMA_E_BANCO.md`
  (`:741`), com a nota de que a cortesia nunca é `quitado` per Docs a atualizar: docs/01 (partial)
