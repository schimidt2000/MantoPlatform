# Feature Specification: Catálogo Vitrine Completo — Temas, Personagens e Vídeo

**Feature Branch**: `185-catalogo-vitrine-completo`

**Created**: 2026-07-24

**Status**: Draft

**Input**: User description: "Refinar, enriquecer e evoluir por completo o Módulo de Catálogo, abrangendo o Catálogo Público do Cliente (frontend/apps/public) e o Gerenciador de Catálogo Interno (frontend/apps/internal). Suporte a relação Tema/Personagem, vídeo (Drive/MP4/Vimeo), vínculo direto a Ficha de Figurino, design vibrante com animações fluidas, chip input de tags, e auto-vínculo de figurino na criação de eventos."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Cliente descobre um Tema e seu elenco de Personagens (Priority: P1)

Um cliente (visitante anônimo) acessa o link público de um Tema do catálogo (ex.: "A Casa Mágica da Gabby") e vê a vitrine com fotos e vídeos do pacote completo, além de uma seção "Elenco Individual" listando cada Personagem filho (ex.: "Gatuno", "Gabby") com sua própria foto/vídeo. O cliente pode adicionar o Tema inteiro ou apenas os Personagens que interessam à sua lista de interesse, e enviar essa lista como pedido de orçamento.

**Why this priority**: É o núcleo comercial da vitrine — sem isso, o catálogo não comunica que um Tema é composto por atrações individuais que também podem ser contratadas separadamente, o que hoje é invisível para o cliente.

**Independent Test**: Publicar um Tema com 2 Personagens filhos cadastrados (via gerenciador interno) e acessar `/catalogo/:slug` sem sessão autenticada — verificar que os cards de Personagens aparecem, cada um adicionável à lista independentemente do Tema.

**Acceptance Scenarios**:

1. **Given** um Tema publicado com 2 Personagens filhos cadastrados, **When** o cliente abre `/catalogo/:slug`, **Then** vê a seção "Elenco Individual" com um card por Personagem (foto/preview, nome, botão "+ Adicionar à lista").
2. **Given** a página de um Tema, **When** o cliente clica "+ Adicionar à lista" em um Personagem específico, **Then** apenas aquele Personagem entra na lista de interesse (o Tema completo não é adicionado junto).
3. **Given** a página de um Tema, **When** o cliente clica "Adicionar à lista" no cabeçalho do Tema, **Then** o pacote completo entra na lista de interesse como um único item.
4. **Given** um Tema sem nenhum Personagem filho cadastrado, **When** o cliente abre a página, **Then** a seção "Elenco Individual" não é exibida (sem espaço vazio/quebrado).

---

### User Story 2 - Cliente assiste vídeos de prévia na galeria do catálogo (Priority: P1)

Na galeria de mídias de um Tema ou Personagem, o cliente alterna entre fotos e vídeos. Vídeos tocam automaticamente em loop, mudos, e o cliente pode ativar o áudio ou abrir em tela cheia. A troca entre uma foto horizontal e um vídeo vertical (9:16) não causa saltos bruscos de layout.

**Why this priority**: Vídeo é o principal diferencial comercial pedido — hoje o catálogo só suporta fotos, subestimando shows que dependem de movimento/performance para vender.

**Independent Test**: Cadastrar um item com 1 foto horizontal e 1 vídeo vertical e navegar a galeria pública, verificando autoplay mudo, botões de som/tela cheia e transição suave de altura do container.

**Acceptance Scenarios**:

1. **Given** um item com vídeo cadastrado, **When** a mídia de vídeo entra em foco na galeria, **Then** o vídeo inicia automaticamente, mudo, em loop, sem controles nativos do navegador por cima do layout.
2. **Given** um vídeo em reprodução, **When** o cliente clica no botão de som, **Then** o áudio é ativado/desativado sem reiniciar o vídeo.
3. **Given** um vídeo em reprodução, **When** o cliente clica no botão de tela cheia, **Then** o vídeo expande para tela cheia mantendo a reprodução.
4. **Given** a galeria alternando entre uma foto horizontal e um vídeo vertical, **When** a transição ocorre, **Then** o container se redimensiona de forma animada (sem "pulo" instantâneo).
5. **Given** um link de vídeo inválido ou indisponível, **When** a galeria tenta carregá-lo, **Then** a mídia é ignorada silenciosamente na vitrine pública (sem quebrar a navegação) e sinalizada no gerenciador interno.

---

