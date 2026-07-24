# Feature Specification: Revisão de Mídia estilo Vimeo

**Feature Branch**: `182-revisao-midia-vimeo`

**Created**: 2026-07-24

**Status**: Draft

**Input**: User description: "Transformar o módulo de Revisão de Mídia/Vídeos (/revisao/[id]) em uma ferramenta moderna e de altíssima performance, inspirada no fluxo de revisão de vídeos do Vimeo: layout imersivo widescreen de 2 colunas, player interativo com scrubber marcado por comentários, comentários indexados por timestamp com resolução, gestão de versões e fluxo de aprovação com status persistente. Escopo restrito a `frontend/apps/internal` + backend mínimo aditivo necessário; Jinja legado intacto."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Assistir e navegar o vídeo com precisão (Priority: P1)

Um revisor (ex.: diretor de arte, equipe comercial) abre um material em vídeo dentro de um espaço de revisão e precisa avaliar o conteúdo com controle fino: pausar/retomar rapidamente, avançar/voltar poucos segundos para comparar cortes, mudar a velocidade de reprodução para revisar detalhes devagar ou passar rápido por trechos já aprovados, e sempre saber em que ponto do vídeo está.

**Why this priority**: É a base de qualquer revisão de vídeo — sem um player preciso e responsivo, nenhuma outra melhoria (comentários por timestamp, versões) tem o mesmo valor. Entrega valor sozinho mesmo antes das outras stories existirem.

**Independent Test**: Abrir um material de vídeo existente e verificar que dá para pausar/retomar com a barra de espaço, saltar 5s com as setas, trocar a velocidade e ver o tempo atual/total formatado — sem depender de nenhuma mudança em comentários, layout ou versões.

**Acceptance Scenarios**:

1. **Given** um material de vídeo aberto, **When** o usuário pressiona a barra de espaço (fora de um campo de texto), **Then** o vídeo alterna entre reproduzir e pausar.
2. **Given** um vídeo em reprodução, **When** o usuário pressiona a seta direita/esquerda, **Then** o vídeo avança/retrocede 5 segundos, mantendo o estado de play/pause.
3. **Given** o cursor dentro do campo de comentário, **When** o usuário pressiona espaço ou as setas, **Then** o atalho NÃO afeta o player (o texto é digitado normalmente).
4. **Given** um vídeo aberto, **When** o usuário escolhe uma velocidade (0.5x/1x/1.5x/2x), **Then** a reprodução passa a ocorrer nessa velocidade e a escolha fica visível nos controles.
5. **Given** um vídeo em qualquer ponto, **Then** o tempo atual e a duração total aparecem formatados como `MM:SS / MM:SS`, atualizando continuamente durante a reprodução.

---

### User Story 2 - Comentar e resolver feedback ancorado no tempo exato (Priority: P2)

Um revisor identifica um ponto específico do vídeo que precisa de ajuste, escreve um comentário e ele fica automaticamente vinculado ao segundo exato do vídeo. Mais tarde, qualquer pessoa com acesso ao espaço revisita os comentários, clica em um deles para pular direto para o momento comentado, e marca como resolvido quando o ajuste for feito. É possível filtrar para ver só o que ainda está pendente.

**Why this priority**: É o núcleo funcional da "revisão" em si — sem isso o player é só um tocador de vídeo. Depende do player da US1 mas é testável de forma isolada (a captura de timestamp e o feed já existem parcialmente no sistema hoje).

**Independent Test**: Com o player da US1 funcionando, escrever um comentário, confirmar que ele é salvo com o timestamp correto, clicar nele no feed e confirmar que o player pula para aquele ponto; marcar/desmarcar como resolvido e alternar o filtro "Todos"/"Pendentes".

**Acceptance Scenarios**:

