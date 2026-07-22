# Feature Specification: Comissões em React (Leitura)

**Feature Branch**: `158-comissoes-leitura`

**Created**: 2026-07-22

**Status**: Draft

**Input**: User description: "Migrar a tela de Comissões (/financeiro/comissoes) do Jinja para React, somente LEITURA — terceira fatia da US4 (Financeiro/Vendas), depois do Pipeline de Vendas (156) e do Dashboard Financeiro DRE (157). Escopo: tela lista comissões (CommissionPayment) do mês selecionado (entries a_pagar/pago + estornos pendentes), total a pagar, seletor de mês, seletor de vendedor (para FINANCEIRO/SUPERADMIN que gerenciam todos) vs visão restrita à própria comissão (COMERCIAL/VENDAS vendo só as próprias). Reaproveitar toda a lógica já existente em app/financeiro/routes.py (comissoes(), _resync_pending_commissions, _COMMISSION_STATUS_LABELS) sem duplicar regra de negócio — endpoint novo só monta query e serializa. Escrita (marcar como pago, set_commission_status) fica para uma fatia futura, como aconteceu com pagamentos/funcionário também adiados nas fatias 156/157."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Ver as comissões do mês em React (Priority: P1)

Como usuário Financeiro/Superadmin, Comercial ou responsável EducaManto, preciso ver a lista de
comissões (a pagar, pagas e estornos pendentes) de um mês na tela React, com o mesmo recorte que
já vejo hoje — completo se eu gerencio comissões, ou só as minhas se eu sou vendedor.

**Why this priority**: é a tela que Financeiro consulta para fechar o ciclo de pagamento de
comissões e que cada vendedor consulta para conferir o que tem a receber; é 100% leitura (sem
ação de marcar status), tornando-a a fatia mais estreita que resta na US4 depois do pipeline
(156) e do dashboard (157).

**Independent Test**: abrir a tela de comissões em React para um mês qualquer, com um usuário
Financeiro e com um usuário Comercial (sem papel Financeiro), e conferir que as linhas, o total a
pagar e os estornos batem exatamente com os da tela antiga para o mesmo usuário e mesmo mês.

**Acceptance Scenarios**:

1. **Given** um usuário Financeiro ou Superadmin autenticado, **When** ele abre a tela de
   comissões em React sem escolher mês, **Then** vê as comissões (status `a_pagar` ou `pago`) de
   todos os vendedores cujo `sale_date` cai no mês corrente (ou, na ausência de `sale_date`,
   cuja data de criação cai no mês corrente), ordenadas por data de venda e depois por vendedor.
2. **Given** o mesmo usuário, **When** ele troca o mês (seletor `YYYY-MM`), **Then** a lista e o
   total a pagar são recalculados para o novo mês, com os mesmos valores da tela antiga para o
   mesmo intervalo.
3. **Given** existem estornos pendentes (comissões com `status="a_pagar"` e valor negativo,
   geradas por cancelamento de evento em mês anterior), **When** a tela carrega, **Then** esses
   estornos aparecem em uma lista separada, somados ao total a pagar do mês, independentemente do
   mês selecionado.
4. **Given** um usuário Comercial (sem papel Financeiro/Superadmin) ou o responsável EducaManto
   autenticado, **When** ele abre a mesma tela, **Then** vê somente as próprias comissões e
   estornos (filtrados pelo seu `seller_id`), sem opção de ver as de outros vendedores.
5. **Given** um usuário Financeiro/Superadmin, **When** a tela carrega, **Then** vê a lista de
   vendedores elegíveis (papel Comercial) disponível para referência/seleção de mês, igual à tela
   antiga.
6. **Given** a tela carrega, **When** existem comissões pendentes de sincronização (eventos
   realizados que ainda não geraram a linha de comissão), **Then** a sincronização acontece antes
   da consulta (mesmo comportamento de `_resync_pending_commissions` hoje), sem exigir ação
   manual do usuário.
7. **Given** um usuário sem papel Comercial/Financeiro/Superadmin e que não é o responsável
   EducaManto configurado, **When** ele tenta abrir a tela ou chamar a API diretamente, **Then**
   o acesso é recusado (403).

