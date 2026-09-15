<!-- ADAPTADO PARA A MANTO (2026-09-08) — reaplicar após qualquer atualização do Spec Kit; para este
     arquivo o hash em .specify/integrations/speckit.manifest.json deixa de conferir de propósito. -->
# Plano de implementação: Feature 299 — Sem valor e cobranças

**Branch**: `299-sem-valor-cobrancas` | **Data**: 2026-09-14 | **Spec**: [spec.md](./spec.md)

**Input**: `/specs/299-sem-valor-cobrancas/spec.md`

**Nota**: preenchido pelo `/speckit-plan`. A constituição (`.specify/memory/constitution.md`,
v3.0.0) é lida em tempo de execução — o Constitution Check abaixo é o que ela cobra.

## Resumo

A Home ganha o painel "Sem valor" (vendas desde 01/06 sem valor de venda) e o painel "Cobranças"
passa a tratar o grupo como uma venda só, com vencimento explícito, sem alarme de centavos e com
selos em português. O cadastro aceita "Valor a definir", e a página do evento mostra o mesmo
recebido e o mesmo saldo do grupo que a Home.

**Abordagem** (detalhe em [research.md](./research.md), R1–R29):

1. **Um núcleo puro novo, `app/financeiro/cobranca_ops.py`.** Ele resume cada venda (evento avulso,
   ou grupo pelo principal) num `VendaResumo` em `Decimal`:
   - valor, recebido do grupo e saldo;
   - data do grupo;
   - vencimento e a origem dele;
   - cliente;
   - motivo de ficar fora.

   A Home o chama em lote, com consultas fixas; a página do evento o chama para um grupo. É uma
   fonte só para os dois (SC-003) e substitui as duas cópias de hoje (`dashboard_service.py:270-345`
   e `agenda_read.py:401-421`).
2. **As regras saem da camada de endpoint.** `compute_comercial_pending` e `_compute_cobranca` viram
   adaptadores finos. Cor, selo e dias recebem o "hoje" de São Paulo por argumento.
3. **O contrato cresce só por acréscimo.**
   - `pending_payments` continua sendo a lista de cobranças: mantém as chaves antigas, para o site
     em cache, e ganha as novas.
   - Nasce `comercial.sem_valor`.
   - O total do topo passa a usar `para_agir`, calculado no servidor.
4. **"Valor a definir" é uma marca no corpo do POST/PATCH, e não é gravada.** O servidor grava o valor
   vazio e pula a validação. Se a comissão nasce num mês posterior ao da data da venda, ela entra no
   ciclo do mês do valor (`payable_from`, o mesmo mecanismo da EducaManto).
5. **A Home extrai da 298 as peças de lista**: grupo com 6 linhas e saída animada, cores e distância
   em palavras. Com elas monta dois painéis, "Cobranças" e "Sem valor".

**Mudanças de comportamento deliberadas**:
- **Página do evento com cronograma**: o saldo passa a ser valor menos recebido do grupo, e as
  parcelas só dão a data.
- **Relógio da página**: o "hoje" passa a ser o de São Paulo, no lugar do UTC.
- **Botão "Copiar cobrança"**: some no outro evento do grupo, na cortesia e no valor simbólico.
- **Cobranças da Home**: a lista cresce, de ~15 para ~40 linhas, porque as vendas com metade paga
  deixam de ficar escondidas. O total do topo cai, porque as linhas cinza deixam de contar.

## Contexto técnico

**Linguagem/Versão**: Python 3.11 (Flask + SQLAlchemy) no backend; TypeScript + React 18 (Vite)
no frontend

**Dependências principais**: Flask, SQLAlchemy, Alembic; React, TanStack Query, Tailwind CSS,
shadcn/ui (`@manto/ui`), Framer Motion, `@manto/api-client`, `@manto/money`. Nenhuma dependência
nova.

**Armazenamento**: PostgreSQL — produção no Render (`manto-postgres`); verificação contra
`manto_local`. **Sem migration**: as colunas de valor e de data da venda já aceitam nulo
(`models.py:261-264`), e `CommissionPayment.payable_from` já existe (`models.py:920`).

**Verificação**:
- `specs/299-sem-valor-cobrancas/verify_299.py` contra `manto_local`, com 17 cenários; o 16 deve
  falhar.
- Login só pela API e escrita conferida por conexão separada.
- Um falso do Google que **conta** as chamadas de `insert_event` e `update_event`, e um
  `load_credentials` que estoura se for chamado.
- `cd frontend && npm run typecheck` e a tela aberta no Browser pane.

