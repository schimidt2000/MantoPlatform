<!-- ADAPTADO PARA A MANTO (2026-09-08) — reaplicar após qualquer atualização do Spec Kit; para este
     arquivo o hash em .specify/integrations/speckit.manifest.json deixa de conferir de propósito. -->
# Plano de implementação: Feature 315 — pedido de cancelamento pelo sistema

**Branch**: `315-pedido-de-cancelamento` | **Data**: 2026-10-22 | **Spec**: [spec.md](./spec.md)

**Input**: `/specs/315-pedido-de-cancelamento/spec.md` · reconferência `pesquisa/reconferencia-2026-10-22.md` ·
decisões técnicas `research.md` (R1–R12)

## Resumo

O Comercial pede o cancelamento pelo sistema, com o motivo, o alcance (numa venda de vários dias) e a devolução
combinada completa; o pedido grava cinco colunas do evento (as três da 224 e duas novas) por um `UPDATE` condicional e,
na mesma transação, avisa cada Superadmin no sino. Enquanto espera: quadro na tela do evento (motivo e autor cortados
no servidor pela Q6), frase na faixa vermelha (Comercial e Superadmin), selo na agenda e "Evento em confirmação" no
portal — o satélite herda o pedido de "todos os dias" do principal por um lote, sem N+1. O Superadmin decide: recusa
(claim; resposta ao autor), cancela pelo diálogo da 306 (que abre vazio com o pedido acima, só leitura — o fecho do
pedido mora em `ao_cancelar`, lendo o pedido antes de zerar) ou exclui (resposta "excluído" sem link). O código do
pedido mora num módulo novo, `app/calendar/solicitacao_ops.py`, para não colidir com o `PedidoDeCancelamento` da 306.

## Contexto técnico

**Linguagem/Versão**: Python 3.11 (Flask + SQLAlchemy) no backend; TypeScript + React 18 (Vite) no frontend

**Dependências principais**: Flask, SQLAlchemy, Alembic (migration à mão); React, TanStack Query, Tailwind,
`@manto/ui` (`ConfirmDialog`, `Badge`), `@manto/money` (`MoneyInput`, `formatBRL`), `@manto/api-client`

**Armazenamento**: PostgreSQL — duas colunas nulas em `calendar_events`; nenhuma tabela nova

**Verificação**: `specs/315-pedido-de-cancelamento/verify_315.py` contra `manto_local`, com o harness da 306 (Google e
e-mail falsos que falham fechado); `npm run typecheck`; tela aberta (interno e portal em 375 px)

**Plataforma-alvo**: web — Render; staff em desktop (e Comercial no celular), portal em smartphone

**Tipo de projeto**: SPA desacoplada (API JSON + React)

**Metas de desempenho**: nenhuma consulta por linha a mais no mês, no dia, na busca e no portal (o lote do satélite é
uma consulta por resposta); a faixa continua um GET de 60 s

**Restrições**: o pedido não escreve no Google nem manda e-mail; o bundle velho continua pedindo e recusando pelo
caminho `/solicitar-exclusao` por um deploy; `total` da faixa continua só do sumiço; a altura da faixa não muda

**Escala/escopo**: 2 colunas; 2 kinds no sino; 2 rotas novas (como regras a mais nas views de hoje) + 4 respostas
alteradas (detalhe, fila, faixa, resumo) + portal; ~10 arquivos de backend, ~12 do interno, 0 do portal (campo já
existe); 88 eventos futuros vivos, 1 pedido pendente real

## Constitution Check

*GATE: aprovado antes da Phase 0; reavaliado após a Phase 1.*

