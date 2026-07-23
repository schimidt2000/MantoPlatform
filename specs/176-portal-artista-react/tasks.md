# Tasks: Portal do Artista — App React (fatia 1)

**Input**: Design documents from `specs/176-portal-artista-react/`
**Prerequisites**: plan.md, spec.md, data-model.md, contracts/portal-endpoints.md, quickstart.md

**Tests**: não solicitados no spec — a verificação funcional (script contra `manto_local`) cobre
o papel de teste de integração, seguindo o padrão já usado em todas as fatias anteriores.

## Phase 1: Setup

- [ ] T001 Configurar `frontend/apps/portal/package.json` com as dependências do padrão `public`
  (react-router-dom, @tanstack/react-query, framer-motion, react-hook-form, @hookform/resolvers,
  zod, @manto/ui, @manto/api-client, @manto/money) + devDependencies de Tailwind (tailwindcss,
  postcss, autoprefixer); rodar `npm install` na raiz do monorepo.
- [ ] T002 [P] Criar `frontend/apps/portal/tailwind.config.ts` (tokens portados de
  `app/templates/portal/*`, mesmos nomes de token que `internal`/`public`) e
  `frontend/apps/portal/postcss.config.js` (mesmo padrão do `public`).
- [ ] T003 [P] Criar `frontend/apps/portal/src/index.css` com as diretivas Tailwind e importar
  em `main.tsx`; atualizar `vite.config.ts` do portal com os aliases para `@manto/ui`/
  `@manto/money`/`@manto/api-client` (mesmo padrão de `internal`/`public`).

## Phase 2: Foundational

- [ ] T004 Extrair `app/talent_portal/portal_ops.py`: funções puras
  `get_agenda(talent) -> dict` (pendentes/futuros/histórico, reusando as queries hoje só em
  `home()`/`historico()`), `accept_invite(talent, role_id)`, `reject_invite(talent, role_id)`,
  `ack_event_change(talent, role_id)`, `get_figurino(talent, event_id) -> list | None` (`None` =
  não escalado), `update_photo(talent, kind, file)`, `update_document(talent, file)` — sem
  `flask.request`/`render_template` (recebem `talent`/dados já parseados).
- [ ] T005 Atualizar `app/talent_portal/routes.py` para chamar `portal_ops.py` nos pontos
  correspondentes (`home`, `historico`, `accept_invite`, `reject_invite`, `ack_event_change`,
  `event_figurino`) — zero mudança de comportamento, só remoção da duplicação.
- [ ] T006 Rodar uma verificação manual rápida das rotas Jinja de `app/talent_portal` (login,
  home, aceitar/recusar convite) para confirmar paridade após a extração, antes de prosseguir.
- [ ] T007 [P] Criar `app/api/portal_auth.py`: `portal_api_login_required` (decorator — só
  autenticação, paridade com `api_login_required`), `POST /api/portal/auth/login` (resolve
  `must_redirect_to_classic`), `POST /api/portal/auth/logout`, `GET /api/portal/auth/me`;
  registrar em `app/api/__init__.py`.

**Checkpoint**: núcleo de negócio extraído e sessão de API funcionando — pronto para as telas.

---

## Phase 3: User Story 1 — Login do talento (P1) 🎯 MVP (gate de tudo)

**Goal**: talento entra no app com CPF/e-mail + senha e chega numa área logada (ou é
redirecionado à versão clássica, se pendente troca de senha/termos).

**Independent Test**: acessar `/login`, entrar com credenciais válidas, confirmar sessão aberta
e redirecionamento correto (área logada OU versão clássica, conforme o estado da conta).

- [ ] T008 [P] [US1] `frontend/apps/portal/src/lib/portalAuth.ts` — `useLogin()`,
  `useLogout()`, `useCurrentTalent()` (`GET /api/portal/auth/me`, `null` em 401).
- [ ] T009 [US1] `frontend/apps/portal/src/pages/PortalLoginPage.tsx` — formulário CPF/e-mail +
  senha (react-hook-form + zod), erro genérico amigável, `loading` no botão; ao ver
  `must_redirect_to_classic`, `window.location.href = "/portal/login"` (redirect de página
  inteira, fora do router SPA).
- [ ] T010 [US1] `frontend/apps/portal/src/components/RequireTalentAuth.tsx` (paridade com
  `RequireAuth` do `internal`) + `frontend/apps/portal/src/App.tsx` com o router (`/login`
  público; demais rotas dentro do shell autenticado).
