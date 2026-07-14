# Feature Specification: Feedback do Cliente por Evento

**Feature Branch**: `130-feedback-cliente-evento`

**Created**: 2026-07-14

**Status**: Draft

**Input**: "Nessa lista de funções [menu de ferramentas do evento] é importante ter um feedback
cliente. Ao clicar, copia para a área de transferência um link para a página de avaliação
específica desse evento. UI: 1) pergunta única + 5 estrelas grandes, nada mais aparece até
clicar numa estrela (progressivo); 2) ao clicar, aparecem cards/chips selecionáveis
(múltipla escolha) — um conjunto de elogios se a nota for 5, um conjunto de pontos de
atenção se a nota for de 1 a 4; 3) campo de texto opcional + botão grande de envio."

## Contexto

Hoje o sistema já coleta avaliação dos **artistas** sobre o evento (portal do talento).
Não existe nenhum canal para coletar a avaliação da **cliente** (quem contratou) sobre a
experiência com a equipe da Manto. A ferramenta entra no menu "⋯ Ferramentas" da página do
evento (feature 129): um clique gera e copia um link público específico daquele evento,
para a comercial enviar à cliente por WhatsApp depois do evento.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Pedir feedback da cliente (Priority: P1)

Uma pessoa da comercial, depois de um evento, abre a página do evento, clica em "⋯
Ferramentas" → "Pedir feedback da cliente". O link da página de avaliação daquele evento
específico é copiado para a área de transferência, pronto para colar numa conversa de
WhatsApp com a cliente.

**Why this priority**: sem essa ação não existe link nenhum para enviar — é o ponto de
entrada de toda a feature.

**Independent Test**: clicar no item do menu numa página de evento e verificar que o
conteúdo da área de transferência é uma URL válida que resolve para a página de avaliação
daquele evento (e não de outro).

**Acceptance Scenarios**:

1. **Given** a página de um evento, **When** a comercial clica em "Pedir feedback da
   cliente" no menu de ferramentas, **Then** um link é copiado para a área de transferência
   e o botão mostra confirmação visual de que copiou (mesmo padrão dos outros botões de
   copiar do sistema).
2. **Given** que o link para aquele evento ainda não existia, **When** a comercial clica
   pela primeira vez, **Then** o sistema cria o link automaticamente (não precisa de um
   passo de configuração separado).
3. **Given** que o link para aquele evento já existe, **When** a comercial clica de novo
   (ex.: outro dia), **Then** o mesmo link de sempre é copiado — continua funcionando para
   quem já o recebeu antes.

### User Story 2 - Cliente avalia a experiência (Priority: P1)

A cliente recebe o link pelo WhatsApp, abre no celular e vê uma pergunta única — "Como foi
a experiência com a equipe da Manto Produções?" — com 5 estrelas grandes. Assim que toca
numa estrela, aparecem cards para marcar (pode marcar mais de um) e um campo de texto
opcional, terminando num botão grande de enviar.

**Why this priority**: é o coração da feature — sem uma avaliação simples de preencher no
celular, o link pedido na User Story 1 não gera nenhum dado.

**Independent Test**: abrir o link da página de avaliação de um evento (sem estar logada em
nada) direto de um navegador de celular, preencher e enviar, e conferir que a resposta foi
salva vinculada ao evento certo.

**Acceptance Scenarios**:

1. **Given** a página de avaliação recém-aberta, **When** a cliente ainda não tocou em
   nenhuma estrela, **Then** só a pergunta e as 5 estrelas aparecem — nenhum card, campo de
   texto ou botão de enviar é visível ainda.
2. **Given** a página de avaliação, **When** a cliente toca na 5ª estrela, **Then** aparece
   o título "Incrível! O que mais se destacou?" com os cards: 🎭 Atuação Impecável, 👗
   Figurino Perfeito, 🤝 Interação com Convidados, ⏰ Pontualidade, ✨ Pura Magia.
