# Specification Quality Checklist: Feature 297 — vídeo leve com moldura, menu na tag NFC e recado da cliente

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-09-09
**Feature**: [spec.md](../spec.md)

## Content Quality

- [x] No implementation details (languages, frameworks, APIs) — *com a exceção deliberada do
  template da Manto: as seções "RBAC" e "Verificação" existem justamente para nomear endpoints e
  arquivos (constituição, Princípios VIII e XIII). Histórias, requisitos e critérios de sucesso
  ficaram livres de tecnologia, salvo FR-001, que precisa nomear o formato do vídeo para ser
  testável.*
- [x] Focused on user value and business needs
- [x] Written for non-technical stakeholders — *o diagnóstico foi escrito em termos de peso e de
  "a cliente não consegue carregar", não de codec.*
- [x] All mandatory sections completed

## Requirement Completeness

- [x] No [NEEDS CLARIFICATION] markers remain — *as decisões abertas viraram Premissas; as cinco
  primeiras foram confirmadas pelo dono na sessão de clarify de 09/09.*
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
- [x] No implementation details leak into specification — *ver a ressalva do primeiro item.*

## Portões da Manto *(conferidos no fim da implementação, não agora)*

- [ ] CHK001 `cd frontend && npm run typecheck` limpo nos três SPAs
- [ ] CHK002 `ruff check` limpo nos arquivos tocados
- [ ] CHK003 `verify_297.py` verde, com escrita conferida por conexão separada e cenários que falham
- [ ] CHK004 telas abertas no Browser pane; `/nfc/<code>` em viewport mobile
- [ ] CHK005 migration escrita à mão, `down_revision` no head
- [ ] CHK006 `validar_startcommand.py` — não se aplica (a feature não toca `startCommand`)
- [ ] CHK007 os sete endpoints com gate declarado e linha em `docs/01` §4.3
- [ ] CHK008 docs por fonte única (`01`, `02`, `03` sempre; `00` e `05` nesta feature)
- [ ] CHK009 `/speckit-converge` sem lacunas
- [ ] CHK010 antes de "está em produção": `git status`, `git log -1`, migrations sem untracked, sonda `/api/`

## Notes

- Validação rodada em 09/09/2026, uma iteração, sem reprovações.
- O diagnóstico da queixa (vídeos que não tocam) foi feito **antes** da spec, contra o disco da
  produção e a rota pública, sem incrementar `access_count`. As evidências estão na seção
  "O que a investigação de 09/09 encontrou".
- Sessão de `/speckit-clarify` em 09/09: cinco perguntas feitas e respondidas, integradas na seção
  "Clarifications" da spec. As Premissas 1 a 5 deixaram de ser suposição.
- Dois arquivos ainda não existem e são do dono: a **moldura PNG** e o **vídeo de abertura**. O
  desenvolvimento não depende deles (o sistema trata a ausência), mas a entrega sim.