1. **Given** um vídeo em reprodução, **When** o usuário foca o campo de novo comentário, **Then** o vídeo pausa automaticamente e o timestamp atual (ex.: `@ 01:24`) aparece marcado perto do campo.
2. **Given** um timestamp capturado, **When** o usuário escreve o texto e envia, **Then** o comentário é salvo vinculado exatamente àquele segundo e aparece no feed.
3. **Given** o feed de comentários de uma versão, **Then** os itens aparecem ordenados cronologicamente pelo tempo do vídeo (não pela ordem de criação).
4. **Given** um comentário no feed, **When** o usuário clica nele (ou no seu timestamp), **Then** o player salta (seek) instantaneamente para aquele segundo exato.
5. **Given** um comentário pendente, **When** quem tem permissão marca "Resolvido", **Then** o comentário passa a exibir esse estado (e pode ser reaberto), preservando quem resolveu e quando.
6. **Given** o feed de comentários, **When** o usuário alterna o filtro para "Apenas pendentes", **Then** só os comentários não resolvidos aparecem; alternar de volta para "Todos" mostra todos novamente.

---

### User Story 3 - Revisar em layout imersivo widescreen (Priority: P3)

Ao abrir um material em uma tela larga, o revisor vê o player ocupando a maior parte da tela (coluna principal) com o histórico de versões, status e comentários organizados numa coluna lateral sempre visível — sem precisar rolar a página para alternar entre assistir e ler/escrever comentários. Em telas estreitas (celular), o conteúdo se reorganiza em uma coluna só, com o player no topo.

**Why this priority**: É uma melhoria de organização visual sobre as duas stories anteriores — só faz sentido (e só é testável de forma significativa) depois que player e comentários já existem no novo formato, mas é uma mudança independente de reestruturação de layout.

**Independent Test**: Abrir a tela de um material em viewport largo (≥1280px) e confirmar visualmente a divisão em duas colunas (player ~70% à esquerda, painel ~30% à direita); redimensionar para viewport mobile e confirmar que o conteúdo empilha em uma coluna com o player no topo.

**Acceptance Scenarios**:

1. **Given** a tela de um material aberta em viewport widescreen, **Then** o player e a timeline ocupam a coluna esquerda (~70% da largura) e o painel de versões/status/comentários ocupa a coluna direita (~30%).
2. **Given** a mesma tela em viewport mobile, **Then** o layout empilha em uma única coluna, com o player sempre visível no topo antes do painel de comentários.
3. **Given** qualquer viewport, **Then** nenhuma ação de revisão (assistir, comentar, trocar versão, aprovar) fica inacessível ou cortada da tela.

---

### User Story 4 - Gerenciar versões e aprovar com um clique (Priority: P4)

Quem gerencia o espaço de revisão precisa comparar diferentes versões de um mesmo material ao longo do tempo e sinalizar formalmente o status de aprovação daquela versão (em revisão, aprovado, precisa de ajustes, rejeitado) para que toda a equipe saiba o estado atual sem precisar perguntar. Trocar de versão para reavaliar comentários antigos deve ser rápido, e alterar o status deve ser uma ação de um clique.

**Why this priority**: Depende conceitualmente das stories anteriores (é avaliado dentro do mesmo player/layout) e introduz uma capacidade nova de dados (status persistente) — por isso vem por último, mas fecha o ciclo completo de aprovação que a spec pede.

**Independent Test**: Com duas versões de um material existentes, alternar entre elas por um seletor no cabeçalho e confirmar que os comentários exibidos mudam para os da versão selecionada; como usuário com permissão de gerenciar o espaço, trocar o status do material entre os 4 valores e confirmar que o badge no cabeçalho reflete a mudança após recarregar a página.

**Acceptance Scenarios**:

1. **Given** um material com múltiplas versões, **When** o usuário abre o seletor de versões no cabeçalho, **Then** vê todas as versões (ex.: `v1 (20/07)`, `v2 (23/07)`) e pode escolher qualquer uma para visualizar (somente leitura para versões antigas, como hoje).
2. **Given** um material recém-criado, **Then** seu status inicial é "Em Revisão".
3. **Given** um usuário com permissão de gerenciar o espaço (criador do espaço ou super admin), **When** ele escolhe um novo status (Aprovado / Precisa de Ajustes / Rejeitado / Em Revisão), **Then** o badge do cabeçalho atualiza imediatamente e o valor persiste (visível para todos os revisores após recarregar).
4. **Given** um usuário sem permissão de gerenciar o espaço, **Then** ele vê o badge de status mas não vê os controles para alterá-lo.
5. **Given** um material com status "Aprovado" (ou outro), **When** uma nova versão do arquivo é enviada (substituição), **Then** o status volta automaticamente para "Em Revisão".

