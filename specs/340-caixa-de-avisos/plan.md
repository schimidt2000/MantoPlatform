<!-- ADAPTADO PARA A MANTO (2026-09-08) — reaplicar após qualquer atualização do Spec Kit; para este
     arquivo o hash em .specify/integrations/speckit.manifest.json deixa de conferir de propósito. -->
# Plano de implementação: 340 — caixa de avisos fora do deploy

**Branch**: `340-caixa-de-avisos` | **Data**: 2026-11-10 | **Spec**: [spec.md](./spec.md)

**Input**: `/specs/340-caixa-de-avisos/spec.md`

**Nota**: preenchido pelo `/speckit-plan`. A constituição (`.specify/memory/constitution.md`,
v3.1.0) é lida em tempo de execução — o Constitution Check abaixo é o que ela cobra.

## Resumo

O aviso de pagamento da InfinitePay passa a entrar por um serviço web separado, `manto-avisos`
(`servicos/avisos/app.py`, WSGI puro + gunicorn + psycopg2), que confere o segredo, guarda o corpo
numa tabela nova (`virtual_payment_inbox`) e responde. Sem disco e com healthcheck, ele nunca fica
fora num deploy, e o `rootDir` faz com que só reinicie quando a própria pasta muda. O backend drena
a caixa a cada 10 s e no início de cada varredura, chamando as funções da 310 sem alterá-las. A
página de retorno da família ganha retentativa pelo próprio TanStack Query. O `render.yaml` ganha o
serviço novo, o healthcheck do frontend e o filtro de caminhos do backend. A regra R-20 sai da
documentação e a constituição vai para 3.2.0. Pesquisa: [research.md](./research.md).

## Contexto técnico

**Linguagem/Versão**: Python 3.11 (Flask + SQLAlchemy) no backend; Python 3.11 WSGI puro no
receptor; TypeScript + React 18 (Vite) no frontend

**Dependências principais**: backend inalterado. Receptor: `gunicorn==23.0.0`,
`psycopg2-binary==2.9.10` (as versões da raiz), biblioteca padrão (`hmac`, `json`, `zoneinfo`,
`threading`). Frontend: `@tanstack/react-query` (`retry`/`retryDelay` de `useMutation`)

**Armazenamento**: PostgreSQL (`manto-postgres`). Tabela nova `virtual_payment_inbox`
([data-model.md](./data-model.md)); o receptor lê `site_settings` (3 colunas do segredo) e escreve
só na caixa

**Verificação**: `specs/340-caixa-de-avisos/verify_340.py` contra **`manto_340`** (ver
Rastreamento de complexidade); receptor exercitado com `werkzeug.test.Client` sobre o WSGI;
InfinitePay e Google por dublê; regressão 310/205/304; `npm run typecheck`; tela de retorno em
375×812

**Plataforma-alvo**: Render — `manto-backend` (python, disco), `manto-frontend` (node),
`manto-avisos` (python, **novo**, sem disco), `manto-postgres`

**Tipo de projeto**: SPA desacoplada (API JSON + React) + serviço receptor

**Metas de desempenho**: receptor responde em < 1 s (pedido da operadora); aviso decidido em
≤ ~10 s com o backend no ar

**Restrições**: o receptor não importa `app/`; segredo nunca em log nem em banco; URL do aviso é
constante do código (Princípio XIV); `registrar_aviso`/`processar_aviso`/`decidir_pagamento` não
mudam; rota antiga do backend continua

**Escala/escopo**: 1 tabela, 1 serviço com 3 rotas, 1 função de núcleo + 1 thread, 1 config, 1
hook React alterado, 3 blocos no `render.yaml`, docs

## Constitution Check

*GATE: aprovado antes da Phase 0; reavaliado após a Phase 1.*

