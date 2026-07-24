# Feature Specification: Reestruturação do Módulo de Comissões

**Feature Branch**: `187-comissoes-modulo-completo`

**Created**: 2026-07-24

**Status**: Draft

**Input**: User description: "Reestruturação completa do Módulo de Comissões (/financeiro/comissoes no app React apps/internal) — visão por papel (Minhas Comissões para vendedor comum vs. visão gerencial para financeiro/superadmin), KPIs do mês, duas visões (resumo por vendedor / detalhamento de vendas), pagamento em lote atômico por vendedor com modal de confirmação, exportação CSV."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Vendedor acompanha suas próprias comissões (Priority: P1)

Um vendedor (papel Comercial) acessa a tela de comissões para ver quanto acumulou de comissão no mês corrente e conferir os eventos que compõem esse valor, sem ver dados de outros vendedores nem ter acesso a nenhuma ação de pagamento.

**Why this priority**: É o uso mais frequente da tela (todo vendedor confere periodicamente) e é onde o risco de vazamento de dados entre vendedores é maior se o RBAC falhar — precisa estar correto antes de qualquer outra funcionalidade.

**Independent Test**: Logar como usuário só com papel Comercial, abrir "Minhas Comissões", confirmar que todos os valores/eventos exibidos pertencem exclusivamente a esse vendedor e que nenhum botão de ação de pagamento é exibido.

**Acceptance Scenarios**:

1. **Given** um usuário logado com papel Comercial (sem Financeiro/Superadmin), **When** ele abre a tela de comissões, **Then** o título exibido é "Minhas Comissões" e todas as linhas mostradas têm `vendedor_id` igual ao do usuário logado.
2. **Given** a mesma tela, **When** o vendedor procura por qualquer botão de "marcar como pago" ou alterar status, **Then** nenhum desses controles está presente na interface.
3. **Given** um vendedor autenticado, **When** ele tenta chamar diretamente (fora da UI) o endpoint de liquidação em lote para o seu próprio ID ou o de outro vendedor, **Then** o servidor responde 403 e nenhum registro é alterado.

---

### User Story 2 - Financeiro/Superadmin fecha o pagamento do mês por vendedor (Priority: P1)

Um usuário com papel Financeiro ou Superadmin seleciona um mês, revisa o resumo agrupado por vendedor e liquida o pagamento de um vendedor específico em uma única ação, com confirmação prévia do valor exato.

**Why this priority**: É a ação financeira crítica da tela — envolve dinheiro real e é onde hoje existe o bug de dessincronização; corrigi-la é o principal motivo da reestruturação.

**Independent Test**: Logar como Financeiro, selecionar um mês com comissões pendentes de um vendedor, clicar em "Pagar Mês", confirmar no modal e verificar que todos os registros elegíveis daquele vendedor/mês (e somente eles) passam a `status='pago'` com `pago_em` preenchido, e que os KPIs da tela atualizam sem F5.

**Acceptance Scenarios**:

1. **Given** um vendedor com múltiplas comissões `a_pagar` em um mês, **When** o Financeiro clica em "Pagar Mês" na linha desse vendedor, **Then** um modal exibe "Confirmar pagamento de R$ X.XXX,XX para [Nome do Vendedor] relativo ao mês [YYYY-MM]?" com o valor exato somado no servidor.
2. **Given** o modal de confirmação aberto, **When** o Financeiro confirma, **Then** todos os registros elegíveis daquele vendedor/mês são atualizados para `status='pago'` e `pago_em=NOW()` em uma única operação atômica — ou todos, ou nenhum, mesmo que ocorra uma falha no meio do processo.
3. **Given** o pagamento confirmado, **When** a resposta retorna, **Then** os cards de KPI, o status do vendedor na tabela ("Pago") e a lista de "Detalhamento de Vendas" refletem o novo estado imediatamente, sem recarregar a página.
4. **Given** um vendedor cujas comissões do mês já foram todas liquidadas, **When** o Financeiro reabre a tela, **Then** o status do mês para esse vendedor aparece como "Pago" e o botão de ação primária não permite pagamento duplicado.

---

### User Story 3 - Financeiro/Superadmin analisa e exporta o detalhamento do mês (Priority: P2)

Um usuário com papel Financeiro ou Superadmin alterna para a visão "Detalhamento de Vendas", filtra por vendedor/evento/status para conferência, e exporta um CSV do resumo do mês para enviar à contabilidade.

**Why this priority**: Suporta o fechamento contábil mensal, mas depende das visões e dados já corretos das User Stories 1 e 2 — é valor incremental sobre a base funcional.

