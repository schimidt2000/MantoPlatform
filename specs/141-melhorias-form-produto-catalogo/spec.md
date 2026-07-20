# Feature Specification: Melhorias na criação de produtos do catálogo

**Feature Branch**: `141-melhorias-form-produto-catalogo`

**Created**: 2026-07-20

**Status**: Draft

**Input**: User description: "na pagina de criar um novo produto no catalogo preciso que melhore umas coisas — 1) ao selecionar as fotos, nenhuma fica marcada como capa, não dá pra escolher; 2) é de extrema importância que exista compressão da foto ao criar o produto, pra não dar problema ao carregar o site nem na miniatura do link do WhatsApp — a foto original pode ser descartada depois; 3) o botão de importar do WordPress é inútil, foi um script usado uma vez só, não pretendo usar de novo."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Escolher qual foto é a capa ao criar um produto novo (Priority: P1)

Ao criar um produto novo e selecionar várias fotos de uma vez, o super admin precisa
escolher qual delas vai ser a capa (a foto que aparece na listagem do catálogo, na busca e
na miniatura quando o link é compartilhado) — hoje isso não é possível: nenhuma foto fica
marcada, e a capa acaba sendo decidida sozinha pela ordem em que os arquivos foram
selecionados, sem controle nenhum.

**Why this priority**: sem isso, criar um produto sempre exige um passo extra (editar
depois pra trocar a capa) — quebra o fluxo de "criar e já ficar pronto".

**Independent Test**: selecionar 3 fotos ao criar um produto novo, marcar a segunda como
capa antes de salvar, e confirmar que ela (e não a primeira) aparece como capa do produto
depois de criado.

**Acceptance Scenarios**:

1. **Given** o formulário de novo produto, **When** o super admin seleciona várias fotos,
   **Then** consegue ver uma prévia de cada uma e marcar qual delas será a capa antes de
   salvar.
2. **Given** fotos selecionadas sem nenhuma marcação explícita de capa, **When** o super
   admin salva, **Then** o sistema usa a primeira foto selecionada como capa (mesmo
   comportamento de hoje, preservado como padrão razoável).
3. **Given** o mesmo controle já existente ao editar um produto (marcar uma foto já salva
   como capa), **When** o super admin usa a tela de criar produto, **Then** a experiência é
   equivalente — só que aplicada às fotos que ainda vão ser enviadas.

---

### User Story 2 - Toda foto de produto é comprimida de forma confiável (Priority: P1)

É essencial que toda foto de produto do catálogo seja salva já otimizada — leve o
suficiente para carregar rápido no site e para aparecer corretamente como miniatura quando
o link do produto é compartilhado no WhatsApp. A foto no tamanho/formato original enviada
pelo super admin não precisa ser preservada depois desse processo.

**Why this priority**: afeta diretamente a experiência de quem recebe o link e a
velocidade do catálogo público — é a característica mais citada como crítica pelo usuário.

**Independent Test**: enviar uma foto grande (alta resolução, vários MB) ao criar um
produto e confirmar que o arquivo salvo no sistema é significativamente menor e carrega
rápido, tanto na página do produto quanto na miniatura de um link compartilhado.

**Acceptance Scenarios**:

1. **Given** uma foto grande (alta resolução) sendo enviada na criação de um produto,
   **When** o produto é salvo, **Then** a foto armazenada é redimensionada/comprimida — o
   arquivo original enviado não é mantido separadamente.
2. **Given** um arquivo que não é uma foto válida num formato suportado (ex.: PDF, ou um
   formato de foto que o sistema não consegue processar), **When** o super admin tenta
   enviá-lo, **Then** o sistema recusa esse arquivo especificamente com uma mensagem clara
   — nunca aceita silenciosamente um arquivo não processado como se fosse uma foto válida.
3. **Given** um produto já criado com fotos comprimidas, **When** alguém compartilha o link
   do produto no WhatsApp, **Then** a miniatura da prévia carrega corretamente (imagem
   leve, dimensões adequadas a uma pré-visualização).

---

### User Story 3 - Remover o botão de importação do WordPress (Priority: P3)

O botão/tela de importar o catálogo do WordPress foi usado uma única vez, na migração
inicial do catálogo (feature 133), e não tem uso previsto daqui pra frente. Ele deve parar
de aparecer como opção na gestão do catálogo.

**Why this priority**: não bloqueia nada nem tem urgência — é limpeza de interface para não
confundir com uma ação que não deve mais ser usada.

**Independent Test**: abrir a tela de gestão do catálogo e confirmar que não há mais nenhum
botão ou link levando à importação do WordPress.

