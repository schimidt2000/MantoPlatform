<!-- ADAPTADO PARA A MANTO (2026-09-08) — reaplicar após qualquer atualização do Spec Kit; para este
     arquivo o hash em .specify/integrations/speckit.manifest.json deixa de conferir de propósito. -->
# Plano de implementação: O cancelado sai de toda lista e só se vê onde se trata do cancelamento

**Branch**: `312-cancelado-fora-das-listas` | **Data**: 2026-10-20 | **Spec**: [spec.md](./spec.md)

**Input**: `/specs/312-cancelado-fora-das-listas/spec.md`

**Nota**: preenchido pelo `/speckit-plan`. A constituição (`.specify/memory/constitution.md`,
v3+) é lida em tempo de execução — o Constitution Check abaixo é o que ela cobra.

## Resumo

O evento cancelado deixa de ser item de qualquer lista do sistema (Dia, busca, fichas, seletores, filas, painel do
grupo, conflito de agenda) e passa a ser visto só na página de Cancelamentos (agora também do Financeiro, com
filtros), no card "Cancelamentos do período" (Dashboard Comercial e DRE) e na tela dele, que fica só para
consulta — menos os dados de venda (Superadmin, regra da 306), o motivo (Superadmin e Comercial, 306b) e os
desfazer. O motivo e o autor do cancelamento saem só para Comercial, Financeiro e Superadmin. O Casting ganha na
Home a pendência "excluir e avisar", e no cancelado só ele (e o Superadmin) tira artista da escala.

Abordagem: filtros `cancelled_at IS NULL` de uma linha onde falta; duas funções novas no núcleo do cancelado
(`exigir_evento_vivo` para a trava, `recusar_se_cancelado_para_ligar` para os vínculos) chamadas pelas rotas e
núcleos de cada domínio; uma função de painel (`painel_de_cancelamentos`) para o card das duas telas; nada de
tabela, coluna, migration, env ou escrita externa nova. Mapa do código em `pesquisa/reconferencia-2026-10-20.md`;
decisões em `research.md`.

## Contexto técnico

**Linguagem/Versão**: Python 3.11 (Flask + SQLAlchemy) no backend; TypeScript + React 18 (Vite)
no frontend

**Dependências principais**: Flask, SQLAlchemy; React, TanStack Query, Tailwind CSS, shadcn/ui (`@manto/ui`),
`@manto/api-client`, `@manto/money`

**Armazenamento**: PostgreSQL — produção no Render; verificação contra `manto_local`. Sem migration.

**Verificação**: `specs/312-cancelado-fora-das-listas/verify_312.py` contra `manto_local` (molde e semente do
`verify_306.py`); `cd frontend && npm run typecheck` (as três SPAs mudam: interno, portal pela ficha de figurino,
público pela avaliação); `ruff check` nos tocados; tela aberta; portal e avaliação em 375×812 e 320–430 px

**Plataforma-alvo**: web — Render (Flask API JSON + 3 SPAs servidas por `frontend/server.js`)

**Tipo de projeto**: SPA desacoplada (API JSON + React)

**Metas de desempenho**: nenhuma consulta por linha — a página de Cancelamentos, o card, a ficha da cliente e a
pendência do Casting leem em lote (`resumos_cancelados`, uma consulta para a escala). O Dia e a busca ganham uma
condição a mais, sem custo mensurável (84 eventos em out/26).

**Restrições**: sem migration; sem rota pública nova (a avaliação já é `/api/avaliar`); campo novo sempre
opcional no TypeScript (bundle e backend em versões diferentes na janela do deploy); deploy num push só; Jinja só
ganha a linha da trava e os filtros de uma linha (remoção pausada).

**Escala/escopo**: 0 tabelas, 0 colunas; ~25 endpoints com recusa ou filtro novo, 3 com campo novo
(`/events/cancelamentos`, `/vendas/pipeline`, `/clientes/<id>`) e 2 com flag/campo (`/events/<id>`,
`/dashboard`); ~20 componentes de tela tocados; 2 telas fora do interno (portal e avaliação).

## Constitution Check

*GATE: aprovado antes da Phase 0; reavaliado após a Phase 1.*

