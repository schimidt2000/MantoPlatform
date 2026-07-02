# Feature Specification: Revisão de Vídeo Profissional Mobile-First

**Feature Branch**: `104-revisao-video-mobile`

**Created**: 2026-07-02

**Status**: Draft

**Input**: User description: "Preciso melhorar e deixar mais profissional a parte de revisão. Funcionando muito espelhado em como o Vimeo funciona e parando para pensar que a maioria das vezes os vídeos serão revisados pelo celular. Ou seja, precisa pensar em uma forma que funcione bem no celular. Tenha design condizente com o sistema. Os comentários feitos pelos revisores devem ficar visíveis para todos envolvidos, para evitar comentários de ideias concorrentes. A Erika ao concluir um comentário, não o exclui, apenas o deixa marcado como concluído. Assim os revisores podem ver o que foi feito. Deve ser possível ver um histórico de versões também. Construa isso de forma elegante e funcional."

## Contexto

A plataforma já possui um espaço de revisão de mídia (features 088/090): espaços com materiais
(vídeo/áudio/imagem/PDF), revisores selecionados, comentários ancorados em time code, e
substituição de arquivo com contador de versão. Esta feature **evolui** esse módulo em três
frentes: (1) experiência mobile-first profissional estilo Vimeo Review, (2) fluxo de conclusão
de comentários transparente (concluir ≠ excluir, com autoria e data da conclusão visíveis a
todos), e (3) histórico de versões navegável — hoje substituir um arquivo apaga o anterior e
só incrementa um número, sem histórico consultável.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Revisar vídeo pelo celular com experiência profissional (Priority: P1)

Um revisor (diretor, cliente interno, equipe de marketing) recebe o link de um material e abre
no celular. O vídeo ocupa o topo da tela, com player funcional em tela pequena. Abaixo, a lista
de comentários da equipe, cada um com o time code clicável. O revisor pausa o vídeo no ponto
desejado, toca em "Comentar", escreve e envia — o comentário fica ancorado naquele instante.
Tocar no time code de qualquer comentário leva o player àquele momento exato.

**Why this priority**: É o cenário dominante de uso real ("a maioria das vezes os vídeos serão
revisados pelo celular") e hoje a tela foi desenhada para desktop (coluna lateral de 360px,
alvos de toque pequenos, campo de comentário distante do player). Sem isso, a revisão continua
sendo feita fora da plataforma.

**Independent Test**: Abrir um material de vídeo num viewport mobile (≤ 480px), reproduzir,
pausar, comentar ancorado no tempo, e navegar pelos comentários existentes tocando nos time
codes — tudo sem zoom, sem scroll horizontal e sem perder o player de vista.

**Acceptance Scenarios**:

1. **Given** um material de vídeo aberto em tela de celular, **When** a página carrega,
   **Then** o player aparece no topo em largura total, a lista de comentários logo abaixo, e a
   ação de comentar fica sempre acessível (fixa) sem precisar rolar até o fim da página.
2. **Given** o vídeo pausado em 0:42, **When** o revisor escreve um comentário e envia,
   **Then** o comentário aparece na lista com a âncora "0:42" e um marcador surge na barra de
   progresso/timeline de comentários naquela posição.
3. **Given** uma lista com comentários de vários revisores, **When** qualquer envolvido toca no
   time code de um comentário, **Then** o player salta para aquele instante.
4. **Given** a mesma tela aberta em desktop, **When** a página carrega, **Then** o layout usa o
   espaço maior (player + painel lateral de comentários) mantendo as mesmas funções.
5. **Given** qualquer tela do módulo de revisão, **When** comparada ao restante do sistema,
   **Then** usa a mesma paleta, tipografia e componentes (botões, painéis, badges) do design
   system existente.

---

### User Story 2 - Concluir comentários sem excluí-los (Priority: P2)

A Erika (editora, criadora do espaço) trabalha nos ajustes pedidos. Ao atender um comentário,
ela o marca como **concluído** — o comentário não some: fica visível para todos, com indicação
visual de concluído, mostrando **quem** concluiu e **quando**. Os revisores acompanham o que já
foi feito e o que está pendente. Comentários concluídos ficam agrupados/recolhidos para não
poluir a lista de pendências, mas sempre consultáveis. A exclusão de comentários deixa de fazer
parte do fluxo normal (reservada ao autor do comentário para casos de erro, e ao super admin).

**Why this priority**: É a mudança de processo central pedida — transparência do que foi
atendido evita retrabalho e "ideias concorrentes" entre revisores. Depende só da tela de
revisão existir (US1).

**Independent Test**: Com dois usuários (criador e revisor), criar comentários, concluir um
deles como criador e verificar que o revisor vê o comentário marcado como concluído com autor
e data da conclusão, separado dos pendentes.

**Acceptance Scenarios**:

1. **Given** um comentário pendente, **When** a Erika o marca como concluído, **Then** o
   comentário permanece visível para todos os envolvidos com estado "concluído", nome de quem
   concluiu e data/hora.
