# Feature Specification: Cadastro de Cliente Mais Completo

**Feature Branch**: `119-cliente-dados-completos`

**Created**: 2026-07-08

**Status**: Draft

**Input**: User description: "Ter mais informações das clientes, como endereço, CPF e tudo mais. A parte dos dados do cliente pode ficar mais completa usando dos dados dos formulários preenchidos."

## Contexto

O cadastro de cliente (feature 094) hoje guarda apenas nome, telefone, e-mail e empresa —
o suficiente para identificar quem é a cliente, mas não para fechar contrato (falta CPF/
CNPJ e endereço). Com os formulários de pré-contrato (feature 118) a cliente já digita
esses dados no preenchimento; hoje eles ficam presos na resposta e não chegam ao cadastro
do cliente. Esta feature aproveita esse preenchimento para completar automaticamente a
ficha do cliente, e dá à equipe comercial um jeito de completar manualmente quando não há
formulário.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Associar resposta completa o cadastro do cliente (Priority: P1)

Quando o comercial associa uma resposta de formulário a um cliente (criando um cliente
novo a partir da resposta, ou vinculando a um já existente), os campos de CPF/CNPJ e
endereço do cliente que ainda estão vazios são preenchidos automaticamente com o que veio
naquela resposta. Dados que o cliente já tinha preenchido antes (manualmente ou de uma
resposta anterior) nunca são sobrescritos.

**Independent Test**: criar uma resposta de formulário com CPF e endereço preenchidos,
associá-la a um cliente sem esses dados, conferir que a ficha do cliente passou a exibir
CPF e endereço; repetir associando uma segunda resposta com CPF diferente e conferir que o
CPF original do cliente não muda.

**Acceptance Scenarios**:

1. **Given** uma resposta do formulário comum com CPF e endereço, **When** o comercial cria
   um cliente novo a partir dela, **Then** o cliente nasce com nome, telefone, CPF e
   endereço vindos da resposta.
2. **Given** uma resposta do formulário corporativo com CNPJ e endereço da empresa,
   **When** o comercial cria um cliente a partir dela, **Then** o cliente nasce com CNPJ e
   endereço da empresa.
3. **Given** um cliente já existente sem CPF, **When** o comercial associa (vincula, sem
   criar) uma resposta que tem CPF, **Then** o CPF do cliente é preenchido.
4. **Given** um cliente que já tem CPF preenchido, **When** o comercial associa uma
   resposta com um CPF diferente, **Then** o CPF do cliente permanece o que já estava lá
   (nunca sobrescreve dado existente).
5. **Given** uma resposta sem CPF/endereço preenchido (campo opcional deixado em branco),
   **When** associada a um cliente, **Then** os campos correspondentes do cliente
   permanecem como estavam (nada é apagado).

### User Story 2 - Completar ou corrigir dados manualmente (Priority: P2)

A ficha do cliente mostra CPF/CNPJ e endereço quando preenchidos, e a equipe comercial
pode editar esses campos diretamente ali — útil para clientes que nunca preencheram um
formulário, ou para corrigir um dado errado.

**Acceptance Scenarios**:

1. **Given** a ficha de um cliente, **When** o comercial abre a edição, **Then** vê campos
   para CPF/CNPJ e endereço (vazios ou com o valor atual).
2. **Given** a edição preenchida, **When** salva, **Then** a ficha do cliente reflete o
   novo valor imediatamente.
3. **Given** um usuário sem papel comercial, **Then** não vê a opção de editar.

## Requirements *(mandatory)*

- **FR-001**: O cadastro de cliente DEVE suportar CPF, CNPJ e endereço, além dos campos já
  existentes (nome, telefone, e-mail, empresa).
- **FR-002**: Ao associar uma resposta de formulário de pré-contrato (feature 118) a um
  cliente — seja criando um cliente novo a partir da resposta, seja vinculando a um já
  existente — o sistema DEVE preencher automaticamente os campos de CPF/CNPJ e endereço do
  cliente que estiverem vazios, usando os dados equivalentes da resposta.
- **FR-003**: O preenchimento automático NUNCA PODE sobrescrever um valor que o cliente já
  tenha (preenchido manualmente ou por uma associação anterior) — só entra em campos
  vazios.
- **FR-004**: A ficha do cliente DEVE exibir CPF/CNPJ e endereço quando preenchidos.
- **FR-005**: A equipe comercial (COMERCIAL/FINANCEIRO/SUPERADMIN) DEVE poder editar
  manualmente CPF/CNPJ e endereço do cliente pela própria ficha.
- **FR-006**: Resposta do formulário comum (pessoa física) alimenta CPF e endereço do
  contratante; resposta do formulário corporativo alimenta CNPJ e endereço da empresa —
  cada tipo de formulário preenche os campos que fazem sentido para ele.

### Key Entities

- **Cliente (Client)**: ganha os campos CPF, CNPJ e endereço (texto livre, como capturado
  no formulário ou digitado manualmente).

## Success Criteria *(mandatory)*

- **SC-001**: Depois de associar uma resposta de formulário, o cliente tem CPF/CNPJ e
  endereço na ficha sem qualquer digitação manual adicional.
- **SC-002**: Nenhum dado de cliente já preenchido é perdido ou sobrescrito por uma
  associação de resposta.
- **SC-003**: Um cliente sem nenhum formulário associado ainda pode ter a ficha completada
  manualmente pela equipe comercial.

## Assumptions

- CPF/CNPJ e endereço são guardados como texto livre (mesmo formato capturado no
  formulário — ex.: "390.533.447-05", endereço em uma linha) — sem decompor em
  logradouro/número/bairro separados, pois o formulário de pré-contrato também captura o
  endereço da contratante/empresa como um campo único de texto corrido.
- Não há verificação de duplicidade de CPF/CNPJ entre clientes nesta feature (diferente do
  banco de talentos, que já bloqueia CPF duplicado) — o cadastro de cliente não teve essa
  regra antes e adicioná-la está fora do pedido original.
- O endereço do formulário comum vem do campo "Endereço completo da contratante" (dados da
  pessoa), não do "Endereço do Evento" (que é o local da festa e pode ser um espaço
  diferente da casa da contratante).
