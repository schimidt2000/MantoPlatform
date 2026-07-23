# Feature Specification: Agenda com múltiplas visualizações (Mês, Dia, Lista)

**Feature Branch**: `178-agenda-multiplas-visualizacoes`

**Created**: 2026-07-23

**Status**: Draft

**Input**: User description: "Refinar e expandir o módulo de Agenda (/agenda) para torná-lo fluido, responsivo e com múltiplas visualizações (Mês, Dia e Lista), com base no comportamento do Live e no padrão visual do Google Agenda: seletor de visualização + barra de navegação (‹ Hoje ›), clique no dia da grade mensal abre a visão Dia, visão Dia em linha do tempo (00h–23h) com sobreposição lado a lado de eventos simultâneos, visão Lista agrupada por dia, layout fluido de largura total, responsivo no mobile."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Alternar entre Mês, Dia e Lista (Priority: P1)

Um usuário da equipe (staff autenticado) está na Agenda e precisa mudar rapidamente entre a visão geral do mês, o detalhe de um dia específico e uma lista corrida de eventos, sem perder o contexto da data selecionada.

**Why this priority**: É a fundação de toda a feature — sem o seletor de visualização e a navegação de período, nenhuma das outras visões é alcançável. Sem isso não há MVP.

**Independent Test**: Pode ser testado abrindo `/agenda`, clicando em cada uma das 3 opções do seletor (Mês/Dia/Lista) e confirmando que a tela troca de layout mantendo a mesma data de referência, e que ‹, Hoje e › avançam/retrocedem/resetam o período corretamente em cada modo.

**Acceptance Scenarios**:

1. **Given** a Agenda está aberta na visão Mês, **When** o usuário clica em "Dia" no seletor, **Then** a tela troca para a visão de linha do tempo do dia atualmente selecionado (ou hoje, se nenhum dia foi selecionado), preservando a data de referência.
2. **Given** a Agenda está na visão Dia, mostrando "25 de Julho de 2026", **When** o usuário clica em "›", **Then** a visão avança para "26 de Julho de 2026" sem sair da visão Dia.
3. **Given** a Agenda está na visão Mês, mostrando "Julho de 2026", **When** o usuário clica em "Hoje", **Then** a visão volta para o mês atual (a partir da data real do sistema).
4. **Given** a Agenda está na visão Lista, **When** o usuário clica em "‹", **Then** o período da lista retrocede (mês anterior) e o feed é reordenado para o novo período.

---

### User Story 2 - Clicar num dia da grade mensal para ver o detalhe (Priority: P2)

Um usuário vendo a grade mensal quer saber rapidamente tudo o que está marcado num dia específico, sem precisar contar badges ou clicar em "+N" para expandir a célula.

**Why this priority**: É a ponte natural entre a visão macro (mês) e a visão detalhada (dia) — depende da US1 já existir, mas entrega valor imediato de navegação sem exigir a visão Lista.

**Independent Test**: Na visão Mês, clicar em qualquer número de dia ou em qualquer área vazia da célula do dia (não apenas num evento específico) deve levar diretamente à visão Dia daquela data.

**Acceptance Scenarios**:

1. **Given** a grade mensal exibe o dia 25 com 2 eventos, **When** o usuário clica no número "25" (fora dos badges de evento), **Then** a Agenda alterna para a visão Dia de 25/07/2026.
2. **Given** a grade mensal exibe um dia sem nenhum evento, **When** o usuário clica na célula desse dia, **Then** a Agenda alterna para a visão Dia daquela data, mostrando a linha do tempo vazia.
3. **Given** o usuário clica diretamente sobre o badge de um evento específico na grade, **When** o clique é processado, **Then** o comportamento atual é preservado (abre o detalhe do evento, `/events/:id`) — não o dia.

---

### User Story 3 - Visão Dia em linha do tempo com sobreposição (Priority: P1)

Um usuário precisa entender, num único dia, exatamente em que horário cada evento começa/termina e identificar rapidamente conflitos de horário (dois compromissos simultâneos), algo que a grade mensal não consegue mostrar em detalhe.

**Why this priority**: É o principal ganho funcional pedido — a visão que replica o "estilo Google Agenda" e resolve o caso de uso real de detectar sobreposição de horários entre shows/ensaios. Crítica o suficiente para ser P1 junto com a US1.