- [ ] T011 [US1] `frontend/apps/portal/src/components/PortalShell.tsx` — header simples +
  bottom nav mobile (Agenda / Convites / Fotos), botão "Sair".
- [ ] T012 [US1] Verificação funcional: login com sucesso/senha errada, `must_redirect_to_classic`
  correto para conta pendente, logout encerra sessão, `me` reflete estado.

**Checkpoint**: US1 completa — gate de autenticação funcionando, pronta para as demais telas.

---

## Phase 4: User Story 2 — Minha Agenda de Ensaios/Eventos (P1)

**Goal**: talento vê eventos futuros confirmados e histórico com situação de pagamento.

**Independent Test**: como talento com eventos futuros e passados, abrir a Agenda e conferir
ordenação e situação de pagamento no histórico.

- [ ] T013 [US2] `GET /api/portal/agenda` em `app/api/portal_agenda.py` — chama
  `portal_ops.get_agenda`, serializa pendentes/futuros/histórico.
- [ ] T014 [P] [US2] `frontend/apps/portal/src/lib/portalAgenda.ts` — `useAgenda()`.
- [ ] T015 [US2] `frontend/apps/portal/src/pages/PortalAgendaPage.tsx` — lista de futuros
  (data/local, aviso de alteração) + histórico (cachê via `@manto/money`, situação de
  pagamento), estados vazios amigáveis, link para a Ficha de Figurino de cada evento.
- [ ] T016 [US2] `POST /api/portal/roles/<id>/ack-change` em `portal_agenda.py` + botão "Ciente"
  na tela para o aviso de alteração.
- [ ] T017 [US2] Verificação funcional: futuros ordenados, histórico com cachê/pagamento
  corretos, aviso de alteração aparece e some após "ack-change", estado vazio sem evento.

**Checkpoint**: US1 + US2 completas — talento já consegue logar e ver sua agenda.

---

## Phase 5: User Story 3 — Meus Convites de Casting (Aceitar/Recusar) (P1)

**Goal**: talento vê convites pendentes e aceita/recusa cada um.

**Independent Test**: aceitar um convite pendente e confirmar que ele passa a aparecer como
confirmado na Agenda (US2); recusar outro e confirmar que some da lista de pendentes.

- [ ] T018 [US3] `POST /api/portal/invites/<id>/accept` e `/reject` em `app/api/portal_agenda.py`
  — chama `portal_ops.accept_invite`/`reject_invite`, 404 se o role não é do talento da sessão,
  idempotente.
- [ ] T019 [P] [US3] `useAcceptInvite()`/`useRejectInvite()` em `portalAgenda.ts`, invalidando a
  query da Agenda em ambos.
- [ ] T020 [US3] `frontend/apps/portal/src/pages/PortalConvitesPage.tsx` — lista de pendentes
  (evento/data/local), botão "Aceitar" e "Recusar" (`window.confirm` antes de recusar), estado
  vazio amigável.
- [ ] T021 [US3] Verificação funcional: aceitar/recusar mudam `invite_status`, 404 para role de
  outro talento, repetir a ação não quebra (idempotência), lista de pendentes atualiza.

**Checkpoint**: US1 + US2 + US3 completas — os 2 fluxos de uso diário do portal já funcionam.

---

## Phase 6: User Story 4 — Minha Ficha de Figurino (P2)

**Goal**: talento vê a ficha de figurino do seu personagem num evento em que está escalado.

**Independent Test**: a partir de um evento na Agenda, abrir a ficha e ver foto/observações;
tentar acessar a ficha de um evento onde não está escalado e ser negado.

- [ ] T022 [US4] `GET /api/portal/events/<id>/figurino` em `app/api/portal_figurino.py` — chama
  `portal_ops.get_figurino`, 403 se não escalado, `sheets: []` se não há ficha ainda; registrar
  módulo em `app/api/__init__.py`.
- [ ] T023 [P] [US4] `useFigurino(eventId)` em `frontend/apps/portal/src/lib/portalFigurino.ts`.
- [ ] T024 [US4] `frontend/apps/portal/src/pages/PortalFigurinoPage.tsx` — foto de referência +
  observações por personagem, estado vazio ("ainda não há ficha disponível").
