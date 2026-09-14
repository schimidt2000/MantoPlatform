# Pesquisa — Feature 299 (Phase 0)

Feita em 14/09/2026, em duas rodadas de leitura do código na `main`, que já inclui a 298:
- **Primeira rodada**: três leitores e um crítico mapearam cobranças, grupos e valor.
- **Segunda rodada**: seis leitores e um crítico desenharam o núcleo, a página do evento, o "valor a
  definir", a tela da Home, o contrato do painel e o verify.

Os números de produção foram lidos só para consulta em 14/09. Nenhuma incógnita do contexto técnico
ficou aberta: as quatro decisões de produto que a pesquisa levantou foram respondidas pelo dono no
mesmo dia (R7, R8, R22, R25).

## O que o código faz hoje (fatos que o plano precisa respeitar)

- **Cobranças da Home** (`app/api/dashboard_service.py:270-361`):
  - **Filtros.** Entra `sale_value > 0`, com início a partir do corte (`dashboard_cutoff`, `:19-23`:
    `release_date` ou `date.today()` em UTC), título fora de `'🟧 ENSAIO%'` e evento não cancelado.
    Não exclui cortesia, Loja Virtual, satélite (só escapa porque agrupar zera a venda,
    `group_ops.py:47-52`) nem o marcador 🟠.
  - **Conta.** O recebido soma só os comprovantes do próprio evento (`:299-307`), em float
    (`:311-313`), sem folga de centavos. A data combinada só vale em `futuro`/`faturado` (`:319-321`).
    A venda com metade paga e evento a mais de 2 dias some por um `continue` (`:328-331`).
  - **Saída.** Severidades em inglês e cruas (`:267`); a tela mostra `severity.toUpperCase()`
    (`DashboardPage.tsx:363-365`).
  - **Chamada.** Única, em `:567`, dentro de `_bloco("comercial")`.
- **Cobrança da página do evento** (`app/api/agenda_read.py:401-421`, chamada em `:974`):
  - **Conta.** Recebido só do próprio evento. Com cronograma, o saldo é a soma das parcelas não
    recebidas. `payment_due_date` vale em qualquer forma. O relógio é `date.today()` (UTC no Render).
  - **Mensagem.** `_serialize_mensagens` (`:635-661`) monta o texto de cobrança com `outstanding` e
    `due`.
  - **Satélite.** Sai "Recebido X de R$ 0,00" (`FinanceiroSection.tsx:216-228`), com o saldo
    negativo.
- **Grupo** (`app/calendar/group_ops.py`):
  - **Estrutura.** É uma estrela por `group_leader_id`, sem tabela. O principal é quem tem
    satélites (`models.py:397-410`).
  - **Ao agrupar.** Zera 14 campos comerciais do satélite, mas não move nem apaga comprovantes,
    parcelas, notas e contratos (`:47-52, 96-99`).
  - **`group_events`** (`:64-75`) devolve `[principal, *satélites]`, cancelados inclusive; ele quebra
    com o principal `None`.
  - **Cancelamento.** O principal não pode ser cancelado com satélites (`cancel_ops.py:260-270`), mas
    o sync do Google o apaga sem essa trava (`calendar/routes.py:352-385`).
- **Peças prontas**:
  - `contratante_name` (Contratante > 1ª cliente > `client_id`, `vendas_ops.py:81-93`);
  - `is_loja_virtual` (`:197-205`) e `NON_SALE_EVENT_TYPE` (`:41`);
  - `_is_permuta` (`financeiro/routes.py:125-126`);
  - `corte_dia_sp` (`formularios_ops.py:86-91`) e `now_sp` (`constants.py:290-301`);
  - `FORM_COR_VERMELHO_ATE_DIAS` e `FORM_COR_AMARELO_ATE_DIAS` (`constants.py:404-405`).
- **Armadilha do NULL.** `list_closed_sales` filtra `event_type != 'ENSAIO'` (`vendas_ops.py:168`),
  e `NULL` cai fora: descarta a venda sem tipo (o 395, de R$ 35.000). A 299 não repete isso.
