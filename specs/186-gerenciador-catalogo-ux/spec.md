# Feature Specification: Gerenciador de Catálogo — UX e Fluxo Ficha↔Catálogo↔Venda

**Feature Branch**: `186-gerenciador-catalogo-ux`

**Created**: 2026-07-24

**Status**: Draft

**Input**: User description: "Evolução de UI/UX do Gerenciador de Catálogo (apps/internal) e perfeição do fluxo de trabalho entre Ficha de Figurino ↔ Catálogo ↔ Venda (Novo Evento): amarração bidirecional visível, busca visual de personagem no elenco do evento (só Personagens Filhos, com foto em miniatura), painel de associação rápida com indicador 'sem ficha vinculada', alternador de visualização Cards/Árvore no /admin/catalogo, kebab menu nos cards, seleção múltipla com ações em massa (mover/inativar/excluir), seleção de capa e reordenação de fotos mais intuitivas, e correção da rota /catalogo no menu lateral."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Vendedor escala um Personagem visualmente correto no elenco (Priority: P1)

Ao montar o elenco de um Novo Evento, o comercial busca por nome de personagem e vê, junto de
cada sugestão, uma foto em miniatura — só Personagens Filhos aparecem na busca (nunca o Tema
pai, que não é uma atração vendável isoladamente). Isso evita escalar visualmente o produto
errado por confusão de nomes parecidos.

**Why this priority**: É o elo comercial→produção que a feature 185 deixou funcional mas "cego"
(só nome); erro de escalação visual é o risco mais caro (cliente recebe o personagem errado).

**Independent Test**: num evento novo, digitar parte do nome de um Personagem cadastrado no
catálogo e confirmar que o dropdown mostra a foto dele, e que Temas pai não aparecem como opção
selecionável isoladamente.

**Acceptance Scenarios**:

1. **Given** o formulário de Novo Evento, **When** o comercial digita no campo de busca de
   personagem do catálogo, **Then** as sugestões mostram foto em miniatura + nome, e são
   filtradas para conter apenas Personagens Filhos ativos (não Temas).
2. **Given** um Personagem sem foto cadastrada, **When** ele aparece na busca, **Then** um
   placeholder visual substitui a miniatura (sem quebrar o layout da lista).
3. **Given** o comercial seleciona um Personagem na busca, **When** a seleção é aplicada, **Then**
   nome e (se houver) `figurino_sheet_id` são preenchidos na linha do elenco, como já ocorre hoje.

---

### User Story 2 - Staff associa Ficha↔Personagem a partir de qualquer lado, com indicador de pendência (Priority: P1)

O vínculo entre um Personagem do catálogo e sua Ficha de Figurino pode ser criado tanto editando
o Personagem (já existe) quanto editando a Ficha de Figurino (novo). Nas listagens de ambos os
lados, itens sem vínculo mostram um indicador visual claro, e podem ser vinculados em 2 cliques
sem abrir a tela de edição completa — importante porque existe um acervo grande de fichas e
produtos antigos sem essa associação.

**Why this priority**: Sem isso, o time precisa abrir dezenas de telas de edição uma a uma para
zerar o backlog de vínculos pendentes — trabalho manual que a spec pede para eliminar.

**Independent Test**: abrir a ficha de um personagem sem vínculo, associá-la a um Personagem do
catálogo pelo campo novo, e confirmar que o Personagem no catálogo passa a mostrar essa mesma
ficha vinculada (e vice-versa, associando pelo lado do catálogo primeiro).

**Acceptance Scenarios**:

1. **Given** a tela de edição de uma Ficha de Figurino sem vínculo, **When** o staff usa o campo
   "Vincular a um Personagem do Catálogo" e escolhe um Personagem, **Then** o vínculo é salvo e
   passa a valer nos dois sentidos (o Personagem no catálogo mostra essa ficha).
