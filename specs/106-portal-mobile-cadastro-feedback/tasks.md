# Tasks: Checkup Mobile do Portal + Feedback de Validação no Cadastro

**Input**: Design documents from `/specs/106-portal-mobile-cadastro-feedback/`

**Prerequisites**: plan.md, spec.md, research.md (auditoria A–H), contracts/ui-contract.md, quickstart.md

**Tests**: não solicitados — verificação via [quickstart.md](./quickstart.md) (test client +
conferência visual em 320/360/390/430px). Sem migration, sem mudanças Python.

**Organization**: por user story; US1 (portal mobile) é o grosso; US2 (cadastro) é independente.

## Format: `[ID] [P?] [Story] Description`

## Path Conventions

Templates em `app/templates/portal/` e `app/templates/cadastro/`; CSS compartilhado em
`app/static/style.css`.

---

## Phase 1: Setup

- [X] T001 Confirmar app rodando contra a cópia local (`.\scripts\db\run-local.ps1`) e identificar um talento de teste com convite pendente, eventos futuros com ensaio e histórico com valores (para o roteiro do quickstart)

---

## Phase 2: Foundational

*(vazio — as duas stories são independentes e não há pré-requisito compartilhado)*

---

## Phase 3: User Story 1 - Portal confortável no celular (Priority: P1) 🎯 MVP

**Goal**: aplicar as correções da auditoria ([research.md](./research.md), achados A–H) — dinheiro
BR, alvos de toque ≥44px, pares de campos empilhados, indent/wrap corrigidos, fontes ≥12px.

**Independent Test**: roteiro US1 do [quickstart.md](./quickstart.md) em 4 viewports.

### Implementation for User Story 1

- [X] T002 [P] [US1] Achado A em `app/templates/portal/home.html`: trocar TODAS as ocorrências `R$ {{ "{:,.0f}".format(x) }}` por `R$ {{ x | brl }}` (cachê+transporte do convite, cachê+transporte do card de evento, Recebido/Pendente do resumo, valor do histórico recente)
- [X] T003 [P] [US1] Achado A em `app/templates/portal/historico.html`: idem nos 3 cards de resumo e no valor por evento
- [X] T004 [US1] Achado B em `app/templates/portal/home.html`: materiais de ensaio `margin-left:98px` → `16px`; permitir quebra no cluster direito do "Histórico recente" (flex-wrap no `.event-row` e no bloco de badges/valor); badges `.days-badge`/`.pay-badge` 11px → 12px (achado G)
- [X] T005 [P] [US1] Achado C em `app/templates/portal/profile.html`: adicionar classe `grid-pair` nos 4 pares inline `grid-template-columns: 1fr 1fr`; × de remover foto 20px → 28px; cores `#666`/`#888` → `var(--muted)`, `#e0e0e0`/`#f0f0f0` → `var(--line)`, `#e45858` → `var(--red)`
- [X] T006 [P] [US1] Achado D+C em `app/static/style.css` (bloco `@media (max-width: 768px)` existente do portal): `.portal-wrap .btn { min-height: 44px; }` e `@media (max-width:480px) { .grid-pair { grid-template-columns: 1fr !important; } }`
- [X] T007 [P] [US1] Achado F em `app/templates/portal/rate_detail.html`: `.mini-stars label` 26px → 30px, gap 2px → 6px, padding para alvo ≥38px; achado G em `app/templates/portal/login.html` (hint 11px → 12px) e `app/templates/portal/figurino_viewer.html` (`.fig-photo-hint` 11px → 12px; badge `.pay-badge` se houver)
- [X] T008 [US1] Achado H — auditoria residual: renderizar/inspecionar `first_access.html`, `forgot_password.html`, `reset_password.html`, `change_password.html`, `terms.html` em 320–430px e corrigir problemas concretos encontrados (sem redesenho)
- [X] T009 [US1] Verificação do roteiro US1 do [quickstart.md](./quickstart.md): script test client (render 200 das telas + regex proibindo padrão americano `\d,\d{3}` no HTML) + conferência visual nos 4 viewports

**Checkpoint**: portal auditado e corrigido — MVP entregável

---

## Phase 4: User Story 2 - Feedback claro de validação no cadastro (Priority: P2)

**Goal**: validação própria no `/cadastro` conforme [contracts/ui-contract.md](./contracts/ui-contract.md):
novalidate + destaque (borda + shake) + mensagem por campo/grupo + scroll/foco no primeiro +
limpeza ao corrigir; sem `alert`, sem perda de dados.

**Independent Test**: roteiro US2 do [quickstart.md](./quickstart.md).

### Implementation for User Story 2

- [X] T010 [US2] CSS em `app/templates/cadastro/form.html`: classes `.field-invalid` (borda `var(--danger)` nos inputs/grupo + animação `@keyframes shake` ~400ms) e `.field-errmsg` (12.5px, `var(--danger)`, margin-top 4px)
- [X] T011 [US2] JS em `app/templates/cadastro/form.html`: `novalidate` no form; no submit coletar campos `:invalid` habilitados/visíveis + grupos `[data-required-group]` vazios; marcar todos (classe no container `.field` + mensagem conforme tabela do contrato); `preventDefault` + scroll `center` + `focus({preventScroll:true})` no primeiro; remover `alert()`; travar botão só quando válido; listener `input`/`change` limpa o erro do campo corrigido
- [X] T012 [US2] Casos condicionais: garantir que CPF desabilitado (estrangeiro) e `gender_other` oculto não entram na validação nem recebem scroll (usar checagem `disabled`/`offsetParent`); arquivos obrigatórios recebem "Anexe o arquivo."
- [X] T013 [US2] Verificação do roteiro US2 do [quickstart.md](./quickstart.md): test client (form contém `novalidate`, classes novas, zero `alert(` no script) + visual: enviar incompleto em 390px, corrigir, grupos, estrangeiro, e cadastro completo de ponta a ponta contra `manto_local`

**Checkpoint**: as 2 stories completas

---

## Phase 5: Polish & Cross-Cutting Concerns

- [X] T014 Passada final: nenhuma cor hardcoded NOVA nos trechos tocados; textos pt-BR; `ruff check app/` (sanidade); re-execução rápida do quickstart completo
- [X] T015 Commits atômicos por story + merge da branch `106-portal-mobile-cadastro-feedback` em `main` + push (stage explícito)

---

## Dependencies & Execution Order

- **US1 (Phase 3)**: T002–T007 são [P] entre si onde marcado (arquivos distintos); T004 depende de T002 (mesmo arquivo home.html); T008 depois dos anteriores; T009 fecha a story
- **US2 (Phase 4)**: independente de US1 (arquivos distintos); T010 → T011 → T012 (mesmo arquivo, sequencial)
- **Polish (Phase 5)**: depende de tudo

### Parallel Opportunities

- T002/T003/T005/T006/T007 tocam arquivos diferentes — paralelizáveis
- US2 inteira pode andar em paralelo com US1 (form.html × portal/*)

## Implementation Strategy

Sequencial por prioridade (agente único): US1 (auditoria aplicada + verificação) → US2
(validação do cadastro) → Polish. Um commit por story; verificação test client + visual a
cada checkpoint.