- **Valor obrigatório.** Hoje é exigido em três lugares:
  - o Zod (`eventFormSchema.ts:17-18, 28-35`, `z.number()` com default 0);
  - `_validate_event_core` (`calendar/routes.py:3264-3268`), chamado por POST, PATCH em bloco,
    `/basico` (que filtra os erros) e a criação Jinja;
  - a edição completa, que troca nulo por 0 (`EventEditPage.tsx:125-127`).

  O `PATCH /comercial` não valida e aceita nulo (`agenda_write.py:1033-1065`).
- **Foco.** Os `MoneyInput` de valor não têm `id` nem `ref` (`ValoresBlock.tsx:60-74`), então o efeito
  de foco (`EventCreatePage.tsx:373-383`) não os acha. O 400 do servidor não leva foco (`:481-493`).
- **Comissão.** `_sync_commission_payment` (`comissoes_ops.py:689-747`):
  - cria a linha quando há valor e cancela a `a_pagar` quando o valor sai;
  - o ciclo de pagamento é `coalesce(payable_from, sale_date, created_at)` (`:190-216`);
  - `payable_from` só é usado pela EducaManto (`:720-744`) e é reescrito como `NULL` a cada
    sincronização nas comissões comuns (`:736`).
- **Cache do front.** `staleTime` de 30 s, sem refetch no foco (`queryClient.ts:39-40`). Salvar
  valor, comprovante, orçamento, criar e cancelar não invalidam `['dashboard']`.
- **App interno.** Sem ErrorBoundary: um `TypeError` no render deixa a Home em branco.

## Decisões

### R1 — O núcleo mora em `app/financeiro/cobranca_ops.py` (novo)

- **Decisão**: módulo puro novo, fonte única da Home e da página do evento. Importa de `vendas_ops`,
  de `calendar.group_ops` e, por import tardio, `_is_permuta`, como `vendas_ops` já faz (`:244`).
- **Porquê**: Princípios I e III. A direção financeiro → calendar é a permitida
  (`group_ops.py:29-31`). `vendas_ops` é o núcleo do funil, que continua por evento pela spec.
  `dashboard_service` é agregador em `app/api`.
- **Alternativas**:
  - estender `vendas_ops`: mistura funil e cobrança num arquivo que cresceria para ~550 linhas;
  - `app/calendar/cobranca_ops.py`: inverte a dependência;
  - dentro do `dashboard_service`: viola o Princípio III.

### R2 — Constantes e o predicado `sem_valor_de_venda`

- **Decisão**:
  - **Constantes em `app/constants.py`**:
    - `VALOR_MINIMO_DE_VENDA = Decimal("1.00")` e `FOLGA_COBRANCA = Decimal("1.00")`, dois nomes
      para o mesmo valor;
    - `SALDO_VENCE_DIAS_ANTES = 2`;
    - `MARCADORES_COMPROMISSO_INTERNO = ("🟧", "🟠")`;
    - `COBRANCA_COR_VERMELHO_ATE_DIAS = 2` e `COBRANCA_COR_AMARELO_ATE_DIAS = 30`;
    - os textos dos selos.
  - **Predicado.** `sem_valor_de_venda(valor: Decimal | None) -> bool` (vazio, zero ou abaixo de
    R$ 1) mora em `app/calendar/event_ops.py`, e o `cobranca_ops` o importa.
  - **Front.** Nunca compara com 1: recebe `sem_valor`/`valor_simbolico` do servidor.
- **Porquê**:
  - O orçamento (`orcamento_evento_ops.py:284, 404`) precisa do predicado e é calendar.
  - Com dois nomes, mudar o valor simbólico não muda a folga sem querer.
  - Princípio II.
- **Alternativas**: o predicado no `cobranca_ops`, que o calendar não alcança; uma constante espelhada
  no front, que viola o Princípio I.

### R3 — Uma fonte para o recebido do grupo

