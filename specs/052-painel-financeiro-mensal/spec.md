# Feature Specification: Painel Financeiro Mês a Mês (Competência + Projeção)

**Feature Branch**: `052-painel-financeiro-mensal`

**Created**: 2026-06-15

**Status**: Ready

**Input**: Refatorar o painel financeiro (`/financeiro/`) para uma visão mês a mês em regime de competência, separando receita realizada de projetada, corrigindo distorções de margem causadas por eventos de cortesia/permuta, adicionando provisionamento de impostos, novos KPIs (break-even, Fator R) e um layout em grade (bento) mais escaneável.

---

## Contexto e Problema Atual

O painel atual (`/financeiro/`) tem dois problemas:

1. **Visualização horizontal demais**: tudo em sequência vertical longa, difícil de escanear.
2. **Distorções de cálculo**: eventos de permuta/cortesia (venda = 0, mas com cachês pagos a talentos) jogam o CPV para ~83% da receita e quebram a DRE — porque o custo do talento entra no CPV sem a receita correspondente.

A solução é mudar a abordagem principal para **mês a mês** (regime de competência ancorado na data do evento), isolar os custos de cortesia/permuta como "Marketing", provisionar impostos e separar receita **realizada** de **projetada**.

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Ver o resultado do mês sem distorção de permutas (Priority: P1)

O financeiro/superadmin abre o painel, vê o mês corrente por padrão e enxerga uma DRE em que os cachês de eventos de cortesia/permuta **não** inflam o CPV — eles aparecem numa linha separada de "Custos de Marketing".

**Why this priority**: É a dor central. Hoje a margem bruta é irreal por causa das permutas.

**Independent Test**: Marcar um evento como cortesia/permuta (venda 0, com talentos alocados) e conferir que o CPV/Margem Bruta não muda, e que o cachê aparece em "Custos de Marketing".

**Acceptance Scenarios**:

1. **Given** um evento normal com venda e cachês, **When** abro o painel no mês do evento, **Then** o cachê entra no CPV e reduz o Lucro Bruto.
2. **Given** um evento marcado como cortesia/permuta (venda 0, com cachês), **When** abro o painel, **Then** o cachê NÃO entra no CPV; entra em "Custos de Marketing (Permutas/Cortesias)" e não distorce a Margem Bruta.
3. **Given** um evento ENSAIO, **When** abro o painel, **Then** ele é 100% ignorado em qualquer cálculo.

---

### User Story 2 - Separar receita realizada de projetada (Priority: P1)

Ao olhar o mês corrente ou um período que inclui datas futuras, o usuário vê claramente o que já aconteceu (Realizado) e o que ainda vai acontecer (Projetado), sem que a projeção infle o resultado efetivado.

**Why this priority**: Decisão de caixa e fiscal depende de saber o que é real vs projeção.

**Independent Test**: Num mês com eventos passados e futuros, conferir que a DRE mostra colunas/linhas distintas de Realizado e Projetado.

**Acceptance Scenarios**:

1. **Given** eventos com data anterior a hoje, **When** abro o painel, **Then** eles contam como Receita Realizada.
2. **Given** eventos com data igual/posterior a hoje, **When** abro o painel, **Then** eles contam como Receita Projetada, em coluna/linha separada.
3. **Given** um período totalmente no passado, **When** abro o painel, **Then** a coluna Projetado fica zerada (sem ruído visual).

---

### User Story 3 - Provisionar impostos só de quem emite nota (Priority: P2)

A DRE desconta uma provisão de imposto somente sobre o `sale_value` de eventos que exigem nota fiscal, chegando à Receita Líquida Operacional.

**Why this priority**: Sem isso, o resultado superestima a margem real (a empresa paga imposto sobre o faturamento com nota).

**Independent Test**: Marcar "emitir nota" em um evento e conferir que aparece a linha "(–) Impostos Provisionados" proporcional só a esse evento.

**Acceptance Scenarios**:

1. **Given** evento com `emitir_nota` ativo, **When** abro o painel, **Then** a provisão = taxa configurada × `sale_value` desse evento entra na DRE.
2. **Given** evento sem nota, **When** abro o painel, **Then** ele não gera provisão de imposto.

---

### User Story 4 - KPIs de gestão: break-even e Fator R (Priority: P2)

O usuário vê de relance: termômetro de break-even (quanto a margem do mês já cobriu o custo fixo) e um alerta de Fator R (proporção folha ÷ faturamento) indicando risco de alíquota.

**Why this priority**: São indicadores de gestão que orientam decisão fiscal e de meta.

**Acceptance Scenarios**:

1. **Given** margem acumulada do mês ≥ custo fixo nominal, **When** abro o painel, **Then** o termômetro mostra 100% (break-even atingido).
2. **Given** folha ÷ faturamento ≥ corte do Fator R configurado, **When** abro o painel, **Then** o selo é verde "Imposto Protegido"; abaixo do corte, alerta de risco de alíquota maior.