3. **Given** a página de avaliação, **When** a cliente toca em qualquer estrela de 1 a 4,
   **Then** aparece o título "Obrigado! Onde podemos melhorar para a próxima?" com os cards:
   ⏰ Atraso, 👗 Figurino, 🎭 Atuação / Energia, 🗣️ Comunicação.
4. **Given** os cards visíveis, **When** a cliente toca em mais de um, **Then** todos os
   tocados ficam marcados ao mesmo tempo (seleção múltipla).
5. **Given** os cards visíveis, **When** a cliente troca de nota (ex.: de 5 para 3
   estrelas), **Then** o conjunto de cards muda para o do novo cenário e qualquer card já
   marcado do conjunto anterior é desmarcado (os dois conjuntos não se misturam).
6. **Given** o formulário preenchido (nota obrigatória; cards e texto opcionais), **When**
   a cliente toca em "Enviar Avaliação", **Then** a resposta é salva vinculada ao evento e a
   cliente vê uma confirmação de agradecimento na mesma tela.
7. **Given** um link de avaliação inválido ou já usado incorretamente, **When** alguém
   abre uma URL que não corresponde a nenhum evento, **Then** vê uma mensagem amigável de
   link inválido, nunca um erro técnico.

### User Story 3 - Time vê o feedback recebido (Priority: P2)

Alguém da comercial ou a superadmin volta à página do evento e vê, num painel próprio, as
avaliações da cliente já recebidas para aquele evento: nota, cards marcados e comentário.

**Why this priority**: pedir feedback (US1) e coletá-lo (US2) não geram valor se ninguém
consegue ler o resultado depois — mas isso só importa depois que já existe algo para
mostrar.

**Independent Test**: com pelo menos uma avaliação já enviada para um evento, abrir a
página desse evento e conferir que a nota, os cards e o comentário aparecem corretamente.

**Acceptance Scenarios**:

1. **Given** um evento sem nenhum feedback recebido ainda, **When** a comercial abre a
   página do evento, **Then** o painel de feedback mostra um estado vazio explicativo (não
   fica escondido nem quebra a página).
2. **Given** um evento com uma ou mais avaliações recebidas, **When** a comercial abre a
   página do evento, **Then** vê cada avaliação com nota em estrelas, os cards marcados e o
   comentário (quando houver) e a data de envio.

### Edge Cases

- Cliente abre o link, começa a preencher, mas fecha a aba antes de enviar: nada é salvo
  (mesmo comportamento de qualquer formulário não enviado) — nenhuma avaliação parcial fica
  registrada.
- Cliente reabre o mesmo link depois de já ter enviado uma vez: o link continua funcionando
  e permite enviar de novo (ex.: duas pessoas diferentes do lado da cliente usando o mesmo
  link) — o sistema não tenta impedir múltiplos envios pelo mesmo link, já que não há login
  para identificar quem está respondendo.
- Link de avaliação é enviado/reencaminhado para muita gente ao mesmo tempo (ex.: grupo de
  WhatsApp): o envio tem um limite de tentativas por período para não virar alvo de spam
  automatizado, sem impedir o uso normal esperado.
- Evento sem nenhum dado de data/local ainda preenchido: a página de avaliação continua
  funcionando (mostra só o nome do evento).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O menu de ferramentas da página do evento (feature 129) DEVE ter um item
  "Pedir feedback da cliente", visível para quem já vê hoje as demais ferramentas
  comerciais do evento (Confirmar dados, Cobrança).
- **FR-002**: Clicar nesse item DEVE copiar para a área de transferência uma URL pública
  específica daquele evento, criando-a automaticamente se ainda não existir, com feedback
  visual de que copiou.
- **FR-003**: A URL pública NÃO DEVE ser baseada no identificador sequencial do evento (que
  seria adivinhável) — precisa de um identificador não previsível.
- **FR-004**: A página pública de avaliação DEVE funcionar sem exigir login ou qualquer
  identificação da cliente.
- **FR-005**: A página DEVE mostrar, inicialmente, apenas a pergunta "Como foi a
  experiência com a equipe da Manto Produções?" e 5 estrelas — nada mais visível antes do
  primeiro clique numa estrela.