- **Decisão**:
  - **Primitiva.** `recebido_por_evento(ids) -> dict[int, Decimal]` no `cobranca_ops`: `SUM(coalesce(amount, 0))`
    com `GROUP BY event_id`, e `Decimal(str(x))` como `cancel_ops.py:54`.
  - **Soma do grupo.** `recebido_da_venda(eventos, mapa)` soma principal e satélites, **inclusive os
    cancelados**.
  - **Consultas.** A Home faz uma consulta para todos os ids do lote. A página faz uma para os ids do
    grupo e reusa o mapa para `outros_do_grupo`.
  - **O que fica como está** (spec: relatórios financeiros fora de escopo), registrado no `docs/05`
    como candidato a delegar para a primitiva:
    - `received_map` (`vendas_ops.py:118-131`);
    - `total_recebido` (`cancel_ops.py:47-54`);
    - o "a receber" (`financeiro_read.py:306-318`).
- **Porquê**:
  - SC-003: Home e página pela mesma soma.
  - FR-001/FR-004: o comprovante do satélite cancelado conta.
  - Princípio IX.
- **Alternativas**:
  - SQL por `coalesce(group_leader_id, id)`: serve à Home, mas a página precisaria de outra soma
    para o detalhamento;
  - `group_events` + `IN` por venda: N+1 na Home;
  - fazer `received_map` delegar agora: toca o funil, que está fora de escopo.

### R4 — O tipo `VendaResumo`

- **Decisão**: `@dataclass(frozen=True)` com:
  - `principal`;
  - `eventos` (principal primeiro, cancelados inclusive);
  - `valor: Decimal | None` e `recebido: Decimal`;
  - `data_do_grupo: date | None`;
  - `vencimento: date | None` e `vencimento_origem` (`"data_combinada" | "parcela" | "politica"`);
  - `cliente: str | None`;
  - `motivo_fora: str | None`.

  Propriedades derivadas:
  - `saldo`;
  - `sem_valor` e `valor_simbolico`;
  - `sinal_pendente`;
  - `situacao` (`"fora" | "sem_valor" | "quitada" | "com_saldo"`);
  - `eventos_vivos`.

  Nenhum número depende de "hoje": cor, selo e dias vêm de funções que recebem `hoje`.
- **Porquê**: os mesmos números servem às duas listas e à página. É testável sem request e fica em
  `Decimal`.
- **Alternativa**: dicts soltos por consumidor, que é como nasceram as duas cópias de hoje.

### R5 — Principal e data do grupo

- **Decisão**:
  - `principal_da_venda(event)` devolve `group_leader` quando existe; senão o próprio evento, o que
    também cobre o principal apagado.
  - `data_do_grupo(eventos)` é o menor `start_at.date()` entre os **não cancelados**, comparado como
    hora de parede de São Paulo.
  - Essa data vale para o corte, para a partição, para os 2 dias antes e para a linha.
- **Porquê**: FR-002 e os casos de borda; `group_events` quebra com o principal `None`.
- **Alternativa**: a data do principal, que quebra o cenário 4 da História 1.

### R6 — Quem fica fora (`motivo_fora_da_venda`)

- **Decisão**: uma função em Python, nesta ordem:
  1. cancelado;
  2. ensaio (`event_type == NON_SALE_EVENT_TYPE`, com `None` = não é ensaio);
  3. compromisso interno (`title.lstrip().startswith(MARCADORES_COMPROMISSO_INTERNO)`);
  4. cortesia (`_is_permuta`);
  5. Loja Virtual (`is_loja_virtual`).

  Nenhum filtro de negócio no SQL. Vale para as duas listas e para o `enabled` da página.
- **Porquê**: FR-006/FR-019; a armadilha do `NULL`; uma fonte só para o recorte de canal.
- **Alternativa**: filtros SQL espalhados, que repetem a regra e caem no `NULL`.

### R7 — Ordem do vencimento (dono, 14/09)

- **Decisão**:
  1. a data combinada (`payment_due_date` do principal, em qualquer forma de pagamento);
  2. senão, a primeira parcela não recebida **do principal**;
  3. senão, a data do grupo menos `SALDO_VENCE_DIAS_ANTES`.

  A origem sai em `vencimento_origem`. As parcelas antigas que ficaram no satélite são ignoradas.
