# Implementation Plan: Vincular gasto extra a um evento

**Branch**: `015-gasto-vinculado-evento` | **Date**: 2026-06-01 | **Spec**: [spec.md](./spec.md)

## Summary

Adicionar um vínculo opcional `event_id` ao gasto extra. No formulário, buscar eventos por data e
selecionar. Gastos **aprovados** vinculados aparecem na página do evento (área financeira) e abatem
do "Lucro líquido" (venda − cachês − gastos extras). Super admin pode vincular/alterar/remover o
evento de gastos já existentes (organizar o passado). Migration **à mão** (autogenerate quebrado).

## Technical Context

**Language/Version**: Python 3.11+ (Flask, SQLAlchemy, Jinja2), JS vanilla.
**Storage**: nova coluna `special_expenses.event_id` (FK nullable → calendar_events) + índice.
Migration escrita à mão (down_revision = head atual `d9e0f1a2b3c4`).
**Constraints**: vínculo opcional; só aprovado entra no evento/lucro; editar vínculo existente só
super admin (servidor + UI); demais fluxos intactos.
**Scale/Scope**: model + migration; rota `novo` (lê event_id) + API eventos-por-data + rota
vincular (super admin); event_detail (total + lista); templates gastos/index e event_detail.

## Constitution Check

- **I. Reutilizar antes de criar** ✅ — reaproveita SpecialExpense, a página de gastos e a área
  financeira do evento; adiciona só um vínculo.
- **II. Padrões Python** ✅ — funções pequenas; query de aprovados-por-evento reutilizável.
- **III. Camadas** ✅ — vínculo/validação nas rotas; exibição nos templates.
- **IV. Não quebrar** ✅ — coluna nullable (gastos atuais ficam sem vínculo); migration aditiva;
  Lucro só muda quando há gastos aprovados; verificação no app.
- **V. UI/UX (pt-BR)** ✅ — busca por data clara; lista discreta no evento; edição só p/ super admin.
- **VI. Planejar antes de codar** ✅ — este plano; 2 decisões confirmadas com o usuário.
- **Migration à mão** ✅ (autogenerate quebrado — memória do projeto).

## Project Structure

```text
app/
├── models.py                       # SpecialExpense.event_id (FK nullable) + relationship event
├── gastos/routes.py                # novo: lê event_id opcional; API /gastos/api/eventos?date=;
│                                   #   POST /gastos/<id>/vincular-evento (super admin)
├── calendar/routes.py              # event_detail: total + lista de gastos aprovados do evento
├── templates/
│   ├── gastos/index.html           # form: buscar evento por data + select; lista: coluna Evento
│   │                               #   + editor inline (super admin)
│   └── event_detail.html           # KPI "Gastos extras" + lista; Lucro abate gastos aprovados
└── migrations/versions/
    └── e0f1a2b3c4d5_gasto_event_id.py   # add_column event_id + índice (à mão)
```

## Design Detalhado

### 1. Model + Migration
- `SpecialExpense.event_id = db.Column(db.Integer, db.ForeignKey("calendar_events.id"), nullable=True)`
  + `event = db.relationship("CalendarEvent", foreign_keys=[event_id], lazy=True)`.
- Migration `e0f1a2b3c4d5` (down_revision `d9e0f1a2b3c4`): `add_column` + `create_index`
  `ix_special_expenses_event_id`. `downgrade` remove ambos.

### 2. Buscar eventos por data (API)
- `GET /gastos/api/eventos?date=YYYY-MM-DD` (qualquer autenticado): retorna eventos cuja data
  (start_at/coalesce) cai no dia → `[{id, label}]` com label = "HH:MM · Título". Usado pelo form e
  pelo editor inline.

### 3. Criar gasto com vínculo (`novo`)
- Ler `event_id` (opcional). Se informado e numérico, validar que o `CalendarEvent` existe; senão
  ignora (sem vínculo). Setar `expense.event_id`. Resto inalterado (NF obrigatória etc.).

### 4. Vincular gasto existente (super admin)
- `POST /gastos/<id>/vincular-evento`: `_is_superadmin()` senão 403. Lê `event_id` ("" = remover).
  Valida existência; atualiza; `_log` da ação; commit; redirect para a lista.

### 5. Página do evento (event_detail)
- Na rota: `event_expenses = SpecialExpense.query.filter_by(event_id=event.id, status="aprovado")...`
  e `event_expenses_total = sum(amount)`. Passar ambos ao template.
- Template (área `show_financeiro`): novo KPI "Gastos extras" = total; **Lucro líquido** passa a
  `venda − event_cost − event_expenses_total`. Abaixo, lista curta dos gastos (descrição, valor,
  link da Nota Fiscal). Tudo sob `show_financeiro`.

### 6. Lista de gastos (gastos/index.html)
- Form: bloco opcional "Vincular a evento": input `date` (event_search_date) + `select` (event_id)
  populado via API ao mudar a data (JS). Opção vazia = sem vínculo.
- Lista: coluna "Evento" mostra o evento vinculado (título/data) ou "—". Para super admin, um botão
  "Vincular/Alterar" revela um mini-editor inline (date + select via API + salvar →
  `vincular-evento`). JS genérico por linha (data-attrs com o id do gasto).

### Verificação (app real)
- Migration aplica (`flask db upgrade`) e `flask db downgrade` volta.
- Criar gasto com evrento (busca por data) → vínculo gravado.
- Aprovar → aparece no evento + Lucro abate; pendente/rejeitado → não aparece/afeta.
- Super admin vincula gasto antigo a evento passado; não-admin → 403 no endpoint.

### Fora de escopo
- Alterar o balanço financeiro global por período (dashboard) — segue como está.
- Vincular um gasto a múltiplos eventos; ratear um gasto entre eventos.
- Editar outros campos do gasto além do vínculo de evento.
