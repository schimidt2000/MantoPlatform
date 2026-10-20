<!-- ADAPTADO PARA A MANTO (2026-09-08) — reaplicar após qualquer atualização do Spec Kit; para este
     arquivo o hash em .specify/integrations/speckit.manifest.json deixa de conferir de propósito. -->
# Plano de implementação: Produtos de tabela — a Visita Mágica vendida pelo preço da tabela de venda

**Branch**: `309-produtos-de-tabela` (worktree `C:\tmp\mp309`, da `main` `6356b80`) | **Data**:
2026-10-19 | **Spec**: [spec.md](./spec.md)

**Input**: `/specs/309-produtos-de-tabela/spec.md` + plano de análise
`docs/backlog/308-produtos-de-tabela-visita-magica.md` (árvore principal, untracked; o número no nome
é 308, a feature é a 309) + mapas de código do workflow `wf_21e30e2c-5fe` (citações conferidas contra
o HEAD `6356b80`).

**Nota**: preenchido pelo `/speckit-plan`. A constituição (`.specify/memory/constitution.md`,
v3+) é lida em tempo de execução — o Constitution Check abaixo é o que ela cobra.

## Resumo

A Visita Mágica passa a ser um **produto de tabela**: a tabela de preços ganha o bloco `produtos`
(preço fixo por visita, preço por faixa de data especial, composição de vagas com cachê "pela tabela"
ou fixo) e a vendedora o seleciona num card próprio da calculadora. O preço do produto entra na conta
**depois do markup e antes dos itens pós-markup** (`quote_ops.py:306-313` → novo bloco → `:315`), fixo
nas quatro durações e fora da régua; os itens avulsos seguem a fórmula. As vagas do evento nascem das
vagas do produto com **teto = cachê da tabela vigente na data** (Noel 600 / 1.000 na faixa), pelo mesmo
caminho de hoje (`_compute_performer_caches` → prefill, criação, vínculo 273), com o cachê nascendo
vazio. "Papai Noel" e "Ajudante do Noel" voltam a dizer o cachê (600/270), a troca automática 600→712
da 307 sai, e um script de uma vez rebaixa os tetos 712/423 já gravados. Um módulo puro
`app/orcamento/produtos.py` é a fonte única para venda e teto. Sem migration; EducaManto neutro.

## Contexto técnico

**Linguagem/Versão**: Python 3.11 (Flask + SQLAlchemy) no backend; TypeScript + React 18 (Vite)
no frontend

**Dependências principais**: Flask, SQLAlchemy, Alembic (migrations à mão); React, TanStack
Query, Tailwind CSS, shadcn/ui (`@manto/ui` — `Combobox` em `packages/ui/src/components/combobox.tsx:92`),
Framer Motion, `@manto/api-client` (`apiFetch`/`assetUrl`), `@manto/money` (`MoneyInput`, `brl`);
reportlab (`pdf.py`)

**Armazenamento**: PostgreSQL — produção no Render (`manto-postgres`, `render.yaml`); verificação
contra a cópia `manto_local`. Nenhuma coluna nova: o produto mora no JSON `site_settings.pricing_config`
(bloco `produtos` + `produtos_estimativa`) e no `OrcamentoHistory.form_snapshot`/`result_snapshot`
(chave `produtos`); `EventRole.cache_cap`/`cache_cap_note` já existem (`app/models.py:565-607`)

**Verificação**: `specs/309-produtos-de-tabela/verify_309.py` contra `manto_local` (login só pela API;
escrita por conexão separada; evento descartável criado pela API com escrita no Google suprimida;
20 cenários, 1 que DEVE FALHAR); `verify_307.py` reescrito onde afirma 712 e `verify_305.py` em
regressão; `cd frontend && npm run typecheck` (três SPAs); telas no Browser pane (`/orcamento`,
`/orcamento/:id`, `/orcamento/configuracoes`, `/events/new?orcamento_id=`)

**Plataforma-alvo**: web — Render (Flask API JSON + 3 SPAs servidas por `frontend/server.js`);
staff em desktop (calculadora e configuração são internas; nada público)

**Tipo de projeto**: SPA desacoplada (API JSON + React)

**Metas de desempenho**: o produto é resolvido a partir de `cfg_precos` (`quote_ops.py:129`) e da
`faixa` (`:146-147`) já carregados — sem `load()` adicional (a calculadora dispara request a cada
tecla). Hoje a função ainda recarrega a tabela em `:238`/`:299` e nos getters de `pricing.py`; a 309
não piora nem conserta isso (research D22)

