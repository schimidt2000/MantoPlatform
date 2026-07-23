# Research — 173 Design System Global e Shell (FASE A)

## 1. Estado atual do frontend interno

- **Não existe layout compartilhado**: grep por `Layout|<aside|<nav` em
  `frontend/apps/internal/src` → zero resultados. Cada página renderiza
  `<div className="mx-auto max-w-4xl p-6">` + `<header>` próprio (ex.:
  `DashboardPage.tsx` tem uma fileira de `Button`s como navegação improvisada).
- **35 páginas** em `src/pages/`, todas roteadas em `App.tsx` com `<RequireAuth>` por
  rota (padrão repetido 34x — oportunidade de layout route).
- `@manto/ui` exporta: `cn`, `Button`, `Input`, `Card*`, `Skeleton`, `FileUpload`.
  Deps: radix slot, cva, clsx, lucide-react, tailwind-merge. **Sem framer-motion** (é dep
  só do app internal hoje).

## 2. Tokens — o que já existe vs. o que foi pedido

`frontend/apps/internal/tailwind.config.ts` já porta a paleta do Jinja
(`app/static/style.css :root`): `bg #f4f3f8`, `panel #fff`, `line #e5e3ef`,
`accent #544596/#3c316b`, `sidebar.bg #1e1635`, `sidebar.accent #f7d897`, sombras e radii.

**Decisão**: promover esses tokens a um preset compartilhado
(`frontend/packages/ui/tailwind-preset.ts`) e atualizar os valores pedidos pelo usuário:
`sidebar.bg → #1f1a30`, `bg → #f4f5f7`. Racional: o usuário especificou os hexes
explicitamente; a diferença vs. Jinja é imperceptível (mesma família de roxo/cinza) e a
"fidelidade" cobrada é de identidade, não de hex exato. Complementos novos no preset:
tokens de densidade tipográfica já cobertos por `text-xs`/`text-sm` nativos (nada a
inventar) e cor de borda de card `slate-200/80` mapeada para o token `line` existente
(uma fonte só — não introduzir segunda cor de borda).

**Alternativa rejeitada**: criar arquivo CSS de variáveis — a constituição proíbe CSS
solto; preset Tailwind é o mecanismo idiomático para compartilhar tema entre apps do
monorepo (`presets: [mantoPreset]`).

## 3. Navegação — fonte da verdade (base.html)

Estrutura extraída de `app/templates/base.html` (linhas 27–271), com regras de
visibilidade (`eff_has_role` = papel efetivo, respeitando impersonação):

