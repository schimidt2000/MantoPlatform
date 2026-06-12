# Feature Specification: Avaliações robustas (filtros, navegação e insights)

**Feature Branch**: `038-avaliacoes-melhorias`

**Created**: 2026-06-12

**Status**: Draft

**Input**: User description: "a parte de avaliações desenvolvida ainda está crua. Seria legal poder
filtrar para ver apenas reviews de figurino, coordenação... e outras coisas. E a forma para achar os
eventos está ridícula — faz mais sentido primeiro achar a data e depois o evento. Planejar melhorias
além das propostas para essa ser uma seção robusta e importante do site."

## Contexto

A página **Resumo das Avaliações** (035) mostra hoje: nota média, total, distribuição 1–5, média por
categoria e comentários gerais — com um único dropdown plano de eventos. Limitações atuais:

1. **Sem filtro por categoria** — não dá para ver só as avaliações de figurino, coordenação etc.
2. **Achar evento é ruim** — o dropdown lista todos os eventos avaliados de uma vez; o natural é
   navegar primeiro pela **data** (período/mês) e depois escolher o evento.
3. **Comentários por categoria ficam invisíveis** — quem avalia pode comentar dentro de cada
   categoria, mas a página só mostra o comentário geral.
4. **Sem visão de tendência nem destaque de problemas** — não dá para ver se as notas estão melhorando
   nem identificar rapidamente os eventos/categorias com pior desempenho.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Filtrar por categoria (Priority: P1)

A gestora quer ver apenas as avaliações de **figurino** (ou coordenação, som, texto, maquiagem,
artista). Ao escolher a categoria, toda a página reflete o recorte: média, distribuição de notas e
comentários daquela categoria.

**Why this priority**: pedido direto do usuário; transforma a página de "vitrine" em ferramenta de
diagnóstico por área.

**Independent Test**: escolher "Figurino" no filtro e conferir que média/distribuição/comentários
mostram somente dados de figurino.

**Acceptance Scenarios**:

1. **Given** a página de avaliações, **When** seleciono a categoria "Figurino", **Then** a nota média,
   a distribuição e os comentários exibidos passam a considerar apenas as avaliações de figurino.
2. **Given** uma categoria selecionada, **When** volto para "Todas", **Then** a página volta à visão
   completa.
3. **Given** categoria + evento selecionados ao mesmo tempo, **When** a página carrega, **Then** os
   dois recortes se combinam (ex.: figurino do evento X).
4. **Given** uma categoria sem nenhuma avaliação no recorte atual, **When** filtro por ela, **Then**
   vejo um estado vazio claro (não uma página quebrada).

---

### User Story 2 - Achar evento pela data (Priority: P1)

A gestora navega primeiro pelo **período** (ex.: mês) e então escolhe o evento. O seletor de eventos
é agrupado/ordenado por data, e um filtro de período (atalhos: últimos 30 dias, 3 meses, ano, tudo —
ou intervalo personalizado) restringe tanto a lista de eventos quanto os números da visão geral.

**Why this priority**: pedido direto do usuário; sem isso a navegação não escala com o volume de
eventos.

**Independent Test**: selecionar "últimos 30 dias" e conferir que o seletor só lista eventos desse
período e que os KPIs gerais consideram só esse período.

**Acceptance Scenarios**:

1. **Given** a página de avaliações, **When** escolho um período, **Then** a visão geral (médias,
   distribuição, comentários) considera apenas avaliações de eventos daquele período.
2. **Given** um período escolhido, **When** abro o seletor de eventos, **Then** vejo apenas eventos
   avaliados do período, agrupados por mês e ordenados do mais recente ao mais antigo, cada um com a
   data visível.
3. **Given** um intervalo personalizado (de/até), **When** aplico, **Then** o recorte respeita as
   datas informadas.
4. **Given** um período sem eventos avaliados, **When** aplico o filtro, **Then** vejo estado vazio
   amigável.

---

### User Story 3 - Comentários por categoria visíveis (Priority: P2)

Os comentários feitos dentro de cada categoria (ex.: comentário sobre o figurino daquele evento)
aparecem na lista de comentários, com uma etiqueta indicando a categoria — e respeitam os filtros.

**Acceptance Scenarios**:

1. **Given** uma avaliação com comentário na categoria figurino, **When** vejo a lista de
   comentários, **Then** esse comentário aparece com etiqueta "Figurino" (além do comentário geral,
   etiquetado como "Geral").
2. **Given** o filtro de categoria "Coordenação" ativo, **When** vejo os comentários, **Then** só
   aparecem comentários da categoria coordenação.

---

### User Story 4 - Destaques e pontos de atenção (Priority: P2)

Na visão geral, a gestora vê um **ranking de eventos** (melhores e piores médias do recorte atual,
com link para a visão do evento) e um destaque de **pontos de atenção**: notas baixas (1–2) recentes,
com evento, categoria e comentário quando houver.

**Why this priority**: é o que torna a seção "importante" — aponta onde agir, não só números.

