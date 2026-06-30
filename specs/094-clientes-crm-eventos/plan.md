# Implementation Plan: Clientes (CRM) — base Kommo, associação a eventos e ecossistema de marketing

**Branch**: `094-clientes-crm-eventos` | **Date**: 2026-06-29 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/094-clientes-crm-eventos/spec.md`

## Summary

Introduzir uma entidade **Cliente** (chave única = telefone normalizado), importar a base do Kommo
(`kommo_export_leads_2026-06-29.csv`, deduplicando por telefone), permitir **associar/criar um cliente
em cada evento** na seção "Dados de Venda", **exigir cliente ao salvar dados de venda** de eventos a
partir da ativação (grandfathering para passados; sync do Google não bloqueado) e entregar um
**ecossistema** com lista de clientes e ficha por cliente (eventos, datas, totais, metadados de
marketing).

Abordagem: modelo novo `Client` + FK `client_id` em `CalendarEvent` (migration manual — autogenerate
está quebrado por drift, ver memória), comando CLI de importação idempotente, blueprint `clientes_bp`
para lista/ficha/criação/busca, e enxerto no handler comercial existente
(`_handle_update_comercial`) para associação + validação obrigatória.

## Technical Context

**Language/Version**: Python 3.x, Flask, SQLAlchemy, Jinja2, JS vanilla

**Primary Dependencies**: Flask-Login (RBAC via `current_user.roles`), Flask-Migrate (Alembic),
biblioteca padrão `csv` (sem dependência nova)

**Storage**: PostgreSQL (prod) / SQLite (dev). Nova tabela `clients` + coluna `calendar_events.client_id`
(FK nullable). **Testar contra `manto_local` (Postgres)**, não SQLite (regra do CLAUDE.md).

**Testing**: pytest contra `manto_local`. Casos-chave: normalização de telefone, dedup/idempotência da
importação, validação de obrigatoriedade no save comercial, totais da ficha do cliente.

**Target Platform**: Web (área comercial/financeiro/admin)

**Project Type**: Web application (monolito Flask com blueprints + templates Jinja2)

**Performance Goals**: Importar ~6,5 mil linhas em uma execução de comando sem erro; buscas de cliente
respondem instantaneamente para o vendedor (índice em telefone e nome).

**Constraints**: Migration **manual** (autogenerate quebrado). Não bloquear o sync do Google Calendar.
Normalização de telefone consistente entre importação, criação inline e busca. Sem secrets novos.

**Scale/Scope**: ~6,5k linhas no CSV → alguns milhares de clientes únicos por telefone. 1 modelo novo,
1 FK, 1 comando CLI, 1 blueprint (3-4 rotas), ~3 templates, enxertos em event_detail + handler comercial.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Separação de responsabilidades**: lógica de normalização/dedup e importação isolada em um módulo de
  serviço (`app/clientes/service.py` ou `importer.py`); rotas só orquestram. ✅
- **Sem duplicação**: reutiliza `phone_digits`/normalização já existente em `Talent` se aplicável;
  reutiliza RBAC e o handler comercial existente em vez de criar fluxo paralelo. ✅
- **Type hints + docstrings** nas funções novas (Google style). ✅
- **Migration manual** conforme memória (autogenerate quebrado). ✅
- **Sem segredos hardcoded**; caminho do CSV é argumento do comando. ✅
- **Não quebrar o que funciona**: FK nullable, obrigatoriedade só no save comercial e só para eventos a
  partir da ativação. ✅

Resultado: PASS. Sem violações a justificar.

## Project Structure

### Documentation (this feature)

```text
specs/094-clientes-crm-eventos/
├── spec.md
├── plan.md
├── tasks.md
└── checklists/
    └── requirements.md
```

### Source Code (repository root)

```text
app/
├── models.py                         # ADD: class Client; ADD CalendarEvent.client_id + relationship
├── clientes/
│   ├── __init__.py                   # NEW blueprint package
│   ├── routes.py                     # NEW clientes_bp: lista, ficha, criar, buscar (JSON p/ autocomplete)
│   └── importer.py                   # NEW: normalize_phone(), import_kommo_csv() (dedup/idempotente)
├── calendar/routes.py                # EDIT _handle_update_comercial: associar client + validar obrigatório
├── cli.py                            # EDIT register_commands: comando "import-kommo-clients <path>"
├── __init__.py                       # EDIT: register clientes_bp
└── templates/
    ├── event_detail.html             # EDIT "Dados de Venda": seletor/criação de cliente
    └── clientes/
        ├── list.html                 # NEW lista pesquisável
        ├── detail.html               # NEW ficha do cliente (eventos, datas, totais, marketing)
        └── _form.html (ou inline)    # NEW form de criação (página e/ou modal no evento)

