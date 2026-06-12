# Feature Specification: Controle de vendas, descontos e pagamentos recebidos

**Feature Branch**: `040-vendas-pagamentos`

**Created**: 2026-06-12

**Status**: Draft

**Input**: User description: "Valor do contrato é inútil — tirar. Preciso de valor final antes de
desconto e valor de venda final (o que a cliente pagou); a diferença vira relatório de desconto no
painel financeiro. Comprovante: digitar o valor deve ser obrigatório. Super admin pode editar e
excluir comprovantes e contratos. Conta: valor final de venda − soma dos valores recebidos com
comprovante = eventos faltando pagamento. Política: à vista, ou 50% no ato + 50% até 2 dias antes
do evento. Criar avisos na home do comercial para eventos com recebido < venda. Nova forma de
pagamento 'pagamento futuro' com data, que também gera aviso na home do comercial."

## Contexto

Na seção Comercial do evento hoje:
- O upload de contrato pede um "Valor do contrato" que ninguém usa (o valor real da venda já fica
  em "Dados da venda").
- Só existe um "Valor de venda"; não há onde registrar o preço cheio (antes do desconto), então a
  empresa não sabe quanto deu de desconto em um período.
- O comprovante de pagamento pode ser anexado sem valor — aí a soma dos recebidos fica errada e não
  dá para saber se o evento está quitado.
- Contratos e comprovantes não podem ser corrigidos nem removidos (nem por engano).
- Não existe nenhum aviso de cobrança: eventos chegam na data sem o pagamento completo e ninguém vê.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Preço cheio × valor final (desconto) (Priority: P1)

A vendedora registra no evento o **valor antes do desconto** (preço cheio) e o **valor de venda
final** (o que a cliente de fato pagou). O painel financeiro mostra quanto foi dado de desconto no
período.

**Acceptance Scenarios**:

1. **Given** um evento, **When** a vendedora preenche "Valor antes do desconto" R$ 3.000 e "Valor de
   venda final" R$ 2.625, **Then** os dois valores ficam salvos e a tela mostra o desconto de R$ 375.
2. **Given** eventos com desconto no período, **When** o financeiro abre o dashboard, **Then** vê o
   total de descontos concedidos no período (e o % sobre o preço cheio).
3. **Given** um evento sem preço cheio preenchido, **Then** nada de desconto é mostrado (sem erro).

---

### User Story 2 - Contrato sem valor; comprovante com valor obrigatório (Priority: P1)

O formulário de contrato deixa de pedir valor (só arquivo). O formulário de comprovante exige o
valor recebido — sem valor, o pagamento não é adicionado.

**Acceptance Scenarios**:

1. **Given** o formulário de contrato, **Then** não existe mais campo "Valor do contrato"; basta o
   arquivo.
2. **Given** o formulário de comprovante sem valor digitado (ou valor 0), **When** envia, **Then** o
   pagamento NÃO é gravado e aparece aviso claro pedindo o valor.
3. **Given** comprovante com arquivo e valor, **When** envia, **Then** o pagamento é gravado e
   aparece confirmação.

---

### User Story 3 - Super admin corrige e exclui (Priority: P2)

O super admin pode editar o valor de um comprovante e excluir comprovantes e contratos enviados por
engano. Demais perfis não veem essas ações.

**Acceptance Scenarios**:

1. **Given** um comprovante com valor errado, **When** o super admin edita o valor, **Then** o valor
   é atualizado e a soma de recebidos reflete a correção.
2. **Given** um contrato/comprovante duplicado, **When** o super admin exclui (com confirmação),
   **Then** o registro some da lista.
3. **Given** um usuário comercial (não super admin), **Then** os botões de editar/excluir não
   aparecem e a ação é recusada no servidor se forçada.

---

### User Story 4 - Avisos de cobrança na home do comercial (Priority: P1)

A home mostra ao setor comercial os eventos com pagamento incompleto
(**valor de venda final − soma dos comprovantes anexados > 0**), seguindo a política da empresa:
à vista, ou 50% no ato do contrato + 50% até 2 dias antes do evento.

**Acceptance Scenarios**:

1. **Given** um evento daqui a 10 dias com venda R$ 2.000 e nenhum comprovante, **Then** aparece na
   home como "sinal pendente" (recebido < 50%).
2. **Given** um evento daqui a 1 dia com venda R$ 2.000 e R$ 1.000 recebidos, **Then** aparece como
   **URGENTE** (faltam ≤ 2 dias e recebido < total).
3. **Given** um evento já realizado com saldo em aberto, **Then** continua na home como urgente até
   quitar.
4. **Given** um evento quitado (recebido ≥ venda), **Then** não aparece em nenhum aviso.
5. **Given** um evento com ≥ 50% recebido e faltando > 2 dias, **Then** não gera aviso (dentro da
   política).

