# Checklist de requisitos: LGPD, dado de criança, RBAC e saída automática — 350

**Purpose**: testar se a spec da 350 está bem escrita (completa, clara, consistente e mensurável) nos
pontos de consentimento, privacidade de criança, autorização e saída automática — não testa o código.
**Created**: 2026-11-17 · **Profundidade**: padrão · **Público**: revisor da branch (fluxo autônomo,
sem perguntas; foco escolhido pela sessão principal)
**Feature**: [spec.md](../spec.md) · [research.md](../research.md)

## Completude do consentimento

- [x] CHK001 - Os dois consentimentos estão definidos como separados, com finalidade própria? [Completeness, Spec §FR-001]
- [x] CHK002 - Está especificado o que cada registro guarda para servir de prova (data, texto completo, versão, origem, referência, autor)? [Completeness, Spec §FR-002]
- [x] CHK003 - Está dito que nenhum aceite é pré-marcado nem condição para fechar a festa? [Completeness, Spec §FR-001]
- [x] CHK004 - A regra de versionar o texto (mudou o texto → versão nova) está escrita? [Completeness, Spec §FR-003]
- [x] CHK005 - A lista de origens possíveis é fechada e enumerada? [Clarity, Spec §Clarifications, §FR-004]
- [x] CHK006 - Está definido o que acontece quando a versão do texto exibido difere da atual na página pública? [Edge Case, Research §D8, Contracts]
- [x] CHK007 - Os pontos de coleta estão todos listados (ficha, conversa, página pública, orçamento, loja)? [Coverage, Spec §Histórias 1, 3, 6, §FR-009]

## Dado de criança (art. 14)

- [x] CHK008 - O conjunto mínimo de dados da criança está delimitado (primeiro nome e data, nada mais)? [Clarity, Spec §Entidades]
- [x] CHK009 - Está definido que o aceite é por criança (irmãos separados)? [Completeness, Research §D4]
- [x] CHK010 - A remoção apaga o dado e o histórico não guarda nome nem data? [Completeness, Spec §FR-005]
- [x] CHK011 - Os limites de validade da data (futuro, idade máxima) estão quantificados? [Measurability, Spec §Casos de borda]
- [x] CHK012 - Quem pode ver o dado da criança está restrito e justificado? [Coverage, Spec §Clarifications, §RBAC]
- [ ] CHK013 - O prazo de guarda do dado da criança sem interação está definido? [Gap — adiado ao parecer jurídico, Research §Pontos 4]
- [x] CHK014 - O destino do dado quando a ficha é excluída está especificado? [Edge Case, Spec §Casos de borda]

## Saída automática e prospecção

- [x] CHK015 - As palavras de saída estão enumeradas e a regra de comparação (mensagem inteira, normalizada) é explícita? [Clarity, Spec §FR-006]
- [x] CHK016 - Há um exemplo negativo que delimita o falso positivo ("vou sair às 15h")? [Measurability, Spec §História 2]
- [x] CHK017 - Os dois caminhos do erro 131050 (aviso de status e recusa síncrona) estão cobertos? [Coverage, Spec §FR-007]
- [x] CHK018 - O comportamento para conversa sem ficha está definido? [Edge Case, Spec §Casos de borda]
- [x] CHK019 - "Sem aceite, nada de prospecção" está traduzido em requisitos verificáveis (modelo de marketing recusado, lista de aniversários com os dois aceites)? [Measurability, Spec §FR-008, §FR-019]
- [x] CHK020 - Está decidido se o pós-evento é prospecção, com o porquê? [Ambiguity resolvida, Spec §Clarifications, §FR-016]
- [x] CHK021 - A interação entre a retirada e o aceite da loja (344) está especificada sem conflito? [Consistency, Spec §FR-009, §Casos de borda]
- [x] CHK022 - Está explícito que nada desta feature envia mensagem sozinho? [Completeness, Spec §FR-020]

## RBAC e superfície pública

- [x] CHK023 - Todo endpoint novo ou alterado tem papéis declarados? [Coverage, Spec §RBAC, Contracts]
- [x] CHK024 - Há um cenário de autorização que deve falhar na verificação? [Measurability, Spec §Verificação #4]
- [x] CHK025 - O endpoint público tem limite de uso definido? [Non-Functional, Spec §RBAC]
- [x] CHK026 - Está definido o que a página pública revela da ficha (só o primeiro nome e se recebe novidades)? [Clarity, Contracts §avaliar]
- [ ] CHK027 - A verificação de que quem marca na página pública é a responsável está especificada? [Gap — Premissa; vai ao parecer jurídico, Research §Pontos 2]
- [x] CHK028 - O filtro do Google só para nota 5 está protegido por requisito explícito? [Consistency, Spec §O pedido, §FR-012]

## Critérios de aceite

- [x] CHK029 - Os critérios de sucesso são mensuráveis sem tecnologia (toques, 100%, tempo, meta 40%/50%)? [Acceptance Criteria, Spec §SC-001..006]
- [x] CHK030 - Cada história nomeia o cenário do verify que a prova? [Traceability, Spec §Cenários]

## Notas

- 28/30 atendidos. CHK013 e CHK027 são decisões jurídicas fora do alcance da spec; ficam registradas em
  `research.md` §Pontos para parecer jurídico e no relatório final, sem bloquear o plano.
