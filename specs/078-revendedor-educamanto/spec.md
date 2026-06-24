# Feature Specification: Revendedor EducaManto + acréscimo do vendedor + taxa interna

**Feature Branch**: `078-revendedor-educamanto`

**Created**: 2026-06-23

**Status**: Draft

**Input**: "Criar uma permissão 'revendedor educamanto' que acessa só a agenda (visualização) e a
página de orçamentos EducaManto. Uma função para limpar o transporte. Um lugar para o vendedor pôr
um acréscimo acima do show — essa diferença é a comissão do vendedor. Esconder a comissão do
vendedor já existente (agora chamada 'taxa interna'), que será usada para formar rendimento/comissão
do Gabriel Lara no futuro — não hardcoded, customizável em painel já existente. Usar toda a base da
calculadora de orçamentos para parecer o mesmo sistema, com funcionalidades levemente diferentes."

## Contexto

O EducaManto (orçamentos por pacote) já calcula valor sem/com NF, com transporte (076) e gera PDF
(077). Esta feature adiciona: (1) um **perfil restrito** "Revendedor EducaManto", que só vê a
**agenda (somente leitura)** e o **EducaManto**; (2) um botão para **limpar o transporte**; (3) um
**acréscimo do vendedor** somado ao valor, que **é a comissão** do vendedor; (4) renomear a antiga
"comissão do vendedor" para **"taxa interna"** e **escondê-la** da calculadora (segue customizável
no cadastro do pacote, para uso futuro).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Perfil Revendedor EducaManto (Priority: P1) 🎯 MVP

Como administrador, quero um perfil que só acessa a **agenda (visualização)** e o **EducaManto**,
para dar acesso a revendedores sem expor o resto do sistema.

**Independent Test**: Um usuário só com o perfil "Revendedor EducaManto" consegue abrir a agenda e o
EducaManto; ao tentar abrir financeiro, talentos, admin, home etc., é **redirecionado/bloqueado**; e
**não consegue editar** eventos na agenda.

**Acceptance Scenarios**:

1. **Given** um usuário só com "Revendedor EducaManto", **When** acessa **/agenda** e **/educamanto**,
   **Then** as páginas abrem normalmente.
2. **Given** o mesmo usuário, **When** tenta acessar páginas fora do permitido (financeiro, talentos,
   admin, gastos, orçamento, home), **Then** é **bloqueado** (redirecionado para a agenda).
3. **Given** o mesmo usuário na agenda, **When** tenta editar/criar/alterar um evento, **Then** a
   ação é **negada** (somente leitura).
4. **Given** o menu lateral, **When** o revendedor está logado, **Then** vê apenas **Agenda** e
   **EducaManto** (sem as demais seções).
5. **Given** o cadastro de usuários (admin), **When** edito um usuário, **Then** posso atribuir o
   novo perfil.

### User Story 2 - Limpar transporte (Priority: P2)

Como usuário do EducaManto, quero um botão para **limpar o transporte** calculado, caso precise
refazer.

**Acceptance Scenarios**:

1. **Given** um transporte calculado, **When** clico em "Limpar", **Then** endereço, distância, tipo,
   carretinha e pessoas voltam ao padrão e o transporte volta a **zero** (o valor final desconta).

### User Story 3 - Acréscimo do vendedor = comissão (Priority: P1)

Como vendedor, quero adicionar um **acréscimo** ao valor (acima do valor do pacote/"show"); esse
acréscimo **é a minha comissão** e entra no valor final do orçamento.

**Acceptance Scenarios**:

1. **Given** um pacote calculado, **When** informo um acréscimo (R$), **Then** o **valor final**
   (sem e com NF) aumenta nesse acréscimo e vejo "**Comissão do vendedor: R$X**" (= o acréscimo).
2. **Given** um acréscimo informado, **When** gero o PDF, **Then** o valor no PDF **já inclui** o
   acréscimo (o cliente vê o total); a comissão não aparece como linha no PDF (é interna do vendedor).
3. **Given** acréscimo zero, **When** vejo o resultado, **Then** o valor final é o do pacote (+
   transporte), sem comissão.

