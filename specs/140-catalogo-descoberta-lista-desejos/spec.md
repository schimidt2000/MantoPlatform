# Feature Specification: Catálogo — tags/categorias criáveis, navegação por categoria, produtos relacionados e lista de desejos

**Feature Branch**: `140-catalogo-descoberta-lista-desejos`

**Created**: 2026-07-20

**Status**: Draft

**Input**: User description: "https://app.mantoproducoes.com.br/admin/catalogo/novo — melhorar tags (autocomplete + criar nova), criar categoria nova (na página de novo produto ou na gestão), desenvolver as categorias como no WordPress (página só de categorias, com fotos maiores, mostrando todas), sugerir produtos semelhantes na página do produto, e lista de desejos (cliente escolhe produtos, envia lista pro vendedor via WhatsApp)."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Escolher tags já usadas em vez de redigitar (Priority: P1)

Ao criar ou editar um produto do catálogo, o super admin digita tags de busca num campo de
texto livre — sem saber quais tags já existem, é fácil digitar a mesma coisa de formas
diferentes ("show infantil" vs. "Show Infantil" vs. "show-infantil"), o que quebra a busca
por tag. Ele precisa ver as tags já usadas conforme digita, escolher uma existente com um
clique, ou criar uma nova quando ela realmente não existe ainda.

**Why this priority**: é a fricção mais direta relatada — acontece toda vez que alguém
mexe num produto, e prejudica a busca do catálogo público quando tags divergem.

**Independent Test**: ao editar um produto, digitar parte de uma tag já usada em outro
produto e ver ela sugerida; escolher a sugestão e salvar; digitar algo que não existe ainda
e conseguir adicioná-la como tag nova.

**Acceptance Scenarios**:

1. **Given** o formulário de produto, **When** o super admin começa a digitar no campo de
   tags, **Then** vê sugestões das tags já usadas em qualquer produto do catálogo que
   combinam com o que foi digitado.
2. **Given** uma sugestão de tag existente, **When** o super admin clica nela, **Then** a
   tag é adicionada ao produto exatamente como já existe (sem criar uma variante nova).
3. **Given** um texto que não corresponde a nenhuma tag existente, **When** o super admin
   confirma esse texto (ex.: Enter ou um botão "criar"), **Then** essa tag nova é
   adicionada ao produto e passa a existir para sugestão em produtos futuros.

---

### User Story 2 - Criar e organizar categorias sem depender do CSV (Priority: P1)

Hoje não existe nenhuma forma de criar uma categoria nova no catálogo — elas só chegam pela
importação do CSV do WordPress. O super admin precisa poder criar uma categoria nova
diretamente no sistema, tanto ao cadastrar um produto quanto na tela geral de gestão do
catálogo.

**Why this priority**: bloqueia completamente a organização do catálogo por temas novos —
sem isso, o catálogo fica travado nas categorias que vieram da importação original.

**Independent Test**: criar uma categoria nova diretamente no formulário de produto (sem
sair da tela) e vê-la disponível para seleção; criar uma categoria pela tela de gestão do
catálogo e vê-la disponível ao editar qualquer produto.

**Acceptance Scenarios**:

1. **Given** o formulário de criação/edição de produto, **When** o super admin digita o
   nome de uma categoria nova (que ainda não existe) e confirma, **Then** a categoria é
   criada e já fica marcada naquele produto.
2. **Given** a tela de gestão do catálogo, **When** o super admin cria uma categoria nova
   ali (fora do contexto de um produto específico), **Then** ela passa a estar disponível
   para qualquer produto, e aparece na navegação pública por categoria (História 3).
3. **Given** uma categoria já existente com o mesmo nome (ignorando maiúsculas/acentos),
   **When** o super admin tenta criar outra com o mesmo nome, **Then** o sistema usa a
   categoria já existente em vez de criar uma duplicata.

---

### User Story 3 - Navegar o catálogo público por categoria, com fotos grandes (Priority: P2)

Hoje o catálogo público é uma única página com todos os personagens e um filtro por aba de
categoria. O usuário quer uma experiência mais parecida com a do site WordPress anterior:
uma página que mostra todas as categorias (cada uma com uma foto de destaque), e ao clicar
numa categoria, uma página só com os produtos daquela categoria, com fotos maiores do que
as usadas na grade atual — pensada para quem está decidindo o tema do evento e quer ver bem
os personagens antes de escolher.

**Why this priority**: é uma melhoria de navegação/descoberta importante, mas o catálogo já
funciona hoje (busca + filtro por aba) — não é um bloqueio, é uma experiência melhor.

**Independent Test**: abrir a página de categorias e ver todas as categorias com uma foto
cada; clicar numa e ver só os produtos daquela categoria, em destaque maior que a grade
compacta de hoje.

**Acceptance Scenarios**:

1. **Given** o catálogo público, **When** alguém acessa a página de categorias, **Then** vê
   todas as categorias que têm ao menos um produto ativo, cada uma com uma foto
   representativa e a contagem de produtos.
