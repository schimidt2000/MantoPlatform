# Research — Fundação da migração React SPA + Flask API (144, User Story 1)

Este research cobre só as decisões técnicas necessárias para a **Fundação** (US1): o
monorepo/ferramental frontend, a ponte de autenticação entre 3 SPAs e o Flask, a convenção
de contrato JSON que todas as ~194 rotas futuras vão herdar, e a migração dos design tokens
CSS existentes para Tailwind. Decisões específicas de US2–US6 (Agenda, Talentos/Figurino,
Financeiro, Público, Admin) ficam para o `/speckit-plan` de cada uma, quando começarem.

## 1. Ferramental do monorepo frontend

**Decision**: `npm workspaces` simples — sem Turborepo/Nx nesta fase.

**Rationale**: a constituição 2.0.0 já define a stack (Vite, TS, Tailwind, shadcn/ui,
Framer Motion, TanStack Query); adicionar uma ferramenta de monorepo orquestrando builds é
complexidade que a Governança da constituição pede para evitar até ser necessária (YAGNI —
"na dúvida, escolha o caminho mais simples"). Com 3 apps + 2-3 pacotes compartilhados,
`npm workspaces` + scripts do Vite já bastam; cache de build distribuído só compensa quando
o tempo de build incomodar de verdade.

**Alternatives considered**: Turborepo (cache de build mais rápido em CI, mas é uma
ferramenta nova para o time aprender antes de ter 1 linha de React em produção); pnpm
workspaces (funcionalmente equivalente ao npm workspaces para este caso, mas o projeto não
usa pnpm em nenhum outro lugar — sem motivo para introduzir um segundo gerenciador de
pacotes).

## 2. Sessão de autenticação entre 3 SPAs e o Flask (Q3 já decidida: cookie HttpOnly)

**Decision**: manter Flask-Login com cookie de sessão `HttpOnly` + `Secure` (produção) +
`SameSite=Lax`; adicionar `flask-cors` com `supports_credentials=True` e lista explícita de
origens permitidas por ambiente (dev: as 3 portas do Vite; produção: os 3 domínios/subdomínios
dos bundles React). Todo `fetch` do frontend usa `credentials: "include"`.

**Dev proxy**: cada app Vite roda um proxy (`server.proxy` no `vite.config.ts`) mapeando
`/api/*` para o Flask local — evita problema de cookie cross-origin em desenvolvimento
(o browser trata como same-origin do ponto de vista do app, já que a chamada sai do próprio
host:porta do Vite) e elimina a necessidade de CORS relaxado em dev. Em produção, se os 3
bundles forem servidos de subdomínios diferentes do domínio da API, CORS com
`supports_credentials` continua necessário (proxy de dev não existe em produção).

**Rationale**: é exatamente a escolha do usuário na Q3 — menor risco de segurança/regressão,
reaproveita o RBAC (`@login_required` / checagem de papel) hoje já implementado nas views,
sem reescrever autenticação do zero. Cobre também a sessão separada do Portal do Artista
(mesmo mecanismo, cookie de sessão próprio dessa área).

**Alternatives considered**: JWT em header `Authorization` (Q3 opção B) — rejeitado pelo
usuário; exigiria implementar emissão/expiração/refresh de token do zero num sistema que
nunca teve isso, risco maior sem ganho real dado que os 3 frontends e a API vivem sob domínios
controlados pela própria Manto (não é uma API pública third-party, onde token faria mais
sentido).

## 3. Convenção de contrato JSON (herdada por todas as rotas futuras)

**Decision**:
- Sucesso: o recurso (ou lista de recursos) direto no corpo — `{"id": 1, "nome": "..."}` ou
  `{"items": [...], "total": N}` para listas paginadas. Sem envelope `{"data": ...}`
  desnecessário para recursos simples.
- Erro: sempre `{"error": {"message": "<mensagem amigável pt-BR>", "fields": {...}}}` com
  status HTTP correto (400 validação, 401 não autenticado, 403 sem permissão, 404 não
  encontrado, 500 erro interno) — `fields` é opcional, usado para apontar qual campo falhou
  (consumido pelo `react-hook-form` + `zod` no FR-009).
- Toda resposta de erro amigável em português, nunca stack trace (mantém o que já vale hoje
  para HTML, agora para JSON).

**Rationale**: precisa ser definida UMA vez porque vai se repetir em ~194 endpoints — mudar
depois que dezenas de endpoints já existirem é caro. O formato escolhido é o mínimo que
resolve os dois casos reais do projeto (recurso singular/lista, erro com campo específico)
sem adicionar metadados que ninguém vai consumir ainda (ex.: não há necessidade de
`links`/HATEOAS neste sistema).

**Alternatives considered**: envelope JSON:API completo (mais padronizado, mas verboso demais
para o tamanho do time e sem ferramentas do ecossistema JSON:API já em uso aqui).

## 4. Migração dos design tokens (CSS variables → Tailwind theme)

**Decision**: mapear as variáveis CSS hoje espalhadas (`--accent`, `--line` do painel
interno; `--cat-bg`, `--cat-accent`, `--cat-radius` etc. do catálogo público) para o
`tailwind.config.ts` de cada app como `theme.extend.colors`/`borderRadius`, preservando os
valores exatos — zero mudança de paleta como efeito colateral da migração de stack.

**Rationale**: Princípio V da constituição ainda exige "Design System unificado via Tailwind
CSS" mas isso não significa redesenhar; a auditoria já identificou que o catálogo público tem
identidade visual própria e deliberada (não deve herdar o tema do painel interno) — os 3 apps
(interno, portal, público) terão 3 arquivos de tema Tailwind distintos, cada um herdando os
valores hoje hardcoded em CSS, não um tema único genérico.

## 5. Verificação funcional da Fundação

**Decision**: reaproveitar o padrão já estabelecido no projeto — script Python com o test
client do Flask contra `manto_local`, requests sempre fora de `with app.app_context()` — mas
chamando os novos endpoints JSON (`/api/auth/login`, `/api/auth/me`, `/api/dashboard`) e
inspecionando `response.get_json()` em vez de procurar strings no HTML renderizado. Para o
frontend, o portão de qualidade novo da constituição (`npx tsc --noEmit` sem erros, mais
`npm run build` sem falhas) substitui a antiga verificação de template.

**Rationale**: reaproveita 100% do padrão de verificação já validado ao longo de ~30 features
anteriores neste projeto (Princípio I — reutilizar antes de criar) — só muda o que é
inspecionado na resposta.