**Restrições**: sem migration; chave `produtos` ausente = conta byte a byte a de hoje (padrão 262/305/
307); `_migrar_309` roda dentro do `try` de `load()` (`settings.py:569-578`) — exceção ali devolve os
DEFAULTS do código para a tabela INTEIRA, então a normalização nunca indexa sem conferir tipo; nada de
`<select>` nativo (XII.1); `MemoriaLinha.tipo` é união fechada (`lib/orcamento.ts:169-174`) e `FUNDO`
(`MemoriaDeCalculo.tsx:19-25`) precisam do tipo `produto`; EducaManto compartilha `calculate_quote`
(`educamanto/quote_ops.py:119-140`) e lê `total_*`/`memoria`/`team_lines`; pareamento posicional na
criação (`routes.py:3508-3523`) exige a mesma ordem de emissão no prefill e na criação; `verify_307`
afirma 712/2.501/3.601 e passa a afirmar 600/2.210/2.912; worktree próprio (a árvore principal está
com a 308 de outro chat)

**Escala/escopo**: 0 tabelas/colunas novas; 0 endpoints novos (5 alterados: `POST /orcamento/calcular`
e `POST /orcamento/salvar` aceitam `produtos`; `POST /orcamento/settings` aceita `produtos` +
`produtos_estimativa`; `GET /orcamento/opcoes` e `GET /orcamento/settings` passam a devolvê-los por já
devolver `settings` inteiro); 1 módulo puro novo; 1 script one-off; 3 componentes React novos
(`ProdutoLinha`, card da calculadora, card de configuração); 4 telas tocadas; 20 cenários de verify +
gabarito; 2 produtos padrão

## Constitution Check

*GATE: aprovado antes da Phase 0; reavaliado após a Phase 1.*

