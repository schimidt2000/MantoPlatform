# Feature Specification: Botão para rever o termo de consentimento no portal

**Feature Branch**: `091-portal-botao-termo-consentimento`

**Created**: 2026-06-26

**Status**: Draft

**Input**: "Preciso de um botão pequeno porém visível no portal para que as pessoas possam ver o termo de
consentimento que fazemos elas aceitarem ao entrar no sistema. Também me diga qual o link para eu ver."

## Contexto

No primeiro acesso ao **Portal do Artista**, o talento precisa **aceitar** um Termo de Consentimento. Hoje,
depois de aceito, **não há como rever** o termo — ao abrir a página do termo, o sistema redireciona para a
home. O talento precisa de uma forma simples de **consultar** o termo que aceitou, a qualquer momento.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Rever o termo a qualquer momento (Priority: P1) 🎯 MVP

Como talento que já aceitou o termo, quero um botão visível no portal para **rever** o texto do termo de
consentimento quando quiser.

**Acceptance Scenarios**:

1. **Given** que estou logado no portal e já aceitei o termo, **When** vejo a tela inicial, **Then** há um
   botão pequeno e visível para ver o termo de consentimento.
2. **Given** que clico nesse botão, **When** a página abre, **Then** vejo o **texto completo** do termo em
   modo **leitura**, com a informação de **quando** eu o aceitei.
3. **Given** que estou vendo o termo já aceito, **When** termino de ler, **Then** consigo **voltar** ao
   portal facilmente.
4. **Given** que **ainda não** aceitei o termo (primeiro acesso), **When** acesso a página do termo,
   **Then** continuo vendo o fluxo de **aceite** (como hoje), sem alteração.

### Edge Cases

- Usuário não logado tentando acessar a página do termo → enviado ao login (comportamento atual).
- Talento com troca de senha pendente → fluxo atual de troca de senha tem prioridade.

## Requirements *(mandatory)*

- **FR-001**: O portal MUST exibir um **botão pequeno e visível** que leva à página do termo de
  consentimento.
- **FR-002**: A página do termo MUST permitir **reler** o texto completo mesmo depois de aceito (modo
  leitura), em vez de redirecionar para a home.
- **FR-003**: No modo leitura, a página MUST informar **quando** o termo foi aceito e oferecer um caminho
  para **voltar** ao portal, **sem** exibir novamente o botão de aceitar.
- **FR-004**: Para quem **ainda não aceitou**, o fluxo de **aceite** MUST permanecer inalterado.

## Success Criteria *(mandatory)*

- **SC-001**: Um talento logado encontra e abre o termo em **1 clique** a partir da tela inicial.
- **SC-002**: O termo aceito pode ser **relido** quantas vezes quiser, sem refazer o aceite.
- **SC-003**: O fluxo de primeiro aceite continua funcionando como antes.

## Assumptions

- O "portal" é o **Portal do Artista** (`/portal`). O botão fica na **tela inicial** do portal (cabeçalho),
  pequeno e visível.
- O termo exibido é o **mesmo** texto já usado no aceite (não muda o conteúdo).
- A data exibida no modo leitura é a data registrada de aceite do talento.