### User Story 3 - Time comercial gerencia Temas, Personagens e mídias no painel interno (Priority: P1)

Um usuário staff (comercial/admin) usa o Gerenciador de Catálogo Interno para criar/editar um Tema, cadastrar seus Personagens filhos (nome, foto, URL de vídeo) e vincular cada Personagem à Ficha de Figurino correspondente. Tags são digitadas como chips removíveis com autocomplete das tags já existentes.

**Why this priority**: Sem uma tela de gestão, a estrutura de dados nova (Tema/Personagem, vídeo, vínculo de figurino) fica inacessível para quem mantém o catálogo — a P1 e P2 do cliente dependem de dados que só existem se o staff conseguir cadastrá-los.

**Independent Test**: No painel `/admin/catalogo`, criar um Tema, adicionar 2 Personagens com foto e URL de vídeo, vincular cada um a uma Ficha de Figurino existente via busca, salvar, e conferir que os dados aparecem corretamente na vitrine pública (US1).

**Acceptance Scenarios**:

1. **Given** o formulário de edição de um Tema, **When** o staff digita uma tag e pressiona Enter ou vírgula, **Then** a tag vira um chip removível (✕) e o campo de texto limpa para a próxima.
2. **Given** o campo de tags, **When** o staff começa a digitar, **Then** aparecem sugestões das tags já usadas em outros produtos do catálogo, filtradas pelo texto digitado.
3. **Given** o painel de Personagens de um Tema, **When** o staff adiciona um novo Personagem com nome, foto e URL de vídeo, **Then** o Personagem é salvo como filho daquele Tema.
4. **Given** um Personagem sendo editado, **When** o staff busca no dropdown de Ficha de Figurino e seleciona uma ficha, **Then** o Personagem fica vinculado a essa `figurino_id`.
5. **Given** uma URL de vídeo inválida (não é Drive/MP4/Vimeo reconhecível), **When** o staff tenta salvar, **Then** o sistema recusa com uma mensagem de erro específica no campo.

---

### User Story 4 - Comercial cria evento e o figurino do elenco é vinculado automaticamente (Priority: P2)

Ao montar um Novo Evento, o comercial seleciona no formulário os itens do catálogo (Tema e/ou Personagens) que compõem o elenco contratado. O sistema auto-vincula a Ficha de Figurino de cada Personagem selecionado ao elenco do evento, eliminando um passo manual hoje sujeito a esquecimento.

**Why this priority**: É uma melhoria de eficiência operacional que depende da estrutura de dados da US3 já existir — não bloqueia o lançamento da vitrine pública, mas é o elo que fecha o ciclo comercial→produção.

**Independent Test**: Criar um evento novo, selecionar um Personagem do catálogo com `figurino_id` vinculada, e verificar que a Ficha de Figurino aparece automaticamente associada ao elenco do evento sem ação manual adicional.

**Acceptance Scenarios**:

1. **Given** o formulário de Novo Evento, **When** o comercial seleciona um Personagem do catálogo que tem `figurino_id` vinculada, **Then** a Ficha de Figurino correspondente é associada automaticamente ao elenco do evento.
2. **Given** um Personagem do catálogo sem `figurino_id` vinculada, **When** selecionado no formulário de evento, **Then** o evento é criado normalmente e nenhum vínculo automático é tentado (sem erro).
3. **Given** um vínculo automático já aplicado, **When** o comercial remove manualmente a ficha do elenco do evento, **Then** a remoção manual prevalece (o sistema não reaplica o vínculo automático nesse evento).

---

### User Story 5 - Catálogo público não é indexado por buscadores (Priority: P3)

As páginas do catálogo público carregam com uma diretiva que instrui buscadores a não indexar nem seguir os links, mantendo o catálogo acessível só por link direto compartilhado pelo time comercial.

**Why this priority**: Requisito de privacidade comercial (evitar que preços/pacotes apareçam em buscas do Google), mas não bloqueia nenhum fluxo funcional das outras stories.

**Independent Test**: Carregar `/catalogo` e `/catalogo/:slug` e inspecionar o `<head>` renderizado, confirmando a presença da diretiva de não-indexação em ambas as rotas.

**Acceptance Scenarios**:

1. **Given** a rota `/catalogo`, **When** a página carrega, **Then** o `<head>` contém a diretiva de não-indexação/não-seguimento para buscadores.
2. **Given** a rota `/catalogo/:slug` de qualquer Tema, **When** a página carrega, **Then** o `<head>` contém a mesma diretiva.