| Grupo | Item | Rota | Visibilidade Jinja | Na SPA? |
|---|---|---|---|---|
| (topo) | Home | `/` | todos | ✅ |
| (topo) | Agenda | `/agenda` | todos | ✅ |
| (topo) | Gastos Extras | `/gastos/` | todos | ❌ Jinja-only |
| Casting | Banco de Talentos | `/talents` | todos | ✅ |
| Casting | Avaliações | `/talents/avaliacoes` | todos | ❌ Jinja-only |
| Produção | Revisão | `/revisao` | todos | ✅ |
| Produção | Figurinos | `/figurinos` | todos | ✅ |
| Comercial | Novo Evento | `/events/new` | COMERCIAL, SUPERADMIN | ✅ |
| Comercial | Pipeline de Vendas | `/vendas` | COMERCIAL, FINANCEIRO, SUPERADMIN ou responsável EducaManto | ✅ |
| Comercial | Clientes | `/clientes` | COMERCIAL, FINANCEIRO, SUPERADMIN | ✅ |
| Comercial | Avaliações (clientes) | `/clientes/avaliacoes` | COMERCIAL, FINANCEIRO, SUPERADMIN | ✅ |
| Comercial | Formulários | `/formularios/` | COMERCIAL, FINANCEIRO, SUPERADMIN | ❌ Jinja-only (admin) |
| Comercial | Catálogo (pública, nova aba) | `/catalogo/` | COMERCIAL, FINANCEIRO, SUPERADMIN | ✅ como link externo |
| Comercial | Gerenciar catálogo | `/admin/catalogo` | SUPERADMIN | ✅ |
| Comercial | Comissões | `/financeiro/comissoes` | COMERCIAL, FINANCEIRO, SUPERADMIN ou resp. EducaManto | ✅ |
| Financeiro | Painel Financeiro | `/financeiro` | FINANCEIRO, SUPERADMIN | ✅ |
| Financeiro | Pagamentos | `/financeiro/pagamentos` | FINANCEIRO, SUPERADMIN | ✅ |
| Financeiro | Gastos Recorrentes | `/gastos/recorrentes` | FINANCEIRO, SUPERADMIN | ❌ Jinja-only |
| Ferramentas | Calc. Orçamento | `/orcamento/` | COMERCIAL, SUPERADMIN | ❌ Jinja-only |
| Ferramentas | Config. Preços | `/orcamento/settings` | SUPERADMIN | ❌ Jinja-only |
| Ferramentas | Orçamentos | `/orcamento/historico` | COMERCIAL, SUPERADMIN | ❌ Jinja-only |
| Ferramentas | EducaManto | `/educamanto` | COMERCIAL, SUPERADMIN, ENSAIO, REVENDEDOR_EDUCAMANTO | ✅ (calculadora, feature 171) |
| Ferramentas | Pacotes EducaManto | `/educamanto/packages` | COMERCIAL, SUPERADMIN | ❌ Jinja-only |
| Sistema | Usuários | `/admin/usuarios` | SUPERADMIN ou FINANCEIRO | ✅ |
| Sistema | Administração | `/admin/configuracoes` (hub Jinja `/admin/`) | SUPERADMIN | ✅ (config/sync/logs/desempenho etc. como itens próprios) |
| Sistema | Desempenho | `/admin/desempenho` | SUPERADMIN | ✅ |
| Sistema | Logs | `/admin/logs` | SUPERADMIN | ✅ |
| Sistema | Sincronização Agenda | `/admin/sync` | SUPERADMIN | ✅ |

Notas:
- `is_revendedor_only` (REVENDEDOR_EDUCAMANTO sem outros papéis) esconde quase tudo no
  Jinja — a config declarativa reproduz: revendedor-only vê apenas EducaManto (e Agenda?
  não: no Jinja, Home/Casting/Produção/Comercial somem com `not is_revendedor_only`;
  Agenda fica visível pois não tem guard — manter paridade: Agenda visível).
- Rotas SPA extra sem item no menu Jinja (páginas de detalhe/formulário) não entram no
  menu — são alcançadas por navegação interna (ex.: `/events/:id`, `/talents/:id/edit`).
- Telas admin SPA sem item dedicado no Jinja (`/admin/anuncio-portal`,
  `/admin/migrar-arquivos`, `/admin/importar-catalogo`) ficam alcançáveis pela página de
  Configurações (como hoje) — menu lista só o que o Jinja lista, para paridade visual.

## 4. Impersonação ("Ver como")

- Jinja: `POST /impersonate/<role>` e `POST /impersonate/reset`
  (`app/__init__.py:790–804`), guardando `session["impersonate_role"]`; restrito a
  SUPERADMIN real; papéis válidos `CASTING, FIGURINO, COMERCIAL, FINANCEIRO, ENSAIO`
  (lista local `_IMPERSONABLE_ROLES`).
- Todo o backend já respeita a sessão (`session.get("impersonate_role")` em
  `api/agenda*.py`, `api/dashboard.py`, context processors etc.) — impersonar via API
  afeta imediatamente todas as respostas. ✅ nada a mudar nos endpoints existentes.
- `serialize_user` (`app/api/auth.py`) já expõe `roles`, `is_superadmin` (real e sem
  impersonação ativa) e `impersonating`.