**Plataforma-alvo**: web — Render (Flask API JSON + 3 SPAs servidas por `frontend/server.js`);
staff em desktop

**Tipo de projeto**: SPA desacoplada (API JSON + React)

**Metas de desempenho**:
- **Home**: o bloco comercial passa a ter consultas fixas, nenhuma por linha:
  - os principais desde o corte, com `selectinload` de satélites, clientes e parcelas (3 a 4 idas
    ao banco);
  - uma soma de comprovantes para todos os ids;
  - o corte, lido uma vez.

  Hoje são ~237 eventos desde 01/06.
- **Página do evento**: uma consulta a mais (os comprovantes do grupo).

**Restrições**:
- `start_at` é hora de parede de São Paulo, sem fuso.
- Dinheiro em `Decimal` com `ROUND_HALF_UP` até a serialização, e `float` só na borda.
- Evento sem tipo não é ensaio: nada de `event_type != 'ENSAIO'` em SQL, por causa do `NULL`.
- O marcador 🟧/🟠 é conferido com `lstrip()`.
- Campos novos do payload são opcionais no TS.
- Nenhuma rota pública nova, então `frontend/server.js` não muda.
- `useReducedMotion` nas listas e na marca.

**Escala/escopo**:
- **Banco**: nenhuma tabela nem coluna nova.
- **Endpoints**: nenhum novo. Mudam `GET /api/dashboard`, `GET /api/events/<id>` (e as escritas que
  devolvem o detalhe), `POST /api/events`, `PATCH /api/events/<id>` e
  `PATCH /api/events/<id>/orcamento` (regra do valor simbólico).
- **Regra de comissão**: `_sync_commission_payment` (`payable_from`).
- **Telas**:
  - Home: dois painéis e o total do topo;
  - cadastro e edição completa;
  - aba Comercial, Resumo e cabeçalho do evento.

## Constitution Check

*GATE: aprovado antes da Phase 0; reavaliado após a Phase 1.*