**Acceptance Scenarios**:

1. **Given** a tela de gestão do catálogo, **When** o super admin olha as ações
   disponíveis, **Then** não há mais nenhum botão de "Importar do WordPress" ou equivalente.

---

### Edge Cases

- Super admin marca uma foto como capa e depois a remove da seleção antes de salvar: o
  sistema não deve travar — cai de volta na regra padrão (primeira foto restante vira
  capa).
- Envio de uma única foto: ela é a capa automaticamente, sem precisar de nenhuma marcação
  manual (o controle de escolha só faz diferença com 2+ fotos).
- Foto que o navegador aceita selecionar mas o sistema não consegue abrir/processar de
  forma alguma: tratada como o caso do FR relacionado a recusar arquivo inválido — nunca
  fica "meio salva".

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Ao selecionar fotos para um produto novo, o sistema MUST permitir que o
  super admin marque qual delas será a capa antes de salvar — mesmo controle/conceito já
  existente para fotos de um produto já salvo (edição).
- **FR-002**: Quando nenhuma foto é explicitamente marcada como capa, o sistema MUST usar
  a primeira foto selecionada como padrão (preserva o comportamento atual como
  default razoável).
- **FR-003**: O sistema MUST comprimir/redimensionar toda foto de produto do catálogo ao
  salvar, de forma que o arquivo resultante seja leve o suficiente para carregar
  rapidamente no site e funcionar como miniatura de pré-visualização em links
  compartilhados (ex.: WhatsApp).
- **FR-004**: O arquivo original enviado pelo super admin MUST NOT ser retido em disco
  separadamente após o processo de compressão — só a versão processada é mantida.
- **FR-005**: O sistema MUST recusar, com mensagem clara, um arquivo que não seja uma foto
  válida num formato suportado — nunca aceitar silenciosamente um arquivo não processável
  como se fosse uma foto pronta para uso.
- **FR-006**: A tela de gestão do catálogo MUST deixar de exibir qualquer botão ou link
  para a importação do WordPress.

### Key Entities

- **Foto do produto** (`CatalogItemImage`, já existe): nenhuma mudança de estrutura — a
  garantia de compressão e a escolha de capa já se aplicam ao mesmo dado (`url`,
  `position`) que já existe hoje.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Ao criar um produto com múltiplas fotos, o super admin escolhe a capa antes
  de salvar, sem precisar de um passo de edição posterior.
- **SC-002**: Uma foto de celular típica (vários MB) enviada na criação de um produto
  resulta em um arquivo salvo com uma fração do tamanho original, sem perda perceptível de
  qualidade na exibição do site.
- **SC-003**: Nenhum arquivo inválido/não processável chega a ficar salvo como se fosse
  uma foto de produto.
- **SC-004**: A tela de gestão do catálogo não mostra mais nenhuma opção de importação do
  WordPress.

## Assumptions

- **Sobre remover o botão (História 3)**: a interpretação adotada é remover o *botão/link*
  da interface de gestão do catálogo — não apagar a funcionalidade de importação em si
  (`app/catalogo/importer.py` e a rota administrativa por trás do botão continuam
  existindo, só não ficam mais expostas/alcançáveis pela navegação normal). Justificativa:
  o pedido do usuário foi especificamente sobre o botão ser inútil na interface; manter o
  código por trás intacto (sem excluir nada) é reversível e não tem custo de manutenção,
  enquanto apagar uma funcionalidade que já funcionou é uma ação mais difícil de desfazer
  caso seja necessária de novo no futuro — sem necessidade real de removê-la agora que o
  pedido já é satisfeito só tirando o botão da tela.
- **Sobre compressão (História 2)**: investigação do código atual mostrou que a
  compressão em si já existe (`app/storage.py`, usada tanto pela importação quanto pela
  criação de produto) e funciona corretamente para os formatos já aceitos (JPG, PNG,
  WebP). A lacuna real encontrada: não há validação alguma antes de tentar processar um
  arquivo — se o formato não puder ser aberto pelo processador de imagem (ex.: um arquivo
  de foto em formato não suportado, ou um arquivo que não é imagem), o sistema hoje salva
  o arquivo bruto sem nenhum tratamento, silenciosamente. FR-005 fecha essa lacuna
  específica. Não é necessária nenhuma migração de dado nem mudança na forma como a
  compressão em si funciona para os formatos já suportados.
- Miniatura de WhatsApp (compartilhamento de link) já depende da mesma foto/capa do
  produto (`og:image`, já implementado) — esta feature garante que essa imagem está sempre
  comprimida/leve, não introduz um mecanismo de preview novo.
