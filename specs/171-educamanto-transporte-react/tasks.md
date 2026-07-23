# Tasks: Transporte explícito por dias no EducaManto + calculadora em React (171)

**Input**: Design documents from `specs/171-educamanto-transporte-react/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md,
contracts/educamanto-calculadora-endpoints.md, quickstart.md

**Tests**: verificação é o script de paridade `scripts/db/verify_171_educamanto_transporte.py`
contra `manto_local`, criado na Phase de Polish (mesmo padrão das fatias 165–170).

**Organização**: 2 user stories — US1 corrige o multiplicador de dias na tela Jinja atual (P1,
MVP, sem tocar em backend), US2 cria a calculadora equivalente em React (P2, precisa de API/ops
novos). US1 e US2 não dependem uma da outra (US1 não toca em Python; US2 nasce direto com a
fórmula correta).

## Phase 1: Setup

- [X] T001 Confirmar `manto_local` (Postgres) atualizado (`python -m flask db heads`) — sem
      migration nova nesta fatia (nenhuma mudança de schema).

## Phase 2: Foundational

**Nota de escopo**: nesta fatia, só a US2 (React) precisa de infraestrutura de API nova — a US1
(Jinja) é só um ajuste de JS no template existente e pode ser feita antes, depois ou em paralelo a
esta fase.

- [X] T002 [P] Criar `app/api/educamanto_read.py` (NOVO, esqueleto): reusa o `api_bp` único do
      projeto (não um blueprint próprio — convenção real do `app/api/`), gate `_require_use`
      reimplementado como função (paridade com `_CAN_USE` de `app/educamanto/routes.py`: papéis
      Comercial/Superadmin/Ensaio/Revendedor EducaManto).
- [X] T003 Importar o módulo por efeito colateral em `app/api/__init__.py` (mesma convenção das
      demais fatias — `api_bp` já é registrado uma única vez em `app/__init__.py`).

**Checkpoint**: infraestrutura de API pronta para a US2. US1 não depende desta fase.

---

## Phase 3: User Story 1 — Transporte multiplicado pelos dias do pacote, no Jinja (P1) 🎯 MVP

**Goal**: o valor de transporte somado ao valor final do EducaManto (tela Jinja atual) passa a ser
"valor de uma viagem × total de dias do pacote", exibido de forma explícita, em vez do valor de uma
única viagem independente do número de dias.

**Independent Test**: no EducaManto, preencher um pacote com mais de 1 dia total, calcular a
distância de um endereço fora de São Paulo, escolher van/carretinha/pessoas → a linha de resultado
mostra o valor da viagem, "× N dias" e o total; esse total (não o valor de uma viagem só) é o que
soma ao valor final sem/com nota e ao PDF gerado.

- [X] T004 [US1] Ajustar `calcTransporte()` em `app/templates/educamanto/index.html` (função hoje
      em torno da linha 608): ler o total de dias já calculado em `calcular()` (`d1 + d2`, mínimo
      1) e multiplicar `vt + afsp` por esse total antes de retornar `total` — manter `vt`/`afsp`
      individuais no retorno (sem multiplicar) para permitir exibir o valor de uma viagem separado
      do total multiplicado (FR-001, FR-002, FR-003).
- [X] T005 [US1] Conferir que `calcular()` (linha ~720) já invoca `calcTransporte()` a cada mudança
      de `d1`/`d2`/tipo/carretinha/carros/pessoas (via `oninput`/`onchange` existentes) — se algum
      desses campos não disparar recálculo automático hoje, adicionar o listener que falta
      (FR-005).
- [X] T006 [US1] Atualizar a linha de resultado do transporte (`#t-result-line`, dentro de
      `calcular()`, linha ~832) para exibir explicitamente: valor de uma viagem, "× N dias" e o
      total resultante, mantendo km/tipo de veículo/pessoas já exibidos hoje (FR-004). Quando N=1,
      a linha deve continuar clara sem soar redundante (ex.: omitir o "× 1 dia" ou deixá-lo, à
      escolha de quem implementar, desde que o valor de 1 dia bata com o comportamento anterior).