2. **Given** um comentário concluído, **When** qualquer envolvido visualiza a lista, **Then**
   consegue distinguir imediatamente pendentes de concluídos (contadores e agrupamento), com os
   concluídos recolhidos por padrão mas expansíveis.
3. **Given** um comentário concluído por engano, **When** quem pode concluir o reabre, **Then**
   ele volta ao estado pendente e o registro de conclusão anterior é limpo.
4. **Given** um revisor que não é o autor de um comentário nem criador do espaço, **When**
   visualiza o comentário, **Then** não vê ação de excluir (apenas o autor do comentário e o
   super admin podem excluir).

---

### User Story 3 - Histórico de versões navegável (Priority: P3)

A Erika sobe o corte v2 do vídeo após atender os comentários da v1. O material passa a mostrar
"Versão 2" com acesso ao histórico: lista de todas as versões com data de envio, quem enviou e
os comentários daquela versão. Os revisores comentam sempre sobre a versão atual; ao abrir uma
versão anterior, veem os comentários feitos naquela versão (contexto do que foi pedido), com
indicação clara de que estão vendo uma versão antiga. Arquivos de versões antigas continuam
sujeitos à política de expiração (7 dias) — quando expiram, a entrada do histórico permanece
com data, autor e comentários, apenas sem o arquivo reproduzível.

**Why this priority**: Completa o ciclo profissional de revisão (rastreabilidade), mas o fluxo
de revisão funciona sem ele — hoje já existe substituição com contador de versão.

**Independent Test**: Substituir o arquivo de um material duas vezes e verificar que o
histórico lista 3 versões com datas/autor, que os comentários ficaram associados às versões em
que foram feitos e que é possível abrir uma versão anterior não expirada.

**Acceptance Scenarios**:

1. **Given** um material na versão 1 com comentários, **When** a Erika envia uma nova versão,
   **Then** o material passa a exibir a versão 2 como atual e o histórico mostra a versão 1 com
   data, autor do envio e seus comentários.
2. **Given** um material com 3 versões, **When** um revisor abre o histórico e seleciona a
   versão 2 (não expirada), **Then** vê o arquivo da versão 2 com os comentários daquela versão
   e um aviso claro de que não é a versão atual, sem possibilidade de comentar nela.
3. **Given** uma versão antiga cujo arquivo expirou, **When** aberta pelo histórico, **Then**
   mostra os metadados (data, autor, nº da versão) e os comentários, com aviso de arquivo
   expirado no lugar do player.
4. **Given** um novo comentário criado, **When** salvo, **Then** fica associado à versão que
   estava sendo exibida como atual naquele momento.

---

### Edge Cases

- Vídeo ainda carregando metadados (duração desconhecida): a timeline de marcadores só é
  desenhada quando a duração estiver disponível; comentar continua possível.
- Comentário enviado com o vídeo em reprodução: a âncora usa o instante corrente no momento em
  que o campo de comentário foi aberto/focado, evitando que o tempo "escorra" enquanto se digita.
- Teclado virtual aberto no celular: o campo de comentário permanece visível (não coberto pelo
  teclado) e o envio não exige rolar a página.
- Dois revisores comentam quase ao mesmo tempo: ambos os comentários aparecem para todos ao
  recarregar a lista (a lista é atualizada após cada envio; sem exigência de tempo real).
- Material de imagem/PDF/áudio: mantêm as âncoras atuais (ponto, página, time code) e recebem o
  mesmo layout mobile e o mesmo fluxo de conclusão/histórico de versões.
- Substituição de arquivo com tipo de mídia diferente do original: continua bloqueada (regra
  existente da feature 090).
- Espaço com material finalizado (arquivo removido): histórico e comentários continuam
  consultáveis; nenhuma versão pode ser reproduzida.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: A tela de revisão de material DEVE ser mobile-first: em telas pequenas, player em
  largura total no topo, comentários abaixo, ação de comentar sempre acessível sem rolagem até o
  fim; em telas grandes, layout de duas colunas (player + painel de comentários).
- **FR-002**: Todos os alvos de toque da tela de revisão (botões, time codes, marcadores)
  DEVEM ser confortáveis para uso com o polegar (área mínima de toque adequada a mobile).
- **FR-003**: O design DEVE reutilizar a identidade visual do sistema (variáveis de cor,
  tipografia, componentes de painel/botão/badge existentes), sem cores hardcoded novas.
- **FR-004**: Comentários em vídeo/áudio DEVEM ser ancorados ao instante em que o usuário
  iniciou o comentário (captura do tempo ao focar o campo), com time code exibido e clicável
  para navegar o player.
- **FR-005**: O player de vídeo DEVE exibir uma linha do tempo de comentários (marcadores nas
  posições dos time codes) utilizável também em telas pequenas.
