# Feature Specification: EducaManto — ensemble, catering por pessoa, dropdown e acesso ensaio

**Feature Branch**: `048-educamanto-ensemble`

**Created**: 2026-06-15

**Status**: Draft (aguardando 2 esclarecimentos de cálculo)

**Input**: User description: "Mostrar todos os pacotes num dropdown. EducaManto disponível para a
role ensaio. Botão 'adicionar ensemble' (digitar quantos). Padronizar o cachê do ensemble nas
configs do pacote: 1 sessão 350, 2s 600, 1s/dia 300, 2s/dia 550. A quantidade de ensemble aumenta a
quantidade de ajuda de custo ensaio e aumenta proporcionalmente o catering da apresentação e/ou
ensaio — fazer a matemática do custo por pessoa do catering ensaio e apresentação, e mudar todos os
pacotes para essa conta."

## Contexto

A tela do EducaManto lista os pacotes como uma fileira longa de abas (24+), o que fica difícil de
navegar. Só COMERCIAL/SUPERADMIN acessam. O cálculo trata "Catering ensaio" e "Catering
apresentação" como valores fixos, e a "Ajuda de custo ensaio" tem quantidade fixa (11 pessoas =
3 Cara Limpa + 6 Bonecos + 2 Produção). Não há como adicionar "ensemble" (bailarinos/figurantes
extras) num orçamento, que deveria: ter cachê próprio, aumentar a ajuda de custo e aumentar o
catering proporcionalmente.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Selecionar pacote por dropdown (Priority: P2)

O usuário escolhe o pacote num **dropdown** em vez de procurar numa fileira de abas.

**Acceptance Scenarios**:

1. **Given** vários pacotes, **When** o usuário abre o dropdown e escolhe um, **Then** a tela
   recalcula para o pacote escolhido.

---

### User Story 2 - EducaManto disponível para o ensaio (Priority: P1)

Quem é da role ENSAIO acessa o EducaManto (calculadora) pelo menu e usa normalmente.

**Acceptance Scenarios**:

1. **Given** um usuário ENSAIO, **Then** vê "EducaManto" no menu e abre a tela de orçamento.
2. **Given** um usuário ENSAIO, **Then** NÃO consegue criar/editar/excluir pacotes (gestão segue
   só do super admin).

---

### User Story 3 - Adicionar ensemble ao orçamento (Priority: P1)

O usuário clica em "Adicionar ensemble", digita a quantidade, e o orçamento passa a incluir:
(a) o cachê do ensemble (valor padronizado por cenário), (b) +1 por ensemble na ajuda de custo
ensaio, (c) aumento proporcional do catering.

**Acceptance Scenarios**:

1. **Given** um pacote e 3 ensembles, **When** calcula 1 sessão/1 dia, **Then** soma 3 × R$350 de
   cachê de ensemble ao custo.
2. **Given** 3 ensembles, **Then** a "Ajuda de custo ensaio" passa de 11 para 14 pessoas.
3. **Given** 3 ensembles, **Then** o catering (ensaio e/ou apresentação) cresce proporcional ao
   número de pessoas — conforme o custo por pessoa definido.
4. **Given** 0 ensembles, **Then** o orçamento é idêntico ao de hoje (nada muda sem ensemble).

---

### User Story 4 - Cachê do ensemble padronizado nas configs (Priority: P1)

O cachê do ensemble é configurado na página de configurações do pacote (super admin), por cenário:
1 sessão R$350, 2 sessões R$600, 1s/dia R$300, 2s/dia R$550.

**Acceptance Scenarios**:

1. **Given** as configs do pacote, **Then** existe o cachê do ensemble por cenário (com os padrões
   acima) e o super admin pode ajustar.

---

### Edge Cases

- Ensemble = 0: orçamento idêntico ao atual.
- Catering vira "por pessoa": com 11 pessoas o total bate com o valor atual; cada ensemble soma o
  custo por pessoa.
- Multidia: cachê do ensemble e catering por pessoa entram por dia, como os demais itens.
- A mudança para "catering por pessoa" vale para TODOS os pacotes existentes.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: A seleção de pacote MUST ser por dropdown.
- **FR-002**: A role ENSAIO MUST ter acesso de uso ao EducaManto (calculadora); gestão de pacotes
  permanece exclusiva do super admin.
- **FR-003**: O orçamento MUST permitir adicionar uma quantidade de ensemble; cada ensemble soma o
  cachê padronizado do cenário (1s R$350, 2s R$600, 1s/dia R$300, 2s/dia R$550, configuráveis).
- **FR-004**: Cada ensemble MUST aumentar em 1 a quantidade de "Ajuda de custo ensaio".
- **FR-005**: O catering (ensaio e apresentação) MUST ser calculado **por pessoa** e crescer com o
  número de pessoas (base + ensembles). [NEEDS CLARIFICATION: divisor/headcount e se ensemble entra
  em ensaio, apresentação ou ambos — ver perguntas]
- **FR-006**: A conta de catering por pessoa MUST ser aplicada a todos os pacotes; com 0 ensemble e
  headcount base, o total MUST permanecer igual ao atual.

### Key Entities

- **Pacote EducaManto** — ganha o cachê do ensemble por cenário.
- **Orçamento (cálculo)** — passa a aceitar quantidade de ensemble, refletida em cachê, ajuda de
  custo e catering.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Com 0 ensemble, todos os pacotes mantêm exatamente o valor atual.
- **SC-002**: Adicionar N ensembles soma N × cachê, +N na ajuda de custo e +N pessoas no catering.
- **SC-003**: ENSAIO acessa a calculadora; não acessa a gestão de pacotes.

## Assumptions

- Headcount base do elenco = 11 (3 Cara Limpa + 6 Bonecos + 2 Produção), igual à quantidade atual
  de "Ajuda de custo ensaio".
- Cachê do ensemble por cenário (350/600/300/550) é configurável por pacote, com esses padrões.
- Gestão de pacotes (criar/editar/excluir e configs) continua só do super admin; ENSAIO só usa.
- Dropdown substitui as abas; demais cálculos inalterados fora do ensemble/catering.
