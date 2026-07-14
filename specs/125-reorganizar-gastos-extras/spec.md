# Feature Specification: Reorganizar e Filtrar a Tela de Gastos Extras

**Feature Branch**: `125-reorganizar-gastos-extras`

**Created**: 2026-07-13

**Status**: Draft

**Input**: "Acho que a página dos gastos extras está meio fora do padrão do restante. Além
de ser muito ruim de visualizar. E preciso que ela seja filtrável também e que seja
organizada de uma forma que faça sentido com o restante do sistema."

## Contexto

A tela de Gastos Extras (`/gastos/`) hoje mistura, sem hierarquia visual clara, um
formulário de cadastro sempre aberto (o mais longo do sistema, com vários blocos
condicionais) empilhado diretamente acima de uma tabela de histórico densa — quem entra
na tela para consultar ou aprovar um gasto precisa rolar por todo o formulário primeiro.
A lista não tem nenhuma forma de filtrar por situação, categoria ou buscar por texto, ao
contrário de telas equivalentes do sistema (ex.: Planilha de Pagamentos, em
`/financeiro/pagamentos`, já usa cartões de resumo clicáveis como filtro + busca por
texto em tempo real). Os badges de status usam cor solta no HTML em vez das classes de
badge já padronizadas no restante do sistema (`badge-green`, `badge-amber`, `badge-red`,
`badge-gray`), e a tela não mostra um resumo no cabeçalho como as demais listas do
sistema mostram (ex.: "42 clientes na base").

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Filtrar e encontrar um gasto rapidamente (Priority: P1)

Um super admin entra em Gastos Extras para revisar o que está pendente de aprovação.
Em vez de rolar toda a lista, ele clica no cartão "Pendentes" e vê só os gastos
pendentes; ou digita parte da descrição/categoria/nome de quem registrou na busca e a
lista filtra na hora, sem recarregar a página.

