# Feature Specification: Escrita da Planilha de Pagamentos (React)

**Feature Branch**: `160-escrita-pagamentos-financeiro`

**Created**: 2026-07-22

**Status**: Draft

**Input**: User description: "Migrar a escrita da Planilha de Pagamentos (/financeiro/pagamentos) do Jinja para React — quinta fatia da US4 (Financeiro/Vendas), depois das quatro fatias de leitura (Pipeline de Vendas 156, Dashboard DRE 157, Comissões 158, Pagamentos leitura 159). Escopo: as ações de escrita que ficaram fora da fatia 159 — marcar status de pagamento de um item (pago/pendente, função set_payment_status), ações em massa sobre itens selecionados (bulk_payment_action), registrar e excluir adiantamento de salário (salary_advance, salary_advance_delete) e exportação CSV dos pagamentos do mês (export_pagamentos). Reaproveitar 100% da lógica de negócio já existente em app/financeiro/routes.py, sem duplicar regra — endpoints novos em /api/financeiro só chamam os mesmos helpers e retornam JSON (ou blob CSV, seguindo o padrão de download binário já definido na constituição para a US4). Gate: require_financeiro (FINANCEIRO/SUPERADMIN), igual à tela Jinja atual. Tela React é a mesma PagamentosPage.tsx criada na 159, agora com as ações habilitadas (botões de marcar status, seleção múltipla + ação em massa, formulário de adiantamento, botão de exportar CSV) — nenhuma tela nova."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Marcar status de um item de pagamento (Priority: P1)

Uma pessoa do Financeiro abre a Planilha de Pagamentos (já migrada, só leitura) e precisa marcar
um cachê, salário, gasto, repasse (BV) ou comissão como pago, pendente ou "no banco" (quando
aplicável), sem sair da tela.

**Why this priority**: é a ação mais frequente da tela — o uso diário da Planilha de Pagamentos é
majoritariamente "marcar como pago" item a item. Sem ela a fatia de leitura (159) fica incompleta
como fluxo de trabalho.

**Independent Test**: na tela de pagamentos, clicar no seletor de status de um item de cada tipo
(cachê, salário, gasto, BV, comissão) e confirmar que o status muda imediatamente na tela e persiste
ao recarregar a página.

**Acceptance Scenarios**:

1. **Given** um cachê de talento com status "não pago", **When** o usuário marca como "pago",
   **Then** o item passa a exibir "Pago" e o total do mês é recalculado sem recarregar a página.
2. **Given** uma comissão de um vendedor agrupada por período, **When** o usuário marca o grupo
   inteiro como "pago", **Then** todas as comissões daquele vendedor/mês mudam de status junto.
3. **Given** um item de conta recorrente ou comissão, **When** o usuário tenta marcar como "no
   banco", **Then** a ação é rejeitada (esses tipos só têm pago/não pago).
4. **Given** o status enviado não é um dos valores válidos, **When** a requisição é feita (ex.: via
   chamada direta à API), **Then** o servidor responde com erro e nenhum dado é alterado.

---

### User Story 2 - Ações em massa sobre itens selecionados (Priority: P2)

Uma pessoa do Financeiro seleciona vários itens de uma vez (checkbox em cada linha) e aplica uma
ação — marcar todos como pagos, ou excluir cachês/salários selecionados — em vez de repetir a ação
item a item.

**Why this priority**: acelera o fechamento mensal, mas depende da ação individual (US1) já existir
como base visual/de estado; é a segunda ação mais usada.

**Independent Test**: selecionar 3 itens de tipos diferentes (cachê, salário, gasto) na tela,
escolher "marcar como pago" na ação em massa, e confirmar que os 3 mudam de status juntos e a
seleção é limpa ao final.

**Acceptance Scenarios**:

1. **Given** vários cachês e salários selecionados, **When** o usuário aplica "marcar como pago" em
   massa, **Then** todos os itens selecionados mudam de status e a tela mostra quantos foram
   atualizados.
2. **Given** cachês e salários selecionados, **When** o usuário aplica "excluir" em massa, **Then**
   os itens são removidos da planilha (cachê ou lançamento de salário).
3. **Given** gastos e/ou comissões estão entre os selecionados para exclusão, **When** a ação em
   massa de excluir é aplicada, **Then** esses itens são ignorados (não são excluídos por aqui) e o
   usuário é avisado de quantos foram ignorados e por quê.
4. **Given** comissões selecionadas e a ação escolhida é "no banco", **When** a ação é aplicada,
   **Then** as comissões são ignoradas (não têm esse estado) e o usuário é avisado.
