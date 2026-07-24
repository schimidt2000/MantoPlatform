# Feature Specification: Resumo das Avaliações — fidelidade visual e RBAC de anonimato

**Feature Branch**: `181-avaliacoes-fidelidade-rbac`

**Created**: 2026-07-24

**Status**: Draft

**Input**: User description: "Reestruturar e refinar por completo a página de Resumo das Avaliações (React, /casting/avaliacoes em frontend/apps/internal), restaurando a riqueza visual e os gráficos do sistema Jinja legado (Live) e corrigindo o controle de privacidade por RBAC. Barra de filtros rica em pills (período incl. última semana, filtrar por data do evento/avaliação, categoria, evento), painel de KPIs e gráficos (tendência mensal, distribuição de notas, média por categoria, melhores/piores eventos), blocos de pontos de atenção e comentários, layout widescreen sem max-w estreito."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Consultar o panorama de avaliações com a mesma riqueza do sistema clássico (Priority: P1)

Um usuário autenticado (Casting, Produção, Comercial, Superadmin etc.) acessa `/casting/avaliacoes` para entender como os eventos recentes foram avaliados pelo elenco: nota geral, distribuição de notas, tendência ao longo dos meses, médias por categoria (Artista, Som, Figurino, Texto, Coordenação, Maquiagem) e quais eventos se saíram melhor ou pior. Hoje a versão em React só mostra 3 KPIs simples e uma lista de comentários — sem os gráficos e painéis que o sistema clássico (Jinja) sempre teve.

**Why this priority**: É a razão de existir da tela — sem os gráficos e painéis, a tela em React entrega menos valor que a versão antiga que está sendo substituída, e o time volta a preferir o sistema legado.

**Independent Test**: Acessar `/casting/avaliacoes` com dados de avaliação existentes e confirmar que aparecem os 3 KPIs principais e os 4 painéis de gráficos/rankings (tendência mensal, distribuição de notas, média por categoria, melhores/piores eventos), com os mesmos números que a página Jinja equivalente (`/talents/avaliacoes`) mostra para o mesmo recorte.

**Acceptance Scenarios**:

1. **Given** existem avaliações registradas em múltiplos meses, **When** o usuário abre a tela sem filtro, **Then** vê a nota média geral (com estrelas), o total de avaliações e o número de eventos avaliados no topo, e um gráfico de tendência mensal abaixo.
2. **Given** existem avaliações com notas variadas, **When** o usuário visualiza o painel "Distribuição das notas", **Then** vê uma barra horizontal para cada nota de 5 a 1 estrelas, com o comprimento proporcional à contagem e o número exato ao lado.
3. **Given** existem sub-notas por categoria (Artista, Som, Figurino, Texto, Coordenação, Maquiagem), **When** nenhum filtro de categoria está ativo, **Then** o painel "Média por categoria" mostra uma linha por categoria com estrelas e nota média, e cada linha é clicável para filtrar por aquela categoria.
4. **Given** múltiplos eventos avaliados, **When** o usuário visualiza o painel de ranking, **Then** vê até 3 eventos com melhor média e até 3 com pior média (quando houver pelo menos 2 eventos avaliados), cada um clicável para focar naquele evento.
5. **Given** nenhuma avaliação no recorte atual, **When** a tela carrega, **Then** é exibido um estado vazio claro em vez de gráficos quebrados ou em branco.

---

### User Story 2 - Filtrar o panorama com a mesma riqueza de opções do sistema clássico (Priority: P1)

Um usuário quer refinar a visão para um recorte específico: só o último mês, só a categoria "Figurino", só um evento específico, ou comparando data do evento vs. data em que a avaliação foi enviada. Hoje o React só oferece dropdowns simples de evento/categoria/período; o Jinja legado oferece pills de acesso rápido, incluindo uma opção de período que o React nem tem ("última semana").

**Why this priority**: Sem filtros rápidos e visualmente claros, o usuário não consegue chegar ao recorte que precisa em poucos cliques — é a interação mais frequente da tela, junto da User Story 1.

