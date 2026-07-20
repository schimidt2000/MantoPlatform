# Feature Specification: Reembolsos de Despesas do Evento

**Feature Branch**: `136-reembolsos-evento`

**Created**: 2026-07-17

**Status**: Draft

**Input**: "Ao criar um evento, o comercial pode marcar que o evento terá um reembolso. Seja
de bagagens, alimentação ou qualquer outra coisa. Na página do evento depois podemos ver
os reembolsos pendentes, ou adicionar manualmente. Exemplo: 1200 reais de bagagem, com
nota fiscal anexada. Aí aparece na home como função do comercial cobrar os reembolsos. Aí
dá para anexar comprovante e colocar o valor, da mesma forma que funciona a parte de
adicionar pagamentos, para esses reembolsos. E também deve ter um botão na aba de tools de
cobrar os reembolsos."

## Contexto

Às vezes a Manto adianta um gasto durante um evento por conta da cliente (ex.: excesso de
bagagem de um voo, alimentação extra) e depois precisa cobrar esse valor de volta dela —
separado do valor de venda do evento, que já tem seu próprio fluxo de cobrança. Hoje não
existe nenhum lugar no sistema para registrar "isso aqui a cliente ainda me deve", nem uma
forma de a comercial lembrar de cobrar e confirmar quando recebeu.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Registrar um reembolso a cobrar (Priority: P1)

Ao criar um evento, a comercial marca que vai haver um reembolso e já registra o que for
(ex.: "Bagagem", R$ 1.200,00, nota fiscal anexada). Se preferir, pode pular esse passo na
criação e registrar depois, direto na página do evento — inclusive mais de um reembolso
por evento.

**Why this priority**: sem um jeito de registrar o reembolso, não existe nada para cobrar
depois — é a base de todo o resto.

**Independent Test**: criar um evento marcando um reembolso com descrição e valor, e
confirmar que ele aparece na página do evento como pendente. Depois, numa página de evento
já existente, adicionar um reembolso manualmente e confirmar que também aparece.

**Acceptance Scenarios**:

1. **Given** a tela de criar evento, **When** a comercial marca que haverá reembolso e
   preenche descrição e valor, **Then** o evento é criado já com esse reembolso registrado
   como pendente.
2. **Given** a tela de criar evento, **When** a comercial não marca reembolso nenhum,
   **Then** o evento é criado normalmente, sem nenhum reembolso associado.
3. **Given** a página de um evento já existente, **When** a comercial adiciona um
   reembolso manualmente (descrição, valor, nota fiscal opcional), **Then** ele aparece na
   lista de reembolsos daquele evento como pendente.
4. **Given** um evento, **When** a comercial adiciona mais de um reembolso, **Then** todos
   aparecem separadamente na lista, cada um com sua própria descrição e valor.

### User Story 2 - Cobrar e confirmar o recebimento do reembolso (Priority: P1)

A comercial usa o botão de cobrar reembolsos (na página do evento, dentro das
ferramentas) para copiar uma mensagem pronta e enviar à cliente. Quando a cliente
reembolsa, a comercial marca o reembolso como cobrado, anexando o comprovante e
confirmando o valor recebido — do mesmo jeito que já funciona para os pagamentos do valor
de venda.

**Why this priority**: fechar o ciclo (cobrar → confirmar recebido) é o que dá valor
prático ao registro — sem isso, o reembolso fica pendente para sempre mesmo depois de
pago.

**Independent Test**: com um reembolso pendente, clicar no botão de cobrar reembolsos e
conferir que o texto copiado lista o reembolso e o valor; depois, marcar esse reembolso
como cobrado anexando um comprovante e um valor, e conferir que ele passa a aparecer como
cobrado, com o comprovante acessível.

**Acceptance Scenarios**:

1. **Given** um evento com pelo menos um reembolso pendente, **When** a comercial abre o
   menu de ferramentas do evento, **Then** vê um botão para cobrar os reembolsos.
2. **Given** o botão de cobrar reembolsos, **When** a comercial clica nele, **Then** uma
   mensagem é copiada para a área de transferência listando os reembolsos pendentes
   daquele evento e o valor total.
3. **Given** um evento sem nenhum reembolso pendente, **When** a comercial olha o menu de
   ferramentas, **Then** o botão de cobrar reembolsos aparece desabilitado (mesmo padrão
   já usado pelo botão de Cobrança quando não há nada em aberto).
4. **Given** um reembolso pendente, **When** a comercial anexa o comprovante e confirma o
   valor recebido, **Then** o reembolso passa a aparecer como cobrado, com a data e o
   comprovante visíveis.

### User Story 3 - Ver os reembolsos pendentes na home (Priority: P2)

Alguém da comercial abre a home do sistema e vê, junto das demais pendências comerciais,
quais reembolsos ainda precisam ser cobrados — de qualquer evento, não só do que está
olhando no momento.

