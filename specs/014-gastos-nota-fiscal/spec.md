# Feature Specification: Nota Fiscal obrigatória no gasto extra

**Feature Branch**: `014-gastos-nota-fiscal`

**Created**: 2026-06-01

**Status**: Draft

**Input**: User description: "Na seção de gastos extras, trocar 'comprovante' por 'Nota Fiscal' e
torná-la obrigatória. Mini texto explicando que pode ser a nota escaneada ou uma foto da nota
fiscal que mostre o valor dos produtos. Comprovante fiscal não serve."

## Contexto

No registro de gastos extras (features 004/005/013), o anexo era um **comprovante opcional**
("recomendado"). A empresa precisa garantir rastreabilidade fiscal: o documento anexado deve ser a
**Nota Fiscal** que mostra o valor dos produtos — não um simples comprovante/cupom de pagamento. O
usuário quer (1) **renomear** o campo para "Nota Fiscal", (2) torná-lo **obrigatório** e (3) exibir
uma **orientação curta** sobre o que vale como Nota Fiscal.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Anexar a Nota Fiscal ao registrar um gasto (Priority: P1)

Ao registrar um gasto extra, o usuário vê o campo "Nota Fiscal" com uma orientação curta e precisa
anexar o arquivo (foto ou digitalização) para conseguir salvar.

**Why this priority**: É o objetivo central — garantir que todo gasto tenha a Nota Fiscal.

**Independent Test**: Abrir o formulário de gasto, confirmar o rótulo "Nota Fiscal" e a orientação,
anexar um arquivo e salvar com sucesso.

**Acceptance Scenarios**:

1. **Given** o formulário de gasto, **When** o usuário o vê, **Then** o campo de anexo se chama
   "Nota Fiscal" e exibe a orientação de que pode ser a nota escaneada ou uma foto que mostre o
   valor dos produtos, e que comprovante/cupom fiscal não serve.
2. **Given** um gasto com Nota Fiscal anexada, **When** o usuário salva, **Then** o gasto é
   registrado normalmente (status pendente) com a Nota Fiscal acessível.

---

### User Story 2 - Bloquear gasto sem Nota Fiscal (Priority: P1)

Se o usuário tentar registrar um gasto sem anexar a Nota Fiscal, o sistema impede e avisa que o
anexo é obrigatório.

**Why this priority**: Sem a obrigatoriedade efetiva, a regra não se cumpre.

**Independent Test**: Preencher descrição e valor, deixar o anexo vazio, tentar salvar e confirmar
que o gasto não é criado e há um aviso claro.

**Acceptance Scenarios**:

1. **Given** o formulário preenchido sem anexo, **When** o usuário tenta salvar, **Then** o gasto
   não é criado e ele recebe um aviso de que a Nota Fiscal é obrigatória.
2. **Given** a tentativa bloqueada, **When** o usuário anexa a Nota Fiscal e salva de novo, **Then**
   o gasto é registrado com sucesso.

---

### Edge Cases

- **Gastos antigos sem Nota Fiscal**: registros criados antes desta mudança permanecem como estão;
  a obrigatoriedade vale apenas para novos registros.
- **Arquivo inválido/sem nome**: tratado como anexo ausente — o gasto não é criado e o usuário é
  avisado.
- **Coluna na lista**: a coluna/label que antes dizia "Comprovante" passa a dizer "Nota Fiscal".

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O campo de anexo do gasto extra MUST se chamar "Nota Fiscal" (no formulário e na
  lista), substituindo "Comprovante".
- **FR-002**: Anexar a Nota Fiscal MUST ser obrigatório para registrar um novo gasto extra.
- **FR-003**: Ao tentar registrar um gasto sem a Nota Fiscal, o sistema MUST impedir a criação e
  exibir um aviso claro de que o anexo é obrigatório.
- **FR-004**: O formulário MUST exibir uma orientação curta indicando que vale a nota escaneada ou
  uma foto da Nota Fiscal que mostre o valor dos produtos, e que comprovante/cupom fiscal não serve.
- **FR-005**: A obrigatoriedade MUST valer apenas para novos registros; gastos já existentes sem
  anexo não são afetados.
- **FR-006**: O restante do fluxo de gastos (categorias, valor, desembolso, aprovação, balanço,
  permissões da feature 013) MUST permanecer inalterado.

### Key Entities *(include if feature involves data)*

- **Gasto extra** (já existe): o anexo passa a ser **obrigatório** e renomeado para "Nota Fiscal";
  sem mudança de estrutura de dados.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% dos novos gastos registrados passam a ter uma Nota Fiscal anexada.
- **SC-002**: 0 novos gastos conseguem ser criados sem anexo de Nota Fiscal.
- **SC-003**: 100% dos usuários veem o rótulo "Nota Fiscal" e a orientação no formulário.
- **SC-004**: Nenhuma regressão no restante do fluxo de gastos (aprovação, balanço, permissões).

## Assumptions

- O anexo continua aceitando imagem (foto) ou PDF (digitalização) — o que muda é o rótulo, a
  obrigatoriedade e a orientação.
- "Comprovante fiscal não serve" é uma orientação ao usuário (texto), não uma validação automática
  do conteúdo do arquivo — o sistema não inspeciona o documento, apenas exige que algo seja anexado.
- Reaproveita o mesmo armazenamento de anexo já existente (sem mudança de banco).
- A obrigatoriedade é verificada no servidor (não só no navegador), para valer de fato.