2. **Given** um Personagem do catálogo já vinculado a uma Ficha, **When** o staff tenta vinculá-lo
   a partir da tela da Ficha a uma ficha diferente, **Then** o vínculo antigo é substituído pelo
   novo (um Personagem só aponta para uma Ficha por vez — não duplica).
3. **Given** a lista/árvore do catálogo e a lista de fichas de figurino, **When** um item não tem
   vínculo, **Then** um indicador visual "Sem ficha vinculada" (catálogo) / "Sem personagem
   vinculado" (figurino) aparece na linha, com um botão `+ Vincular Ficha` (ou equivalente) que
   associa em até 2 cliques sem navegar para a tela de edição completa.

---

### User Story 3 - Staff alterna entre Cards e Árvore Hierárquica para gerenciar Temas e Personagens (Priority: P1)

Na tela `/admin/catalogo`, um seletor no topo alterna entre o modo Cards (visual, uma grade de
capas) e o modo Árvore (lista hierárquica expansível: cada Tema pode ser expandido para revelar
seus Personagens filhos recuados, com guia visual de hierarquia). O modo Árvore é o mais eficiente
para navegar o vínculo Tema→Personagens de um catálogo com muitos itens.

**Why this priority**: A estrutura Tema/Personagem (feature 185) não tem hoje nenhuma visão que
mostre a hierarquia de forma navegável — a única forma de ver os Personagens de um Tema é abrir a
edição dele um por um.

**Independent Test**: alternar para o modo Árvore, expandir um Tema com Personagens cadastrados e
confirmar que aparecem recuados com foto, nome e status do vínculo de figurino; recolher e
confirmar que somem da visão sem apagar dado nenhum.

**Acceptance Scenarios**:

1. **Given** `/admin/catalogo`, **When** o staff alterna para o modo Árvore, **Then** cada Tema
   aparece com foto, nome, contagem de Personagens filhos e um controle de expandir/recolher.
2. **Given** um Tema expandido no modo Árvore, **When** ele tem Personagens filhos, **Then** cada
   um aparece recuado abaixo do pai com linha guia vertical, foto em miniatura, nome, status do
   vínculo de figurino e ações rápidas (editar, vincular ficha).
3. **Given** o modo selecionado (Cards ou Árvore), **When** o staff sai e volta à tela, **Then** o
   último modo escolhido é lembrado (preferência persiste na sessão do navegador).

---

### User Story 4 - Staff limpa o menu de ações do card e faz seleção múltipla (Priority: P2)

No modo Cards, as ações "Inativar" e "Excluir" saem do corpo visível do card e vão para um menu
discreto (kebab, `⋮`) no canto do card — o card fica mais limpo. Além disso, cada item (Tema ou,
na Árvore, também Personagem) tem uma caixa de seleção; ao marcar 1 ou mais, uma barra flutuante
de ações em massa aparece, permitindo mover os selecionados para debaixo de um novo Tema pai,
inativar ou excluir todos de uma vez.

**Why this priority**: Ganho de produtividade sobre o fluxo já funcional da US3 — não bloqueia o
uso básico do gerenciador, mas é necessário para arrumar rapidamente um acervo antigo desorganizado.

**Independent Test**: selecionar 3 produtos no modo Cards, usar a barra de ações em massa para
inativá-los de uma vez, e confirmar que os 3 mudam de estado sem precisar abrir cada um.

**Acceptance Scenarios**:

1. **Given** um card no modo Cards, **When** o staff olha o card, **Then** não há botões
   "Inativar"/"Excluir" soltos no corpo — essas ações estão dentro de um menu kebab (`⋮`) no
   canto, junto de "Editar" e "Realocar/Mover".
2. **Given** 1 ou mais itens selecionados via checkbox, **When** a seleção muda de 0 para 1,
   **Then** uma barra flutuante de ações em massa aparece com as opções Mover, Inativar e Excluir
   selecionados; ao voltar a 0 selecionados, a barra some.