**Why this priority**: é o que transforma "um registro perdido na página de um evento
específico" em algo que a comercial realmente lembra de fazer — mas só faz sentido depois
que já existem reembolsos registrados (User Story 1) e um jeito de cobrá-los (User Story
2).

**Independent Test**: com reembolsos pendentes em eventos diferentes, abrir a home e
conferir que todos aparecem juntos na área comercial, cada um levando para a página do
evento correspondente.

**Acceptance Scenarios**:

1. **Given** reembolsos pendentes em um ou mais eventos, **When** alguém da comercial abre
   a home, **Then** vê uma lista desses reembolsos, com o evento, a descrição e o valor de
   cada um.
2. **Given** nenhum reembolso pendente em todo o sistema, **When** alguém da comercial
   abre a home, **Then** essa lista simplesmente não aparece (sem afetar as demais
   pendências comerciais já existentes).
3. **Given** um reembolso pendente na home, **When** a comercial clica para abrir o
   evento, **Then** vai direto para a página daquele evento.

### Edge Cases

- Um reembolso marcado como cobrado não pode ser "descobrado" por engano — reverter esse
  estado (se necessário) é uma operação sensível, tratada como as demais edições
  financeiras sensíveis do sistema (restrita a quem já pode editar/excluir comprovantes de
  pagamento hoje).
- Excluir um evento que tem reembolsos registrados (cobrados ou não) não pode falhar por
  causa desses registros — eles são removidos junto, como já acontece com contratos e
  comprovantes de pagamento.
- Um evento pode ter zero, um ou vários reembolsos — a lista e a mensagem de cobrança
  precisam funcionar igual em qualquer um desses casos.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Ao criar um evento, DEVE ser possível marcar que ele terá um reembolso e
  registrar sua descrição e valor nesse mesmo passo (opcional — pular não impede criar o
  evento).
- **FR-002**: Na página de um evento, DEVE ser possível adicionar um reembolso manualmente
  a qualquer momento (descrição, valor obrigatórios; nota fiscal do gasto original
  opcional), inclusive mais de um por evento.
- **FR-003**: A página do evento DEVE mostrar a lista de reembolsos daquele evento, com
  descrição, valor e se já foi cobrado ou está pendente.
- **FR-004**: DEVE ser possível marcar um reembolso pendente como cobrado, anexando um
  comprovante e confirmando o valor recebido — mesma mecânica já usada para registrar
  pagamentos do valor de venda (valor + arquivo).
- **FR-005**: Um reembolso já marcado como cobrado DEVE mostrar a data em que foi cobrado
  e um link para o comprovante.
- **FR-006**: A página do evento DEVE ter um botão (nas ferramentas do evento) que copia
  uma mensagem pronta cobrando os reembolsos pendentes daquele evento, com a lista e o
  valor total.
- **FR-007**: Esse botão de cobrar reembolsos DEVE ficar desabilitado quando não houver
  nenhum reembolso pendente naquele evento.
- **FR-008**: A home do sistema DEVE mostrar, na área de pendências comerciais, os
  reembolsos ainda não cobrados de qualquer evento, cada um levando para a página do
  evento correspondente.
- **FR-009**: Quando não houver nenhum reembolso pendente, essa lista na home não deve
  aparecer nem quebrar a exibição das demais pendências.
- **FR-010**: Excluir um evento DEVE remover também os reembolsos registrados nele, sem
  falhar por causa desses registros.
- **FR-011**: O acesso para ver/adicionar/cobrar reembolsos segue a mesma regra de
  permissão já usada hoje para a área comercial da página do evento (comprovantes de
  pagamento, cobrança).

### Key Entities

- **Reembolso**: um valor que a Manto adiantou durante um evento e precisa cobrar de
  volta da cliente. Pertence a um evento; tem descrição (livre — bagagem, alimentação,
  etc.), valor a cobrar, opcionalmente a nota fiscal do gasto original, e — quando
  cobrado — data, valor recebido e comprovante do reembolso.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Todo reembolso registrado (na criação do evento ou manualmente depois)
  aparece corretamente na página do evento e na home enquanto estiver pendente.
- **SC-002**: A comercial consegue cobrar um reembolso e confirmar seu recebimento sem
  sair da página do evento.
- **SC-003**: Depois de marcado como cobrado, um reembolso não aparece mais como pendência
  na home nem no botão de cobrança daquele evento.

## Assumptions

- "Marcar como cobrado" não tem um caminho de reverter pela interface nesta primeira
  versão — é uma decisão consistente com o restante do módulo financeiro (edições
  sensíveis já dependem de quem tem acesso mais amplo); se precisar desfazer, por ora é
  ajuste direto no banco, como já acontece hoje com correções financeiras raras.
- O reembolso é sempre associado a um evento específico — não existe reembolso "solto",
  sem evento.
- Igual aos comprovantes de pagamento existentes, o comprovante do reembolso recebido
  fica salvo dentro do próprio sistema (não é reenviado nem gerado automaticamente).
