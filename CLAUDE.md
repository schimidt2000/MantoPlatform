# CLAUDE.md — Instruções para o Claude Code

> Este arquivo é lido automaticamente pelo Claude Code ao abrir o projeto.
> Ele define como o Claude deve trabalhar neste projeto (backend Python/Flask + frontend
> React/TypeScript).

---

## 🏗️ Sobre o Projeto

- **Nome**: Plataforma Manto
- **Descrição**: Sistema empresarial ERP para gestão de eventos, talentos, figurino, financeiro e agenda. Integrado com Google Calendar e Google Sheets.
- **Arquitetura**: SPA desacoplada — **Frontend React** (Vite + TypeScript + Tailwind CSS +
  shadcn/ui + Framer Motion + TanStack Query) consumindo o **Flask como API JSON estrita**
  (`/api/*`). Banco: SQLite (dev casual) → PostgreSQL (produção, Railway).
- **Integrações**: Google Calendar API (OAuth 2.0), Google Sheets API (service account)

> ✅ **MIGRAÇÃO REACT CONCLUÍDA (feature 144, constituição v2.0.0)** — 2026-07-22. As 6 User
> Stories da spec (`specs/144-migracao-react-spa/spec.md`) estão 100% feitas: Fundação (auth +
> dashboard) → Agenda/Eventos → Talentos/Figurino → Financeiro/Vendas → Superfícies Públicas
> (catálogo, `/cadastro`, formulários, feedback) → Cauda Administrativa (usuários, RH,
> configurações, catálogo admin, revisão de mídia). Todo o sistema dentro desse escopo tem
> endpoint JSON equivalente e tela em React — ver `specs/144-migracao-react-spa/` e
> `specs/165..170-*` (fatias da Cauda Administrativa) para o histórico completo.
>
> **Escopo real da migração 144 — leia antes de assumir "tudo é React"**:
> - **Dentro do escopo (React + API, completo)**: tudo que staff autenticado usa —
>   `frontend/apps/internal` (agenda, talentos, figurino, financeiro, vendas, clientes, admin,
>   RH, revisão de mídia) e `frontend/apps/public` (catálogo, `/cadastro`, formulários,
>   feedback por link — visitante anônimo, sem login).
> - **FORA do escopo desta migração — ainda 100% Jinja2/vanilla**: o **Portal do Artista**
>   (`app/talent_portal`, sessão própria do talento) nunca foi atribuído a nenhuma das 6 User
>   Stories, apesar de a spec original (Q2) ter reservado um 3º bundle para ele
>   (`frontend/apps/portal` — hoje só scaffold vazio, sem telas). Migrá-lo é uma **iniciativa
>   futura própria, com sua própria spec** — não assuma que está coberto, e não misture
>   trabalho nele com o padrão desta migração sem uma spec dedicada.
> - **Código Jinja legado das áreas já migradas**: as views/templates antigos de cada
>   blueprint migrado (`app/admin`, `app/calendar`, `app/talents`, `app/figurino`,
>   `app/financeiro`, `app/clientes`, `app/revisao`, `app/catalogo`, `app/cadastro`,
>   `app/formularios`, `app/feedback`) **continuam existindo em paralelo** no código — cada
>   fatia manteve a rota Jinja antiga funcionando sem regressão em vez de apagá-la
>   (strangler-fig). Decomissionar/apagar esse código legado é limpeza futura, fora do escopo
>   desta migração; ao tocar esses blueprints por outro motivo, não é necessário preservar o
>   Jinja também — confirme com o usuário antes de apagar uma view antiga.
>
> **Padrões obrigatórios em código NOVO** (dentro do escopo migrado): contrato JSON em
> `specs/144-migracao-react-spa/contracts/api-conventions.md`; auth por cookie de sessão
> HttpOnly (Flask-Login) + `credentials:"include"`; máscara monetária BRL via `@manto/money`
> (nunca reinventar); núcleo de negócio em módulo `*_ops.py` reusado por API e (quando ainda
> presente) pela view Jinja legada — nunca duplicar lógica. Rodar `frontend/`:
> `npm run dev:internal` (staff) / `npm run dev:public` (visitante anônimo) — proxy Vite
> `/api`→Flask.

---

## 📁 Estrutura do Projeto

