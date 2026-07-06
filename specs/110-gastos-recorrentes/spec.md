# Feature Specification: Gastos Recorrentes

**Feature Branch**: `110-gastos-recorrentes`

**Created**: 2026-07-06

**Status**: Draft

**Input**: User description: "Preciso de uma parte parecida com a de gastos extras, porém é mais para cadastrar gastos recorrentes. Como Conta de Luz, água, gás, advogado. E isso gera alertas na página principal como financeiro. De água eu sei que gasto entre x e y todo mês. Eu só consigo inserir o pix e valor exato quando recebo a conta. De advogado eu sempre tenho que pagar a mesma coisa, mas isso já está como débito automático, ou seja, não precisa ser pago, apenas registrado. Tenho diversas assinaturas que estão em cartão de crédito e também preciso apenas organizá-las. Acho que é uma extensão da seção de gastos extras."

## Clarificações (respondidas pelo usuário em 2026-07-06)

1. **Alerta de conta variável**: dia esperado configurável por conta — o alerta aparece na
   home a partir desse dia até a conta do mês ser preenchida e paga.
2. **Pagamento**: conta variável preenchida (valor + PIX) entra na planilha de Pagamentos do
   financeiro, no mesmo fluxo dos demais itens (PIX copiável, marcar pago).
3. **Balanço**: débito automático e assinaturas geram lançamento mensal automático (já
   "registrado", sem ação de pagamento) que compõe as despesas do mês no painel financeiro.
4. **Acesso**: FINANCEIRO + SUPERADMIN.

## Contexto

Os gastos extras (`/gastos/`) cobrem despesas pontuais (compra de material, manutenção),
com fluxo de aprovação. Contas fixas da empresa — luz, água, gás, advogado, assinaturas —
não têm onde morar: repetem todo mês, não precisam de aprovação, e cada tipo se comporta
diferente:

- **Conta variável** (luz/água/gás): valor muda dentro de uma faixa conhecida; o PIX e o
  valor exato só existem quando a conta chega. Precisa de lembrete para não esquecer e de
  entrada no fluxo de pagamento.
- **Débito automático** (advogado): valor fixo, debitado sozinho — ninguém precisa pagar
  nada, mas o custo precisa aparecer no balanço mensal.
- **Assinatura em cartão** (softwares, serviços): valor fixo no cartão de crédito — idem:
  só organizar e compor o custo mensal.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Conta variável: alerta, preenchimento e pagamento (Priority: P1)

O financeiro cadastra "Conta de Luz" como gasto recorrente variável: faixa esperada (ex.:
R$ 400–600) e dia esperado da conta (ex.: dia 10). A partir do dia 10, a home mostra um
alerta ao time financeiro: "Conta de Luz aguardando valor". Quando a conta chega, o
financeiro preenche valor exato, PIX e vencimento — o alerta muda para "a pagar" e o item
aparece na planilha de Pagamentos do mês com PIX copiável. Ao marcar como pago (na planilha
ou na tela de recorrentes), o alerta some até o mês seguinte.

**Why this priority**: é o caso que gera esquecimento e multa hoje — o pedido central
("alertas na página principal").

**Independent Test**: cadastrar conta variável com dia esperado ≤ hoje; ver alerta na home;
preencher valor+PIX; ver item na planilha de Pagamentos; marcar pago; alerta some.

**Acceptance Scenarios**:

1. **Given** uma conta variável com dia esperado 10 e sem valor preenchido no mês, **When**
   um usuário FINANCEIRO/SUPERADMIN abre a home no dia 10 ou depois, **Then** vê um alerta
   com o nome da conta e a faixa esperada.
2. **Given** o alerta ativo, **When** o financeiro preenche valor exato + PIX (+ vencimento
   opcional), **Then** o lançamento do mês vira "a pagar" e aparece na planilha de
   Pagamentos com o PIX copiável.
3. **Given** o lançamento "a pagar", **When** marcado como pago, **Then** sai dos alertas da
   home e fica registrado no histórico do mês.
4. **Given** um mês novo, **When** vira o mês, **Then** a conta volta ao estado "aguardando
   valor" (novo ciclo), sem apagar o histórico dos meses anteriores.
