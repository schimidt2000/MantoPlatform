# Tasks: EducaManto por responsabilidades — fim dos pacotes por nível

**Input**: Design documents from `/specs/235-educamanto-responsabilidades/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/educamanto-endpoints.md, quickstart.md

**Tests**: A validação segue o padrão da casa — script `verify_235.py` contra `manto_local` + roteiro do quickstart (sem TDD formal).

**Organization**: Fases por user story (P1→P5), com fundação bloqueante antes.

## Path Conventions

Monorepo existente: backend em `app/`, frontend em `frontend/apps/internal/src/`, migrações em `migrations/versions/`.

---

## Phase 1: Setup

- [x] T001 Criar `app/educamanto/pdf_textos.py` com: constantes `PROVISORIO_*` (custos sonoplasta/téc. som/téc. iluminação por cenário; áreas X/Y do som — a divisão personagens×produção provisória vive SÓ nas colunas do banco, populadas pela migração T003), rascunhos dos textos por responsabilidade (Manto: "o que levaremos"; contratante: "mínimo exigido"), tooltips, avisos fixos (palco 5×4 m, camarim, visita técnica) e formas de pagamento — tudo num único módulo (gate de deploy = editar só este arquivo + colunas provisórias)
- [ ] T002 Adicionar chave `caminhao_sp: 800` ao default de `pricing_config['transporte']` em `app/orcamento/settings.py` (única mudança permitida no módulo orcamento — chave nova de config, sem alterar comportamento existente) e expor na tela de Configurações de Preços

## Phase 2: Foundational (bloqueia todas as stories)

- [x] T003 Migração Alembic `migrations/versions/xxxx_educamanto_musicais.py`: rename das tabelas (`educamanto_packages`→`educamanto_musicals`, `educamanto_items`→`educamanto_musical_items`, `package_id`→`musical_id`), colunas novas (num_personagens, num_producao, num_ensaios≥2, custo_som_*, custo_iluminacao_*, custo_cenario_*, custo_alimentacao_1s/2s), drop de `commission_rate`, poda dos níveis (manter ids Master 1/11/15/18/23/26/29, apagar 9/10/13/14/16/17/19/20/24/25/27/28/30/31/32 e seus itens), mover Som→custo_som_*, Catering apresentação→custo_alimentacao_*, remover item Transporte 600, tirar " - Master" dos nomes, popular num_personagens/num_producao (UAA 9+2 confirmado; demais provisórios a partir dos headcounts 10/9/7/9/10), num_ensaios=2
- [x] T004 Atualizar `app/models.py`: renomear models para `EducaMantoMusical`/`EducaMantoMusicalItem` com os campos novos, default `discount_days=3`, remover `commission_rate`; ajustar imports em todo o backend (`grep -r EducaMantoPackage app/`)
- [x] T005 Reescrever `app/educamanto/pricing_ops.py`: dataclass de responsabilidades, headcounts de ensaio (personagens+produção+ensemble) e de evento (+técnicos do caso), matriz técnica (sonoplasta fixo), blocos de custo condicionais (som/iluminação/cenário/alimentação), ensaios × num_ensaios, transporte caminhão-SP/2-vans (tarifas de `orcamento/settings`), fechamento mantido (margens, desconto>discount_days, teto do acréscimo, ceil100, ÷0,84) e à vista ×0,95 — remover `pessoas_transporte` e a lógica antiga de pacotes
- [x] T006 Criar `app/educamanto/musical_ops.py` (CRUD de musicais com validação num_ensaios≥2, nome único, custos≥0, duplicate com "Cópia de") e apagar `app/educamanto/package_ops.py`
- [x] T007 Rodar migração no `manto_local` (`.\scripts\db\run-local.ps1` + `flask db upgrade`) e validar o bloco 1 do quickstart.md (7 musicais, ids preservados, custos migrados, paridade numérica) — criar `verify_235.py` com essa checagem

**Checkpoint**: fundação pronta — banco migrado, motor de cálculo novo puro e testável.

---

## Phase 3: US1 — Calculadora por responsabilidades (P1) 🎯 MVP

**Goal**: vendedor monta orçamento marcando responsabilidades; valores/equipe reagem; RBAC de visibilidade no servidor.

**Independent Test**: quickstart blocos 2, 5 e 7 (matriz técnica, transporte, RBAC) numa única configuração.

- [x] T008 [US1] Reescrever `app/educamanto/quote_ops.py`: entrada de configuração única (musical, responsabilidades, dias, ensemble, fora_sp/km, acrescimo), validações (musical existe, d1+d2>0, km>0 quando fora_sp), montagem do resultado calculado no servidor; manter leitura de snapshots v1 intacta
- [x] T009 [US1] Atualizar `app/api/educamanto_read.py`: `GET /api/educamanto/musicals` (payload sem custos para a calculadora), `POST /api/educamanto/calcular` novo contrato, e o **corte de breakdown no servidor** para não-superadmin (remover item_rows/raw_cost/valor_base/desconto/blocos antes de serializar), conforme contracts/educamanto-endpoints.md
- [ ] T010 [P] [US1] Atualizar `frontend/apps/internal/src/lib/educamanto.ts`: tipos do contrato novo (Musical, Responsabilidades, ResultadoCalculo com breakdown opcional), hooks `useMusicals`/`useCalcularConfig`
- [ ] T011 [US1] Reescrever `frontend/apps/internal/src/pages/EducaMantoCalculadoraPage.tsx` (parte 1 — configuração única): seletor de musical, 4 blocos de responsabilidade com Switch Manto/contratante + tooltip (conteúdo de pdf_textos servido pela API de musicals), dias/ensemble/acréscimo, transporte (checkbox fora de SP + endereço/km), cards de valores (sem NF, com NF, à vista), equipe técnica exibida, aviso de teto do acréscimo, breakdown só quando a API o devolve — debounce 300ms, estados loading/erro TanStack, Framer Motion nas transições; preservar o campo "Data da apresentação" e o alerta de personagens já escalados no dia (GET /api/educamanto/personagens-no-dia)
- [ ] T012 [US1] Validar quickstart blocos 2, 5 e 7 contra `manto_local` (matriz nas 4 combinações com valores conferidos à mão em `verify_235.py`; RBAC pela resposta crua da API com usuário comercial)

**Checkpoint**: MVP utilizável — calcular e conferir na tela, sem PDF ainda.

---

## Phase 4: US2 — PDF por responsabilidades (P2)

**Goal**: PDF com mínimos/o que levamos, quantidades, avisos, à vista real, dias zerados ocultos, observação.

**Independent Test**: quickstart bloco 3 nas 4 combinações + bloco 8 (v1 intacto).

- [x] T013 [US2] Reescrever `app/educamanto/pdf.py`: página A4 por configuração (identidade visual mantida), seções por responsabilidade a partir de `pdf_textos.py`, quantidades da equipe, avisos fixos, valores sem/com NF + à vista 5%, linhas de dias só >0, observação (transbordo p/ página de continuação), remoção total de SHORT_DESC/LONG_DESC/`_tipo_for`; manter renderização de snapshot v1 (função separada, intocada)
- [x] T014 [US2] Atualizar `app/educamanto/quote_ops.py` + `app/api/educamanto_write.py`: `POST /api/educamanto/orcamento/gerar` recebe entradas, **recalcula tudo no servidor**, congela snapshot v2 (`{"version": 2, "configs": [...]}`), devolve PDF; erros por índice de configuração (`configs[i].campo`)
- [ ] T015 [US2] Campo de observação (até 2.000 chars) na Calculadora + botão "Gerar orçamento" com estados de feedback em `EducaMantoCalculadoraPage.tsx`
- [ ] T016 [US2] Validar quickstart blocos 3 e 8 (PDF nas 4 combinações; orçamento v1 antigo abre/baixa idêntico; novo grava version 2 com valores do servidor)

---

## Phase 5: US3 — Multi-páginas (P3)

**Goal**: N configurações editáveis (musicais podem diferir), uma página por configuração no PDF.

**Independent Test**: quickstart bloco 4.

- [ ] T017 [US3] Estado multi-configuração na `EducaMantoCalculadoraPage.tsx`: abas "Página 1..N", criar (cópia da atual), navegar, editar e remover (mínimo 1), cálculo debounced por página ativa
- [ ] T018 [US3] `gerar` já aceita `configs[]` (T014) — ligar o envio de todas as páginas, e validar quickstart bloco 4 (PDF multipágina, edição retroativa, bloqueio de remoção da última)

---

## Phase 6: US4 — Contratação Manto embutida (P4)

**Goal**: parte Manto reusando `calculate_quote` como fonte única; totais combinados por duração; NF sobre a soma.

**Independent Test**: quickstart bloco 6 + bloco 10 (orçamento de eventos sem regressão).

- [ ] T019 [P] [US4] Extrair `PerformersEditor.tsx` e `AcrescimosEditor.tsx` de `OrcamentoCalculadoraPage.tsx` para `frontend/apps/internal/src/components/orcamento/` (mesmo comportamento, tipos de `lib/orcamento.ts`) e fazer a página original consumi-los sem mudança visual
- [ ] T020 [US4] Backend: em `app/educamanto/pricing_ops.py`/`quote_ops.py`, aceitar `contratacao_manto` (payload + durações), chamar `app.orcamento.quote_ops.calculate_quote` com `nota_fiscal=False`/`fora_sp=False`, somar por duração ao líquido antes do ceil100/÷0,84 (FR-016), incluir memória da parte Manto no breakdown (só superadmin)
- [ ] T021 [US4] Frontend: botão "Adicionar contratação Manto" por página na Calculadora, montando os editores compartilhados + coordenador + durações (1h–4h e custom), herdando data/local; exibir totais combinados por duração
- [ ] T022 [US4] PDF: trecho "Contratação Manto — o que está incluso" (equipe + durações) e totais combinados por duração em `app/educamanto/pdf.py`; validar quickstart blocos 6 e 10 (incluindo `/orcamento` intacta)

---

## Phase 7: US5 — Administração de musicais (P5)

**Goal**: CRUD de musicais substitui a tela de pacotes; comercial vê sem custos.

**Independent Test**: quickstart bloco 2 com musical recém-criado.

- [x] T023 [P] [US5] `app/api/educamanto_write.py` + `educamanto_read.py`: CRUD `/api/educamanto/musicals*` (validações do contrato; listagem de gestão com custos só p/ superadmin; remover endpoints `/packages*`)
- [ ] T024 [US5] Criar `EducaMantoMusicaisPage.tsx` e `EducaMantoMusicalFormPage.tsx` (campos novos: personagens, produção, ensaios≥2, custos de som/iluminação/cenário/alimentação, itens; sem o campo comissão morto), atualizar rotas em `App.tsx`/`navigation.tsx` (/educamanto/musicais), apagar `EducaMantoPackagesPage.tsx`/`EducaMantoPackageFormPage.tsx`
- [ ] T025 [US5] Ajustar `EducaMantoHistoricoPage.tsx`: dialog "Ver" renderiza snapshot v1 e v2 (responsabilidades, técnicos, combinados); "Recalcular" de v1 mapeia pacote→musical (id preservado ou prefixo do nome; Econômica pré-marca alimentação/iluminação contratante) com aviso do mapeamento

---

## Phase 8: Polish & Cross-Cutting

- [x] T026 Desligar o Jinja do EducaManto: `app/educamanto/routes.py` vira só redirects 302 (rota a rota conforme contrato), apagar `templates/educamanto/` e helpers exclusivos do template; conferir quickstart bloco 9
- [ ] T027 `npx tsc --noEmit` limpo em `frontend/apps/internal`; rodada final completa do quickstart.md contra `manto_local`; rodar `verify_235.py` inteiro
- [ ] T028 Documentação viva: atualizar `docs/01_SISTEMA_E_BANCO.md` (schema/rotas/RBAC), `docs/02_MAPA_DE_PAGINAS_E_UX.md` (telas novas) e entrada no topo de `docs/03_HISTORICO_MUTACOES.md` (migração, regras, pegadinhas); registrar em `docs/05_DIVIDA_TECNICA.md` a baixa das dívidas resolvidas (fórmula duplicada Jinja, valores do cliente sem recálculo) e a pendência dos valores provisórios

---

## Dependencies & Execution Order

- **Setup (T001–T002)** → **Foundational (T003–T007)** → US1 → US2 → US3/US4 (podem intercalar; US4 depende de T014 p/ snapshot) → US5 → Polish.
- US3 depende de US2 (geração multi-config usa o `gerar` novo). US4 depende de US1 (motor) e toca o PDF (T022 depende de T013). US5 é independente após a fundação (pode rodar em paralelo com US2+), exceto T025 que depende do snapshot v2 (T014).
- Paralelizáveis dentro de fase: T010 ∥ T008-T009; T019 ∥ T020; T023 ∥ T024 (arquivos distintos).

## Implementation Strategy

MVP = Fases 1–3 (calculadora nova funcionando com RBAC). Entrega incremental: cada fase fecha num commit atômico com seu bloco do quickstart validado. Os valores provisórios (T001/T003) ficam grep-áveis por `PROVISORIO` — a troca pelos definitivos do dono é o gate de deploy, junto com a revisão dos textos de `pdf_textos.py`.