**Independent Test**: Na tela `/casting/avaliacoes`, clicar em cada pill de período (Tudo, Última semana, 30 dias, 3 meses, 12 meses, Personalizado), cada pill de categoria, e alternar entre "Data do evento"/"Data da avaliação", confirmando que os KPIs e listas recalculam para refletir cada seleção, e que a seleção ativa fica visualmente destacada.

**Acceptance Scenarios**:

1. **Given** a tela carregada sem filtros, **When** o usuário clica na pill "Última semana", **Then** o recorte passa a considerar apenas avaliações dos últimos 7 dias e a pill fica destacada como ativa.
2. **Given** a tela carregada, **When** o usuário clica em "Personalizado" e informa duas datas (início e fim) e clica em "Aplicar", **Then** o recorte reflete exatamente esse intervalo.
3. **Given** o usuário alterna o modo "Filtrar por" entre "Data do evento" e "Data da avaliação", **When** um período pré-definido está ativo, **Then** o recorte é recalculado usando a coluna de data correspondente escolhida.
4. **Given** o usuário clica em uma pill de categoria (ex.: "Figurino"), **When** a seleção é aplicada, **Then** apenas os dados daquela categoria aparecem nos KPIs, distribuição de notas e comentários, e o painel "Média por categoria" (que compara todas as categorias) deixa de ser exibido.
5. **Given** o usuário seleciona um evento específico no dropdown de eventos, **When** a seleção é aplicada, **Then** a tela passa para uma visão focada naquele evento (sem o filtro de período, já que o recorte já é o evento) e os painéis de ranking de eventos somem (não fazem sentido para um único evento).
6. **Given** filtros ativos, **When** o usuário aciona "Limpar filtros", **Then** todos os filtros voltam ao estado padrão ("Tudo"/"Todas"/nenhum evento).

---

### User Story 3 - Ver pontos de atenção e comentários recentes com contexto completo (Priority: P2)

Um usuário quer identificar rapidamente avaliações críticas (notas 1-2 estrelas) para agir sobre elas, e acompanhar os comentários mais recentes de forma geral. Hoje o React já mostra "Pontos de atenção" e "Comentários", mas sem o destaque visual de alerta (vermelho) nem a mesma riqueza de contexto (categoria, evento, autor) do sistema clássico.

**Why this priority**: É importante para ação corretiva, mas depende dos KPIs/filtros (US1/US2) para ter o recorte certo primeiro — por isso prioridade P2.

**Independent Test**: Com uma avaliação de nota 1 ou 2 registrada no recorte, confirmar que ela aparece destacada em tom de alerta no bloco "Pontos de atenção", com nota, categoria, autor (respeitando a regra de anonimato), nome do evento e texto do comentário (ou indicação de que não há comentário).

**Acceptance Scenarios**:

1. **Given** existe ao menos uma avaliação com nota 1 ou 2 no recorte atual, **When** a tela carrega, **Then** o bloco "Pontos de atenção" aparece com destaque visual de alerta (borda/tom vermelho) e lista cada avaliação crítica com badge de nota, categoria, autor, evento e data.
2. **Given** não existe nenhuma avaliação com nota 1 ou 2 no recorte, **When** a tela carrega, **Then** o bloco "Pontos de atenção" mostra uma confirmação positiva (ex.: "nenhuma nota baixa no recorte") em vez de lista vazia sem explicação.
3. **Given** existem comentários com texto no recorte, **When** o usuário visualiza o bloco "Comentários", **Then** vê até um limite razoável dos mais recentes, cada um com estrelas, categoria, nome do evento e data de envio.

---

### User Story 4 - Confiar que a autoria das avaliações respeita a política de anonimato por papel (Priority: P1)

O sistema tem uma política de privacidade: por padrão, todos os usuários (exceto SUPERADMIN) sempre veem "Anônimo" como autor de qualquer avaliação — nunca o nome de quem avaliou. Apenas o SUPERADMIN pode, opcionalmente, ver a autoria real, e apenas o SUPERADMIN tem acesso a um controle para desativar completamente a exibição de autoria até para ele mesmo ("modo anônimo total"). Esse controle não deve aparecer para nenhum outro papel.