**Independent Test**: Com um mês contendo comissões pagas e pendentes de múltiplos vendedores, alternar para "Detalhamento de Vendas", aplicar filtro por status e por nome de evento, depois clicar em "Exportar Relatório (CSV)" e confirmar que o arquivo baixado reflete o mês selecionado com os totais batendo com os KPIs exibidos.

**Acceptance Scenarios**:

1. **Given** a aba "Detalhamento de Vendas" ativa, **When** o usuário filtra por status "A pagar", **Then** somente eventos com esse status aparecem na tabela.
2. **Given** um mês selecionado, **When** o usuário clica em "Exportar Relatório (CSV)", **Then** um arquivo CSV é baixado contendo o resumo por vendedor daquele mês (vendedor, quantidade de vendas, valor total, status).
3. **Given** a aba "Resumo por Vendedor", **When** o usuário expande a linha de um vendedor, **Then** um accordion mostra os eventos individuais que compõem aquele total, cada um com data, evento e valor.

---

### Edge Cases

- Vendedor sem nenhuma comissão no mês selecionado: tela exibe estado vazio, KPIs mostram R$ 0,00, sem erro.
- Vendedor com uma comissão de estorno (valor negativo) misturada com comissões positivas no mesmo mês: o valor total do vendedor e o total "A Pagar" do KPI descontam o estorno corretamente; um estorno pendente não pode ser "pago" isoladamente sem as demais comissões do mês do mesmo vendedor.
- Financeiro tenta pagar o mês de um vendedor que não tem nenhum registro `a_pagar` (todas já pagas ou não existem): ação primária fica desabilitada/oculta, sem permitir chamada ao endpoint.
- Duas liquidações em lote disparadas quase simultaneamente para o mesmo vendedor/mês (double-click ou duas abas): a segunda operação não deve gerar duplicidade nem sobrescrever `pago_em` de registros já pagos pela primeira — deve reportar que não havia mais itens elegíveis.
- Usuário Comercial que também é responsável EducaManto (acesso a vendas por regra especial) mas não tem papel Financeiro/Superadmin: continua tratado como vendedor comum nesta tela — só vê e só pode ver as próprias comissões, sem ações de pagamento.
- Exportação de CSV para um mês sem nenhuma comissão: arquivo é gerado apenas com o cabeçalho de colunas.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O sistema DEVE determinar o papel do usuário logado (Comercial vs. Financeiro/Superadmin) no servidor e aplicar esse papel tanto na leitura dos dados quanto em qualquer ação de escrita — nunca apenas ocultar controles no cliente.
- **FR-002**: Para usuários com papel Comercial (e sem Financeiro/Superadmin), o sistema DEVE exibir a tela com o título "Minhas Comissões" e restringir todos os dados exibidos e retornados pela API às comissões cujo vendedor é o próprio usuário logado.
- **FR-003**: Para usuários com papel Comercial, o sistema DEVE ocultar todos os controles de alteração de status/pagamento e DEVE rejeitar no servidor (HTTP 403) qualquer tentativa de chamar uma ação de liquidação, independente de o vendedor-alvo ser o próprio usuário ou outro.
- **FR-004**: Para usuários com papel Financeiro ou Superadmin, o sistema DEVE exibir um seletor de Mês/Ano (formato `YYYY-MM`) e um filtro rápido por vendedor, aplicados tanto à visão de resumo quanto à de detalhamento.
- **FR-005**: O sistema DEVE exibir três cards de KPI no topo da tela para o mês selecionado: Total de Comissões do Mês, Total Pago (com indicador visual verde) e A Pagar/Pendente (com indicador visual de alerta), calculados por soma direta no banco de dados com precisão de centavos.
- **FR-006**: O sistema DEVE oferecer duas visões alternáveis da mesma consulta: (a) "Resumo por Vendedor" — agrupado por vendedor com quantidade de vendas, valor total da comissão, status do mês (Pendente/Pago) e ação de liquidação; (b) "Detalhamento de Vendas" — uma linha por evento/comissão com data da venda, vendedor, evento, valor, status e data de pagamento.
- **FR-007**: Na visão "Resumo por Vendedor", o sistema DEVE permitir expandir cada linha (accordion) para revelar os eventos individuais que compõem o total daquele vendedor no mês.
- **FR-008**: Na visão "Detalhamento de Vendas", o sistema DEVE permitir filtrar por nome do evento (busca textual) e por status (A pagar / Pago).
- **FR-009**: O sistema DEVE calcular o "Status do Mês" de um vendedor como "Pago" somente quando todas as comissões elegíveis daquele vendedor no mês estiverem com `status='pago'`, e como "Pendente" caso exista ao menos uma comissão `a_pagar`.
- **FR-010**: O botão de ação primária na linha de um vendedor com pendências DEVE exibir o valor exato a ser liquidado (ex.: "Pagar Mês (R$ X.XXX,XX)"), calculado pelo servidor no momento da renderização — nunca somado apenas no cliente.
- **FR-011**: Ao acionar a liquidação de um vendedor, o sistema DEVE exibir um modal de confirmação com o nome do vendedor, o mês/ano e o valor exato antes de efetivar qualquer mudança.
- **FR-012**: Ao confirmar a liquidação, o sistema DEVE atualizar `status='pago'` e `pago_em` (data/hora atual) em todos os registros de comissão elegíveis daquele vendedor naquele mês dentro de uma única transação de banco atômica — se qualquer etapa falhar, nenhuma alteração é persistida.
- **FR-013**: Após uma liquidação bem-sucedida, o sistema DEVE fazer com que os KPIs, o status do vendedor e a visão de detalhamento reflitam o novo estado sem exigir recarregamento manual da página.
- **FR-014**: O sistema DEVE prevenir duplicidade quando duas liquidações forem disparadas para o mesmo vendedor/mês: a segunda operação DEVE considerar apenas os registros ainda `a_pagar` no momento da sua própria execução e não reprocessar os já `pago`.
- **FR-015**: O sistema DEVE oferecer um botão "Exportar Relatório (CSV)" que gera um arquivo com o resumo por vendedor do mês selecionado (vendedor, quantidade de vendas, valor total, status), disponível apenas para Financeiro/Superadmin.
- **FR-016**: Toda ação de liquidação em lote DEVE gerar um registro de auditoria identificando quem executou, quando, o vendedor e o valor total liquidado.
- **FR-017**: O sistema NÃO DEVE alterar o comportamento, as rotas ou os cálculos já existentes na tela Jinja legada de comissões nem em qualquer outra tabela do banco de dados além dos registros de comissão.

