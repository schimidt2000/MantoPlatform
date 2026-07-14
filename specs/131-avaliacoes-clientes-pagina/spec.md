# Feature Specification: Página de Clientes Organizada + Botão de Feedback Trava Após Envio

**Feature Branch**: `131-avaliacoes-clientes-pagina`

**Created**: 2026-07-14

**Status**: Draft

**Input**: "1) Os reviews das clientes devem ficar armazenados na página das clientes. Preciso
que organize essa página. Uma parte é para buscar as clientes e outra para ver as
avaliações. E aí posso aplicar filtros similares ao das avaliações dos talentos. 2) Quando
o feedback da cliente for enviado por ela, o botão deve ficar inacessível, seguindo o
padrão do botão de cobrança."

## Contexto

A feature 130 criou o feedback da cliente (nota + cards + comentário), mas hoje ele só
aparece espalhado dentro de cada página de evento — não existe um lugar para ver todas as
avaliações juntas, filtrar e enxergar padrões (ex.: quais clientes deram nota baixa). O
módulo de Clientes já existe (busca + ficha por cliente) mas não tem nenhuma ligação com
esse feedback ainda.

Separadamente, o botão "Pedir feedback da cliente" na página do evento continua clicável
mesmo depois que a cliente já respondeu — sem necessidade, já que pedir de novo não faz
sentido depois que a resposta já chegou.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Ver e filtrar as avaliações das clientes (Priority: P1)

Alguém da comercial quer entender como as clientes têm avaliado a equipe: abre a área de
Clientes, acessa a parte de avaliações e vê todas as respostas recebidas, podendo filtrar
por período, nota e pelo que foi marcado nos cards — do mesmo jeito que já filtra as
avaliações dos artistas.

**Why this priority**: sem um lugar para ver o conjunto das avaliações, o feedback
coletado na feature 130 fica invisível fora do contexto de um evento por vez — é o que dá
utilidade real ao que já foi coletado.

**Independent Test**: com feedbacks já recebidos para eventos diferentes, abrir a área de
avaliações de clientes, aplicar um filtro de nota e outro de período, e conferir que só as
avaliações que batem com os dois aparecem.

**Acceptance Scenarios**:

1. **Given** a área de Clientes, **When** a comercial acessa, **Then** encontra duas partes
   claramente separadas: uma para buscar/listar clientes (como já existe hoje) e outra
   dedicada a ver as avaliações recebidas.
2. **Given** a parte de avaliações, **When** não há nenhum filtro aplicado, **Then** vê
   todas as avaliações recebidas, mais recentes primeiro, com nota, cards marcados,
   comentário, cliente e data.
3. **Given** a parte de avaliações, **When** aplica um filtro de período (ex.: últimos 30
   dias), **Then** só avaliações enviadas dentro desse período aparecem.
4. **Given** a parte de avaliações, **When** aplica um filtro de nota (ex.: só 5 estrelas),
   **Then** só avaliações com aquela nota aparecem.