**Why this priority**: É uma regra de privacidade não-negociável (dado sensível de avaliação de desempenho) — uma falha aqui expõe autoria indevidamente ou permite que um usuário sem permissão altere a política para todo o sistema. Prioridade máxima junto da US1.

**Independent Test**: Acessar a tela autenticado como um usuário sem papel SUPERADMIN e confirmar que (a) nenhum controle de "ativar/desativar modo anônimo total" é exibido em nenhum lugar da tela, e (b) todo campo de autoria em qualquer lista (pontos de atenção, comentários) mostra exatamente "Anônimo". Repetir autenticado como SUPERADMIN e confirmar que o controle aparece e que, com o modo anônimo total desativado, a autoria real é exibida.

**Acceptance Scenarios**:

1. **Given** um usuário autenticado sem papel SUPERADMIN, **When** ele acessa a tela, **Then** nenhum botão ou toggle de "modo anônimo total" é exibido em qualquer parte da página.
2. **Given** um usuário autenticado sem papel SUPERADMIN, **When** ele visualiza qualquer avaliação (ponto de atenção ou comentário), **Then** o campo de autor sempre mostra "Anônimo", independentemente do estado do modo anônimo total.
3. **Given** um usuário SUPERADMIN, **When** ele acessa a tela, **Then** vê o controle de "modo anônimo total" com o estado atual (ativo/inativo) claramente indicado.
4. **Given** um usuário SUPERADMIN com o modo anônimo total desativado, **When** ele visualiza uma avaliação, **Then** vê o nome de quem avaliou (e sua função no evento, quando disponível).
5. **Given** um usuário SUPERADMIN ativa o modo anônimo total, **When** a ação é confirmada, **Then** a autoria deixa de ser exibida até mesmo para ele, em toda a tela, até que o modo seja desativado novamente.

---

### User Story 5 - Usar a tela confortavelmente em monitores widescreen (Priority: P3)

Um usuário em um monitor grande (desktop de produção) quer que a tela aproveite o espaço disponível em vez de ficar confinada a uma coluna estreita centralizada, especialmente com o grid de gráficos 2x2 e as listas de comentários.

**Why this priority**: Melhoria de conforto/produtividade, mas não bloqueia nenhuma decisão de negócio — por isso a menor prioridade entre as cinco.

**Independent Test**: Abrir a tela em uma janela larga (≥1440px) e confirmar que o conteúdo se estende por boa parte da largura da tela (com padding lateral adequado), em vez de ficar limitado a uma coluna centralizada estreita.

**Acceptance Scenarios**:

1. **Given** uma janela widescreen (≥1440px), **When** a tela carrega, **Then** o grid de gráficos usa a largura disponível para mostrar mais colunas/painéis lado a lado em vez de empilhar tudo em uma coluna estreita.
2. **Given** uma tela mobile/estreita, **When** a tela carrega, **Then** o mesmo conteúdo continua utilizável, empilhado verticalmente sem overflow horizontal da página.

---

### Edge Cases

- O que acontece quando o usuário filtra por categoria e por um evento específico ao mesmo tempo? O recorte deve considerar ambos (evento + categoria), como já ocorre hoje.
- O que acontece se o filtro de "última semana" (novo) for combinado com "Data da avaliação" em vez de "Data do evento"? O recorte deve usar a coluna de data escolhida, igual aos demais períodos pré-definidos.
- O que acontece quando um evento específico é selecionado? Os painéis que só fazem sentido na visão agregada (tendência mensal, melhores/piores eventos) não devem ser exibidos, seguindo o mesmo comportamento do sistema clássico.
- O que acontece com o painel "Média por categoria" quando um filtro de categoria específica já está ativo? Ele não deve ser exibido (seria redundante mostrar a média de uma categoria dentro do filtro daquela mesma categoria).
- O que acontece se não houver avaliações suficientes para calcular tendência mensal (menos de 2 meses com dados)? O painel de tendência não deve ser exibido, evitando um gráfico sem sentido.
- O que ocorre se o usuário digitar um intervalo de datas personalizado inválido (fim antes do início, ou campos vazios)? O botão "Aplicar" não deve gerar um recorte quebrado — a ação só é efetivada com ao menos uma data válida informada.
- O que acontece com uma avaliação sem comentário de texto? Ela conta para os KPIs/distribuição/pontos de atenção quando aplicável, mas não aparece na lista de "Comentários" (que exige texto).

