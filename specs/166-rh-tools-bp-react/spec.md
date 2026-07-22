# Feature Specification: RH em React + destino do blueprint órfão `tools_bp`

**Feature Branch**: `166-rh-tools-bp-react`

**Created**: 2026-07-22

**Status**: Draft

**Input**: User description: "Migrar o blueprint `rh` (scaffolding, 1 rota) para React + API JSON
e decidir o destino do blueprint órfão `tools_bp` (calculadora de transporte, hoje não registrado
em `app/__init__.py`), como fatia da User Story 6 (Cauda Administrativa) da migração 144. Escopo:
`GET /rh/dashboard` (RH, permissão `rh.view`) e a decisão explícita sobre `tools_bp` (FR-016 da
spec 144: migrar/reativar ou remover definitivamente)."

## Contexto da decisão sobre `tools_bp`

Auditoria do código (2026-07-22) encontrou que `app/tools/routes.py` (`calculadora_transporte`,
`/tools/calculadora-transporte`) **duplica** a lógica de cálculo de transporte que já existe,
de forma mais correta, em `app/orcamento/transport.py` (`calcular_van`/`calcular_carro`): a
versão em `orcamento` lê as tarifas de uma configuração central (`app/orcamento/settings.py`),
enquanto a versão órfã em `tools_bp` tem as mesmas tarifas **hardcoded** (`5.5`, `6.3`, `1.9`,
etc.) — se a tarifa configurada mudar, a calculadora órfã ficaria com valores desatualizados
sem ninguém perceber, pois não está nem registrada em produção hoje. Não há nenhum consumidor
apontando para `/tools/calculadora-transporte` (blueprint nunca registrado em
`app/__init__.py`), então esta fatia não corre risco de quebrar um fluxo em uso.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Consultar o painel de RH em React (Priority: P1)

Como usuário com permissão `rh.view`, preciso abrir o painel de RH pela interface React, do
mesmo jeito que hoje abro pela tela Jinja.

**Why this priority**: é a única rota real da fatia — pequena, mas precisa ser migrada para
fechar a paridade "toda rota tem endpoint JSON equivalente" (SC-002 da spec 144).

**Independent Test**: abrir `/rh` em React com um usuário que tem a permissão `rh.view` e ver o
painel carregar; com um usuário sem essa permissão, ver o acesso recusado.

**Acceptance Scenarios**:

1. **Given** um usuário autenticado com permissão `rh.view`, **When** ele abre o painel de RH em
   React, **Then** a tela carrega, indicando também se o usuário tem a permissão `user.manage`
   (usada hoje para mostrar/esconder o atalho de gestão de usuários).
2. **Given** um usuário autenticado sem a permissão `rh.view`, **When** ele tenta abrir o painel
   ou chamar a API diretamente, **Then** recebe 403.

---

### User Story 2 - Decisão registrada sobre o blueprint órfão `tools_bp` (Priority: P2)

Como responsável técnico pela migração, preciso que a decisão sobre `tools_bp` (calculadora de
transporte) fique registrada explicitamente — não apenas herdada por omissão — antes de a
migração 144 ser considerada completa.

**Why this priority**: é um requisito explícito da spec da migração (FR-016) — mas, por não ter
nenhum usuário nem tela dependendo dele hoje (nunca esteve em produção), é uma decisão de menor
risco que a US1, podendo vir depois dela.

**Independent Test**: conferir que o código órfão foi removido do repositório (opção escolhida
nesta spec, ver seção acima) e que a calculadora de transporte "de verdade" (dentro do fluxo de
Orçamento) continua funcionando sem nenhuma mudança.

**Acceptance Scenarios**:

1. **Given** o código de `app/tools/` (blueprint, rotas, template), **When** esta fatia é
   concluída, **Then** o código é removido do repositório — decisão explícita: **remover**, não
   migrar (ver Assumptions), por duplicar lógica já existente e mais correta em
   `app/orcamento/transport.py`, sem nenhum consumidor real.
2. **Given** o cálculo de transporte usado de verdade (dentro do fluxo de Orçamento,
   `app/orcamento/transport.py`), **When** `tools_bp` é removido, **Then** nada muda nesse fluxo
   — são módulos independentes, sem import cruzado.

---

### Edge Cases

- Usuário sem a permissão `rh.view` mas com outras permissões (ex.: `user.manage`) → ainda
  recebe 403 no painel de RH (permissões são independentes, sem hierarquia implícita).
- Nenhum edge case relevante para a remoção de `tools_bp` — código sem consumidor, remoção não
  tem efeito colateral observável.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O sistema DEVE expor o painel de RH (indicando permissão `rh.view` já validada e a
  flag `can_manage_users` equivalente a `user.manage`) como endpoint JSON.
- **FR-002**: O endpoint DEVE recusar acesso (403) a usuários sem a permissão `rh.view` — mesma
  regra de hoje (`require_permission("rh.view")`).
- **FR-003**: O comportamento da rota Jinja antiga (`/rh/dashboard`) DEVE permanecer idêntico ao
  de antes desta fatia até ser desativada — sem regressão enquanto ambas coexistirem.
- **FR-004**: O blueprint `tools_bp` (`app/tools/`) e seu template (`app/templates/tools/`) DEVEM
  ser removidos do repositório — decisão explícita (FR-016 da spec 144) motivada por: (a) nunca
  esteve registrado/acessível em produção, (b) duplica, de forma desatualizada (tarifas
  hardcoded), a lógica já existente e configurável em `app/orcamento/transport.py`.
- **FR-005**: A remoção de `tools_bp` NÃO DEVE alterar o comportamento do cálculo de transporte
  usado de verdade no fluxo de Orçamento (`app/orcamento/transport.py`) — módulos independentes,
  sem import cruzado a preservar ou remover.

### Key Entities

Nenhuma entidade de dados nova ou alterada — RH não tem modelo próprio (permissão é checada via
`User.has_permission`, já existente); `tools_bp` não tem modelo próprio.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Um usuário com permissão `rh.view` consegue ver o painel de RH inteiramente pela
  interface React, sem abrir a tela antiga; um usuário sem a permissão recebe 403 nos dois
  caminhos (tela e API).
- **SC-002**: O repositório não contém mais o blueprint `tools_bp` nem seu template — decisão
  FR-016 da spec 144 fica satisfeita para o restante da migração.
- **SC-003**: O fluxo de Orçamento (cálculo de transporte real) continua funcionando sem nenhuma
  mudança perceptível após a remoção.

## Assumptions

- **Decisão sobre `tools_bp`: remover definitivamente**, não migrar/reativar — critério: zero
  consumidores em produção hoje (nunca registrado), lógica duplicada e desatualizada frente ao
  equivalente já existente e configurável em `app/orcamento/transport.py`. Se a equipe comercial
  precisar de uma calculadora de transporte avulsa no futuro, o caminho correto é expor
  `app/orcamento/transport.py` por um endpoint dedicado (decisão de uma fatia futura, fora desta
  spec) — não reviver o código órfão.
- RH permanece scaffolding nesta fatia — nenhuma funcionalidade nova é adicionada ao painel além
  de expô-lo via API; expandir o RH é trabalho futuro fora do escopo da migração 144.
