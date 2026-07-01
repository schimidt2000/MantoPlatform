# Feature Specification: Duração de 3 horas na calculadora de orçamentos

**Feature Branch**: `098-orcamento-duracao-3h`

**Created**: 2026-07-01

**Status**: Draft

**Input**: "Na calculadora de orçamentos preciso resolver um problema para o caso de ser um evento de 3 horas. Acredito que a melhor forma seja fazer uma nova coluna de valores e coeficientes para 3 horas que faça sentido na progressão. E permitir que o vendedor selecione por 3 horas também."

## Contexto

A calculadora de orçamentos trabalha hoje com **três durações fixas**: **1h, 2h e 4h**. Todos os preços
de cachê (ator, cantor, técnico, coordenador, especiais) e os coeficientes de markup são definidos como
uma tripla de valores `[1h, 2h, 4h]`. Quando o evento é de **3 horas**, o vendedor não tem uma opção
correta: precisa aproximar por 2h ou 4h, distorcendo o valor.

O pedido é adicionar uma **coluna de 3 horas** — valores de cachê e coeficientes — que **faça sentido na
progressão** existente, e **permitir o vendedor selecionar 3h** na calculadora, junto com as demais
durações.

## Decisões de escopo (confirmadas)

- **Valor padrão de 3h = média entre 2h e 4h** (progressão linear; ex.: ator `[200, 250, 300]` → 3h =
  **275**; markup receptivo `[3.0, 2.7, 2.5]` → 3h = **2.6**). Arredondado, e **editável** nas
  configurações depois.
- **Seleção**: 3h entra como **mais uma duração selecionável** (na ordem natural 1h/2h/**3h**/4h), do
  mesmo jeito que o vendedor já escolhe quais durações incluir hoje.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Selecionar 3h no orçamento (Priority: P1) 🎯 MVP

Como vendedor, quero **incluir a duração de 3 horas** ao montar um orçamento e ver o **valor de 3h**
calculado corretamente, para cotar eventos de 3 horas sem aproximar por 2h ou 4h.

**Why this priority**: É o problema central — hoje não existe 3h. Entrega valor sozinha assim que a
coluna e a seleção existirem.

**Independent Test**: Montar um orçamento marcando a duração de 3h e conferir que o resultado apresenta o
valor de 3h coerente (entre o de 2h e o de 4h) e o inclui na mensagem/resumo.

**Acceptance Scenarios**:

1. **Given** a calculadora, **When** o vendedor abre as durações, **Then** vê **3h** como opção, na ordem
   entre 2h e 4h.
2. **Given** um orçamento com 3h selecionada, **When** calcula, **Then** o resultado mostra o valor de 3h
   junto das demais durações escolhidas.
3. **Given** os cachês/markup atuais, **When** o valor de 3h é calculado, **Then** ele resulta em um
   número **coerente com a progressão** (por padrão, a média entre 2h e 4h) — nunca zero por falta de
   configuração.
4. **Given** que o vendedor seleciona **apenas 3h**, **When** calcula, **Then** o orçamento apresenta só a
   linha de 3h (e o PIX/à vista correspondente), sem quebrar as demais funções.

### User Story 2 - Coluna de 3h nas configurações de preços (Priority: P1)

Como administrador, quero que a **coluna de 3h exista em todos os preços e coeficientes** e seja
**editável** nas configurações, para ajustar os valores de 3h quando necessário.

**Why this priority**: Sem a coluna nos preços/coeficientes, a seleção de 3h não teria de onde tirar o
valor. É pré-requisito do cálculo correto.

**Independent Test**: Abrir as configurações de preços e ver, para cada item (ator, cantor, técnico,
coordenador, especiais, markup), um campo de **3h** já preenchido com o padrão (média 2h–4h) e editável;
salvar uma alteração e ver o orçamento refletir.

**Acceptance Scenarios**:

1. **Given** as configurações de preços, **When** abro qualquer tabela (ator/cantor/técnico/coordenador/
   especiais/markup), **Then** vejo um campo de **3h** entre o de 2h e o de 4h.
2. **Given** uma configuração **já salva** (só com 1h/2h/4h), **When** o sistema carrega os preços,
   **Then** o valor de 3h é **preenchido automaticamente** com a média entre 2h e 4h (sem exigir ação
   manual e sem perder os valores existentes).
3. **Given** que edito e salvo um valor de 3h, **When** monto um orçamento com 3h, **Then** o cálculo usa
   o valor salvo.

### User Story 3 - Orçamentos salvos e uso no evento incluem 3h (Priority: P2)

Como usuário, quero que o **histórico de orçamentos** e a **criação de evento a partir do orçamento**
reconheçam a duração de 3h, para o fluxo ponta-a-ponta funcionar.

**Why this priority**: Fecha o ciclo (salvar orçamento → criar evento). Depende de US1/US2.

**Independent Test**: Salvar um orçamento com 3h no histórico e criar um evento a partir dele escolhendo
3h; conferir que o valor de venda e os cachês correspondem à duração de 3h.