**Decisão**: endpoints JSON `POST /api/auth/impersonate` (body `{"role": "CASTING"}`) e
`DELETE /api/auth/impersonate`, ambos retornando `serialize_user` atualizado; promover a
lista para `app/constants.py` (`IMPERSONABLE_ROLES`) e fazer as rotas Jinja importarem a
mesma constante (fonte única, Princípio I). RBAC por função no início da view (padrão da
API). No front, `useImpersonate`/`useImpersonateReset` fazem
`queryClient.invalidateQueries()` global no sucesso — tudo que depende de RBAC refaz o
fetch com a nova sessão.

**Gap detectado**: o menu precisa de `is_educamanto_responsavel` (visibilidade de
Pipeline/Comissões/EducaManto) — hoje só o context processor Jinja expõe
(`app/__init__.py:300–308`). **Decisão**: acrescentar o campo em `serialize_user`
reusando o mesmo helper.

**Detalhe de front**: `AuthUser.is_superadmin` é `false` durante impersonação (semântica
"efetivo"); para exibir o seletor "Ver como" o front precisa do flag REAL — expor
`is_real_superadmin` no `serialize_user` (o Jinja usa `is_real_superadmin()` para isso).
Campo aditivo, não quebra consumidores atuais.

## 5. Padrão de adoção nas 35 páginas

**Decisão**: layout route do react-router v6 — `App.tsx` ganha
`<Route element={<RequireAuth><AppShell/></RequireAuth>}>` englobando todas as rotas
autenticadas (elimina os 34 `<RequireAuth>` repetidos); `AppShell` renderiza
`AppLayout` + `<Outlet/>`. `/login` e o fallback `*` ficam fora/dentro conforme spec.
Cada página então: (a) remove `max-w-*` wrapper próprio se conflitar com o container do
shell, (b) troca `<header>` ad-hoc por `<PageHeader>`, (c) remove navegação improvisada
(botões do Dashboard). Logout sai das páginas e vive no rodapé da sidebar.

**Alternativa rejeitada**: envolver página a página com `<AppShell>` — 35 edições de
rota redundantes e risco de esquecer telas futuras.

## 6. Componentes novos — contratos de props (resumo)

- `AppLayout`: `brand` (nó), `sections: NavSection[]` (`{label?, items: {key, label,
  icon, href, active, external?}[]}`), `footer` (nó), `renderLink` (render prop para o
  app injetar `NavLink` do router — `@manto/ui` não depende de react-router),
  `mobileTitle?`. Gerencia drawer mobile (estado interno + framer-motion +
  `useReducedMotion`), overlay, fechamento em navegação/resize/tecla Esc.
- `PageHeader`: `title`, `breadcrumbs?: {label, href?}[]`, `actions?` (nó),
  `filters?` (nó), `subtitle?`.
- `DenseCard`: `title`, `headerRight?`, `stats?: {label, value}[]`, `children`,
  `padding?: "compact" | "normal"` — composto sobre `Card` existente.
- `MetricBadge`: `children`/`items?: string[]` (junção com "•"), `tone?: "neutral" |
  "accent" | "green" | "red" | "blue" | "gold"`, `size?: "xs" | "sm"`.
- framer-motion entra como `peerDependency` de `@manto/ui` (apps já têm/instalam a dep
  real; hoisting do npm workspaces resolve).

## 7. Logo / marca

`base.html` usa bloco `sidebar-brand` com nome "Manto" + subtítulo "Plataforma" (sem
imagem obrigatória; há favicon/logo em `app/static/`). **Decisão**: brand tipográfica
idêntica ao Jinja (nome + subtítulo, dourado `sidebar.accent` no acento) — sem copiar
asset binário nesta fase; se existir SVG da logo em `app/static`, avaliar no implement.

## 8. Verificação

- **Backend**: script test client contra `manto_local` — login SUPERADMIN → impersonate
  cada papel válido (200 + `impersonating` correto + efeito em endpoint RBAC real, ex.:
  `/api/financeiro/dashboard` 403 sob CASTING), papel inválido (400), não-SUPERADMIN
  (403), DELETE reset (200 + `impersonating: null`), tudo fora de `app_context`.
- **Frontend**: `npx tsc --noEmit` + `npm run build` em `frontend/apps/internal` (e
  `public`, que passa a consumir o preset); conferência visual desktop + mobile 375px.