3. **Given** vários itens selecionados, **When** o staff escolhe "Mover/Tornar filhos de…" e
   confirma um Tema pai num modal, **Then** todos os itens selecionados passam a ser Personagens
   filhos daquele Tema (com o mesmo cuidado de unicidade de slug já existente).
4. **Given** vários itens selecionados, **When** o staff escolhe "Excluir selecionados" e confirma,
   **Then** todos são excluídos definitivamente numa única confirmação (não uma por item).

---

### User Story 5 - Staff define capa e reordena fotos sem fricção (Priority: P2)

Na edição de um Tema, a foto atualmente definida como capa exibe um selo "⭐ Capa" visível na
galeria; para trocar, basta um clique em "Definir como capa" em qualquer outra foto — sem precisar
usar um seletor de rádio escondido. A ordem das fotos pode ser ajustada arrastando ou pelos
botões de seta já existentes.

**Why this priority**: Melhoria de usabilidade sobre um fluxo que já funciona (feature 139/141) —
não bloqueia nada, mas reduz erro de capa errada indo para o Open Graph/WhatsApp.

**Independent Test**: numa edição de Tema com 3 fotos, clicar em "Definir como capa" numa foto que
não é a atual e confirmar que o selo "⭐ Capa" migra visualmente para ela, sem perder a ordem das
outras.

**Acceptance Scenarios**:

1. **Given** a galeria de fotos na edição de um Tema, **When** o staff olha a foto que é capa
   hoje, **Then** ela exibe um selo "⭐ Capa" visível, sem precisar procurar um rádio button.
2. **Given** qualquer outra foto que não é a capa, **When** o staff clica em "Definir como capa",
   **Then** ela vira a capa imediatamente (visualmente, antes mesmo de salvar) e o selo migra.
3. **Given** a lista de fotos, **When** o staff arrasta uma foto para outra posição (ou usa as
   setas já existentes), **Then** a nova ordem é refletida visualmente antes de salvar.

---

### User Story 6 - Link "Catálogo" no menu lateral abre a vitrine pública de verdade (Priority: P2)

Ao clicar em "Catálogo" no menu lateral do painel interno, uma nova aba abre corretamente na
vitrine pública (não faz loop nem volta para a página anterior).

**Why this priority**: Bug de navegação reportado pelo usuário — a causa raiz é uma lacuna de
deploy (não existe hoje nenhum serviço publicando o app público em produção; ver Assumptions),
não um link com URL errada em si.

**Independent Test**: em produção (ou ambiente equivalente com os dois apps servidos juntos),
clicar em "Catálogo" no menu e confirmar que a vitrine pública abre na nova aba, navegável, sem
redirecionar de volta.

**Acceptance Scenarios**:

1. **Given** o painel interno logado, **When** o staff clica em "Catálogo" no menu lateral,
   **Then** uma nova aba abre a vitrine pública funcional (grade de produtos carregando).
2. **Given** a vitrine pública aberta a partir desse link, **When** o staff navega para o detalhe
   de um Tema (recarregando a página / deep link direto pela URL), **Then** a página carrega
   normalmente (sem 404 nem redirecionamento para o login do painel interno).

---

### Edge Cases

- Tema com 0 Personagens no modo Árvore: mostra o controle de expandir desabilitado ou oculto (sem
  seta para "nada"), sem quebrar o alinhamento das linhas.
- Ação em massa "Mover para…" incluindo o próprio Tema de destino na seleção: o sistema recusa
  com mensagem clara (um Tema não pode virar filho de si mesmo).
- Ação em massa "Mover" misturando Temas e Personagens já filhos de outro Tema na mesma seleção: um
  Personagem sendo movido perde o vínculo com o Tema antigo e passa a ser filho só do novo.
- Vincular uma Ficha de Figurino a um Personagem que já tem outra Ficha vinculada: o vínculo
  antigo é substituído (Assumption já validada na feature 185 — sem duplicar).
