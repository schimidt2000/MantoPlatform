# Implementation Plan: Página de Gastos Especiais

**Branch**: `004-gastos-especiais` | **Date**: 2026-05-29 | **Spec**: [spec.md](./spec.md)

## Summary

Novo módulo `gastos`: model `SpecialExpense`, blueprint `/gastos` (lista + criação aberta a
qualquer usuário; aprovar/rejeitar só super admin), upload de comprovante, e integração ao
dashboard financeiro (gastos **aprovados** abatem o lucro líquido do mês da data do gasto).
Reaproveita helpers de BRL (`_parse_brl`/`_fmt_brl`), o padrão de upload e a rota
`/uploads/<path>` existentes.

## Technical Context

**Language/Version**: Python 3.11+ (Flask + SQLAlchemy)
**Storage**: SQLite/PostgreSQL — **nova tabela** `special_expenses` (migration Alembic obrigatória).
**Primary Dependencies**: Flask, SQLAlchemy, Flask-Migrate (nada novo).
**Uploads**: nova pasta `instance/uploads/expenses/`, servida pela rota `/uploads/<path>` já existente.
**Testing**: verificação manual no app real.
**Constraints**: valores em R$ (pt-BR); só aprovado conta; aprovar = super admin; sem regressão no financeiro.

## Constitution Check

- **I. Reutilizar antes de criar** ✅ — reusa `_parse_brl`/`_fmt_brl` do financeiro, o padrão de
  upload (`secure_filename` + dir) e a rota `/uploads/<path>`; reusa `AuditLog` para o log.
- **II. Padrões Python** ✅ — model tipado, rotas pequenas, funções com docstring; constantes
  (categorias/status) no topo do módulo.
- **III. Arquitetura em camadas** ✅ — novo blueprint isolado; a query de impacto no balanço
  fica no financeiro (consumidor), o módulo gastos não conhece o financeiro.
- **IV. Não quebrar o que funciona** ✅ — migration aditiva (nova tabela, não altera existentes);
  dashboard só ganha uma linha; branch isolado; verificação no app.
- **V. UI/UX (pt-BR)** ✅ — página com estado vazio, confirmação em exclusão, feedback de
  sucesso/erro, valores R$; variáveis CSS.
- **VI. Planejar antes de codar** ✅ — este plano.

**Sem violações.** (Migration é exigência da constituição quando `models.py` muda — será criada.)

## Project Structure

```text
app/
├── models.py                       # + class SpecialExpense
├── config.py                       # + UPLOAD_EXPENSES
├── __init__.py                     # registra gastos_bp; cria pasta de upload
├── gastos/
│   ├── __init__.py
│   └── routes.py                   # gastos_bp: lista, criar, aprovar, rejeitar, excluir
├── financeiro/
│   └── routes.py                   # dashboard(): soma gastos aprovados do mês -> lucro_liquido
└── templates/
    ├── gastos/
    │   └── index.html              # lista + formulário de novo gasto
    ├── financeiro/dashboard.html   # + linha "Gastos Extras"
    └── base.html                   # + item de menu "Gastos Extras"
migrations/versions/
└── xxxx_special_expenses.py        # nova tabela (flask db migrate)
```

## Design Detalhado

### 1. Model `SpecialExpense` (`special_expenses`)
- `id`, `description` (String 200, req), `category` (String 30), `amount` (Numeric(10,2), req),
  `expense_date` (Date, req — competência), `receipt_path` (String 300, null),
  `status` (String 20, default "pendente": pendente|aprovado|rejeitado),
  `created_by_id` (FK users), `created_at` (DateTime),
  `approved_by_id` (FK users, null), `approved_at` (DateTime, null), `notes` (Text, null — motivo).
- Relationships: `created_by`, `approved_by` (User). Propriedade `amount_brl` (formatada).
- Constantes no módulo: `CATEGORIES = ["Figurino","Escritório","Marketing","Manutenção","Outros"]`,
  `STATUSES`.

### 2. Blueprint `gastos_bp` (`/gastos`)
- `GET /gastos/` — lista (qualquer autenticado): gastos ordenados por data desc, totais
  (pendente/aprovado), flag `is_superadmin` para mostrar ações.
- `POST /gastos/novo` — cria (qualquer autenticado): valida valor via `_parse_brl`; salva
  comprovante (se enviado) em `UPLOAD_EXPENSES`; status "pendente"; AuditLog "create".
- `POST /gastos/<id>/aprovar` — **super admin**: status "aprovado" + approved_by/at; AuditLog.
- `POST /gastos/<id>/rejeitar` — **super admin**: status "rejeitado" + motivo (notes); AuditLog.
- `POST /gastos/<id>/excluir` — autor (se pendente) ou super admin.
- Decorator/checagem de super admin reaproveitando o padrão de RoleName.

### 3. Integração financeira (`financeiro/routes.py::dashboard`)
- Somar `SpecialExpense` com `status="aprovado"` e `expense_date` dentro do mês → `gastos_extras_mes`.
- `lucro_liquido = lucro_bruto - comissoes_mes - salarios_mes - gastos_extras_mes`.
- Passar `gastos_extras_mes` ao template; `dashboard.html` ganha a linha "Gastos Extras".

### 4. Upload
- `UPLOAD_EXPENSES = instance/uploads/expenses`; criado no factory (`os.makedirs`).
- Salvar com nome único (timestamp + secure_filename); `receipt_path` guarda caminho relativo
  `expenses/<arquivo>`, exibido via `/uploads/expenses/<arquivo>`.

### 5. Menu
- Item "Gastos Extras" no `base.html` para qualquer autenticado.

### 6. Migration
- `flask db migrate -m "special expenses"` + `flask db upgrade` (cria `special_expenses`).

### Acesso
- Lista + criar: qualquer usuário autenticado (a empresa toda anota).
- Aprovar/rejeitar: somente `SUPERADMIN`.
- Painel financeiro: segue restrito a Financeiro/Super admin.

### Fora de escopo
- Edição de gasto já aprovado; relatórios/exportação dedicados; categorias configuráveis em tela.