## Requirements *(mandatory)*

### Functional Requirements

**Privacidade e RBAC (US4)**

- **FR-001**: O sistema DEVE exibir o controle de "ativar/desativar modo anônimo total" somente para usuários com papel SUPERADMIN; nenhum outro papel deve ver esse controle em nenhuma parte da tela.
- **FR-002**: O sistema DEVE exibir "Anônimo" como autor de qualquer avaliação (ponto de atenção ou comentário) para todo usuário que não seja SUPERADMIN, independentemente do estado do modo anônimo total.
- **FR-003**: O sistema DEVE permitir que apenas um usuário SUPERADMIN altere o estado do modo anônimo total, e essa alteração DEVE se refletir imediatamente na tela para o próprio SUPERADMIN.

**Filtros (US2)**

- **FR-004**: O sistema DEVE oferecer pills de período com as opções: Tudo, Última semana, 30 dias, 3 meses, 12 meses, e uma opção Personalizada com seleção de data inicial e final aplicada por um botão "Aplicar".
- **FR-005**: O sistema DEVE oferecer uma alternância "Filtrar por" entre "Data do evento" e "Data da avaliação", afetando qual data é usada para os filtros de período.
- **FR-006**: O sistema DEVE oferecer pills de categoria com as opções: Todas, Artista, Som, Figurino, Texto, Coordenação, Maquiagem.
- **FR-007**: O sistema DEVE oferecer um seletor de evento específico, agrupado por mês, que ao ser escolhido foca o recorte inteiro naquele evento.
- **FR-008**: O sistema DEVE indicar visualmente qual pill/opção está ativa em cada grupo de filtro (período, categoria, modo de data).
- **FR-009**: O sistema DEVE oferecer uma ação de "limpar filtros" quando houver algum filtro ativo, retornando ao estado padrão.
- **FR-010**: O sistema NÃO DEVE exibir o seletor "Filtrar por" (data do evento/avaliação) quando um evento específico estiver selecionado, já que o período não se aplica nesse caso.

**KPIs e gráficos (US1)**

- **FR-011**: O sistema DEVE exibir os indicadores: nota média geral (com representação em estrelas), total de avaliações no recorte e número de eventos avaliados (este último omitido quando um evento específico está selecionado).
- **FR-012**: O sistema DEVE exibir um painel de tendência mensal (média e quantidade de avaliações por mês), exibido apenas quando houver dados de pelo menos 2 meses distintos e nenhum evento específico selecionado.
- **FR-013**: O sistema DEVE exibir um painel de distribuição de notas com uma barra por nota (5 a 1 estrela), proporcional à contagem, mais o valor numérico.
- **FR-014**: O sistema DEVE exibir um painel de média por categoria (uma linha por categoria com estrelas e nota média), visível apenas quando nenhum filtro de categoria específica estiver ativo; cada linha DEVE permitir aplicar o filtro daquela categoria com um clique.
- **FR-015**: O sistema DEVE exibir um painel de ranking com os melhores e piores eventos do recorte (até 3 cada), visível apenas na visão agregada (sem evento específico selecionado); cada evento listado DEVE permitir focar o recorte naquele evento com um clique.

**Feedback e comentários (US3)**

- **FR-016**: O sistema DEVE exibir um bloco "Pontos de atenção" com as avaliações de nota 1-2 do recorte, destacado visualmente como alerta, mostrando nota, categoria, autor (respeitando FR-001/FR-002), nome do evento e o texto do comentário (ou indicação de ausência de comentário).
- **FR-017**: O sistema DEVE exibir uma confirmação positiva no lugar do bloco "Pontos de atenção" quando não houver nenhuma avaliação de nota 1-2 no recorte.
- **FR-018**: O sistema DEVE exibir um bloco "Comentários" com as avaliações que possuem texto, ordenadas das mais recentes, mostrando estrelas, categoria, nome do evento e data de envio.