- Busca visual de personagem no elenco do evento sem nenhum resultado: mostra estado vazio claro
  ("nenhum personagem encontrado"), nunca uma lista quebrada.
- Excluir em massa um Tema que tem Personagens filhos não incluídos na mesma seleção: segue a
  mesma regra já validada (cascade — os filhos são excluídos junto), com o modal de confirmação
  deixando isso explícito antes de confirmar.
- Barra de ações em massa com uma ação em andamento (ex.: excluindo) e o staff muda a seleção: a
  ação em andamento continua até o fim antes de aceitar uma nova.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O sistema DEVE permitir vincular uma Ficha de Figurino a um Personagem do catálogo a
  partir da tela de edição da própria Ficha (não só a partir do catálogo).
- **FR-002**: Vincular a partir de qualquer um dos dois lados (Ficha ou Personagem) DEVE produzir
  o mesmo resultado consistente — consultar de qualquer um dos dois lados mostra o vínculo
  atualizado.
- **FR-003**: A busca de personagem para o elenco de um evento DEVE listar exclusivamente
  Personagens Filhos ativos do catálogo — Temas pai NUNCA aparecem como opção selecionável nessa
  busca.
- **FR-004**: Cada sugestão da busca de personagem no elenco do evento DEVE exibir uma foto em
  miniatura do Personagem (ou um placeholder visual quando não há foto) ao lado do nome.
- **FR-005**: As listagens de Personagens do catálogo e de Fichas de Figurino DEVEM exibir um
  indicador visual claro quando o item não tem vínculo do outro lado ("Sem ficha vinculada" /
  "Sem personagem vinculado").
- **FR-006**: Deve existir uma ação rápida de vincular (Ficha↔Personagem) diretamente na
  listagem, sem exigir abrir a tela de edição completa, completável em até 2 interações de clique.
- **FR-007**: `/admin/catalogo` DEVE oferecer um seletor de modo de visualização com pelo menos
  dois modos: Cards (grade visual) e Árvore (lista hierárquica expansível Tema→Personagens).
- **FR-008**: No modo Árvore, cada Tema DEVE exibir foto, nome, contagem de Personagens filhos e
  um controle de expandir/recolher; ao expandir, os Personagens aparecem recuados com indicação
  visual de hierarquia (guia), foto, nome e status do vínculo de figurino.
- **FR-009**: O modo de visualização escolhido (Cards ou Árvore) DEVE persistir entre visitas à
  tela na mesma sessão do navegador.
- **FR-010**: No modo Cards, as ações "Inativar" e "Excluir" NÃO DEVEM aparecer como botões soltos
  no corpo do card — DEVEM estar agrupadas num menu (kebab) por item, junto de "Editar" e
  "Realocar/Mover"; a ação "Excluir" DEVE ser visualmente destacada como destrutiva (ex.: cor de
  alerta) dentro desse menu.
- **FR-011**: Cada item do catálogo (Tema, e Personagem quando visível na Árvore) DEVE ter uma
  caixa de seleção individual.
- **FR-012**: Ao existir 1 ou mais itens selecionados, uma barra de ações em massa DEVE aparecer,
  com pelo menos: mover/realocar para um novo Tema pai, inativar selecionados, excluir
  selecionados — cada ação exige confirmação antes de executar irreversivelmente.
- **FR-013**: A ação de mover em massa DEVE reatribuir todos os itens selecionados como
  Personagens filhos do Tema escolhido num único modal/passo, sem exigir uma operação por item.
- **FR-014**: Na edição de um Tema, a foto que é a capa atual DEVE exibir um indicador visual
  permanente e óbvio (ex.: selo "⭐ Capa"); qualquer outra foto DEVE ter uma ação de 1 clique
  "Definir como capa".
- **FR-015**: A reordenação de fotos na edição de um Tema DEVE ser possível tanto por
  arrastar-e-soltar quanto pelos controles de seta já existentes.