5. **Given** nenhum item selecionado, **When** o usuário tenta aplicar uma ação em massa, **Then**
   nada acontece (ação desabilitada ou sem efeito).

---

### User Story 3 - Registrar e excluir adiantamento de salário (Priority: P3)

Uma pessoa do Financeiro registra um adiantamento (valor + comprovante obrigatório) para um
lançamento de salário do mês, e pode remover um adiantamento lançado por engano.

**Why this priority**: usada com menos frequência que marcar status, mas é uma ação de escrita
completa (upload de arquivo) que hoje só existe no Jinja — fecha a paridade da tela.

**Independent Test**: em um lançamento de salário, abrir o formulário de adiantamento, informar
valor e anexar um comprovante, salvar, e confirmar que o valor líquido a pagar do salário é
atualizado na tela; depois excluir o adiantamento e confirmar que o valor volta ao original.

**Acceptance Scenarios**:

1. **Given** um lançamento de salário sem adiantamentos, **When** o usuário registra um adiantamento
   com valor válido e comprovante anexado, **Then** o adiantamento aparece na lista do lançamento e
   o valor líquido a pagar é reduzido pelo valor do adiantamento.
2. **Given** um valor de adiantamento informado é maior que o saldo restante do salário (soma dos
   adiantamentos existentes + novo > valor do salário), **When** o usuário tenta salvar, **Then** a
   ação é rejeitada com mensagem explicando o motivo, e nada é salvo.
3. **Given** o formulário de adiantamento sem comprovante anexado, **When** o usuário tenta salvar,
   **Then** a ação é rejeitada pedindo o comprovante.
4. **Given** um comprovante maior que 10 MB, **When** o usuário tenta salvar, **Then** a ação é
   rejeitada informando o limite de tamanho.
5. **Given** um adiantamento já registrado, **When** o usuário o exclui, **Then** ele some da lista,
   o comprovante correspondente é removido do armazenamento, e o valor líquido a pagar volta a
   incluir aquele valor.

---

### User Story 4 - Exportar CSV dos pagamentos do mês (Priority: P4)

Uma pessoa do Financeiro baixa um CSV com os cachês do mês selecionado (data, evento, função, nome,
valor, PIX, situação) para conferência ou repasse externo.

**Why this priority**: é a ação menos frequente das quatro (uso pontual, fim de mês ou repasse
bancário), por isso fica por último nesta fatia.

**Independent Test**: com um mês que tenha pelo menos um cachê lançado, clicar em "exportar CSV" e
confirmar que o arquivo baixado abre com as colunas e linhas esperadas para aquele mês.

**Acceptance Scenarios**:

1. **Given** a tela de pagamentos em um mês com cachês lançados, **When** o usuário clica em
   "exportar CSV", **Then** um arquivo é baixado com nome indicando o mês e contendo uma linha por
   cachê do mês, nas mesmas colunas de hoje (Data, Evento, Função, Nome, Valor, Pix, Situação).
2. **Given** um mês sem nenhum cachê lançado, **When** o usuário exporta, **Then** o arquivo é
   baixado só com o cabeçalho, sem erro.

---

### Edge Cases

- Tentar marcar status de um item que não existe mais (removido por outra pessoa entre carregar a
  tela e clicar) — a ação não altera nada e a tela reflete o estado real após a resposta.
- Duplo clique rápido no mesmo botão de status — a ação final refletida deve ser consistente com o
  último clique, sem estado intermediário travado visualmente (Princípio V — feedback em botões).
- Usuário sem papel FINANCEIRO/SUPERADMIN tenta chamar qualquer uma dessas ações diretamente (fora
  da UI) — recebe erro de acesso negado, igual à tela Jinja hoje.
- Ação em massa com uma mistura de tipos onde alguns IDs já não existem mais — os que existem são
  processados normalmente, os que não existem são ignorados silenciosamente (mesmo comportamento
  atual).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O sistema DEVE permitir marcar o status de um item individual de pagamento (cachê,
  salário, gasto, repasse/BV ou grupo de comissões de um vendedor/período) como pago, não pago, ou
  "no banco" quando esse status for válido para o tipo de item, reaproveitando exatamente a mesma
  regra de negócio hoje em `set_payment_status`.
- **FR-002**: O sistema DEVE rejeitar (sem alterar dados) uma tentativa de marcar status inválido
  para o tipo de item (ex.: "no banco" para conta recorrente ou comissão).
- **FR-003**: O sistema DEVE permitir aplicar uma ação em massa (marcar status ou excluir) sobre uma
  seleção de itens de múltiplos tipos (cachês, salários, gastos, comissões) em uma única chamada,
  reaproveitando exatamente `bulk_payment_action`.