---

### User Story 5 - Auditoria de input e status financeiro por evento (Priority: P3)

O usuário vê um card de auditoria listando eventos com receita zerada que **não** estão marcados como cortesia/permuta (provável erro de preenchimento), e a tabela de eventos mostra o status financeiro de cada um em badges coloridos.

**Acceptance Scenarios**:

1. **Given** evento com venda 0 e SEM flag cortesia/permuta, **When** abro o painel, **Then** ele aparece no card de auditoria "Receita zerada sem permuta".
2. **Given** eventos com pagamentos parciais/totais/permuta, **When** vejo a tabela, **Then** cada linha tem badge de status (Pago Total, Pendente, Permuta/Cortesia).

---

### Edge Cases

- **Divisão por zero**: receita líquida 0, nenhum evento com venda, nenhum talento — todos os percentuais e médias devem retornar 0, nunca erro ou infinito.
- **Permuta com `sale_value` preenchido por engano**: a flag `is_cortesia_permuta` é a fonte de verdade; se ativa, a venda é tratada como 0 e o cachê vai para Marketing.
- **Período customizado cruzando meses**: salários por pro-rata; mês cheio usa o total real lançado.
- **Mês sem eventos**: painel mostra estados vazios claros, sem quebrar.

---

## Requirements *(mandatory)*

### Functional Requirements

#### Filtros e período
- **FR-001**: O painel MUST abrir no **mês corrente** por padrão.
- **FR-002**: MUST oferecer filtros rápidos: "Este Mês", "Últimos 30 dias", "Mês Anterior" e "Intervalo Customizado (início/fim)".
- **FR-003**: Os cálculos MUST orbitar a **data do evento** (`start_at`) — regime de competência.
- **FR-004**: Eventos do tipo ENSAIO MUST ser excluídos de 100% dos cálculos.
- **FR-005**: Eventos com `start_at` ≥ hoje (Brasília) MUST ser classificados como **Projetado**; anteriores como **Realizado**, e exibidos separadamente.

#### Flags de evento
- **FR-006**: MUST existir a flag `is_cortesia_permuta` no evento; quando ativa, `sale_value` é tratado como 0 e o evento não exige comprovantes de recebimento.
- **FR-007**: A flag de nota fiscal MUST reusar o campo existente `with_invoice` (rótulo "Emitir Nota"), sem criar coluna duplicada.

#### DRE Gerencial (DRG) — cascata exata
- **FR-008**: `Receita Bruta` = soma de `sale_value` dos eventos **normais** (não-permuta) do período.
- **FR-009**: `(–) Impostos Provisionados` = `taxa_imposto` (config) × `sale_value`, **apenas** dos eventos com `with_invoice = true`.
- **FR-010**: `= Receita Líquida Operacional`.
- **FR-011**: `(–) CPV (Custo dos Talentos)` = soma de `cache_value` dos talentos alocados **apenas em eventos normais** (exclui permutas/cortesias).
- **FR-012**: `= Lucro Bruto` (exibir valor e % sobre **Receita Líquida**).
- **FR-013**: `(–) Custos de Marketing (Permutas/Cortesias)` = soma de `cache_value` dos talentos alocados em eventos com `is_cortesia_permuta = true`.
- **FR-014**: `(–) Comissões de Vendas` = `taxa_comissao` × `sale_value` dos eventos do período (vinculado ao mês do evento), respeitando `receives_commission` do vendedor.
- **FR-015**: `(–) Pessoal (Salários)`: se o filtro for um **mês cheio**, usar o total real de `SalaryPayment` do mês; se for período fracionado/customizado, aplicar pro-rata `(salários ativos ÷ 30) × dias do período`.
- **FR-016**: `= EBITDA / Resultado Operacional` (exibir valor e % de margem sobre Receita Líquida).
- **FR-017**: `(–) Gastos Extras` = `SpecialExpense` aprovadas com `expense_date` no período.
- **FR-018**: `= Resultado Líquido`.
- **FR-019**: A DRE MUST exibir colunas separadas de **Realizado** e **Projetado** (mesma cascata aplicada a cada conjunto).

#### KPIs (8 cards)
- **FR-020**: Ticket Médio = Receita Bruta ÷ nº de eventos com venda.
- **FR-021**: Custo Talento / Receita = CPV ÷ Receita Líquida (vermelho se > 60%).
- **FR-022**: Margem Bruta = Lucro Bruto ÷ Receita Líquida.
- **FR-023**: Margem Operacional (EBITDA) = % de margem do EBITDA.
- **FR-024**: Termômetro de Break-even = barra de progresso: quanto a margem (Lucro Bruto) acumulada do mês já cobriu o **custo fixo nominal** (por ora = Salários + Comissões; ver Assumptions sobre gastos recorrentes futuros).
- **FR-025**: Alerta Fiscal (Fator R) = Folha ÷ Faturamento acumulado; ≥ corte configurado → selo verde "Imposto Protegido (6%)"; abaixo → alerta "Risco de Alíquota (15,5%)".
- **FR-026**: A Receber (Clientes) = soma de `(sale_value − comprovantes)` dos eventos do período (≥ 0 por evento).
- **FR-027**: A Pagar (Talentos) = cachês com `payment_status = 'nao_pago'` no período.