| Princípio / seção | Como o plano cumpre (ou por que não se aplica) |
|---|---|
| I. Reutilizar antes de criar | Reusa:<br>• `contratante_name`, `is_loja_virtual` e `NON_SALE_EVENT_TYPE` (`vendas_ops.py:41, 81-93, 197-205`) e `_is_permuta` (`financeiro/routes.py:125-126`);<br>• `group_ops.group_events` (`:64-75`), na página;<br>• `corte_dia_sp` (`formularios_ops.py:86-91`), `now_sp` (`constants.py:290-301`) e `FORM_COR_*` (`constants.py:404-405`);<br>• o ponteiro do principal que já sai em `event.group` (`agenda_read.py:562-602`);<br>• `payable_from` (feature 109);<br>• `SectorPanel`, `HomeOverview`, `MetricBadge` e `formatBRL`;<br>• o esqueleto do `verify_298.py`.<br><br>O `GrupoFormularios` e o "Mostrar todas", hoje duplicado (`DashboardPage.tsx:236-242, 681-689`), são **extraídos**, não copiados. O novo é só `cobranca_ops`, que junta as duas cópias da regra de cobrança numa fonte. As somas por evento que ficam (`received_map`, "a receber", Jinja) estão fora de escopo pela spec e vão para o `docs/05`. |
| II. Padrões de código | Type hints e docstrings Google; funções de até ~30 linhas; constantes novas em `app/constants.py` (`VALOR_MINIMO_DE_VENDA`, `FOLGA_COBRANCA`, `SALDO_VENCE_DIAS_ANTES`, `MARCADORES_COMPROMISSO_INTERNO`, `COBRANCA_COR_*`, textos de selo); `except` sempre com log. TS estrito, sem `any`. Sai o `style` inline da `PendingPaymentRow` (`DashboardPage.tsx:356`). `ruff check` nos tocados e `ruff format` só em `cobranca_ops.py`. |
| III. Camadas / API First | O núcleo fica em `app/financeiro/cobranca_ops.py`, puro, com "hoje" e corte por argumento. A dependência vai de financeiro para calendar, a direção permitida (`group_ops.py:29-31`). `dashboard_service` e `agenda_read` só serializam. A regra do `enabled` sai de `agenda_read` para o núcleo (`pode_copiar_cobranca`). A regra do satélite na edição completa fica em `update_event_core`, não no endpoint. Nenhum módulo novo em `app/api/`. |
| IV. Não quebrar o que funciona | Tudo aditivo:<br>• `pending_payments` continua lista e mantém as chaves antigas, com `severity` na união antiga;<br>• as chaves antigas de `cobranca` mantêm nome e tipo;<br>• campos TS opcionais, lidos com fallback.<br><br>Consumidores conferidos: bundle antigo da Home (`DashboardPage.tsx:333-377, 908-919, 1256-1276`), `ResumoSection`, `EventHeader`, `eventDetail.ts`, `EventEditPage`, `verify_174`, `verify_273` e `verify_298`. A extração da 298 é mecânica, e o painel de Formulários é reconferido. |
| V. UI/UX com feedback | A marca "Valor a definir" no padrão da cortesia e o aviso no lugar ao apagar um valor. O foco real chega ao campo de valor (`Controller` passando `id` e `ref`), no envio e no 400 do servidor. Estados vazios nos dois painéis. Sublista ausente esconde o painel, em vez de mostrar "✓". Botões com o carregamento de hoje. |
| VI. Esteira (Nível 1) | Dois domínios (comercial/financeiro e agenda) e três telas: esteira completa, com os artefatos em `specs/299-sem-valor-cobrancas/`. |
| VII. Living Spec | A spec recebeu 7 respostas no specify e no clarify e 4 no plan (14/09). Qualquer desvio no implement volta primeiro para a `spec.md`. |
| VIII. Verify antes do núcleo | O `verify_299.py` fica na Foundational do `tasks.md`, depois de os contratos serem congelados, e falha primeiro pelos motivos certos: bloco `sem_valor` ausente e soma por evento. São 17 cenários, e o 16 deve falhar: CASTING sem bloco comercial, e FINANCEIRO criando evento com 403 exato. |
| IX. Dinheiro BRL | Conta em `Decimal` com `quantize(0.01, ROUND_HALF_UP)` no núcleo e `float` só na serialização. `total_em_aberto` é somado no servidor. Nenhum texto de dinheiro é montado no servidor. A tela usa `formatBRL` e `MoneyInput`. |
| X. Mobile-first público | Não é superfície pública; mesmo assim a Home é conferida a 375 px (FR-030), com os textos de dinheiro fora de `MetricBadge`, que não quebra linha. |
| XI. Framer Motion | `GrupoDeLinhas` com `AnimatePresence` e `useReducedMotion` (a saída da linha resolvida, FR-010). A marca "Valor a definir" usa o mesmo `AnimatePresence` da cortesia (`ValoresBlock.tsx:48-86`). |
| XII. Combobox / Maps | Nenhuma lista nova com mais de 10 itens; nenhum endereço. |
| XIII. RBAC declarado | Nenhum endpoint novo. Os gates continuam os mesmos:<br>• `/api/dashboard`: `show_comercial`;<br>• POST e PATCH de evento: `_can_create_event` (`agenda_write.py:84-88`);<br>• `/orcamento`: `_can_manage_sale`;<br>• detalhe: `show_comercial`.<br><br>`pode_editar_venda` sai pelo mesmo cálculo do `pode_criar_evento` da 298. O `docs/01` §4.3 ganha a linha de `/api/dashboard`, que não existe hoje. Tabela em [contracts/api-eventos-valor.md](./contracts/api-eventos-valor.md). |
| XIV. Config / efeito externo | Nenhuma env nova. Nenhuma escrita externa nova: o POST continua escrevendo no Google como hoje, e o verify troca o Google por falsos. |
| Stack | Sem migration. Sem Jinja novo; a cópia Jinja da regra de cobrança (`calendar/routes.py:1833-1850`) não é tocada, porque a remoção está pausada e a rota não passa pelo `server.js`. |
| Operação e Deploy | Não toca `startCommand`. Nenhum comando pós-deploy. Avisar a equipe no dia: as cobranças crescem e o total do topo cai. |

**Resultado do gate**: aprovado, sem violação a justificar. Reavaliado após a Phase 1, com os
contratos, o modelo de dados e o quickstart escritos: continua aprovado.

## Estrutura do projeto

### Documentação (esta feature)

```text
specs/299-sem-valor-cobrancas/
├── spec.md              # /speckit-specify + clarify + respostas do plan (14/09)
├── plan.md              # este arquivo
├── research.md          # Phase 0 — R1..R29
├── data-model.md        # Phase 1 — VendaResumo, estados, linhas, comissão
├── quickstart.md        # Phase 1 — verify, telas, conferência em produção
├── contracts/
│   ├── dashboard-comercial.md   # bloco comercial do /api/dashboard (+ formularios.para_agir)
│   ├── evento-cobranca.md       # cobranca/venda/pagamentos do detalhe do evento; orçamento
│   └── api-eventos-valor.md     # valor_a_definir no POST/PATCH, comissão, RBAC
├── checklists/requirements.md
├── tasks.md             # /speckit-tasks
└── verify_299.py        # Princípio VIII — escrito antes do núcleo
```

