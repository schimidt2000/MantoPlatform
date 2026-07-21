# Specification Quality Checklist: Agenda/Eventos — escrita de casting em React

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-07-20
**Feature**: [spec.md](../spec.md)

## Content Quality

- [X] Sem detalhe de implementação além do que é o próprio assunto (migração de stack)
- [X] Focado em valor/risco (paridade de estado, sem e-mail duplicado, coexistência)
- [~] Escrito para não-técnicos — parcialmente: a auditoria dos handlers é técnica por
      necessidade, mas cada User Story tem narrativa em linguagem simples
- [X] Todas as seções obrigatórias preenchidas

## Requirement Completeness

- [X] Nenhum [NEEDS CLARIFICATION] — o pedido já fixou ações, RBAC, princípios e forma de
      verificação; a única decisão de design aberta (extrair handler vs. reusar) é HOW (plano),
      registrada em Assumptions
- [X] Requisitos testáveis e não ambíguos (FR-001..009)
- [X] Critérios de sucesso mensuráveis
- [X] Critérios tecnologia-agnósticos onde possível
- [X] Cenários de aceitação definidos (3 User Stories)
- [X] Edge cases identificados (e-mail, coexistência mesmo banco, envio duplicado, cargo
      dispensado × sync, teto de cachê por papel)
- [X] Escopo delimitado (P1 detalhada; P2/P3 alto nível; fora de escopo explícito)
- [X] Dependências e premissas identificadas

## Feature Readiness

- [X] Todos os FRs têm critério de aceitação
- [X] Cenários cobrem o fluxo primário (escalar) e secundários
- [X] Atende aos resultados mensuráveis
- [X] Sem vazamento de detalhe desnecessário

## Notes

- Primeira migração de ESCRITA — pattern-setting. O maior risco não é a UI, é **divergir da
  lógica de negócio existente** (teto de cachê, transições de invite, e-mails). Por isso a
  diretriz de reusar os handlers e a verificação de **paridade de estado campo a campo** contra
  `manto_local`.
- **Pronta para `/speckit-plan`** (escopado à fatia P1 — escalar talento).
- Ponto de maior atenção do plano: como extrair o núcleo de `_handle_assign_casting` sem
  quebrar o POST Jinja que a equipe usa (coexistência), e como isolar o envio de e-mail na
  verificação.
