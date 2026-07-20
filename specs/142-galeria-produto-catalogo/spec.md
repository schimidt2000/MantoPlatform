# Feature Specification: Galeria de fotos do produto e reordenação na gestão

**Feature Branch**: `142-galeria-produto-catalogo`

**Created**: 2026-07-20

**Status**: Draft

**Input**: User description: "na página do produto: 1) cada foto tem seu tamanho/proporção — não pode ficar fixo; no WordPress, ao trocar de foto a proporção mudava junto e a barra de próximas fotos acompanhava; 2) poder trocar de foto arrastando pro lado; 3) o botão 'ver mais personagens' é inútil, trocar por outro; 4) na criação/edição do produto, poder reordenar as fotos." Resposta à pergunta de esclarecimento sobre o item 3 (frase cortada na mensagem original): o botão passa a levar para a categoria daquele produto ("Ver mais em <categoria>").

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Ver cada foto do produto na proporção certa (Priority: P1)

Hoje a foto principal da página do produto fica dentro de uma moldura de proporção fixa
(retrato 4:5) — fotos que não são desse formato (paisagem, quadrada, retrato mais
alongado) ficam cortadas ou distorcidas dentro dessa moldura. Ao navegar entre as fotos de
um mesmo produto, a pessoa precisa ver cada uma na sua proporção real, sem corte forçado —
a moldura deve se ajustar a cada foto, como acontecia no site WordPress anterior.

**Why this priority**: fotos cortadas de forma errada prejudicam a apresentação do
produto — é a reclamação mais concreta e visual do usuário sobre a página pública.

**Independent Test**: abrir um produto com fotos de proporções bem diferentes entre si
(uma quadrada, uma bem vertical) e confirmar que a moldura da foto principal se ajusta a
cada uma ao navegar, sem cortar nem distorcer.

**Acceptance Scenarios**:

1. **Given** um produto com fotos de proporções diferentes, **When** a pessoa navega de
   uma foto para outra (clicando numa miniatura), **Then** a moldura da foto principal
   ajusta sua proporção para a da foto atual, mostrando a imagem inteira sem corte
   forçado.
2. **Given** a foto principal mudando de proporção, **When** a transição acontece,
   **Then** a barra de miniaturas abaixo continua mostrando com clareza qual foto está
   selecionada no momento (acompanha a troca).

---

### User Story 2 - Trocar de foto arrastando (swipe) (Priority: P2)

Em vez de precisar clicar numa miniatura específica, a pessoa navegando pelo celular quer
poder arrastar a foto principal para o lado (like um carrossel/story) para ver a próxima
ou a anterior.

**Why this priority**: melhora a experiência em celular (onde a maior parte do tráfego do
catálogo acontece), mas não bloqueia nada — a navegação por miniatura já funciona.

**Independent Test**: num produto com várias fotos, arrastar a foto principal para a
esquerda avança para a próxima foto; arrastar para a direita volta para a anterior.

**Acceptance Scenarios**:

1. **Given** um produto com mais de uma foto, **When** a pessoa arrasta a foto principal
   para a esquerda, **Then** a próxima foto é exibida (com a moldura ajustada à proporção
   dela, e a miniatura correspondente marcada como ativa).
2. **Given** a mesma situação, **When** a pessoa arrasta para a direita, **Then** a foto
   anterior é exibida.
3. **Given** a pessoa está na última foto, **When** arrasta para avançar, **Then** nada
   quebra (não avança além da última — sem foto "vazia").

---

### User Story 3 - Botão útil para continuar navegando (Priority: P2)

O botão "Ver mais personagens" na página do produto não leva a lugar nenhum de valor real
(repete o link que já existe no topo da página). Em vez dele, um botão que leve para a
categoria daquele produto específico é mais útil — continua a navegação de forma mais
direcionada, aproveitando a página de categoria já existente (feature 140).

**Why this priority**: é uma melhoria de navegação pequena — nem bloqueia nada, nem tem a
urgência visual da História 1.

**Independent Test**: abrir a página de um produto que pertence a pelo menos uma
categoria e confirmar que o botão leva para a página daquela categoria.

**Acceptance Scenarios**:

1. **Given** um produto com ao menos uma categoria, **When** a pessoa vê a página do
   produto, **Then** existe um botão "Ver mais em <nome da categoria>" que leva à página
   pública daquela categoria.
2. **Given** um produto com mais de uma categoria, **When** o botão é montado, **Then**
   usa a primeira categoria do produto (mesmo critério simples já usado em outros lugares
   do catálogo para "a categoria principal" de um produto).
3. **Given** um produto sem nenhuma categoria, **When** a página é montada, **Then** o
   botão não aparece (não há categoria para levar).

---

### User Story 4 - Reordenar as fotos ao criar/editar um produto (Priority: P1)

Ao gerenciar as fotos de um produto (feature 139/141: marcar capa, remover, adicionar),
falta poder reorganizar a ordem das fotos já salvas — hoje a única forma de mudar a ordem
é via a escolha de capa (que só afeta qual foto vem primeiro), sem controle sobre a ordem
das demais.