---

### Edge Cases

- Material sem nenhum comentário na versão atual: a timeline não mostra marcadores e o feed mostra o estado vazio já existente ("Nenhum comentário nesta versão"), sem quebrar o restante da tela.
- Dois comentários no mesmo segundo exato: ambos aparecem no feed, ordenados de forma estável (ex.: por ordem de criação como critério de desempate).
- Usuário troca de versão (seletor) enquanto o vídeo está tocando: a reprodução para e o player recarrega a mídia da versão selecionada, mantendo os controles funcionais.
- Vídeo ainda carregando/buffering quando o usuário tenta usar atalhos de teclado: os atalhos não devem gerar erro, apenas não ter efeito até o player estar pronto.
- Comentário criado a poucos milissegundos do fim do vídeo: o marcador na timeline aparece próximo ao fim, sem sair da área visível da barra.
- Tentativa de alterar status por alguém sem permissão via chamada direta à API (não só escondendo o botão na UI): deve ser rejeitada pelo backend com erro de permissão, mesma regra de `can_manage`.
- Material finalizado (arquivo removido do armazenamento, feature 090/104 já existente): o player deve mostrar o estado "arquivo não disponível" já existente, sem tentar montar scrubber/marcadores sobre uma mídia inexistente; status e comentários continuam visíveis normalmente.
- Materiais que não são vídeo (áudio, imagem, PDF): continuam com o tratamento atual de comentário (timecode para áudio, página para PDF, ponto x/y para imagem) dentro do novo layout de 2 colunas — o scrubber com marcadores e os atalhos de teclado de vídeo não se aplicam a eles.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O sistema DEVE exibir, para materiais de vídeo, um player com barra de progresso (scrubber) clicável/arrastável que mostra marcadores visuais nos segundos exatos onde existem comentários da versão atualmente exibida.
- **FR-002**: O sistema DEVE permitir alternar a velocidade de reprodução entre 0.5x, 1x, 1.5x e 2x, com a velocidade atual visível no player.
- **FR-003**: O sistema DEVE responder aos atalhos de teclado Espaço (play/pause) e Setas Esquerda/Direita (retroceder/avançar 5 segundos) sempre que o foco não estiver em um campo de texto/textarea da página.
- **FR-004**: O sistema DEVE exibir o tempo atual e a duração total do vídeo no formato `MM:SS / MM:SS`, atualizado continuamente durante a reprodução.
- **FR-005**: Ao focar o campo de novo comentário em um material de vídeo, o sistema DEVE pausar a reprodução automaticamente e capturar/exibir o timestamp atual do player antes do envio.
- **FR-006**: O sistema DEVE permitir enviar um comentário vinculado exatamente ao timestamp capturado, reutilizando o comportamento de criação de comentário já existente (mesma validação de versão atual).
- **FR-007**: O sistema DEVE listar os comentários da versão em exibição ordenados cronologicamente pelo tempo do vídeo (timestamp), não pela ordem de criação.
- **FR-008**: O sistema DEVE fazer o player saltar (seek) para o segundo exato de um comentário quando o usuário clicar nesse comentário ou em seu timestamp no feed.
- **FR-009**: O sistema DEVE permitir marcar/desmarcar um comentário como resolvido (reaproveitando a regra de permissão já existente), e permitir filtrar o feed entre "Todos os comentários" e "Apenas pendentes".
- **FR-010**: O sistema DEVE apresentar, em telas largas (widescreen), um layout de duas colunas: player/timeline/controles à esquerda (~70% da largura) e histórico de versões + status + feed de comentários à direita (~30%).
- **FR-011**: Em telas estreitas (mobile), o sistema DEVE reorganizar o mesmo conteúdo em uma única coluna, com o player sempre no topo.
- **FR-012**: O sistema DEVE oferecer um seletor de versões no cabeçalho da tela (não apenas uma lista simples) para alternar entre as versões existentes de um material, mantendo o comportamento atual de versões antigas serem somente leitura.
- **FR-013**: O sistema DEVE persistir um status de aprovação por material, com os valores possíveis: "Em Revisão" (padrão ao criar), "Aprovado", "Precisa de Ajustes" e "Rejeitado".
- **FR-014**: O sistema DEVE exibir o status atual como um badge visível no cabeçalho da tela do material, para qualquer pessoa com acesso de visualização ao espaço.
- **FR-015**: O sistema DEVE permitir que apenas usuários com permissão de gerenciar o espaço (mesma regra já usada para excluir/substituir material) alterem o status, com uma ação de um clique por valor de status.
- **FR-016**: O sistema DEVE rejeitar, no backend, qualquer tentativa de alterar o status por um usuário sem permissão de gerenciar o espaço, independentemente do que a interface exibir.
- **FR-017**: Ao substituir o arquivo de um material por uma nova versão, o sistema DEVE redefinir o status desse material para "Em Revisão".
- **FR-018**: O sistema DEVE manter, sem regressão, o comportamento atual de comentário por página (PDF), por ponto x/y (imagem) e por timecode (áudio) — os itens 1–2 desta lista (scrubber com marcadores, atalhos de teclado) aplicam-se apenas a materiais de vídeo.
- **FR-019**: O sistema NÃO DEVE alterar o comportamento das views Jinja legadas do módulo de revisão (`app/revisao/routes.py`) nem das telas de `frontend/apps/public` ou `frontend/apps/portal`.