2. **Given** a página de categorias, **When** alguém clica numa categoria, **Then** vê só os
   produtos ativos daquela categoria, com fotos em destaque maior que a grade compacta da
   página inicial de hoje.
3. **Given** uma categoria sem nenhum produto ativo no momento, **When** o catálogo monta a
   página de categorias, **Then** essa categoria não aparece (mesma regra de hoje — só
   mostrar o que tem produto ativo).

---

### User Story 4 - Descobrir produtos parecidos na página de um produto (Priority: P2)

Ao ver um personagem específico, a pessoa não tem nenhum caminho de navegação além de
voltar para o catálogo inteiro. Mostrar produtos parecidos logo abaixo incentiva a pessoa a
continuar navegando e descobrir mais opções.

**Why this priority**: melhora a navegação/permanência no catálogo, mas não bloqueia nada —
o produto e seu link continuam funcionando perfeitamente sem isso.

**Independent Test**: abrir a página de um produto que compartilha categoria com outros
produtos ativos e ver uma seção de sugestões abaixo das informações do produto, cada
sugestão levando à respectiva página de produto.

**Acceptance Scenarios**:

1. **Given** a página de um produto que tem ao menos uma categoria em comum com outros
   produtos ativos, **When** a página carrega, **Then** aparece uma seção "Você também pode
   gostar" (ou equivalente) logo abaixo das informações do produto, com produtos daquela(s)
   mesma(s) categoria(s), excluindo o próprio produto.
2. **Given** um produto sem nenhuma categoria em comum com outro produto ativo, **When** a
   página carrega, **Then** a seção de sugestões simplesmente não aparece (sem erro, sem
   espaço vazio estranho).

---

### User Story 5 - Montar uma lista de desejos e enviar pro vendedor pelo WhatsApp (Priority: P1)

Ao navegar o catálogo, a pessoa quer marcar vários personagens que gostou (como um
carrinho de compras) e, quando terminar de escolher, enviar essa lista para a Manto pelo
WhatsApp de uma vez, sem precisar copiar nome por nome manualmente ou mandar vários links
separados.

**Why this priority**: é a funcionalidade de maior valor comercial direto do pedido —
transforma a navegação do catálogo num lead qualificado e específico para o vendedor, sem
fricção nenhuma para quem está navegando (sem cadastro, sem login).

**Independent Test**: adicionar 2-3 produtos à lista de desejos navegando o catálogo,
abrir a lista, e enviar — confirmando que abre o WhatsApp com uma mensagem citando os
produtos escolhidos.

**Acceptance Scenarios**:

1. **Given** qualquer página do catálogo público (lista, categoria ou produto), **When** a
   pessoa marca "adicionar à lista de desejos" num produto, **Then** esse produto passa a
   fazer parte da lista, visível a partir de qualquer página do catálogo (contador
   visível), mesmo depois de navegar para outras páginas.
2. **Given** uma lista de desejos com produtos, **When** a pessoa abre a lista, **Then** vê
   os produtos escolhidos (nome + foto) e pode remover qualquer um antes de enviar.
3. **Given** uma lista de desejos com ao menos um produto, **When** a pessoa clica em
   "Enviar para o vendedor" (ou equivalente), **Then** o WhatsApp abre com uma mensagem
   pronta citando os nomes dos produtos escolhidos (e idealmente os links), pronta para
   enviar ao número comercial da Manto.
4. **Given** uma lista de desejos vazia, **When** a pessoa procura o botão de enviar,
   **Then** ele fica desabilitado ou escondido — não é possível mandar uma mensagem vazia.
5. **Given** a pessoa fechou o navegador e voltou depois, **When** ela reabre o catálogo no
   mesmo aparelho/navegador, **Then** a lista de desejos que ela tinha montado continua lá
   (não se perde ao simplesmente fechar a aba).

---

### Edge Cases

- Duas tags digitadas com capitalização diferente ("Natal" e "natal"): tratadas como a
  mesma tag para fins de sugestão (não geram duas entradas equivalentes na lista de
  sugestões).
- Categoria renomeada ou excluída enquanto produtos ainda a referenciam: fora de escopo
  desta feature (não há tela de editar/excluir categoria — só criar); se isso vier a ser
  necessário, é uma feature futura.
- Produto adicionado à lista de desejos e depois marcado como inativo pelo super admin
  antes da pessoa enviar: a lista de desejos (armazenada no navegador da pessoa) não sabe
  disso em tempo real — o link enviado ao vendedor pode apontar a um produto que saiu do
  ar; risco aceito, mesmo padrão de qualquer link compartilhado de um catálogo.
- Lista de desejos em dois navegadores/aparelhos diferentes da mesma pessoa: não sincroniza
  entre eles (cada navegador tem sua própria lista) — não há conta de cliente nessa parte
  pública do sistema.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Ao digitar no campo de tags do formulário de produto, o sistema MUST sugerir
  tags já usadas em qualquer produto do catálogo que combinem com o texto digitado.
