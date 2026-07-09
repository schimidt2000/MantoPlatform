# Feature Specification: Editor de Formulários

**Feature Branch**: `123-editor-formularios`

**Created**: 2026-07-09

**Status**: Draft

**Input**: "Hoje os formulários estão hardcoded, certo? Gostaria de poder editar os formulários
direto do sistema. Adicionando campos, editando textos, mudando obrigatoriedade. Enfim, tudo
que um editor de formulários pode proporcionar."

## Contexto

Os dois formulários públicos de pré-contrato (comum e corporativo, feature 118) têm hoje
todos os campos, rótulos, seções e regras de obrigatoriedade fixos no código. Qualquer ajuste
— corrigir um texto, tornar um campo opcional, adicionar uma pergunta nova — exige alteração
de código e novo deploy. Esta feature move essa estrutura para dentro do sistema, editável
pelo painel, sem precisar mexer em código para mudanças de conteúdo.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Editar texto e obrigatoriedade de um campo existente (Priority: P1)

Um SUPERADMIN acessa a área de edição de um dos formulários públicos, altera o rótulo (texto
exibido) de um campo existente e muda se ele é obrigatório ou opcional. Ao salvar, o
formulário público já reflete a mudança no próximo carregamento — sem deploy.

**Why this priority**: é o pedido mais direto do usuário ("editando textos, mudando
obrigatoriedade") e o de menor risco — não altera a estrutura de dados, só como ela é
apresentada e validada.

**Independent Test**: alterar o rótulo e a obrigatoriedade de um campo do formulário comum
pelo painel; abrir `/f/pre-contrato` numa aba anônima e confirmar o novo texto e o novo
comportamento de validação (bloqueia envio se ficou obrigatório e está vazio; permite envio
vazio se ficou opcional).

**Acceptance Scenarios**:

1. **Given** um campo existente com um rótulo, **When** o SUPERADMIN edita o texto pelo
   painel e salva, **Then** o formulário público mostra o novo texto no próximo carregamento.
2. **Given** um campo opcional, **When** o SUPERADMIN o marca como obrigatório, **Then** o
   envio do formulário público passa a ser bloqueado (com aviso amigável) se esse campo ficar
   vazio.
3. **Given** um campo obrigatório, **When** o SUPERADMIN o marca como opcional, **Then** o
   formulário público aceita o envio mesmo com esse campo vazio.

---

### User Story 2 - Adicionar um novo campo personalizado (Priority: P2)

Um SUPERADMIN adiciona um campo novo a uma seção de um dos formulários — escolhendo um tipo
(texto curto, texto longo, seleção com opções, data, hora, telefone, e-mail, CPF, CNPJ ou
sim/não), um rótulo e se é obrigatório. O campo passa a aparecer no formulário público, na
posição escolhida, participando da validação e sendo incluído na resposta salva e na mensagem
de WhatsApp gerada no envio.

**Why this priority**: é o segundo pedido explícito ("adicionando campos") — depende da
capacidade de edição da User Story 1 já existir (rótulo/obrigatoriedade), mas adiciona
estrutura nova em vez de só editar a existente.

**Independent Test**: adicionar um campo de texto curto opcional a uma seção do formulário
corporativo; preencher e enviar o formulário público; conferir que o valor aparece na resposta
salva (banco de respostas) e na mensagem de WhatsApp montada.

**Acceptance Scenarios**:

1. **Given** uma seção de um formulário, **When** o SUPERADMIN adiciona um campo novo com tipo,
   rótulo e obrigatoriedade definidos, **Then** o campo aparece no formulário público na
   posição escolhida.
2. **Given** um campo novo marcado como obrigatório, **When** o formulário público é enviado
   sem preenchê-lo, **Then** o envio é bloqueado com o mesmo padrão de aviso dos campos
   existentes.
3. **Given** um campo novo preenchido, **When** o formulário é enviado, **Then** o valor
   aparece na resposta salva e na mensagem de WhatsApp, na mesma posição/seção configurada.

---

### User Story 3 - Remover e reordenar campos (Priority: P3)

Um SUPERADMIN remove um campo personalizado que não faz mais sentido, e reordena os campos
restantes de uma seção arrastando/movendo-os para a posição desejada. A ordem no editor passa
a ser a mesma ordem exibida ao público.

**Why this priority**: completa o conjunto "tudo que um editor de formulários pode
proporcionar", mas é o menos crítico dos três — os formulários já funcionam plenamente sem
essa capacidade, ela só refina a organização.

**Independent Test**: reordenar dois campos de uma seção pelo painel; abrir o formulário
público e confirmar a nova ordem. Remover um campo personalizado; confirmar que ele some do
formulário público e que respostas já enviadas antes da remoção continuam mostrando o valor
que tinham naquele campo.

**Acceptance Scenarios**:

1. **Given** dois campos numa seção, **When** o SUPERADMIN inverte a ordem entre eles pelo
   painel, **Then** o formulário público passa a exibi-los na nova ordem.
2. **Given** um campo personalizado, **When** o SUPERADMIN o remove, **Then** ele deixa de
   aparecer no formulário público, mas respostas já enviadas antes da remoção continuam
   íntegras e visíveis no banco de respostas com o valor que foi preenchido.
3. **Given** um campo fixo do sistema (nome, telefone, data do evento — usados por outras
   telas), **When** o SUPERADMIN tenta removê-lo, **Then** o sistema impede a remoção e explica
   por que esse campo é necessário.

### Edge Cases

- O que acontece se o SUPERADMIN renomear ou remover um dos campos que hoje alimentam o
  preenchimento automático de CPF/CNPJ/endereço do cliente (feature 119)? A automação não pode
  quebrar silenciosamente — precisa continuar funcionando após a edição, ou deixar claro que um
  campo necessário está ausente.
- O que acontece com uma resposta enviada antes de um campo ser removido/renomeado? Ela deve
  continuar íntegra e legível no banco de respostas, exatamente como foi preenchida.
- O que acontece se um usuário sem papel SUPERADMIN tentar acessar a edição de estrutura? Deve
  ser bloqueado (403), mantendo o acesso de visualização/gestão de respostas como já é hoje
  (COMERCIAL/FINANCEIRO/SUPERADMIN).
- O que acontece se o SUPERADMIN tentar salvar uma seção sem nenhum campo, ou um campo de
  seleção sem nenhuma opção cadastrada? A edição deve ser rejeitada com aviso claro em vez de
  gerar um formulário público quebrado.
- O que acontece se dois campos ficarem com o mesmo rótulo na mesma seção? Deve ser possível
  (rótulos podem coincidir), mas cada campo mantém identidade própria internamente, sem
  confundir respostas já salvas.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O sistema DEVE permitir que um SUPERADMIN visualize, numa tela dedicada do
  painel, a estrutura completa (seções, campos, tipo, obrigatoriedade, ordem) de cada
  formulário público (comum e corporativo), de forma independente entre os dois.
- **FR-002**: O SUPERADMIN DEVE poder editar o rótulo (texto exibido) e o texto de ajuda de
  qualquer campo existente, inclusive campos fixos do sistema, sem alterar sua identidade
  interna nem seu tipo.
- **FR-003**: O SUPERADMIN DEVE poder adicionar um campo novo a uma seção, escolhendo entre um
  conjunto de tipos suportados (texto curto, texto longo, seleção com opções, data, hora,
  telefone, e-mail, CPF, CNPJ, sim/não) e se ele é obrigatório ou opcional.
- **FR-004**: O SUPERADMIN DEVE poder remover um campo que ele mesmo adicionou. Campos fixos do
  sistema — necessários para o funcionamento de outras telas (listagem de respostas,
  associação a cliente, alerta na home, buscador de `/events/new`) — NÃO PODEM ser removidos,
  só ter texto/obrigatoriedade ajustados conforme aplicável.
- **FR-005**: O SUPERADMIN DEVE poder reordenar os campos dentro de uma seção; a ordem definida
  no editor DEVE ser a mesma ordem exibida no formulário público.
- **FR-006**: Mudanças de estrutura DEVEM valer imediatamente no próximo carregamento do
  formulário público — sem exigir novo deploy.
- **FR-007**: Alterar a estrutura de um formulário NUNCA PODE alterar ou reinterpretar
  respostas já enviadas antes da mudança — cada resposta preserva exatamente os dados como
  foram preenchidos no momento do envio.
- **FR-008**: Um campo novo marcado como obrigatório DEVE ser validado no envio do formulário
  público com o mesmo padrão já usado para os campos existentes (bloqueia envio, aviso
  amigável, sem tela de erro técnica).
- **FR-009**: Renomear ou remover um campo usado para completar automaticamente CPF/CNPJ/
  endereço do cliente (feature 119) NÃO PODE quebrar essa automação silenciosamente — a
  identificação desses campos pelo sistema deve continuar funcionando após edições de texto,
  ou o sistema deve sinalizar claramente que um campo necessário está ausente.
- **FR-010**: Somente SUPERADMIN pode editar a estrutura dos formulários. O acesso já existente
  para visualizar e gerenciar respostas (COMERCIAL/FINANCEIRO/SUPERADMIN) permanece inalterado.
- **FR-011**: O formulário público DEVE continuar utilizável em celular após qualquer edição de
  estrutura (Princípio VIII — mobile-first) — o conjunto de tipos de campo suportados é
  desenhado para caber nesse padrão em qualquer combinação.
- **FR-012**: A mensagem de WhatsApp montada no envio DEVE refletir automaticamente a estrutura
  vigente (campos, rótulos, ordem) no momento do envio, sem necessidade de alteração de código.

### Key Entities

- **Definição de campo de formulário**: representa um campo de um dos dois formulários
  públicos — a qual formulário e seção pertence, tipo, rótulo, texto de ajuda, se é
  obrigatório, opções (quando aplicável), posição/ordem, e se é um campo fixo do sistema ou
  personalizado (removível).
- **Resposta de formulário** (já existente, `FormResponse`): continua guardando o retrato
  exato dos dados preenchidos no momento do envio — não é afetada por edições de estrutura
  feitas depois.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Um SUPERADMIN consegue editar texto/obrigatoriedade de um campo, ou adicionar um
  campo novo, e ver o resultado no formulário público em menos de 2 minutos, sem precisar de
  deploy.
- **SC-002**: 100% das respostas enviadas antes de uma edição de estrutura permanecem íntegras
  e legíveis no banco de respostas depois da edição.
- **SC-003**: 100% dos campos novos marcados como obrigatórios bloqueiam o envio quando
  deixados em branco, no mesmo padrão dos campos que já existiam antes desta feature.
- **SC-004**: O preenchimento automático de CPF/CNPJ/endereço do cliente (feature 119) continua
  funcionando corretamente para respostas enviadas depois de edições de estrutura nos campos
  correspondentes.

## Assumptions

- Esta feature cobre a edição da estrutura dos dois formulários públicos **já existentes**
  (comum e corporativo) — criar formulários novos do zero (outro tipo, outra URL pública) fica
  fora de escopo, como evolução futura.
- O conjunto de tipos de campo suportados é fixo e limitado ao já necessário hoje (texto curto,
  texto longo, seleção, data, hora, telefone, e-mail, CPF, CNPJ, sim/não) — não inclui
  validações personalizadas livres ou lógica condicional entre campos (mostrar/esconder campo
  conforme resposta de outro).
- "Campos fixos do sistema" (nome do contratante/responsável, WhatsApp, data e hora do evento,
  e os campos usados pela automação de CPF/CNPJ/endereço) continuam existindo sempre — só têm
  texto e obrigatoriedade editáveis, nunca são removíveis, porque outras partes do sistema
  (listagem de respostas, alerta na home, buscador de `/events/new`, feature 119) dependem
  deles.
- O reordenamento de **seções inteiras** (não só campos dentro de uma seção) é desejável mas
  não obrigatório nesta versão — a prioridade é reordenar campos dentro da seção onde estão.
- O título da mensagem de WhatsApp de cada formulário ("INFORMAÇÕES PARA PRÉ-CONTRATO —
  MANTO PRODUÇÕES" / "CONTRATO CORPORATIVO — MANTO PRODUÇÕES") permanece fixo nesta versão —
  não é um campo editável pelo editor.
- Apenas SUPERADMIN edita estrutura, seguindo o mesmo padrão já adotado para outras edições
  sensíveis do sistema (ex.: CPF de talento).
