# Specification Quality Checklist: 303 — o sync não apaga evento com venda

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-09-29
**Feature**: [spec.md](../spec.md)

## Content Quality

- [x] No implementation details (languages, frameworks, APIs)
- [x] Focused on user value and business needs
- [x] Written for non-technical stakeholders
- [x] All mandatory sections completed

## Requirement Completeness

- [x] No [NEEDS CLARIFICATION] markers remain
- [x] Requirements are testable and unambiguous
- [x] Success criteria are measurable
- [x] Success criteria are technology-agnostic (no implementation details)
- [x] All acceptance scenarios are defined
- [x] Edge cases are identified
- [x] Scope is clearly bounded
- [x] Dependencies and assumptions identified

## Feature Readiness

- [x] All functional requirements have clear acceptance criteria
- [x] User scenarios cover primary flows
- [x] Feature meets measurable outcomes defined in Success Criteria
- [x] No implementation details leak into specification

## Notes

- O template da Manto (adaptado em 08/09) pede de propósito o nome das entidades, o gate de RBAC e
  a tabela do verify: esses nomes (`CalendarEvent`, `Notification`, `POST`) não contam como
  vazamento de implementação. Onde o estado "sumiu" mora ficou explicitamente para o plan.
- 29/09, respostas do dono incorporadas: portal com "Evento em confirmação — entre em contato com
  a produção" (FR-022); aviso marcante = faixa no topo + sino para Superadmin e Comercial
  (FR-009/010); devolução do dinheiro dentro da decisão (FR-013/014); comissão sobre o retido (D14)
  nesta feature (FR-016 a FR-021), absorvendo a correção 224g do plano.
- Candidato ao `/speckit-clarify`: a premissa do EducaManto cancelado (taxa EDU sobre o retido, sem
  descontar cachês). *(Resolvido no clarify: comissão proporcional ao retido.)*
- **30/09 — spec dividida em três entregas por decisão do dono, antes do plan.** A 303 ficou com a
  trava do sync (Histórias 1, 2, 3 na parte "devolver", 5 e 6); dinheiro do cancelamento e
  sinalização de cancelados foram para `entregas-2-e-3-rascunho.md`. A spec reescrita foi revalidada
  contra esta lista: 16/16. A coluna da marca deixou de ser "decisão do plan" (é
  `google_missing_since`); os requisitos FR-039 a FR-045 vieram da pesquisa do plano.