### User Story 4 - Taxa interna (antiga comissão) escondida e customizável (Priority: P2)

Como gestor, quero que a antiga "comissão do vendedor" do pacote passe a se chamar **"taxa interna"**,
fique **escondida** na calculadora e continue **customizável** no cadastro do pacote (para uso
futuro de rendimento do Gabriel Lara).

**Acceptance Scenarios**:

1. **Given** a calculadora do EducaManto, **When** vejo o resultado, **Then** **não** aparece mais a
   "Comissão do vendedor" antiga (taxa interna oculta).
2. **Given** o cadastro/edição do pacote, **When** edito, **Then** o campo aparece como **"Taxa
   interna (%)"** e é salvo normalmente (customizável, não hardcoded).

### Edge Cases

- Usuário com Revendedor EducaManto **+ outro perfil**: a restrição se aplica **apenas** quando o
  perfil for o **único** (multi-perfil mantém os acessos dos outros).
- Acréscimo aplicado igual para todos os pacotes escolhidos no PDF (como o transporte).
- "Limpar transporte" não afeta dias/ensemble/acréscimo.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: MUST existir um perfil **"Revendedor EducaManto"**, atribuível no cadastro de usuários.
- **FR-002**: Um usuário **somente** com esse perfil MUST acessar apenas **/agenda** (e visualizar
  eventos) e **/educamanto**; demais páginas MUST ser **bloqueadas** (redirecionadas à agenda).
- **FR-003**: O perfil MUST ser **somente leitura** na agenda (sem criar/editar/excluir eventos,
  ensaios, casting, etc.).
- **FR-004**: O menu MUST mostrar a esse perfil apenas **Agenda** e **EducaManto**.
- **FR-005**: O EducaManto MUST ter um botão **"Limpar transporte"** que zera o transporte e seus
  campos.
- **FR-006**: O EducaManto MUST ter um campo de **acréscimo do vendedor** (R$) somado ao valor final
  (sem e com NF); esse acréscimo MUST ser exibido como **"Comissão do vendedor"** e **incluído** no
  total do PDF (sem linha separada de comissão no PDF).
- **FR-007**: A antiga **"comissão do vendedor"** do pacote MUST ser renomeada para **"taxa interna"**,
  **escondida** na calculadora, e permanecer **customizável** no cadastro do pacote (não hardcoded).
- **FR-008**: Reutilizar a base do EducaManto/calculadora (mesmo visual e componentes) — apenas as
  funcionalidades acima diferem.

### Key Entities

- **Perfil/Role (existente)**: novo valor "Revendedor EducaManto".
- **Pacote EducaManto (existente)**: o campo de comissão passa a se chamar "taxa interna".
- **Orçamento gerado (existente, 077)**: o instantâneo passa a guardar também o **acréscimo do
  vendedor**.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: O revendedor abre agenda + EducaManto e é bloqueado em 100% das outras páginas; não
  consegue editar eventos.
- **SC-002**: "Limpar transporte" zera o transporte e o valor final ajusta.
- **SC-003**: Informar acréscimo aumenta o valor final nesse exato valor e o mostra como comissão do
  vendedor; o PDF inclui o acréscimo no total.
- **SC-004**: A antiga comissão não aparece na calculadora; o cadastro do pacote mostra "Taxa interna".

## Assumptions

- **Acréscimo** é um **valor em R$** somado ao final (como o transporte), igual para todos os pacotes
  do PDF; é a comissão do vendedor; o total do PDF já o inclui (cliente vê o total, sem destacar a
  comissão).
- A restrição do revendedor é aplicada por um **guarda central** (lista de páginas permitidas);
  somente leitura na agenda é garantida pelas permissões de edição já existentes (o perfil não entra
  nelas).
- "Taxa interna" = o `commission_rate` atual do pacote, apenas renomeado/oculto; será usado no futuro
  para o rendimento do Gabriel Lara (fora do escopo desta feature, mas já customizável).
- Restrição vale para usuários **somente** com esse perfil (multi-perfil preserva outros acessos).