| Princípio / seção | Como o plano cumpre (ou por que não se aplica) |
|---|---|
| I. Reutilizar antes de criar | reusa o resumo em lote da 306 (`resumos_cancelados`, `cancelados_do_periodo`, `totais_cancelamentos`, `filtro_devolucao`), `CODIGO_EVENTO_CANCELADO`, `CancelValidationError` e `_recusa_do_cancelado`, `group_ops.dias_vivos`, `elenco_do_ato`, `marcar_lidas_por_entidade`, `serialize_unconfirmed_ref`/`UnconfirmedRow`, `SeloSituacao`, `CalendarEvent.situacao`. Novo só o que não existe: a trava, a recusa de vínculo, o painel do card |
| II. Padrões de código | type hints e docstrings pt-BR no novo; mensagens em constantes da classe de erro; TS estrito com campos opcionais; `ruff check` nos tocados (comparar com a `main` antes) |
| III. Camadas / API First | regras no núcleo (`cancel_ops`, `casting_ops`, `event_ops`, `nfc_ops`, `impressoes3d_ops`, `formularios_ops`, `producao_ops`, `dashboard_service`); endpoints só traduzem; nenhum módulo novo em `app/api/` |
| IV. Não quebrar o que funciona | filtros só olham `cancelled_at`; mês sem cancelado = payload igual à `main` (cenário 22); portas de venda da 306 e o motivo da 306b intocados (cenário 10); verifies 306, 306b, 303 e os de `scripts/db/` rodados de novo |
| V. UI/UX com feedback | a recusa do servidor aparece onde a ação foi pedida; a tela recarrega ao receber `cancelado`; estados vazio e erro da página; frase "só o Superadmin altera" no lugar dos botões |
| VI. Esteira (Nível 1) | esteira completa; artefatos em `specs/312-…/` |
| VII. Living Spec | spec com Session 2026-10-20; decisões novas do implement voltam para a spec |
| VIII. Verify antes do núcleo | `verify_312.py` na Foundational, rodado vermelho contra a `main` (23 cenários; os "deve falhar" de visibilidade e de escrita ficam vermelhos pelo motivo certo) |
| IX. Dinheiro BRL | só leitura de números da 306 (`Decimal`); a tela formata por `@manto/money` |
| X. Mobile-first público | página de avaliação (410) e ficha de figurino do portal conferidas de 320 a 430 px |
| XI. Framer Motion | nenhum componente animado novo; o card reusa o molde estático do card da loja |
| XII. Combobox / Maps | nenhuma lista nova de escolha; os seletores existentes só perdem o cancelado; o select de Gastos mostra o vínculo atual |
| XIII. RBAC declarado | `GET /events/cancelamentos` = SUPERADMIN ou FINANCEIRO (papel real); `assign` no cancelado = CASTING ou SUPERADMIN; motivo por `show_comercial`; card com imposto só SA/FIN; linhas em `docs/01` §4.3 e `docs/00` §4 |
| XIV. Config / efeito externo | nenhuma env; nenhuma escrita externa nova — as recusas vêm **antes** do Google (`create_ensaio`) e do e-mail (`send_invite`, `assign_role`) |
| Stack | sem migration; sem Jinja novo (só a checagem de uma linha nas views existentes); sem segredo |
| Operação e Deploy | não toca `startCommand`; deploy num push só, fora do horário, quando o dono pedir |

Sem violação: a seção "Rastreamento de complexidade" fica vazia.

## Estrutura do projeto

### Documentação (esta feature)

```text
specs/312-cancelado-fora-das-listas/
├── spec.md
├── plan.md
├── research.md
├── data-model.md        # formas dos payloads (sem entidade nova)
├── quickstart.md
├── contracts/api.md     # os contratos alterados, com RBAC
├── pesquisa/reconferencia-2026-10-20.md
├── checklists/
├── tasks.md             # /speckit-tasks
└── verify_312.py        # escrito antes do núcleo
```

### Código

