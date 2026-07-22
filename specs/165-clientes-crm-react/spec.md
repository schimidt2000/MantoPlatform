# Feature Specification: Clientes (CRM) em React

**Feature Branch**: `165-clientes-crm-react`

**Created**: 2026-07-22

**Status**: Draft

**Input**: User description: "Migrar o blueprint `clientes` (CRM) para React + API JSON, como
fatia da User Story 6 (Cauda Administrativa) da migração 144. Escopo: 7 rotas de
`app/clientes/routes.py` — busca (já JSON), criação rápida (já JSON), lista, avaliações
(feedback das clientes), ficha do cliente, atualizar CPF/CNPJ/endereço, excluir cliente. RBAC:
`require_vendas` (COMERCIAL/FINANCEIRO/SUPERADMIN); exclusão restrita a SUPERADMIN/FINANCEIRO.
Cliente é identificado por telefone (chave); busca sem acentos (feature 114) replicada em React."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Buscar e criar cliente rapidamente (Priority: P1)

Como usuário Comercial/Financeiro/Superadmin, preciso buscar um cliente por nome ou telefone (sem
me preocupar com acentos) e, se ele não existir, criá-lo rapidamente com nome e telefone — mesmo
fluxo usado hoje no seletor de cliente da tela de evento.

**Why this priority**: é o único ponto de integração do CRM com outro módulo já migrado (Agenda/
Eventos, US2) — sem essa fatia, a tela de evento em React perde o autocomplete de cliente. É
também a parte mais estreita e de maior uso diário.

**Independent Test**: no seletor de cliente de uma tela React, digitar um nome com acento
("José") e encontrar o cliente cujo nome está sem acento no banco; digitar um telefone/nome
inexistente e criar o cliente inline, recebendo de volta os mesmos dados que a tela antiga
retornaria (incluindo o caso de telefone já cadastrado ser reaproveitado, não duplicado).

**Acceptance Scenarios**:

1. **Given** um usuário Comercial/Financeiro/Superadmin autenticado, **When** ele digita 2+
   caracteres de nome ou telefone no campo de busca, **Then** recebe até 10 clientes cujo nome
   (comparado sem acentos) ou telefone contém o termo, ordenados por nome.
2. **Given** o mesmo usuário, **When** ele envia nome e telefone de um cliente que não existe,
   **Then** um novo cliente é criado com esses dados e o telefone normalizado como chave.
3. **Given** o telefone informado já pertence a um cliente existente, **When** a criação rápida é
   chamada, **Then** o cliente existente é retornado (`reused: true`), sem duplicar.
4. **Given** nome vazio ou telefone inválido, **When** a criação rápida é chamada, **Then** a API
   responde 400 com mensagem específica do campo inválido.

---

### User Story 2 - Consultar a lista e a ficha de clientes (Priority: P2)

Como usuário Comercial/Financeiro/Superadmin, preciso ver a lista de clientes cadastrados (com
busca e contagem de eventos) e abrir a ficha de um cliente específico (contato, CPF/CNPJ,
endereço, eventos associados e total vendido).

**Why this priority**: é a tela de consulta do dia a dia do CRM — depende da busca (US1) já
estar pronta e é a base para as ações de escrita (US3).

**Independent Test**: abrir a lista de clientes em React, buscar por um nome, abrir a ficha de um
cliente e conferir que os eventos associados e o total vendido batem com a tela antiga para o
mesmo cliente.

**Acceptance Scenarios**:

1. **Given** um usuário autorizado, **When** ele abre a lista de clientes sem filtro, **Then** vê
   até 300 clientes ordenados por número de eventos (desc) e depois nome, com o total geral de
   clientes cadastrados.
2. **Given** o mesmo usuário, **When** ele busca por nome ou telefone (com ou sem acento), **Then**
   a lista filtra com a mesma regra de busca sem acentos da US1.
3. **Given** um cliente com eventos associados, **When** o usuário abre sua ficha, **Then** vê
   contato, CPF/CNPJ, endereço, a lista de eventos (mais recente primeiro) com o tipo de relação
   em cada um, e o total vendido (soma de `sale_value` dos eventos).