- **FR-002**: O sistema MUST permitir adicionar uma tag nova (que ainda não existe) direto
  do mesmo campo, sem sair da tela.
- **FR-003**: Tags MUST ser tratadas de forma insensível a maiúsculas/acentos para fins de
  sugestão e para evitar duplicatas variantes da mesma tag.
- **FR-004**: O sistema MUST permitir criar uma categoria nova a partir do formulário de
  produto (criar/editar) sem sair da tela.
- **FR-005**: O sistema MUST permitir criar uma categoria nova a partir da tela de gestão
  do catálogo, independente de estar editando um produto específico.
- **FR-006**: Criar uma categoria com nome igual (ignorando maiúsculas/acentos) a uma já
  existente MUST reaproveitar a categoria existente em vez de criar uma duplicata.
- **FR-007**: O catálogo público MUST ter uma página que lista todas as categorias com
  produto ativo, cada uma com uma imagem representativa e a contagem de produtos.
- **FR-008**: Cada categoria MUST ter sua própria página pública, mostrando só os produtos
  ativos daquela categoria, com fotos maiores do que as da grade compacta da página inicial
  atual.
- **FR-009**: A página de um produto MUST mostrar produtos relacionados (mesma categoria,
  excluindo o próprio produto) quando existir ao menos um; quando não existir nenhum, a
  seção simplesmente não aparece.
- **FR-010**: Qualquer página do catálogo público MUST permitir adicionar/remover um
  produto de uma lista de desejos, com o estado (quantos itens) visível de qualquer página
  do catálogo.
- **FR-011**: A lista de desejos MUST persistir no navegador da pessoa entre visitas (sem
  precisar de login ou cadastro).
- **FR-012**: O sistema MUST permitir ver o conteúdo completo da lista de desejos (nome e
  foto de cada produto) e remover itens antes de enviar.
- **FR-013**: O sistema MUST permitir enviar a lista de desejos para o WhatsApp comercial da
  Manto com uma única ação, citando os produtos escolhidos numa mensagem pronta — usando o
  mesmo número comercial já configurado no sistema para outras mensagens do catálogo/site
  (não é um número novo a cadastrar).
- **FR-014**: O botão de enviar MUST ficar indisponível quando a lista de desejos estiver
  vazia.

### Key Entities

- **Categoria** (`CatalogCategory`, já existe): passa a poder ser criada também pela
  interface, não só pela importação — sem mudança de estrutura.
- **Tag**: hoje já armazenada em cada produto (lista de textos); passa a ter uma origem
  única de sugestão (todas as tags já usadas em qualquer produto), sem virar uma entidade
  própria no banco — é só uma lista de valores distintos já existentes.
- **Lista de desejos**: nova, mas vive inteiramente no navegador da pessoa (não é
  persistida no servidor) — uma lista de referências a produtos do catálogo.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Nenhuma tag nova criada por engano é uma variante de uma já existente (super
  admin sempre vê a opção de reaproveitar antes de criar).
- **SC-002**: Uma categoria nova pode ser criada e usada num produto sem sair da tela de
  edição do produto.
- **SC-003**: A partir da página de categorias, alguém encontra e abre uma categoria
  específica em até 2 cliques.
- **SC-004**: Em produtos com categoria compartilhada, a seção de relacionados aparece e
  leva a outro produto navegável.
- **SC-005**: Uma pessoa consegue montar uma lista com múltiplos produtos e enviá-la pelo
  WhatsApp em menos de 1 minuto, sem precisar copiar nomes manualmente.
- **SC-006**: A lista de desejos sobrevive ao fechamento do navegador (mesmo aparelho).

## Assumptions

- "Produtos parecidos" (História 4) é definido como produtos ativos que compartilham ao
  menos uma categoria com o produto atual — sem recomendação mais sofisticada (não há
  pedido nem dado disponível para isso); limitado a um punhado de sugestões (não a lista
  inteira da categoria).
- A lista de desejos usa armazenamento local do navegador (sobrevive a fechar a aba/voltar
  depois no mesmo aparelho, mas não sincroniza entre aparelhos/navegadores diferentes) —
  coerente com o catálogo público não ter login nem conceito de conta de cliente.
- O WhatsApp de destino da lista de desejos é o mesmo número comercial já configurado no
  sistema para outras mensagens vindas do site/catálogo (reaproveitado, não um cadastro
  novo) — a mensagem não é atribuída a um vendedor específico, porque a navegação pública
  do catálogo não sabe qual vendedor está atendendo aquela pessoa.
- Tags continuam sendo texto livre por produto (sem virar uma tabela própria no banco) — a
  "sugestão com base nas já existentes" é resolvida a partir de todas as tags já
  cadastradas em qualquer produto, não de uma lista fixa pré-cadastrada.
- Fora de escopo: editar ou excluir uma categoria depois de criada, reordenar categorias,
  e qualquer forma de "carrinho com preço/checkout" — a lista de desejos é só uma lista de
  interesse a ser conversada com o vendedor, não uma compra.
