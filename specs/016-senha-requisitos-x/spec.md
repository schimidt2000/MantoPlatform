# Feature Specification: Marcar requisitos de senha não cumpridos com "✗"

**Feature Branch**: `016-senha-requisitos-x`

**Created**: 2026-06-04

**Status**: Draft

**Input**: User description: "Na tela onde a pessoa define a senha do portal existem as exigências. As
exigências não cumpridas devem estar marcadas com um xzinho, para ficar mais claro que todas
precisam ser preenchidas."

## Contexto

No portal do artista, ao criar/redefinir a senha, há uma lista de exigências (mínimo de
caracteres, maiúscula, minúscula, número, símbolo). Hoje a exigência **cumprida** mostra um "✓"
verde, mas a **não cumprida** aparece com um marcador neutro (um círculo cinza, ou sem ícone),
o que não deixa claro que ainda falta. O usuário quer que cada exigência **não cumprida** apareça
marcada com um **"✗"**, reforçando visualmente que todas precisam ser atendidas.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Ver claramente o que falta na senha (Priority: P1)

Ao digitar a senha na tela de criação/redefinição, cada exigência ainda não atendida aparece com um
"✗"; assim que é atendida, vira "✓".

**Why this priority**: É a melhoria pedida — clareza de que todas as exigências precisam ser
cumpridas.

**Independent Test**: Abrir a tela de definir senha, digitar uma senha parcial e confirmar que as
exigências faltantes mostram "✗" e as atendidas mostram "✓", atualizando em tempo real.

**Acceptance Scenarios**:

1. **Given** o campo de senha vazio ou parcialmente preenchido, **When** a pessoa olha a lista de
   exigências, **Then** cada exigência ainda não atendida aparece marcada com "✗".
2. **Given** a pessoa digitando a senha, **When** uma exigência passa a ser atendida, **Then** o
   "✗" daquela linha vira "✓" imediatamente.
3. **Given** todas as exigências atendidas, **When** a pessoa termina de digitar, **Then** todas as
   linhas mostram "✓" e nenhuma mostra "✗".

---

### Edge Cases

- **Campo vazio**: todas as exigências aparecem com "✗" (nada cumprido ainda).
- **Daltonismo/baixo contraste**: o "✗" e o "✓" diferenciam por símbolo (não só por cor), então a
  distinção não depende apenas da cor.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Na(s) tela(s) de definição de senha do portal, cada exigência **não cumprida** MUST
  exibir um marcador "✗" claramente visível.
- **FR-002**: Cada exigência **cumprida** MUST continuar exibindo o marcador "✓".
- **FR-003**: A troca entre "✗" e "✓" MUST acontecer em tempo real conforme a pessoa digita.
- **FR-004**: A distinção entre cumprido e não cumprido MUST ser perceptível pelo símbolo (não
  apenas pela cor).
- **FR-005**: A mudança é apenas visual; as regras de validação da senha e o fluxo de salvar NÃO
  MUST mudar.

### Key Entities *(include if feature involves data)*

- N/A — mudança puramente visual, sem dados.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% das exigências não cumpridas exibem "✗" enquanto não atendidas.
- **SC-002**: 100% das exigências cumpridas exibem "✓".
- **SC-003**: Ao atender uma exigência, o marcador muda de "✗" para "✓" em tempo real (sem recarregar
  a página).
- **SC-004**: Nenhuma mudança no comportamento de validação/salvamento da senha.

## Assumptions

- "A tela onde a pessoa define a senha" = a tela de **criar senha pessoal** do portal; por
  consistência, a mesma marcação "✗"/"✓" se aplica também à tela de **redefinir senha** (fluxo de
  esqueci a senha), que mostra as mesmas exigências.
- O símbolo de não cumprido é "✗" (em cor de alerta) e o de cumprido é "✓" (em verde), mantendo o
  visual já existente.
- A telinha de primeiro acesso (digitar a senha temporária) não tem lista de exigências e não é
  afetada.
