# Feature Specification: Gestão de produtos do catálogo (criar e editar)

**Feature Branch**: `139-gestao-catalogo-admin`

**Created**: 2026-07-20

**Status**: Draft

**Input**: User description: "preciso dessa página de criação de novos produtos e também edição dos já existentes. Uma abordagem que podemos fazer é a seguinte. Se a pessoa que estiver olhando o catálogo for uma super admin. Ao entrar no catálogo ou produto pode ser possível entrar em um modo de edição... ou sei lá. Me diga qual a melhor abordagem para criar novos produtos e editar já existentes. Pensando de uma forma que funcione em sincronia com o restante do sistema."

## Abordagem recomendada (resposta à pergunta do usuário)

O usuário pediu explicitamente uma recomendação entre abordagens antes de especificar.
Duas foram consideradas:

1. **"Modo de edição" sobre a própria página pública do catálogo** (sugestão inicial do
   usuário): ao acessar `/catalogo` logado como super admin, controles de edição aparecem
   sobre a página que a cliente final também vê.
2. **Área de gestão dentro do admin** (`/admin/catalogo/...`), separada da página pública,
   escrevendo nas mesmas tabelas que a página pública já lê.

**Recomendação: opção 2.** Motivos:

- **Consistência com o resto do sistema**: é exatamente o padrão já usado duas vezes no
  projeto para o mesmo tipo de problema — "converter algo importado de fonte externa em
  algo nativamente editável": Figurino (fichas antes só via Google Drive, hoje criadas
  nativamente por uma tela própria, autenticada) e os campos dos formulários de
  pré-contrato (editor próprio, restrito a super admin, separado do formulário público que
  a cliente preenche). Seguir o mesmo padrão é o que a constituição do projeto pede
  ("reutilizar antes de criar" — não um padrão de UI novo por feature).
- **A página pública tem um requisito não-negociável de ser simples e seura para o público
  externo** (mobile-first, sem login, `noindex`, link mandado direto no WhatsApp da
  cliente). Misturar ali qualquer controle administrativo — mesmo escondido atrás de uma
  checagem de papel — aumenta a superfície de risco daquela página (é a única do sistema
  pensada para tráfego 100% externo) e complica manter esse requisito ao longo do tempo.
- **"Funcionar em sincronia com o resto do sistema" já está garantido de outra forma**: a
  tela de gestão escreve nas MESMAS tabelas (`CatalogItem`, `CatalogItemImage`,
  `CatalogCategory`) que a página pública lê — qualquer produto criado ou editado aparece
  no catálogo público imediatamente, sem sincronização adicional. A sincronia não depende
  de as duas telas compartilharem o mesmo layout.

A ideia do "modo de edição inline" fica descartada para esta feature, documentada aqui para
não ser reconsiderada sem motivo.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Criar um produto novo no catálogo (Priority: P1)

O super admin precisa colocar um personagem/show novo no catálogo público sem depender de
reimportar o CSV do WordPress (que nem é a fonte de verdade para itens novos, criados
diretamente na plataforma). Ele acessa a área de gestão do catálogo, preenche nome,
descrição, categoria(s) e envia as fotos, e o produto passa a existir e aparecer no
catálogo público.

**Why this priority**: é a lacuna original reportada (não dá pra colocar produto novo sem
mexer direto no banco) — sem isso a feature não entrega nada.

**Independent Test**: criar um produto novo com nome, ao menos uma foto e uma categoria; ao
abrir o catálogo público, o produto aparece na seção da categoria escolhida e sua página de
detalhe carrega corretamente.

**Acceptance Scenarios**:

1. **Given** a área de gestão do catálogo, **When** o super admin preenche nome, descrição,
   categoria e envia uma ou mais fotos e salva, **Then** um novo produto é criado e
   aparece imediatamente no catálogo público, com a primeira foto como capa.
2. **Given** o formulário de criação, **When** o super admin tenta salvar sem nome ou sem
   nenhuma foto, **Then** o sistema bloqueia o salvamento com uma mensagem clara indicando
   o que falta, sem perder o que já foi preenchido.
