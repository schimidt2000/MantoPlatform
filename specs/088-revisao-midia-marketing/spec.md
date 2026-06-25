# Feature Specification: Espaço de Revisão de Mídia (estilo Vimeo Review)

**Feature Branch**: `088-revisao-midia-marketing`

**Created**: 2026-06-25

**Status**: Draft

**Input**: "Ferramenta para a equipe de marketing: um espaço de revisão. Subir um arquivo (ou uma pasta de
arquivos) e escolher quais usuários poderão revisar. Os revisores veem cada material; em vídeo, ao
clicar, podem comentar naquele time code exato (facilitando para a editora). Também subir fotos, áudio e
PDF — tudo seguindo a lógica do Vimeo."

## Contexto

A equipe de marketing precisa revisar materiais (vídeos, fotos, áudios, PDFs) de forma colaborativa,
como no **Vimeo Review**: quem produz sobe os arquivos num "espaço", escolhe quem pode revisar, e os
revisores deixam **comentários ancorados** — em vídeo/áudio no **time code exato**, para a editora saber
precisamente a que segundo o comentário se refere. Hoje isso é feito por links externos e mensagens
soltas, sem precisão e sem histórico organizado.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Criar espaço e subir materiais (Priority: P1) 🎯 MVP

Como pessoa da equipe de marketing, quero criar um espaço de revisão, subir **um ou vários arquivos** e
escolher **quais usuários** poderão revisar.

**Acceptance Scenarios**:

1. **Given** que tenho permissão de marketing, **When** crio um espaço com título e envio vários
   arquivos de uma vez, **Then** o espaço é criado com todos os materiais listados.
2. **Given** o espaço criado, **When** seleciono os usuários revisores, **Then** apenas eles (mais eu e
   o super admin) passam a ter acesso ao espaço.
3. **Given** tipos diferentes (vídeo, áudio, imagem, PDF), **When** subo cada um, **Then** o sistema
   reconhece o tipo e mostra o material no visualizador adequado.

### User Story 2 - Comentar em vídeo/áudio no time code exato (Priority: P1) 🎯 MVP

Como revisor, quero assistir ao vídeo (ou ouvir o áudio) e deixar um comentário **ancorado no segundo
exato**, para a editora saber onde aplicar a correção.

**Acceptance Scenarios**:

1. **Given** um vídeo no visualizador, **When** escrevo um comentário, **Then** ele é salvo com o **time
   code atual** do player (ex.: 00:42).
2. **Given** comentários com time code, **When** clico em um comentário da lista, **Then** o player
   **salta** para aquele exato momento.
3. **Given** a linha do tempo do player, **When** há comentários, **Then** vejo **marcadores** nos
   momentos comentados.
4. **Given** um comentário resolvido pela editora, **When** marco como **concluído**, **Then** ele fica
   sinalizado como resolvido para todos.

### User Story 3 - Comentar em foto e PDF (Priority: P2)

Como revisor, quero comentar em fotos e PDFs também.

**Acceptance Scenarios**:

1. **Given** uma foto, **When** clico em um ponto da imagem e comento, **Then** o comentário fica
   **ancorado naquele ponto** (um "pin" visível).
2. **Given** um PDF, **When** comento, **Then** posso indicar a **página** a que o comentário se refere.
3. **Given** qualquer material, **When** abro o visualizador, **Then** vejo a **lista de comentários**
   com autor, data e (quando houver) time code / página / posição.

### Edge Cases

- Usuário sem acesso ao espaço tenta abrir → bloqueado.
- Arquivo de tipo não suportado → rejeitado com mensagem; tipos suportados: vídeo, áudio, imagem, PDF.
- Arquivo grande além do limite → rejeitado com mensagem clara (limite por arquivo).
- Comentário sem texto → não é salvo.
- Excluir um material → remove seus comentários junto; excluir o espaço → remove tudo dele.

## Requirements *(mandatory)*

### Espaço e materiais

- **FR-001**: Usuários com permissão de **marketing** (e o super admin) MUST poder **criar** espaços de
  revisão com título e descrição opcional.
- **FR-002**: Ao criar/editar um espaço, o criador MUST poder **enviar vários arquivos de uma vez**
  (equivalente a "uma pasta de arquivos").
