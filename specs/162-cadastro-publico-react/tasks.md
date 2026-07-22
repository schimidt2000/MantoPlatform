# Tasks: Cadastro Público de Talentos em React (162)

**Input**: Design documents from `specs/162-cadastro-publico-react/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md,
contracts/cadastro-endpoints.md, quickstart.md

**Tests**: verificação é o script de paridade
`scripts/db/verify_162_cadastro_publico_react.py` contra `manto_local`, gerado na Phase de
Polish.

**Organização**: 3 user stories (US1 enviar o cadastro, US2 aviso de CPF duplicado em tempo
real, US3 proteção anti-abuso), nessa ordem de prioridade.

## Phase 1: Setup

- [X] T001 Adicionar `react-hook-form` e `zod` (mesmas versões de `apps/internal/package.json`)
      às `dependencies` de `frontend/apps/public/package.json`.
- [X] T002 [P] Adicionar rotas `/cadastro` e `/cadastro/enviado` (placeholders) em
      `frontend/apps/public/src/App.tsx`, substituídos nas fases seguintes.

## Phase 2: Foundational

- [X] T003 Criar `app/cadastro/cadastro_ops.py` (NOVO — `research.md` §4): mover
      `_build_phone`, `_height_to_cm`, `_validate_upload`, `_yes_no` (e as constantes
      `_PHOTO_EXTS`/`_DOC_EXTS`/`_PHOTO_MAX`/`_DOC_MAX`) de `app/cadastro/routes.py` para cá,
      sem alterar comportamento; type hints e docstrings já existentes preservados.
- [X] T004 Atualizar `app/cadastro/routes.py` para importar essas funções/constantes de
      `cadastro_ops.py` (mesmo comportamento do handler Jinja, zero duplicação).
- [X] T005 [P] Criar `frontend/packages/ui/src/components/file-upload.tsx` (`research.md` §3):
      componente `FileUpload` — input de arquivo estilizado (`Button` + input escondido),
      preview de thumbnail quando `image/*`, mensagem de erro (borda vermelha), texto de tipos/
      tamanho aceitos; props `accept`, `maxSizeBytes`, `label`, `required?`, `error?`,
      `onChange(file: File | null)`.
- [X] T006 [P] Exportar `FileUpload` em `frontend/packages/ui/src/index.ts`.

**Checkpoint**: núcleo compartilhado pronto (backend `cadastro_ops.py`, frontend `FileUpload`) —
as user stories podem começar.

---

## Phase 3: User Story 1 — Candidato preenche e envia o cadastro (Priority: P1) 🎯 MVP

**Goal**: visitante anônimo preenche o formulário completo, anexa os 3 arquivos obrigatórios e
envia — talento pendente é criado e a confirmação é exibida.

**Independent Test**: enviar o formulário com todos os campos/arquivos obrigatórios válidos e ver
a tela de confirmação; enviar com um campo/arquivo faltando ou inválido e ver o erro específico
sem perder o preenchimento.

### Implementation for User Story 1

- [X] T007 [US1] Criar `app/api/cadastro_write.py` (NOVO): `POST /api/cadastro` — lê
      `request.form`/`request.files`, reaproveita `cadastro_ops` (T003) e
      `app/talents/importer.py` (`parse_date`, `normalize_tags`, `only_digits`,
      `_parse_passport_status`) para validar e montar o `Talent` exatamente como
      `app/cadastro/routes.py:submit` (mesma ordem de validação e mesmas mensagens, ver
      `data-model.md` e `contracts/cadastro-endpoints.md`); grava uploads via
      `app.storage.save_file`; responde `201 {"id": talent.id}` ou `400 {"error": {...}}`.
      Type hints e docstring (Google style).
- [X] T008 [US1] Importar `cadastro_write` em `app/api/__init__.py` (mesmo padrão dos demais
      módulos `_write`).
- [X] T009 [P] [US1] Criar `frontend/apps/public/src/lib/cadastro.ts`: schema `zod` espelhando
      as validações obrigatórias do backend (`contracts/cadastro-endpoints.md`) + hook
      `useSubmitCadastro()` (`useMutation`, `@tanstack/react-query`) que monta `FormData` (campos
      de texto + `languages`/`skills` repetidos + 4 arquivos) e chama `apiFetch("/cadastro",
      {method: "POST", body: formData})` (`@manto/api-client`).
- [X] T010 [US1] Criar `frontend/apps/public/src/components/cadastro/CadastroForm.tsx`:
      `react-hook-form` + resolver `zod` (T009); seções (dados pessoais, contato, medidas, PIX,
      veículo/CNH, uploads com `FileUpload` de T005 para rosto/corpo/documento/CNH); campo
      "Outro" de gênero revela input de texto livre; honeypot (`website`) como campo oculto
      (`aria-hidden`, fora do fluxo de tab); erro de campo focado + destacado (Princípio V);
      botão de envio com estado "Enviando..." (disabled) via `isPending` da mutation (T009); em
      sucesso, navega para `/cadastro/enviado`; em erro 400, mostra a mensagem da API num
      alerta/toast sem apagar os campos preenchidos.
- [X] T011 [P] [US1] Criar `frontend/apps/public/src/pages/CadastroPage.tsx`: monta
      `CadastroForm` (T010) num layout mobile-first (coluna única em 320–430px).
- [X] T012 [P] [US1] Criar `frontend/apps/public/src/pages/CadastroSucessoPage.tsx`: tela de
      confirmação (mensagem de recebido + link para o catálogo), paridade com
      `app/templates/cadastro/success.html`.
- [X] T013 [US1] Em `App.tsx` (T002), substituir os placeholders de `/cadastro` e
      `/cadastro/enviado` pelas páginas reais (T011, T012).

**Checkpoint**: US1 completa e testável isoladamente — envio ponta a ponta cria talento pendente.

---

## Phase 4: User Story 2 — Aviso de CPF já cadastrado antes de enviar tudo (Priority: P2)

**Goal**: enquanto digita o CPF, o candidato vê um aviso em tempo real se ele já existe.

**Independent Test**: digitar um CPF já cadastrado e ver o aviso aparecer sem submeter o
formulário; digitar um CPF novo/incompleto e não ver aviso nenhum.

### Implementation for User Story 2

- [X] T014 [US2] Em `app/api/cadastro_write.py` (T007), adicionar `GET /api/cadastro/check-cpf`
      — mesma lógica de `app/cadastro/routes.py:check_cpf` (extrai dígitos, responde
      `{"exists", "valid"}`), `@limiter.limit("60 per hour")` (mesmo limite do Jinja).
- [X] T015 [P] [US2] Em `frontend/apps/public/src/lib/cadastro.ts` (T009), adicionar
      `useCheckCpf(cpf: string)` (`useQuery`, debounced/`enabled` só com 11 dígitos) chamando
      `GET /cadastro/check-cpf?cpf=...`.
- [X] T016 [US2] Criar `frontend/apps/public/src/components/cadastro/CpfField.tsx`: campo de CPF
      com máscara de dígitos, usa `useCheckCpf` (T015) — mostra aviso "CPF já cadastrado" abaixo
      do campo quando `exists=true`, sem bloquear a digitação; oculto quando `is_foreigner`
      estiver marcado (paridade com a regra de CPF opcional para estrangeiro).
- [X] T017 [US2] Em `CadastroForm.tsx` (T010), substituir o input de CPF genérico por
      `CpfField` (T016).

**Checkpoint**: US1 + US2 funcionam juntas — aviso de duplicidade em tempo real, sem impedir o
fluxo de envio (a validação final do POST continua sendo a garantia real).

---

## Phase 5: User Story 3 — Proteção contra automações e abuso (Priority: P3)

**Goal**: honeypot e rate limit sobrevivem à migração, sem fricção para o candidato humano.

**Independent Test**: uma submissão com o campo oculto preenchido não cria talento e recebe a
mesma resposta de sucesso; excesso de tentativas de envio/checagem de CPF é recusado
temporariamente.

### Implementation for User Story 3

- [X] T018 [US3] Em `app/api/cadastro_write.py` (T007), adicionar a checagem de honeypot no
      início de `POST /api/cadastro` (mesma regra do Jinja: se `website` vier preenchido,
      responde `201 {"id": null}` sem criar talento nem validar o restante).
- [X] T019 [US3] Adicionar `@limiter.limit("10 per hour")` em `POST /api/cadastro` (mesmo
      limite do Jinja).

**Checkpoint**: as 3 user stories completas — cadastro público 100% em React, com paridade de
proteção anti-abuso.

---

## Phase 6: Polish & Verificação

- [X] T020 Criar `scripts/db/verify_162_cadastro_publico_react.py` (gitignored): test client
      Flask contra `manto_local`, requests fora de `app_context` — cobre envio válido (paridade
      de campos do `Talent` resultante vs. o caminho Jinja para os mesmos dados/arquivos), erro
      por campo obrigatório faltante, erro por upload inválido (tipo/tamanho), CPF duplicado no
      POST final, estrangeiro sem CPF, honeypot preenchido (sem criar talento), `check-cpf` para
      CPF existente/inexistente/incompleto.
- [X] T021 Rodar `ruff check app/api/cadastro_write.py app/cadastro/cadastro_ops.py
      app/cadastro/routes.py`.
- [X] T022 Rodar `npm run typecheck:public` e `npm run build:public`.
- [X] T023 Conferência mobile (320–430px) da tela de cadastro (todas as seções, os 4 campos de
      upload com alvo de toque ≥44px, teclado virtual não esconde campo ativo/botão de envio) e
      da tela de confirmação — Princípio VIII. **Não verificado visualmente nesta sessão**: sem
      Playwright/chromium-cli disponível no ambiente (mesma limitação recorrente das fatias
      156-161). O layout foi construído mobile-first desde o início (`Section`/`Card` em coluna
      única, `grid-cols-1 sm:grid-cols-2` só expande a partir do breakpoint `sm`, botões/inputs
      já em `h-11`/`h-12` ≥44px, `FileUpload` e `CpfField` seguem o mesmo padrão de largura
      total); recomenda-se conferência visual manual em viewport real antes do próximo passo da
      US5.
- [X] T024 Atualizar `docs/changelog.html` com entrada em linguagem simples (entrada 162) e
      republicar no artifact já existente (mesmo link).

## Dependencies

Setup (Phase 1) → Foundational (Phase 2) → US1 (Phase 3) → US2 (Phase 4) → US3 (Phase 5) →
Polish (Phase 6).

US2 e US3 dependem de US1 (adicionam ao mesmo endpoint/formulário criados na Phase 3) — não são
paralelizáveis com US1, mesmo padrão de dependência sequencial já visto na 161 (US2 dependia de
US1). Dentro de cada phase: tarefas `[P]` tocam arquivos distintos e podem rodar em paralelo.

## Implementation Strategy

MVP = US1 (enviar o cadastro — sozinha já entrega o valor central: candidato cadastrado). US2
(aviso de CPF) e US3 (honeypot/rate limit) incrementam proteção/UX sobre a mesma base sem mudar
arquitetura. Com esta fatia completa, falta migrar formulários dinâmicos (`/f/pre-contrato`,
`/f/corporativo`) e feedback público por token para fechar a US5.
