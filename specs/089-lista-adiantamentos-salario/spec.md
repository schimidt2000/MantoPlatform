# Feature Specification: Lista de adiantamentos de salário (histórico preservado)

**Feature Branch**: `089-lista-adiantamentos-salario`

**Created**: 2026-06-26

**Status**: Draft

**Input**: "Na tela de adiantamento preciso que funcione diferente. Para essa pessoa já fiz um
adiantamento de 1.200; quero fazer mais um agora de 2.666. Porém as informações se perdem. Preciso
adicionar mais um sem perder o histórico — talvez funcionando como uma lista de adiantamentos."

## Contexto

Hoje a tela "Adiantamento de salário" guarda **um único valor** (e um comprovante). Ao registrar um
**novo** adiantamento, ele **sobrescreve** o anterior — o histórico se perde. O financeiro precisa
poder lançar **vários adiantamentos** para o mesmo salário (cada um com seu valor e comprovante),
mantendo a lista completa. O **valor a pagar** continua sendo o salário menos a **soma** de todos os
adiantamentos.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Adicionar vários adiantamentos sem perder o histórico (Priority: P1) 🎯 MVP

Como financeiro, quero adicionar um novo adiantamento sem apagar os anteriores, vendo a lista completa.

**Acceptance Scenarios**:

1. **Given** um salário com um adiantamento de R$ 1.200 já lançado, **When** adiciono outro de R$ 2.666,
   **Then** os **dois** passam a aparecer na lista (R$ 1.200 e R$ 2.666), nenhum é apagado.
2. **Given** vários adiantamentos lançados, **When** abro a tela do salário, **Then** vejo a **lista** com
   cada adiantamento (valor, data e comprovante) e o **total adiantado**.
3. **Given** a lista de adiantamentos, **When** somo todos, **Then** o **valor a pagar** exibido é
   salário − soma dos adiantamentos.
4. **Given** que recarrego a tela de pagamentos, **When** ela é regenerada, **Then** os adiantamentos
   lançados **continuam lá** (não se perdem).

### User Story 2 - Remover um adiantamento específico (Priority: P2)

Como financeiro, quero remover **um** adiantamento da lista (ex.: lançado errado) sem afetar os demais.

**Acceptance Scenarios**:

1. **Given** três adiantamentos, **When** removo o do meio, **Then** os outros dois permanecem e o total
   é recalculado.
2. **Given** que removo um adiantamento, **When** ele tinha comprovante, **Then** o comprovante daquele
   item também é descartado.

### Edge Cases

- Cada adiantamento exige **comprovante** próprio quando o valor é maior que zero.
- A **soma** dos adiantamentos não pode **exceder** o salário; tentativa que ultrapassaria é bloqueada
  com aviso.
- Adiantamento com valor zero/!vazio não é criado (avisa).
- Adiantamentos não alteram o **custo de salário** do balanço (apenas o valor a pagar) — comportamento
  atual mantido.
- Os adiantamentos já existentes (modelo antigo de valor único) **continuam visíveis** após a mudança.

## Requirements *(mandatory)*

- **FR-001**: O sistema MUST permitir **vários adiantamentos** por salário, cada um com **valor** e
  **comprovante** próprios, exibidos como uma **lista**.
- **FR-002**: Adicionar um novo adiantamento MUST **preservar** os anteriores (nunca sobrescrever).
- **FR-003**: A tela MUST mostrar a lista de adiantamentos (valor, data, comprovante) e o **total
  adiantado**.
- **FR-004**: O **valor a pagar** do salário MUST ser salário − **soma** dos adiantamentos.
- **FR-005**: A **soma** dos adiantamentos MUST não exceder o salário; um lançamento que ultrapassaria é
  rejeitado com mensagem clara.
- **FR-006**: Cada adiantamento com valor > 0 MUST exigir **comprovante**.
- **FR-007**: O financeiro MUST poder **remover** um adiantamento específico (e seu comprovante) sem
  afetar os demais.
- **FR-008**: A regeneração da tela de pagamentos MUST **preservar** os salários que têm adiantamentos
  (não apagá-los), como hoje preserva o adiantamento único.
- **FR-009**: Os adiantamentos MUST não reduzir o **custo de salário** no balanço financeiro (mantém o
  comportamento atual: afetam só o valor a pagar).
- **FR-010**: Os adiantamentos já registrados no formato antigo (valor único) MUST aparecer na nova
  lista (migração do histórico).

## Success Criteria *(mandatory)*

- **SC-001**: É possível ter 2+ adiantamentos no mesmo salário, todos visíveis, sem nenhum sumir.
- **SC-002**: O valor a pagar reflete sempre salário − soma de todos os adiantamentos.
- **SC-003**: Remover um adiantamento mantém os demais e recalcula o total.
- **SC-004**: Recarregar/regenerar a tela nunca apaga adiantamentos lançados.
- **SC-005**: Nenhum adiantamento antigo é perdido após a atualização.

## Key Entities

- **Adiantamento de salário**: pertence a um pagamento de salário (pessoa + data); tem **valor**,
  **comprovante** e **data de lançamento**. Um salário pode ter **muitos** adiantamentos.
- **Pagamento de salário**: já existente; o "valor a pagar" passa a considerar a **soma** dos seus
  adiantamentos.

## Assumptions

- A lista de adiantamentos pertence ao **pagamento de salário** específico (pessoa + vencimento), como o
  adiantamento único atual. Cada item guarda a data em que foi lançado.
- Limite de tamanho do comprovante mantém o atual (~10 MB) e os mesmos tipos (PDF/imagem).
- Migração: cada adiantamento único já existente vira **um item** na nova lista, preservando valor e
  comprovante.
- Permissões inalteradas (acesso do financeiro/super admin).