---

### User Story 5 - Forma de pagamento "Futuro" com data (Priority: P1)

Nova forma de pagamento **"Pagamento futuro"**: a vendedora informa a data combinada. Eventos assim
não seguem a régua 50/50 — o aviso na home usa a data combinada (vencido = urgente).

**Acceptance Scenarios**:

1. **Given** a forma "Pagamento futuro" selecionada, **Then** o campo de data combinada aparece e é
   obrigatório para salvar a forma.
2. **Given** um evento "pagamento futuro" com data daqui a 10 dias e saldo em aberto, **Then**
   aparece na home como informativo, com a data.
3. **Given** a data combinada já passada e saldo em aberto, **Then** o aviso vira urgente.
4. **Given** evento "pagamento futuro" quitado, **Then** não gera aviso.

---

### Edge Cases

- Evento sem valor de venda preenchido: não entra nos avisos de cobrança.
- "Valor antes do desconto" menor que o valor final: desconto não é mostrado (tratado como sem
  desconto; valores ficam salvos como digitados).
- Comprovante sem arquivo: continua recusado (regra atual mantida), agora com aviso claro.
- "Faturado" já tem data de vencimento: passa a usar a mesma régua do "pagamento futuro" nos avisos
  (data combinada), em vez da régua 50/50.
- Edição/exclusão fica registrada no log de atividades do evento.
- Excluir um contrato/comprovante remove o registro da lista; o arquivo permanece no armazenamento
  (sem risco de quebrar outro registro que aponte para o mesmo arquivo).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O formulário de contrato MUST conter apenas o arquivo (campo "Valor do contrato"
  removido da tela; valores antigos deixam de ser exibidos).
- **FR-002**: O evento MUST ter "Valor antes do desconto" e "Valor de venda final" editáveis na
  seção Comercial; o desconto (diferença, quando positiva) MUST ser visível no evento.
- **FR-003**: O dashboard financeiro MUST mostrar o total de descontos concedidos no período
  filtrado e o % médio sobre o preço cheio.
- **FR-004**: Adicionar comprovante MUST exigir valor (> 0) e arquivo; recusas mostram aviso claro,
  sucesso mostra confirmação.
- **FR-005**: Apenas o super admin MUST poder editar valor e excluir contratos/comprovantes, com
  confirmação antes de excluir; toda edição/exclusão MUST ir para o log do evento.
- **FR-006**: O sistema MUST calcular por evento: saldo = valor de venda final − soma dos valores
  dos comprovantes; o evento MUST exibir recebido/saldo (quitado quando saldo ≤ 0).
- **FR-007**: A home MUST mostrar ao comercial (e financeiro/super admin) os eventos com saldo em
  aberto: urgente quando faltam ≤ 2 dias (ou evento passado); sinal pendente quando recebido < 50%.
- **FR-008**: Forma de pagamento "Pagamento futuro" MUST existir com data combinada obrigatória;
  eventos "futuro" (e "faturado", que já tem data) MUST gerar aviso pela data combinada: informativo
  antes, urgente quando vencida — sempre só com saldo em aberto.

### Key Entities

- **Evento** — ganha uso do preço cheio (já existente) e da forma "futuro"; saldo derivado dos
  comprovantes.
- **Contrato** — arquivo anexado ao evento; sem valor na tela.
- **Comprovante (pagamento recebido)** — arquivo + valor obrigatório; soma define o saldo.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 0 comprovantes novos sem valor.
- **SC-002**: 100% dos eventos com saldo em aberto e dentro da régua (≤ 2 dias, < 50%, ou data
  combinada vencida/futura) aparecem na home do comercial.
- **SC-003**: O financeiro consegue ver o total de descontos de um período em uma única tela.
- **SC-004**: Apenas super admin consegue editar/excluir contratos e comprovantes (0 ações de outros
  perfis aceitas no servidor).

## Assumptions

- "Valor de venda final" é o campo de venda já existente (usado em comissão/lucro/dashboard) — o
  novo campo é o preço cheio antes do desconto, que já existe no banco (usado na criação de evento
  pela plataforma) e agora passa a ser editável na seção Comercial e usado no relatório.
- O campo de valor do contrato continua existindo no banco (dados antigos preservados); apenas sai
  da interface.
- "Editar" comprovante = corrigir o valor (trocar arquivo = excluir + adicionar de novo).
- Avisos consideram eventos a partir da data de corte já usada na home (release date), excluindo
  ensaios; eventos sem valor de venda não entram.
- "Faturado" adota a régua da data combinada (igual ao "futuro") por já ter data de vencimento.
- Sem mudança de banco (colunas necessárias já existem).
