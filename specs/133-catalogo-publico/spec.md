# Feature Specification: Catálogo Público de Personagens (Import do WordPress)

**Feature Branch**: `133-catalogo-publico`

**Created**: 2026-07-16

**Status**: Draft

**Input**: Migrar o catálogo de personagens/shows hoje hospedado no WordPress para dentro
da Plataforma Manto: importar os 451 itens do export (`Produtos Catalogo/wc-product-
export-*.csv`), servir uma página pública (sem login, sem indexação no Google) com busca
e navegação por seções, design próprio e refinado (não segue o padrão visual do sistema),
com imagens leves o bastante para gerar miniatura ao compartilhar o link no WhatsApp.
Integrações futuras (anexar ao orçamento, cliente sinalizar o que gostou, estoque
associado, tela de edição/criação de itens) ficam fora do escopo desta feature — só a
importação e a navegação pública.

## Contexto

O catálogo de personagens/shows da Manto vive hoje só no site WordPress, desconectado do
resto do sistema. O WordPress pode sair do ar. O export do WooCommerce (451 produtos) tem
nome, descrição curta, categorias, tags (para busca) e fotos — mas não tem preço, estoque
ou SKU, porque nunca foi usado como loja de verdade, só como vitrine visual. Este é o
ponto de partida de uma futura integração mais profunda com orçamentos e estoque, mas essa
integração não é construída agora.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Trazer todo o catálogo para dentro do sistema (Priority: P1)

Alguém da equipe roda a importação do catálogo exportado do WordPress. Cada personagem/
show vira um item no sistema, com suas fotos baixadas e leves o bastante para carregar
rápido e gerar miniatura ao ser compartilhado.

**Why this priority**: sem os dados importados, não existe catálogo nenhum para mostrar —
é a base de tudo o mais.

**Independent Test**: rodar a importação com o CSV fornecido e conferir que os itens
esperados existem no sistema, com fotos acessíveis e categorias corretas.

**Acceptance Scenarios**:

1. **Given** o CSV exportado do WordPress, **When** a importação é executada, **Then**
   todo item publicado e com conteúdo válido (nome, ao menos uma categoria e ao menos uma
   foto) é criado no sistema.
2. **Given** um item com múltiplas fotos no CSV, **When** ele é importado, **Then** todas
   as fotos daquele item ficam disponíveis, na mesma ordem em que apareciam no WordPress.
3. **Given** uma foto pesada baixada do WordPress, **When** ela é processada na
   importação, **Then** vira uma versão leve, e o processo registra quais fotos (se
   houver) continuam pesadas mesmo depois de processadas, para revisão manual.
4. **Given** um registro do CSV sem conteúdo aproveitável (ex.: sem categoria e sem foto,
   claramente um rascunho abandonado), **When** a importação roda, **Then** esse registro
   é ignorado, sem virar um item vazio no catálogo.
5. **Given** que a importação já rodou uma vez, **When** ela é executada de novo com o
   mesmo CSV, **Then** os itens já importados não são duplicados.

### User Story 2 - Cliente navega o catálogo (Priority: P1)

Uma cliente recebe o link do catálogo (ex.: pelo WhatsApp) e abre pelo celular ou
computador, sem precisar de login. Ela busca por uma palavra (ex.: um tema, um
personagem) ou navega pelas seções (categorias) até achar o que procura, num visual
cuidado e diferente do restante do sistema interno.

**Why this priority**: é o objetivo final da migração — dar à cliente uma forma de
explorar o catálogo hospedada no próprio sistema da Manto, no lugar do WordPress.

**Independent Test**: abrir a página do catálogo sem estar logado, buscar por um termo que
aparece nas tags de um item específico e confirmar que ele aparece nos resultados; alternar
entre "ver tudo" e uma seção específica e confirmar que a lista muda de acordo.

**Acceptance Scenarios**:

1. **Given** a página do catálogo, **When** qualquer pessoa (sem login) acessa a URL,
   **Then** a página abre normalmente, sem exigir autenticação.
2. **Given** a página do catálogo, **When** alguém digita um termo de busca, **Then** os
   itens cujo nome, categoria ou alguma tag combinam com o termo aparecem — mesmo que o
   termo só apareça numa tag, não no nome.
3. **Given** a página do catálogo, **When** a pessoa escolhe "ver tudo", **Then** vê todos
   os itens juntos; **When** escolhe uma seção específica, **Then** vê só os itens
   daquela seção.
4. **Given** a busca ou uma seção sem nenhum item correspondente, **When** o resultado é
   exibido, **Then** aparece um estado vazio claro (nunca uma página em branco sem
   explicação).
5. **Given** a página do catálogo, **When** um mecanismo de busca como o Google tenta
   indexá-la, **Then** ela não deve aparecer nos resultados de busca (mesma regra já
   aplicada ao restante do sistema).

### User Story 3 - Compartilhar um item específico com miniatura no WhatsApp (Priority: P2)

Alguém da comercial abre um item do catálogo, copia o link daquele item específico e cola
numa conversa do WhatsApp. A pessoa que recebe vê uma prévia com a foto, o nome e uma
descrição curta — não só um link cru.

**Why this priority**: é o comportamento que motivou a preocupação com o peso das
imagens — sem uma página própria por item com prévia rica, o link compartilhado fica sem
graça e sem a miniatura que a equipe está acostumada a ver.

**Independent Test**: abrir um item específico do catálogo, copiar o link e colar em um
verificador de prévia de link (ou no próprio WhatsApp) e conferir que aparece imagem,
título e descrição.