- [X] T007 [US1] Validar manualmente que `gerarOrcamento()` (linha ~942), que também chama
      `calcTransporte()`, herda automaticamente o total já multiplicado no payload enviado a
      `POST /educamanto/orcamento/gerar` — sem precisar de mudança adicional de código, já que
      reusa a mesma função ajustada em T004 (FR-006, paridade tela↔PDF).

**Checkpoint**: US1 completa e testável isoladamente — nenhuma mudança de backend necessária.

---

## Phase 4: User Story 2 — Mesma calculadora do EducaManto em React (P2)

**Goal**: uma tela nova em `frontend/apps/internal` reproduz a calculadora do EducaManto (pacote,
dias, ensemble, transporte já com a multiplicação por dias, totais sem/com nota, detalhamento),
consumindo API JSON nova que reusa a mesma regra de negócio (extraída para Python nesta fatia,
já que hoje só existe em JS no template Jinja). PDF, histórico e CRUD de pacotes continuam só na
tela Jinja, com link de saída visível.

**Independent Test**: na tela React, para os mesmos pacote/dias/ensemble/endereço usados no teste
da US1, os valores sem/com nota e a linha de transporte (com a multiplicação por dias) batem
exatamente com os obtidos na tela Jinja.

- [X] T008 [P] [US2] Criar `app/educamanto/pricing_ops.py` (NOVO): `pessoas_transporte(package,
      ensemble)` — deriva o nº de pessoas do item "Catering apresentação" (mesma regra do Jinja,
      feature 079); `calcular_transporte(km_ida, pessoas, dias_total)` — reusa `calcular_van` de
      `app.orcamento.transport` (sempre van com carretinha, decisão fixa da feature 080) para o
      valor de uma viagem, multiplica pelo `max(dias_total, 1)` (mesma regra da US1, agora em
      Python); `calcular_pacote(package, d1, d2, ensemble, acrescimo, transporte)` — reproduz em
      Python a lógica hoje só em JS (`valoresPacote`/`effectiveItemsFor`/cenário/desconto por
      dias/cap do acréscimo/`ceil100`), somando o transporte já calculado. Funções puras, type
      hints, docstrings Google-style, sem `flask.request`/`render_template` (Princípio III).
- [X] T009 [US2] Implementar `GET /api/educamanto/packages` em `app/api/educamanto_read.py`: lista
      `EducaMantoPackage.query.order_by(id)`, serializa via `to_dict()` já existente (conforme
      `contracts/educamanto-calculadora-endpoints.md`).
- [X] T010 [P] [US2] Implementar `GET /api/educamanto/distancia` em `app/api/educamanto_read.py`:
      reusa `app.maps.distance_km_ida` (mesmo cálculo da rota Jinja `/educamanto/api/distancia`,
      endpoint próprio na API por não depender de rota que renderiza página).
- [X] T011 [US2] Implementar `POST /api/educamanto/calcular` em `app/api/educamanto_read.py`:
      valida `package_id` (400 se inválido) e `d1 + d2 > 0` (400 se não), deriva pessoas via
      `pricing_ops.pessoas_transporte`, chama `pricing_ops.calcular_transporte`/`calcular_pacote`,
      serializa a resposta conforme o contrato (`scenario`, `item_rows`, `raw_cost`, `valor_base`,
      `desconto_aplicado`, `desconto`, `transporte`, `valor_final_sem_nota`,
      `valor_final_com_nota`).