### Key Entities

- **Material de revisão (ReviewAsset)**: já existente; passa a ter um status de aprovação persistente (Em Revisão / Aprovado / Precisa de Ajustes / Rejeitado), redefinido para "Em Revisão" a cada nova versão enviada.
- **Comentário (ReviewComment)**: já existente; usado como fonte dos marcadores na timeline do vídeo (timestamp) e do agrupamento pendente/resolvido no feed — sem mudança de estrutura, só de apresentação/ordenação.
- **Versão do material (ReviewAssetVersion)**: já existente (histórico); passa a ser navegável por um seletor no cabeçalho em vez de uma lista simples.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Um revisor consegue localizar e assistir o trecho comentado de um vídeo em menos de 2 segundos a partir do clique no comentário (sem precisar arrastar a barra manualmente).
- **SC-002**: Em telas widescreen, 100% das ações de revisão (assistir, comentar, trocar versão, aprovar) ficam visíveis sem rolagem vertical dentro de cada coluna, para vídeos de duração típica.
- **SC-003**: Toda a equipe envolvida em um espaço de revisão consegue identificar o status atual de aprovação de um material olhando só para o badge do cabeçalho, sem precisar perguntar a outra pessoa.
- **SC-004**: Trocar o status de um material leva uma única ação (clique) para quem tem permissão, sem etapas de confirmação adicionais.
- **SC-005**: A tela de revisão de um material permanece totalmente utilizável (nenhum controle cortado ou sobreposto) tanto em desktop widescreen quanto em viewport mobile.

## Assumptions

- O RBAC de quem pode alterar o status reaproveita exatamente a regra existente de "gerenciar o espaço" (`can_manage`: criador do espaço ou super admin) — não é criado um papel novo de "direção/comercial".
- O escopo de scrubber com marcadores, controles de velocidade e atalhos de teclado é específico de `media_type == "video"`; áudio, imagem e PDF continuam com o fluxo de comentário atual, apenas dentro do novo layout de 2 colunas.
- "Altíssima performance" é interpretado como responsividade de interação (seek, play/pause, troca de versão sem recarregar a página inteira) — não implica em reencode/streaming adaptativo do arquivo de vídeo, que está fora de escopo.
- Notificações, exportação de comentários em PDF, transcrição/legendas automáticas e waveform de áudio estão fora de escopo desta feature.
- O arquivo de vídeo continua sendo servido pela mesma URL/mecanismo atual (`assetUrl`/Flask storage) — não há mudança de infraestrutura de armazenamento ou streaming.
