# Feature Specification: Reestruturação do Banco de Figurinos

**Feature Branch**: `183-figurinos-modulo-completo`

**Created**: 2026-07-24

**Status**: Draft

**Input**: User description: "Reestruturar e refinar por completo o Módulo do Banco de Figurinos (/figurinos e /figurinos/[id]) no app Beta (apps/internal), corrigindo o enquadramento das fotos, os botões de ação e o painel de figurinos faltantes."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Navegar o banco de figurinos com densidade e enquadramento corretos (Priority: P1)

Qualquer usuário autenticado abre `/figurinos` e vê uma grade densa (5-6 colunas em telas widescreen) de fichas de figurino, cada card mostrando a foto do figurino inteira (da cabeça aos pés, sem cortes), o nome do personagem, a quantidade de peças e a data da última edição.

**Why this priority**: É a tela principal do módulo — sem uma grade legível e bem enquadrada, nenhuma outra ação (imprimir, editar, buscar) tem valor.

**Independent Test**: Abrir `/figurinos` com fichas cadastradas e confirmar visualmente que a grade tem 5-6 colunas em desktop widescreen, os cards usam proporção vertical (retrato) com a foto alinhada ao topo, e o rodapé exibe nome, nº de peças e data.

**Acceptance Scenarios**:

1. **Given** existem fichas de figurino cadastradas com foto, **When** o usuário abre `/figurinos` em uma tela widescreen (≥1280px), **Then** a grade exibe 5-6 colunas de cards.
2. **Given** uma ficha tem foto de corpo inteiro, **When** o card é renderizado, **Then** a imagem preenche o quadro vertical (`object-cover`, alinhada ao topo) sem esticar/distorcer e sem cortar a cabeça.
3. **Given** uma ficha não tem foto, **When** o card é renderizado, **Then** um placeholder ocupa o mesmo quadro vertical, mantendo a grade alinhada.
4. **Given** um card qualquer, **When** o usuário olha o rodapé, **Then** vê nome do personagem, quantidade de peças e data da última edição (ou "—" quando nunca editado).

---

### User Story 2 - Agir diretamente a partir do card (Priority: P1)

Um usuário com permissão de edição de figurino (FIGURINO ou SUPERADMIN) precisa imprimir a ficha completa ou editá-la sem sair da grade.

**Why this priority**: Imprimir e editar são as duas ações mais frequentes do dia a dia (preparação de eventos); hoje só existe o link de edição, sem atalho de impressão no card.

**Independent Test**: Em um card com permissão de edição, clicar em "Imprimir" abre a ficha de impressão em nova aba; clicar no ícone de lápis abre a edição da ficha.

**Acceptance Scenarios**:

1. **Given** um usuário com permissão de edição, **When** ele clica no botão "Imprimir" de um card, **Then** a ficha de impressão completa do figurino abre em uma nova aba (fluxo de impressão/PDF já existente no sistema).
2. **Given** um usuário com permissão de edição, **When** ele clica no ícone de lápis (Editar) de um card, **Then** ele é levado para a tela/gaveta de edição daquela ficha.
3. **Given** um usuário sem permissão de edição (sem papel FIGURINO/SUPERADMIN), **When** ele vê o card, **Then** os botões "Imprimir" e "Editar" continuam visíveis apenas para quem pode editar — usuários somente leitura veem o card sem essas ações de escrita (impressão pode ficar disponível a todos, edição não).

---

### User Story 3 - Gerenciar personagens sem ficha, com controle restrito (Priority: P2)

Um SUPERADMIN precisa ver quais personagens já usados em eventos ainda não têm ficha de figurino, sem que esse alerta polua a tela de todos os outros perfis, e precisa poder descartar um alerta que não é mais relevante ou vincular o personagem a uma ficha já existente.

**Why this priority**: Hoje o alerta de "personagens sem ficha" aparece sempre aberto para todo mundo, ocupando espaço e sem nenhuma ação — vira ruído para quem não decide sobre figurino.

**Independent Test**: Logar como SUPERADMIN, ver o painel "Figurinos solicitados/faltantes" fechado por padrão com a contagem no título; abrir, descartar um item e associá-lo a uma ficha existente; logar como um usuário não-SUPERADMIN e confirmar que o painel não aparece.

**Acceptance Scenarios**:

