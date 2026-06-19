# Implementation Plan: NF futura e parcelas com datas + recebimentos no painel

**Branch**: `065-comercial-datas-futuras` | **Date**: 2026-06-19 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/065-comercial-datas-futuras/spec.md`

## Summary

Permitir registrar, nos dados comerciais de um evento, um **cronograma de parcelas** (data +
valor cada) e a **data prevista de emissão da NF**; e mostrar no painel financeiro duas visões
informativas — **Recebimentos previstos** (parcelas por data) e **NF a emitir** —, **sem alterar
o reconhecimento de receita** (que segue pela data do evento). Requer modelo novo +
`invoice_due_date` → **migration manual** (head `s5b6c7d8e9f0`).

## Technical Context

**Language/Version**: Python 3.11, Flask + SQLAlchemy; Jinja2 + HTML/CSS/JS vanilla.

**Primary Dependencies**: Nenhuma nova. Reusa `parse_brl` (máscara BR), o handler comercial e o
filtro de período do dashboard.

**Storage**: PostgreSQL (prod) / SQLite (dev). **Migration manual** (autogenerate quebrado):
nova tabela `event_installments` + coluna `calendar_events.invoice_due_date`.

**Testing**: Verificação contra **`manto_local` (Postgres)**: aplicar migration, salvar parcelas
+ NF num evento, conferir persistência e as visões do painel; receita do período inalterada.

**Target Platform**: App web (Railway), mobile-first.

**Project Type**: Web application (monolito Flask).

**Constraints**: Não alterar o DRE/reconhecimento (decisão do cliente); não quebrar métodos de
pagamento e comprovantes atuais; valores em BR; pt-BR.

**Scale/Scope**: `models.py` (+EventInstallment, +invoice_due_date), 1 migration, `calendar/
routes.py` (`_handle_update_comercial`), `financeiro/routes.py` (`dashboard`),
`event_detail.html` (form de parcelas + data NF) e `financeiro/dashboard.html` (visões).

## Constitution Check

- **I. Reutilizar antes de criar (NÃO-NEGOCIÁVEL)**: ✅ Reusa `parse_brl`, o handler comercial
  único e o período do dashboard. Modelo novo só onde necessário (cronograma de parcelas).
- **II. Padrões Python**: ✅ Modelo pequeno tipado; handler estende o existente.
- **III. Arquitetura em camadas**: ✅ Persistência na rota; visões montadas na rota e exibidas no
  template.
- **IV. Não quebrar o que funciona (NÃO-NEGOCIÁVEL)**: ✅ DRE intacto; métodos/comprovantes
  atuais inalterados; migration aditiva. Verificação no `manto_local`.
- **V. UI/UX consistente (pt-BR)**: ✅ Cronograma claro (data+valor), aviso de divergência
  informativo; visões do painel com totais.
- **VI. Planejar antes de codar**: ✅ Este plano + research + data-model.
- **VII. Valores monetários BR (NÃO-NEGOCIÁVEL)**: ✅ Parcelas/valores via `parse_brl` e `brl`.

**Resultado**: PASS — migration aditiva, sem violações.

## Project Structure

### Documentation (this feature)

```text
specs/065-comercial-datas-futuras/
├── plan.md  spec.md  research.md  data-model.md  quickstart.md
├── contracts/recebimentos.md
└── checklists/requirements.md
```

### Source Code (repository root)

```text
app/
├── models.py                 # + class EventInstallment; + CalendarEvent.invoice_due_date + relação installments
├── calendar/routes.py        # _handle_update_comercial: ler invoice_due_date + recriar parcelas (parcelado_datas)
├── financeiro/routes.py      # dashboard: recebimentos_previstos + nf_a_emitir (informativos)
└── templates/
    ├── event_detail.html      # método "Parcelado (datas)" + lista dinâmica (data/valor) + data de emissão NF
    └── financeiro/dashboard.html  # seções "Recebimentos previstos" e "NF a emitir"
migrations/versions/
└── t6c7d8e9f0a1_event_installments_invoice_due_date.py  # manual; down_revision s5b6c7d8e9f0
```

**Structure Decision**: Monolito Flask. Modelo novo + migration manual; reuso do handler
comercial e do período do painel. Receita reconhecida segue inalterada.

## Complexity Tracking

> Sem violações de constituição. Migration manual é a norma do projeto (autogenerate quebrado).
