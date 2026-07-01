# Feature Specification: Tipos de acréscimo configuráveis, redesign do editor e múltiplos clientes por evento

**Feature Branch**: `100-multi-cliente-acrescimos-config`

**Created**: 2026-07-01

**Status**: Draft

**Input**: "Deixe as opções da lista de acréscimos configuráveis na página de configurações de preços. Melhore o design da parte de adicionar acréscimos (ficou feio e não intuitivo). E na associação de clientes a evento: preciso associar mais de um cliente a cada evento, podendo dizer se é assessora, contratante, mãe/pai, familiar ou outros."

## Contexto

Três ajustes sobre features recentes:

1. **Tipos de acréscimo configuráveis**: a lista de tipos de acréscimo (feature 099) é hoje **fixa no
   código**. Precisa ser **editável na página de Configurações de Preços**, como os demais parâmetros.
2. **Design do editor de acréscimos**: a UI de "adicionar acréscimo" (no orçamento e na tela comercial
   do evento) ficou **feia e pouco intuitiva** e precisa ser reformulada.
3. **Múltiplos clientes por evento**: hoje o evento associa **um único cliente** (feature 094). Precisa
   permitir **vários clientes por evento**, cada um com um **tipo de relação**: *assessora*,
   *contratante*, *mãe/pai*, *familiar* ou *outros*.

## Decisões de escopo (assumidas — ver Assumptions)

- **BV permanece um tipo especial protegido**: a lista configurável cobre os tipos **comuns**; **BV** e
  **Outro** continuam sempre disponíveis (BV é protegido por causa da regra financeira de repasse).
- **Tipos de relação de cliente** são uma **lista fixa** (assessora, contratante, mãe/pai, familiar,
  outros) — não configurável nesta entrega.
- **Compatibilidade de clientes**: o vínculo único atual (um cliente por evento) é **migrado** para a
  nova associação (como "contratante"); nenhum vínculo existente é perdido.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Múltiplos clientes por evento com tipo de relação (Priority: P1) 🎯 MVP

Como vendedor/financeiro, na tela comercial do evento, quero **associar mais de um cliente** ao evento e
**marcar o tipo de relação** de cada um (assessora, contratante, mãe/pai, familiar, outros), para
registrar corretamente todas as pessoas envolvidas.

**Why this priority**: É a mudança de maior valor e a única com modelo de dados novo; as outras duas são
melhorias sobre o que já existe.

**Independent Test**: Em um evento, associar dois clientes com relações diferentes, salvar, reabrir e ver
os dois listados com suas relações; conferir que cada um aparece na sua ficha de cliente.

**Acceptance Scenarios**:

1. **Given** a tela comercial do evento, **When** adiciono um cliente e escolho a relação, **Then** posso
   **adicionar outro** cliente com outra relação, e ambos são salvos.
2. **Given** um evento com dois clientes, **When** reabro a página, **Then** vejo os dois clientes e suas
   relações, podendo **remover** ou **trocar** qualquer um.
3. **Given** um cliente que ainda não existe, **When** uso a criação rápida (como hoje), **Then** ele é
   criado e associado com a relação escolhida.
4. **Given** um evento com clientes associados, **When** abro a **ficha** de qualquer um desses clientes,
   **Then** o evento aparece no histórico dele (independente da relação).
5. **Given** a regra de cliente obrigatório (feature 094), **When** salvo a venda de um evento elegível,
   **Then** é exigido **ao menos um** cliente associado (qualquer relação).

### User Story 2 - Tipos de acréscimo configuráveis nas configurações de preços (Priority: P2)

Como administrador, quero **editar a lista de tipos de acréscimo** na página de Configurações de Preços
(adicionar, renomear, remover), para adaptar os motivos sem depender de código.

**Why this priority**: Autonomia de configuração; depende só de mover a lista para as configurações.

**Independent Test**: Nas configurações, adicionar um tipo novo e remover um existente; abrir o orçamento/
evento e ver a lista de tipos refletindo a mudança; **BV** e **Outro** continuam presentes.

**Acceptance Scenarios**:

1. **Given** a página de Configurações de Preços, **When** abro a seção de tipos de acréscimo, **Then**
   vejo a lista atual e posso **adicionar/renomear/remover** tipos comuns.
2. **Given** que salvo a lista, **When** abro o orçamento ou a tela comercial do evento, **Then** o
   seletor de tipos reflete a lista salva (mais **BV** e **Outro**).
3. **Given** a lista configurável, **When** tento remover **BV**, **Then** o sistema **não permite** (BV é
   protegido pela regra financeira); **Outro** também permanece sempre disponível.
4. **Given** acréscimos já gravados com um tipo que foi renomeado/removido, **When** eles são exibidos,
   **Then** continuam mostrando o texto com que foram salvos (sem quebrar).

### User Story 3 - Editor de acréscimos redesenhado (Priority: P2)

Como usuário, quero um editor de acréscimos **claro e intuitivo** (no orçamento e no evento), para
adicionar acréscimos sem confusão.

**Why this priority**: Melhoria de usabilidade sobre a feature 099; não muda regras, só a apresentação.

**Independent Test**: Adicionar/editar/remover acréscimos no novo editor e confirmar que continua
calculando/salvando igual, com uma aparência organizada (rótulos claros, alinhamento, R$/% evidente).

**Acceptance Scenarios**:

1. **Given** o editor redesenhado, **When** adiciono um acréscimo, **Then** os campos (tipo, valor, R$/%,
   descrição para "Outro", e PIX para BV no evento) ficam **claramente rotulados e alinhados**.