5. **Given** um usuário sem papel FINANCEIRO/SUPERADMIN, **When** abre a home ou a tela de
   recorrentes, **Then** não vê alertas nem a tela (403).

---

### User Story 2 - Débito automático e assinaturas: registro automático no balanço (Priority: P2)

O financeiro cadastra "Advogado" como débito automático (valor fixo, dia do débito) e as
assinaturas de cartão (nome, valor, cartão, dia da cobrança). Todo mês o sistema registra
sozinho o lançamento desses gastos — já como "registrado", sem pedir nenhuma ação — e o
painel financeiro passa a incluir esses valores nas despesas do mês.

**Why this priority**: elimina digitação repetitiva e faz o balanço refletir o custo fixo
real; mas sem isso o P1 já entrega o valor principal (alertas + pagamento).

**Independent Test**: cadastrar um débito automático e uma assinatura; abrir o painel
financeiro do mês corrente e confirmar que as despesas incluem os dois valores; confirmar
que não aparecem como pendência em alerta nem na planilha de Pagamentos.

**Acceptance Scenarios**:

1. **Given** um débito automático ativo de R$ 1.000, **When** o mês corrente é consultado
   (painel financeiro/tela de recorrentes), **Then** existe um lançamento do mês de
   R$ 1.000 marcado como "registrado" criado automaticamente.
2. **Given** lançamentos automáticos do mês, **When** o financeiro abre o painel financeiro,
   **Then** as despesas do mês incluem a soma dos gastos recorrentes do mês.
3. **Given** um débito automático/assinatura, **When** a home ou a planilha de Pagamentos é
   aberta, **Then** eles NÃO aparecem como pendência (não há nada a pagar manualmente).
4. **Given** uma assinatura desativada, **When** vira o mês, **Then** nenhum lançamento novo
   é criado para ela (histórico antigo preservado).

---

### User Story 3 - Organizar o cadastro de recorrentes (Priority: P3)

O financeiro abre a tela de gastos recorrentes e vê todas as contas cadastradas agrupadas
por tipo (variáveis, débito automático, assinaturas), com valor/faixa, dia, cartão (quando
houver) e status do mês corrente. Pode cadastrar, editar, desativar e reativar contas, e
consultar o histórico de lançamentos de cada uma.

**Why this priority**: organização e manutenção do cadastro — necessária, mas serve às
outras duas histórias.

**Independent Test**: criar, editar, desativar e reativar uma conta de cada tipo; conferir
lista agrupada e histórico.

**Acceptance Scenarios**:

1. **Given** contas cadastradas dos três tipos, **When** o financeiro abre a tela de
   recorrentes, **Then** vê as contas agrupadas por tipo com os dados principais e a soma
   mensal estimada.
2. **Given** uma conta, **When** editada (valor, faixa, dia, PIX padrão, cartão), **Then**
   os lançamentos FUTUROS refletem a mudança; os já criados não mudam.
3. **Given** uma conta desativada, **When** listada, **Then** aparece como inativa e para de
   gerar alertas/lançamentos.

---

### Edge Cases

- Conta variável cujo valor chega fora da faixa esperada (x–y): o sistema aceita (a faixa é
  referência, não trava), mas destaca visualmente que saiu da faixa.
- Mês em que a conta variável não veio (ex.: gás bimestral): o financeiro pode "pular o mês"
  — o alerta some sem criar pagamento e o histórico registra o pulo.
- Dia esperado 29/30/31 em mês mais curto: o alerta dispara no último dia do mês.
- Conta criada no meio do mês, depois do dia esperado: o alerta do mês corrente dispara
  imediatamente (não espera o mês seguinte).
- Lançamento de mês anterior nunca preenchido: continua visível como pendência em aberto no
  histórico, mas o alerta da home é sempre do mês corrente (não acumula alertas antigos).
- Exclusão de conta com histórico: não permitida — desativar em vez de excluir (histórico
  compõe balanços passados). Conta sem nenhum lançamento pode ser excluída.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O sistema DEVE permitir cadastrar gastos recorrentes de três tipos: conta
  variável (faixa min–max + dia esperado), débito automático (valor fixo + dia do débito) e
  assinatura em cartão (valor fixo + dia da cobrança + identificação do cartão).