| Princípio / seção | Como o plano cumpre (ou por que não se aplica) |
|---|---|
| I. Reutilizar antes de criar | O dreno chama `registrar_aviso`, `registrar_aviso_invalido`, `processar_aviso` e `_avisar_a_conferir` como estão; a thread segue o molde de `_start_virtual_sweep`; a retentativa usa `retry`/`retryDelay` do TanStack. O receptor repete três regras curtas do backend (segredo, teto de corpo, IP do cliente) porque não pode importar `app/` (research R3) — o verify confere que as duas pontas concordam |
| II. Padrões de código | type hints e docstrings Google; constantes no topo (`CORPO_MAXIMO`, limites, tetos); funções ≤ ~30 linhas; `ruff check` nos tocados, `ruff format` só nos arquivos novos |
| III. Camadas / API First | Núcleo novo em `virtuais_ops.py` (sem `flask.request`); receptor responde JSON; nenhum endpoint novo no backend (nada a registrar em `app/api/__init__.py` nem em `BACKEND_PREFIXES`); config com default real em `app/config.py` |
| IV. Não quebrar o que funciona | Tudo aditivo: tabela nova, rota antiga intacta, funções da 310 intactas, regressão 310/205/304. O único comportamento alterado do backend é a base do `webhook_url` dos links novos, com saída por env (quickstart §3) |
| V. UI/UX com feedback | A página segue em "Confirmando…" enquanto tenta; nenhum texto novo |
| VI. Esteira (Nível 1) | esteira completa; artefatos em `specs/340-caixa-de-avisos/` |
| VII. Living Spec | spec antes do código; constituição emendada (3.2.0) no mesmo ciclo — mudança de infraestrutura |
| VIII. Verify antes do núcleo | `verify_340.py` na fase Foundational; contra a `main` os cenários do dreno e do receptor ficam BLOQUEADOS (função/arquivo ausente) e os de `render.yaml`/config FALHAM |
| IX. Dinheiro BRL | não toca valor |
| X. Mobile-first público | a página do pedido é conferida em 375×812 |
| XI. Framer Motion | sem mudança visual |
| XII. Combobox / Maps | não se aplica |
| XIII. RBAC declarado | rota do receptor pública com segredo (mesma regra da 310); `/health*` públicas sem dado; linha em `docs/01` §4.3 |
| XIV. Config / efeito externo | `AVISOS_BASE_URL` constante + `INFINITEPAY_AVISO_BASE_URL` por `_url_para_fora`; o receptor não escreve fora do banco; o dreno herda as travas da 310 (`INFINITEPAY_SUPPRESS_CALLS`, `CALENDAR_SUPPRESS_EVENT_WRITES`, `_suppress_mail`) |
| XV. Texto por superfície | nenhum texto visível novo; a mensagem do sino segue o tom interno ("Loja virtual: aviso de pagamento parado na caixa") |
| Stack | migration à mão (`down_revision` = head da `main`); sem Jinja; sem segredo no repositório |
| Operação e Deploy | `startCommand` do backend **não** muda; `render.yaml` muda em três commits isolados, publicados à noite com os Events abertos; validador rodado mesmo assim |

**Reavaliação pós-design**: sem violação nova. O receptor é a única peça fora do desenho em camadas
— é infraestrutura de borda, não domínio (a decisão segue no backend).

## Estrutura do projeto

### Documentação (esta feature)

```text
specs/340-caixa-de-avisos/
├── spec.md · plan.md · research.md · data-model.md · quickstart.md
├── contracts/manto-avisos.md
├── checklists/requirements.md (+ /speckit-checklist)
├── tasks.md             # /speckit-tasks
└── verify_340.py        # Princípio VIII — escrito antes do núcleo
```

### Código

```text
servicos/avisos/app.py            # NOVO — receptor WSGI (rotas, segredo, limites, gravação)
servicos/avisos/requirements.txt  # NOVO — gunicorn, psycopg2-binary
servicos/avisos/README.md         # NOVO — o que é, por que não importa app/, como rodar local
app/models.py                     # VirtualPaymentInbox
migrations/versions/e340c1a2b3d4_caixa_de_avisos.py   # NOVO, aditiva
app/constants.py                  # VIRTUAL_CAIXA_*
app/config.py                     # AVISOS_BASE_URL, INFINITEPAY_AVISO_BASE_URL, VIRTUAL_CAIXA_INTERVAL
app/marketing/virtuais_ops.py     # drenar_caixa_de_avisos (+ auxiliares); ciclo_de_varredura; webhook_url
app/__init__.py                   # _start_caixa_de_avisos
frontend/apps/public/src/lib/virtuais.ts   # useRetornoCheckout: retry/retryDelay
render.yaml                       # manto-avisos; healthCheckPath do frontend; buildFilter do backend
```

**Decisão de estrutura**: `servicos/` na raiz, fora de `app/` e de `frontend/`, para o `rootDir`
do Render isolar o build e o gatilho de deploy (R9). O núcleo do dreno mora em `virtuais_ops.py`
porque é parte da regra do aviso da loja (310), ao lado de `reprocessar_avisos`.

## Ordem de entrega (commits)

1. `docs(340)`: spec, plano, tarefas.
2. `test(340)`: `verify_340.py` (falha/bloqueia pelos motivos certos).
3. `feat(340)`: modelo + migration + constantes + config + dreno + thread + `webhook_url`.
4. `feat(340)`: receptor `servicos/avisos/`.
5. `feat(340)`: retentativa do retorno.
6. `chore(340)`: `render.yaml` — serviço `manto-avisos` (commit sozinho).
7. `chore(340)`: `render.yaml` — `healthCheckPath` do frontend (commit sozinho).
8. `chore(340)`: `render.yaml` — `buildFilter` do backend (commit sozinho).
9. `docs(340)`: constituição 3.2.0, `DEVELOPMENT.md`, skill `manto-deploy`, `CLAUDE.md`, `docs/00–05`.

## Rastreamento de complexidade

| Violação | Por que é necessária | Alternativa mais simples rejeitada porque |
|---|---|---|
| Verify contra `manto_340`, não `manto_local` (Princípio VIII) | o `manto_local` está na migration `d334b2c4e6f8` do CRM 334 (sem push); `flask db upgrade` desta branch não a encontra | refazer o `manto_local` apagaria o esquema das sessões do CRM; `manto_340` é o dump de produção de 10/11 02:00, mesma natureza do espelho |
| Três regras repetidas no receptor (segredo, teto de corpo, IP) — Princípio I | o receptor não pode importar `app/` (R3) | importar `app/` traria threads, Google e e-mail para o receptor e o acoplaria a todo deploy do backend; o verify prova que as duas pontas aceitam e recusam os mesmos casos |