**Independent Test**: Pode ser testado isoladamente carregando a visão Dia de uma data com eventos conhecidos (via seed/fixture) e conferindo que cada bloco aparece na altura vertical correspondente ao seu horário, e que dois eventos com horários sobrepostos aparecem lado a lado (colunas), sem um cobrir o outro.

**Acceptance Scenarios**:

1. **Given** um dia com um evento das 14:00 às 16:00, **When** a visão Dia é carregada, **Then** o bloco do evento é renderizado ocupando a faixa vertical correspondente a 14:00–16:00 na grade de horários de 00:00 a 23:00.
2. **Given** um dia com dois eventos que se sobrepõem (ex.: 14:00–16:00 e 15:00–17:00), **When** a visão Dia é carregada, **Then** os dois blocos são exibidos lado a lado (colunas), cada um com largura reduzida proporcionalmente, sem sobrepor visualmente o texto um do outro.
3. **Given** um evento sem horário de início/fim definido (`start_at`/`end_at` nulos), **When** a visão Dia é carregada, **Then** o evento aparece numa área separada de "sem horário" no topo ou rodapé da visão, e não quebra o layout da linha do tempo.
4. **Given** um bloco de evento na linha do tempo, **When** o usuário observa o bloco, **Then** ele exibe categoria (ex.: R&I, SHOW, ENSAIO), nome do evento, horário de início–fim e o local/endereço (quando houver).
5. **Given** um bloco de evento na linha do tempo, **When** o usuário clica nele, **Then** a navegação para o detalhe do evento (`/events/:id`) ocorre, mantendo o padrão já usado na grade mensal.

---

### User Story 4 - Visão em Lista (feed cronológico) (Priority: P2)

Um usuário que prefere escanear os compromissos em formato de lista corrida (sem grade visual) — por exemplo, para revisar rapidamente tudo que vem no mês, dia a dia, com local e categoria bem legíveis — usa a visão Lista.

**Why this priority**: Complementa as outras duas visões com um formato mais compacto e legível, especialmente valioso no mobile, mas o produto já entrega valor central sem ela (por isso P2, depois de Mês+Dia).

**Independent Test**: Pode ser testado carregando a visão Lista de um mês com eventos em múltiplos dias e conferindo que os eventos aparecem agrupados por dia, em ordem cronológica, cada item com horário, badge de categoria, título, local e botão "Abrir".

**Acceptance Scenarios**:

1. **Given** o mês corrente tem eventos em 3 dias distintos, **When** a visão Lista é aberta, **Then** os eventos aparecem agrupados sob um cabeçalho por dia (ex.: "Sexta-feira, 25 de julho"), em ordem cronológica dentro do dia e os dias em ordem cronológica entre si.
2. **Given** um item na Lista, **When** o usuário observa o item, **Then** ele exibe horário, badge colorido da categoria, título do evento, local (quando houver) e um botão "Abrir" alinhado à direita.
3. **Given** um item na Lista, **When** o usuário clica no botão "Abrir" (ou no item), **Then** a navegação leva ao detalhe do evento (`/events/:id`).
4. **Given** um evento sem horário definido, **When** a visão Lista é montada, **Then** o evento ainda aparece no dia correspondente (se houver data) com indicação de "sem horário definido", ou numa seção separada "sem data" (paridade com o comportamento atual da visão Mês).

---

### User Story 5 - Layout fluido e responsivo (Priority: P3)

Um usuário em monitor widescreen quer que a Agenda aproveite toda a largura da tela (hoje limitada a uma coluna central estreita); um usuário no celular quer que a visão Dia/Lista continue perfeitamente legível em telas pequenas.

**Why this priority**: É uma melhoria de qualidade visual/ergonômica que se aplica a todas as visões já entregues nas histórias anteriores — por isso vem depois, como polimento, embora seja parte explícita do pedido original.

**Independent Test**: Pode ser testado redimensionando a janela do navegador (ou usando o inspetor de dispositivo) entre um viewport widescreen (ex.: 1920px) e mobile (320–375px) em cada uma das 3 visões, e conferindo que não há barra de rolagem horizontal indevida, texto cortado, ou espaço desperdiçado excessivo nas laterais em telas largas.

**Acceptance Scenarios**:

1. **Given** a Agenda é aberta num monitor widescreen (≥1920px), **When** qualquer uma das 3 visões é exibida, **Then** o conteúdo ocupa a largura total disponível da área de conteúdo (respeitando o menu lateral fixo), sem uma coluna central artificialmente estreita.
2. **Given** a Agenda é aberta num viewport mobile (320–375px), **When** a visão Dia é exibida, **Then** a linha do tempo permanece legível (sem texto cortado ou blocos ilegíveis), com rolagem vertical normal e sem rolagem horizontal da página.
3. **Given** a Agenda é aberta num viewport mobile, **When** a visão Lista é exibida, **Then** cada item do feed se adapta em coluna única, com o botão "Abrir" continuando acessível e clicável.

---

### Edge Cases

- Dia/mês sem nenhum evento: a visão Dia mostra a linha do tempo vazia (sem erro); a visão Lista mostra um estado vazio amigável para o período; a visão Mês já trata isso hoje.
- Mais de 2 eventos simultâneos no mesmo intervalo de horário (3+): a visão Dia deve dividir o espaço horizontal entre todos os eventos sobrepostos daquele intervalo, mantendo cada bloco legível (título pode truncar com reticências, mas categoria e horário permanecem visíveis).
- Evento que atravessa a meia-noite (ex.: início 23:00, fim 01:00 do dia seguinte): tratado como caso de escopo reduzido — o evento é exibido no dia de início, com o bloco truncado visualmente ao final da grade (23:59), sem exigir renderização contínua no dia seguinte.
- Evento sem `location`: o bloco/linha da lista omite o campo de local sem deixar espaço vazio quebrado.
- Navegação rápida repetida em ‹/› (cliques em sequência): cada clique deve resultar em uma transição de período válida, sem estados intermediários quebrados ou race condition visível no carregamento dos dados do novo período.
- Troca de visualização (Mês→Dia→Lista) deve preservar a "data de referência" (o dia/mês selecionado), não resetar sempre para hoje.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: A Agenda MUST exibir um seletor de visualização com 3 opções mutuamente exclusivas: "Mês", "Dia" e "Lista", com a opção ativa claramente destacada visualmente.
- **FR-002**: A Agenda MUST exibir controles de navegação de período (‹, "Hoje", ›) e um título dinâmico que reflete o período/data corrente exibido (ex.: "Julho de 2026" na visão Mês/Lista; "25 de julho de 2026" na visão Dia).
- **FR-003**: Ao clicar em ‹ ou ›, o sistema MUST avançar/retroceder o período de acordo com a visão ativa (um dia na visão Dia; um mês nas visões Mês e Lista).
- **FR-004**: Ao clicar em "Hoje", o sistema MUST retornar ao dia/mês atual (data real do sistema no momento do clique), independentemente da visão ativa.
- **FR-005**: Trocar entre Mês/Dia/Lista MUST preservar a data de referência atualmente selecionada (não resetar para hoje ao trocar de visão).
- **FR-006**: Na visão Mês, clicar no número do dia ou em qualquer área da célula do dia que não seja um evento específico MUST alternar a Agenda para a visão Dia daquela data.
- **FR-007**: Na visão Mês, clicar diretamente num evento (badge) dentro da célula MUST continuar navegando para o detalhe do evento (`/events/:id`), preservando o comportamento atual — não deve ser interpretado como clique no dia.
- **FR-008**: A visão Dia MUST renderizar uma grade vertical de horários cobrindo 00:00 a 23:00.
- **FR-009**: Na visão Dia, cada evento com horário de início e fim definidos MUST ser posicionado verticalmente de forma proporcional ao seu horário de início/fim dentro da grade de 00:00–23:00.
- **FR-010**: Na visão Dia, quando dois ou mais eventos do mesmo dia tiverem intervalos de horário sobrepostos, o sistema MUST exibi-los lado a lado (em colunas), dividindo o espaço horizontal disponível entre eles, sem sobreposição visual do conteúdo de um bloco sobre o outro.
- **FR-011**: Cada bloco de evento na visão Dia MUST exibir: categoria do evento, nome do evento, horário de início–fim e local/endereço (quando disponível).
- **FR-012**: Eventos sem horário de início/fim definidos MUST aparecer numa área distinta da visão Dia (fora da grade de horários), sem quebrar o posicionamento dos demais eventos.
- **FR-013**: A visão Lista MUST agrupar os eventos do período corrente por dia, em ordem cronológica (dias em ordem crescente; eventos dentro do dia em ordem de horário).
- **FR-014**: Cada item da visão Lista MUST exibir horário, badge colorido de categoria, título do evento, local (quando houver) e um botão "Abrir" alinhado à direita.
- **FR-015**: Clicar num bloco de evento (visão Dia) ou num item/botão "Abrir" (visão Lista) MUST navegar para o detalhe do evento (`/events/:id`), consistente com o padrão de navegação já usado na visão Mês.
- **FR-016**: O container principal da página de Agenda MUST ocupar a largura total disponível da área de conteúdo (respeitando a barra lateral fixa do layout interno), removendo a restrição de largura máxima estreita usada atualmente.
- **FR-017**: Todas as 3 visões MUST se adaptar a viewports mobile (a partir de ~320px de largura) sem rolagem horizontal da página e sem cortar texto essencial (categoria, horário, título).
- **FR-018**: O sistema MUST usar as mesmas categorias e cores de evento já definidas hoje (R&I, SHOW, CORP, VM, SOCIAL, e fallback "Outro" para tipos não mapeados, incluindo ENSAIO) em todas as 3 visões, sem introduzir uma nova paleta.
- **FR-019**: A visão Lista e a visão Dia MUST reutilizar os dados já retornados pelos endpoints de agenda existentes (mês e dia), sem exigir novos campos que não existem hoje na resposta da API (título, horário início/fim, local, categoria derivada do título, personagens, satélite/grupo, confirmado).