```text
app/calendar/cancel_ops.py           # exigir_evento_vivo, EventoSomenteConsultaError, recusar_se_cancelado_para_ligar,
                                     # painel_de_cancelamentos, listar_cancelamentos(mes, devolucao), a_avisar_do_casting
app/calendar/casting_ops.py          # assign_role/add_role/send_invite/convidar_recem_escalados recusam o cancelado
app/calendar/event_ops.py            # search_events (filtro), create_ensaio, link_ensaio_to_show, ensure_feedback_token
app/calendar/group_ops.py            # renomear_grupo cai na trava (via rota)
app/calendar/routes.py               # Jinja: agenda_day, _talent_time_conflict, disponibilidade, despachante, rotas fora dele
app/calendar/dashboard_service.py    # cancelados_a_avisar; ensaio legado fora de agendado
app/api_utils.py                     # json_recusa_do_cancelado (tradução única)
app/api/agenda.py                    # Dia sem cancelado
app/api/agenda_read.py               # flags somente_consulta; Q9; _group_block só vivos; ensaios[] sem cancelado
app/api/agenda_write.py              # _trava_do_cancelado em toda escrita da tabela "Trava"; assign no cancelado; cancelamentos(mes, devolucao, gate)
app/api/clientes_read.py             # lista sem cancelado; cancelamentos{quantidade,retido}; form_history.event_situacao
app/api/financeiro_read.py           # pipeline.cancelamentos; paineis.cancelamentos pela função única; group_label só vivos
app/api/feedback_write.py            # 410 no cancelado
app/api/portal_figurino.py           # 400 no cancelado depois do não escalado
app/api/{nfc_write,impressoes3d_write,figurino_producao_write,formularios_admin_write,formularios_admin_read}.py
app/financeiro/vendas_ops.py         # group_label só vivos
app/gastos/gastos_ops.py             # search_events_by_date sem cancelado
app/talents/talent_ops.py            # histórico e números sem cancelado
app/impressoes3d/{impressoes3d_ops,nfc_ops}.py  # filas sem cancelado; recusas; serialize_tag.event_situacao
app/formularios/formularios_ops.py   # _real_event_candidates sem cancelado; apply_event_link recusa
app/figurino/producao_ops.py         # _resolver_evento recusa vínculo novo; event_situacao
app/figurino/routes.py               # "Imprimir fichas" recusa
app/talent_portal/portal_ops.py      # (só se a recusa do figurino morar no núcleo)
frontend/apps/internal/src/components/EventDetail/*   # somente_consulta, frases, recarregar no "cancelado"
frontend/apps/internal/src/components/SeloSituacao.tsx  # ramo cancelado
frontend/apps/internal/src/pages/{EventosCancelamentosPage,VendasPipelinePage,FinanceiroDashboardPage,
  ClientDetailPage,GastosExtrasPage,DashboardPage,FormulariosAdminPage,FigurinoProducao*Page,…}.tsx
frontend/apps/internal/src/lib/{eventOps,financeiro,clientes,types,navigation,nfc,agenda}.ts(x)
frontend/apps/portal/src/pages/PortalFigurinoPage.tsx
frontend/apps/public/src/pages/AvaliarPage.tsx
```

**Decisão de estrutura**: as regras novas do cancelado moram em `cancel_ops` (casa das regras do cancelado; evita
o ciclo `event_ops` ↔ `cancel_ops`); cada domínio chama a regra do seu núcleo, antes de escrever; a tradução para
JSON é uma só, em `app/api_utils.py`.

## Fases de construção

Cada fase fecha com a rodada inteira do verify e o `typecheck`; a ordem segue a dependência.

1. **Setup** — ponteiro, conferência do ambiente (`.local-db-url`, venv), leitura de `armadilhas` da 306.
2. **Foundational** — `verify_312.py` inteiro (23 cenários) rodado vermelho contra a `main` (guardar a 1ª saída
   em `verify_312_primeira_falha.txt`); as funções novas de `cancel_ops` (trava, recusa de vínculo) e a tradução
   única em `api_utils`, sem chamadores ainda.
3. **História 1 (P1)** — filtros de leitura: Dia API e Jinja, busca, seletor por data, candidatos do formulário,
   ficha do talento, ficha da cliente (+`cancelamentos`), Fila 3D e pendências, conflito (3 cópias), `_group_block`
   e `group_label`, ensaio legado (detalhe e Home). Cenários 1–7 e 22 verdes.
4. **História 2 (P1)** — recusas de vínculo (Q2, Q5) nos núcleos; a trava em cada escrita da tabela "Trava" (API e
   Jinja, "Imprimir fichas"); flags `somente_consulta` e Q9 no detalhe; tela do evento (esconder o que grava,
   frase dos painéis de venda, caixa reescrita, recarregar no "cancelado"); avaliação pública 410. Cenários 8–14.
5. **História 3 (P2)** — `cancelados_a_avisar`; `assign` no cancelado (gate, só remoção, sino lido); bloco na Home e
   a escala na tela. Cenário 15.
6. **História 4 (P2)** — página: gate FINANCEIRO, `mes`/`devolucao`/400, totais, sai o `devolucao` legado; tela com
   filtros, busca, colunas, vazio, erro, dia cortado; menu. Cenários 16–17.
7. **História 5 (P2)** — `painel_de_cancelamentos` usado pela DRE e pelo pipeline; card nas duas telas. Cenários
   18–19.
8. **História 6 (P3)** — `event_situacao` nas listas ligadas; ramo `cancelado` do `SeloSituacao`; select de Gastos
   com o vínculo atual; portal (ficha de figurino). Cenários 20–21.
9. **Polimento** — limpeza (cenário 23), regressão dos verifies vizinhos, tela aberta, docs 00/01/02/03/04/05,
   textos que mentem (docstring de `is_cancelled`, comentário "única porta").

## Rastreamento de complexidade

Sem violação.
