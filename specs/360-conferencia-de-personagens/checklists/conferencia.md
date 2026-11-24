# Checklist de qualidade dos requisitos: dados e fila, e tela no celular (360)

**Purpose**: testar se os requisitos da conferência estão completos, claros e mensuráveis antes de
implementar (não testa o código)
**Created**: 2026-11-24
**Feature**: [spec.md](../spec.md) · [plan.md](../plan.md) · [data-model.md](../data-model.md)
**Público**: quem implementa e quem revisa antes do merge · **Profundidade**: padrão

## Completude — dados e fila

- [x] CHK001 A regra da fila está escrita com todas as condições (ativo, sem ficha própria, sem elenco, não é página própria)? [Completeness, Spec §FR-002]
- [x] CHK002 Está definido o que acontece com as decisões de um item que sai da fila e depois volta? [Completeness, Spec §História 2, cenário 2]
- [x] CHK003 O estado "sem leitura" está definido quanto ao que mostra, ao que conta e ao que permite? [Completeness, Spec §FR-003]
- [x] CHK004 A idempotência da carga cobre repetição, clique duplo, item já decidido e item carregado mas intocado? [Coverage, Spec §FR-010]
- [x] CHK005 Estão definidas as três referências que podem não existir na carga (item, foto, ficha) e o que cada uma vira? [Coverage, Spec §FR-011]
- [x] CHK006 Estão definidas as referências que morrem DEPOIS da carga (item, foto, ficha, usuário que conferiu)? [Edge Case, Spec §Casos de borda]
- [x] CHK007 Está dito que a conferência não altera o catálogo, e há critério para medir isso? [Measurability, Spec §FR-014, §SC-006]

## Clareza e consistência — dados e fila

- [x] CHK008 Os limites de cada campo editável (nome, observação) estão quantificados? [Clarity, data-model §Validações]
- [x] CHK009 A mudança de tipo está definida nos dois sentidos, para o elenco e para a ficha do item? [Consistency, Spec §FR-007]
- [x] CHK010 Os contadores estão definidos sem ambiguidade (o que entra no progresso, onde fica o "sem leitura", se seguem o filtro)? [Clarity, Spec §FR-012]
- [x] CHK011 A ordem da fila e o critério de "próximo item" estão especificados? [Clarity, Spec §FR-012, §FR-018]
- [x] CHK012 O que "conferido" trava está definido para todas as escritas (item, personagem, acrescentar, excluir)? [Consistency, Spec §FR-009]
- [x] CHK013 A condição para conferir um tema ou dupla está definida, com o que a tela orienta na recusa? [Completeness, Spec §FR-017]
- [x] CHK014 A diferença entre "excluir" (acrescentado à mão) e "não criar" (da leitura) está explícita e alinhada ao glossário? [Consistency, Spec §FR-005, constituição XV]

## Cobertura de cenários — concorrência e autorização

- [x] CHK015 Há requisito para duas pessoas no mesmo item, inclusive conferir × editar? [Coverage, Spec §Casos de borda]
- [x] CHK016 Todo endpoint novo tem papel declarado, e está dito o que os outros papéis recebem e veem? [Completeness, Spec §RBAC, §FR-015]
- [x] CHK017 Cada história nomeia o cenário do verify que a prova, com cenários que devem falhar? [Traceability, Spec §Verificação]

## Tela no celular

- [x] CHK018 O requisito de 390 px é objetivo (sem rolagem lateral, alvo mínimo em px)? [Measurability, Spec §FR-016, §SC-005]
- [x] CHK019 "Ao alcance do polegar" está traduzido em posição concreta da ação principal? [Clarity, Spec §FR-018]
- [x] CHK020 Os estados de salvar na hora estão definidos (salvando, salvo, erro, falha de rede) e dizem o que acontece com o que foi digitado? [Completeness, Spec §FR-008, §Casos de borda]
- [x] CHK021 Está definido que o proposto pela leitura continua visível depois da correção? [Completeness, Spec §FR-004]
- [x] CHK022 Há requisito para ver as fotos originais do item e para como elas abrem? [Completeness, Spec §FR-013]
- [x] CHK023 Os estados vazios estão definidos (fila zerada, filtro sem resultado, item sem foto, leitura não carregada)? [Coverage, Spec §Casos de borda, contracts §Textos]
- [x] CHK024 Os textos da tela estão listados e seguem o tom do app interno e o glossário? [Consistency, contracts §Textos, constituição XV]
- [x] CHK025 Há requisito de rótulo acessível para os controles repetidos por personagem? [Coverage, Spec §FR-016]
- [x] CHK026 A ação destrutiva (excluir personagem acrescentado) tem confirmação prevista? [Coverage, plan §Constitution Check V]

## Dependências e premissas

- [x] CHK027 A premissa "a conferência só registra; gravar é a feature seguinte" está escrita e apontada como revisável pelo dono? [Assumption, Spec §Clarifications, §Premissas]
- [x] CHK028 A dependência do espelho `manto_360` no lugar do `manto_local` está registrada como exceção? [Dependency, plan §Rastreamento de complexidade]

## Notas

- Lacunas achadas nesta rodada e fechadas na spec antes de marcar: FR-007 (ficha do item na mudança de
  tipo), FR-012 (ordem da fila e definição do progresso), FR-016 (rótulo acessível) e dois casos de
  borda (falha de rede ao salvar; usuário que conferiu excluído).
- Itens CHK008, CHK024 e CHK026 se apoiam em `data-model.md`, `contracts/` e `plan.md`, não só na spec.
