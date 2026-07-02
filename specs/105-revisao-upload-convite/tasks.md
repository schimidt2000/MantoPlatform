# Tasks: RevisÃ£o â€” Progresso de Upload, Convite aos Revisores e Fix do Popup

**Input**: Design documents from `/specs/105-revisao-upload-convite/`

**Prerequisites**: plan.md, spec.md, research.md, contracts/routes.md, quickstart.md

**Tests**: nÃ£o solicitados â€” verificaÃ§Ã£o via roteiro do [quickstart.md](./quickstart.md)
(script com test client contra `manto_local` + conferÃªncia visual). Sem migration.

**Organization**: por user story; US1 (fix do popup) Ã© o MVP mÃ­nimo.

## Format: `[ID] [P?] [Story] Description`

## Path Conventions

Monolito Flask: rotas em `app/revisao/routes.py`, JS estÃ¡tico em `app/static/`,
templates em `app/templates/revisao/`.

---

## Phase 1: Setup

- [X] T001 Confirmar app rodando contra a cÃ³pia local (`.\scripts\db\run-local.ps1` / `DATABASE_URL` de `.local-db-url`) â€” sem migration nesta feature

---

## Phase 2: Foundational (Blocking Prerequisites)

*(vazio â€” nÃ£o hÃ¡ prÃ©-requisito compartilhado; o helper JS Ã© especÃ­fico da US2)*

---

## Phase 3: User Story 1 - Popup de histÃ³rico nÃ£o bloqueia mais a tela (Priority: P1) ðŸŽ¯ MVP

**Goal**: tela do material carrega sem popup sobreposto; histÃ³rico abre pelo badge e fecha
pelo âœ•/clique fora.

**Independent Test**: roteiro US1 do [quickstart.md](./quickstart.md).

### Implementation for User Story 1

- [X] T002 [US1] Corrigir o CSS do modal em `app/templates/revisao/asset.html`: adicionar regra `.rv-modal[hidden] { display: none; }` junto Ã s regras `.rv-modal` (causa raiz: `display:flex` da classe vence o `[hidden]` do user-agent â€” ver R1 do [research.md](./research.md))
- [X] T003 [US1] Verificar no app real (manto_local): pÃ¡gina carrega sem popup; abre/fecha pelo badge, âœ• e clique fora, 3Ã— consecutivas (roteiro US1 do quickstart)

**Checkpoint**: tela do material utilizÃ¡vel novamente â€” MVP do fix

---

## Phase 4: User Story 2 - Progresso real do upload na criaÃ§Ã£o do espaÃ§o (Priority: P2)

**Goal**: barra de progresso real (% + MB) nos envios com arquivo (criar espaÃ§o, nova versÃ£o,
adicionar materiais); formulÃ¡rio bloqueado durante envio; erro amigÃ¡vel sem perder dados;
fluxo tradicional preservado sem JS/sem arquivos.

**Independent Test**: roteiro US2 do [quickstart.md](./quickstart.md) (upload grande, falha de
rede, envio sem arquivos).

### Implementation for User Story 2

- [X] T004 [P] [US2] Criar helper `app/static/upload_progress.js` â€” `uploadFormWithProgress(form, opts)` conforme contrato ([contracts/routes.md](./contracts/routes.md)): intercepta submit apenas quando hÃ¡ arquivo selecionado; XHR + FormData + header `X-Requested-With: XMLHttpRequest`; `upload.onprogress` atualiza barra (% via width) e label "N% â€” X MB de Y MB" (MB com 1 casa); desabilita `submitBtn` e campos (fieldset/disabled) durante envio; sucesso â†’ `window.location = json.redirect`; HTTP 400 â†’ exibe `json.error` em `errorEl` e reabilita form; erro de rede â†’ mensagem amigÃ¡vel e reabilita form (dados intactos)
- [X] T005 [P] [US2] Em `app/revisao/routes.py`: helper `_wants_json() -> bool` (header `X-Requested-With`); `new_space` responde `200 {"redirect": url}` no sucesso XHR e `400 {"error": ...}` na validaÃ§Ã£o XHR (fluxo tradicional intacto); `replace_asset` e `upload_assets` idem (erros de validaÃ§Ã£o do replace viram 400 JSON no modo XHR) â€” conforme [contracts/routes.md](./contracts/routes.md)
- [X] T006 [US2] Em `app/templates/revisao/new.html`: incluir o helper (`<script src="/static/upload_progress.js">`), adicionar o bloco da barra de progresso (container + label + Ã¡rea de erro, tokens `--accent`/`--line`/`--r-md`, oculto por padrÃ£o) e ligar `uploadFormWithProgress` ao form `#new-space-form` (substituindo o handler atual de submit)
- [X] T007 [US2] Em `app/templates/revisao/asset.html` e `app/templates/revisao/space.html`: aplicar o mesmo helper + barra aos forms de "Enviar nova versÃ£o" (asset) e "Adicionar materiais" (space)
- [X] T008 [US2] VerificaÃ§Ã£o: script de test client (JSON mode das 3 rotas: redirect no sucesso, 400 com erro na validaÃ§Ã£o, 302 tradicional sem header) + visual no app real com arquivo grande e Network offline (roteiro US2 do quickstart)

