# Feature Specification: RBAC, edição e "Aprovado com edições" em Gastos Extras

**Feature Branch**: `179-gastos-extras-rbac-edicao`

**Created**: 2026-07-23

**Status**: Draft

**Input**: User description: "Reestruturar a tela de Gastos Extras (/gastos, React Beta) com RBAC por papel, capacidade de edição pelo admin/financeiro, e um novo status 'Aprovado com edições'. Usuário comum vê só os próprios gastos; SUPERADMIN e FINANCEIRO têm visão gerencial completa (4 KPIs + tabela global + ações completas). Admin edita qualquer gasto; aprovar um gasto pendente com dados alterados (ou editar um já aprovado) marca 'Aprovado com edições'. Substituir formulário fixo + cards por botão '+ Novo gasto' (modal) + tabela densa. Escopo exclusivo do React Beta — Jinja legado intocado."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Colaborador comum registra e acompanha os próprios gastos (Priority: P1)

Um colaborador sem papel de gestão financeira (ex.: talento, staff de produção) registra um
gasto avulso (ex.: material de figurino comprado com recursos próprios) e depois volta à tela
para acompanhar se foi aprovado.

**Why this priority**: É o uso mais frequente da tela — todo colaborador da empresa pode
registrar um gasto, e hoje já é o fluxo existente; qualquer regressão aqui afeta o maior número
de pessoas.

**Independent Test**: Logar como um usuário sem papel SUPERADMIN/FINANCEIRO, clicar em "+ Novo
gasto", preencher e enviar; verificar que a tabela mostra apenas gastos desse usuário, com o
status atualizado, sem nenhum dado de outros colaboradores nem KPIs globais visíveis.

**Acceptance Scenarios**:

1. **Given** um colaborador comum autenticado na tela de Gastos Extras, **When** ele clica em
   "+ Novo gasto" e preenche descrição, categoria, valor, data e anexa a nota fiscal, **Then** o
   gasto aparece na tabela "Meus Gastos" com status "Pendente".
2. **Given** um colaborador comum com gastos próprios em diferentes status, **When** ele abre a
   tela, **Then** vê apenas os próprios gastos (nunca gastos de outro colaborador) e não vê
   cards de KPI globais da empresa.
3. **Given** um gasto do colaborador que foi aprovado pelo financeiro com ajuste de valor,
   **When** ele abre a tela, **Then** vê o status "Aprovado c/ edições" com um visual
   diferenciado do "Aprovado" comum.

---

### User Story 2 - Financeiro/Superadmin gerencia todos os gastos da empresa (Priority: P1)

Uma pessoa com papel FINANCEIRO ou SUPERADMIN abre a tela para revisar os gastos pendentes de
todos os colaboradores, aprovar, rejeitar, corrigir dados incorretos antes de aprovar, vincular
um gasto a um evento e acompanhar o total gasto no período.

**Why this priority**: É a visão que sustenta o controle financeiro real da empresa — sem ela,
gastos não são conferidos nem entram corretamente no cálculo de custos/DRE.

**Independent Test**: Logar como usuário com papel FINANCEIRO (sem SUPERADMIN) ou SUPERADMIN,
abrir a tela e confirmar que aparecem os 4 KPIs, a tabela com gastos de todos os colaboradores, e
que todas as ações (aprovar, rejeitar, editar, vincular evento, ver nota fiscal, excluir) estão
disponíveis em cada linha.

**Acceptance Scenarios**:

1. **Given** um usuário com papel FINANCEIRO ou SUPERADMIN, **When** ele abre a tela, **Then**
   vê 4 cards (Todos, Pendentes, Aprovados, Rejeitados) com contagem e valor total em R$ de toda
   a empresa, e a tabela lista gastos de todos os colaboradores.
2. **Given** um gasto pendente na tabela, **When** o gestor clica em "Aprovar" sem abrir o
   modal de edição, **Then** o gasto vira "Aprovado" (sem a marca de edição) imediatamente.
3. **Given** um gasto pendente com a categoria errada, **When** o gestor clica em "Editar",
   corrige a categoria e usa a ação "Salvar e Aprovar" dentro do modal, **Then** o gasto vira
   "Aprovado c/ edições" (não "Aprovado" simples), refletindo que os dados originais do
   colaborador foram ajustados.
4. **Given** um gasto já aprovado anteriormente, **When** o gestor o edita (ex.: corrige o
   valor) e salva, **Then** o gasto passa a exibir "Aprovado c/ edições", mesmo sem passar de
   novo pela ação de aprovar.
5. **Given** um gasto pendente, **When** o gestor clica em "Rejeitar", **Then** o gasto vira
   "Rejeitado", visível para o colaborador que o registrou.