3. **Given** um nome de produto já usado por outro produto, **When** o super admin tenta
   criar um novo com o mesmo nome, **Then** o sistema ainda permite (nomes podem repetir
   no catálogo de verdade — personagens com o mesmo nome em pacotes diferentes), mas
   garante que o link público de cada um seja único.

---

### User Story 2 - Editar um produto existente (Priority: P1)

O super admin precisa corrigir ou atualizar um produto que já existe no catálogo — trocar
foto, ajustar descrição, mudar categoria — sem depender de reimportar tudo do WordPress
(que, segundo o registro do catálogo, pode nem estar mais no ar no futuro).

**Why this priority**: tão essencial quanto criar — um catálogo de 450 itens vai
inevitavelmente precisar de correções pontuais ao longo do tempo.

**Independent Test**: abrir um produto existente na área de gestão, alterar a descrição e
adicionar uma foto nova, salvar, e conferir que a página pública do produto reflete a
mudança imediatamente.

**Acceptance Scenarios**:

1. **Given** um produto já existente, **When** o super admin abre sua edição, altera
   qualquer campo (nome, descrição, categorias) e salva, **Then** a mudança aparece
   imediatamente na página pública daquele produto.
2. **Given** um produto com várias fotos, **When** o super admin adiciona uma foto nova,
   remove uma foto antiga ou muda qual foto é a capa, **Then** a página pública reflete a
   nova ordem/capa corretamente.
3. **Given** um produto que a Manto não quer mais mostrar (descontinuado) mas cujo
   histórico não deve ser perdido, **When** o super admin o marca como inativo, **Then**
   ele some do catálogo público e da busca, mas continua existindo na área de gestão
   (pode ser reativado depois) — sem excluir de fato os dados.

---

### User Story 3 - Encontrar rapidamente o produto certo para editar (Priority: P2)

Com um catálogo de centenas de itens, o super admin precisa localizar rapidamente o
produto que quer editar, em vez de rolar uma lista enorme.

**Why this priority**: sem busca/filtro, a tela de gestão fica pouco prática num catálogo
deste tamanho — mas o catálogo já funciona hoje (só não é editável), então isso não bloqueia
o valor central das Histórias 1 e 2.

**Independent Test**: na lista de gestão, buscar por parte do nome de um produto e
encontrá-lo entre os resultados filtrados; filtrar só os produtos inativos e ver apenas
esses.

**Acceptance Scenarios**:

1. **Given** a lista de produtos na área de gestão, **When** o super admin digita parte de
   um nome na busca, **Then** a lista filtra para mostrar só os produtos que combinam.
2. **Given** a lista de produtos, **When** o super admin filtra por categoria ou por status
   (ativo/inativo), **Then** a lista mostra só os produtos que atendem ao filtro.

---

### Edge Cases

- Produto sem nenhuma categoria selecionada: o sistema não deve travar — o produto some das
  seções por categoria da home do catálogo, mas continua acessível pela própria página do
  produto (mesmo comportamento hoje esperado para dados incompletos).
- Foto muito grande enviada: aplicar o mesmo limite/tratamento já usado em outros uploads do
  sistema (rejeitar com mensagem clara, sem travar a tela).
- Duas pessoas editando o mesmo produto ao mesmo tempo: a última a salvar prevalece — sem
  bloqueio de edição concorrente (mesmo padrão de qualquer outro formulário do sistema).
- Produto importado do WordPress (`wp_product_id` preenchido) sendo editado manualmente:
  passa a ser editável normalmente; uma futura reimportação do CSV não deve sobrescrever
  edições manuais feitas depois da importação original — comportamento a confirmar como
  fora de escopo (ver Assumptions).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O sistema MUST prover uma tela, restrita a SUPERADMIN, para criar um produto
  novo do catálogo: nome, descrição curta, categoria(s), tags de busca e uma ou mais fotos.
- **FR-002**: O sistema MUST prover uma tela, restrita a SUPERADMIN, para editar qualquer
  campo de um produto já existente, incluindo adicionar/remover/reordenar fotos e trocar
  qual foto é a capa.
