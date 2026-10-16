<!-- ADAPTADO PARA A MANTO (2026-09-08) — reaplicar após qualquer atualização do Spec Kit; para este
     arquivo o hash em .specify/integrations/speckit.manifest.json deixa de conferir de propósito. -->
# Plano de implementação: Papai Noel em data especial — tabela de preços com faixa de 24 e 25/12 e gatilho pela data do evento

**Branch**: `307-natal-papai-noel-calculadora` | **Data**: 2026-10-15 | **Spec**: [spec.md](./spec.md)

**Input**: `/specs/307-natal-papai-noel-calculadora/spec.md`

**Nota**: preenchido pelo `/speckit-plan`. A constituição (`.specify/memory/constitution.md`,
v3+) é lida em tempo de execução — o Constitution Check abaixo é o que ela cobra. Base técnica: o
plano aprovado pelo dono em 15/10 (`.claude/plans/precisamos-fazer-uma-pequena-compressed-platypus.md`)
mais as correções dos dois refutadores do workflow (piso de cachê, horas lineares, `_migrate`
defensivo, botão travado durante o debounce, teto pela data do evento).

## Resumo

A tabela de preços (`pricing_config`) ganha o bloco `datas_especiais` (faixa `natal`: dias `12-24` e
`12-25`, markup 3,34, cachês de Noel/Ajudante/Coordenador, piso para os demais, nota). O cálculo do
orçamento resolve a faixa a partir de `event_date` e a aplica no lugar do markup normal e dos cachês
de tabela, **antes** dos acréscimos/NF/transporte; o mesmo helper alimenta o teto de cachê das vagas
(`_compute_performer_caches`) pela data do evento. A tabela normal passa a ter "Papai Noel" 712 e
"Ajudante do Noel" 423 por migração guardada do JSON (valor editado nunca é tocado). Superadmin edita
o bloco pela Configuração de Preços; a calculadora avisa pela data e trava "Gerar Orçamento" durante o
recálculo; EducaManto fica neutro. Sem migration de banco.

## Contexto técnico

**Linguagem/Versão**: Python 3.11 (Flask + SQLAlchemy) no backend; TypeScript + React 18 (Vite)
no frontend

**Dependências principais**: Flask, SQLAlchemy; React, TanStack Query, Tailwind CSS, shadcn/ui
(`@manto/ui`), Framer Motion, `@manto/api-client`, `@manto/money` — nada novo

**Armazenamento**: PostgreSQL — `site_settings.pricing_config` (JSON TEXT, linha id=1) e
`orcamento_history.result_snapshot`/`form_snapshot` (JSON TEXT). **Sem migration**: nenhuma coluna
nova; o snapshot já guarda `event_date` (`quote_ops.py:595`).

**Verificação**: `specs/307-natal-papai-noel-calculadora/verify_307.py` contra `manto_local`
(cenários 1–18 da spec; login só pela API; configuração de preços real salva e restaurada no
`finally` por conexão separada); `cd frontend && npm run typecheck`; telas abertas no Browser pane
(`/orcamento` em 20/12, 24/12 e sem data; `/orcamento/configuracoes`; `/orcamento/:id`)

**Plataforma-alvo**: web — Render; superfície interna (desktop)

**Tipo de projeto**: SPA desacoplada (API JSON + React)

**Metas de desempenho**: nenhuma nova. `calculate_quote` carrega a tabela uma vez (`cfg_precos`) e
a repassa a `faixa_especial`, `markup_vigente` e `aplicar_markup`; os getters antigos continuam
chamando `settings.load()` por conta própria (o objeto já está na sessão — sem SQL a mais).