- **FR-006**: Ao clicar numa estrela, a página DEVE revelar um conjunto de cards
  selecionáveis (múltipla escolha) apropriado à nota: cards de elogio para nota 5, cards de
  ponto de atenção para notas de 1 a 4 (conforme listas do Contexto/User Story 2).
- **FR-007**: Trocar a nota depois de já ter revelado os cards DEVE atualizar o conjunto de
  cards mostrado e desmarcar qualquer seleção do conjunto anterior.
- **FR-008**: A página DEVE mostrar um campo de texto opcional para recado/sugestão,
  independente da nota escolhida, e um botão de envio.
- **FR-009**: Nota é obrigatória para enviar; cards marcados e o campo de texto são
  opcionais.
- **FR-010**: Ao enviar, o sistema DEVE salvar a avaliação (nota, cards marcados,
  comentário, data/hora) vinculada ao evento correspondente ao link.
- **FR-011**: Depois de enviar, a cliente DEVE ver uma tela de agradecimento na mesma
  página (sem exigir navegação extra).
- **FR-012**: Uma URL de avaliação que não corresponde a nenhum evento válido DEVE mostrar
  uma mensagem amigável, nunca um erro técnico.
- **FR-013**: O envio da avaliação DEVE ter um limite de tentativas por período (mesma
  família de proteção já usada nos formulários públicos existentes) para conter abuso
  automatizado.
- **FR-014**: A página do evento DEVE mostrar, para quem tem permissão de ver as
  ferramentas comerciais, um painel com as avaliações da cliente já recebidas (nota, cards,
  comentário, data), com estado vazio claro quando ainda não há nenhuma.
- **FR-015**: A página pública de avaliação DEVE funcionar bem em tela de celular (é o
  contexto de uso esperado — link aberto pelo WhatsApp).

### Key Entities

- **Feedback do Cliente**: uma avaliação enviada por uma cliente sobre um evento — nota (1
  a 5), cards selecionados (lista, pode ser vazia), comentário (opcional), data/hora de
  envio. Pertence a um evento; um evento pode ter várias avaliações de feedback.
- **Link de Avaliação do Evento**: identificador não adivinhável associado a um evento, que
  resolve para a página pública de avaliação daquele evento específico.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A comercial consegue gerar e copiar o link de avaliação de um evento em um
  único clique, a partir da página do evento.
- **SC-002**: Uma cliente sem nenhuma conta ou login no sistema consegue enviar uma
  avaliação completa a partir do celular em menos de 1 minuto.
- **SC-003**: 100% das avaliações enviadas aparecem corretamente vinculadas ao evento certo
  na página interna do evento, com nota, cards e comentário fiéis ao que foi enviado.
- **SC-004**: Nenhuma avaliação parcial (estrela tocada mas não enviada) aparece salva no
  painel interno.

## Assumptions

- O link de avaliação é o mesmo para qualquer pessoa que o receba (não há um link por
  destinatário) — está alinhado ao pedido original ("copia... um link para a página de
  avaliação específica desse evento", no singular por evento, não por pessoa).
- Múltiplos envios pelo mesmo link são permitidos e todos ficam registrados como
  avaliações separadas — o sistema não tenta impedir isso, porque não há identificação de
  quem está respondendo; mais sinal (mesmo que duplicado) é preferível a bloquear
  respostas legítimas de pessoas diferentes do lado da cliente.
- Visibilidade do painel de feedback e do item de menu segue o mesmo grupo que já vê hoje
  "Confirmar dados do evento" e "Cobrança" (comercial + superadmin) — é informação sobre a
  relação com a cliente, mesma família das demais ferramentas comerciais do evento.
- O limite de tentativas de envio (FR-013) segue o mesmo padrão já usado nos formulários
  públicos de pré-contrato existentes (throttling por período, não bloqueio permanente).
- Não faz parte deste escopo: notificar automaticamente o time quando uma nota baixa
  chegar, painel agregado de todos os eventos, ou edição/exclusão da avaliação pela
  cliente depois de enviada — pode virar uma feature futura se a necessidade aparecer.