6. **Given** qualquer gasto na tabela, **When** o gestor usa "Vincular evento" e escolhe uma
   data/evento, **Then** o gasto passa a mostrar o evento vinculado na coluna EVENTO.
7. **Given** qualquer gasto, **When** o gestor clica em "Excluir" e confirma, **Then** o gasto
   é removido da tabela.

---

### User Story 3 - Novo cadastro via modal centralizado, sem formulário fixo ocupando a tela (Priority: P2)

Qualquer usuário (comum ou gestor) cadastra um novo gasto por um modal acionado pelo cabeçalho,
em vez de rolar a página até um formulário fixo — a tela principal fica dedicada à tabela.

**Why this priority**: É a reestruturação visual pedida; não bloqueia o uso da tela (o
formulário atual já funciona), mas é o que torna a tela usável em alta densidade de dados.

**Independent Test**: Abrir a tela em desktop e mobile, clicar em "+ Novo gasto", confirmar que
o modal abre centralizado sobre a tabela, com todos os campos do formulário, e que ele fecha ao
cadastrar com sucesso ou ao cancelar, sem deixar a página rolada para um formulário fixo.

**Acceptance Scenarios**:

1. **Given** a tela de Gastos Extras carregada, **When** o usuário clica em "+ Novo gasto" no
   cabeçalho, **Then** um modal centralizado abre com o formulário completo (descrição,
   categoria, valor, data, forma de pagamento, vínculo a evento opcional, nota fiscal,
   observações).
2. **Given** o modal de novo gasto aberto, **When** o usuário escolhe "Reembolso a funcionário",
   "Pagamento a fornecedor" ou "Sem desembolso definido" no campo "Como será pago?", **Then** os
   campos correspondentes (funcionário/fornecedor) aparecem apenas quando relevantes.
3. **Given** o modal aberto em um celular, **When** o usuário interage com o formulário,
   **Then** todos os campos e botões continuam utilizáveis sem quebra de layout.

---

### Edge Cases

- Um gestor tenta editar um gasto já "Rejeitado" sem reconsiderar a aprovação: a edição fica
  bloqueada nesse caso — reconsiderar um gasto rejeitado exige usar "Salvar e Aprovar" no mesmo
  modal, que também aprova o gasto ao salvar.
- Um colaborador comum tenta acessar/editar um gasto de outro colaborador diretamente (ex. via
  URL/ID): o sistema nega a ação (mesma regra de hoje, mantida).
- Um gestor edita um gasto pendente sem de fato mudar nenhum valor e usa "Salvar e Aprovar": o
  gasto vira "Aprovado" simples (não "c/ edições"), pois não houve alteração real de dados.
- Um gasto sem nenhum desembolso definido ("Sem desembolso definido") é aprovado: continua sem
  aparecer nas telas que dependem de reembolso/fornecedor, igual ao comportamento atual.
- Upload de nota fiscal acima de 10MB: o sistema recusa o arquivo e mostra o alerta de tamanho
  máximo, tanto no cadastro quanto em qualquer tentativa futura de reenvio.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O sistema MUST exibir, para usuários sem papel de gestão financeira (SUPERADMIN ou
  FINANCEIRO), apenas os gastos que o próprio usuário registrou ("Meus Gastos"), sem KPIs
  globais nem dados de outros colaboradores.
- **FR-002**: O sistema MUST exibir, para usuários com papel SUPERADMIN ou FINANCEIRO, os 4
  cards de resumo (Todos, Pendentes, Aprovados, Rejeitados) com contagem e valor total em R$ de
  todos os gastos da empresa, mais a tabela completa com todos os gastos de todos os
  colaboradores.
- **FR-003**: O sistema MUST permitir que qualquer usuário autenticado registre um novo gasto
  via um botão "+ Novo gasto" que abre um formulário em modal (não mais um formulário fixo na
  página).
- **FR-004**: O sistema MUST permitir que usuários com papel SUPERADMIN ou FINANCEIRO editem
  qualquer gasto (pendente ou já decidido no histórico), alterando descrição, categoria, valor,
  data do gasto, forma de pagamento e evento vinculado.
- **FR-005**: O sistema MUST manter a ação de aprovação rápida (um clique, sem abrir o modal de
  edição) para gastos pendentes, preservando o comportamento atual.
- **FR-006**: O sistema MUST oferecer, dentro do modal de edição de um gasto pendente, uma ação
  que edita e aprova o gasto na mesma operação ("Salvar e Aprovar").
- **FR-007**: O sistema MUST marcar um gasto como "Aprovado com edições" (em vez de "Aprovado")
  sempre que a operação que resulta em status aprovado também alterar algum dado do gasto
  (descrição, categoria, valor, data, forma de pagamento) em relação ao que estava salvo antes
  dessa operação.