**Restrições**: data comparada por recorte de texto (`AAAA-MM-DD` → `MM-DD`), nunca `datetime`/
`new Date` com fuso (a casa já se queimou: `OrcamentoPicker.tsx:48-53`); chave ausente em snapshot
antigo = conta de hoje; `MemoriaLinha.tipo` é união fechada no TS — não criar tipo de linha novo;
`_migrate` roda dentro do `try` de `load()` — qualquer exceção ali devolve os DEFAULTS do código para
a tabela inteira (markup 3,0 e sem "Papai Noel"), logo o código novo ali é defensivo; EducaManto
chama `calculate_quote` com `event_date` (`EducaMantoCalculadoraPage.tsx:174-183`) e tem de ficar
neutro; deploy só a partir das ~19h com a calculadora fechada pela equipe; o 3b do backlog vai
reescrever `calculate_quote` em "por dia" — a mudança aqui é pequena, localizada e neutra quando
ausente.

**Escala/escopo**: 0 tabelas/colunas novas; 0 endpoints novos (2 contratos ampliados:
`POST /api/orcamento/settings`, `POST /api/orcamento/calcular`; `GET /opcoes` já devolve o bloco;
`DELETE /settings/especiais/<nome>` também limpa a sobrescrita); 3 telas tocadas (calculadora,
resultado, configuração de preços); 8 arquivos Python (+ o verify), 4 TS/TSX tocados e 2 componentes
novos (`PriceTable` extraído, `DatasEspeciaisCard`); três domínios (orcamento, calendar, educamanto).

## Constitution Check

*GATE: aprovado antes da Phase 0; reavaliado após a Phase 1 — sem violação nova.*

| Princípio / seção | Como o plano cumpre (ou por que não se aplica) |
|---|---|
| I. Reutilizar antes de criar | Reusa `settings.load()/_migrate()/_ensure4`, os getters de `pricing.py`, `calculate_quote`, `_compute_performer_caches` (fonte única do teto), `AgendaNoDiaAlert` (padrão visual do aviso), `PriceTable` (extraída para componente e reusada) e `useSaveOrcamentoSettings`, `json_error`. Regras novas com UMA fonte: `pricing.cache_na_faixa` (sobrescrita × piso — venda e teto), `pricing.markup_vigente` (markup da conta, da memória e do `markup_used`), `settings.faixa_especial` (data → faixa; o React não recalcula: o aviso lê `quote.data_especial` do servidor), `orcamento_evento_ops.data_do_evento` (data do teto na criação e no vínculo) |
| II. Padrões de código | Type hints e docstrings Google nos helpers; constantes (`MARKUP_FAIXA_MIN/MAX`, `NOTA_FAIXA_MAX_CHARS`, `ROTULO_FAIXA_MAX_CHARS`, `CHAVE_FAIXA_RE`, `PAPAI_NOEL_CACHE_ANTIGO`) no topo de `settings.py`; helpers novos ≤ 30 linhas; TS estrito (`FaixaEspecial`); `ruff check` nos tocados. `calculate_quote`, `_compute_performer_caches` e `settings_save` JÁ excediam 30 linhas — a 307 só acrescenta chamadas a helpers (ver Rastreamento) |
| III. Camadas / API First | Regra em `app/orcamento/settings.py` (`validar_datas_especiais` com `SettingsValidationError(fields)`, `faixa_especial`, migração) + `pricing.py` + `quote_ops.py` (puros); o endpoint só chama o núcleo e traduz a recusa em `json_error(400, fields)`; nenhum módulo/rota novos; `_compute_performer_caches` continua em `calendar/routes.py` (dívida `docs/05:208`, fora do escopo mover) |
| IV. Não quebrar o que funciona | Mudança aditiva: parâmetro `faixa=None` nos getters; sem faixa, totais/mensagem/memória/PDF byte a byte iguais (cenários 1, 2, 15, 16, 17); `_migrate` defensivo (cenário 12); EducaManto neutro (cenário 10); os 3 chamadores de `_compute_performer_caches` conferidos |
| V. UI/UX com feedback | Aviso dourado (do `quote.data_especial`) e dica com a data vazia; "Gerar Orçamento" vira "Recalculando…" e fica `disabled` do payload mudar até a resposta chegar (`seq` descarta resposta antiga); card de config salva pelo botão existente com `loading`/sucesso/erro; 400 com `fields` → o campo recusado ganha `aria-invalid`, borda vermelha, mensagem e o foco (`DatasEspeciaisCard`) |
| VI. Esteira (Nível 1) | specify → clarify (feito) → plan (este) → checklist → tasks → analyze → implement → converge; artefatos em `specs/307-…/` |
| VII. Living Spec | spec escrita antes do código, com Clarifications do dono (15/10) |
| VIII. Verify antes do núcleo | `verify_307.py` escrito na Foundational e rodado vermelho: sem a feature, 1–9, 11–13, 15 e 16 falham; 10 e 14 passam por desenho (paridade e gate existentes). Desvio registrado: o `settings.py` (migração + `faixa_especial`) foi escrito ANTES do verify; a prova vermelha de 1, 2 e 12 foi refeita contra o `settings.py` da `main` e anexada ao `verify_307_primeira_falha.txt`. Sem `--regressao` o 17 sai PULADO, fora da contagem |
| IX. Dinheiro BRL | `MoneyInput` (via `PriceTable`) para cachês, piso e também para o coeficiente de markup — exatamente como o card de Markup atual já faz; `format_brl` na mensagem; totais `round(…, 2)` como hoje (float — dívida pré-existente, fora do escopo); markup gravado com 2 casas HALF_UP |
| X. Mobile-first público | não toca superfície pública |
| XI. Framer Motion | aviso dourado entra/sai com `AnimatePresence` + `motion.div`; chips de dias com `AnimatePresence` + `motion.span`; tudo com `useReducedMotion()` |
| XII. Combobox / Maps | Nenhum select novo: as sobrescritas do card são chips/botões. O `<select>` nativo de especiais do `PerformersEditor` passa de 11 para 12 itens com "Ajudante do Noel" — violação **já existente** do XII.1, levada ao dono (ver Rastreamento de complexidade) |
| XIII. RBAC declarado | `POST /api/orcamento/settings` continua `_require_superadmin`; `/calcular` e `/opcoes` continuam `_require_vendas`; linha de `docs/01` §4.3 revisada; cenário 14 (COMERCIAL → 403) |
| XIV. Config / efeito externo | sem env nova; sem escrita externa |
| Stack | sem migration; sem Jinja; sem segredo |
| Operação e Deploy | não toca `startCommand`; sem migração; deploy em lote à noite |

