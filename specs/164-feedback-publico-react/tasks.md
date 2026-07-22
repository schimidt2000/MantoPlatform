# Tasks: Feedback Público por Token em React (164)

**Input**: Design documents from `specs/164-feedback-publico-react/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md,
contracts/feedback-endpoints.md, quickstart.md

**Tests**: verificação é o script de paridade
`scripts/db/verify_164_feedback_publico_react.py` contra `manto_local`, gerado na Phase de
Polish.

**Organização**: 1 user story (US1 avaliar e enviar) — é o fluxo inteiro, sem outra fatia
independente a distinguir (o estado de "link inválido" e "agradecimento" são partes do mesmo
fluxo único, não user stories separadas).

## Phase 1: Setup

- [ ] T001 [P] Adicionar rota `/avaliar/:token` (placeholder) em
      `frontend/apps/public/src/App.tsx`, substituído na fase seguinte.

## Phase 2: User Story 1 — Cliente avalia a experiência através do link recebido (P1) 🎯 MVP

**Goal**: cliente abre o link, avalia de 1 a 5 estrelas, marca etiquetas da categoria certa,
comenta (opcional) e envia — feedback salvo, tela de agradecimento exibida; token inválido
mostra a tela de link inválido.

**Independent Test**: abrir `/avaliar/<token-válido>`, escolher uma nota, ver as etiquetas da
categoria certa, enviar com nome preenchido — ver a tela de agradecimento; abrir
`/avaliar/<token-inválido>` — ver a tela de link inválido; tentar enviar sem nome — ver o erro
sem perder a nota escolhida.

### Implementation for User Story 1

- [ ] T002 [US1] Criar `app/api/feedback_write.py` (NOVO): importa `POSITIVE_TAGS`,
      `ATTENTION_TAGS`, `_tags_for_score` de `app/feedback/routes.py` (`research.md` §1).
      `GET /api/avaliar/<token>` — 404 se token não corresponder a evento; 200 com
      `event_title`/`event_date`/`positive_tags`/`attention_tags` (`data-model.md`).
      `POST /api/avaliar/<token>` (`@limiter.limit("10 per hour")`) — 404 se token inválido;
      400 se faltar `client_name` ou `score` inválido (1-5); filtra `tags` por
      `_tags_for_score(score)` (descarta silenciosamente as fora de categoria); cria
      `ClientFeedback` e responde `201 {"ok": true}`. Type hints e docstring (Google style).
- [ ] T003 [US1] Importar `feedback_write` em `app/api/__init__.py` (mesmo padrão dos demais
      módulos `_write`).
- [ ] T004 [P] [US1] Criar `frontend/apps/public/src/lib/feedback.ts`: tipos (`FeedbackEvent`) +
      hooks `useFeedbackEvent(token)` (`useQuery`) e `useSubmitFeedback(token)` (`useMutation`,
      JSON body).
- [ ] T005 [P] [US1] Criar `frontend/apps/public/src/components/feedback/StarRating.tsx`: 5
      botões preenchendo até o valor sob hover ou até `score` (`research.md` §3), `onChange
      (score: number)`, alvo de toque ≥44px.
- [ ] T006 [P] [US1] Criar `frontend/apps/public/src/components/feedback/TagChips.tsx`: chips de
      etiqueta (seleção múltipla), usado tanto para as positivas quanto para as de atenção
      (mesmo componente, lista de opções diferente).
- [ ] T007 [US1] Criar `frontend/apps/public/src/pages/AvaliarPage.tsx`: busca o evento pelo
      token (`useFeedbackEvent`, T004) — 404 renderiza o estado de link inválido; sucesso
      renderiza o formulário (nome, `StarRating` de T005, bloco de etiquetas com
      `AnimatePresence`/altura animada revelado ao escolher a nota — `TagChips` de T006 com a
      lista certa por `score`, `useReducedMotion()`, `research.md` §4 — e comentário opcional);
      erro 400 mostra a mensagem sem apagar nome/nota; em sucesso (`useSubmitFeedback`, T004),
      troca o estado local para a tela de agradecimento, sem navegação de rota (`research.md`
      §2); botão de envio com estado "Enviando..." (disabled).
- [ ] T008 [US1] Em `App.tsx` (T001), substituir o placeholder de `/avaliar/:token` por
      `AvaliarPage` (T007).

**Checkpoint**: US1 completa e testável isoladamente — os 3 estados (formulário, agradecimento,
link inválido) funcionam ponta a ponta.

---

## Phase 3: Polish & Verificação

- [ ] T009 Criar `scripts/db/verify_164_feedback_publico_react.py` (gitignored): test client
      Flask contra `manto_local`, requests fora de `app_context` — cobre `GET` com token válido/
      inválido, submissão válida com paridade de campos salvos (`ClientFeedback`) vs. o caminho
      Jinja para os mesmos dados, erro por nome/nota faltando, etiqueta fora de categoria
      descartada silenciosamente (nota 5 + etiqueta de atenção não é salva).
- [ ] T010 Rodar `ruff check app/api/feedback_write.py`.
- [ ] T011 Rodar `npm run typecheck:public` e `npm run build:public`.
- [ ] T012 Conferência mobile (320–430px) dos 3 estados da tela — Princípio VIII.
- [ ] T013 Atualizar `docs/changelog.html` com entrada em linguagem simples (entrada 164,
      encerrando a US5) e republicar no artifact já existente (mesmo link).

## Dependencies

Setup (Phase 1) → US1 (Phase 2) → Polish (Phase 3).

## Implementation Strategy

Fatia única (US1) — não há incremento menor que entregue valor parcial aqui (o formulário, o
link inválido e o agradecimento são o mesmo fluxo). Com esta fatia completa, a US5 (Superfícies
Públicas) fica 100% concluída: catálogo (161), cadastro de talentos (162), formulários dinâmicos
(163) e feedback público (164) — a migração 144 segue para a US6 (Cauda administrativa).