| Princípio / seção | Como o plano cumpre (ou por que não se aplica) |
|---|---|
| I. Reutilizar antes de criar | Reusa: `settings.load()/_migrate` e o molde `_migrar_307`/`validar_datas_especiais` (`settings.py:469-534`) para o bloco novo; `SettingsValidationError.fields` e o ramo de `api_orcamento_settings_save` (`orcamento_write.py:208, 276-282`); getters `get_especial_prices/get_coordenador_prices(faixa=)` e `calcular_maquiador` para "pela tabela vigente na data"; `_compute_performer_caches` e `_montar_cap_note` (`routes.py:2801-2832`) para o teto; `Combobox` de `@manto/ui`; `DatasEspeciaisCard` como molde do card de configuração (contrato de props/erros/foco, `DatasEspeciaisCard.tsx:26-55`); `useSaveOrcamentoSettings` manda `settings` inteiro (sem endpoint novo); padrão `calcPendente`/`seq` da 307 para o botão; molde `specs/239b-hotfix-carrinho-fora-de-sp/reclassificar_fora_de_sp.py` para o script. Nada de camada de repositório |
| II. Padrões de código | `produtos.py` com type hints, docstrings pt-BR e constantes (`TIPOS_DE_VAGA`, limites); `ruff check` nos tocados, `ruff format` só nos novos; TS estrito com tipos opcionais (`produtos?`); `calculate_quote` e `_compute_performer_caches` já excedem 30 linhas (docs/05 #106) — a 309 põe TODA a regra do produto em helpers puros de `produtos.py` (`resolver_produtos`, `split_coordenadores`, `incremento_make`, `total_na_duracao`, `linhas_da_memoria`, `itens_do_teto`, `avisos_para`…) e as duas funções só os chamam nos pontos em que o produto entra (antes do laço, depois do markup, nos pós-markup, na saída); o que sobra inline são as atribuições de `quote`/`snapshot` — registrado no Rastreamento de complexidade |
| III. Camadas / API First | núcleo puro em `app/orcamento/produtos.py` (sem `flask.request`); `orcamento_write.py` só traduz `SettingsValidationError` em 400 (como a 307); nenhum endpoint novo, nenhum módulo novo em `app/api/`; nada em `BACKEND_PREFIXES` (não há rota pública); exceção documentada: `routes.py` do calendar continua sendo o dono do teto (`docs/00` §7) |
| IV. Não quebrar o que funciona | aditivo: chave `produtos` ausente = conta de hoje (cenário 1 de paridade chave a chave); produto entra ANTES de acréscimos/NF (BV 305 e `_conta_inversa` em `orcamento_evento_ops.py:211-229` continuam); `cache_value` continua nascendo vazio (236/238 intactas); EducaManto com `pop` explícito (cenário 16); a ÚNICA mudança de comportamento para quem não usa produto é Noel/Ajudante avulsos a 600/270 — decisão do dono, registrada na spec (SC-003) e no `docs/03`; `verify_307` atualizado em vez de silenciado |
| V. UI/UX com feedback | TanStack Query (`useOrcamentoOpcoes`, `useCalcularOrcamento`, `useSaveOrcamentoSettings`); 400 do servidor por campo → `aria-invalid` + foco no card de configuração (molde 307); remover produto/vaga com `ConfirmDialog` de `@manto/ui` (não o `window.confirm` do molde); "Gerar Orçamento" com rótulo "Recalculando…" e travado na janela de deploy; avisos pt-BR vindos do servidor (`quote.avisos`); toasts existentes |
| VI. Esteira (Nível 1) | specify ✓ (309, worktree) → clarify ✓ (3 perguntas) → plan (este) → checklist → tasks (verify na Foundational) → analyze → implement → converge; artefatos em `specs/309-produtos-de-tabela/` |
| VII. Living Spec | spec com Clarifications de 19/10 antes de qualquer código; decisões D5–D12 do plano de análise viraram Premissas/FRs |
| VIII. Verify antes do núcleo | `verify_309.py` escrito e rodado VERMELHO antes de `produtos.py` (primeira falha guardada em `verify_309_primeira_falha.txt`); 20 cenários, cenário 17 DEVE FALHAR (COMERCIAL 403); config real salva/restaurada por conexão separada; evento descartável só pela API |
| IX. Dinheiro BRL | preços e cachês do produto como `float` com 2 casas no JSON, `parse_brl` na validação (como a 307), `Decimal` HALF_UP onde a 305 já usa (`valores_brl`); React com `MoneyInput`/`brl` de `@manto/money` |
| X. Mobile-first público | não se aplica (calculadora e configuração são internas, desktop) |
| XI. Framer Motion | lista de produtos selecionados e avisos com `AnimatePresence`/`motion.div` + `useReducedMotion`, como o `DataEspecialAlert` da 307 |
| XII. Combobox / Maps | seletor de produto é `Combobox` de `@manto/ui` (`clearable` padrão; `description`/`fallbackIcon`/`badge` por opção); o `<select>` nativo de especiais do `PerformersEditor` (docs/05 #103) NÃO é tocado nem agravado (o produto não entra nele) — fatia Nível 2 própria |
| XIII. RBAC declarado | nenhum endpoint novo; `_require_superadmin` em `POST /settings` e `_require_vendas` em `/calcular`, `/salvar`, `/opcoes` inalterados; linhas de `docs/01` §4.3 atualizadas (payload/bloco) |
| XIV. Config / efeito externo | nenhuma env nova; o script one-off é dry-run por padrão e `--execute` explícito; o verify cria evento com `_suppress_calendar_event_writes`/Google suprimido (`MANTO_SEM_THREADS=1`) |
| Stack | sem migration (`models.py` intocado); sem Jinja novo (o wrapper Jinja de criação `routes.py:4039-4041` continua passando as mesmas chaves — paridade mantida); sem segredo |
| Operação e Deploy | não toca `startCommand`; deploy à noite em lote; janela bundle novo × backend velho coberta por FR-017 (botão travado); pós-deploy: script dos tetos no Shell do Render (dry-run → `--execute`), conferência de `/orcamento/configuracoes` e de um orçamento com produto em produção |

## Estrutura do projeto

### Documentação (esta feature)

```text
specs/309-produtos-de-tabela/
├── spec.md              # /speckit-specify + /speckit-clarify (19/10)
├── plan.md              # este arquivo (/speckit-plan)
├── research.md          # Phase 0 — decisões D1–D20 com alternativas
├── data-model.md        # Phase 1 — JSON do bloco, snapshot/quote, item do teto
├── quickstart.md        # Phase 1 — como provar (verify, typecheck, telas, script)
├── contracts/api.md     # Phase 1 — payload/quote/snapshot, POST /settings, item do teto, CLI do script
├── checklists/          # requirements.md (/speckit-specify) + dinheiro-e-regressao.md (/speckit-checklist)
├── tasks.md             # /speckit-tasks
├── verify_309.py        # Princípio VIII — escrito antes do núcleo
└── verify_309_primeira_falha.txt
```

### Código (caminhos reais)

```text
app/orcamento/produtos.py                   # NOVO, puro: resolver_produtos, preco_do_produto, vagas_do_produto,
                                            #   cache_da_vaga, coordenadores_dos_produtos — fonte única venda × teto
app/orcamento/settings.py                   # DEFAULTS: especiais 600/270, bloco produtos (2 padrão) e produtos_estimativa;
                                            #   _migrar_307 sem a troca 600→712; _migrar_309 (setdefault + inversa guardada
                                            #   712→600/423→270 + normalização defensiva); validar_produtos (+ estimativa)
app/orcamento/quote_ops.py                  # produtos no payload → resolver; coordenador split; bloco do produto após
                                            #   "= Após markup"; memória tipo "produto"; avisos; personalizado; régua;
                                            #   quote.produtos/avisos; snapshot.produtos (congelado); mensagem
app/orcamento/pdf.py                        # linha do produto (+ "(estimativa)") após a lista da equipe
app/api/orcamento_write.py                  # settings_save: ramo produtos/produtos_estimativa → validar → 400 fields
app/educamanto/quote_ops.py                 # _totais_contratacao: payload.pop("produtos", None)
app/calendar/routes.py                      # _compute_performer_caches: vagas dos produtos primeiro (flat, pela tabela
                                            #   na data, cap_note "produto …"), split do coordenador, maquiador do
                                            #   produto; _build_orcamento_prefill: total_custom com produtos_total
app/calendar/orcamento_evento_ops.py        # _total_da_duracao: régua com produtos_total do snapshot
specs/309-produtos-de-tabela/rebaixar_tetos_noel_309.py  # NOVO: relatório + --execute (cache_cap 712/423 → 600/270);
                                            #   `scripts/oneoff/` é gitignored — o molde 239b também mora na pasta da spec
frontend/apps/internal/src/lib/orcamento.ts # ProdutoDeTabela, ProdutosEstimativa, Quote.produtos/avisos,
                                            #   snapshot.produtos, CalcularOrcamentoInput.produtos, MemoriaLinha.tipo
frontend/apps/internal/src/components/MemoriaDeCalculo.tsx          # FUNDO["produto"]
frontend/apps/internal/src/components/orcamento/ProdutoLinha.tsx      # NOVO: linha "📦 rótulo — preço de tabela" (fonte única das 3 telas)
frontend/apps/internal/src/components/orcamento/ProdutosCard.tsx      # NOVO: card da calculadora (Combobox + lista)
frontend/apps/internal/src/components/orcamento/ProdutosConfigCard.tsx# NOVO: card de configuração (molde DatasEspeciaisCard)
frontend/apps/internal/src/components/orcamento/PerformersEditor.tsx  # prop OPCIONAL coordenadoresInclusos (EducaManto não passa)
frontend/apps/internal/src/pages/OrcamentoCalculadoraPage.tsx         # estado produtos (5 lugares), card, avisos, botão travado,
                                                                      #   valor único quando só produto
frontend/apps/internal/src/pages/OrcamentoResultadoPage.tsx           # linha do produto junto das notas
frontend/apps/internal/src/pages/OrcamentoConfigPrecosPage.tsx        # card de produtos; rodapé filtra produtos.*
specs/307-natal-papai-noel-calculadora/verify_307.py                  # 712→600, 2.501→2.210, 3.601→2.912, teto 600
docs/01, docs/02, docs/03, docs/04, docs/05                           # documentação viva
```

**Decisão de estrutura**: o produto é um conceito do domínio Orçamento, então o núcleo mora em
`app/orcamento/produtos.py` e é importado pelo calendário (`routes.py` já importa `pricing`/`settings`
do orçamento para o teto — mesma direção da 307). A venda (`quote_ops`) e o teto (`routes`) chamam as
MESMAS funções com os MESMOS argumentos (`cfg_precos`, `faixa`), como `cache_na_faixa` fez na 307 — é
isso que impede "preço certo com teto errado". O preço aplicado E as vagas são **congelados no
snapshot** (`snapshot.produtos[]` com `preco_aplicado` e `vagas`), para o prefill, a criação e o
vínculo não dependerem da tabela viva para saber o que foi vendido nem para listar as vagas (pareamento
posicional estável; produto apagado continua produzindo as vagas); só o VALOR do cachê das vagas vem da
tabela viva na data do evento, como hoje. A régua >4h sai de uma função só (`total_na_duracao`) para a
venda, o prefill, `_total_da_duracao` e o BV da duração custom.
Na UI, o produto NÃO entra no `PerformersEditor` (que já viola XII.1 e é compartilhado com o
EducaManto): ganha card próprio, e o editor recebe só uma prop opcional para mostrar "N incluído(s) no
produto".

## Rastreamento de complexidade

| Violação | Por que é necessária | Alternativa mais simples rejeitada porque |
|---|---|---|
| `calculate_quote` (~540 l.) e `_compute_performer_caches` (~270 l.) continuam acima das 30 linhas do Princípio II (docs/05 #106) | a 309 precisa entrar em três pontos de cada uma (antes do laço, depois do markup, na emissão) | quebrar o núcleo agora dobraria o alvo da feature que já toca dinheiro em dois domínios; a 309 extrai TODA a regra nova para `produtos.py` (3 chamadas, zero ramo inline) e deixa a quebra para o 3b (gabarito de paridade), como o #106 já prevê |
| `routes.py` (calendar) continua sendo o dono do teto (`docs/00` §7) | o pareamento posicional e os extras vivem lá | mover o teto para `_ops` é refatoração lateral fora de escopo (constituição IV) |