**Acceptance Scenarios**:

1. **Given** a visão geral com vários eventos avaliados, **When** a página carrega, **Then** vejo os
   eventos com melhor e pior média do recorte, e clicar em um leva à visão daquele evento.
2. **Given** avaliações com nota 1 ou 2 no recorte, **When** a página carrega, **Then** elas aparecem
   destacadas em "Pontos de atenção" com evento, categoria e comentário (se houver).
3. **Given** nenhum problema no recorte, **When** a página carrega, **Then** "Pontos de atenção"
   mostra um estado positivo (ex.: "nenhuma nota baixa no período").

---

### User Story 5 - Tendência ao longo do tempo (Priority: P3)

Na visão geral, um gráfico simples mostra a **média mensal** das avaliações do recorte, permitindo ver
se a qualidade está melhorando ou piorando.

**Acceptance Scenarios**:

1. **Given** avaliações distribuídas em vários meses, **When** vejo a visão geral, **Then** há uma
   barra/coluna por mês com a média e a quantidade de avaliações daquele mês.
2. **Given** filtro de categoria ativo, **When** vejo a tendência, **Then** ela reflete só a categoria.

---

### Edge Cases

- **Combinação de filtros sem resultados**: estado vazio claro com opção de limpar filtros.
- **Evento selecionado fora do período filtrado**: a visão do evento prevalece (período é ignorado ou
  ajustado), sem quebrar.
- **Categorias com pouquíssimas avaliações**: contagens sempre visíveis para não dar peso indevido a
  médias de amostra pequena.
- **Filtros inválidos na URL** (categoria inexistente, datas malformadas): ignorados com fallback para
  o padrão.
- **Acesso**: continua restrito a quem gere talentos (mesmo controle de acesso atual).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: A página MUST permitir filtrar todas as visões (médias, distribuição, comentários,
  destaques, tendência) por **categoria** de avaliação (todas / artista / som / figurino / texto /
  coordenação / maquiagem).
- **FR-002**: A página MUST oferecer filtro de **período** com atalhos (30 dias, 3 meses, 12 meses,
  tudo) e intervalo personalizado (de/até), aplicado a toda a página e à lista de eventos.
- **FR-003**: O seletor de eventos MUST ser organizado por data (agrupado por mês, mais recente
  primeiro, com a data de cada evento visível) e refletir o período filtrado.
- **FR-004**: Os filtros MUST ser combináveis (período + categoria + evento) e estar refletidos na
  URL, permitindo compartilhar/recarregar a visão.
- **FR-005**: Comentários de categoria MUST aparecer na lista de comentários com etiqueta da
  categoria; comentários gerais com etiqueta "Geral".
- **FR-006**: A visão geral MUST exibir ranking dos eventos com melhor e pior média do recorte, com
  link para a visão do evento.
- **FR-007**: A visão geral MUST exibir "Pontos de atenção": avaliações (gerais ou de categoria) com
  nota 1–2 no recorte, com evento, categoria, autor e comentário quando houver.
- **FR-008**: A visão geral MUST exibir a média mensal do recorte (tendência), com contagem por mês.
- **FR-009**: Recortes sem dados MUST exibir estados vazios amigáveis, com ação de limpar filtros.
- **FR-010**: O acesso MUST continuar restrito ao controle atual (equipe que gere talentos); nada da
  página aparece no portal do talento.

### Key Entities

- **Avaliação de evento** — nota geral 1–5 + comentário, enviada pelo talento (já existe).
- **Sub-avaliação por categoria** — nota 1–5 + comentário por categoria (já existe; passa a ser
  exibida e filtrável).
- **Evento** — agrupa avaliações; navegável por data.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Usuária encontra um evento avaliado de um mês específico em até 3 interações
  (período → seletor → evento).
- **SC-002**: 100% dos números exibidos (médias, distribuição, comentários, destaques, tendência)
  respeitam os filtros ativos.
- **SC-003**: Comentários de categoria ficam visíveis (hoje 0% aparecem; passa a 100% no recorte).
- **SC-004**: Toda combinação de filtros sem dados mostra estado vazio amigável (0 páginas quebradas).
- **SC-005**: URL com filtros recarregada reproduz exatamente a mesma visão.

## Assumptions

- Sem mudança de banco: tudo é leitura/agregação de dados já existentes (avaliações, sub-avaliações,
  eventos). Sem migration.
- "Pontos de atenção" = notas 1 e 2 (geral ou categoria), limitadas às mais recentes do recorte.
- Ranking de eventos considera só eventos com pelo menos 1 avaliação no recorte; contagem sempre
  exibida ao lado da média.
- Período filtra pela **data do evento** (não pela data de envio da avaliação) — é assim que a equipe
  pensa ("avaliações dos eventos de maio").
- Tendência mensal agrupa pela data do evento, pelos mesmos motivos.
- Visão por evento ignora o filtro de período (o evento já é o recorte mais específico).