1. **Given** um usuário SUPERADMIN, **When** ele abre `/figurinos` e existem personagens sem ficha, **Then** vê um painel colapsável fechado por padrão com o título "⚠️ Figurinos solicitados/faltantes (X itens)".
2. **Given** um usuário que não é SUPERADMIN, **When** ele abre `/figurinos`, **Then** o painel de figurinos faltantes não é exibido, mesmo que existam personagens sem ficha.
3. **Given** o painel aberto, **When** o SUPERADMIN clica em "Excluir" em um item, **Then** aquele alerta some da lista (para todos os usuários, em toda sessão futura) sem apagar nenhum evento ou personagem.
4. **Given** o painel aberto, **When** o SUPERADMIN clica em "Associar a uma ficha existente" em um item e escolhe uma ficha, **Then** o personagem passa a apontar para aquela ficha (os cargos de evento daquele personagem ficam vinculados à ficha escolhida) e o item some da lista de faltantes.

---

### User Story 4 - Encontrar uma ficha rapidamente (Priority: P3)

Qualquer usuário autenticado precisa localizar rapidamente a ficha de um personagem específico em um banco que já tem centenas de fichas, seja pelo nome ou por uma categoria/tag.

**Why this priority**: Sem busca e filtro, a densidade de 5-6 colunas ainda exige rolagem manual longa em bancos grandes — valor incremental sobre a P1, não bloqueante para o MVP.

**Independent Test**: Digitar um nome parcial no campo de busca e ver a grade filtrar em tempo real; selecionar uma tag no filtro de categoria e ver apenas fichas com aquela tag.

**Acceptance Scenarios**:

1. **Given** a grade carregada, **When** o usuário digita parte de um nome de personagem na busca, **Then** somente fichas cujo nome contém o texto (case-insensitive, sem acento) permanecem visíveis.
2. **Given** fichas com tags cadastradas, **When** o usuário seleciona uma tag no filtro, **Then** somente fichas com aquela tag aparecem; **When** ele limpa o filtro, **Then** todas voltam a aparecer.
3. **Given** busca e filtro de tag combinados, **When** ambos têm valor, **Then** o resultado é a interseção (nome contém o texto E tem a tag).

### Edge Cases

- Ficha sem nenhuma peça cadastrada → rodapé mostra "0 peça(s)", não quebra o layout.
- Ficha nunca editada (sem `updated_at`) → mostra a data de criação como referência, ou "—" se nenhuma das duas existir.
- Personagem sem ficha aparece em múltiplos eventos → conta como um único item na lista de faltantes (agrupado por nome normalizado).
- SUPERADMIN tenta associar um item faltante a uma ficha, mas não seleciona nenhuma → ação fica desabilitada até uma ficha ser escolhida.
- Item de "faltante" é descartado, mas o mesmo nome de personagem volta a ser usado em um evento novo → deve reaparecer na lista (o descarte vale para a ocorrência atual, não bane o nome para sempre) — ver FR-011.
- Usuário sem permissão de edição tenta acessar a URL de edição diretamente → bloqueado pelo mesmo RBAC já existente na tela de edição.
- Tela estreita (mobile/tablet) → a grade reduz de 5-6 colunas para 2-3/1 coluna, mantendo a proporção do card.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: A grade de `/figurinos` MUST exibir 5 a 6 colunas em telas ≥1280px de largura, reduzindo progressivamente em telas menores.
- **FR-002**: Cada card MUST exibir a foto do figurino em um quadro de proporção vertical (retrato), com a imagem cobrindo o quadro e alinhada ao topo, mostrando o figurino inteiro sempre que a foto original permitir.
- **FR-003**: Cada card MUST exibir no rodapé: nome do personagem, quantidade de peças e data da última edição (fallback para data de criação, depois "—").
- **FR-004**: Cada card MUST exibir um botão primário "Imprimir" que abre a ficha de impressão completa do figurino (fluxo já existente) em uma nova aba/janela.
- **FR-005**: Cada card MUST exibir um ícone/botão "Editar" (lápis), visível apenas para usuários com papel FIGURINO ou SUPERADMIN, que leva à edição daquela ficha.
- **FR-006**: O sistema MUST exibir o painel "Figurinos solicitados/faltantes" exclusivamente para usuários SUPERADMIN.
- **FR-007**: O painel de faltantes MUST iniciar colapsado por padrão, com o título indicando a quantidade de itens (ex.: "⚠️ Figurinos solicitados/faltantes (3 itens)").
- **FR-008**: O SUPERADMIN MUST poder excluir/descartar um item da lista de faltantes, removendo-o da visualização sem apagar eventos ou personagens.
- **FR-009**: O SUPERADMIN MUST poder associar um item faltante a uma ficha de figurino já existente, escolhendo-a em uma lista/dropdown das fichas cadastradas.
- **FR-010**: Ao associar um item faltante a uma ficha, o sistema MUST atualizar os cargos de evento daquele personagem (nome normalizado) para apontarem para a ficha escolhida, e o item MUST deixar de aparecer na lista de faltantes.
- **FR-011**: Um item descartado MUST deixar de aparecer para o mesmo personagem enquanto nenhum cargo de evento novo for criado com aquele nome depois do descarte; um novo cargo com o mesmo nome, criado após o descarte, MUST voltar a aparecer como faltante.
- **FR-012**: A tela `/figurinos` MUST oferecer um campo de busca por nome de ficha/personagem, filtrando a grade em tempo real (case-insensitive, sem acento).
- **FR-013**: A tela `/figurinos` MUST oferecer um filtro por categoria/tag do figurino; fichas MUST poder ter zero ou mais tags, atribuídas na criação/edição da ficha.
- **FR-014**: Busca por nome e filtro por tag MUST poder ser combinados (interseção dos dois critérios).
- **FR-015**: Nenhuma alteração desta feature MUST modificar as views/templates Jinja legados do módulo de figurino (`app/figurino/routes.py`, `app/templates/figurino_*.html`) — a reestruturação é exclusiva da tela React em `frontend/apps/internal`.