#### Layout (Bento Grid)
- **FR-028**: Top: filtro de data + seleção rápida de mês.
- **FR-029**: Row 1: os 8 KPI cards em grade compacta.
- **FR-030**: Row 2: 2 colunas — esquerda (~65%) a DRE expandida com indentação contábil e valores negativos em cor de contraste; direita (~35%) Receita por Tipo (maior→menor) + Top Vendedores (5 maiores por receita e lucro).
- **FR-031**: Row 3: Tendência dos últimos 6 meses (visão operacional pura) + Card de Auditoria (eventos com receita zerada sem flag de permuta).
- **FR-032**: Row 4: Tabela de eventos do período com badges de status financeiro (Pago Total, Parcial/Pendente, Permuta/Cortesia).

#### Configuração
- **FR-033**: MUST haver campos configuráveis em Settings: taxa de imposto (default 16%) e corte do Fator R (default 28%). A taxa de comissão continua usando `default_commission_rate`.

#### Robustez
- **FR-034**: Todo cálculo com divisão MUST tratar denominador 0 retornando 0 (sem erro, sem infinito), incluindo `sale_value` nulo/zero.
- **FR-035**: Todos os valores MUST usar aritmética `Decimal` (consistente com o módulo atual), e datas/horas em horário de Brasília.

### Acesso
- **FR-036**: Painel restrito a FINANCEIRO e SUPERADMIN (mantém `require_financeiro`).

---

## Key Entities

- **CalendarEvent** (alterado): nova coluna `is_cortesia_permuta` (Boolean, default false). Reusa `with_invoice`, `sale_value`, `sale_value_gross`, `event_type`, `start_at`, `seller_id`.
- **SiteSetting** (alterado): novos campos `tax_rate` (Float, default 16.0) e `fator_r_threshold` (Float, default 28.0).
- **SalaryPayment / SalaryHistory** (lido): fonte de salários (real no mês cheio; pro-rata em período fracionado).
- **SpecialExpense** (lido): gastos extras aprovados por competência.
- **EventPayment** (lido): comprovantes para "A Receber".

---

## Success Criteria *(mandatory)*

- **SC-001**: Eventos de cortesia/permuta deixam de afetar o CPV e a Margem Bruta (0 distorção); seus cachês aparecem em "Custos de Marketing".
- **SC-002**: O usuário identifica em < 5 segundos o Resultado Líquido do mês e quanto é Realizado vs Projetado.
- **SC-003**: Nenhuma divisão por zero ou margem infinita em nenhum cenário (mês vazio, sem vendas, sem talentos).
- **SC-004**: A taxa de imposto e o corte do Fator R podem ser alterados sem deploy (via Settings).
- **SC-005**: O layout em grade cabe a primeira dobra (KPIs + topo da DRE) sem rolagem horizontal.

---

## Assumptions

- **Stack**: implementação em **Flask + Jinja2 + CSS/JS vanilla** (padrão do projeto). As sugestões de React/TypeScript/Tailwind/Shadcn do pedido original são traduzidas para o nosso stack: "Bento Grid" = CSS Grid com as variáveis de cor existentes; "badges" e "cards" = componentes já usados nos templates do financeiro. **Nenhum framework JS novo é introduzido.**
- **`emitir_nota` = `with_invoice`** (campo já existente). Não criamos coluna duplicada.
- **Break-even / Estrutura**: por ora o custo fixo do break-even = Salários (+ Comissões). O cadastro de **gastos recorrentes mensais** (aluguel, contas) que devem entrar nessa conta é uma **feature seguinte separada**; a arquitetura deixa o ponto de extensão pronto (uma função que soma os componentes de custo fixo).
- **Alíquotas 6% / 15,5%** do Fator R são rótulos do alerta (Simples Nacional, fixos por lei) — apenas o **corte** (28%) é configurável. A taxa de provisionamento (16%) é configurável.
- **Mês cheio** = filtro "Este Mês" ou "Mês Anterior", ou custom de dia 1 ao último dia do mesmo mês → usa `SalaryPayment` real. Caso contrário, pro-rata.
- **Migration manual** (autogenerate quebrado por drift pré-existente).
- Nenhuma alteração nos fluxos de pagamentos/comissões existentes — apenas leitura para o painel.