- **Porquê**: resposta do dono. Combina com o caso de borda "data combinada que sobrou vale mesmo
  assim".
- **Alternativa**: a parcela antes da data combinada, como a página faz hoje; o dono não escolheu.

### R8 — Saldo, sinal e folga (dono, 14/09)

- **Decisão**:
  - `saldo = valor do principal − recebido do grupo`, também com cronograma; as parcelas só dão a
    data.
  - A linha existe só com `valor >= VALOR_MINIMO_DE_VENDA` e `saldo >= FOLGA_COBRANCA`.
  - `sinal_pendente = sem data combinada E recebido < valor/2 − FOLGA_COBRANCA`, em `Decimal` com
    `quantize(0.01, ROUND_HALF_UP)`.
  - Com data combinada, não há sinal pendente.
- **Porquê**: FR-021/FR-022/FR-023, SC-003 e as respostas do dono.
- **Alternativa**: manter o saldo pela soma das parcelas na página, o que quebra o SC-003.

### R9 — Régua de cor e selo

- **Decisão**:
  - **Régua.** Uma função, `cor_por_distancia(dias, *, vermelho_ate, amarelo_ate)`, com o passado
    sempre vermelho:
    - as cobranças usam 2/30;
    - o sinal pendente sobe cinza para amarelo e nunca rebaixa vermelho;
    - a lista sem valor usa `FORM_COR_*` (7/30).
  - **Selo.** Em pt-BR, vindo do servidor, nesta precedência:
    1. "Atrasado" (dias < 0);
    2. "Vence hoje";
    3. "Sinal pendente";
    4. "Vence em N dias" ("Vence em 1 dia" no singular).
  - **Ordem.** Vencimento ascendente, com desempate pela data do grupo e depois pelo `event_id`.
  - **298.** `destino_ops.severidade` (298) fica intacta.
- **Porquê**: FR-009/FR-025/FR-026 e o clarify. A régua da 298 pinta o passado de amarelo e está em
  produção (IV).
- **Alternativas**: uma função por lista, o que daria três réguas; parametrizar a da 298, o que toca
  um painel em produção.

### R10 — Lote da Home

- **Decisão**: `vendas_desde(corte) -> list[VendaResumo]`:
  - **Q1.** Eventos com `group_leader_id IS NULL`, `cancelled_at IS NULL` e
    `start_at >= combine(corte, time.min)`, com `selectinload` de `satellites`,
    `event_clients.client` e `installments`, e `joinedload(client)`.
  - **Mais uma consulta.** `recebido_por_evento` sobre todos os ids, satélites inclusive.
  - **Em Python.** Reconferir `data_do_grupo >= corte` e aplicar `motivo_fora`.
- **Porquê**: o pré-filtro é seguro, porque com o principal vivo `data_do_grupo <= start_at` do
  principal. Evita N+1 (`models.py:329-332, 348-351, 365-368, 403-405`).
- **Alternativa**: carregar "alguns dias antes, com cancelados", mais caro e sem ganho.

### R11 — Hoje e corte

- **Decisão**: `build_dashboard_summary` resolve `hoje = now_sp().date()` e
  `corte = corte_dia_sp()` uma vez, e passa os dois. `dashboard_cutoff` e `_base_filters` ficam
  intactos, porque servem casting, figurino, ensaio, dispensados e os convites
  (`invite_reminders.py:66-76`). A página troca `date.today()` pelo hoje de São Paulo.
- **Porquê**: o mesmo corte das três listas e o relógio da casa.
- **Alternativa**: mudar `dashboard_cutoff`, que é escopo lateral.

### R12 — Contrato das cobranças

- **Decisão**:
  - **Lista.** `comercial.pending_payments` continua sendo a **única** lista de cobranças e só
    cresce por acréscimo.
  - **Chaves antigas mantidas**:
    - `event_id` (o principal), `event_title` e `start_at`;
    - `sale`, `received` e `saldo`, agora pelo grupo;
    - `severity`, mapeada da cor na união antiga;
    - `due_date`.
  - **Chaves novas**, opcionais no TS: `titulo`, `cliente`, `data_evento`, `vencimento`,
    `vencimento_origem`, `dias_ate_vencimento`, `sinal_pendente`, `severidade`, `selo` e
    `grupo_comercial`.
  - **Resumo ao lado.** `cobrancas_resumo {por_cor, para_agir, total_em_aberto}`.
  - **Dinheiro** como número JSON.

  Detalhe em [contracts/dashboard-comercial.md](./contracts/dashboard-comercial.md).