### Código (caminhos reais)

```text
app/constants.py                                   # VALOR_MINIMO_DE_VENDA, FOLGA_COBRANCA, SALDO_VENCE_DIAS_ANTES,
                                                   #   MARCADORES_COMPROMISSO_INTERNO, COBRANCA_COR_*, SELO_*
app/financeiro/cobranca_ops.py          (novo)     # VendaResumo, recebido_por_evento, principal_da_venda, data_do_grupo,
                                                   #   motivo_fora_da_venda, vencimento_do_saldo, cor_por_distancia, selo,
                                                   #   vendas_desde (lote da Home), resumo_da_venda_do_evento (página),
                                                   #   pode_copiar_cobranca, listar_cobrancas, listar_sem_valor
app/calendar/event_ops.py                          # sem_valor_de_venda, aplicar_valor_a_definir, resolver_data_da_venda(a_definir),
                                                   #   update_event_core: satélite não grava campos comerciais
app/calendar/routes.py                             # _validate_event_core: pula valor com a marca; valor e vendedor no satélite
app/calendar/orcamento_evento_ops.py               # :284 e :404 — valor simbólico conta como "sem venda"
app/financeiro/comissoes_ops.py                    # _sync_commission_payment: payable_from = hoje para comissão que nasce
                                                   #   depois do mês da data da venda; não volta a NULL
app/formularios/destino_ops.py                     # listar_sem_destino ganha para_agir (aditivo)
app/api/dashboard_service.py                       # _painel_comercial dentro de _bloco("comercial"); compute/serialize viram
                                                   #   adaptadores; pending_payments estendido; sem_valor; cobrancas_resumo
app/api/agenda_read.py                             # _compute_cobranca → adaptador do núcleo; venda.sem_valor/valor_simbolico;
                                                   #   pagamentos.outros_do_grupo
app/api/agenda_write.py                            # _build_create/_build_update repassam valor_a_definir
frontend/apps/internal/src/lib/types.ts            # PendingPayment (+opcionais), LinhaSemValor, SemValorSummary, ComercialSummary
frontend/apps/internal/src/lib/agenda.ts           # cobranca/venda/pagamentos (+opcionais)
frontend/apps/internal/src/lib/homeListas.ts  (novo)  # Severidade, tom e fundo, diaMes, distanciaDaData(vocabulário)
frontend/apps/internal/src/components/home/{GrupoDeLinhas,LinhaDaHome,PainelCobrancas,PainelSemValor}.tsx  (novos)
frontend/apps/internal/src/pages/DashboardPage.tsx # usa as peças extraídas; dois painéis; SectionStat.noTotal; sai PendingPaymentRow
frontend/apps/internal/src/lib/eventFormSchema.ts  # valor_a_definir; refines
frontend/apps/internal/src/components/EventFormBlocks/ValoresBlock.tsx  # marca; Controller com id/ref nos MoneyInput
frontend/apps/internal/src/pages/{EventCreatePage,EventEditPage}.tsx    # corpo com null + marca; hidratação; foco no 400
frontend/apps/internal/src/lib/{eventCreate,eventInline,eventAttachments,eventOps}.ts  # tipos; invalidar ['dashboard']
frontend/apps/internal/src/components/EventDetail/{FinanceiroSection,ComercialSection,ResumoSection,EventHeader}.tsx
specs/299-sem-valor-cobrancas/verify_299.py
```

**Decisão de estrutura**:
- **O núcleo mora em `app/financeiro/`**, porque é regra de venda e cobrança e precisa das peças de
  `vendas_ops`. Ele não vai para dentro de `vendas_ops.py`, que é o núcleo do funil `/vendas` (358
  linhas) e continua contando por evento, por decisão da spec.
- **O predicado `sem_valor_de_venda` mora em `event_ops`**, porque o orçamento (calendar) também o
  usa e calendar não importa de financeiro.
- **As peças de lista da Home ficam no app interno**, e não no `@manto/ui`, porque só a Home as usa.
- **Os painéis novos são arquivos próprios**, porque o `DashboardPage.tsx` já tem ~1.360 linhas.

## Sequência de implementação (blocos commitáveis)

1. **Foundational.**
   - Constantes.
   - Contratos congelados.
   - `verify_299.py` falhando pelos motivos certos.
