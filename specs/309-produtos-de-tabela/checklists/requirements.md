# Specification Quality Checklist: Produtos de tabela (Visita Mágica)

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-10-19
**Feature**: [spec.md](../spec.md)

## Content Quality

- [x] No implementation details (languages, frameworks, APIs) — os nomes de chave do JSON e de
      funções aparecem só onde são o contrato (bloco `produtos`, `quote.produtos`) ou a convenção da
      casa (`verify_309.py`, `Combobox`), como nas specs 305/307
- [x] Focused on user value and business needs
- [x] Written for non-technical stakeholders (histórias e critérios em linguagem do dono)
- [x] All mandatory sections completed

## Requirement Completeness

- [x] No [NEEDS CLARIFICATION] markers remain (as quatro dúvidas foram respondidas pelo dono em
      19/10 e estão em Clarifications)
- [x] Requirements are testable and unambiguous (FR-001…FR-021 com números e condições)
- [x] Success criteria are measurable (SC-001…SC-006)
- [x] Success criteria are technology-agnostic (valores ao cliente, tetos, eventos, telas)
- [x] All acceptance scenarios are defined (7 histórias, 1–4 cenários cada)
- [x] Edge cases are identified (faixa sem preço, dois exemplares, make do avulso, nomes do Google,
      coordenador abaixo do produto, bloco malformado, preço mudado depois da venda)
- [x] Scope is clearly bounded (Fora de escopo: markup por item, piso, 30 min, alias, recorte, #103)
- [x] Dependencies and assumptions identified (Premissas: markup 2,6, 2h–4h, label fixo, make, NF/PIX)

## Feature Readiness

- [x] All functional requirements have clear acceptance criteria (cada história cita os cenários do
      verify; FR mapeados em 1–20)
- [x] User scenarios cover primary flows (venda, teto, tabela, configuração, convivência, correção,
      neutralidade)
- [x] Feature meets measurable outcomes defined in Success Criteria
- [x] No implementation details leak into specification

## Notes

- Validada em 19/10/2026 na criação da spec. `/speckit-clarify` (19/10) fez 3 perguntas — produto
  sem preço na faixa (estimativa: cachê dobrado × markup 3,0), maquiagem inclusa, 2h–4h dos avulsos
  — todas respondidas e integradas (Clarifications, Casos de borda, FR-001/010/013/019, cenário 15,
  Premissas). Revalidada: 16/16 itens passando. Pronta para `/speckit-plan`.
- Feature numerada 309 porque a 308 foi alocada por outro chat (`308-casting-sem-compromisso-interno`)
  na árvore principal em 19/10 11:54; esta vive no worktree `C:\tmp\mp309`.