```
Manto_Platform/
├── CLAUDE.md
├── run.py                 ← entrypoint do Flask (python run.py)
├── requirements.txt
├── migrations/            ← Alembic (Flask-Migrate) — sempre escritas à mão
├── instance/
│   └── uploads/           ← arquivos locais (dev); produção usa volume/S3 (app/storage.py)
├── docs/
│   └── changelog.html     ← changelog do time (republicar no artifact existente)
├── specs/                 ← spec-kit — uma pasta por feature (spec/plan/tasks/contracts)
│   └── 144-migracao-react-spa/   ← spec-mãe da migração + fatias 145–170
│
├── app/                   ← backend Flask — API JSON (100% do escopo migrado) + Jinja legado
│   ├── __init__.py        ← app factory, registro de blueprints
│   ├── config.py
│   ├── models.py          ← todos os modelos SQLAlchemy
│   ├── api/                       ← blueprint único `/api/*` — toda rota nova nasce aqui
│   │   ├── __init__.py            ← api_bp; importa cada módulo de rotas por efeito colateral
│   │   ├── auth.py, dashboard.py  ← Fundação (144)
│   │   ├── agenda*.py             ← Agenda/Eventos (145–153)
│   │   ├── talents_*.py, figurino_*.py    ← Talentos/Figurino (154–155)
│   │   ├── financeiro_*.py                ← Financeiro/Vendas (156–160)
│   │   ├── catalogo_read.py, cadastro_write.py, formularios_write.py, feedback_write.py
│   │   │                                  ← Superfícies Públicas (161–164)
│   │   ├── clientes_*.py, rh_read.py, admin_*.py, revisao_*.py
│   │   │                                  ← Cauda Administrativa (165–170)
│   │   └── (cada rota nova = função pura que só valida RBAC e serializa; a regra de
│   │       negócio mora em `app/<blueprint>/<nome>_ops.py`, reusada pela view Jinja legada)
│   ├── admin/, calendar/, talents/, figurino/, financeiro/, clientes/, rh/, revisao/,
│   │   catalogo/, cadastro/, formularios/, feedback/
│   │       ← blueprints migrados: `routes.py` (view Jinja legada, mantida) + `*_ops.py`
│   │         (núcleo de negócio, fonte única, reusado pela API)
│   ├── talent_portal/     ← ⚠️ Portal do Artista — FORA do escopo da migração 144, 100%
│   │                         Jinja/vanilla ainda; ver aviso no topo deste arquivo
│   ├── static/, templates/  ← Jinja2/CSS/JS legado (ainda presente, ver aviso no topo)
│   └── storage.py          ← abstração de upload (local/S3), usada por API e Jinja legado
│
└── frontend/               ← monorepo npm workspaces — interface completa (staff + público)
    ├── apps/
    │   ├── internal/        ← staff autenticado — TUDO que existe além do Portal do Artista
    │   ├── public/          ← visitante anônimo — catálogo, /cadastro, formulários, feedback
    │   └── portal/          ← ⚠️ scaffold vazio — Portal do Artista NÃO migrado (ver aviso)
    └── packages/
        ├── ui/               ← design system (Button, Card, Input, Skeleton, FileUpload…)
        ├── api-client/       ← apiFetch/apiFetchBlob, ApiRequestError, assetUrl (fonte única)
        └── money/            ← formatBRL/parseBRL (fonte única, Princípio VII)

.claude/
└── skills/
    ├── python-quality.md
    ├── ui-ux.md
    ├── autonomy.md
    └── architecture.md
```

---

## 🐍 Qualidade de Código Python

### Antes de escrever qualquer código:
1. Verifique se já existe algo parecido no projeto — **não duplique lógica**
2. Pense na interface pública da função/classe antes da implementação
3. Escreva o teste ANTES do código (TDD: Red → Green → Refactor)

### Padrões obrigatórios:
- **Type hints** em todas as funções e métodos
- **Docstrings** em classes e funções públicas (formato Google style)
- **Nomes descritivos**: sem abreviações obscuras (`user_count`, não `uc`)
- **Funções pequenas**: máximo ~30 linhas; se passar, extraia funções
- **Evite aninhamento profundo**: máximo 3 níveis de indentação
- **Constantes em UPPER_CASE** no topo do módulo ou em `config.py`
- **Nunca use `except Exception` sem logar o erro**

### Ferramentas que devem ser usadas:
```bash
# Linting (obrigatório nos arquivos tocados)
ruff check app/

# Formatação: só em arquivos NOVOS (legado segue o estilo circundante — não reformatar arquivo inteiro)
ruff format <arquivo_novo.py>

# Verificação funcional da feature (obrigatória antes do merge):
# script com test client do Flask contra a cópia local manto_local (Postgres).
# REGRA: requests do test client SEMPRE fora de `with app.app_context()` —
# contexto persistente vaza o usuário logado entre requests.

# mypy: recomendado (vira obrigatório quando instalado no ambiente)
```

### Exemplo de código de qualidade:
```python
from typing import Optional
from dataclasses import dataclass

@dataclass
class User:
    """Representa um usuário do sistema."""
    id: int
    name: str
    email: str
    is_active: bool = True

def get_active_users(users: list[User]) -> list[User]:
    """Retorna apenas usuários ativos.
    
    Args:
        users: Lista completa de usuários.
        
    Returns:
        Lista filtrada com apenas usuários ativos.
    """
    return [u for u in users if u.is_active]
```

---

## 🎨 UI/UX — React (Tailwind + shadcn/ui + Framer Motion)

Toda tela nova é um componente React em `frontend/apps/internal` (staff) ou
`frontend/apps/public` (visitante anônimo) — nunca um template Jinja novo (ver aviso no topo
sobre o escopo real da migração). Regras completas: Princípios V/VII/VIII/IX da constituição
(`.specify/memory/constitution.md`).

### Princípios de design que devem ser seguidos:
- **Hierarquia visual clara**: o usuário deve saber onde olhar primeiro
- **Feedback imediato**: toda ação tem loading/erro/sucesso via TanStack Query — nenhum botão
  fica "morto" ao clique (Princípio V, não-negociável)
- **Consistência**: só Tailwind CSS + componentes de `@manto/ui` (`Button`, `Card`, `Input`,
  `Skeleton`, `FileUpload`…) — zero CSS solto, zero estilo inline
- **Mobile-first**: comece pelo mobile, expanda para desktop (obrigatório em superfícies
  públicas — Princípio VIII)
- **Movimento com propósito**: transições de Framer Motion (150–350ms), respeitando
  `useReducedMotion()` (Princípio IX)

### Padrões obrigatórios (fonte única, nunca reinventar):
- **Valor monetário**: sempre `@manto/money` (`formatBRL`/`parseBRL`) — nunca outra máscara
- **Chamada à API**: sempre `apiFetch`/`apiFetchBlob` de `@manto/api-client` (trata erro/
  `ApiRequestError` com `fields` para apontar campo inválido em formulários)
- **Arquivo servido pelo Flask**: sempre `assetUrl()` de `@manto/api-client` (nunca concatenar
  URL à mão — production usa origem diferente do frontend)

### Componentes obrigatórios:
- Estado de loading para toda operação assíncrona (`Skeleton` ou `loading` no `Button`)
- Mensagens de erro amigáveis em pt-BR (nunca stack trace)
- Confirmação antes de ações destrutivas — `window.confirm()` é o padrão já usado no projeto
  (não há `Dialog` no design system compartilhado ainda)
- Feedback de sucesso após operações importantes

### Ao criar qualquer tela nova:
1. Veja se já existe algo parecido em `frontend/apps/internal/src/pages/` — reaproveite o
   padrão (hooks em `lib/<dominio>.ts`, página em `pages/<Nome>Page.tsx`)
2. Defina o objetivo da tela e liste os elementos necessários
3. Pense no estado vazio e nos erros antes de escrever código
4. Núcleo de negócio novo no backend? Sempre um endpoint em `app/api/<dominio>_read.py`/
   `_write.py`, chamando um `app/<blueprint>/<dominio>_ops.py` — nunca lógica direto na rota

---

## 🤖 Autonomia — Como o Claude Deve Trabalhar

### Fluxo de desenvolvimento:
```
1. ENTENDER → Perguntar se a tarefa não está clara
2. PLANEJAR  → Mostrar o plano ANTES de escrever código
3. EXECUTAR  → Implementar em pequenos passos verificáveis
4. TESTAR    → Rodar os testes após cada mudança
5. REVISAR   → Checar qualidade antes de declarar "pronto"
```

### Regras de autonomia:
- **Nunca assuma**: se houver dúvida sobre um requisito, pergunte antes
- **Mostre o plano**: antes de mudanças grandes, liste o que será alterado
- **Pequenos commits**: cada funcionalidade = um commit atômico
- **Não quebre o que funciona**: rode os testes antes de cada commit
- **Relate o progresso**: informe o que foi feito e o que falta
- **Mantenha o changelog do time atualizado**: ao concluir uma feature/mudança visível ao
  usuário, adicione uma entrada em `docs/changelog.html` (linguagem simples, o que mudou —
  não como) e republique no mesmo link já existente (nunca crie um link novo). É a página
  que o usuário usa para acompanhar e apresentar as entregas ao time.

### Quando travar:
1. Tente 2 abordagens diferentes
2. Se ainda travar, pare e explique o problema claramente
3. Não fique em loop — peça ajuda ao usuário

### Antes de qualquer task grande, fazer:
```bash
# Garantir que a cópia local (manto_local, Postgres) está atualizada e no head das
# migrations — toda verificação roda contra ela, nunca contra o SQLite vazio.
# Ver a "REGRA DE TESTES" em "🔧 Comandos do Projeto".
python -m flask db heads   # com DATABASE_URL apontando p/ manto_local

# Lint limpo nos arquivos que serão tocados
ruff check app/
```

---

## 🏛️ Arquitetura

### Padrão real do backend (cada blueprint migrado segue isto):
```
app/<blueprint>/
├── routes.py          ← views Jinja legadas — hoje só chamam <dominio>_ops, nunca duplicam
│                         lógica (ver aviso no topo sobre o Jinja legado)
└── <dominio>_ops.py   ← núcleo de negócio: funções puras (sem `request`/`render_template`),
                          type hints + docstring, exceções próprias p/ erro de validação
                          (ex.: `ClientValidationError`) — fonte única, reusada por Jinja e API

app/api/
├── <dominio>_read.py  ← GET — só valida RBAC (função, não decorator) e serializa
└── <dominio>_write.py ← POST/PATCH/DELETE — idem; erros viram `json_error(msg, status,
                          fields=...)` de `app.api_utils`
```

### Regras de arquitetura:
- **Routes não fazem lógica de negócio** — só validam RBAC, chamam `*_ops` e serializam/
  redirecionam
- **`*_ops.py` são puros**: nunca importam `flask.request`/`render_template`/`flash`
- **RBAC em endpoint de API é função, não decorator Flask** — os decorators legados
  (`@require_superadmin` etc.) dependem de sessão de página; a API reimplementa o mesmo check
  como função chamada no início da view, validada por paridade de comportamento (não por
  reusar o decorator)
- **Extrair `*_ops.py` só quando há núcleo de negócio real a duplicar** — se a "lógica" é só
  checar uma permissão (ex.: `app/rh`), não vale a pena um módulo novo
- **Config centralizado**: zero strings mágicas espalhadas no código

### Dependências (só pode depender da camada abaixo):
```
API (app/api/*) ──┐
                   ├──→ <dominio>_ops.py ──→ Models (app/models.py)
Jinja (routes.py) ─┘
```

### Configuração via variáveis de ambiente:
```python
# config.py
import os
from dataclasses import dataclass

@dataclass
class Config:
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///dev.db")
    secret_key: str = os.getenv("SECRET_KEY", "dev-only-key")
    debug: bool = os.getenv("DEBUG", "false").lower() == "true"

config = Config()
```

---

## ✅ Checklist Antes de Dizer "Pronto"

- [ ] **Verificação funcional automatizada da feature passando** — script com test client
      contra `manto_local` (Postgres), cobrindo sucesso/erro/permissões; requests fora de
      `app_context`. Nunca validar contra o SQLite vazio.
- [ ] Sem warnings de linting nos arquivos tocados (`ruff check`)
- [ ] Arquivos novos formatados (`ruff format`); legado segue o estilo circundante
- [ ] Funções novas têm docstring e type hints (Python) / interfaces/types explícitos (TS)
- [ ] Casos de erro tratados — todo `except` amplo registra em log; React trata erro/loading/
      sucesso (TanStack Query) em toda tela nova
- [ ] Sem secrets/senhas hardcoded no código
- [ ] Variáveis com nomes claros e descritivos
- [ ] **Tela React tocada?** `npx tsc --noEmit` e `npm run build` (em `frontend/apps/<app>`)
      sem erros antes de declarar pronto
- [ ] Superfície pública ou tela nova tocada? Conferida em viewport mobile (Princípio VIII da
      constituição)
- [ ] `docs/changelog.html` atualizado com a entrega, republicado no mesmo link

---

## 🔧 Comandos do Projeto

> ⚠️ **REGRA DE TESTES — LEIA ANTES DE VERIFICAR QUALQUER COISA**
> Produção roda em **PostgreSQL**. Por isso, **todo teste/verificação DEVE rodar contra a
> cópia local do banco real** (`manto_local`, PostgreSQL 18 local) — **nunca** contra o
> SQLite vazio de `instance/`. O SQLite não pega bugs Postgres-only (ex.: `float−Decimal` no
> financeiro). Antes de verificar: garanta que `manto_local` está atualizado e aponte o app/
> teste para ele via `DATABASE_URL` (use `scripts/db/run-local.ps1`).
> Detalhes e setup: `scripts/db/README.md`.

```powershell
# Instalar dependências
pip install -r requirements.txt

# Rodar aplicação (SQLite de dev — só para uso casual)
python run.py

# ── BANCO DE TESTES (cópia real de produção) ──────────────────────────
# Rodar o app/verificações apontando para a cópia local (Postgres) — USE ISTO PARA TESTAR
.\scripts\db\run-local.ps1
#   (equivale a: $env:DATABASE_URL = (Get-Content .local-db-url -Raw).Trim(); python run.py)

# Atualizar a cópia local com o backup mais recente
.\scripts\db\refresh-local-db.ps1
# Baixar um dump novo do Railway E atualizar a cópia local
.\scripts\db\refresh-local-db.ps1 -Fresh
# Backup manual do banco de produção (também roda sozinho toda noite, 02:00)
.\scripts\db\backup-railway.ps1
# ──────────────────────────────────────────────────────────────────────

# Aplicar migrations do banco
python -m flask db upgrade

# Criar nova migration após alterar models.py
python -m flask db migrate -m "descrição"

# Verificação funcional — SEMPRE contra manto_local (defina DATABASE_URL para a cópia local)
# Padrão: script com test client do Flask (requests FORA de app_context)
$env:DATABASE_URL = (Get-Content .local-db-url -Raw).Trim(); $env:PYTHONPATH = (Get-Location).Path
.venv\Scripts\python.exe <script_de_verificacao.py>

# Verificar lint
ruff check app/

# Formatar (apenas arquivos novos)
ruff format <arquivo_novo.py>
```

### Frontend (React)

```powershell
# Instalar dependências (na primeira vez, ou após mudar package.json)
cd frontend; npm install

# Rodar em dev — staff (proxy Vite /api → Flask local, rode o backend em paralelo)
npm run dev:internal
# Rodar em dev — visitante anônimo (catálogo/cadastro/formulários/feedback)
npm run dev:public

# Checar tipos sem emitir build (rodar sempre que tocar uma tela React)
npx tsc --noEmit          # dentro de frontend/apps/internal ou frontend/apps/public

# Build de produção (mesmo comando valida tsc + vite build)
npm run build             # dentro do app específico
```

---

## 📋 Skills Adicionais

O Claude deve ler os arquivos em `.claude/skills/` quando trabalhar nas áreas correspondentes:

- **`.claude/skills/python-quality.md`** → ao escrever ou revisar código Python
- **`.claude/skills/ui-ux.md`** → ao criar ou modificar interfaces
- **`.claude/skills/autonomy.md`** → ao planejar tarefas complexas
- **`.claude/skills/architecture.md`** → ao criar novos módulos/estruturas

---

*Gerado para uso com Claude Code (VSCode Extension)*
*Inspirado em: obra/superpowers, VoltAgent/awesome-agent-skills, nextlevelbuilder/ui-ux-pro-max-skill*

<!-- SPECKIT START -->
For additional context about technologies to be used, project structure,
shell commands, and other important information, read the current plan:
`specs/174-redesenho-fidelidade-visual/plan.md`
<!-- SPECKIT END -->
