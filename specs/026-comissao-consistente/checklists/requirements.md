# Specification Quality Checklist: Comissão consistente entre as telas

**Created**: 2026-06-04
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
- Causa: comissão a pagar foi gravada a 2%; padrão virou 2,5% (feat 023) e o gravado não re-sincronizou.
- Fix: reconciliar comissões a pagar com o cálculo ao vivo (reaproveita _sync_commission_payment).
  Pagas preservadas; estornos intactos. Sem migration.
