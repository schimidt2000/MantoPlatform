# Feature Specification: Arquivos temporários na Revisão (expiração, versão e finalizar)

**Feature Branch**: `090-revisao-arquivos-temporarios`

**Created**: 2026-06-26

**Status**: Draft

**Input**: "Os arquivos subidos na revisão devem ser temporários: após 7 dias podem ser excluídos, para
não ocupar tanto espaço. Avisar isso a quem cria o espaço. Depois de criar, o criador pode **substituir**
o arquivo (versionamento). E quando o vídeo for **aprovado e clicado como finalizado** pelo criador, o
arquivo pode ser excluído do nosso armazenamento."

## Contexto

O módulo de Revisão (feature 088) guarda vídeos/áudios/imagens/PDFs no nosso armazenamento (volume). Como
vídeos ocupam muito espaço, os materiais devem ser **temporários**: ficam disponíveis por **7 dias** e
depois o arquivo é **removido automaticamente**. O **histórico de comentários permanece** — apenas o
arquivo sai do armazenamento. O criador é **avisado** disso ao montar o espaço. Ele também pode
**substituir** um material por uma nova versão (reiniciando os 7 dias) e, quando o material está aprovado,
marcá-lo como **finalizado**, o que remove o arquivo na hora (libera espaço).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Aviso de arquivos temporários ao criar (Priority: P1) 🎯 MVP

Como criador de um espaço de revisão, quero ser avisado de que os arquivos são temporários (7 dias),
para não contar com eles como armazenamento permanente.

**Acceptance Scenarios**:

1. **Given** a tela de criar espaço, **When** abro o formulário, **Then** vejo um aviso claro de que os
   arquivos ficam ~7 dias e depois são removidos automaticamente.
2. **Given** um material recém-enviado, **When** vejo o espaço, **Then** há indicação de **quando** ele
   expira (ex.: "expira em 7 dias").

### User Story 2 - Expiração automática em 7 dias (Priority: P1) 🎯 MVP

Como responsável pela plataforma, quero que materiais com mais de 7 dias tenham o **arquivo removido**
automaticamente, mantendo o registro e os comentários.

**Acceptance Scenarios**:

1. **Given** um material enviado há mais de 7 dias e **não finalizado**, **When** a limpeza automática
   roda, **Then** o **arquivo** é removido do armazenamento e o material fica marcado como **expirado**.
2. **Given** um material expirado, **When** abro o visualizador, **Then** vejo "arquivo removido" no
   lugar do player, mas os **comentários continuam** visíveis.
3. **Given** um material **finalizado**, **When** a limpeza roda, **Then** ele não é tratado como
   "expirado" (já foi removido pela finalização).

### User Story 3 - Substituir arquivo (versionamento) (Priority: P2)

Como criador, quero substituir o arquivo de um material por uma nova versão, reiniciando o prazo.

**Acceptance Scenarios**:

1. **Given** um material no espaço, **When** o criador envia um novo arquivo no lugar, **Then** o arquivo
   antigo é **removido** do armazenamento e o novo passa a valer, com a **versão** incrementada.
2. **Given** a substituição, **When** ela ocorre, **Then** o **prazo de 7 dias reinicia** a partir da
   nova versão e os **comentários são mantidos**.
3. **Given** um material já expirado/removido, **When** o criador substitui, **Then** ele volta a ter
   arquivo disponível (nova versão).

### User Story 4 - Finalizar (aprovado → remove arquivo) (Priority: P2)

Como criador, quando o material está aprovado, quero marcá-lo como **finalizado**, removendo o arquivo do
armazenamento para liberar espaço.

**Acceptance Scenarios**:

1. **Given** um material aprovado, **When** o criador clica em **Finalizar**, **Then** o arquivo é
   removido do armazenamento e o material fica marcado como **finalizado**.
2. **Given** um material finalizado, **When** alguém abre, **Then** vê "finalizado — arquivo removido" e
   os comentários permanecem.
3. **Given** que finalizar remove o arquivo, **When** o criador confirma, **Then** há uma confirmação
   antes (ação irreversível para o arquivo).

### Edge Cases

- Apenas o **criador** do espaço (ou super admin) pode substituir e finalizar; revisores não.
- Substituir exige o **mesmo tipo** de mídia (não trocar vídeo por PDF).
- Material finalizado **não** volta a expirar; substituir um finalizado o reativa (nova versão).
- A remoção do arquivo (expiração/finalização) **nunca** apaga o registro nem os comentários.

## Requirements *(mandatory)*

- **FR-001**: Cada material MUST ter um **prazo de validade** de **7 dias** a partir do envio (ou da
  última substituição).
- **FR-002**: A tela de **criar espaço** MUST exibir um **aviso** de que os arquivos são temporários
  (~7 dias) e depois removidos.
- **FR-003**: O espaço/visualizador MUST indicar **quando** cada material expira (ou que já expirou/
  finalizou).
- **FR-004**: O sistema MUST remover **automaticamente** o **arquivo** de materiais com prazo vencido e
  **não finalizados**, mantendo registro e comentários (estado "expirado").
- **FR-005**: O **criador** (ou super admin) MUST poder **substituir** o arquivo de um material; isso
  remove o arquivo antigo, registra **nova versão** e **reinicia** o prazo de 7 dias, preservando os
  comentários.
- **FR-006**: A substituição MUST manter o **mesmo tipo** de mídia do material.
- **FR-007**: O **criador** (ou super admin) MUST poder **finalizar** um material; isso **remove o
  arquivo** do armazenamento na hora e marca como **finalizado**, preservando registro e comentários.
- **FR-008**: A finalização MUST pedir **confirmação** (remoção do arquivo é irreversível).
- **FR-009**: Substituir e finalizar MUST ser restritos ao criador/super admin; revisores não têm essas
  ações.
- **FR-010**: Quando o arquivo de um material foi removido (expirado ou finalizado), o visualizador MUST
  mostrar isso claramente em vez do player, **sem** ocultar os comentários.

## Success Criteria *(mandatory)*

- **SC-001**: Quem cria um espaço entende, na própria tela, que os arquivos duram ~7 dias.
- **SC-002**: 100% dos materiais não finalizados com mais de 7 dias têm o **arquivo** removido, sem
  perder comentários.
- **SC-003**: Substituir um material gera uma nova versão, reinicia o prazo e libera o arquivo antigo.
- **SC-004**: Finalizar um material libera o espaço do arquivo imediatamente, mantendo o histórico.
- **SC-005**: O espaço em armazenamento ocupado por revisões antigas cai ao longo do tempo (arquivos
  expirados/finalizados não permanecem).

## Key Entities

- **Material de revisão** (existente): ganha **prazo de validade** (expira em), estado de **finalizado**,
  marcação de **arquivo removido** e número de **versão**. O registro e os comentários sobrevivem à
  remoção do arquivo.

## Assumptions

- **Janela** padrão de **7 dias** a partir do envio/substituição. A limpeza roda **periodicamente** (ao
  menos uma vez ao dia) — não precisa ser exatamente no minuto do vencimento.
- **Expirar/finalizar removem só o arquivo** do armazenamento; o material continua na lista marcado como
  expirado/finalizado, e os comentários permanecem (são o valor da revisão).
- **Substituir** mantém o mesmo material (mesma identidade e comentários), troca o arquivo, soma 1 na
  versão e reinicia o prazo. Mantém o **mesmo tipo** de mídia.
- Materiais **já existentes** (anteriores a esta mudança) recebem prazo = data de envio + 7 dias.
- Ações de substituir/finalizar seguem a permissão atual do módulo (criador do espaço ou super admin).