- **FR-002**: Acesso (ver, cadastrar, editar, preencher, marcar pago) restrito a usuários
  FINANCEIRO e SUPERADMIN; demais papéis não veem alertas nem a tela.
- **FR-003**: Para contas variáveis, a home DEVE exibir alerta ao time financeiro a partir
  do dia esperado da conta até o lançamento do mês ser pago (estados: "aguardando valor" →
  "a pagar" → some quando pago). O alerta refere-se sempre ao mês corrente.
- **FR-004**: O financeiro DEVE poder preencher o lançamento do mês de uma conta variável
  com valor exato, PIX e vencimento opcional; o lançamento preenchido DEVE entrar na
  planilha de Pagamentos do financeiro com PIX copiável e marcação de pago.
- **FR-005**: Débitos automáticos e assinaturas DEVEM gerar lançamento mensal
  automaticamente (valor fixo cadastrado, estado "registrado"), sem aparecer como pendência
  de pagamento em nenhuma tela.
- **FR-006**: O painel financeiro DEVE incluir os lançamentos recorrentes do período
  (variáveis preenchidas + fixos registrados) nas despesas do mês.
- **FR-007**: O sistema DEVE manter histórico mensal por conta (valor, estado, quem
  preencheu/pagou e quando), preservado ao editar ou desativar a conta.
- **FR-008**: Contas DEVEM poder ser desativadas/reativadas; desativada não gera alerta nem
  lançamento novo. Exclusão só é permitida para conta sem lançamentos.
- **FR-009**: O financeiro DEVE poder pular o mês de uma conta variável (conta não veio),
  encerrando o alerta do mês sem gerar pagamento.
- **FR-010**: Valor preenchido fora da faixa esperada DEVE ser aceito com destaque visual de
  "fora da faixa".
- **FR-011**: Os gastos extras existentes (`/gastos/`) NÃO PODEM mudar de comportamento.

### Key Entities

- **Gasto recorrente (cadastro)**: nome, tipo (variável | débito automático | assinatura),
  faixa esperada (min–max) OU valor fixo, dia (esperado/débito/cobrança), PIX padrão
  (opcional), cartão (assinaturas), observações, ativo/inativo, autor.
- **Lançamento mensal**: referência ao cadastro + mês (um por conta/mês), valor, PIX,
  vencimento, estado ("aguardando valor" implícito pela ausência | "a_pagar" | "pago" |
  "registrado" | "pulado"), quem/quando preencheu e pagou.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% das contas variáveis com dia esperado atingido e mês não resolvido geram
  alerta visível na home para FINANCEIRO/SUPERADMIN.
- **SC-002**: Preencher uma conta variável (valor + PIX) leva no máximo 3 cliques a partir
  do alerta da home, e o item aparece na planilha de Pagamentos imediatamente.
- **SC-003**: 100% dos débitos automáticos/assinaturas ativos têm lançamento do mês criado
  automaticamente, sem nenhuma ação manual, e compõem as despesas do painel financeiro.
- **SC-004**: Nenhum débito automático/assinatura aparece como pendência de pagamento em
  qualquer tela (0 casos nos testes).
- **SC-005**: Usuários sem papel financeiro não encontram alertas nem a tela de recorrentes
  em nenhuma navegação (0 vazamentos nos testes de RBAC).
- **SC-006**: O fluxo de gastos extras existente permanece idêntico (verificação de
  regressão passa em 100% dos casos testados).

## Assumptions

- "Página principal como financeiro" = home dashboard (`/`), num bloco de alertas visível
  apenas para FINANCEIRO/SUPERADMIN — não é uma página nova.
- Lançamentos fixos (débito automático/assinatura) nascem "registrados" no mês corrente por
  geração automática ao usar o sistema (sem necessidade de tarefa agendada externa) — mesmo
  padrão dos salários mensais já existentes.
- Competência do lançamento = mês de referência (um lançamento por conta por mês).
- Assinaturas em dólar/valor variável de cartão ficam fora do escopo: valor fixo em R$
  (editável a qualquer momento).
- Recorrentes não passam por aprovação (diferente dos gastos extras): quem cadastra já é o
  financeiro.
- Sem anexo de nota fiscal obrigatório nos recorrentes (a conta/fatura fica fora do sistema
  por ora; campo de observações cobre referências).