---

### Edge Cases

- Mês sem nenhuma comissão para o usuário → lista vazia com total R$ 0,00, estado amigável, não
  erro.
- Mês em formato inválido no seletor (`month` fora de `YYYY-MM`) → mesmo fallback de hoje: usa o
  mês corrente.
- Estorno com valor negativo → soma corretamente ao total a pagar (reduzindo-o), mesma regra de
  hoje.
- Vendedor sem nenhuma comissão no mês, mas com papel Comercial → continua aparecendo na lista de
  vendedores elegíveis (não depende de ter lançamento no mês).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O sistema DEVE expor a lista de comissões do mês selecionado (status `a_pagar` ou
  `pago`) e a lista de estornos pendentes (status `a_pagar`, valor negativo, independente do mês)
  como endpoint JSON, reaproveitando exatamente a lógica já existente (`comissoes()`,
  `_resync_pending_commissions`) sem duplicar nenhuma regra de negócio.
- **FR-002**: O sistema DEVE restringir o acesso a esse endpoint a usuários com papel Comercial,
  Financeiro ou Superadmin, ou ao responsável EducaManto configurado (independente de papel) —
  mesma regra de hoje (`require_vendas`).
- **FR-003**: O sistema DEVE aceitar o mesmo filtro de mês que a tela antiga aceita hoje via
  querystring (`month`, formato `YYYY-MM`), com o mesmo padrão (mês corrente) quando nenhum filtro
  é informado ou o valor é inválido.
- **FR-004**: A resposta DEVE restringir as comissões e estornos aos do próprio vendedor quando o
  usuário autenticado não tem papel Financeiro/Superadmin — mesma regra de `can_manage` hoje.
- **FR-005**: A resposta DEVE incluir, para cada comissão: vendedor, evento (título), data da
  venda, valor, status e data de pagamento (quando paga) — mesmos campos exibidos hoje.
- **FR-006**: A resposta DEVE incluir o total a pagar do mês (soma das comissões `a_pagar` mais os
  estornos pendentes) — mesmo cálculo de hoje.
- **FR-007**: A resposta DEVE incluir a lista de vendedores elegíveis (papel Comercial) para
  usuários que gerenciam comissões (Financeiro/Superadmin) — mesma lista de hoje.
- **FR-008**: O comportamento da tela antiga (Jinja, `/financeiro/comissoes`) DEVE permanecer
  idêntico ao de antes desta fatia — sem regressão.

### Key Entities

- **Comissão (CommissionPayment)**: vendedor, evento, data da venda, valor (positivo ou negativo
  para estorno), status (`a_pagar`/`pago`/`cancelado`), data de pagamento; já existente — esta
  fatia só lê e serializa, nenhum campo novo.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Um usuário Financeiro/Superadmin, Comercial ou responsável EducaManto consegue
  conferir as comissões do mês (e estornos pendentes) inteiramente pela tela React, sem abrir a
  tela antiga.
- **SC-002**: Os valores mostrados em React são idênticos aos da tela antiga para o mesmo
  usuário, mesmo mês e mesmos dados — verificado por paridade automatizada.
- **SC-003**: Um usuário Comercial (sem Financeiro/Superadmin) não consegue ver comissões de
  outro vendedor nem pela tela nem pela API; um usuário sem nenhum dos papéis autorizados e que
  não é o responsável EducaManto não consegue ver a tela nem a API (403 nos dois casos).

## Assumptions

- Esta fatia é só leitura — marcar comissão como paga/cancelada (`set_commission_status`) não faz
  parte dela; essa ação continua só na tela antiga até sua própria fatia futura.
- Ficam explicitamente fora desta fatia (fatias futuras da US4, mesmo padrão de 156/157): planilha
  de pagamentos de salário com ações em massa e exportação (`/financeiro/pagamentos`). O cadastro
  de funcionário/salário (`/financeiro/funcionarios`) já está unificado em Usuários (feature 022)
  e não é mais uma tela própria do Financeiro — fica fora do escopo da US4 por não existir mais
  como superfície independente.
- Valores monetários exibidos em React usam `@manto/money` (formatBRL) como fonte única — nunca
  reimplementados no frontend.
