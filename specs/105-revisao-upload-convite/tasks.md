# Tasks: Revisão — Progresso de Upload, Convite aos Revisores e Fix do Popup

**Input**: Design documents from `/specs/105-revisao-upload-convite/`

**Prerequisites**: plan.md, spec.md, research.md, contracts/routes.md, quickstart.md

**Tests**: não solicitados — verificação via roteiro do [quickstart.md](./quickstart.md)
(script com test client contra `manto_local` + conferência visual). Sem migration.

**Organization**: por user story; US1 (fix do popup) é o MVP mínimo.

## Format: `[ID] [P?] [Story] Description`

## Path Conventions

Monolito Flask: rotas em `app/revisao/routes.py`, JS estático em `app/static/`,
templates em `app/templates/revisao/`.

---

## Phase 1: Setup

- [X] T001 Confirmar app rodando contra a cópia local (`.\scripts\db\run-local.ps1` / `DATABASE_URL` de `.local-db-url`) — sem migration nesta feature

---

## Phase 2: Foundational (Blocking Prerequisites)

*(vazio — não há pré-requisito compartilhado; o helper JS é específico da US2)*

---

## Phase 3: User Story 1 - Popup de histórico não bloqueia mais a tela (Priority: P1) 🎯 MVP

**Goal**: tela do material carrega sem popup sobreposto; histórico abre pelo badge e fecha
pelo ✕/clique fora.

**Independent Test**: roteiro US1 do [quickstart.md](./quickstart.md).

### Implementation for User Story 1

- [X] T002 [US1] Corrigir o CSS do modal em `app/templates/revisao/asset.html`: adicionar regra `.rv-modal[hidden] { display: none; }` junto às regras `.rv-modal` (causa raiz: `display:flex` da classe vence o `[hidden]` do user-agent — ver R1 do [research.md](./research.md))
- [X] T003 [US1] Verificar no app real (manto_local): página carrega sem popup; abre/fecha pelo badge, ✕ e clique fora, 3× consecutivas (roteiro US1 do quickstart)

**Checkpoint**: tela do material utilizável novamente — MVP do fix

---

## Phase 4: User Story 2 - Progresso real do upload na criação do espaço (Priority: P2)

**Goal**: barra de progresso real (% + MB) nos envios com arquivo (criar espaço, nova versão,
adicionar materiais); formulário bloqueado durante envio; erro amigável sem perder dados;
fluxo tradicional preservado sem JS/sem arquivos.

**Independent Test**: roteiro US2 do [quickstart.md](./quickstart.md) (upload grande, falha de
rede, envio sem arquivos).

### Implementation for User Story 2

- [X] T004 [P] [US2] Criar helper `app/static/upload_progress.js` — `uploadFormWithProgress(form, opts)` conforme contrato ([contracts/routes.md](./contracts/routes.md)): intercepta submit apenas quando há arquivo selecionado; XHR + FormData + header `X-Requested-With: XMLHttpRequest`; `upload.onprogress` atualiza barra (% via width) e label "N% — X MB de Y MB" (MB com 1 casa); desabilita `submitBtn` e campos durante envio; sucesso → `window.location = json.redirect`; HTTP 400 → exibe `json.error` em `errorEl` e reabilita form; erro de rede → mensagem amigável e reabilita form (dados intactos)
- [X] T005 [P] [US2] Em `app/revisao/routes.py`: helper `_wants_json() -> bool` (header `X-Requested-With`); `new_space` responde `200 {"redirect": url}` no sucesso XHR e `400 {"error": ...}` na validação XHR (fluxo tradicional intacto); `replace_asset` e `upload_assets` idem (erros de validação do replace viram 400 JSON no modo XHR) — conforme [contracts/routes.md](./contracts/routes.md)
- [X] T006 [US2] Em `app/templates/revisao/new.html`: incluir o helper (`<script src="/static/upload_progress.js">`), adicionar o bloco da barra de progresso (container + label + área de erro, tokens `--accent`/`--line`/`--r-md`, oculto por padrão) e ligar `uploadFormWithProgress` ao form `#new-space-form` (substituindo o handler atual de submit)
- [X] T007 [US2] Em `app/templates/revisao/asset.html` e `app/templates/revisao/space.html`: aplicar o mesmo helper + barra aos forms de "Enviar nova versão" (asset) e "Adicionar materiais" (space)
- [X] T008 [US2] Verificação: script de test client (JSON mode das 3 rotas: redirect no sucesso, 400 com erro na validação, 302 tradicional sem header) + visual no app real com arquivo grande e Network offline (roteiro US2 do quickstart)

**Checkpoint**: uploads com progresso real e sem regressão no fluxo tradicional

---

## Phase 5: User Story 3 - Copiar convite para os revisores (Priority: P3)

**Goal**: botão "Copiar convite" na tela do espaço (mensagem pronta com título + link
absoluto), com confirmação visual e fallback manual; destaque pós-criação.

**Independent Test**: roteiro US3 do [quickstart.md](./quickstart.md).

### Implementation for User Story 3

- [X] T009 [US3] Em `app/revisao/routes.py`: `new_space` redireciona para a tela do espaço com `?novo=1` no sucesso (ambos os fluxos); `space_detail` passa `just_created` e `invite_text` (mensagem pt-BR com título + `url_for('revisao.space_detail', space_id=..., _external=True)` — texto conforme R4 do [research.md](./research.md)) ao template
- [X] T010 [US3] Em `app/templates/revisao/space.html`: botão "🔗 Copiar convite" nas page actions (todos com acesso); painel de destaque quando `just_created` ("Espaço criado! Envie o convite…"); JS de cópia — `navigator.clipboard.writeText` com fallback `<textarea>` readonly selecionada; botão vira "✓ Copiado!" por ~2,5s
- [X] T011 [US3] Verificação: copiar/colar com título com acento+emoji, destaque só com `?novo=1`, link funciona logado e dá 403 sem acesso (roteiro US3 do quickstart)

**Checkpoint**: as 3 stories completas

---

## Phase 6: Polish & Cross-Cutting Concerns

- [X] T012 Portões: `ruff check app/revisao/`; docstrings/type hints nas funções tocadas; nenhuma cor hardcoded nova nos templates; textos pt-BR
- [X] T013 Re-execução rápida do quickstart completo (US1+US2+US3) contra `manto_local`
- [X] T014 Commits atômicos por story + merge da branch `105-revisao-upload-convite` em `main` + push (stage explícito)

---

## Dependencies & Execution Order

- **Setup (Phase 1)** → nada bloqueia além dele
- **US1 (Phase 3)**: independente — 1 linha de CSS + verificação
- **US2 (Phase 4)**: T004 e T005 são [P] entre si (JS novo × rotas); T006–T007 dependem dos dois
- **US3 (Phase 5)**: independente de US2 (arquivos distintos exceto `routes.py`/`space.html` — executar após US2 para evitar conflito de edição)
- **Polish (Phase 6)**: depende de tudo

### Parallel Opportunities

- T004 (upload_progress.js) ∥ T005 (routes.py) — arquivos diferentes
- US1 inteira pode rodar em paralelo com US2/US3 (arquivos distintos: só CSS do asset.html; T007 também toca asset.html — sequenciar T002 antes de T007)

## Implementation Strategy

Sequencial por prioridade (agente único): US1 (fix, deploy-ável sozinho) → US2 → US3 →
Polish. Verificação com test client + visual a cada checkpoint; um commit por story.