### Key Entities

- **Evento de Agenda (resumo)**: representação já existente de um evento no período — título, categoria (derivada do prefixo do título), horário de início e fim (opcionais), local, e indicadores de satélite/confirmação. Não inclui dados financeiros nesta camada.
- **Período de visualização**: estado de UI (não persistido) que define a visão ativa (Mês/Dia/Lista) e a data de referência associada — controla o que é buscado e exibido em cada troca de visão ou navegação ‹/Hoje/›.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A partir de qualquer uma das 3 visões, um usuário consegue chegar ao detalhe de um evento específico em no máximo 2 cliques.
- **SC-002**: Um usuário consegue identificar visualmente, sem rolar ou abrir nenhum evento, se há conflito de horário (eventos simultâneos) num dia específico, ao abrir a visão Dia daquele dia.
- **SC-003**: Em telas widescreen (≥1920px), a área de conteúdo da Agenda ocupa pelo menos 90% da largura disponível ao lado do menu — contra a coluna estreita atual.
- **SC-004**: Em viewport mobile (320–375px), todas as 3 visões permanecem utilizáveis sem exigir zoom ou rolagem horizontal.
- **SC-005**: Trocar de visão (Mês↔Dia↔Lista) ou navegar ‹/Hoje/› não exige recarregar a página nem perde a data de referência selecionada.

## Assumptions

- A feature é somente de frontend (React, `frontend/apps/internal`), reaproveitando os endpoints já existentes de agenda mensal (`GET /api/agenda?ym=`) e diária (`GET /api/agenda/day/<data>`, já implementado no backend porém sem consumidor hoje). Nenhuma mudança de backend é esperada, exceto se a visão Dia revelar necessidade de ajuste pontual no endpoint diário já existente.
- A visão Lista usa o mesmo período/granularidade de mês já suportado pela API (não há endpoint de range arbitrário de datas); "o período" da Lista é o mês de referência corrente, com navegação ‹/› em incrementos mensais — igual à visão Mês.
- Clique em evento continua navegando para a página de detalhe completa (`/events/:id`), sem introduzir modal — mantendo o padrão de UX já estabelecido no restante do módulo.
- Categorias e cores de evento são as já existentes hoje no sistema (R&I, SHOW, CORP, VM, SOCIAL, fallback cinza "Outro" para ENSAIO e tipos desconhecidos) — não é criada nova categoria nem nova paleta.
- Evento que atravessa a meia-noite é tratado no dia de início, com o bloco visualmente truncado ao final da grade (23:59) — não é renderizado contínuo no dia seguinte (fora de escopo desta iteração).
- "Endereço/Local" no bloco de evento corresponde ao campo `location` já existente no resumo do evento retornado pela API.
- O público desta feature é o staff autenticado do sistema interno (não há mudança em superfícies públicas).