### Key Entities

- **Ficha de Figurino (FigurinoSheet)**: representa o figurino de um personagem — nome, foto, lista de peças, notas, tags/categorias, datas de criação/edição. Já existe; ganha o atributo de tags.
- **Personagem faltante**: nome de personagem usado em cargos de evento que ainda não tem ficha correspondente (calculado, não é uma entidade persistida por si só) — passa a ter um estado de "descartado" opcional.
- **Descarte de alerta faltante**: registro de que um nome de personagem foi descartado da lista de faltantes em determinado momento; deixa de valer se um cargo de evento novo for criado depois com o mesmo nome.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Em telas widescreen, um usuário vê pelo menos 5 fichas por linha sem rolagem horizontal.
- **SC-002**: 100% dos cards com foto mostram o figurino da cabeça aos pés (sem corte da cabeça) para fotos enquadradas em retrato no enquadramento original.
- **SC-003**: Um usuário com permissão consegue abrir a impressão de uma ficha em no máximo 1 clique a partir da grade.
- **SC-004**: Usuários que não são SUPERADMIN nunca veem o painel de figurinos faltantes (0% de vazamento de RBAC).
- **SC-005**: Um SUPERADMIN consegue associar um personagem faltante a uma ficha existente em no máximo 3 cliques (abrir painel → escolher ficha → confirmar).
- **SC-006**: Buscar por um nome parcial reduz a grade ao subconjunto correto em menos de 300ms de digitação (sem chamada de rede adicional).

## Assumptions

- "Fluxo de impressão/geração de PDF da ficha completa" reaproveita a rota de impressão Jinja já existente (`/figurinos/<id>/print`), aberta em nova aba a partir do React — nenhuma nova geração de PDF é criada, e a rota legada não é alterada.
- Tags/categoria de figurino não existem hoje no modelo de dados; esta feature adiciona um campo simples de tags (lista curta de palavras livres, sem taxonomia fixa pré-definida) à ficha, editável no formulário de criação/edição.
- "Excluir" o alerta de faltante é um descarte reversível pelo sistema (reaparece se um novo cargo de evento com o mesmo nome for criado depois), não uma exclusão permanente de dado histórico.
- Endpoints novos de API (para tags, descarte de alerta e associação de ficha) seguem o padrão arquitetural já usado no repositório (`app/api/figurino_*.py` chamando `app/figurino/figurino_ops.py`) — são adições, não alterações do código Jinja legado, e por isso são consistentes com a regra de manter o trabalho desta feature no lado React/API novo do sistema.
- RBAC de edição (FIGURINO/SUPERADMIN) e de SUPERADMIN já é obtido do usuário autenticado atual (`useCurrentUser()`), sem necessidade de novos papéis.
- Mobile não é o foco desta feature (uso interno majoritariamente em desktop), mas a grade deve degradar de forma razoável em telas estreitas (sem quebrar).
