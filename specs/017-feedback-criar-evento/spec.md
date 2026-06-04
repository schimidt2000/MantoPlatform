# Feature Specification: Feedback ao criar evento (sem duplicar, sem limpar)

**Feature Branch**: `017-feedback-criar-evento`

**Created**: 2026-06-04

**Status**: Draft

**Input**: User description: "Ao clicar em criar evento, demora e não há feedback de carregamento
nem de erro — já criei dois eventos iguais por clicar duas vezes. Quero feedback visual de
carregamento e de erro; e telas que limpam tudo quando há erro ficam ruins."

## Contexto

A tela de criar evento chama a API do Google Calendar ao salvar, o que demora alguns segundos.
Hoje o botão **não dá nenhum feedback**: não desabilita nem mostra carregamento. Resultado: o
usuário clica de novo achando que não funcionou e **cria eventos duplicados na agenda**. Além
disso, quando há erro de validação, a tela **re-renderiza limpando tudo** o que foi preenchido.
Esta feature aplica, na tela de criar evento, a política de feedback do Princípio V da constituição
(reforçado na v1.1.0).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Não criar evento duplicado (Priority: P1)

Ao clicar em "Adicionar à Agenda", o botão desabilita e mostra um estado de carregamento até a
resposta; cliques adicionais não enviam o formulário de novo.

**Why this priority**: É o problema mais grave relatado — eventos duplicados na agenda.

**Independent Test**: Preencher um evento válido, clicar em salvar e clicar de novo rapidamente;
confirmar que apenas **um** evento é criado e que o botão mostrou carregamento.

**Acceptance Scenarios**:

1. **Given** um formulário válido, **When** o usuário clica em salvar, **Then** o botão desabilita
   e mostra "Adicionando…".
2. **Given** o envio em andamento, **When** o usuário clica novamente, **Then** nenhum segundo
   envio acontece (nenhum evento duplicado).

---

### User Story 2 - Saber o que está faltando (Priority: P1)

Se faltar um campo obrigatório (título, data) ou o horário estiver incoerente (fim antes do
início), o sistema bloqueia o envio e dá feedback visível no campo (realce + "shake"), levando o
foco até ele — sem recarregar a página.

**Why this priority**: Hoje o clique sem campos válidos leva a um round-trip que limpa o
formulário; o usuário fica sem entender o que houve.

**Independent Test**: Deixar o título vazio, clicar em salvar e confirmar que o campo de título é
realçado/sacode, recebe foco e o formulário não é enviado nem limpo.

**Acceptance Scenarios**:

1. **Given** um campo obrigatório vazio, **When** o usuário clica em salvar, **Then** o envio é
   bloqueado e o campo é realçado com um "shake", recebendo o foco.
2. **Given** horário de fim ≤ início, **When** o usuário tenta salvar, **Then** o campo de fim é
   realçado e o envio é bloqueado.
3. **Given** o usuário corrige o campo, **When** ele digita/seleciona, **Then** o realce de erro
   some.

---

### User Story 3 - Não perder o que foi digitado (Priority: P2)

O que o usuário preencheu não é apagado por um erro. Como a validação dos campos obrigatórios
passa a acontecer no próprio navegador (sem round-trip), o caminho que limpava o formulário deixa
de ser alcançado no uso normal.

**Why this priority**: Reflete a dor "limpa tudo que preenchi"; com a validação no cliente, o
formulário não é mais zerado nos casos comuns.

**Acceptance Scenarios**:

1. **Given** campos obrigatórios faltando, **When** o usuário clica em salvar, **Then** o erro é
   tratado no navegador e os dados permanecem na tela (nenhuma re-renderização que zere o form).

---

### Edge Cases

- **JavaScript desabilitado**: a validação do servidor continua existindo (rede de segurança); o
  comportamento de feedback no cliente é uma camada adicional.
- **Falha na API do Google ao criar**: é um erro raro de servidor; o evento não é criado. (Repor
  todos os campos nesse caso é um aprimoramento futuro, fora do escopo desta entrega.)
- **Clique no botão já desabilitado**: não dispara nada.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Ao enviar o formulário de criar evento, o botão de salvar MUST desabilitar e exibir
  estado de carregamento até a navegação/resposta.
- **FR-002**: Cliques adicionais durante o envio NÃO MUST disparar um segundo envio (sem eventos
  duplicados).
- **FR-003**: Antes de enviar, o sistema MUST validar no navegador os campos que hoje causam erro
  no servidor: **título** (obrigatório), **data** (obrigatória) e **horário de fim > início**
  quando ambos preenchidos.
- **FR-004**: Quando a validação bloqueia o envio, o(s) campo(s) com problema MUST receber feedback
  visível (realce + "shake") e o foco ir ao primeiro deles.
- **FR-005**: O realce de erro de um campo MUST desaparecer quando o usuário corrige aquele campo.
- **FR-006**: A validação no cliente NÃO MUST substituir a validação no servidor (que permanece
  como rede de segurança).
- **FR-007**: A mudança NÃO MUST alterar as regras de criação do evento nem os campos enviados —
  apenas adiciona feedback e prevenção de duplicidade.

### Key Entities *(include if feature involves data)*

- N/A — comportamento de interface; sem mudança de dados.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Cliques repetidos no botão de salvar resultam em **no máximo 1** evento criado.
- **SC-002**: 100% dos envios válidos mostram o estado de carregamento no botão.
- **SC-003**: 100% dos bloqueios por validação mostram feedback no campo (realce/shake) — 0
  bloqueios silenciosos.
- **SC-004**: Nos casos comuns de erro de obrigatório, o formulário não é mais zerado.
- **SC-005**: Nenhuma mudança no resultado de criação do evento para envios válidos.

## Assumptions

- Os campos obrigatórios espelhados no cliente são os mesmos já exigidos hoje pelo servidor
  (título, data; coerência de horário). Demais campos seguem opcionais como hoje.
- "Estado de carregamento" = botão desabilitado com texto/ícone de progresso (ex.: "Adicionando…").
- Repor todos os campos quando a API do Google falha ao criar é um aprimoramento futuro (fora de
  escopo), pois nesse caso o evento não foi criado e o erro é raro.
- Esta feature é a primeira aplicação concreta do Princípio V reforçado (constituição v1.1.0); o
  mesmo padrão será aplicado a outras telas conforme forem tocadas.