**Acceptance Scenarios**:

1. **Given** um item do catálogo, **When** alguém abre sua página específica, **Then** vê
   o nome, a descrição, todas as fotos daquele item e um botão para copiar o link.
2. **Given** o link de um item específico, **When** esse link é compartilhado numa
   plataforma que gera prévia (ex.: WhatsApp), **Then** a prévia mostra a foto principal
   do item, o nome e uma descrição curta.

### Edge Cases

- Nomes repetidos no CSV que são, na prática, itens diferentes (categorias/fotos
  diferentes) DEVEM virar itens separados no catálogo — só duplicatas reais (mesmo nome,
  mesmo conteúdo, uma delas vazia/rascunho) são descartadas.
- Um item sem nenhuma foto não deve quebrar a página — mas como o objetivo é um catálogo
  visual, um item assim é uma exceção rara e deve ficar visualmente sinalizado como
  incompleto ou simplesmente não entrar na importação (ver User Story 1, cenário 4).
- Se o WordPress sair do ar durante ou depois da importação, o catálogo dentro do sistema
  continua funcionando normalmente — nenhuma foto do catálogo depende do WordPress
  continuar no ar.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O sistema DEVE importar os itens do arquivo CSV exportado do WordPress,
  criando um item de catálogo por produto válido (nome + ao menos uma categoria + ao
  menos uma foto).
- **FR-002**: A importação DEVE baixar as fotos de cada item (hoje hospedadas no
  WordPress) e guardá-las dentro do próprio sistema, para que o catálogo não dependa do
  WordPress continuar no ar.
- **FR-003**: A importação DEVE processar cada foto para um tamanho de arquivo leve,
  adequado a carregar rápido e gerar miniatura ao ser compartilhada por WhatsApp.
- **FR-004**: A importação DEVE registrar (relatório ao final) quaisquer fotos que
  continuem pesadas mesmo depois do processamento, para revisão manual.
- **FR-005**: A importação DEVE poder ser executada mais de uma vez sobre o mesmo CSV sem
  duplicar itens já importados.
- **FR-006**: Itens do CSV sem conteúdo aproveitável (sem categoria e sem foto) NÃO DEVEM
  virar itens no catálogo.
- **FR-007**: A página principal do catálogo DEVE ser acessível sem login.
- **FR-008**: A página principal do catálogo e as páginas de item DEVEM ser configuradas
  para não aparecer em buscadores como o Google (mesma regra já aplicada ao restante do
  sistema).
- **FR-009**: A página principal DEVE ter uma busca que encontra itens pelo nome, pela
  categoria ou por qualquer tag associada — a busca não pode se limitar só ao nome.
- **FR-010**: A pessoa visitante DEVE poder alternar entre ver todos os itens juntos e ver
  só os itens de uma seção (categoria) específica.
- **FR-011**: Cada item DEVE ter sua própria página, com nome, descrição, todas as suas
  fotos e um jeito de copiar o link daquela página específica.
- **FR-012**: A página de cada item DEVE ser configurada para que, ao ser compartilhada em
  aplicativos como WhatsApp, apareça uma prévia com foto, nome e descrição curta do item.
- **FR-013**: O visual da página pública do catálogo NÃO PRECISA seguir os componentes/
  paleta usados no restante do sistema interno — pode (e deve) ter identidade visual
  própria, condizente com uma vitrine voltada à cliente final.
- **FR-014**: Buscas ou seções sem nenhum item correspondente DEVEM mostrar um estado
  vazio explicativo.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Os itens válidos do export do WordPress (nome + categoria + foto) aparecem
  no catálogo do sistema depois da importação, sem necessidade de reconferência manual
  item a item.
- **SC-002**: Uma pessoa sem login consegue achar um item específico do catálogo (por
  busca ou por seção) em poucos segundos.
- **SC-003**: Um link de item específico compartilhado numa conversa de WhatsApp mostra
  uma prévia com imagem — não aparece só como texto/link cru.
- **SC-004**: O catálogo publicado continua acessível mesmo se o WordPress atual sair do
  ar.

## Assumptions

- Fora do escopo desta feature (mencionado como direção futura pelo usuário, não
  construído agora): anexar itens do catálogo a um orçamento; a cliente sinalizar itens
  que gostou e isso virar uma mensagem para a comercial; associação com estoque real;
  tela de edição/criação de novos itens do catálogo. A modelagem de dados desta feature
  evita decisões que dificultem essas adições depois (ex.: cada item guarda um
  identificador estável e sua galeria de fotos em registros próprios), mas nenhuma
  interface para essas funções é criada agora.
- O item de CSV sem categoria/foto identificado na análise ("Welcome Drinks - Branca",
  versão rascunho) é o único descartado por essa regra; os demais nomes repetidos no CSV
  são itens genuinamente diferentes e todos são importados.
- "Leve o bastante para gerar miniatura no WhatsApp" é tratado como um alvo de tamanho de
  arquivo após processamento (não um teste automatizado contra o WhatsApp de verdade,
  que está fora do controle do sistema) — a importação processa e reporta o que ainda
  ficar acima do alvo, para decisão humana caso a caso.
- Tags do CSV (bem numerosas e específicas) servem só para busca — não viram uma segunda
  navegação por seção além das categorias já existentes no CSV.
- Sem mecanismo de atualização automática do WordPress: a importação é executada quando
  necessário (inicialmente, e de novo se o catálogo do WordPress mudar antes de ele sair
  do ar) — não há sincronização contínua nem tela de import recorrente nesta feature.