- **FR-003**: O sistema MUST permitir marcar um produto como inativo (some do catálogo
  público) sem apagar seus dados, e reverter isso a qualquer momento.
- **FR-004**: Qualquer produto criado ou editado nessa área MUST aparecer no catálogo
  público (`/catalogo`) imediatamente, sem etapa manual de sincronização.
- **FR-005**: O sistema MUST bloquear a criação/edição sem os campos mínimos (nome e ao
  menos uma foto), com mensagem clara e sem apagar o que já foi preenchido — mesmo padrão
  de validação já usado no resto do sistema.
- **FR-006**: A área de gestão MUST oferecer busca por nome e filtro por categoria/status
  (ativo/inativo) na listagem de produtos.
- **FR-007**: A página pública do catálogo (`/catalogo` e a página de cada produto) MUST
  continuar funcionando exatamente como hoje para quem não é super admin — sem nenhum
  controle de edição visível ou acessível ali.
- **FR-008**: Excluir um produto de vez (não só marcar como inativo) MUST ser possível,
  mas só quando o produto não tiver mais nenhuma foto associada nem estiver referenciado
  em nenhum orçamento (ver Assumptions sobre vínculo futuro com orçamentos) — evita
  perda de dado por engano; o caminho recomendado do dia a dia é inativar, não excluir.

### Key Entities

- **Produto do catálogo** (`CatalogItem`, já existe): nome, descrição, categorias, tags,
  fotos, status ativo/inativo. Esta feature não muda a estrutura de dados — ela existe
  desde a importação do WordPress (feature 133) já prevendo esta tela futura (`is_active`
  já existe justamente pra isso). Só passa a ser gerenciável por interface, além de por
  importação.
- **Foto do produto** (`CatalogItemImage`, já existe): imagem vinculada a um produto, com
  posição (a posição 0 é a capa).
- **Categoria** (`CatalogCategory`, já existe): agrupamento usado tanto na página pública
  quanto no filtro da área de gestão.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: O super admin consegue publicar um produto novo no catálogo, do zero até
  aparecer na página pública, sem depender de ninguém mexer direto no banco de dados ou
  reimportar um CSV.
- **SC-002**: Uma correção num produto existente (texto, foto ou categoria) leva menos de
  1 minuto do início da edição até aparecer certo na página pública.
- **SC-003**: Localizar um produto específico para editar, num catálogo de centenas de
  itens, não exige rolar a lista inteira manualmente (busca/filtro cobre o caso comum).
- **SC-004**: Zero mudanças de comportamento perceptíveis na página pública do catálogo
  para quem não é super admin.

## Assumptions

- **Abordagem de UI**: área de gestão dentro do admin (`/admin/catalogo/...`), separada da
  página pública — ver seção "Abordagem recomendada" acima; decisão já tomada nesta
  especificação, não é uma pergunta em aberto.
- Reaproveita a infraestrutura de upload/armazenamento já usada pela importação do catálogo
  (mesma pasta/serviço de fotos) — sem criar um caminho de armazenamento novo.
- `wp_product_id` continua existindo só como identificador de itens vindos da importação
  original; produtos criados nesta tela nascem sem ele. Uma futura reimportação do CSV do
  WordPress não faz parte desta feature e fica fora de escopo decidir agora como ela se
  comportaria diante de edições manuais — se isso vier a ser necessário de novo, é uma
  decisão para quando (e se) o WordPress realmente sair do ar.
- Vínculo entre catálogo e orçamento (mencionado como próximo passo em conversas
  anteriores, mas nunca formalmente pedido) está fora do escopo desta feature — a regra de
  exclusão (FR-008) é escrita de forma genérica para não quebrar se esse vínculo existir no
  futuro, mas não implementa nada dessa integração agora.
- Categorias (`CatalogCategory`) já existem e continuam sendo escolhidas de uma lista
  existente nesta feature — criar/editar categorias em si não foi pedido e fica fora de
  escopo (produto pode ficar sem categoria, ou usar as já existentes).
