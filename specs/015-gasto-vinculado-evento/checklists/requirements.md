# Specification Quality Checklist: Vincular gasto extra a um evento

**Created**: 2026-06-01
**Feature**: [spec.md](../spec.md)

## Content Quality
- [x] No implementation details (linguagem/framework/API)
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
- Continuação das features 004/005/013/014. Exige schema novo (gasto.event_id) → migration à mão.
- 2 decisões confirmadas (AskUserQuestion): (1) gasto aprovado abate do Lucro líquido do evento
  agora; (2) vincular gastos existentes é só super admin.
- Só gastos aprovados entram no evento/lucro; 1 gasto ↔ no máximo 1 evento.
