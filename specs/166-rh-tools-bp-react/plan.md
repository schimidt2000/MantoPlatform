# Implementation Plan: RH em React + destino do blueprint órfão `tools_bp` (166)

**Branch**: `166-rh-tools-bp-react` | **Date**: 2026-07-22 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/166-rh-tools-bp-react/spec.md`

## Summary

Segunda fatia da US6 (Cauda Administrativa) da migração 144. Duas partes independentes: (1)
migra a única rota real do blueprint `rh` (`GET /rh/dashboard`) para um endpoint JSON; (2)
executa a decisão FR-016 sobre o blueprint órfão `tools_bp` — **remoção definitiva** (não
migração), por duplicar de forma desatualizada a lógica já existente em
`app/orcamento/transport.py` e por nunca ter estado registrado em produção.

## Technical Context

Igual às fatias 145–165: Python/Flask + React (Vite/TS/TanStack Query). Sem dependência nova.
Verificação com test client Flask contra `manto_local`, requests fora de `app_context`.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **I (reutilizar)**: a remoção de `tools_bp` É a aplicação do Princípio I — elimina uma segunda
  implementação paralela da mesma lógica de cálculo de transporte, mantendo só a versão
  configurável em `app/orcamento/transport.py`.
- **II (padrões de código)**: endpoint novo em `app/api/rh_read.py`, type hints/docstring.
- **III (API first)**: 1 endpoint novo, 100% JSON (`GET /api/rh/dashboard`); a view Jinja
  `/rh/dashboard` continua existindo em paralelo, sem mudança de comportamento (FR-003).
- **IV (não quebrar)**: paridade verificada contra `manto_local` (mesma flag `can_manage_users`);
  confirma que remover `tools_bp` não afeta `app/orcamento/transport.py` nem `app/__init__.py`
  além de remover a linha de import/registro que nunca existiu (não há linha para remover — ver
  Design Decisions).
- **V (feedback)**: loading/erro/sucesso via TanStack Query na tela nova.
- **VIII (mobile-first)**: painel de RH segue mobile-first por princípio geral de UI.

Sem violação nova.

## Project Structure

### Documentation (this feature)

```text
specs/166-rh-tools-bp-react/
├── plan.md
├── data-model.md
├── quickstart.md
├── contracts/rh-endpoint.md
└── tasks.md
```

### Source Code (repository root)

```text
app/api/rh_read.py                     # NOVO — GET /api/rh/dashboard
app/api/__init__.py                    # + import de rh_read
frontend/apps/internal/src/
├── lib/rh.ts                          # NOVO — useRhDashboard()
└── pages/RhDashboardPage.tsx          # NOVO
App.tsx                                # + rota /rh
frontend/apps/internal/src/pages/DashboardPage.tsx  # + link condicional (permissão rh.view)
app/tools/                             # REMOVIDO (routes.py, __init__.py)
app/templates/tools/                   # REMOVIDO (transport_calculator.html)
scripts/db/verify_166_rh_tools_bp.py   # NOVO: paridade API×Jinja RH + RBAC 403 +
                                        #   confirma orçamento intacto após remoção de tools_bp
```

**Structure Decision**: RH segue o padrão de endpoint único simples (sem módulo `_ops` — a
"lógica" é só checar duas permissões, não vale a pena extrair). `tools_bp` não migra — é
removido; não há "estrutura nova" para ele.

## Design Decisions

1. **`GET /api/rh/dashboard`** (`app/api/rh_read.py`): gate `api_login_required` +
   `current_user.has_permission("rh.view")` (função inline, paridade com
   `require_permission("rh.view")` do Jinja) → 403 `{"error": {"message": "Sem permissão"}}` se
   negado. 200: `{"can_manage_users": bool}` (equivalente a `current_user.has_permission
   ("user.manage")`, mesmo campo passado ao template hoje).
2. **Remoção de `tools_bp`**: apagar `app/tools/routes.py`, `app/tools/__init__.py` (e a pasta,
   se ficar vazia), `app/templates/tools/transport_calculator.html`. Nenhuma linha em
   `app/__init__.py` precisa ser removida — confirmado que `tools_bp` nunca foi importado nem
   registrado ali (só existe o código morto dentro de `app/tools/`).
3. **`app/orcamento/transport.py` não é tocado** — módulo independente, sem import de/para
   `app/tools/`; verificado no script (chamada direta às funções de cálculo, sem depender de
   nada em `app/tools/`).

## Complexity Tracking

Nenhuma violação nova.