- **FR-003**: O sistema MUST identificar o **tipo** de cada material (vídeo, áudio, imagem, PDF) e exibi-lo
  no visualizador apropriado.
- **FR-004**: Os arquivos MUST ser guardados no **armazenamento próprio** (volume), com **limite de
  tamanho por arquivo** e tipos permitidos por segurança.

### Acesso / revisores

- **FR-005**: O criador MUST poder **selecionar quais usuários** podem revisar um espaço.
- **FR-006**: Somente o **criador**, os **revisores selecionados** e o **super admin** MUST conseguir
  abrir o espaço e comentar; demais usuários são bloqueados.
- **FR-007**: Apenas o **criador** (ou super admin) MUST poder editar o espaço, gerenciar revisores e
  excluir materiais/espaço.

### Comentários ancorados

- **FR-008**: Em **vídeo e áudio**, ao comentar, o sistema MUST registrar o **time code** atual do
  player; clicar no comentário MUST **posicionar o player** naquele momento.
- **FR-009**: O player MUST exibir **marcadores** na linha do tempo nos momentos com comentário.
- **FR-010**: Em **imagem**, o revisor MUST poder ancorar o comentário a um **ponto** clicado (pin),
  visível depois.
- **FR-011**: Em **PDF**, o revisor MUST poder associar o comentário a uma **página**.
- **FR-012**: Todo comentário MUST registrar **autor e data**; qualquer revisor com acesso MUST poder
  **comentar**; o autor (ou criador/super admin) MUST poder **excluir** o próprio comentário.
- **FR-013**: Comentários MUST poder ser marcados como **concluídos/resolvidos**, visível a todos.

## Success Criteria *(mandatory)*

- **SC-001**: Um membro de marketing cria um espaço, sobe múltiplos materiais e define revisores em menos
  de 2 minutos.
- **SC-002**: Em 100% dos comentários de vídeo/áudio, clicar no comentário leva o player ao segundo
  correto (±1s).
- **SC-003**: Apenas pessoas autorizadas conseguem abrir/comentar num espaço.
- **SC-004**: Materiais de todos os tipos suportados (vídeo, áudio, imagem, PDF) são visualizáveis dentro
  do app, sem depender de links externos.
- **SC-005**: Cada comentário mostra autor, data e a âncora pertinente (time code / página / ponto).

## Key Entities

- **Espaço de Revisão**: título, descrição, criador, data; agrupa materiais e a lista de revisores.
- **Material**: arquivo pertencente a um espaço; tipo (vídeo/áudio/imagem/PDF), nome original, ordem.
- **Revisor do Espaço**: vínculo entre um espaço e um usuário autorizado a revisar.
- **Comentário**: texto + autor + data, ancorado conforme o tipo (time code em segundos para vídeo/áudio,
  página para PDF, ponto x/y para imagem), com estado **resolvido** e exclusão pelo autor/criador.

## Assumptions

- **Quem cria**: introduz-se um papel **MARKETING**; criação de espaços liberada a MARKETING e
  SUPERADMIN. Revisores podem ser **quaisquer usuários** selecionados (não precisam ser de marketing).
- **Armazenamento**: usa o volume já existente (subpasta dedicada). **Limite por arquivo** padrão de
  ~512 MB e tipos permitidos (vídeo mp4/mov/webm; áudio mp3/wav/m4a/ogg; imagem jpg/png/webp/gif; pdf),
  com o teto de requisição elevado para acomodar vídeos. A capacidade total depende do tamanho do volume
  (redimensionável no provedor).
- **Player**: usa o reprodutor nativo do navegador para vídeo/áudio; PDF embutido; imagem com pin por
  coordenadas relativas (%) para ser fiel em qualquer tela.
- **MVP**: comentários são "planos" (sem respostas aninhadas) nesta versão; resolução (concluído) e
  exclusão incluídas. Respostas/threads e notificações por e-mail ficam para uma evolução futura.
- **Sem streaming/transcodificação**: os vídeos são servidos como arquivo (adequado a clipes de revisão);
  não há geração de múltiplas resoluções como no Vimeo.