5. **Given** a parte de avaliações, **When** filtra por um card específico (ex.: "⏰
   Atraso"), **Then** só avaliações que marcaram aquele card aparecem.
6. **Given** a parte de avaliações, **When** filtra por uma cliente específica, **Then** só
   as avaliações dos eventos daquela cliente aparecem.
7. **Given** a parte de avaliações, **When** não existe nenhuma avaliação recebida ainda
   (ou nenhuma bate com o filtro aplicado), **Then** aparece um estado vazio explicativo,
   nunca uma tela quebrada ou em branco sem explicação.
8. **Given** uma avaliação com nota baixa (1 ou 2 estrelas), **When** a comercial olha a
   parte de avaliações, **Then** consegue identificar rapidamente esses casos de atenção,
   sem precisar ler todas as avaliações uma por uma.

### User Story 2 - Não pedir feedback de novo depois que já chegou (Priority: P2)

Uma pessoa da comercial abre a página de um evento cuja cliente já enviou o feedback.
Percebe que o botão "Pedir feedback da cliente" está desabilitado, com uma explicação, do
mesmo jeito que já acontece com o botão de Cobrança quando ele não se aplica.

**Why this priority**: é uma melhoria de clareza sobre uma ferramenta que já existe (feature
130) — importante, mas menor que ter um lugar para ver as avaliações (US1).

**Independent Test**: para um evento com pelo menos uma avaliação já recebida, abrir a
página do evento e conferir que o botão de pedir feedback aparece desabilitado com uma
explicação, em vez de continuar clicável.

**Acceptance Scenarios**:

1. **Given** um evento que ainda não recebeu nenhuma avaliação da cliente, **When** a
   comercial abre a página do evento, **Then** o botão "Pedir feedback da cliente"
   continua clicável normalmente (comportamento de hoje).
2. **Given** um evento que já recebeu ao menos uma avaliação da cliente, **When** a
   comercial abre a página do evento, **Then** o botão aparece desabilitado (mesmo visual
   do botão de Cobrança quando indisponível: esmaecido, cursor de "não permitido"), com uma
   explicação de que a cliente já enviou feedback para aquele evento.
3. **Given** o botão desabilitado, **When** a comercial passa o mouse ou toca nele,
   **Then** nada acontece (nenhuma cópia de link, nenhuma ação).

### Edge Cases

- Uma avaliação pode pertencer a um evento sem cliente associada (ex.: evento antigo sem
  vínculo) — essa avaliação continua aparecendo na parte de avaliações (não desaparece
  silenciosamente), só não é possível filtrá-la por cliente nem abrir a ficha da cliente a
  partir dela.
- Um evento pode receber mais de uma avaliação (ex.: duas pessoas do lado da cliente
  responderam) — o botão "Pedir feedback da cliente" continua desabilitado normalmente
  (basta ter pelo menos uma).
- Filtros combinados que não batem com nenhuma avaliação (ex.: nota 1 estrela + card que
  só aparece em avaliações de 5 estrelas) mostram o estado vazio, não um erro.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: A área de Clientes DEVE ter duas partes claramente identificáveis: busca/
  listagem de clientes (existente) e avaliações recebidas (nova).
- **FR-002**: A parte de avaliações DEVE listar todo o feedback já recebido das clientes,
  mostrando nota, cards marcados, comentário (quando houver), cliente (quando o evento
  tiver uma associada) e data de envio, mais recente primeiro.
- **FR-003**: A parte de avaliações DEVE permitir filtrar por período de envio (ex.:
  últimos 30/90/365 dias, ou todo o histórico).
- **FR-004**: A parte de avaliações DEVE permitir filtrar por nota (1 a 5 estrelas).
- **FR-005**: A parte de avaliações DEVE permitir filtrar pelo card marcado (ex.: "⏰
  Atraso", "✨ Pura Magia").
- **FR-006**: A parte de avaliações DEVE permitir filtrar por uma cliente específica.
- **FR-007**: A parte de avaliações DEVE mostrar um resumo (média geral de nota, total de
  avaliações) que reflete os filtros aplicados no momento.
- **FR-008**: A parte de avaliações DEVE destacar de forma visível as avaliações com nota
  baixa (1 ou 2 estrelas), para chamar atenção sem exigir leitura de tudo.
- **FR-009**: Quando não houver avaliações (nem no total, nem batendo com o filtro
  aplicado), a parte de avaliações DEVE mostrar um estado vazio explicativo.
- **FR-010**: O acesso à parte de avaliações segue a mesma regra de permissão já usada
  hoje para a área de Clientes.
- **FR-011**: Na página do evento, o botão "Pedir feedback da cliente" DEVE ficar
  desabilitado (visual esmaecido, sem ação ao clicar) assim que existir pelo menos uma
  avaliação recebida para aquele evento — mesmo padrão visual já usado pelo botão de
  Cobrança quando ele está indisponível.
- **FR-012**: O botão desabilitado DEVE explicar o motivo (ex.: via texto ao passar o
  mouse), do mesmo jeito que o botão de Cobrança já explica por que está indisponível.
- **FR-013**: Enquanto nenhuma avaliação tiver sido recebida para o evento, o botão
  continua se comportando exatamente como hoje (clicável, copia o link).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A partir da área de Clientes, alguém da comercial encontra todas as
  avaliações recebidas e consegue restringi-las por período, nota, card e cliente sem
  precisar abrir evento por evento.
- **SC-002**: Avaliações com nota 1 ou 2 estrelas são identificáveis em poucos segundos, sem
  precisar ler a lista inteira.
- **SC-003**: Depois que uma cliente responde o feedback de um evento, ninguém da comercial
  consegue gerar um novo pedido de feedback para aquele mesmo evento pela interface.

## Assumptions

- "Página das clientes" é entendido como o módulo/área de Clientes como um todo (busca +
  avaliações), não necessariamente uma única tela — segue o mesmo padrão já usado pelo
  módulo de Talentos, que tem "Banco de Talentos" e "Avaliações" como duas telas
  separadas dentro do mesmo menu, com filtros no mesmo estilo que a US1 pede para espelhar.
- "Filtros similares aos das avaliações dos talentos" significa os filtros de mesma
  natureza (período, nota/categoria, um seletor de quem está sendo avaliado) e o mesmo
  estilo de interação (chips clicáveis) — não necessariamente todos os widgets daquela
  tela (ex.: gráfico de tendência mensal fica fora do escopo aqui, por não ter sido
  pedido e não ser essencial para filtrar).
- O filtro de período considera a data de envio da avaliação (não a data do evento).
- Uma vez desabilitado por já ter recebido avaliação, o botão "Pedir feedback da cliente"
  não tem um caminho na interface para reabilitar manualmente — se for necessário pedir de
  novo (caso raro), depende de ação fora da interface por ora; pode virar uma necessidade
  futura se aparecer na prática.