4. **Given** um usuário sem nenhum dos papéis autorizados, **When** ele tenta acessar a lista, a
   ficha ou a API diretamente, **Then** recebe 403.

---

### User Story 3 - Editar e excluir cliente (Priority: P3)

Como usuário Comercial/Financeiro/Superadmin, preciso corrigir CPF/CNPJ e endereço de um cliente
na própria ficha; como Superadmin/Financeiro, preciso poder excluir um cliente cadastrado por
engano, sem deixar eventos com referência quebrada.

**Why this priority**: é a ação de escrita mais rara do módulo (dados já vêm em geral do
WhatsApp/Kommo ou da criação rápida) — vem por último por ter o menor uso.

**Independent Test**: editar CPF/CNPJ/endereço de um cliente e ver a mudança refletida na ficha;
excluir um cliente com eventos associados e confirmar que os eventos continuam existindo, agora
sem cliente vinculado, e que o cliente some da lista.

**Acceptance Scenarios**:

1. **Given** a ficha de um cliente, **When** o usuário salva CPF/CNPJ/endereço, **Then** os dados
   são persistidos e a ficha reflete os novos valores.
2. **Given** um usuário Comercial autenticado (sem Financeiro/Superadmin), **When** ele tenta
   excluir um cliente, **Then** recebe 403 — a exclusão é restrita a Financeiro/Superadmin.
3. **Given** um usuário Financeiro/Superadmin, **When** ele exclui um cliente com eventos
   associados, **Then** o cliente é removido, as associações (`EventClient`) são apagadas e os
   eventos que apontavam para ele ficam com `client_id` nulo — nenhum evento é apagado ou quebra.

---

### User Story 4 - Ver avaliações recebidas das clientes (Priority: P4)

Como usuário Comercial/Financeiro/Superadmin, preciso ver o resumo das avaliações (feedback)
recebidas das clientes, filtrando por período, nota, tag e cliente específico.

**Why this priority**: é uma tela de análise, não de operação diária — depende da lista/ficha
(US2) para o filtro por cliente, e é a mais isolada das quatro (não é pré-requisito de nenhuma
outra tela do sistema).

**Independent Test**: abrir a tela de avaliações em React, aplicar cada filtro (período, nota,
tag, cliente) isoladamente e em conjunto, e conferir que o total, a média geral, a distribuição
por nota e a lista de "atenção" (notas baixas) batem com a tela antiga para os mesmos filtros.

**Acceptance Scenarios**:

1. **Given** um usuário autorizado, **When** ele abre a tela sem filtro, **Then** vê todas as
   avaliações, com total, média geral, quantidade de clientes avaliadas e distribuição por nota
   (1 a 5).
2. **Given** o mesmo usuário, **When** ele aplica um filtro de período (últimos 30/90/365 dias,
   período customizado ou "todos"), nota, tag ou cliente, **Then** os resultados e os totais são
   recalculados apenas com as avaliações que atendem a todos os filtros ativos ao mesmo tempo.
3. **Given** existem avaliações com nota ≤2, **When** a tela carrega, **Then** até 10 delas
   aparecem destacadas em uma lista de "atenção", ordenadas da mais recente para a mais antiga.

---

### Edge Cases

- Busca com menos de 2 caracteres → lista vazia, sem erro (mesmo comportamento de hoje).
- Nome de cliente com acento cadastrado, busca digitada sem acento (ou vice-versa) → encontra
  normalmente (busca sem acentos, feature 114).
- Cliente sem nenhum evento associado → ficha mostra "0 eventos" e total vendido R$ 0,00, estado
  amigável, não erro.
- Exclusão de cliente que é o único vínculo de um evento → evento permanece no sistema com
  `client_id` nulo, sem quebrar telas de evento já migradas.
- Filtro de avaliações sem nenhum resultado → tela mostra estado vazio amigável, com os totais
  zerados, não erro.
- Tag de filtro fora da lista de tags conhecidas (`POSITIVE_TAGS`/`ATTENTION_TAGS`) → ignorada,
  mesmo fallback de hoje.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O sistema DEVE expor a busca de clientes (nome ou telefone, sem acentos, mínimo 2
  caracteres, até 10 resultados) como endpoint JSON, reaproveitando a lógica já existente
  (`strip_accents_lower`/`unaccent_lower_sql`) sem duplicá-la.