**Why this priority**: é o pedido explícito e mais concreto ("preciso que ela seja
filtrável") — sem isso, a tela continua difícil de usar conforme a lista cresce.

**Independent Test**: com pelo menos um gasto em cada situação (pendente, aprovado,
rejeitado), clicar em cada cartão de resumo e confirmar que só os gastos daquela
situação aparecem; digitar um termo de busca e confirmar que só as linhas compatíveis
aparecem, sem reload da página.

**Acceptance Scenarios**:

1. **Given** gastos em situações diferentes, **When** o usuário clica no cartão
   "Pendentes", **Then** a lista mostra só os gastos pendentes, e o cartão fica marcado
   como filtro ativo.
2. **Given** um filtro de situação ativo, **When** o usuário clica de novo no mesmo
   cartão, **Then** o filtro é removido e a lista volta a mostrar todos.
3. **Given** qualquer estado de filtro, **When** o usuário digita um termo na busca
   (parte da descrição, categoria, nome de quem registrou, fornecedor/funcionário ou
   valor), **Then** a lista mostra só as linhas que contêm esse termo, combinando com o
   filtro de situação já ativo.
4. **Given** uma combinação de filtro + busca sem nenhum resultado, **When** a lista
   fica vazia, **Then** uma mensagem clara explica que não há resultados e oferece limpar
   a busca.

---

### User Story 2 - Ver a lista sem precisar rolar o formulário inteiro (Priority: P2)

Um usuário comum entra na tela só para conferir os próprios gastos (não para cadastrar um
novo). A lista de gastos aparece em posição de destaque, sem precisar rolar por um
formulário de cadastro totalmente aberto primeiro. Quando ele quer registrar um gasto
novo, encontra facilmente onde abrir o formulário.

**Why this priority**: é a segunda parte do pedido ("muito ruim de visualizar",
"organizada de forma que faça sentido") — depende de existir uma lista para filtrar
(US1), mas é sobre a hierarquia visual da tela como um todo.

**Independent Test**: abrir a tela e confirmar que a lista de gastos é visível sem rolar
por um formulário longo primeiro; confirmar que o formulário de cadastro continua
acessível e funcional a partir de uma ação clara (ex.: botão "Novo gasto").

**Acceptance Scenarios**:

1. **Given** a tela de Gastos Extras carregada, **When** o usuário olha a tela sem
   rolar, **Then** ele já vê o resumo (cartões) e o início da lista de gastos.
2. **Given** a tela carregada, **When** o usuário quer registrar um gasto novo, **Then**
   existe uma ação clara e visível para abrir o formulário, e o formulário continua tendo
   exatamente os mesmos campos e validações de hoje.
3. **Given** o cabeçalho da tela, **When** o usuário olha o topo, **Then** vê um resumo
   textual (ex.: quantidade de gastos) no mesmo estilo usado nas outras listas do sistema.

### Edge Cases

- Nenhum gasto registrado ainda: a tela mostra o estado vazio de forma clara, sem cartões
  de filtro quebrados ou lista "fantasma".
- Usuário comum (não super admin) não vê os cartões de balanço financeiro nem os gastos
  de terceiros — igual ao comportamento de acesso já existente hoje; os novos filtros só
  atuam sobre os gastos que o usuário já pode ver.
- Um gasto rejeitado com motivo, ou vinculado a um evento, continua mostrando essas
  informações extras mesmo com filtro/busca ativos.
- Filtro/busca não pode afetar o que é aprovado, rejeitado ou excluído — são só uma forma
  de visualizar, nunca de restringir ação.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: A lista de gastos DEVE poder ser filtrada por situação (pendente, aprovado,
  rejeitado) através de um clique, sem recarregar a página, seguindo o mesmo padrão de
  interação já usado na Planilha de Pagamentos (cartão de resumo clicável).
- **FR-002**: A lista DEVE ter uma busca por texto livre que encontre gastos pela
  descrição, categoria, nome de quem registrou, nome do fornecedor/funcionário
  reembolsado, ou valor — atualizando a lista em tempo real, sem recarregar a página.
- **FR-003**: O filtro de situação e a busca DEVEM poder ser combinados ao mesmo tempo.
- **FR-004**: A tela DEVE reorganizar a hierarquia visual para que a lista de gastos
  fique em posição de destaque, sem exigir rolar por todo o formulário de cadastro para
  chegar até ela.
- **FR-005**: O formulário de registrar um gasto novo DEVE continuar com exatamente os
  mesmos campos, validações e comportamento de hoje (nada de campo removido/alterado) —
  só a forma como ele aparece na tela muda.
- **FR-006**: Os indicadores de situação (badges) DEVEM usar as mesmas classes visuais já
  padronizadas no restante do sistema, em vez de cor solta no HTML.
- **FR-007**: O cabeçalho da tela DEVE mostrar um resumo (ex.: quantidade de gastos)
  seguindo o mesmo padrão visual usado no cabeçalho de outras listas do sistema.
- **FR-008**: Nenhuma regra de acesso existente pode mudar — super admin continua vendo
  todos os gastos e o balanço; usuário comum continua vendo só os próprios gastos, sem
  balanço.

### Key Entities

Nenhuma entidade nova — a feature reorganiza a apresentação de `SpecialExpense`
(já existente), sem mudança de schema.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Um usuário consegue ver só os gastos de uma situação específica com um
  único clique, sem esperar carregamento de página.
- **SC-002**: Uma busca por texto reduz a lista aos gastos relevantes instantaneamente
  (sem reload) em qualquer combinação com o filtro de situação.
- **SC-003**: A lista de gastos é visível na tela sem precisar rolar por um formulário de
  cadastro totalmente expandido.
- **SC-004**: O cadastro de um gasto novo continua funcionando exatamente como hoje —
  100% dos campos e validações preservados.
- **SC-005**: A tela usa exclusivamente as classes de badge/cartão já padronizadas no
  sistema — zero cor solta nova adicionada para indicar situação.

## Assumptions

- O padrão de referência para "faça sentido com o restante do sistema" é a Planilha de
  Pagamentos (`/financeiro/pagamentos`) — página do mesmo domínio (financeiro) que já
  resolve exatamente esse problema (cartões clicáveis como filtro + busca em tempo real
  sobre uma lista renderizada no servidor, sem recarregar a página).
- "Organizada de uma forma que faça sentido" é interpretado como: colapsar/recolher o
  formulário de cadastro por padrão (ação explícita para abri-lo) e dar destaque à lista
  — não como criar uma página separada para o cadastro, o que mudaria mais navegação do
  que o pedido sugere.
- O filtro por categoria fica coberto pela busca de texto livre (FR-002), sem precisar de
  um seletor dedicado — mesmo padrão já usado na Planilha de Pagamentos, que também não
  tem um seletor dedicado por tipo de pagamento além da busca.
- Mudanças ficam restritas à apresentação (template + pequeno JS de filtro no navegador);
  nenhuma rota, permissão ou regra de negócio do backend muda.