## Estrutura do projeto

### Documentação (esta feature)

```text
specs/307-natal-papai-noel-calculadora/
├── spec.md              # /speckit-specify (+ clarify)
├── plan.md              # este arquivo (/speckit-plan)
├── research.md          # Phase 0
├── data-model.md        # Phase 1
├── quickstart.md        # Phase 1
├── contracts/api.md     # Phase 1
├── checklists/          # requirements.md (specify); /speckit-checklist
├── tasks.md             # /speckit-tasks
└── verify_307.py        # Princípio VIII — escrito antes do núcleo
```

### Código (caminhos reais)

```text
app/orcamento/settings.py          # DEFAULTS (especiais novos, datas_especiais), _migrate 307, faixa_especial()
app/orcamento/pricing.py           # faixa= nos getters, aplicar_markup(faixa), aplicar_piso()
app/orcamento/quote_ops.py         # calculate_quote: resolve a faixa, memória, quote.data_especial, nota
app/orcamento/pdf.py               # nota da faixa (após a frase de deslocamento)
app/calendar/routes.py             # _compute_performer_caches(data_evento=) + criação passa a data
app/calendar/orcamento_evento_ops.py  # vínculo 273 passa event.start_at
app/educamanto/quote_ops.py        # _totais_contratacao remove event_date
app/api/orcamento_write.py         # settings_save aceita/valida datas_especiais
frontend/apps/internal/src/lib/orcamento.ts                     # FaixaEspecial, PricingSettings, Quote.data_especial
frontend/apps/internal/src/pages/OrcamentoConfigPrecosPage.tsx  # card "Datas especiais — Natal"
frontend/apps/internal/src/pages/OrcamentoCalculadoraPage.tsx   # aviso, dica, botão travado
frontend/apps/internal/src/pages/OrcamentoResultadoPage.tsx     # nota da faixa
docs/01, 02, 03, 04, 05            # documentação viva
```