- **Porquê**: Princípio IV. O bundle antigo lê `pending_payments`/`severity` sem proteção. Número,
  porque `formatBRL` só aceita `number`.
- **Alternativas**: uma lista nova com `pending_payments` derivado, o que dobra o payload; dinheiro em
  string, o que quebra o bundle antigo.

### R13 — Contrato da lista "Evento sem valor de venda"

- **Decisão**: `comercial.sem_valor {por_cor, para_agir, a_acontecer, ja_aconteceu}`. Cada
  `LinhaSemValor` traz:
  - `event_id` (o principal), `titulo`, `cliente` e `grupo_comercial` (eventos vivos);
  - `data_evento` e `dias_ate_o_evento`;
  - `valor` (`null` = a definir), `valor_simbolico` e `recebido`;
  - `severidade`.

  Nenhum texto de dinheiro pronto. A lista vem inteira.
- **Porquê**: FR-005/FR-007/FR-008/FR-011; Princípio IX; o verify precisa achar a linha semeada.
- **Alternativa**: `valor_rotulo` pronto, que formata dinheiro no servidor.

### R14 — Montagem no `dashboard_service`

- **Decisão**:
  - **Montagem.** `_painel_comercial()` dentro de `_bloco("comercial")` chama `vendas_desde` uma vez
    e divide o resultado. A serialização de `sem_valor` roda num `_bloco("sem_valor")` interno.
  - **Saída.** `pending_payments` sai sempre como lista.
  - **O que é substituído.** `compute_comercial_pending`, `serialize_comercial_pending` e
    `_SEVERITY_ORDER`, que só são chamados em `:567`.
- **Porquê**: um defeito na lista nova não esconde as cobranças.
- **Alternativa**: dois `_bloco` irmãos, que obrigaria a derivar `pending_payments = []` na falha.

### R15 — Total do topo e "R$ X em aberto"

- **Decisão**:
  - **Servidor.** Manda `para_agir` (vermelho + amarelo, contando **linhas**) em
    `cobrancas_resumo`, em `sem_valor` e, por acréscimo, em `formularios.para_agir`.
  - **Front.** `SectionStat` ganha `noTotal`: `para_agir` nas três listas comerciais e `count` nos
    painéis de operação.
  - **Card.** Continua mostrando todas as linhas.
  - **Em aberto.** "R$ X em aberto" vem de `total_em_aberto`.
  - **Servidor antigo** (sem `para_agir`): `noTotal = count`.
- **Porquê**: FR-029 (clarify) e Princípio III: a regra de quais cores contam fica no servidor, e o
  verify a enxerga.
- **Alternativas**: contar por cor no front, que põe regra na tela; mudar o `count` do card, que muda
  o significado dele.

### R16 — Cobrança na página do evento (FR-003)

- **Decisão**:
  - **Adaptador.** `_compute_cobranca` vira um adaptador de `resumo_da_venda_do_evento(event)`.
    `enabled` vem de `pode_copiar_cobranca(resumo, event, hoje)`: vencido, saldo acima da folga,
    valor de venda de verdade, fora de nenhuma exclusão, e o evento aberto não é satélite.
  - **Chaves antigas**:
    - `outstanding = max(saldo, 0)`;
    - `due`;
    - `enabled`.
  - **Opcionais novas**: `valor`, `recebido`, `quitado`, `sem_valor`, `valor_simbolico`,
    `sinal_pendente`, `vencimento_origem`, `escopo` e `grupo_tamanho`.
  - **Ponteiro do principal.** Continua sendo `event.group.leader` (`agenda_read.py:572-580`).
  - **Pagamentos.** `pagamentos.received_total` continua do próprio evento, e entra
    `pagamentos.outros_do_grupo`.
  - **Mensagens.** `_serialize_mensagens` não muda.