2. **Núcleo.**
   - `cobranca_ops.py`, `sem_valor_de_venda` e o adaptador do dashboard.
   - O contrato novo de `comercial` e `formularios.para_agir`.
   - Cenários 1–4 e 7–14.
3. **Página do evento.**
   - `_compute_cobranca` pelo núcleo e `pode_copiar_cobranca`.
   - `venda.sem_valor` e `pagamentos.outros_do_grupo`.
   - O orçamento aceitando o valor simbólico.
   - Cenários 6b e 15.
4. **Valor a definir no servidor.**
   - Protocolo, validação e `resolver_data_da_venda`.
   - O satélite em `update_event_core`.
   - A comissão com `payable_from`.
   - Cenários 5 e 6a.
5. **Home (front).**
   - Extração das peças da 298.
   - Dois painéis e o total do topo.
   - Invalidação de `['dashboard']`.
6. **Evento (front).**
   - Cadastro e edição: marca, corpo, hidratação e foco.
   - Aba Comercial: "A definir", o valor simbólico e o grupo.
   - Resumo e cabeçalho.
7. **Portões.**
   - Typecheck e ruff.
   - `verify_299` 17/17, mais `verify_298`, `verify_273` e `verify_174` de novo.
   - Telas abertas: Home no computador e a 375 px, com a regressão de Formulários; cadastro;
     edição; principal e satélite.
8. **Antes do deploy** (decisão do dono, R41): levantar, só lendo a produção, o 344, os casos
   grandes de recebido acima do valor e as vendas com comprovante sem valor. O dono confere e corrige
   antes de publicar ([quickstart.md](./quickstart.md) §0).
9. **Docs.**
   - `docs/01`: §3.2, §4.3 e o contrato do detalhe.
   - `docs/02`: Home, cadastro e aba Comercial.
   - `docs/04`: invariantes da cobrança e duas definições de "sem valor".
   - `docs/05`:
     - remover `severity` e `pending_payments` antigos num deploy futuro;
     - a cópia Jinja;
     - o `list_closed_sales` com `NULL`;
     - as somas por evento que ficam;
     - a trava do sync.
   - `docs/03`: entrada no topo.
   - A spec 051 marcada como superada.

## Riscos e como cada um é contido

| Risco | Contenção |
|---|---|
| Bundle antigo (em cache) quebra a Home sem ErrorBoundary | `pending_payments` sempre lista; `severity` e as chaves antigas continuam; valores continuam `number` |
| Home e página voltam a divergir | Uma função (`resumo_da_venda_do_evento` / `vendas_desde`) sobre a mesma primitiva de recebido; o cenário 15 compara a página com a Home |
| N+1 na Home | Lote com `selectinload`; nada de `group_events` nem `is_group_leader` por linha; o verify roda com o volume real do espelho |
| Evento sem tipo (venda de R$ 35.000) sumindo | Nenhuma exclusão de ensaio em SQL; `motivo_fora_da_venda` trata `None` como "não é ensaio" |
| Comissão cair em mês já pago | `payable_from = hoje` quando a comissão nasce depois do mês da venda, sem voltar a `NULL` na sincronização seguinte (R22); cenário 5d |
| Satélite passando a salvar pela edição completa (a marca abre sozinha) | `update_event_core` ignora os campos comerciais do satélite; `_validate_event_core` pula valor e vendedor no satélite; marca travada na tela |
| Refatorar o painel da 298, em produção | Extração mecânica, sem mudar texto nem comportamento; tela de Formulários reconferida; `verify_298` de novo |
| Verify escrevendo no Google real pela edição completa | Falsos em `routes.insert_event`, `routes.update_event` e `service.update_event`, e `load_credentials` que estoura (R27) |
| Bundle novo com servidor antigo: 400 em campo escondido pela marca | Falha segura (valida antes do Google); publicar fora do horário |
| Linha resolvida continua na Home (staleTime de 30 s) | Invalidar `['dashboard']` nos hooks de venda, comprovante, orçamento, criar, editar e cancelar (R23) |
| Duas definições de "sem valor" (Financeiro com `<= 0`, Home com `< 1`) | Predicado com nome próprio; `docs/04` registra as duas para ninguém "unificar" de passagem |
| Comprovante sem valor e o 344 duplicado enganando Cobranças no dia | Conferência de dados antes do deploy, decidida pelo dono (R41) |
| Recusar valor abaixo de R$ 1,00 travando a edição de eventos antigos de R$ 0,01 | A edição que mantém o mesmo valor é aceita (R32); cenário 6 |

## Rastreamento de complexidade

Nenhuma violação do Constitution Check a justificar.