| Princípio / seção | Como o plano cumpre (ou por que não se aplica) |
|---|---|
| I. Reutilizar antes de criar | as colunas, rotas e fila da 224; o gancho `ao_cancelar` da 306; `trava_do_cancelado`; `travar_grupo`; a régua `_papeis_com_cache_pago`/`FRASE_CACHE_PAGO`; `emitir`/`marcar_lidas_por_entidade`; o molde de claim de `sumico_ops.marcar`; o corte `show_comercial` da 312; o diálogo de cancelar da 306; `AvisoEmConfirmacao` do portal; `SeloSituacao`; `ConfirmDialog` |
| II. Padrões de código | type hints e docstrings no módulo novo; constantes em `app/constants.py`; TS estrito com chaves novas opcionais; `ruff check` nos tocados |
| III. Camadas / API First | núcleo em `solicitacao_ops.py` (puro, sem `request`); `agenda_write`/`agenda_read`/`agenda.py` só RBAC + serialização; nenhum módulo novo em `app/api/` |
| IV. Não quebrar o que funciona | migration aditiva; alias do caminho velho; `situacao` e os códigos de hoje intactos; `total` da faixa intacto; endpoint names intactos (9b do `verify_312`); regressão 306/312/303/311/302 |
| V. UI/UX com feedback | botões com loading; erro no campo; 409 recarrega e anuncia (nunca texto vermelho num diálogo que perdeu o sentido); recusa com confirmação |
| VI. Esteira (Nível 1) | esteira completa em `specs/315-pedido-de-cancelamento/` |
| VII. Living Spec | spec, research e contrato antes do código |
| VIII. Verify antes do núcleo | `verify_315.py` inteiro na Foundational, vermelho contra a `main` (primeira saída guardada); cenários "deve falhar" de autorização, leitura (com mutação), concorrência e Q5 = D |
| IX. Dinheiro BRL | valores da devolução em texto decimal (`Decimal` no núcleo, `MoneyInput` na tela, `formatBRL` ao mostrar) |
| X. Mobile-first público | o portal só ganha a condição de um aviso que já existe; conferido em 375×812 nas três telas |
| XI. Framer Motion | o diálogo de pedir e o quadro reusam os componentes animados de hoje; nada de animação nova |
| XII. Combobox / Maps | não se aplica (nenhuma lista longa nem endereço) |
| XIII. RBAC declarado | pedir: Comercial/Superadmin (papel real); recusar: Superadmin (papel real); leituras pelos gates de hoje; linhas em `docs/01` §4.3 |
| XIV. Config / efeito externo | nenhuma env; o pedido não escreve fora (nem Google, nem e-mail); o verify só exercita cancelar/excluir com o Google falso |
| Stack | migration à mão, `down_revision = c5d2f7a9e306`; sem Jinja novo; sem segredo |
| Operação e Deploy | sem `startCommand`; migration aditiva (sem ensaio destrutivo, mas `flask db upgrade` conferido no `manto_local`); deploy à noite |

Sem violação a justificar.

## Estrutura do projeto

### Documentação (esta feature)

```text
specs/315-pedido-de-cancelamento/
├── spec.md · plan.md · research.md · data-model.md · quickstart.md
├── contracts/api.md
├── pesquisa/reconferencia-2026-10-22.md
├── checklists/
├── tasks.md
├── verify_315.py
└── verify_315_primeira_falha.txt
```

### Código (caminhos reais)