- **Porquê**: História 1, cenários 5 e 6. A mensagem sai com os personagens e a data do evento aberto
  (`:647-648`), então quem cobra é o principal. A regra sai da camada de API.
- **Alternativas**: `principal_id` dentro de `cobranca`, um ponteiro duplicado; `received_total` com a
  soma do grupo, que quebra a lista de comprovantes ao lado.

### R17 — O valor simbólico conta como "sem venda" (FR-018)

- **Decisão**:
  - **Payload.** `venda.sem_valor?` e `venda.valor_simbolico?` no detalhe. O `OrcamentoPanel` usa
    `venda.sem_valor ?? (!venda.sale_value && !venda.is_cortesia_permuta)` (`ComercialSection.tsx:512,
    530`).
  - **Servidor.** `orcamento_evento_ops.py:284` e `:404` trocam `event.sale_value` por
    `not sem_valor_de_venda(...)`, com a trava de cortesia antes, que o `verify_273` exige.
  - **Commit.** Front e servidor vão no mesmo commit.
- **Porquê**: se só o front mudar, o botão aparece e o servidor recusa com "evento já tem venda".
- **Alternativa**: um limite no front, que viola o Princípio I.

### R18 — O protocolo do "Valor a definir"

- **Decisão**:
  - **Chave.** Opcional, `valor_a_definir: boolean`, no corpo de `POST /api/events` e de
    `PATCH /api/events/<id>`, e **não gravada**. Os adaptadores a repassam
    (`agenda_write.py:696-730, 854-878`).
  - **Helper.** `aplicar_valor_a_definir(data)` (`event_ops`) zera `sale_value` e `sale_value_gross`
    quando a marca vem sem cortesia.
  - **Validação.** `_validate_event_core` pula os dois erros de valor.
  - **Precedência.** A cortesia vence a marca.
  - **Sem mudança.** Jinja e `/basico` não mandam a chave.
- **Porquê**: distingue esquecimento de intenção (o FR-014 exige 400 sem a marca). Compatível nos
  dois sentidos:
  - **bundle antigo, servidor novo**: vale a regra de hoje;
  - **bundle novo, servidor antigo**: 400 antes do Google (`agenda_write.py:761` contra `:793`).
- **Alternativa**: `null` sozinho como "a definir", que não distingue esquecimento.

### R19 — Tela do cadastro e da edição

- **Decisão**:
  - **Schema.** `valor_a_definir: z.boolean()` no schema e em `DEFAULT_EVENT_FORM_VALUES`. Os
    refines aceitam `cortesia || valor_a_definir || valor > 0`, com a mensagem "Informe o valor de
    venda ou marque “Valor a definir”."
  - **Botão.** De alternar, no padrão da cortesia e excludente com ela, escondendo os valores pelo
    mesmo `AnimatePresence`.
  - **Foco.** `MoneyInput` via `Controller`, com `id` e `ref`. No `onError`, foco e rolagem até o
    primeiro campo de `error.fields`, na ordem de `FIELD_ORDER`.
  - **Corpo.** Manda `null` com a marca.
  - **Hidratação.** A edição abre marcada só com valor `null` ou 0 e sem cortesia; **o R$ 0,01 abre
    desmarcado**.
  - **Aviso.** Marcar num evento com valor mostra, no lugar, "o valor de R$ X será apagado e a
    comissão a pagar, cancelada".
- **Porquê**: FR-012 a FR-015; Princípio V; não apagar o R$ 0,01 numa troca de título.
- **Alternativas**:
  - hidratar por `venda.sem_valor`, que apaga o 0,01 no primeiro salvamento;
  - diálogo de confirmação, excessivo para uma marca que se desfaz antes de salvar.

### R20 — Vendedor e satélite na edição completa

