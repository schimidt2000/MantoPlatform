# Implementation Plan: Comissão EducaManto + Padronização dos Orçamentos

**Branch**: `109-comissao-educamanto` | **Date**: 2026-07-06 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/109-comissao-educamanto/spec.md`

## Summary

Eventos com título começando com "(EDU" (case-insensitive) são EducaManto. A venda desses
eventos passa a gerar comissão para o **responsável EducaManto** (configuração nova
`site_settings.educamanto_seller_id`, backfill = Gabriel Lara), com ciclo de pagamento pelo
mês da **realização** do evento (coluna nova `commission_payments.payable_from`; a agregação
da planilha de pagamentos usa `COALESCE(payable_from, sale_date)`). O responsável ganha
acesso ao Pipeline de Vendas (filtrado a eventos EDU) e à tela de Comissões (só as dele),
sem papéis novos. O histórico do EducaManto é elevado ao padrão do histórico da calculadora
(coluna "Gerado por" + filtro por usuário para superadmin, filtros de período).

Comissões comuns não mudam: beneficiário = vendedor, ciclo = mês da venda
(`payable_from IS NULL` em todas as linhas existentes).

## Technical Context

**Language/Version**: Python 3.12 + Flask + SQLAlchemy (stack existente)

**Primary Dependencies**: nenhuma nova — reusa `CommissionPayment`, `_sync_commission_payment`,
`_resync_pending_commissions`, `_build_commission_items`, padrão de context processor
(`inject_revendedor_flag`) e de filtros do histórico da calculadora

**Storage**: PostgreSQL; 1 migration manual (`site_settings.educamanto_seller_id` FK users +
`commission_payments.payable_from` Date + backfill do responsável)

**Testing**: test client contra `manto_local` (requests fora de app_context), cobrindo:
comissão EDU vai ao responsável; ciclo pela realização (evento futuro não entra como pagável);
comissão comum inalterada; RBAC do pipeline/comissões (responsável vê só EDU; ENSAIO comum
403; COMERCIAL vê tudo); histórico EducaManto com autor/filtros

**Target Platform**: sistema interno (desktop-first); telas: pagamentos, comissões, pipeline,
históricos, configurações do admin

**Project Type**: web app Flask monolítico

**Performance Goals**: irrelevante — colunas nullable, COALESCE em query já pequena

**Constraints**: zero mudança de comportamento para comissões/eventos não-EDU (FR-005,
FR-008); linhas pagas de comissão nunca são alteradas; nenhuma mudança na sync do Google
Calendar

**Scale/Scope**: 1 migration; `app/constants.py` (prefixo); `app/models.py` (property +
2 colunas); `app/financeiro/routes.py` (beneficiário, payable_from, janela COALESCE, RBAC);
`app/calendar/routes.py` (estorno copia payable_from); `app/admin/routes.py` +
`admin_settings.html` (config responsável); `app/__init__.py` (context processor);
`base.html` (links); `app/educamanto/routes.py` + `educamanto/historico.html` (filtros/autor)

## Constitution Check

| Princípio | Avaliação |
|---|---|
| I. Reutilizar antes de criar | ✅ Reusa todo o pipeline de comissões (sync/resync/estorno/planilha); helper único `_commission_beneficiary`; padrão de context processor e de filtros do histórico existentes. |
| II. Padrões Python | ✅ Type hints + docstrings nos helpers novos; constante nomeada para o prefixo; nada de string mágica espalhada. |
| III. Camadas | ✅ Regra de beneficiário centralizada em helper no módulo financeiro (única fonte); rotas só orquestram. |
| IV. Não quebrar o que funciona | ✅ `payable_from IS NULL` ⇒ comportamento idêntico (COALESCE cai em `sale_date`); `require_vendas` só GANHA um caso; verificação cobre regressão de comissão comum explicitamente. |
| V. UI/UX + feedback | ✅ Config nova com descrição na tela do admin; histórico com filtros no padrão já conhecido; flash de sucesso já existente no save de settings. |
| VI. Planejar antes de codar | ✅ Este plano; fluxo de comissão rastreado linha a linha (routes.py 82–156, 913–956, 1004–1008). |
| VII. Moeda BR | ✅ Valores exibidos pelas telas existentes que já usam `format_brl`. |
| VIII. Mobile-first público | N/A — telas internas. |

**Gate: PASS.**

## Project Structure

### Documentation (this feature)

```text
specs/109-comissao-educamanto/
├── plan.md              # Este arquivo
├── research.md          # Fase 0 — decisões técnicas (R1–R7)
├── data-model.md        # Fase 1 — colunas novas + migration
├── quickstart.md        # Fase 1 — roteiro de verificação
├── contracts/
│   └── routes.md        # Fase 1 — contratos de rotas/regras alteradas
└── tasks.md             # Fase 2
```

### Source Code (repository root)

```text
migrations/versions/
└── e5f6a7b8c9d0_educamanto_commission.py   # manual; down_revision = c3d4e5f6a7b8

app/
├── constants.py                 # EDUCAMANTO_TITLE_PREFIX = "(EDU"
├── models.py                    # SiteSetting.educamanto_seller_id; CommissionPayment.payable_from;
│                                #   CalendarEvent.is_educamanto (property)
├── financeiro/routes.py         # _commission_beneficiary(); _is_educamanto_responsavel();
│                                #   require_vendas aceita responsável; _sync_commission_payment
│                                #   (beneficiário + payable_from); _build_commission_items (COALESCE);
│                                #   pipeline() filtra EDU p/ responsável-somente
├── calendar/routes.py           # _delete_event: estorno copia payable_from
├── admin/routes.py              # settings POST lê educamanto_seller_id; passa users ao template
├── __init__.py                  # context processor is_educamanto_responsavel
├── educamanto/routes.py         # historico(): filtros date_from/date_to/user_id + is_superadmin
└── templates/
    ├── admin_settings.html      # select "Responsável EducaManto"
    ├── base.html                # links Pipeline/Comissões: or is_educamanto_responsavel
    └── educamanto/historico.html # coluna "Gerado por" + filtros (padrão calculadora)
```

**Structure Decision**: nenhum blueprint/arquivo novo; mudanças pontuais nos módulos donos de
cada responsabilidade.

## Decisões de design (detalhe em research.md)

1. **Classificação por título, sem coluna** (R1): `"(EDU"` case-insensitive; título é a fonte
   da verdade — property no modelo + `ilike("(EDU%")` em query.
2. **Responsável configurável** (R2): `site_settings.educamanto_seller_id`, select na tela de
   settings do admin; backfill para Gabriel Lara na migration (idempotente).
3. **Beneficiário centralizado** (R3): `_commission_beneficiary(event, settings)` — EDU com
   responsável ⇒ responsável (sem exigir `seller_id`); senão vendedor. Pendentes reconciliam;
   pagas nunca mudam.
4. **Ciclo pela realização** (R4): `payable_from` = data do evento (só EDU); janela da
   planilha usa `COALESCE(payable_from, sale_date)`; estorno copia o campo.
5. **Acesso de menor privilégio** (R5): `require_vendas` aceita o responsável; pipeline
   filtrado a EDU quando ele não tem os papéis plenos; comissões já filtram por dono.
6. **Histórico padronizado** (R6): EducaManto sobe ao padrão da calculadora (autor + filtros,
   regras de visibilidade idênticas); calculadora intocada.
7. **Taxa** (R7): mesmas regras atuais (padrão 2,5% + override por evento).

## Complexity Tracking

Sem violações — tabela não aplicável.
