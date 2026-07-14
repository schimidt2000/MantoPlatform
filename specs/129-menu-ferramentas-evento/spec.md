# Feature Specification: Menu de Ferramentas na Página do Evento

**Feature Branch**: `129-menu-ferramentas-evento`

**Created**: 2026-07-14

**Status**: Draft

**Input**: "Na tela individual do evento senti que agora tem muitos botões e funções,
ficou bagunçado. Seria legal se tivesse um botão no estilo reticências para clicar e
aparecer todas essas tools organizadas."

## Contexto

O topo da página de um evento acumulou, ao longo de várias features, sete botões de
ação lado a lado (sincronizar com o Google, exportar elenco, editar no Google Agenda,
confirmar dados do evento, marcar evento como confirmado, cobrança, excluir evento) —
além do link para voltar à agenda. Em telas menores esses botões quebram em várias
linhas, e mesmo em telas grandes a quantidade deixa o topo da página poluído visualmente,
sem hierarquia entre o que é comum e o que é raro de usar.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Ver a página do evento sem o topo poluído de botões (Priority: P1)

Um usuário abre a página de um evento e vê o topo limpo: o título do evento e um único
botão de reticências reunindo as ferramentas que hoje ficam soltas lado a lado. Clicando
nele, vê a lista organizada de tudo que pode fazer naquele evento.

**Why this priority**: é o pedido direto — resolve a poluição visual relatada.

**Independent Test**: abrir a página de um evento e contar quantos elementos aparecem
soltos no topo antes de qualquer clique; deve ser só o botão de reticências (e o link de
voltar), não os sete botões de hoje.

**Acceptance Scenarios**:

1. **Given** a página de um evento, **When** o usuário olha o topo sem clicar em nada,
   **Then** vê um único botão de reticências reunindo as ferramentas, no lugar dos
   botões soltos de hoje.
2. **Given** o botão de reticências, **When** o usuário clica nele, **Then** aparece uma
   lista organizada com todas as ferramentas que ele tem permissão de usar naquele
   evento.
3. **Given** o menu aberto, **When** o usuário clica fora dele ou aperta Esc, **Then** o
   menu fecha sem executar nenhuma ação.
4. **Given** qualquer ferramenta dentro do menu, **When** o usuário clica nela,
   **Then** ela funciona exatamente como funciona hoje (mesmo resultado, mesma
   confirmação quando for uma ação destrutiva) — só a localização visual muda.

### Edge Cases

- Um usuário sem permissão para uma das ferramentas (ex.: sem papel comercial) não deve
  ver essa ferramenta no menu — a mesma regra de acesso que já existe hoje por botão
  continua valendo dentro do menu.
- Se, para o evento em questão, nenhuma ferramenta do menu se aplica (ex.: evento sem
  vínculo com o Google Agenda) ou nenhuma é permitida para aquele usuário, o botão de
  reticências não deve abrir uma lista vazia sem explicação.
- Ações que hoje pedem confirmação antes de executar (ex.: excluir evento) continuam
  pedindo confirmação exatamente da mesma forma depois de organizadas no menu.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O topo da página do evento DEVE mostrar um único botão (estilo
  reticências) reunindo as ferramentas que hoje aparecem como botões soltos:
  sincronizar com o Google, exportar elenco, editar no Google Agenda, confirmar dados
  do evento, marcar/desmarcar evento como confirmado, cobrança e excluir evento.
- **FR-002**: Clicar no botão de reticências DEVE abrir uma lista organizada com essas
  ferramentas, e clicar fora ou apertar Esc DEVE fechá-la sem executar nada.
- **FR-003**: Cada ferramenta dentro do menu DEVE continuar visível apenas para quem já
  tinha permissão de vê-la hoje — nenhuma regra de acesso muda.
- **FR-004**: Cada ferramenta DEVE continuar se comportando exatamente como hoje
  (mesma ação, mesmo destino, mesma confirmação antes de ações destrutivas) — a
  mudança é só de organização visual, nunca de comportamento.
- **FR-005**: O link para voltar à agenda permanece visível fora do menu (é navegação,
  não uma ferramenta do evento).
- **FR-006**: Se, para o evento e o usuário atuais, nenhuma ferramenta do menu se
  aplicar, o botão de reticências não é mostrado (em vez de abrir uma lista vazia).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: O número de botões soltos e visíveis no topo da página do evento cai de
  sete para um (o de reticências) mais o link de voltar.
- **SC-002**: 100% das ferramentas continuam acessíveis e funcionando exatamente como
  antes, agora dentro do menu.
- **SC-003**: A regra de quem vê cada ferramenta permanece idêntica à de hoje, testada
  para pelo menos dois papéis diferentes.

## Assumptions

- O escopo é o conjunto de botões do topo da página (a barra de ações do cabeçalho) —
  os botões que já vivem dentro de seções específicas do evento (casting, figurino,
  dados comerciais, etc., cada um ligado a uma linha/item concreto daquela seção) não
  fazem parte deste menu, porque não são "ferramentas da página" no mesmo sentido —
  continuam onde estão, junto do que cada um controla.
- A ordem das ferramentas dentro do menu segue a mesma ordem em que os botões aparecem
  hoje no topo, sem reordenar por critério novo.