**Why this priority**: afeta diretamente a ordem em que a pessoa vê as fotos na página do
produto (História 1/2) — sem poder reordenar, o super admin fica sem controle sobre a
experiência que acabou de ganhar mais visibilidade com a proporção dinâmica.

**Independent Test**: num produto com 3+ fotos, mudar a ordem de duas delas na tela de
edição, salvar, e confirmar que a nova ordem aparece na página pública do produto.

**Acceptance Scenarios**:

1. **Given** a tela de criar/editar produto com múltiplas fotos já selecionadas/salvas,
   **When** o super admin reordena as fotos (ex.: arrastando), **Then** a nova ordem é
   refletida visualmente antes de salvar.
2. **Given** uma nova ordem definida, **When** o super admin salva, **Then** a ordem das
   fotos na página pública do produto (e a ordem das miniaturas) reflete exatamente o que
   foi definido.
3. **Given** a escolha de capa (feature 141) e a reordenação usadas juntas, **When** o
   super admin marca uma foto como capa E reordena as demais, **Then** a foto marcada como
   capa continua sendo a primeira, e a ordem das demais segue o que foi definido no
   reordenamento.

---

### Edge Cases

- Produto com uma única foto: a moldura ajusta à proporção dela normalmente; miniaturas e
  swipe não têm efeito visível (nada para navegar).
- Foto muito larga (panorâmica) ou muito alta: a moldura se ajusta à proporção real, sem
  limite artificial que force corte — mas dentro de um teto razoável de altura/largura na
  tela para não quebrar o layout da página (ex.: não deixar a moldura ocupar mais que a
  tela toda).
- Arrastar a foto principal sem intenção de trocar (ex.: apenas tocando/clicando sem
  mover): não deve trocar de foto por engano — só arrastos com deslocamento horizontal
  perceptível contam como swipe.
- Reordenar fotos e não salvar (sair da tela): nenhuma mudança é persistida — mesma regra
  de qualquer formulário não salvo.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: A moldura da foto principal da página do produto MUST se ajustar à
  proporção real de cada foto conforme a pessoa navega entre elas — sem corte nem
  distorção forçados por uma proporção fixa.
- **FR-002**: A indicação de qual foto está selecionada (miniaturas) MUST continuar
  clara e sincronizada com a foto principal, incluindo quando a proporção da moldura
  muda.
- **FR-003**: A pessoa MUST conseguir trocar de foto arrastando a foto principal para a
  esquerda (próxima) ou direita (anterior), além de continuar podendo clicar numa
  miniatura.
- **FR-004**: A página do produto MUST substituir o botão "Ver mais personagens" por um
  botão que leva à página da categoria daquele produto — some quando o produto não tem
  categoria.
- **FR-005**: A tela de criar/editar produto do catálogo MUST permitir reordenar as fotos
  já selecionadas/salvas antes de salvar.
- **FR-006**: A ordem definida na reordenação MUST ser exatamente a ordem exibida na
  página pública do produto (galeria principal e miniaturas) após salvar.
- **FR-007**: A escolha de capa (já existente, feature 141) e a reordenação MUST
  funcionar juntas sem conflito — a foto marcada como capa continua sempre em primeiro,
  independente da posição escolhida no reordenamento das demais.

### Key Entities

- **Foto do produto** (`CatalogItemImage`, já existe): nenhuma mudança de estrutura — a
  reordenação usa o mesmo campo de posição (`position`) que já existe e já determina a
  ordem hoje.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Fotos de qualquer proporção aparecem inteiras na página do produto, sem
  corte que esconda parte relevante da imagem.
- **SC-002**: Alguém navegando pelo celular consegue ver todas as fotos de um produto só
  arrastando, sem precisar tocar em miniaturas.
- **SC-003**: O botão de navegação adicional da página do produto sempre leva a um lugar
  útil (a categoria do produto), nunca a um link redundante.
- **SC-004**: O super admin consegue definir a ordem exata das fotos de um produto sem
  precisar excluir e reenviar fotos para "forçar" uma ordem diferente.

## Assumptions

- **Sobre os prints mencionados**: a mensagem original citava 2 prints do site WordPress
  ilustrando o comportamento esperado, mas eles não chegaram junto com o texto. A
  interpretação usada (moldura da foto principal ajustando a proporção a cada foto, com a
  barra de miniaturas acompanhando a seleção atual) é baseada só na descrição em texto —
  se não bater exatamente com o que os prints mostravam, é o ponto mais provável de
  precisar de um ajuste fino depois de implementado.
- **Botão "Ver mais em categoria"**: conforme resposta do usuário à pergunta de
  esclarecimento, quando o produto tem mais de uma categoria usa a primeira; produto sem
  categoria não mostra o botão.
- Reordenação (História 4) se aplica às fotos já enviadas/salvas de um produto (criação
  ou edição) — não muda o mecanismo de escolha de capa em si (feature 141), só complementa
  com controle sobre a ordem das demais fotos.
- Fora de escopo: mudar como as fotos são armazenadas ou comprimidas (feature 141, já
  resolvido); zoom/lightbox em tela cheia da foto principal não foi pedido.