---

### Edge Cases

- Tema com Personagem filho cujo vídeo é o único media (sem foto) — a vitrine deve exibir o vídeo como mídia principal do card, não quebrar o layout do grid.
- Personagem filho vinculado a uma Ficha de Figurino que é excluída posteriormente — o vínculo deve degradar de forma segura (Personagem continua existindo, sem `figurino_id` pendurada em registro inexistente).
- Staff tenta excluir um Tema que ainda tem Personagens filhos — o sistema deve exigir remoção/realocação dos filhos antes, ou excluir em cascata de forma explícita (decisão registrada em Assumptions).
- Cliente com JavaScript de animação desabilitado (`prefers-reduced-motion`) — a galeria deve alternar mídias sem a animação de redimensionamento, mas continuar funcional.
- URL de vídeo do Google Drive que exige permissão de acesso (não é "qualquer pessoa com o link") — o vídeo falha ao carregar; a vitrine deve tratar como mídia indisponível (mesmo comportamento do edge case de link inválido em US2).
- Dois Personagens com o mesmo nome sob Temas diferentes — permitido, pois o identificador público é o slug do Tema pai + posição, não o nome do Personagem isoladamente.
- Lista de interesse do cliente misturando Temas completos e Personagens avulsos de Temas diferentes — cada item da lista deve ser identificável de forma independente no orçamento gerado.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O sistema DEVE permitir que um produto do catálogo (Tema) tenha zero ou mais Personagens filhos, cada um como entidade própria com nome, foto e URL de vídeo.
- **FR-002**: O sistema DEVE permitir associar uma URL de vídeo externo (Google Drive, MP4 direto, ou Vimeo) tanto ao Tema quanto a cada Personagem filho, sem armazenar o arquivo de vídeo no servidor.
- **FR-003**: O sistema DEVE permitir vincular cada Personagem filho a uma Ficha de Figurino existente (`figurino_id`), com busca/seleção no gerenciador interno.
- **FR-004**: A vitrine pública DE UM Tema DEVE exibir uma seção com todos os seus Personagens filhos ativos, cada um com foto/preview de vídeo, nome e ação de adicionar à lista de interesse.
- **FR-005**: O cliente DEVE poder adicionar à lista de interesse tanto o Tema completo quanto Personagens filhos individualmente, como itens distintos e rastreáveis.
- **FR-006**: A galeria de mídias pública DEVE suportar reprodução de vídeo com autoplay mudo, loop, `playsinline`, controle de mudo/desmudo e alternância para tela cheia.
- **FR-007**: A galeria de mídias pública DEVE animar a transição de tamanho do container ao alternar entre mídias de proporções diferentes (foto horizontal ↔ vídeo vertical), respeitando preferência de movimento reduzido do cliente.
- **FR-008**: As páginas públicas do catálogo (`/catalogo` e `/catalogo/:slug`) DEVEM emitir a diretiva de não-indexação/não-seguimento para buscadores.
- **FR-009**: O gerenciador interno DEVE substituir o campo de texto cru de tags por um input tokenizado (chips), com criação de chip via Enter ou vírgula, remoção via botão dedicado, e sugestões de autocomplete das tags já existentes no catálogo.
- **FR-010**: O gerenciador interno DEVE fornecer um painel para cadastrar, editar, reordenar e remover Personagens filhos de um Tema, incluindo upload de foto e campo de URL de vídeo.
- **FR-011**: O gerenciador interno DEVE validar o formato da URL de vídeo (padrões reconhecíveis de Google Drive/MP4/Vimeo) antes de salvar, recusando URLs em formato não suportado com mensagem de erro específica.
- **FR-012**: O formulário de criação/edição de evento DEVE permitir selecionar itens do catálogo (Tema e/ou Personagens) como parte do elenco contratado.
- **FR-013**: Ao selecionar um Personagem do catálogo com `figurino_id` vinculada no formulário de evento, o sistema DEVE auto-vincular essa Ficha de Figurino ao elenco do evento sem exigir ação manual adicional.
- **FR-014**: A remoção manual de um vínculo de figurino auto-aplicado por um evento NÃO DEVE ser desfeita/reaplicada automaticamente pelo sistema.
- **FR-015**: A estrutura de dados nova (Personagens filhos, campos de vídeo, vínculo de figurino) DEVE ser aditiva — produtos do catálogo existentes (sem Personagens, sem vídeo) DEVEM continuar funcionando sem alteração de comportamento.
- **FR-016**: O design visual das páginas públicas do catálogo DEVE ser distinto do padrão minimalista preto/cinza usado nas telas internas (ERP), usando paleta vibrante da marca (destaque roxo/dourado), sombras suaves, bordas elegantes e micro-animações (150–350ms) respeitando `prefers-reduced-motion`.
- **FR-017**: Vídeos com URL inválida ou inacessível DEVEM ser omitidos silenciosamente na vitrine pública, sem quebrar a navegação, e sinalizados de alguma forma visível para o staff no gerenciador interno.