**Checkpoint**: uploads com progresso real e sem regressÃ£o no fluxo tradicional

---

## Phase 5: User Story 3 - Copiar convite para os revisores (Priority: P3)

**Goal**: botÃ£o "Copiar convite" na tela do espaÃ§o (mensagem pronta com tÃ­tulo + link
absoluto), com confirmaÃ§Ã£o visual e fallback manual; destaque pÃ³s-criaÃ§Ã£o.

**Independent Test**: roteiro US3 do [quickstart.md](./quickstart.md).

### Implementation for User Story 3

- [X] T009 [US3] Em `app/revisao/routes.py`: `new_space` redireciona para a tela do espaÃ§o com `?novo=1` no sucesso (ambos os fluxos); `space_detail` passa `just_created` e `invite_text` (mensagem pt-BR com tÃ­tulo + `url_for('revisao.space_detail', space_id=..., _external=True)` â€” texto conforme R4 do [research.md](./research.md)) ao template
- [X] T010 [US3] Em `app/templates/revisao/space.html`: botÃ£o "ðŸ”— Copiar convite" nas page actions (todos com acesso); painel de destaque quando `just_created` ("EspaÃ§o criado! Envie o conviteâ€¦"); JS de cÃ³pia â€” `navigator.clipboard.writeText` com fallback `<textarea>` readonly selecionada; botÃ£o vira "âœ“ Copiado!" por ~2,5s
- [X] T011 [US3] VerificaÃ§Ã£o: copiar/colar com tÃ­tulo com acento+emoji, destaque sÃ³ com `?novo=1`, link funciona logado e dÃ¡ 403 sem acesso (roteiro US3 do quickstart)

**Checkpoint**: as 3 stories completas

---

## Phase 6: Polish & Cross-Cutting Concerns

- [X] T012 PortÃµes: `ruff check app/revisao/`; docstrings/type hints nas funÃ§Ãµes tocadas; nenhuma cor hardcoded nova nos templates; textos pt-BR
- [X] T013 Re-execuÃ§Ã£o rÃ¡pida do quickstart completo (US1+US2+US3) contra `manto_local`
- [X] T014 Commits atÃ´micos por story + merge da branch `105-revisao-upload-convite` em `main` + push (stage explÃ­cito)

---

## Dependencies & Execution Order

- **Setup (Phase 1)** â†’ nada bloqueia alÃ©m dele
- **US1 (Phase 3)**: independente â€” 1 linha de CSS + verificaÃ§Ã£o
- **US2 (Phase 4)**: T004 e T005 sÃ£o [P] entre si (JS novo Ã— rotas); T006â€“T007 dependem dos dois
- **US3 (Phase 5)**: independente de US2 (arquivos distintos exceto `routes.py`/`space.html` â€” executar apÃ³s US2 para evitar conflito de ediÃ§Ã£o)
- **Polish (Phase 6)**: depende de tudo

### Parallel Opportunities

- T004 (upload_progress.js) âˆ¥ T005 (routes.py) â€” arquivos diferentes
- US1 inteira pode rodar em paralelo com US2/US3 (arquivos distintos: sÃ³ CSS do asset.html; T007 tambÃ©m toca asset.html â€” sequenciar T002 antes de T007)

## Implementation Strategy

Sequencial por prioridade (agente Ãºnico): US1 (fix, deploy-Ã¡vel sozinho) â†’ US2 â†’ US3 â†’
Polish. VerificaÃ§Ã£o com test client + visual a cada checkpoint; um commit por story.
