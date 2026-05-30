# Feature Specification: Página de Gastos Especiais

**Feature Branch**: `004-gastos-especiais`

**Created**: 2026-05-29

**Status**: Draft

**Input**: User description: "preciso criar uma página de gastos especiais (investimento em
figurinos, compras de escritório, etc.). Anotar o gasto anexando um comprovante; o valor
participa do painel financeiro/balanço. Valores em R$ 1.000,00. Qualquer pessoa pode inserir,
mas só entra na conta quando aprovado por um super admin. Adicione o que fizer sentido."

## Contexto

A empresa tem gastos extras fora dos eventos (figurino, escritório, marketing, manutenção…).
Hoje não há onde registrá-los, então eles não aparecem no balanço financeiro. Esta feature cria
uma página onde qualquer colaborador registra um gasto com comprovante; o gasto só impacta o
balanço depois de aprovado por um super admin.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Registrar um gasto especial com comprovante (Priority: P1)

Qualquer colaborador autenticado abre a página de Gastos Extras e registra um gasto:
descrição, categoria, valor (em R$), data do gasto e um comprovante anexado. O gasto entra
como **pendente**.

**Why this priority**: É a base da feature — sem o registro, nada acontece.

**Independent Test**: Registrar um gasto com comprovante e vê-lo aparecer na lista como
"pendente".

**Acceptance Scenarios**:

1. **Given** um colaborador na página, **When** preenche descrição, categoria, valor e anexa
   comprovante e salva, **Then** o gasto aparece na lista com status "pendente".
2. **Given** um valor digitado como "1.000,00", **When** salva, **Then** o sistema interpreta
   como R$ 1.000,00 corretamente.
3. **Given** um valor inválido, **When** tenta salvar, **Then** recebe mensagem amigável e o
   gasto não é criado.

---

### User Story 2 - Aprovar/rejeitar gastos (apenas super admin) (Priority: P1)

Um super admin revisa os gastos pendentes e os **aprova** (passam a contar no balanço) ou os
**rejeita** com um motivo. Quem não é super admin não vê nem consegue executar essas ações.

**Why this priority**: É o controle que garante que só gastos legítimos entrem na conta.

**Independent Test**: Como super admin, aprovar um gasto pendente e vê-lo virar "aprovado";
como não-super-admin, confirmar que as ações de aprovar/rejeitar não estão disponíveis.

**Acceptance Scenarios**:

1. **Given** um gasto pendente e um super admin, **When** ele aprova, **Then** o status vira
   "aprovado", registrando quem aprovou e quando.
2. **Given** um gasto pendente, **When** o super admin rejeita com um motivo, **Then** o status
   vira "rejeitado" e o motivo fica visível.
3. **Given** um colaborador que não é super admin, **When** abre a lista, **Then** não vê
   botões de aprovar/rejeitar e não consegue executá-los.

---

### User Story 3 - Gastos aprovados entram no balanço (Priority: P1)

Os gastos **aprovados** aparecem no painel financeiro e abatem o resultado do mês
correspondente à data do gasto. Gastos pendentes ou rejeitados não impactam o balanço.

**Why this priority**: É o objetivo final — enxergar os gastos extras no financeiro.

**Independent Test**: Aprovar um gasto com data no mês atual e confirmar que o painel
financeiro mostra uma linha de "Gastos Extras" abatendo o lucro líquido daquele mês.

**Acceptance Scenarios**:

1. **Given** um gasto aprovado com data em maio, **When** o financeiro vê o painel de maio,
   **Then** há uma linha "Gastos Extras" com o valor, abatida do lucro líquido.
2. **Given** um gasto pendente, **When** o financeiro vê o painel, **Then** ele NÃO é contado.

---

### User Story 4 - Acompanhar a lista e os totais (Priority: P2)

Qualquer colaborador vê a lista de gastos com status, valor, categoria, autor e comprovante,
além de totais (pendente vs aprovado).

**Why this priority**: Transparência e acompanhamento; não é pré-requisito para o impacto no balanço.

**Acceptance Scenarios**:

1. **Given** vários gastos, **When** o colaborador abre a lista, **Then** vê cada gasto com seu
   status e um total de pendentes e de aprovados.
2. **Given** um gasto com comprovante, **When** o colaborador clica no comprovante, **Then**
   consegue visualizá-lo.

---

### Edge Cases

- **Valor inválido / vazio**: mensagem amigável; não cria o gasto.
- **Sem comprovante**: permitido salvar, mas a interface sinaliza que o comprovante é recomendado.
- **Excluir**: o autor pode excluir o próprio gasto enquanto pendente; o super admin pode excluir qualquer um.
- **Gasto rejeitado**: não conta no balanço; pode ser reenviado/editado conforme o motivo.
- **Mês do balanço**: o gasto impacta o mês da **data do gasto**, não a data de aprovação.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Qualquer colaborador autenticado MUST conseguir registrar um gasto com descrição,
  categoria, valor e data, e anexar um comprovante.
- **FR-002**: Valores MUST ser informados e exibidos no formato brasileiro (R$ 1.000,00).
- **FR-003**: Todo gasto novo MUST entrar com status "pendente".
- **FR-004**: Apenas super admin MUST conseguir aprovar ou rejeitar um gasto; rejeição MUST
  permitir registrar um motivo.
- **FR-005**: A aprovação MUST registrar quem aprovou e quando.
- **FR-006**: Apenas gastos **aprovados** MUST impactar o balanço do painel financeiro.
- **FR-007**: O impacto no balanço MUST ocorrer no mês correspondente à **data do gasto**.
- **FR-008**: O painel financeiro MUST exibir uma linha de "Gastos Extras" abatendo o lucro
  líquido do mês.
- **FR-009**: A lista MUST mostrar status, valor, categoria, autor, data e o comprovante de
  cada gasto, com totais de pendentes e aprovados.
- **FR-010**: O autor MUST conseguir excluir o próprio gasto enquanto pendente; o super admin
  MUST conseguir excluir qualquer gasto.
- **FR-011**: Ações relevantes (criação, aprovação, rejeição) MUST ser registradas no log de
  auditoria do sistema.

### Key Entities *(include if feature involves data)*

- **Gasto Especial**: um gasto extra da empresa. Atributos: descrição, categoria, valor,
  data do gasto, comprovante (anexo), status (pendente/aprovado/rejeitado), autor, aprovador,
  datas de criação/aprovação, e motivo (em caso de rejeição).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Um colaborador registra um gasto com comprovante em menos de 1 minuto.
- **SC-002**: 100% dos gastos não aprovados ficam fora do balanço (0 vazamentos de pendente/rejeitado).
- **SC-003**: Um gasto aprovado aparece no painel financeiro do mês correto, abatendo o lucro líquido.
- **SC-004**: Não-super-admins têm 0 acesso às ações de aprovar/rejeitar.

## Assumptions

- "Qualquer pessoa" = qualquer usuário autenticado do sistema.
- Categorias sugeridas: Figurino, Escritório, Marketing, Manutenção, Outros (com "Outros" para
  casos gerais).
- O comprovante é recomendado, porém não bloqueia o registro (um gasto pode ser anotado e o
  comprovante anexado depois).
- O impacto no balanço usa a data do gasto (competência), abatendo o lucro líquido do mês.
- O painel financeiro continua restrito a Financeiro/Super admin; a lista de gastos é aberta a
  qualquer colaborador (registro), mas a aprovação é exclusiva do super admin.