- **Decisão**:
  - **Vendedor.** Continua obrigatório no cadastro e na edição (FR-016). O evento importado sem
    vendedor mostra o campo apontado e com foco, sem bloqueio silencioso.
  - **Satélite, núcleo.** `update_event_core` deixa de gravar os campos comerciais: valores,
    vendedor, pagamento, cortesia, data da venda e demais.
  - **Satélite, validação.** `_validate_event_core` pula valor e vendedor.
  - **Satélite, tela.** A marca abre travada, com o link para o principal.
- **Porquê**: sem isso, a marca abrindo sozinha deixaria o satélite salvar vendedor e pagamento que o
  agrupamento zera de propósito (`group_ops.py:45-52`). O `/comercial` já recusa satélite
  (`agenda_write.py:1026-1031`). A regra fica no núcleo (III).
- **Alternativas**: dispensar o vendedor com "a definir", o que deixa a comissão sem beneficiário;
  regra do satélite no endpoint, que viola o Princípio III.

### R21 — Data da venda com "Valor a definir" (FR-017)

- **Decisão**: `resolver_data_da_venda` (`event_ops.py:652-684`) ganha `a_definir: bool = False`.
  - Na **criação**, sem data informada, devolve hoje em São Paulo.
  - Na **edição**, mantém `data_atual` antes do ramo `not venda → None`.
- **Porquê**: sem isso, o evento "a definir" fica sem data, ou perde a data numa edição.
- **Alternativa**: confiar que o front sempre manda a data; ele manda `''` quando o campo está vazio.

### R22 — Comissão no mês em que o valor entra (dono, 14/09; FR-031)

- **Decisão**: em `_sync_commission_payment` (`comissoes_ops.py:689-747`), para a comissão **comum**:
  - **Linha nova.** Quando nasce com `sale_date` num mês anterior ao mês corrente de São Paulo,
    recebe `payable_from = hoje` (SP).
  - **Sincronização.** Não volta a `NULL` nas sincronizações seguintes; hoje ela é reescrita em
    `:736`.
  - **Sem mudança.** A comissão EducaManto continua pela data da realização, e a linha já paga não
    muda.
- **Porquê**: a comissão nunca cai num ciclo já pago, e o ciclo continua saindo de
  `coalesce(payable_from, sale_date, created_at)`, que é a mesma expressão que monta e liquida a
  planilha.
- **Alternativas**:
  - comissão no mês do cadastro, que pode cair em mês fechado;
  - trocar a data da venda, que muda os relatórios.

### R23 — Invalidar a Home (FR-010)

- **Decisão**: invalidar `['dashboard']` por prefixo (a query é `['dashboard', periodo]`,
  `DashboardPage.tsx:984`) em:
  - `useUpdateEventComercial`, pelo parâmetro `invalidar` (`eventInline.ts:98-100`);
  - `useSetEventOrcamento` (`:142-147`);
  - os hooks de comprovante (`eventAttachments.ts:107-124`);
  - `useCreateEvent` e `useUpdateEvent` (`eventCreate.ts:190-222`);
  - `useCancelarEvento` (`eventOps.ts:139-144`);
  - o fim da fase 2 de anexos do cadastro (`EventCreatePage.tsx:316-324`).
- **Porquê**: com `staleTime` de 30 s e sem refetch no foco, a linha resolvida fica na tela.
- **Alternativa**: diminuir o `staleTime` da Home, que dá mais carga sem garantia.

### R24 — Componentes da Home

- **Decisão**: **extrair** da 298, sem mudar comportamento:
  - `GrupoDeLinhas<T>`, do `GrupoFormularios` (`DashboardPage.tsx:643-692`);
  - `LinhaDaHome`, a casca da linha (`:504-546`);
  - `BotaoMostrarTodas` (`:236-242, 681-689`);
  - `Severidade` e os mapas de tom e fundo (`:431-444`);
  - `distanciaDaData` com vocabulário: "passou", "aconteceu" ou "venceu", e "vence" (`:459-466`).

  A `PendingPaymentRow` e os mapas em inglês com fundo inline saem (`:333-377`). Sem `severidade`
  (servidor antigo), a linha fica cinza e sem selo, sem mapa de textos no front.