- **FR-006**: Todos os comentários DEVEM ser visíveis a todos os envolvidos do espaço (criador,
  revisores, super admin) — sem comentários privados.
- **FR-007**: Concluir um comentário DEVE registrar quem concluiu e quando, e exibir essas
  informações a todos; o comentário concluído permanece visível.
- **FR-008**: A lista de comentários DEVE separar pendentes de concluídos, com contadores
  (ex.: "3 pendentes · 5 concluídos") e concluídos recolhidos por padrão.
- **FR-009**: Reabrir um comentário concluído DEVE ser possível (volta a pendente e limpa o
  registro de conclusão).
- **FR-010**: A conclusão/reabertura de comentários DEVE ser permitida ao criador do espaço e
  ao super admin; o autor do comentário TAMBÉM pode concluir/reabrir o próprio comentário.
- **FR-011**: Excluir comentário DEVE ficar restrito ao autor do comentário e ao super admin,
  fora do fluxo principal (ação secundária com confirmação).
- **FR-012**: Substituir o arquivo de um material DEVE preservar a versão anterior como entrada
  de histórico (número da versão, data de envio, autor do envio, arquivo e comentários da época).
- **FR-013**: Cada comentário DEVE ficar associado à versão do material vigente no momento em
  que foi criado; a tela da versão atual mostra apenas os comentários da versão atual.
- **FR-014**: O usuário DEVE poder abrir o histórico de versões e visualizar qualquer versão
  anterior (arquivo, se não expirado, e seus comentários), com aviso claro de versão antiga e
  sem permitir novos comentários em versões antigas.
- **FR-015**: Arquivos de versões antigas DEVEM seguir a política de expiração existente
  (7 dias a partir do envio daquela versão); após expirar, a entrada do histórico permanece com
  metadados e comentários.
- **FR-016**: Toda ação assíncrona da tela (comentar, concluir, reabrir, excluir) DEVE ter
  feedback visual imediato (estado de carregando, sucesso ou mensagem de erro amigável).
- **FR-017**: Materiais existentes (criados antes desta feature) DEVEM continuar funcionando:
  comentários atuais tratados como da versão vigente, sem perda de dados.

### Key Entities

- **Material (ReviewAsset — existente)**: passa a apontar para uma versão atual; mantém tipo de
  mídia, posição, estado de finalização/expiração.
- **Versão de Material (nova)**: registro histórico de cada arquivo enviado — número
  sequencial, arquivo, nome original, autor do envio, data de envio, data de expiração do
  arquivo, indicador de arquivo removido. Um material tem 1..N versões; uma é a atual.
- **Comentário (ReviewComment — existente, estendido)**: ganha vínculo com a versão em que foi
  criado e registro de conclusão (quem concluiu, quando).
- **Espaço de Revisão / Revisores (existentes)**: inalterados — continuam controlando acesso.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Um revisor consegue, no celular, abrir um vídeo, comentar ancorado no tempo e
  enviar em menos de 30 segundos, sem zoom nem scroll horizontal.
- **SC-002**: 100% dos comentários exibem autor, momento de criação e âncora (quando houver), e
  comentários concluídos exibem quem concluiu e quando — visíveis a todos os envolvidos.
- **SC-003**: Nenhum comentário é perdido ao substituir arquivo: após criar uma nova versão,
  todos os comentários anteriores permanecem acessíveis pelo histórico da versão correspondente.
- **SC-004**: Qualquer envolvido distingue pendentes de concluídos em até 5 segundos ao abrir a
  tela (contadores visíveis e agrupamento).
- **SC-005**: O histórico de um material com N versões lista as N versões com data e autor, e
  versões não expiradas abrem para visualização.

## Assumptions

- O módulo de revisão existente (features 088/090) é a base: espaços, revisores, tipos de mídia
  e política de expiração de 7 dias permanecem; esta feature melhora a tela do material, o fluxo
  de conclusão e adiciona histórico de versões.
- "Erika" representa o papel de criador do espaço (equipe de marketing/edição); as permissões
  seguem por papel, não por pessoa.
- Comentários já são visíveis a todos os envolvidos hoje; o requisito reforça que isso deve
  continuar valendo (sem comentários privados) e ficar evidente na interface.
- Respostas encadeadas (replies) a comentários NÃO fazem parte do escopo — a organização por
  pendente/concluído com visibilidade total atende ao objetivo de evitar ideias concorrentes.
- Atualização em tempo real (websockets) está fora do escopo: a lista de comentários é
  atualizada ao carregar a página e após cada ação do próprio usuário.
- Versões antigas não aceitam novos comentários (revisão sempre acontece na versão atual),
  espelhando o comportamento do Vimeo Review.
- Não há upload de anexos dentro de comentários nem desenho sobre o vídeo (fora do escopo).
- A capacidade de armazenamento comporta manter arquivos de versões antigas até a expiração
  individual de cada uma (7 dias por versão), pois hoje o arquivo antigo já ocuparia esse espaço
  se não fosse substituído.