- [ ] T025 [US4] Verificação funcional: 200 com ficha(s) para escalado, 403 para não escalado,
  `sheets: []` sem ficha cadastrada, múltiplos personagens do mesmo talento sem duplicar.

**Checkpoint**: US1-US4 completas.

---

## Phase 7: User Story 5 — Atualização de Fotos/Documentos (P3)

**Goal**: talento envia nova foto de rosto/corpo inteiro e novo arquivo de CNH.

**Independent Test**: enviar uma foto nova e confirmar que substitui a anterior; enviar um
arquivo inválido e ver erro amigável sem perder o resto da tela.

- [ ] T026 [US5] `POST /api/portal/profile/photo` e `/document` em `app/api/portal_profile.py`
  — multipart, reusa `cadastro_ops.validate_upload`/`PHOTO_EXTS`/`PHOTO_MAX`/`DOC_EXTS`/
  `DOC_MAX`, chama `portal_ops.update_photo`/`update_document`; registrar módulo em
  `app/api/__init__.py`.
- [ ] T027 [P] [US5] `usePhotoUpload()`/`useDocumentUpload()` em
  `frontend/apps/portal/src/lib/portalProfile.ts`.
- [ ] T028 [US5] `frontend/apps/portal/src/pages/PortalFotosDocumentosPage.tsx` — preview das
  fotos atuais, `FileUpload` (`@manto/ui`) para face/full/CNH, erro de validação inline sem
  limpar a tela.
- [ ] T029 [US5] Verificação funcional: upload válido substitui o arquivo, extensão/tamanho
  inválido retorna 400 com mensagem amigável.

**Checkpoint**: as 5 telas completas — spec 176 encerrada.

---

## Phase 8: Polish & Cross-Cutting

- [ ] T030 [P] `npx tsc --noEmit` e `npm run build` em `frontend/apps/portal` sem erros.
- [ ] T031 [P] `ruff check` nos arquivos Python novos/tocados (`app/talent_portal/portal_ops.py`,
  `routes.py`, `app/api/portal_*.py`); `ruff format` só nos arquivos novos.
- [ ] T032 Conferir as 5 telas em viewport mobile (320px E 375px, Princípio VIII
  NÃO-NEGOCIÁVEL) via Playwright headless antes de "pronto"; confirmar alvos de toque ≥44px,
  sem rolagem horizontal, transições Framer Motion com `useReducedMotion()`.
- [ ] T033 Confirmar zero regressão nas rotas Jinja legadas de `app/talent_portal` (paridade
  final, incluindo login/termos/troca de senha que continuam só lá).
- [ ] T034 Atualizar `docs/changelog.html` com a entrega (linguagem simples) e republicar no
  mesmo link já existente.

## Dependencies & Execution Order

- **Setup (T001-T003) → Foundational (T004-T007)**: bloqueiam todo o resto.
- **US1 (T008-T012)** depende só do Foundational — é o gate de tudo (sem login, nenhuma outra
  tela é alcançável).
- **US2 (T013-T017)** e **US3 (T018-T021)** dependem de US1 (shell autenticado); podem ser
  implementadas em paralelo entre si (arquivos/endpoints diferentes), mas US3 se beneficia de
  US2 já existir para verificar visualmente o efeito de aceitar um convite na Agenda.
- **US4 (T022-T025)** depende de US2 (o link para a ficha parte de um evento da Agenda).
- **US5 (T026-T029)** independente das demais — só depende do Foundational + shell (US1).
- **Polish (T030-T034)** só depois das 5 user stories.

## Parallel Execution Examples

- Setup: T002/T003 são `[P]` entre si.
- Dentro de cada US, o hook de frontend (`[P]`) pode ser escrito em paralelo ao endpoint de
  backend correspondente, integrado ao final (ex.: T008 `[P]` antes de T009 depender dele).
- US2 e US3 podem avançar em paralelo (arquivos/endpoints distintos) depois que US1 estiver de
  pé.
- US5 pode ser implementada a qualquer momento após o Foundational, em paralelo a US2/US3/US4.

## Implementation Strategy

**MVP = User Story 1** (T001-T012): sem login não há acesso a nada — é o gate de toda a
funcionalidade. **US2 + US3** (Agenda + Convites) formam o núcleo de uso diário do app e devem
vir logo em seguida. US4 (Figurino) e US5 (Fotos/Documentos) são incrementos subsequentes, cada
um verificado e commitado antes do próximo.
