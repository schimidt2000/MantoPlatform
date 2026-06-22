# Implementation Plan: Notas fiscais (069)

**Branch**: `069-notas-fiscais` | **Date**: 2026-06-22 | **Spec**: [spec.md](spec.md)

## Summary

Transformar a nota fiscal de campo único em **coleção de notas** por evento (valor + data + estado
+ arquivo). Vendas "com nota" sem arquivo viram **tarefa de emissão** para o super admin (subir
arquivo + marcar emitida conclui). Painel financeiro ganha **custo de nota por mês de emissão** com
detalhe por evento/nota. DRE/balanço **inalterada** (imposto por competência). **Migration manual.**

## Technical Context

**Language/Version**: Python 3.11, Flask + SQLAlchemy; Jinja2 + JS vanilla.

**Primary Dependencies**: nenhuma nova. Reusa `parse_brl`, `money-mask.js` (brl-input),
`UPLOAD_INVOICES`, `_get_tax_rate`, padrão de upload e de listas dinâmicas (parcelas/065).

**Storage**: PostgreSQL/SQLite. **Migration manual** (autogenerate quebrado): cria `event_invoices`
+ migra a nota única existente.

**Testing**: contra **`manto_local`** (Postgres). Ciclo: criar nota a emitir → tarefa do super
admin → emitir → custo por mês de emissão + detalhe; 2 notas em datas diferentes; DRE inalterada;
migração de evento legado preserva a nota. `ruff check` sem erros novos.

**Constraints**: máscara BR; pt-BR; não quebrar DRE/recebimentos; permissões existentes.

**Scale/Scope**: `models.py` (modelo + relationship), 1 migration, `calendar/routes.py`
(CRUD notas no comercial), `financeiro/routes.py` (rota emitir + custo de nota + dashboard),
templates `event_detail.html`, `financeiro/dashboard.html`, badge em `home.html`.

## Constitution Check

- **I. Reutilizar (NÃO-NEGOCIÁVEL)**: ✅ Reusa upload/máscara/lista dinâmica/`tax_rate`.
- **IV. Não quebrar (NÃO-NEGOCIÁVEL)**: ✅ DRE intacta; colunas antigas mantidas; migração preserva
  dados. Verificação em `manto_local`.
- **VII. Valores BR (NÃO-NEGOCIÁVEL)**: ✅ `brl-input` + `parse_brl`.
- **Migrations manuais**: ✅ escrita à mão (autogenerate quebrado).
- Demais princípios: ✅.

**Resultado**: PASS — com migration manual.

## Project Structure

```text
app/
├── models.py                          # + class EventInvoice; CalendarEvent.invoices
├── calendar/routes.py                 # _handle_update_comercial: CRUD das notas + flash divergência
├── financeiro/routes.py              # rota POST nf/<id>/emitir; custo de nota por mês de emissão;
│                                      #   "NF a emitir" por nota (tarefas)
├── templates/event_detail.html       # seção Dados de Venda: lista dinâmica de notas
├── templates/financeiro/dashboard.html # custo de nota do mês + detalhe + tarefas a emitir
└── templates/home.html               # badge de notas a emitir (superadmin/financeiro)
migrations/versions/
└── v8e9f0a1b2c3_event_invoices.py    # cria event_invoices + migra nota única (065)
```

**Structure Decision**: Coleção de notas + tarefa de emissão + relatório de caixa, sem tocar na DRE.

## Complexity Tracking

> Sem violações. Migration manual conforme política do projeto.