- **FR-008**: O sistema MUST exibir o status "Aprovado com edições" com um indicador visual
  distinto do status "Aprovado" comum, tanto para o autor original do gasto quanto para quem
  gerencia os gastos.
- **FR-009**: O sistema MUST continuar contabilizando gastos marcados como "Aprovado com
  edições" em todos os cálculos financeiros que hoje consideram gastos "Aprovados" (ex.: total
  de despesas do período, custos vinculados a eventos, planilha de pagamentos) — a marca de
  edição é uma informação adicional, não uma mudança de categoria financeira.
- **FR-010**: O sistema MUST bloquear a edição de um gasto "Rejeitado", a menos que a edição seja
  acompanhada da ação de aprovar (reconsiderar).
- **FR-011**: O sistema MUST impedir que um usuário sem papel de gestão financeira aprove,
  rejeite, edite gastos de terceiros, vincule um gasto a um evento ou exclua um gasto que não
  seja próprio e ainda pendente.
- **FR-012**: O sistema MUST permitir que usuários com papel SUPERADMIN ou FINANCEIRO vinculem
  ou removam o vínculo de qualquer gasto a um evento do calendário, buscando eventos por data.
- **FR-013**: O sistema MUST permitir que usuários com papel SUPERADMIN ou FINANCEIRO excluam
  qualquer gasto; um colaborador comum MUST poder excluir apenas os próprios gastos enquanto
  ainda estiverem pendentes.
- **FR-014**: O sistema MUST exigir o anexo de uma nota fiscal (imagem ou PDF, até 10MB) ao
  registrar um novo gasto, e MUST rejeitar arquivos acima desse limite com uma mensagem clara.
- **FR-015**: O sistema MUST manter, no formulário de novo gasto/edição, a opção "Sem desembolso
  definido" ao lado de "Reembolso a funcionário" e "Pagamento a fornecedor" na escolha de forma
  de pagamento.
- **FR-016**: O sistema MUST preservar integralmente o comportamento da tela e das rotas
  equivalentes já existentes fora do painel Beta React (aplicação legada), sem nenhuma alteração
  visível nelas.

### Key Entities

- **Gasto Extra**: um custo avulso registrado por um colaborador — descrição, categoria, valor,
  data do gasto, status (pendente/aprovado/rejeitado), indicador de "aprovado com edições",
  forma de pagamento (reembolso a funcionário / pagamento a fornecedor / sem desembolso
  definido), nota fiscal anexada, evento vinculado (opcional), autor, quem decidiu (aprovou/
  rejeitou/editou) e quando.
- **Papel do usuário**: define o nível de acesso à tela — colaborador comum (só os próprios
  gastos) versus SUPERADMIN/FINANCEIRO (gestão completa de todos os gastos da empresa).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Um colaborador comum consegue registrar um novo gasto (do clique em "+ Novo gasto"
  até a confirmação) em menos de 2 minutos, sem nunca visualizar dados de outro colaborador.
- **SC-002**: Um gestor financeiro consegue, a partir da tabela, aprovar um gasto simples em um
  único clique e aprovar-com-correção (editar + aprovar) em uma única interação de formulário,
  sem navegar para outra tela.
- **SC-003**: 100% dos gastos aprovados com dados alterados no momento da aprovação exibem o
  indicador "Aprovado com edições" tanto para o gestor quanto para o autor original.
- **SC-004**: Os totais financeiros que dependem de gastos aprovados (ex.: total do período,
  custo por evento) continuam corretos após a mudança — nenhum gasto "aprovado com edições" fica
  de fora dessas somas.
- **SC-005**: A tela legada (fora do painel Beta React) permanece funcionando exatamente como
  antes da mudança, sem qualquer alteração de comportamento perceptível.

## Assumptions

- "Usuário comum" significa qualquer colaborador autenticado sem o papel SUPERADMIN nem
  FINANCEIRO; não existe hoje um papel específico "Staff"/"Talento" no sistema de papéis — é o
  caso padrão de qualquer usuário sem papel de gestão.
- FINANCEIRO recebe o mesmo nível de gestão que SUPERADMIN especificamente na tela de Gastos
  Extras (decisão confirmada com o solicitante) — em outras áreas do sistema o papel FINANCEIRO
  não muda.
- "Editar e aprovar" e "editar um gasto já aprovado" usam a mesma regra para decidir "Aprovado
  com edições": houve alteração real de dados na operação que resultou (ou manteve) o gasto como
  aprovado.
- O upload de nota fiscal não é reenviado durante uma edição — só existe no cadastro inicial; a
  edição pelo gestor cobre apenas os campos textuais/numéricos do gasto.
- A aplicação legada (fora do escopo desta feature) continua usando os 3 status atuais sem
  nenhuma noção de "aprovado com edições" — isso é aceitável e esperado, não é um defeito desta
  entrega.
