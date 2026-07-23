# Data Model — 173 Design System Global e Shell (FASE A)

Nenhuma tabela nova, nenhuma migration. Os "modelos" desta feature são contratos de
serialização e estruturas de configuração do frontend.

## AuthUser (resposta de `/api/auth/me`, login e impersonate)

Campos existentes + **2 aditivos** (negrito):

| Campo | Tipo | Semântica |
|---|---|---|
| `id` | number | id do usuário |
| `name` | string | nome |
| `email` | string | e-mail |
| `roles` | string[] | papéis REAIS do usuário |
| `is_superadmin` | boolean | SUPERADMIN real **e sem** impersonação ativa (efetivo) |
| `impersonating` | string \| null | papel simulado ativo (só p/ SUPERADMIN real) |
| **`is_real_superadmin`** | boolean | SUPERADMIN real, independente de impersonação — controla a exibição do "Ver como" |
| **`is_educamanto_responsavel`** | boolean | usuário é o responsável EducaManto (`SiteSetting`) — afeta visibilidade de Pipeline/Comissões/EducaManto no menu |

**Papel efetivo (derivação no front)**: `impersonating ? [impersonating] : roles`.

## IMPERSONABLE_ROLES (constante compartilhada)

`app/constants.py`: `IMPERSONABLE_ROLES = [CASTING, FIGURINO, COMERCIAL, FINANCEIRO,
ENSAIO]` — fonte única usada pelas rotas Jinja `/impersonate/*` e pelos endpoints JSON.

## NavSection / NavItem (config declarativa, `frontend/apps/internal/src/lib/navigation.tsx`)

```
NavItem {
  key: string            // identificador estável
  label: string          // pt-BR, idêntico ao Jinja
  href: string           // rota SPA (ou URL externa)
  icon: LucideIcon
  external?: boolean     // ex.: /catalogo/ abre em nova aba
  isActive(pathname): boolean   // regras de destaque portadas do base.html
  isVisible(user: AuthUser): boolean  // papel efetivo + flags (educamanto, revendedor-only)
}
NavSection { label?: string; items: NavItem[] }
```

Estados relevantes:
- **revendedor-only** (só REVENDEDor_EDUCAMANTO): vê apenas Agenda + EducaManto.
- **impersonação ativa**: `isVisible` avalia com o papel efetivo (lista de 1 papel).

## Sessão (inalterada)

`session["impersonate_role"]: str | None` — mesma chave do Jinja; setada/limpa pelos
endpoints novos; lida por todo o backend existente.