- [X] T012 [P] [US2] Criar `frontend/apps/internal/src/lib/educamanto.ts` (NOVO): tipos TypeScript
      (`EducaMantoPackage`, `EducaMantoItem`, `PacoteCalculado`, `TransporteResultado`) e hooks
      TanStack Query — `usePackages()`, `useDistancia()` (mutation sob demanda, botão "Calcular
      distância"), `useCalcularPacote()` (mutation debounced a cada mudança relevante de input) —
      todos via `apiFetch` de `@manto/api-client`.
- [X] T013 [US2] Criar `frontend/apps/internal/src/pages/EducaMantoCalculadoraPage.tsx` (NOVO):
      seletor de pacote, campos de dias (1/2 sessões)/ensemble/acréscimo, bloco de transporte
      (endereço + botão calcular distância — sem seletor de tipo de veículo/carretinha, transporte
      é sempre van com carretinha e pessoas vêm calculadas pelo backend, igual à tela Jinja desde a
      feature 080), linha de resultado do transporte explícita (valor da viagem × dias = total,
      mesma clareza da US1), totais sem/com nota (`formatBRL`/`@manto/money`), tabela de
      detalhamento por item, desconto aplicado; loading (`Skeleton`)/erro (mensagem amigável
      pt-BR)/sucesso via TanStack Query (Princípio V); nenhum botão "morto" ao clicar; link visível
      para `/educamanto` (Jinja) para gerar PDF, ver histórico ou gerenciar pacotes (FR-009);
      transições Framer Motion ao trocar de pacote/expandir detalhamento, respeitando
      `useReducedMotion()` (Princípio IX).
- [X] T014 [US2] Adicionar rota (ex.: `/educamanto`) + item de menu/navegação em `App.tsx` (ou
      arquivo de rotas equivalente) de `frontend/apps/internal`, com RBAC de exibição igual à `_CAN_USE`
      da tela Jinja (FR-008).

**Checkpoint**: US2 completa e testável isoladamente; paridade de valores com a US1 confirmada.

---

## Phase 5: Polish & Verificação

- [X] T015 Criar `scripts/db/verify_171_educamanto_transporte.py` (gitignored): test client Flask
      contra `manto_local`, requests fora de `app_context` — cobre `GET /api/educamanto/packages`
      (200, 401 sem sessão, 403 papel sem acesso), `GET /api/educamanto/distancia` (200, 400),
      `POST /api/educamanto/calcular` com 1 dia (valor de uma viagem), múltiplos dias (valor
      multiplicado — comparar com o cálculo manual esperado), sem `km_ida`/transporte ausente
      (zero), 400 pacote inválido, 400 dias zerados.
- [X] T016 Rodar `ruff check app/` nos arquivos tocados/criados (`pricing_ops.py`,
      `educamanto_read.py`).
- [X] T017 Rodar `npx tsc --noEmit` e `npm run build` em `frontend/apps/internal`.
- [X] T018 Conferência no app real: Flask (contra `manto_local`) e Vite dev server rodados de
      verdade — login por HTTP real, `GET /educamanto` (Jinja) confirmado servindo o JS novo,
      `POST /api/educamanto/calcular` chamado por HTTP real com 1 dia vs. 3 dias (mesmo
      endereço/pessoas) confirmando `total(3 dias) = valor_viagem × 3`, e o módulo
      `EducaMantoCalculadoraPage.tsx` compilado/servido pelo Vite sem erro. **Limitação**: sem
      `chromium-cli`/Playwright neste ambiente (mesma limitação já registrada nas fatias 157/158),
      não foi possível literalmente clicar/tirar screenshot da tela — recomenda-se conferência
      visual manual antes do merge, se possível.
- [X] T019 Atualizar `docs/changelog.html` com a entrega (linguagem simples) e republicar no link
      existente.

## Dependencies

Setup (Fase 1) → Foundational (Fase 2, só bloqueia a US2) → US1 (P1, independente da Fase 2) e US2
(P2, depende da Fase 2) → Polish (Fase 5, depende de US1 e US2 completas). Dentro da US2: ops
(T008) → endpoints (T009–T011) → hooks frontend (T012) → página (T013) → rota (T014).

## Parallel Example: User Story 2

```bash
# Após T008 (pricing_ops.py) pronto, endpoints e frontend podem avançar em paralelo:
Task: "Implementar GET /api/educamanto/distancia em app/api/educamanto_read.py"
Task: "Criar frontend/apps/internal/src/lib/educamanto.ts com tipos e hooks TanStack Query"
```

## Implementation Strategy

MVP = US1 (ajuste na tela Jinja) — resolve o problema relatado (transporte subestimado em pacotes
de múltiplos dias) sem exigir nenhuma mudança de backend/API. US2 (calculadora em React) é a
segunda entrega, incremental, e nasce já com a fórmula corrigida (sem herdar o bug da US1 antes da
correção).
