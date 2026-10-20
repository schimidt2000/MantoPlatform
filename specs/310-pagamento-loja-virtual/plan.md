<!-- ADAPTADO PARA A MANTO (2026-09-08) — reaplicar após qualquer atualização do Spec Kit; para este
     arquivo o hash em .specify/integrations/speckit.manifest.json deixa de conferir de propósito. -->
# Plano de implementação: 310 — Pagamento da loja de conversas ligado com segurança

**Branch**: `310-pagamento-loja-virtual` | **Data**: 2026-10-20 | **Spec**: [spec.md](./spec.md)

**Input**: `/specs/310-pagamento-loja-virtual/spec.md` (decisões do dono de 19/10; teste 0 e teste A
em produção de 20/10)

## Resumo

A InfinitePay já está ligada em produção (`prime-dreams`) e o caminho feliz foi provado com um Pix
real. O que falta é a camada genérica não perder dinheiro nem vender o mesmo horário duas vezes. O
plano concentra **toda** decisão de "pagamento vira venda?" numa função com trava do pedido
(`decidir_pagamento`, research R1), dá ao sistema uma segunda prova de pagamento além do aviso (o
retorno do checkout, R3 — o teste 0 mostrou que a reconsulta sem identificadores responde
`success:false`), tira o processamento pesado de dentro do aviso (R2), trava a operadora fora da
produção (R5), e põe interruptor, visibilidade e as correções de tela que tornam ligar e operar
seguros (R6–R16).

## Contexto técnico

**Linguagem/Versão**: Python 3.11 (Flask + SQLAlchemy) no backend; TypeScript + React 18 (Vite)
no frontend

**Dependências principais**: Flask, SQLAlchemy, Alembic (migration à mão), flask-limiter; React,
TanStack Query, Tailwind, `@manto/ui`, `@manto/api-client`, `@manto/money`; `requests` (cliente da
InfinitePay); Google Calendar API (já existente)

**Armazenamento**: PostgreSQL (`manto-postgres`; verificação no `manto_local`)

**Verificação**: `specs/310-pagamento-loja-virtual/verify_310.py` (44 cenários; InfinitePay e Google
como dublês que falham fechado; concorrência real com duas conexões e `threading.Barrier`; prova por
mutação com sonda limpa antes da mutada); regressão `verify_205.py`/`verify_304.py`; typecheck; tela
aberta em 375×812; testes A e C com a operadora real (quickstart §2)

**Plataforma-alvo**: Render (manto-backend gunicorn 3 workers gthread; manto-frontend Node)

**Metas de desempenho**: resposta ao aviso < 100 ms (a InfinitePay pede < 1 s); família vê "pago"
em ≤ 1 min depois de voltar do checkout sem aviso

**Restrições**: nenhuma chamada externa dentro de trava de linha; ordem de travas pedido → horário →
campanha; `X-Manto-Client-Ip` só vale porque o Node é o único caminho público de `/api`;
nada de deploy no pico da campanha

**Escala/escopo**: 1 migration aditiva (4 tabelas, 13 colunas, 1 backfill); 4 endpoints novos, 7
alterados; 3 telas públicas + Configurações + Devoluções/Pagamentos a conferir + detalhe do pedido na
gestão; `server.js`; `infinitepay_client.py`; `calendar` (marca na criação + pular na sincronização)

## Constitution Check

| Princípio / seção | Como o plano cumpre |
|---|---|
| I. Reutilizar antes de criar | `_abrir_devolucao`, `_enviar_aviso` (UNIQUE por tipo), `regerar_sala` (caminho do id local), `claim_sweep`, política de retry, `notificacoes_ops`, `VirtuaisDevolucoesPage`, `_suppress_*` como molde, `delete_event_gift` |
| II. Padrões de código | type hints/docstrings pt-BR; constantes novas em `constants.py`; `ruff check` |
| III. Camadas / API First | regra em `virtuais_ops.py`; rotas novas em `virtuais_public.py`/`virtuais_read.py`/`virtuais_write.py` só RBAC+serialização; cliente da operadora sem Flask (config injetada) |
| IV. Não quebrar o que funciona | migration aditiva; contrato da operadora provado em produção mantido (telefone só dígitos); `locked_until` segue no payload; regressão 205/304 |
| V. UI/UX com feedback | estados de espera distintos; confirmação com contagem antes de trocar o segredo; erros no campo |
| VI. Esteira Nível 1 | specify → (clarify feito no specify com o dono) → plan → checklist → tasks → analyze → implement → converge |
| VII. Living Spec | spec já ajustada (30 min no pagamento × 2 h na reserva; teste 0/A) |
| VIII. Verify antes do núcleo | `verify_310.py` escrito e rodado contra `98192e8` antes do núcleo; os "deve falhar no HEAD" falhando pelo motivo certo |
| IX. Dinheiro BRL | `Decimal`; centavos só no cliente; `formatBRL` no front |
| X. Mobile-first público | página do pedido e campanha conferidas em 375×812 |
| XI. Framer Motion | só nas transições existentes da página do pedido; `useReducedMotion` |
| XII. Combobox / Maps | não se aplica (nenhuma lista > 10 nova) |
| XIII. RBAC declarado | público por token (retorno); COMERCIAL/SUPERADMIN (a conferir, cancelar); SUPERADMIN (settings); linhas em `docs/01` §4.3 |
| XIV. Config / efeito externo | `_suppress_infinitepay` + `INFINITEPAY_ALLOW_LOCAL_CALLS` no mesmo commit do cliente; `INFINITEPAY_API_KEY` default `""` (desligada = fluxo atual); criação de evento de venda respeita `CALENDAR_SUPPRESS_EVENT_WRITES` |
| Stack | migration à mão, `down_revision='c5d2f7a9e306'` (ajustar no merge, ver data-model); sem Jinja; nenhum segredo no código nem no SiteSetting novo |
| Operação e Deploy | não toca `startCommand`; migration aditiva (ensaio de upgrade/downgrade em dump fresco mesmo assim); deploy à noite; pós-deploy: ligar o interruptor (quickstart §2) |

