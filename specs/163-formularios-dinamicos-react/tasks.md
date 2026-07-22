# Tasks: Formulários Dinâmicos Públicos em React (163)

**Input**: Design documents from `specs/163-formularios-dinamicos-react/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md,
contracts/formularios-endpoints.md, quickstart.md

**Tests**: verificação é o script de paridade
`scripts/db/verify_163_formularios_dinamicos_react.py` contra `manto_local`, gerado na Phase de
Polish.

**Organização**: 2 user stories (US1 preencher/enviar, US2 autopreenchimento por CEP), nessa
ordem de prioridade.

## Phase 1: Setup

- [ ] T001 [P] Adicionar rotas `/f/pre-contrato`, `/f/corporativo` e `/f/:formType/enviado`
      (placeholders) em `frontend/apps/public/src/App.tsx`, substituídos nas fases seguintes.

## Phase 2: Foundational

- [ ] T002 Criar `app/api/formularios_write.py` (NOVO): importa (não copia) `FORM_META`,
      `_load_fields`, `_grouped_sections`, `_validate_dynamic`, `_build_sections_dynamic`,
      `_save_response`, `_attempt_auto_link`, `_build_message`, `_whatsapp_link`,
      `_build_phone_display`, `_parse_event_date` de `app/formularios/routes.py`
      (`research.md` §2). Type hints e docstring (Google style).
- [ ] T003 Importar `formularios_write` em `app/api/__init__.py` (mesmo padrão dos demais
      módulos `_write`).
- [ ] T004 [P] Criar `frontend/apps/public/src/lib/formularios.ts`: tipos
      (`FieldSchema`, `SectionSchema`, `FormSchema`) + hooks `useFormSchema(formType)`
      (`useQuery`) e `useSubmitForm(formType)` (`useMutation`, monta `FormData`) + funções de
      máscara (`maskCpf`, `maskCnpj`, `maskCep`, `maskPhone` — mesma lógica de
      `_form_scripts.html`) + `fetchCep(cep)` (ViaCEP, `research.md` §4).

**Checkpoint**: núcleo compartilhado pronto (backend importa o motor dinâmico, frontend tem
tipos/hooks/máscaras) — as user stories podem começar.

---

## Phase 3: User Story 1 — Visitante preenche e envia um formulário de pré-contrato (P1) 🎯 MVP

**Goal**: visitante preenche qualquer um dos dois formulários (campos vindos 100% do schema) e
envia — resposta salva, WhatsApp abre com a mensagem pronta.

**Independent Test**: abrir `/f/pre-contrato`, preencher todos os obrigatórios vigentes e enviar
— ver a confirmação com o link de WhatsApp; enviar com um campo obrigatório vazio e ver o erro
específico junto ao campo, sem perder o restante preenchido.

### Implementation for User Story 1

- [ ] T005 [US1] Criar `app/api/formularios_write.py` — `GET /api/formularios/<form_type>/schema`
      (404 se `form_type` inválido; 200 com `title`/`header`/`sections`, conforme
      `data-model.md`) e `POST /api/formularios/<form_type>` (`@limiter.limit("10 per hour")`;
      honeypot → `201 {"wa_link": null, "contact_name": null}` sem salvar; validação via
      `_validate_dynamic` → `400` com todos os erros em `fields` e mensagem genérica do banner;
      sucesso → `_save_response` + `_attempt_auto_link` (best-effort, nunca derruba o 201) +
      `_build_message`/`_whatsapp_link` → `201 {"wa_link", "contact_name"}`), conforme
      `contracts/formularios-endpoints.md`.
- [ ] T006 [US1] Criar `frontend/apps/public/src/components/formularios/DynamicField.tsx`:
      despacha o widget por `field.type` (`research.md` §3) — `texto_curto`/`email` → `Input`;
      `texto_longo` → `textarea`; `selecao` → `select` nativo; `telefone` → select de DDI +
      input mascarado (`maskPhone`); `data`/`hora` → `input[type=date|time]`;
      `cpf`/`cnpj`/`cep` → input mascarado; `sim_nao` → checkbox (valor `"Sim"`/vazio); exibe
      `help_text`, `required` (`*`) e mensagem de erro do campo.
- [ ] T007 [US1] Criar `frontend/apps/public/src/components/formularios/DynamicForm.tsx`: busca
      o schema (`useFormSchema`, T004), mantém `values`/`errors` em estado, renderiza seções +
      `DynamicField` (T006) por campo, honeypot oculto (`website`), botão de envio com estado
      "Enviando..." (`useSubmitForm`, T004); em sucesso navega para `/f/{formType}/enviado`
      passando `wa_link`/`contact_name` (query param ou state de navegação); em erro 400,
      popula `errors` por `field_key` (usa o campo de erro cru — sem apagar `values`) e rola até
      o primeiro campo inválido.
- [ ] T008 [P] [US1] Criar `frontend/apps/public/src/pages/FormularioPage.tsx`: lê `formType`
      da rota (`comum` para `/f/pre-contrato`, `corporativo` para `/f/corporativo`), monta
      `DynamicForm` (T007) num layout mobile-first.
- [ ] T009 [P] [US1] Criar `frontend/apps/public/src/pages/FormularioEnviadoPage.tsx`: paridade
      com `enviado.html` — botão "Enviar mensagem no WhatsApp" (abre `wa_link`), tentativa de
      abertura automática após ~1.2s, mensagem alternativa quando `wa_link` é `null`
      (honeypot/sem WhatsApp).
- [ ] T010 [US1] Em `App.tsx` (T001), substituir os placeholders de `/f/pre-contrato`,
      `/f/corporativo` e `/f/:formType/enviado` pelas páginas reais (T008, T009).

**Checkpoint**: US1 completa e testável isoladamente — os 2 formulários funcionam ponta a ponta
com qualquer estrutura de campo vigente.

---

## Phase 4: User Story 2 — Endereço preenchido automaticamente por CEP (P2)

**Goal**: campo de CEP preenche logradouro/bairro/cidade/estado automaticamente.

**Independent Test**: digitar um CEP válido e ver os campos de endereço se preencherem sozinhos,
sem sobrescrever o que já tiver sido digitado manualmente; CEP inválido não trava o formulário.

### Implementation for User Story 2

- [ ] T011 [US2] Em `DynamicForm.tsx` (T007), no `onBlur` de qualquer campo `type === "cep"` com
      8 dígitos, chamar `fetchCep` (T004) e, se a resposta não tiver erro, preencher
      `logradouro`/`bairro`/`cidade`/`estado` em `values` **somente** para chaves que existirem
      no schema atual e ainda estiverem vazias (`research.md` §4); falha da consulta não
      bloqueia nem exibe erro (silenciosa).

**Checkpoint**: as 2 user stories completas — formulários dinâmicos 100% em React, com
autopreenchimento de CEP.

---

## Phase 5: Polish & Verificação

- [ ] T012 Criar `scripts/db/verify_163_formularios_dinamicos_react.py` (gitignored): test client
      Flask contra `manto_local`, requests fora de `app_context` — cobre `GET .../schema` para
      os 2 `form_type` (+ 404 para inválido), submissão válida com paridade de campos salvos
      (`FormResponse.data`) vs. o caminho Jinja para os mesmos dados, múltiplos campos
      inválidos simultâneos, "Descreva outros" obrigatório condicional (forma de pagamento
      "Outros"), honeypot (sem criar resposta).
- [ ] T013 Rodar `ruff check app/api/formularios_write.py`.
- [ ] T014 Rodar `npm run typecheck:public` e `npm run build:public`.
- [ ] T015 Conferência mobile (320–430px) das 2 telas de formulário e da tela de confirmação —
      Princípio VIII.
- [ ] T016 Atualizar `docs/changelog.html` com entrada em linguagem simples (entrada 163) e
      republicar no artifact já existente (mesmo link).

## Dependencies

Setup (Phase 1) → Foundational (Phase 2) → US1 (Phase 3) → US2 (Phase 4) → Polish (Phase 5).

US2 depende de US1 (adiciona ao mesmo `DynamicForm` criado na Phase 3) — não é paralelizável
com US1, mesmo padrão de dependência sequencial já visto nas fatias anteriores da US5.

## Implementation Strategy

MVP = US1 (preencher/enviar os 2 formulários — sozinha já entrega o valor central: substituir o
WhatsForm por um canal que salva a resposta e abre o WhatsApp). US2 (CEP) incrementa conveniência
sobre a mesma base sem mudar arquitetura. Com esta fatia completa, falta só o feedback público
por token para fechar a US5 por completo.