**Acceptance Scenarios**:

1. **Given** um orçamento calculado com 3h, **When** é salvo no histórico, **Then** o total de 3h é
   registrado junto dos demais (1h/2h/4h).
2. **Given** um orçamento salvo com 3h, **When** crio um evento a partir dele e escolho **3h**, **Then** o
   valor de venda e os cachês pré-preenchidos correspondem à duração de 3h.
3. **Given** orçamentos antigos **sem** 3h, **When** são exibidos, **Then** continuam funcionando (3h
   apenas ausente/derivada, sem erro).

### Edge Cases

- **Config salva antiga (3 valores)**: ao carregar, injeta o 3h por interpolação; ao salvar de novo, a
  config passa a ter os 4 valores.
- **Duração custom (por horas/entradas)**: a lógica de duração custom passa a considerar 3h como valor
  "padrão" (não recalcula custom para 3h).
- **Especiais com variação (show/cantor/none)**: cada variante ganha seu 3h por interpolação.
- **Valor de 2h maior que o de 4h** (config atípica): a média ainda é aplicada (fica entre os dois),
  sem erro.
- **Somente 3h selecionada**: mensagem/resumo e PIX consideram apenas 3h.

## Requirements *(mandatory)*

### Coluna/coeficiente de 3h

- **FR-001**: O sistema MUST passar a representar cada preço/coeficiente por **quatro** durações
  ordenadas **[1h, 2h, 3h, 4h]** (ator, cantor, técnico, coordenador, especiais e markup).
- **FR-002**: O valor **padrão de 3h** MUST ser a **média entre 2h e 4h** (arredondada de forma coerente
  com o tipo: valores de cachê como inteiro/moeda; coeficientes de markup com precisão decimal).
- **FR-003**: Configurações de preços **já salvas** (com 3 valores) MUST ser **migradas automaticamente**
  no carregamento, inserindo o 3h por interpolação, **sem** alterar os valores existentes e sem exigir
  ação manual.
- **FR-004**: O valor de 3h MUST ser **editável** nas configurações de preços, na mesma tela dos demais.

### Seleção e cálculo

- **FR-005**: A calculadora MUST oferecer **3h** como duração selecionável, exibida na ordem natural
  entre 2h e 4h.
- **FR-006**: Ao selecionar 3h, o resultado MUST apresentar o **valor de 3h** (cachês + markup) junto das
  demais durações escolhidas, incluindo o cálculo de **PIX/à vista** correspondente.
- **FR-007**: O sistema MUST nunca exibir 3h como **zero por ausência de configuração** (sempre há o
  padrão interpolado).

### Persistência e uso

- **FR-008**: O **histórico de orçamentos** MUST registrar o total de 3h junto de 1h/2h/4h.
- **FR-009**: A **criação de evento a partir do orçamento** MUST permitir escolher 3h e pré-preencher
  valor de venda e cachês da duração de 3h.
- **FR-010**: Orçamentos e eventos **anteriores** (sem 3h) MUST continuar funcionando sem erro.

## Key Entities *(include if feature involves data)*

- **Configuração de preços** (existente, JSON): cada tabela de preço/coeficiente passa de 3 para **4
  valores** por duração; o 3h é derivado por interpolação quando ausente.
- **Orçamento salvo** (histórico): ganha o **total de 3h** ao lado de 1h/2h/4h.
- **Evento** (existente): ao ser criado a partir de um orçamento, pode usar a duração de 3h para valor de
  venda e cachês.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% das tabelas de preço/coeficiente passam a ter um valor de 3h; nenhuma exibe 3h como
  zero por falta de configuração.
- **SC-002**: Para os valores atuais, o 3h calculado fica **entre** o de 2h e o de 4h (progressão
  coerente) em 100% dos itens.
- **SC-003**: O vendedor consegue montar e apresentar um orçamento de **3 horas** sem aproximar por 2h/4h.
- **SC-004**: Configurações e orçamentos **já existentes** continuam funcionando após a mudança (0
  regressões perceptíveis; nada quebra por causa do 3h).
- **SC-005**: Um evento criado a partir de um orçamento de 3h reflete o valor de venda/cachês de 3h.

## Assumptions

- **Interpolação linear (média)** entre 2h e 4h é a definição de "faz sentido na progressão"; o admin
  ajusta manualmente onde quiser depois.
- **Arredondamento**: cachês/moeda para inteiro (padrão da calculadora); coeficientes de markup mantendo
  casas decimais suficientes (ex.: 2.6).
- **3h como opção selecionável**, seguindo o mesmo mecanismo de seleção de durações atual (não é forçada
  como padrão de exibição, apenas disponibilizada na ordem correta).
- **Escopo = calculadora principal** do app (`/orcamento`). O eventual calculador separado
  `Manto_Sales/` (projeto à parte) não faz parte desta feature.
- **Sem novos papéis/permissões**: edição de preços continua restrita a quem já edita as configurações;
  seleção de duração continua com quem já usa a calculadora.