Sem violação a justificar.

## Estrutura do projeto

### Documentação (esta feature)

```text
specs/310-pagamento-loja-virtual/
├── spec.md · plan.md · research.md · data-model.md · quickstart.md
├── contracts/api-310.md
├── pesquisa/            # auditoria, operadoras, refutação (19/10)
├── checklists/
├── tasks.md             # /speckit-tasks
├── verify_310.py        # antes do núcleo
└── limpar_venda_teste.py
```

### Código

```text
migrations/versions/<rev>_pagamento_loja_virtual_310.py   # aditiva + backfill de state
app/models.py                     # colunas novas (SiteSetting, VirtualOrder, VirtualPaymentNotification, VirtualCampaign)
app/constants.py                  # antecedência, folga, motivos, desfechos, sala
app/config.py                     # _suppress_infinitepay, INFINITEPAY_API_KEY
app/integracoes/infinitepay_client.py   # 4 resultados, código da recusa, trava, X-Api-Key/options
app/marketing/virtuais_ops.py     # decidir_pagamento, reservar/listar (2 h), _gerar_link_pagamento,
                                  # _liberar_reserva (trava do pedido), expirar_reservas, avisos
                                  # (gravar/processar/reprocessar), retorno, cancelar_pedido_pago,
                                  # a conferir, retentar_salas longo, client_token, seconds_left
app/api/virtuais_public.py        # retorno; reservar/pedido alterados; ip_do_cliente
app/api/virtuais_webhook.py       # resposta rápida, token anterior, sem token sem NSU, limite, 64 KB
app/api/virtuais_read.py | virtuais_write.py   # a conferir, cancelar, listada, publicar
app/api_utils.py (ip_do_cliente)  · app/__init__.py (key_func do Limiter; filtro do log de acesso)
app/admin/config_ops.py · app/api/admin_config_read.py   # R7
app/notificacoes/notificacoes_ops.py   # KIND_VIRTUAL_ATENCAO
app/calendar/service.py (private_props) · app/calendar/routes.py (pular marca da loja na sync)
app/email_service.py              # e-mail de cancelamento com os motivos novos
frontend/server.js                # X-Manto-Client-Ip; máscara do token nos logs
frontend/apps/public/src/pages/{CampanhaVirtualPage,PedidoVirtualPage}.tsx · lib/virtuais.ts
frontend/apps/internal/src/pages/{AdminSettingsPage,VirtuaisDevolucoesPage,VirtuaisCampanhaFormPage}.tsx
frontend/apps/internal/src/lib/{adminConfig,virtuais}.ts
DEVELOPMENT.md (§Operar a produção) · .claude/skills/manto-deploy (regra da campanha) · docs/00–05
```

**Decisão de estrutura**: tudo de negócio fica em `virtuais_ops.py` (já é o núcleo da loja); a única
coisa que sai do domínio é o `ip_do_cliente` (transversal, usado pelo Limiter) e a marca da agenda
(dois pontos pequenos no calendar, sem refatorar o que o `docs/00` §7 manda não mexer).

## Ordem de entrega (vira as fases do tasks.md)

1. **Fundação**: migration + modelos + constantes + trava da operadora + cliente com 4 resultados →
   `verify_310.py` escrito e rodado (os cenários de núcleo falham no HEAD).
2. **H1 + H2 (núcleo de dinheiro)**: `decidir_pagamento`, travas, efetivar no banco antes do Google,
   aviso assíncrono e reprocessamento, retorno, varredura nova, pagamento em dobro, folga e vaga.
3. **H3 + H5**: interruptor, publicação, tela de configurações, recusa da operadora, privacidade,
   segredo fora dos logs.
4. **H4**: `X-Manto-Client-Ip` + `ip_do_cliente`.
5. **H6 + R15**: a conferir, sino, cancelar pedido pago.
6. **H7 + H8 + H9**: família, sala até a chamada, marca na agenda, API Key condicional.
7. **H10**: campanha fora da vitrine, limpeza de teste, roteiro; docs; converge; testes A e C com o
   dono depois do deploy.

## Rastreamento de complexidade

Nenhuma violação.