- **FR-016**: O link "Catálogo" do menu lateral do painel interno DEVE abrir a vitrine pública
  navegável (grade e detalhe por deep link) numa nova aba, sem redirecionamento de volta ao login
  ou a outra tela do painel interno.
- **FR-017**: Nenhuma mudança desta feature pode alterar o comportamento visual/funcional já
  entregue na feature 185 (galeria com vídeo, Elenco Individual, chip input de tags) além do que
  está explicitamente descrito aqui.

### Key Entities *(include if feature involves data)*

- **CatalogCharacter (já existe, feature 185)**: nenhuma mudança de schema é necessária — o vínculo
  com `FigurinoSheet` já existe via `figurino_sheet_id`; esta feature só adiciona formas novas de
  criar/visualizar esse mesmo vínculo (nenhuma coluna nova).
- **CatalogItem (já existe)**: nenhuma mudança de schema — "mover em massa" reatribui
  `CatalogCharacter.catalog_item_id`, nunca cria um Tema novo por engano.
- **Preferência de visualização (Cards/Árvore)**: estado de UI local (não persiste no banco) —
  guardado no navegador do usuário.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Um comercial consegue escalar um Personagem certo no elenco de um evento olhando a
  foto da sugestão, sem precisar abrir o catálogo em outra aba para confirmar visualmente.
- **SC-002**: O tempo para vincular uma Ficha a um Personagen a partir de qualquer um dos dois
  lados cai para no máximo 2 cliques a partir da listagem (hoje exige abrir a tela de edição
  completa de um dos dois lados).
- **SC-003**: Um staff consegue inativar ou mover 10 itens do catálogo de uma vez em menos tempo
  do que faria um por um (ação em massa mensuravelmente mais rápida que a soma das ações
  individuais).
- **SC-004**: 100% dos Temas com Personagens ficam navegáveis na visão em Árvore sem precisar
  abrir a tela de edição de cada um só para ver quantos/quais filhos existem.
- **SC-005**: A troca de capa de um Tema é feita sem nenhuma etapa a mais que "clicar na foto
  desejada" — sem menus escondidos.
- **SC-006**: O link "Catálogo" do menu lateral funciona (abre a vitrine, navegável por deep link)
  em 100% dos cliques, sem loop de redirecionamento.

## Assumptions

- **Deploy do app público**: hoje não existe nenhum serviço de produção publicando
  `frontend/apps/public` — `frontend/railway.json`/`nixpacks.toml` só builda/serve
  `frontend/apps/internal`. Decisão tomada com o usuário: os dois apps passam a ser servidos pelo
  MESMO serviço Railway, com o app público sob o prefixo de rota `/catalogo/*` (Vite `base` e
  React Router `basename` condicionais ao build de produção; um pequeno servidor Node substitui o
  `serve` estático simples atual para rotear cada prefixo ao `dist` correto, com fallback de SPA
  próprio por app). Isso é o que resolve a User Story 6 — não é uma mudança de link isolada.
- **RBAC da busca de personagem por foto**: a busca visual de Personagem (US1) e a associação
  rápida a partir da Ficha (US2) reaproveitam/estendem o endpoint de leitura já existente da
  feature 185 (`GET /api/catalogo/elenco-busca`), abrindo o acesso também ao papel `FIGURINO` (hoje
  só `COMERCIAL`/`SUPERADMIN`), já que quem edita fichas de figurino também precisa dessa busca.
- **"Realocar/Mover" individual** (fora do modo de seleção múltipla) é a mesma operação da ação em
  massa, só que aplicada a 1 item — não é um fluxo separado.
- **Modo de visualização padrão**: Cards, por já ser o padrão atual — Árvore é uma opção adicional,
  não substitui o comportamento existente.
- **Sem alteração de RBAC do gerenciador de catálogo em si**: continua restrito a `SUPERADMIN`,
  como já é hoje; só a busca visual de personagem (consumida em telas de Comercial/Figurino) tem
  seu RBAC ampliado, não o CRUD do catálogo.