- **FR-002**: O sistema DEVE expor a criação rápida de cliente (nome + telefone, reaproveitando
  cliente existente por telefone) como endpoint JSON, com as mesmas validações e mensagens de
  erro de hoje.
- **FR-003**: O sistema DEVE expor a lista de clientes (busca por nome/telefone, contagem de
  eventos por cliente, limite de 300, ordenação por nº de eventos e depois nome) como endpoint
  JSON.
- **FR-004**: O sistema DEVE expor a ficha de um cliente (dados de contato, CPF/CNPJ, endereço,
  eventos associados com tipo de relação, total vendido) como endpoint JSON.
- **FR-005**: O sistema DEVE expor a edição de CPF/CNPJ/endereço de um cliente como endpoint JSON,
  preenchendo `None` quando o campo vier vazio (mesma regra de hoje).
- **FR-006**: O sistema DEVE expor a exclusão de cliente como endpoint JSON que desvincula
  (`EventClient`) e limpa o `client_id` denormalizado dos eventos associados antes de excluir —
  nenhum evento é apagado.
- **FR-007**: O sistema DEVE expor o resumo de avaliações das clientes (total, média geral,
  clientes avaliadas, distribuição por nota, lista de atenção, filtros de período/nota/tag/
  cliente) como endpoint JSON, reaproveitando `_parse_period` sem duplicar a lógica de filtro.
- **FR-008**: Todo endpoint desta fatia DEVE manter as mesmas regras de RBAC de hoje —
  `require_vendas` (COMERCIAL/FINANCEIRO/SUPERADMIN) para leitura e busca/criação, restrito a
  SUPERADMIN/FINANCEIRO para exclusão.
- **FR-009**: As telas React DEVEM usar o mesmo componente de busca sem acentos (client picker)
  já usado pela tela de evento migrada (US2) — sem duplicar a lógica de normalização no frontend.
- **FR-010**: O comportamento das rotas Jinja antigas (`/clientes/*`) DEVE permanecer idêntico ao
  de antes desta fatia até serem desativadas — sem regressão enquanto ambas coexistirem.

### Key Entities

- **Cliente (Client)**: nome, telefone (chave única, normalizado), telefone de exibição, e-mail,
  empresa, CPF/CNPJ, endereço, origem (`source`); já existente — esta fatia não adiciona campos.
- **Associação Cliente-Evento (EventClient)**: liga cliente a evento com um tipo de relação; já
  existente, usada para listar eventos na ficha e contar eventos na lista.
- **Avaliação de Cliente (ClientFeedback)**: nota (1–5), tags, data de envio, evento associado; já
  existente (feature 130/131) — esta fatia só lê e serializa.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Um usuário Comercial/Financeiro/Superadmin consegue buscar, criar, listar, consultar,
  editar e excluir clientes inteiramente pela interface React, sem abrir a tela antiga.
- **SC-002**: Os dados mostrados em React (lista, ficha, avaliações) são idênticos aos da tela
  antiga para o mesmo usuário e mesmos filtros — verificado por paridade automatizada.
- **SC-003**: Um usuário sem os papéis autorizados não consegue ver nenhuma tela nem chamar
  nenhum endpoint desta fatia (403 em todos); um usuário Comercial sem Financeiro/Superadmin não
  consegue excluir cliente (403).
- **SC-004**: A tela de evento em React (US2, já migrada) continua funcionando com o seletor de
  cliente sem nenhuma mudança de contrato — a busca/criação rápida migradas aqui são
  retrocompatíveis com o consumo já existente.

## Assumptions

- Busca e criação rápida (`/clientes/search`, `/clientes/quick-create`) já retornam JSON hoje —
  esta fatia migra o *consumidor* (frontend) e audita/ajusta o contrato se necessário (FR-002 da
  spec 144), sem reescrever a lógica de negócio.
- Import de clientes via CSV do Kommo (feature 094) é uma operação administrativa pontual, feita
  fora da UI (script/CLI) — fica fora do escopo desta fatia.
- Valores monetários (total vendido) usam `@manto/money` (formatBRL) como fonte única no
  frontend, nunca reimplementados.
