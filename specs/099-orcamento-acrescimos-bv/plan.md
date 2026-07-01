# Implementation Plan: Acréscimos tipados com BV (repasse) e pagamento por PIX

**Branch**: `099-orcamento-acrescimos-bv` | **Date**: 2026-07-01 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/099-orcamento-acrescimos-bv/spec.md`

## Summary

Substituir o acréscimo único do orçamento por **acréscimos tipados** (lista fixa + **BV** + Outro), cada
um em **R$ ou %**. No nível do **evento**, os acréscimos viram uma coleção; o **BV** recebe tratamento
financeiro especial: **desconta do lucro**, **sai da base de comissão** e vira um **item na planilha de
pagamentos** com **PIX/nome do recebedor** (informados na tela comercial do evento). O BV é **embutido no
total** e nunca rotulado ao cliente.

Ponto central: um helper `_event_bv_total(event)` (soma dos acréscimos BV em R$) usado no cálculo de
comissão (`sale_value − bv_total`), no lucro (subtrai `bv_total`) e como fonte de item de pagamento.

## Technical Context

**Language/Version**: Python 3.x (Flask), SQLAlchemy, Jinja2, JS vanilla

**Primary Dependencies**: Flask, Flask-Migrate (Alembic). Sem dependência nova.

**Storage**: PostgreSQL (prod)/SQLite (dev). Nova tabela `event_acrescimos` (migração manual,
down_revision `c5f6a7b8d9e0`). Campo `acrescimo_value` legado é preservado. Testar contra `manto_local`.

**Testing**: pytest/scripts contra `manto_local`. Casos: soma de acréscimos (R$ e %); `bv_total`;
comissão exclui BV; lucro desconta BV; BV na planilha de pagamentos; BV oculto na proposta.

**Target Platform**: Web (comercial + financeiro)

**Project Type**: Web app (monolito Flask + Jinja2 + JS)

**Constraints**: Não regredir eventos/orçamentos sem BV nem o acréscimo legado. BV nunca rotulado ao
cliente. Percentual incide sobre o total pré-acréscimos no orçamento; no evento, `amount_brl` é congelado
no save. Reusar a planilha de pagamentos existente.

**Scale/Scope**: 1 modelo novo + migração; helpers de finança; editor de acréscimos no orçamento (JS) e na
tela comercial do evento; item de BV na planilha de pagamentos.

## Constitution Check

- **Sem duplicação**: um único helper `_event_bv_total` alimenta comissão, lucro e pagamento; o editor de
  acréscimos é um componente reutilizado (orçamento + evento). ✅
- **Separação de responsabilidades**: modelo/serviço de finança separados da view; snapshot do orçamento
  transporta dados sem lógica. ✅
- **Migração manual** conforme padrão; sem segredos novos. ✅
- **Não quebrar o que funciona**: `acrescimo_value` legado tratado como acréscimo comum; BV opcional. ✅

Resultado: PASS.

## Data Model

**`EventAcrescimo`** (tabela `event_acrescimos`):

| Campo | Tipo | Notas |
|-------|------|-------|
| id | int PK | |
| event_id | FK(calendar_events) | cascade delete |
| tipo | str(40) | ex.: "Taxa de urgência", "BV", "Outro" |
| descricao | str(200) nullable | usado quando tipo = "Outro" |
| is_percent | bool | valor em % (senão R$) |
| value | Numeric(12,2) | número informado (R$ ou % base) |
| amount_brl | Numeric(12,2) | **valor efetivo em R$** congelado no save (fonte da finança) |
| is_bv | bool | True para o tipo BV |
| bv_recipient | str(200) nullable | nome de quem recebe o BV |
| bv_pix | str(140) nullable | PIX de quem recebe o BV |
| bv_payment_status | str(20) default "nao_pago" | status na planilha de pagamentos |
| created_at | DateTime | |

`CalendarEvent`: relationship `acrescimos` (cascade). `acrescimo_value` legado permanece (acréscimo
comum, não-BV). Lista fixa de tipos + BV + Outro em `app/orcamento/constants` (ou `constants.py`).

## Implementation Approach (phased)

1. **Modelo + migração** (`EventAcrescimo`, relationship, tabela).
2. **Finança**: `_event_bv_total(event)`; `_event_commission` usa `sale_value − bv_total`; lucro no
   `event_detail` e no dashboard subtrai `bv_total`; `_sync_commission_payment` já passa a excluir BV via
   `_event_commission`.
3. **Planilha de pagamentos**: gerar itens de BV (por evento com BV no mês), com recebedor/PIX/valor/
   status; endpoint set-status atualiza `bv_payment_status`; BV sem PIX sinalizado "pendente de dados".
4. **Tela comercial do evento**: editor de acréscimos (add/remover, tipo, valor, R$/%); quando há BV,
   campos PIX/nome; `_handle_update_comercial` persiste acréscimos + BV e recomputa `amount_brl`.
5. **Orçamento**: UI "Adicionar acréscimo" repetível (substitui o acréscimo único); cálculo soma todos
   (percentuais sobre o total pré-acréscimos); snapshot guarda a lista; mensagem/PDF **não** rotulam BV.
6. **Criar evento a partir do orçamento**: cria `EventAcrescimo` a partir do snapshot.
7. **Verificação** contra `manto_local`: números de comissão/lucro com e sem BV; item de BV na planilha;
   proposta sem "BV".

## Project Structure

```text
app/
├── models.py                    # EventAcrescimo + relationship; (acrescimo_value legado mantido)
├── constants.py                 # ACRESCIMO_TIPOS (lista fixa + BV + Outro)
├── financeiro/routes.py         # _event_bv_total; comissão exclui BV; lucro/dashboard subtrai BV;
│                                #   itens de BV na planilha + set-status
├── calendar/routes.py           # _handle_update_comercial: acréscimos + BV/PIX; profit no event_detail;
│                                #   criação a partir do orçamento cria EventAcrescimo
├── orcamento/routes.py          # cálculo de múltiplos acréscimos + snapshot
├── templates/
│   ├── event_detail.html        # editor de acréscimos + campos BV (PIX/nome)
│   ├── orcamento/index.html     # UI repetível de acréscimos
│   └── financeiro/pagamentos.html # linha(s) de BV
└── static/js/orcamento.js       # cálculo client-side de múltiplos acréscimos

migrations/versions/
└── <hash>_event_acrescimos.py   # nova tabela (down_revision c5f6a7b8d9e0)
```

**Structure Decision**: Mantém a arquitetura atual. O BV é modelado como um tipo de acréscimo com
tratamento financeiro especial, concentrado num helper único, e reaproveita a planilha de pagamentos
existente para o repasse.

## Complexity Tracking

> Sem violações de constituição. Complexidade de *integração financeira* mitigada por um único helper de
> BV e por congelar `amount_brl` no save (evita recomputar bases percentuais na finança).
