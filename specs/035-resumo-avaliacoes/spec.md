# Feature Specification: Página de resumo das avaliações

**Feature Branch**: `035-resumo-avaliacoes`

**Created**: 2026-06-09

**Status**: Draft

**Input**: User description: "fazer uma página que possamos ver um resumo das avaliações, seja por
evento ou geral. Deixe de uma forma bem legal."

## Contexto

O sistema coleta avaliações dos eventos pelo portal do talento: uma **nota geral** (1–5) por evento
com comentário, e **sub-avaliações por categoria** (1–5): Figurino, Som, Texto (gerais) e Artista,
Coordenação, Maquiagem (por pessoa). Hoje essas avaliações só aparecem espalhadas (na página do
talento, no histórico do portal), sem uma **visão consolidada**.

Esta feature cria uma **página de resumo das avaliações**, com duas visões:
- **Geral**: panorama de todas as avaliações (médias, distribuição de notas, médias por categoria).
- **Por evento**: ao escolher um evento, o resumo daquele evento (nota média, médias por categoria,
  comentários).

A apresentação deve ser **visualmente agradável** ("bem legal"): cards de destaque, estrelas, barras
de média por categoria, distribuição de notas.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Visão geral das avaliações (Priority: P1)

A pessoa abre a página e vê um panorama de todas as avaliações: quantas avaliações, nota média geral
(em estrelas), quantos eventos avaliados, distribuição das notas (quantas 5, 4, 3, 2, 1) e a média por
categoria.

**Why this priority**: É o valor central — enxergar a qualidade geral num lugar só.

**Independent Test**: Abrir a página sem escolher evento e conferir os números agregados e as médias
por categoria.

**Acceptance Scenarios**:

1. **Given** existem avaliações, **When** abro a página (visão geral), **Then** vejo total de
   avaliações, nota média geral em estrelas, nº de eventos avaliados, distribuição de notas e média
   por categoria.
2. **Given** não há avaliações ainda, **When** abro a página, **Then** vejo um estado vazio claro.

---

### User Story 2 - Resumo por evento (Priority: P1)

A pessoa escolhe um evento (entre os que têm avaliação) e vê o resumo daquele evento: nota média,
quantas avaliações, médias por categoria e os comentários deixados.

**Why this priority**: Permite analisar um evento específico (o que foi bem/mal).

**Independent Test**: Selecionar um evento avaliado e conferir suas médias e comentários.

**Acceptance Scenarios**:

1. **Given** um evento com avaliações, **When** o seleciono, **Then** vejo a nota média do evento, o
   número de avaliações, as médias por categoria e os comentários.
2. **Given** que volto para "Geral", **When** limpo a seleção, **Then** vejo de novo o panorama
   completo.

---

### User Story 3 - Apresentação agradável (Priority: P2)

O resumo é fácil de ler: notas mostradas em **estrelas**, médias por categoria em **barras**,
distribuição de notas visível, cores consistentes com o sistema.

**Acceptance Scenarios**:

1. **Given** a página, **When** a vejo, **Then** as notas aparecem como estrelas e as médias por
   categoria como barras proporcionais, com a paleta do sistema.

---

### Edge Cases

- **Sem avaliações** (geral ou no evento escolhido): estado vazio claro, sem números quebrados.
- **Categoria sem nenhuma nota**: não aparece (ou aparece como "—"), sem distorcer a média.
- **Comentário vazio**: a avaliação conta na média, mas não polui a lista de comentários.
- **Evento sem avaliação**: não aparece na lista de seleção de eventos.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: A página MUST oferecer duas visões: **Geral** (todas as avaliações) e **Por evento**
  (um evento selecionado entre os que têm avaliação).
- **FR-002**: A visão geral MUST exibir: total de avaliações, nota média geral, nº de eventos
  avaliados, distribuição das notas (1 a 5) e a média por categoria.
- **FR-003**: A visão por evento MUST exibir: nota média do evento, nº de avaliações, médias por
  categoria e a lista de comentários daquele evento.
- **FR-004**: As notas MUST ser apresentadas de forma visual (estrelas) e as médias por categoria em
  barras proporcionais.
- **FR-005**: A página MUST ter acesso restrito a papéis apropriados (gestão de talentos), seguindo o
  controle de acesso já existente.
- **FR-006**: A página MUST tratar estados vazios (sem avaliações) de forma clara.
- **FR-007**: A página MUST ser acessível pelo menu de navegação.

### Key Entities

- **Avaliação de evento (EventRating)** — nota geral + comentário por evento/avaliador (já existe).
- **Sub-avaliação (EventSubRating)** — nota por categoria (Figurino, Som, Texto, Artista, Coordenação,
  Maquiagem), opcionalmente sobre uma pessoa (já existe).
- A feature apenas **lê e agrega** esses dados; não cria entidades novas.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Em até ~3 segundos, a pessoa vê o panorama geral (médias, distribuição, por categoria).
- **SC-002**: Selecionar um evento mostra o resumo correto daquele evento (médias e comentários) em
  100% dos casos.
- **SC-003**: As médias exibidas conferem com as avaliações registradas (mesma base de dados) em 100%.
- **SC-004**: Estados vazios são tratados sem números quebrados em 100% dos casos.

## Assumptions

- Acesso: SUPERADMIN e CASTING (qualidade de elenco é domínio do casting); ajustável depois.
- Notas vão de 1 a 5; média exibida com 1 casa decimal e em estrelas.
- "Geral" considera todas as avaliações já registradas (sem recorte de período nesta entrega; filtro
  por período pode ser follow-up).
- Apenas leitura/agregação; sem mudança de banco.