**Decisão de estrutura**: a regra mora onde a tabela já mora (`settings.py` resolve a faixa;
`pricing.py` aplica markup/cachê/piso; `quote_ops.py` só orquestra e expõe `data_especial`). O teto
das vagas não ganha regra própria: recebe a mesma faixa pelos mesmos getters, com a data do evento
quando o evento existe. Nenhum endpoint novo porque `GET /opcoes` já devolve `settings` inteiro e o
`POST /settings` já recebe o dict completo.

## Rastreamento de complexidade

| Violação | Por que é necessária | Alternativa mais simples rejeitada porque |
|---|---|---|
| XII.1 — `<select>` nativo de especiais com 12 itens (`PerformersEditor.tsx:138-149`, compartilhado com o EducaManto) | "Ajudante do Noel" precisa existir na tabela para a faixa normal (2.501/3.601) e para o piso; é o 12º item de um select que já tinha 11 | Trocar o select por `Combobox` hoje toca um componente compartilhado com a calculadora do EducaManto e não cabe no "para ontem"; a constituição manda corrigir ou o dono emendar — **decisão levada ao dono** no fechamento da 307; registrado em `docs/05` (#103) |
| II — `calculate_quote` (~525 l.), `_compute_performer_caches` (~260 l.) e `api_orcamento_settings_save` (~75 l.) já excedem 30 linhas | são as funções em que a regra tem de entrar | a 307 só acrescenta chamadas a helpers (`cache_na_faixa`, `markup_vigente`, `_rotulo_da_faixa`, `validar_datas_especiais`); quebrar as funções é refatoração lateral — dívida em `docs/05` |
| `_compute_performer_caches` segue em `app/calendar/routes.py` (não em `_ops`) | é a fonte única do teto, chamada em 3 pontos; mover é refatoração lateral | dívida já registrada (`docs/05:208`); aqui só ganha o parâmetro `data_evento` e passa a usar `cache_na_faixa` |

## Fases

### Phase 0 — Pesquisa (`research.md`)

Sem `NEEDS CLARIFICATION`. As decisões técnicas (gatilho pela data × seletor manual; piso; horas
lineares; `_migrate` guardado e defensivo; data do teto; botão travado; EducaManto) estão em
`research.md` com razão e alternativas.

### Phase 1 — Desenho

`data-model.md` (bloco `datas_especiais`, `quote.data_especial`, regras de validação),
`contracts/api.md` (os dois contratos ampliados + o que `/opcoes` devolve), `quickstart.md` (como rodar
o verify, as telas a abrir e os números esperados).

### Phase 2 — Tarefas (`/speckit-tasks`)

Ordem: Setup (branch já criada; ler `pricing_config` do espelho) → Foundational (`verify_307.py`
vermelho; `settings.py` DEFAULTS + `_migrate` + `faixa_especial`) → História 2 (tabela normal) →
História 1 (cálculo, memória, mensagem, PDF) → História 3 (teto) → História 6 (EducaManto) →
História 4 (endpoint + card) → História 5 (calculadora/resultado) → Polimento (ruff, typecheck, telas,
docs 01/02/03/04/05, converge). Estimativa: ~25 tarefas, 5–6 h + deploy à noite.

### Ordem com os outros itens

A 306 (dinheiro do cancelamento) está pausada: os modificados dela no stash `306-wip`, e os
untracked `docs/backlog/` e `specs/306-dinheiro-do-cancelamento/` continuam no disco (não entram em
commit algum da 307 — adicionar sempre por caminho). A 307 nasceu da `main` d855d1a e vai antes do
3b do backlog (restrição 11 do ENCAVALAMENTO: uma branch por vez em `quote_ops.py`). Depois do
merge: voltar à 306 e `git stash pop`.