```text
migrations/versions/<rev>_solicitacao_de_cancelamento.py   # nova; down_revision c5d2f7a9e306
app/models.py                                              # duas colunas (ao lado de :304-306)
app/constants.py                                           # CODIGO_PEDIDO_PENDENTE, CODIGO_SEM_PEDIDO, a união; kinds
app/calendar/solicitacao_ops.py                            # NOVO: solicitar, recusar, fechar_no_cancelamento,
                                                           #   responder_na_exclusao, faixa, lote do satélite, bloqueio,
                                                           #   serializar (o corte por papel)
app/calendar/cancel_ops.py                                 # ao_cancelar chama o fecho; sai a limpeza de :2059-2061;
                                                           #   saem solicitar_exclusao/recusar_solicitacao (:3502-3541);
                                                           #   pendentes da fila pelo serializador do módulo novo
app/notificacoes/notificacoes_ops.py                       # 2 kinds + 2 produtores
app/api/agenda_write.py                                    # rotas novas nas views de hoje (:908-948); resposta na exclusão
app/api/agenda_read.py                                     # bloco do pedido com corte; pedido_bloqueado; pedido_da_venda;
                                                           #   resumo com o lote; busca
app/api/agenda.py                                          # mês e dia com o lote; faixa com `pedidos`
app/talent_portal/portal_ops.py                            # em_confirmacao com o pedido e o lote
frontend/apps/internal/src/lib/{agenda,eventOps,sumidosGoogle,navigation}.ts(x)
frontend/apps/internal/src/components/{FaixaSumidosGoogle,SeloSituacao}.tsx
frontend/apps/internal/src/components/EventDetail/{EventHeader,PedirCancelamentoDialog,ExcluirEventoDialog}.tsx
frontend/apps/internal/src/components/notificacoes/NotificacaoItem.tsx
frontend/apps/internal/src/pages/EventosCancelamentosPage.tsx
frontend/apps/internal/src/components/{CalendarGrid,DayTimelineView}.tsx   # tooltip do chip
```

**Decisão de estrutura**: o pedido é um fluxo à parte com um ponto de contato no cancelamento — módulo próprio
(research R1). O `SolicitarExclusaoDialog.tsx` é renomeado por `git mv` para `PedirCancelamentoDialog.tsx`.

## Fases de construção

1. **Setup** — ponteiro, `env315.ps1`, migration + colunas + constantes (o verify precisa das colunas para semear);
   `flask db upgrade` no `manto_local`.
2. **Foundational** — `verify_315.py` inteiro (cenários 1–28), rodado **vermelho** contra o código de hoje (só a
   migration aplicada), primeira saída em `verify_315_primeira_falha.txt`. Verdes esperados: só 27 (regressão) e 28
   (limpeza) — os cenários usam a rota nova, que ainda não existe.
3. **H1 — pedir** — `solicitacao_ops.solicitar` (forma, recusas, claim, histórico, auditoria), o produtor
   `evento.pedido_cancelamento`, as rotas (nova + alias), a resposta com o detalhe. Verdes: + 1–5, 7–9, 16, 17, 26.
4. **H2 — ver enquanto espera** — o corte no detalhe e na fila, `pedido_bloqueado`, a faixa com `pedidos`, o lote do
   satélite no resumo/detalhe/portal, o portal. Verdes: + 6, 10–12, 14, 15.
5. **H3 — decidir** — `recusar` (claim, resposta), o fecho em `ao_cancelar` (cinco colunas, avisos lidos, resposta
   por pedido e por dia), a resposta na exclusão, concorrência, autor sem acesso. Verdes: + 13, 18–25.
6. **Telas** — tipos, hooks, `PedirCancelamentoDialog`, menu e quadro do `EventHeader`, recusa com confirmação, o
   diálogo de cancelar com o pedido acima (e o texto da Q9), a faixa, o selo e os tooltips, a fila "Cancelamentos" e
   os menus, os ícones do sino. Typecheck.
7. **Polimento** — rodada inteira duas vezes, regressão, tela aberta (interno e portal), docs 01–05, converge.

## Deploy e rollback

Um push só, à noite, com uma migration **aditiva** (duas colunas nulas): o `startCommand` (`flask db upgrade && python
seed.py && gunicorn`) a aplica sozinho. Sonda: um endpoint `/api/` com JSON e o `GET /api/events/sumidos-google`
devolvendo a chave `pedidos` (o 1350 deve aparecer). **Rollback** = `git revert` do merge + push: o código antigo
ignora as duas colunas (a migration fica; o `downgrade` só se for preciso, e perde alcance e devolução de pedidos
pendentes, nunca dinheiro); os pedidos feitos no meio-tempo continuam pendentes pelas três colunas da 224, visíveis no
"Solicitar exclusão" de antes.

## Rastreamento de complexidade

Nenhuma violação do Constitution Check a justificar.