### Key Entities *(include if feature involves data)*

- **Tema (CatalogItem existente)**: Produto "pai" do catálogo (ex.: um pacote de personagens temático). Ganha suporte a uma ou mais URLs de vídeo além das fotos já existentes. Continua sendo a unidade vendável como pacote completo.
- **Personagem (nova entidade filha)**: Pertence a exatamente um Tema. Tem nome, uma foto, uma URL de vídeo opcional, posição de exibição dentro do Tema, e um vínculo opcional a uma Ficha de Figurino. É uma unidade vendável independente do Tema.
- **Ficha de Figurino (entidade existente)**: Já cadastrada no módulo de Figurino; passa a ser referenciada por Personagens do catálogo via `figurino_id` e usada para auto-vínculo no elenco de eventos.
- **Lista de Interesse / Item de Orçamento**: Cada entrada identifica se refere a um Tema completo ou a um Personagem específico, permitindo que o cliente monte uma lista mista.
- **Tag do Catálogo**: Já existente como texto livre; passa a ser gerenciada via componente de chips com deduplicação e reaproveitamento de grafia (comportamento de normalização já existente é preservado).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Um cliente consegue abrir a página pública de um Tema com Personagens e adicionar um Personagem individual à lista de interesse em até 3 cliques, sem confusão sobre o que foi adicionado.
- **SC-002**: 100% dos vídeos cadastrados com URL em formato suportado reproduzem em autoplay mudo na vitrine pública sem interação do cliente.
- **SC-003**: A troca entre mídias de proporções diferentes na galeria não produz nenhum salto de layout perceptível (transição de altura sempre animada) em telas mobile e desktop.
- **SC-004**: O staff consegue cadastrar um Tema completo com 3 Personagens (nome, foto, vídeo, vínculo de figurino) em uma única sessão no gerenciador, sem precisar recarregar a página.
- **SC-005**: 100% dos produtos do catálogo existentes antes desta feature continuam visíveis e funcionais na vitrine pública após a migration, sem necessidade de re-cadastro.
- **SC-006**: As páginas `/catalogo` e `/catalogo/:slug` não aparecem no índice de busca do Google em uma verificação de `site:` após propagação (diretiva de não-indexação presente desde o primeiro deploy).
- **SC-007**: Ao criar um evento selecionando um Personagem com figurino vinculado, o vínculo automático aparece no elenco do evento em 100% dos casos, sem passo manual adicional.

## Assumptions

- O componente de chip/tag input e o painel de Personagens são construídos como componentes novos dentro de `@manto/ui`/`frontend/apps/internal`, sem dependências externas novas (sem libs de terceiros para tag-input), seguindo o design system já existente do projeto.
- "Vídeo hospedado no Google Drive" significa um link de compartilhamento público ("qualquer pessoa com o link"); o sistema não faz autenticação OAuth para acessar vídeos privados do Drive.
- Excluir um Tema que ainda tem Personagens filhos exclui os Personagens em cascata (mesmo padrão hoje usado para fotos de um `CatalogItem`), com confirmação explícita no gerenciador interno antes da ação irreversível.
- A lista de interesse / orçamento do cliente já existente (feature 140) é estendida para suportar itens do tipo "Personagem" além de "Tema" — não é uma feature nova de carrinho.
- O auto-vínculo de figurino em Novo Evento (US4) aplica-se ao fluxo de criação de evento já existente em `/events/new`; não inclui retroaplicar vínculos a eventos já criados antes desta feature.
- Migration de banco é aditiva (novas tabelas/colunas nullable), sem alterar ou remover colunas/tabelas existentes de `CatalogItem`, `CatalogCategory`, `CatalogItemImage`.
- "Elegante e vibrante" é operacionalizado usando os tokens de cor/marca já definidos no design system do projeto (não é necessário criar uma paleta nova do zero) — reforçados com roxo/dourado como cor de destaque conforme pedido.