**Layout (US5)**

- **FR-019**: O sistema DEVE apresentar o conteúdo da tela ocupando a largura total disponível (sem limite estreito de largura), com padding lateral adequado, em telas widescreen.
- **FR-020**: O sistema DEVE permanecer utilizável em telas estreitas (mobile), empilhando o conteúdo verticalmente sem gerar rolagem horizontal da página.

### Key Entities *(include if feature involves data)*

- **Avaliação (rating)**: nota geral e comentário dado por um talento sobre um evento em que participou, vinculada a um evento e, opcionalmente, com sub-notas por categoria.
- **Sub-nota por categoria**: nota e comentário específicos de uma categoria (Artista, Som, Figurino, Texto, Coordenação, Maquiagem) dentro de uma avaliação, podendo referenciar um colega avaliado.
- **Filtro Ativo**: combinação de período (ou evento específico), modo de data (evento/avaliação) e categoria que define o recorte exibido.
- **Política de Anonimato**: configuração global (modo anônimo total) que, combinada com o papel do usuário logado, determina se a autoria de uma avaliação é exibida ou substituída por "Anônimo".

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Um usuário consegue identificar a nota média geral, o total de avaliações e o número de eventos avaliados em menos de 3 segundos após abrir a tela, sem precisar aplicar nenhum filtro.
- **SC-002**: Um usuário consegue restringir o recorte a um período, categoria ou evento específico em no máximo 2 cliques (pill/seleção + eventual "Aplicar" apenas para período personalizado).
- **SC-003**: 100% dos acessos de usuários sem papel SUPERADMIN não exibem o controle de modo anônimo total nem qualquer nome de autor de avaliação — sempre "Anônimo".
- **SC-004**: Um usuário SUPERADMIN consegue alternar o modo anônimo total e ver o efeito refletido na tela sem recarregar a página manualmente.
- **SC-005**: Em uma tela widescreen (≥1440px), o conteúdo principal ocupa ao menos 90% da largura disponível (descontado o padding), em vez de ficar confinado a uma coluna central estreita.
- **SC-006**: Um usuário consegue localizar todas as avaliações críticas (nota 1-2) do recorte atual em um único bloco visualmente destacado, sem precisar procurar entre os comentários gerais.

## Assumptions

- A API de leitura do panorama de avaliações (`GET /api/ratings`) já expõe todos os dados agregados necessários (distribuição de notas, médias por categoria, tendência mensal, ranking de eventos, flags de RBAC) — a única lacuna é o novo preset de período "última semana" (7 dias), que precisa ser adicionado ao cálculo de período no backend reusado por essa API (sem alterar a tela Jinja legada, que não usa esse novo preset).
- A regra de anonimato (autoria "Anônimo" para não-SUPERADMIN, controle exclusivo de SUPERADMIN para o modo anônimo total) já é aplicada corretamente pelo backend na determinação de qual nome retornar; esta feature garante que a tela em React nunca contorna essa regra (ex.: não exibe um controle de alternância para quem não deveria vê-lo) e sempre exibe exatamente o que a API retorna como autor.
- Esta reestruturação não altera nenhuma tela, rota ou template do sistema Jinja legado (`/talents/avaliacoes`, `app/talents/routes.py`, `app/templates/talents/avaliacoes.html`) — a mudança é inteiramente na aplicação React (`frontend/apps/internal`), com o Jinja permanecendo como referência de comportamento e fidelidade visual, não como código compartilhado.
- O limite de comentários mais recentes exibidos na visão agregada (sem evento específico) segue o mesmo limite prático já usado pelo backend (30), evitando uma lista sem fim.
- A verificação funcional automatizada desta entrega roda contra a cópia local do banco de produção (`manto_local`, PostgreSQL), conforme padrão já estabelecido no projeto.