- **Porquê**: Princípio I, com uma fonte para 6 linhas, "Mostrar todas" e saída animada; XI;
  estilo inline proibido; FR-025.
- **Alternativas**: copiar o `GrupoFormularios`, uma terceira cópia; manter mapas de selo no front,
  uma segunda fonte.

### R25 — Dois painéis e a ação por papel (dono, 14/09)

- **Decisão**:
  - **Painéis.** Dois `SectorPanel`, "Cobranças" (a `SectionKey` `comercial` fica) e "Sem valor"
    (`SectionKey` nova `sem_valor`), no lugar do "💼 Comercial", com card e painel do mesmo nome.
  - **Ação por papel.** `pode_editar_venda` sai pelo mesmo cálculo do `pode_criar_evento` da 298
    (`_CAN_CREATE`, papel efetivo). Sem ele, a ação vira "Abrir".
- **Porquê**: resposta do dono. Reusa `propsSecao`, `irParaSecao` e `painelAberto` sem mapa de painel
  pai. O FINANCEIRO vê o painel, mas não grava o `/comercial` (`agenda_write.py:1024-1025`).
- **Alternativa**: um painel "Comercial" com dois blocos; o dono não escolheu.

### R26 — Compatibilidade na janela de deploy

- **Decisão**:
  - **Bundle antigo, servidor novo.** `pending_payments` sempre lista; `severity` na união antiga,
    derivada da cor:
    - vencido → `atrasado`;
    - vermelho a vencer → `urgent`;
    - amarelo → `warn`;
    - cinza → `info`.

    Valores continuam `number`. As chaves antigas de `cobranca` mantêm nome e tipo.
  - **Bundle novo, servidor antigo.** `sem_valor` ausente: sem painel e sem card, nunca o "✓".
    Linha sem `severidade`: cinza e sem selo. Sem `para_agir`: `noTotal = count`.
  - **Remoção.** `severity` e o formato antigo saem num deploy posterior (`docs/05`).
- **Porquê**: portão da constituição (campo novo opcional) e ausência de ErrorBoundary.

### R27 — Verify

- **Decisão**:
  - **Esqueleto.** O do `verify_298`, com três usuários descartáveis: COMERCIAL, FINANCEIRO e
    CASTING.
  - **Google.** Falsos que **contam**: `routes.insert_event`, `routes.update_event` e
    `service.update_event`. `service.insert_event` e `service.load_credentials` estouram.
  - **Identidade dos dados.** Prefixo `v299-` em `google_event_id`, sem `_`, que é coringa no `LIKE`.
    Título com "[TESTE verify 299] pode apagar", depois do marcador quando o cenário exige.
  - **Conferência.** Dinheiro comparado como `Decimal(str(v))`. O verify confere
    `release_date == 01/06/2026` antes de começar. A linha semeada é achada pelo `event_id`.
  - **Limpeza.** Por `google_event_id LIKE 'v299-%'`, apagando as filhas antes, incluindo
    `commission_payments`.
- **Porquê**:
  - Princípio VIII.
  - A edição completa chega ao Google por outro caminho, fora do stub da 298.
  - O stub da 298 levantava erro, e o cenário 5 precisa criar.

### R28 — O que fica como está (e vai para o `docs/05`)

- A cópia Jinja da cobrança (`calendar/routes.py:1833-1850`), inalcançável pelo `server.js`.
- `dashboard_cutoff` caindo em UTC com `release_date` vazio; as listas comerciais usam
  `corte_dia_sp`.
- `list_closed_sales` com `event_type != 'ENSAIO'`, que descarta a venda sem tipo.
- As somas por evento de `received_map`, `total_recebido` e "a receber".
- A trava do sync do Google, que apaga o principal de um grupo.
- A chave `parcelado` contra `parcelado_datas`.
- A Auditoria de Input com a outra definição de "sem valor".

### R29 — O KPI "Venda" da aba Comercial

- **Decisão**: não muda. Continua 0,00 para valor vazio, porque é a base do lucro, que é relatório
  financeiro fora de escopo. O FR-015 vale para o "Valor de venda final" do `VendaPanel`.
- **Porquê**: escopo da spec.
