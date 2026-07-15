# Feature Specification: Nome Obrigatório na Avaliação + Mensagem Pronta ao Copiar o Link

**Feature Branch**: `132-nome-obrigatorio-mensagem-feedback`

**Created**: 2026-07-14

**Status**: Draft

**Input**: "1) Adicione um campo na avaliação do cliente: ela deve preencher
obrigatoriamente o nome antes de fazer a avaliação. 2) No botão de copiar o link, preciso
que copie este texto: 'Olá! Como vai? Obrigado por contar com a Manto para um momento tão
mágico e especial! Se puder, deixe uma avaliação no link abaixo. Seu feedback faz toda a
diferença! 💙 👉 Link aqui Até a próxima!' (com o link de verdade no lugar de 'Link aqui')."

## Contexto

A feature 130 criou a página pública de avaliação (nota + cards + comentário) e a feature
131 organizou onde ver esse feedback. Duas lacunas identificadas no uso real: (1) uma
avaliação chega sem saber quem a enviou — sem nome, fica difícil relacionar com a cliente
certa quando o evento tem mais de uma pessoa envolvida; (2) hoje o botão "Pedir feedback da
cliente" copia só a URL crua, obrigando quem for enviar por WhatsApp a escrever uma
mensagem de acompanhamento na hora — os outros botões da mesma área (Confirmar dados,
Cobrança) já copiam uma mensagem pronta.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Saber quem enviou a avaliação (Priority: P1)

Uma cliente abre o link de avaliação recebido pelo WhatsApp. Antes de conseguir enviar a
avaliação, precisa informar seu nome. Depois, quando alguém da comercial olha essa
avaliação (na página do evento ou na tela de avaliações de clientes), vê o nome de quem
avaliou.

**Why this priority**: sem saber quem respondeu, o feedback perde parte do valor prático —
principalmente em eventos com mais de um contato do lado da cliente.

**Independent Test**: abrir o link de avaliação, tentar enviar sem preencher o nome e
confirmar que não envia; preencher o nome e enviar normalmente; conferir que o nome
aparece depois nas telas internas.

**Acceptance Scenarios**:

1. **Given** a página de avaliação, **When** a cliente carrega a página, **Then** vê um
   campo para digitar o nome, antes da pergunta de nota.
2. **Given** o formulário preenchido sem o nome, **When** a cliente tenta enviar, **Then**
   a avaliação não é enviada e ela vê uma indicação clara de que o nome é obrigatório.
3. **Given** o nome preenchido (e o resto do formulário preenchido normalmente), **When**
   a cliente envia, **Then** a avaliação é salva com o nome informado.
4. **Given** uma avaliação já enviada com nome, **When** alguém da comercial vê essa
   avaliação na página do evento ou na tela de avaliações de clientes, **Then** o nome
   informado aparece junto da nota/comentário.

### User Story 2 - Copiar uma mensagem pronta para enviar (Priority: P2)

Uma pessoa da comercial clica em "Pedir feedback da cliente" na página do evento. O texto
copiado para a área de transferência já vem pronto para colar direto numa conversa de
WhatsApp — com a saudação, o pedido de avaliação e o link de verdade no meio da mensagem —
sem precisar escrever nada a mais.

**Why this priority**: é uma melhoria de conveniência sobre uma ferramenta que já funciona
(feature 130) — importante para o dia a dia, mas menor que garantir a identificação de
quem avalia (US1).

**Independent Test**: clicar no botão, colar o conteúdo copiado num editor de texto e
conferir que o texto bate exatamente com o modelo pedido, com o link de verdade daquele
evento no lugar do link de exemplo.

**Acceptance Scenarios**:

1. **Given** a página de um evento, **When** a comercial clica em "Pedir feedback da
   cliente", **Then** o texto copiado é a mensagem completa (saudação, agradecimento,
   pedido de avaliação, o link de verdade daquele evento e despedida), não apenas o link
   sozinho.
2. **Given** o botão já foi clicado antes para o mesmo evento, **When** a comercial clica
   de novo, **Then** a mensagem copiada continua usando o mesmo link de sempre daquele
   evento (o link não muda a cada clique).

### Edge Cases

- Nome enviado com espaços only ou vazio deve ser tratado como não preenchido (mesma regra
  de "obrigatório" que os demais formulários públicos do sistema).
- Avaliações enviadas antes desta mudança não têm nome — as telas internas devem continuar
  mostrando essas avaliações antigas normalmente, só sem nome (não pode quebrar a
  exibição das avaliações já existentes).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: A página pública de avaliação DEVE pedir o nome de quem está avaliando, como
  campo obrigatório, posicionado antes da pergunta de nota.
- **FR-002**: A avaliação NÃO DEVE ser aceita (nem salva) sem o nome preenchido.
- **FR-003**: O nome informado DEVE ser salvo junto da avaliação.
- **FR-004**: Onde a avaliação já é exibida hoje (página do evento e tela de avaliações de
  clientes), o nome informado DEVE aparecer junto dos demais dados da avaliação.
- **FR-005**: Avaliações enviadas antes desta mudança (sem nome) DEVEM continuar sendo
  exibidas normalmente nas telas internas, sem nome ou com uma indicação de "não
  informado".
- **FR-006**: O botão "Pedir feedback da cliente" DEVE copiar uma mensagem pronta (não
  apenas o link), incluindo o texto de saudação e pedido de avaliação fornecido, com o
  link de verdade daquele evento no lugar indicado.
- **FR-007**: O link dentro da mensagem copiada DEVE ser o mesmo link único e não
  adivinhável já usado hoje (criado automaticamente na primeira vez, reaproveitado depois).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Toda avaliação enviada a partir desta mudança chega com o nome de quem
  respondeu, sem exceção.
- **SC-002**: Quem clica em "Pedir feedback da cliente" consegue colar a mensagem direto
  numa conversa, sem precisar editar ou completar nada antes de enviar.

## Assumptions

- O nome é digitado livremente pela cliente (texto simples) — não precisa bater com o nome
  cadastrado no cliente do sistema (`Client.name`), já que quem responde pode ser uma
  pessoa diferente de quem está cadastrada (ex.: assistente, cônjuge).
- O campo de nome não bloqueia o restante do formulário (estrelas, cards, comentário)
  antes de ser preenchido — ele só impede o envio final, mesma lógica de "obrigatório"
  usada em qualquer outro campo obrigatório do sistema (o formulário todo é validado no
  envio).
- O texto da mensagem é fixo, exatamente como fornecido — não usa a saudação dinâmica
  ("Bom dia"/"Boa tarde"/"Boa noite") que outros botões da mesma tela usam, porque o texto
  pedido já começa com uma saudação própria ("Olá! Como vai?").