### Key Entities

- **Comissão (registro individual)**: representa a comissão de um vendedor sobre um evento/venda específico; possui vendedor responsável, evento de origem, data da venda, valor (positivo ou negativo em caso de estorno), status (a pagar / pago / cancelado) e data de pagamento quando liquidada.
- **Vendedor**: usuário do sistema com papel Comercial (ou Financeiro/Superadmin operando como gestor); é o agrupador da visão de resumo e o alvo da liquidação em lote.
- **Liquidação em lote (evento de negócio)**: a ação de marcar como pagas todas as comissões elegíveis de um vendedor em um mês específico, de uma só vez.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Um vendedor comum consegue abrir "Minhas Comissões" e identificar seu total acumulado do mês em menos de 5 segundos, sem nenhum dado de outro vendedor visível na tela ou nas respostas de rede.
- **SC-002**: O Financeiro consegue liquidar o pagamento mensal completo de um vendedor em no máximo 3 cliques (abrir ação → confirmar no modal → concluído), com os KPIs atualizados imediatamente após a confirmação.
- **SC-003**: 100% das liquidações em lote realizadas resultam em todos os registros elegíveis do vendedor/mês consistentemente `pago` — zero casos de estado parcial (alguns registros pagos, outros não) observados em teste de carga concorrente.
- **SC-004**: A soma exibida nos KPIs bate, centavo a centavo, com a soma direta dos registros de comissão no banco para o mês selecionado, em qualquer volume de dados.
- **SC-005**: Uma tentativa de acesso ou ação fora do escopo do papel do usuário (vendedor comum acessando dados/ações de outro vendedor) é bloqueada no servidor em 100% dos casos testados, independentemente do estado da interface.

## Assumptions

- Os papéis já existentes no sistema (Comercial, Financeiro, Superadmin) são reaproveitados como estão — esta feature não cria papéis novos.
- "Vendedor comum" nesta spec corresponde a um usuário com papel Comercial e sem Financeiro/Superadmin; um usuário com múltiplos papéis (ex.: Comercial + Financeiro) é tratado com a visão gerencial completa.
- A precisão de centavos já é garantida no armazenamento (coluna numérica com duas casas decimais); esta feature garante que as somas exibidas na tela sejam calculadas a partir desse mesmo dado, sem conversões que percam precisão.
- O endpoint de leitura de comissões existente já filtra por vendedor quando o usuário não tem permissão de gestão — esta feature reforça essa mesma regra também nas ações de escrita, que hoje não têm essa checagem por vendedor-alvo.
- "Banco de dados legado" refere-se a qualquer tabela fora dos registros de comissão; a tabela de comissões em si é o dado principal desta feature e pode receber correções de fluxo de atualização (não de schema).
- A tela Jinja legada de comissões continua existindo e funcionando exatamente como hoje; esta feature não a modifica nem remove nenhuma função da qual ela dependa.
- Não há requisito de suporte a exportação em outro formato além de CSV nesta feature.
