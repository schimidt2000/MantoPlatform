# Specification Quality Checklist: Controle de vendas, descontos e pagamentos recebidos

**Created**: 2026-06-12
**Feature**: [spec.md](../spec.md)

## Content Quality
- [x] No implementation details
- [x] Focused on user value and business needs
- [x] Written for non-technical stakeholders
- [x] All mandatory sections completed

## Requirement Completeness
- [x] No [NEEDS CLARIFICATION] markers remain
- [x] Requirements are testable and unambiguous
- [x] Success criteria are measurable
- [x] Success criteria are technology-agnostic
- [x] All acceptance scenarios are defined
- [x] Edge cases are identified
- [x] Scope is clearly bounded
- [x] Dependencies and assumptions identified

## Feature Readiness
- [x] All functional requirements have clear acceptance criteria
- [x] User scenarios cover primary flows
- [x] Feature meets measurable outcomes
- [x] No implementation details leak into spec

## Notes
- Política de cobrança: à vista, ou 50% no ato + 50% até 2 dias antes do evento.
- "Faturado" passa a usar a régua da data combinada (igual "futuro") — decisão registrada nas
  assumptions. Sem migration (sale_value_gross e payment_due_date já existem).