2. **Given** nenhum acréscimo, **When** vejo o editor, **Then** há um **estado vazio** com um botão claro
   de "Adicionar acréscimo".
3. **Given** o novo editor, **When** calculo/salvo, **Then** o resultado é **idêntico** ao comportamento
   atual (só a aparência muda).
4. **Given** o campo de BV, **When** seleciono BV, **Then** os campos de PIX/recebedor aparecem de forma
   destacada e compreensível.

### Edge Cases

- **Mesmo cliente duas vezes no mesmo evento**: evitar duplicar o mesmo cliente com a mesma relação
  (avisar/ignorar duplicata).
- **Remover todos os clientes** de um evento elegível ao salvar a venda: bloqueado pela regra de cliente
  obrigatório (≥1).
- **Cliente associado excluído**: ao excluir um cliente, seus vínculos com eventos são removidos com
  segurança (sem referência órfã), como já ocorre hoje.
- **Tipo de acréscimo removido das configurações**: acréscimos antigos mantêm o texto salvo; o seletor só
  oferece a lista atual + BV + Outro.
- **Migração**: cada evento que já tinha um cliente único passa a ter esse cliente na nova associação como
  "contratante".

## Requirements *(mandatory)*

### Múltiplos clientes por evento

- **FR-001**: Um evento MUST poder ter **vários clientes** associados, cada um com um **tipo de relação**
  (assessora, contratante, mãe/pai, familiar, outros).
- **FR-002**: A tela comercial do evento MUST permitir **adicionar, trocar e remover** clientes e definir
  a relação de cada um, reusando a busca e a criação rápida de clientes já existentes.
- **FR-003**: A regra de **cliente obrigatório** (feature 094) MUST passar a exigir **ao menos um** cliente
  associado (qualquer relação) ao salvar a venda de um evento elegível.
- **FR-004**: A **ficha do cliente** MUST listar todos os eventos em que ele está associado (qualquer
  relação) e a **lista de clientes** MUST contar os eventos por associação.
- **FR-005**: Os vínculos únicos existentes (um cliente por evento) MUST ser **migrados** para a nova
  associação como "contratante", sem perda.

### Tipos de acréscimo configuráveis

- **FR-006**: A página de **Configurações de Preços** MUST permitir **editar a lista de tipos de
  acréscimo** comuns (adicionar, renomear, remover).
- **FR-007**: **BV** e **Outro** MUST permanecer sempre disponíveis; **BV** MUST ser **protegido** (não
  removível) por causa da regra financeira de repasse.
- **FR-008**: Os seletores de tipo (orçamento e evento) MUST refletir a lista salva nas configurações
  (mais BV e Outro).
- **FR-009**: Acréscimos já gravados MUST continuar exibindo o texto com que foram salvos, mesmo se o
  tipo foi renomeado/removido.

### Redesign do editor de acréscimos

- **FR-010**: O editor de acréscimos (orçamento e evento) MUST ter apresentação **clara e organizada**:
  campos rotulados, alinhados, com R$/% evidente, descrição para "Outro" e destaque para os campos de BV.
- **FR-011**: O editor MUST ter um **estado vazio** com ação clara de adicionar.
- **FR-012**: O redesign MUST **preservar** o cálculo e o salvamento atuais (somente a aparência muda).

## Key Entities *(include if feature involves data)*

- **Associação Evento–Cliente**: liga um evento a um cliente com um **tipo de relação** (assessora,
  contratante, mãe/pai, familiar, outros). Um evento tem zero ou mais dessas associações; um cliente pode
  estar associado a vários eventos.
- **Evento** (existente): passa a referenciar clientes **através da associação** (em vez de um único
  `client`); a regra de cliente obrigatório passa a olhar a associação.
- **Configuração de preços** (existente, JSON): passa a guardar a **lista de tipos de acréscimo** comuns.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Um evento pode ter **≥ 2 clientes** com relações diferentes, salvos e reexibidos
  corretamente.
- **SC-002**: 100% dos vínculos de cliente existentes continuam associados após a migração (como
  "contratante").
- **SC-003**: A ficha de um cliente mostra **todos** os eventos em que ele participa, em qualquer relação.
- **SC-004**: O administrador consegue **adicionar e remover** um tipo de acréscimo nas configurações e
  ver o efeito no orçamento/evento; **BV** nunca pode ser removido.
- **SC-005**: O editor de acréscimos redesenhado calcula/salva **idêntico** ao atual (0 regressão de
  valores), com aparência organizada.

## Assumptions

- **Fonte de verdade dos clientes** passa a ser a associação; o campo único atual pode ser mantido de
  forma denormalizada apontando para o cliente "contratante" (primeiro), apenas para compatibilidade de
  telas que mostram "o cliente" do evento.
- **Tipos de relação** são uma lista fixa nesta entrega; se necessário, viram configuráveis depois.
- **Lista de tipos de acréscimo** é guardada na configuração de preços (mesmo mecanismo dos demais
  parâmetros); BV/Outro são acrescentados automaticamente e BV é protegido.
- **Redesign** é de apresentação: nenhuma mudança nas regras de cálculo (percentuais sobre o total
  pré-acréscimos) nem nas regras financeiras do BV (feature 099).
- **Permissões**: editar clientes/acréscimos segue quem já edita dados comerciais; editar a lista de
  tipos segue quem já edita as configurações de preços (super admin).
- **Escopo** = app principal (`/orcamento`, evento, `/clientes`, configurações de preços); o
  `Manto_Sales/` separado fica fora.