migrations/versions/
└── <hash>_clientes_e_event_client_fk.py   # NEW migration manual (down_revision: a3d4e5f6a7b8)
```

**Structure Decision**: Segue o padrão de blueprints do projeto (como `financeiro`, `figurino`). A
entidade Cliente ganha módulo próprio `app/clientes/` com `routes.py` + `importer.py` (serviço puro de
normalização/dedup/import, sem HTTP). A obrigatoriedade e a associação reutilizam o handler comercial
existente em `app/calendar/routes.py` para não criar um segundo fluxo de salvamento de venda.

## Data Model

**`Client`** (tabela `clients`):

| Campo | Tipo | Notas |
|-------|------|-------|
| id | int PK | |
| name | str(200) | de "Nome completo" |
| phone | str(20) **unique, index** | telefone normalizado (só dígitos) — chave de identidade |
| phone_display | str(30) nullable | telefone como exibir (formatado), opcional |
| email | str(200) nullable | quase sempre vazio no CSV |
| company | str(200) nullable | |
| source | str(20) | `kommo_import` \| `manual` |
| kommo_lead_id | str(40) nullable | rastreabilidade (lead mais recente do telefone) |
| responsible | str(120) nullable | "Usuário responsável" |
| tags | str(300) nullable | "Tags" agregadas |
| lead_stage | str(120) nullable | "Etapa do lead" mais recente |
| funnel | str(120) nullable | "Funil de vendas" |
| lead_value | Numeric(12,2) nullable | "Lead venda R$" (agregado/maior) |
| kommo_created_at | DateTime nullable | "Criado em" |
| notes | Text nullable | |
| created_at / updated_at | DateTime | padrão do projeto |
| events | relationship → CalendarEvent | backref `client` |

**`CalendarEvent`**: `client_id = FK(clients.id, nullable=True)`, índice em `client_id`; relationship
`client`. Nullable garante grandfathering dos passados.

## Implementation Approach (phased)

1. **Modelo + migration manual** (US1/US2 base): `Client` + `CalendarEvent.client_id`. Migration manual
   `down_revision = "a3d4e5f6a7b8"`, criando tabela `clients` (com unique em `phone`) e a coluna FK.
2. **Serviço de importação** (`importer.py`): `normalize_phone(raw) -> str|None` (strip não-dígitos,
   valida tamanho mínimo) e `import_kommo_csv(path) -> ImportReport` (dedup por telefone, idempotente,
   agrega metadados). Comando CLI `import-kommo-clients`.
3. **Associação no evento** (US1): UI na seção "Dados de Venda" (buscar/selecionar + criar inline via
   rota JSON); enxerto em `_handle_update_comercial` para setar `event.client_id` (e criar/reaproveitar
   por telefone).
4. **Obrigatoriedade** (US3): no `_handle_update_comercial`, se evento elegível (start_at ≥ data de
   ativação) e sem `client_id` → `flash(erro)` e abortar o save comercial preservando o form. Sync do
   Google não passa por esse handler, então não é afetado.
5. **Ecossistema** (US4): `clientes_bp` com lista pesquisável e ficha (eventos associados, datas,
   totais), restrito a COMERCIAL/FINANCEIRO/SUPERADMIN; link no menu da área comercial.
6. **Testes** contra `manto_local`: normalização, dedup/idempotência, validação obrigatória, totais.

## Constraints & Risks

- **Qualidade do CSV**: nomes ruidosos (ex.: "evaristodesantanafilho"), "Pessoa de contato" = empresa.
  Mitigação: nome de "Nome completo"; telefone como verdade.
- **Drift de migration**: escrever manualmente; rodar `flask db upgrade` contra `manto_local` para
  validar antes de mergear.
- **Data de ativação**: usar a data de deploy (constante/registro), comparando com `start_at` do evento
  para decidir obrigatoriedade — documentado na spec (Assumptions).

## Complexity Tracking

> Sem violações de constituição. Nenhuma complexidade extra a justificar.