- **FR-004**: Na ação em massa de excluir, o sistema DEVE excluir apenas cachês e lançamentos de
  salário, e DEVE informar ao usuário quais itens (gastos, comissões) foram ignorados e por quê.
- **FR-005**: O sistema DEVE permitir registrar um adiantamento de salário com valor e comprovante
  (arquivo) obrigatórios, validando que a soma dos adiantamentos não ultrapasse o valor do salário e
  que o comprovante não exceda 10 MB, reaproveitando exatamente a regra de `salary_advance`.
- **FR-006**: O sistema DEVE permitir excluir um adiantamento de salário já registrado, removendo
  também o comprovante armazenado, reaproveitando exatamente a regra de `salary_advance_delete`.
- **FR-007**: O sistema DEVE permitir exportar em CSV os itens de cachê do mês selecionado, com as
  mesmas colunas e conteúdo produzidos hoje por `export_pagamentos`.
- **FR-008**: Toda ação de escrita desta fatia DEVE exigir usuário autenticado com papel FINANCEIRO
  ou SUPERADMIN, igual ao gate atual (`require_financeiro`); sem esse papel, a ação é recusada.
- **FR-009**: Toda ação de escrita DEVE registrar auditoria (log) igual ao comportamento atual das
  rotas Jinja equivalentes — nenhuma trilha de auditoria existente pode ser perdida na migração.
- **FR-010**: Após qualquer ação de escrita bem-sucedida, a tela DEVE refletir o novo estado (status
  do item, totais do mês, lista de adiantamentos) sem exigir recarregar a página inteira.
- **FR-011**: O sistema DEVE dar feedback visual imediato ao clicar em qualquer botão de ação desta
  fatia (loading/desabilitado durante o envio, sucesso ou erro ao final) — Princípio V da
  constituição.

### Key Entities

- **Item de pagamento**: cachê (EventRole), salário (SalaryPayment), gasto (SpecialExpense), repasse
  BV (EventAcrescimo) ou comissão agregada (CommissionPayment por vendedor/mês) — cada um com um
  status de pagamento próprio.
- **Adiantamento de salário**: valor, data e comprovante (arquivo) vinculados a um lançamento de
  salário específico; múltiplos adiantamentos por lançamento, cada um removível individualmente.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Uma pessoa do Financeiro consegue marcar um item de pagamento como pago sem sair da
  tela e ver o total do mês atualizado em até 1 segundo após a ação.
- **SC-002**: Uma ação em massa sobre 10 itens selecionados de tipos diferentes é aplicada em uma
  única confirmação, sem repetir a ação item a item.
- **SC-003**: 100% dos comprovantes de adiantamento anexados pela tela React abrem corretamente ao
  serem consultados depois (mesmo armazenamento usado pela tela antiga).
- **SC-004**: O CSV exportado pela tela React é byte-a-byte equivalente (mesmas colunas, mesmos
  valores) ao exportado hoje pela tela Jinja, para o mesmo mês.
- **SC-005**: Nenhuma trilha de auditoria é perdida — toda ação de escrita desta fatia aparece no
  log de auditoria com o mesmo nível de detalhe de hoje.

## Assumptions

- A tela React (`PagamentosPage.tsx`, criada na fatia 159) já existe e será estendida com estas
  ações — nenhuma tela nova é criada nesta fatia.
- O upload de comprovante de adiantamento segue o mesmo padrão de multipart já estabelecido nas
  fatias de upload anteriores (ex.: 153, 155), não o padrão JSON puro das fatias de leitura.
- Export de CSV segue o padrão de download binário via blob (`fetch` + `URL.createObjectURL`)
  definido na constituição para a US4, mantendo o nome de arquivo `pagamentos_{mês}.csv`.
- Esta fatia fecha a US4 (Financeiro/Vendas) por completo — depois dela, todo o módulo de
  Financeiro/Vendas migrado até aqui (pipeline, DRE, comissões, pagamentos) tem leitura e escrita em
  React. Fora do escopo desta fatia: gastos especiais/recorrentes, orçamento (PDF), EducaManto (PDF)
  e o módulo de "funcionários" (que já é só redirect para Usuários, não migra) — ficam para outras
  fatias/módulos, se e quando priorizados.
- As rotas Jinja e os endpoints antigos (`/financeiro/pagamentos/set-status`, `/bulk-action`,
  `/salary/<id>/advance`, `/salary/advance/<id>/delete`, `/export`) continuam existindo e
  funcionando normalmente — esta fatia adiciona endpoints novos em `/api/financeiro`, não remove os
  antigos (estratégia strangler-fig, sem quebrar quem ainda usa a tela antiga).
