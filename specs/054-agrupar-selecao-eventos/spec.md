# Feature Specification: Seleção de eventos no agrupamento (busca + multi-seleção)

**Feature Branch**: `054-agrupar-selecao-eventos`

**Created**: 2026-06-16

**Status**: Draft

**Input**: User description: "está ficando bom o esquema de agrupar eventos para a questão comercial. Mas achei um pouco ruim a forma que fez. Ele está mostrando apenas eventos do mesmo dia. Talvez o ideal seja eu poder pesquisar os eventos e ir marcando uma checkbox. Ou daquele modo de seleção que eu clico para o evento ir pra direita. Ai depois eu seleciono qual deles vai ser o principal."

## Contexto

O agrupamento de eventos por contrato (feature 053) já funciona: um evento "principal"
concentra os dados comerciais e os demais viram "satélites". Porém a forma de **escolher
quais eventos agrupar** ficou limitada:

- Só aparecem eventos próximos na data (janela de ±3 dias), então eventos do mesmo
  contrato em datas mais distantes não aparecem para seleção.
- Só dá para vincular **um** evento por vez (um seletor simples), o que é trabalhoso
  quando o contrato tem vários eventos.

Esta feature melhora **somente a etapa de seleção** dos eventos a agrupar. As regras de
negócio do agrupamento (satélite herda do principal, campos comerciais zerados, bloqueios
de integridade, painel financeiro tratando o grupo como 1 venda) permanecem as mesmas da
feature 053.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Buscar e marcar vários eventos para agrupar (Priority: P1) 🎯 MVP

Como usuário comercial, quero buscar qualquer evento (por nome ou data), independente de
quão distante ele esteja do evento atual, e marcar vários de uma vez por checkbox, para
montar o grupo do contrato de uma só vez.

**Why this priority**: É a dor central relatada — hoje os eventos do mesmo contrato em
datas diferentes simplesmente não aparecem, e agrupar um a um é lento. Sem isso a feature
não resolve o problema.

**Independent Test**: Abrir um evento, abrir o seletor de agrupamento, digitar parte do
nome de um evento de outra data, ver a lista filtrar, marcar dois eventos e confirmar que
ambos entram no grupo.

**Acceptance Scenarios**:

1. **Given** um evento aberto e a seção de agrupamento, **When** o usuário digita parte do
   nome ou a data de outro evento no campo de busca, **Then** a lista mostra apenas os
   eventos que correspondem, sem recarregar a página.
2. **Given** a lista de eventos candidatos, **When** o usuário marca os checkboxes de dois
   ou mais eventos e confirma, **Then** todos os eventos marcados são vinculados ao grupo
   de uma única vez.
3. **Given** eventos em datas muito distantes do evento atual (semanas ou meses), **When**
   o usuário busca por eles, **Then** eles aparecem normalmente na lista (sem limite de
   janela de data).
4. **Given** nenhum texto digitado na busca, **When** o seletor é aberto, **Then** uma
   lista inicial de eventos é exibida (mais recentes/próximos primeiro) para seleção
   direta sem precisar digitar.

---

### User Story 2 - Escolher qual evento é o principal depois da seleção (Priority: P1)

Como usuário comercial, depois de escolher o conjunto de eventos do grupo, quero indicar
qual deles é o evento principal (que concentra os dados comerciais), para que o contrato
fique corretamente representado.

**Why this priority**: A definição do principal é o que dá sentido comercial ao grupo; sem
ela o agrupamento não pode ser concluído. Faz parte indivisível do mesmo fluxo da US1.

**Independent Test**: Selecionar 3 eventos, escolher um deles como principal, confirmar, e
verificar que o escolhido ficou como principal e os outros 2 como satélites.

**Acceptance Scenarios**:

1. **Given** o conjunto de eventos selecionados (incluindo o evento atual), **When** o
   usuário precisa confirmar o grupo, **Then** o sistema apresenta a escolha de qual
   evento é o principal entre os participantes do grupo.
2. **Given** o evento atual mais os selecionados, **When** nenhum principal é escolhido
   explicitamente, **Then** o evento atual (de onde a ação partiu) é o principal sugerido
   por padrão.
3. **Given** a escolha do principal feita, **When** o usuário confirma, **Then** o evento
   indicado vira o principal e todos os demais selecionados viram satélites, herdando os
   dados comerciais do principal.

---

### User Story 3 - Confirmação e preservação das regras de integridade (Priority: P2)

Como usuário comercial, quero que o sistema continue protegendo contra agrupamentos
inválidos mesmo quando eu seleciono vários eventos de uma vez, para não corromper grupos
existentes nem perder dados sem aviso.

**Why this priority**: As proteções da feature 053 não podem regredir ao introduzir a
multi-seleção; mas é P2 porque depende do fluxo das US1/US2 já existir.

**Independent Test**: Tentar incluir na seleção um evento que já é satélite de outro grupo
e confirmar que o sistema recusa com aviso claro, sem agrupar nenhum dos demais
indevidamente.

**Acceptance Scenarios**:

1. **Given** um dos eventos marcados já é satélite de outro grupo ou já é principal de um
   grupo existente, **When** o usuário confirma, **Then** o sistema avisa qual evento é
   inválido e não conclui um agrupamento incorreto.
2. **Given** um ou mais eventos selecionados já têm valor de venda preenchido, **When** o
   usuário confirma sem autorizar a substituição, **Then** o sistema exige a confirmação
   explícita antes de zerar os dados comerciais desses satélites.
3. **Given** eventos do tipo ENSAIO, **When** o usuário busca eventos para agrupar,
   **Then** eles não aparecem como candidatos (mantém a regra da feature 053).
4. **Given** uma confirmação com seleção inválida, **When** o sistema recusa, **Then** a
   seleção e a escolha do usuário não são perdidas (mensagem de erro, sem apagar o que foi
   marcado).

---

### Edge Cases

- **Nenhum evento marcado**: confirmar sem marcar nada deve avisar "selecione ao menos um
  evento", sem efeito no banco.
- **Busca sem resultados**: exibir estado vazio ("nenhum evento encontrado") em vez de
  lista vazia silenciosa.
- **Evento atual já é satélite**: a seção de seleção não deve ser oferecida (o evento
  precisa ser desagrupado antes — comportamento herdado da 053).
- **Selecionar o próprio evento atual como item da lista**: o evento atual nunca aparece
  como candidato (ele já faz parte do grupo por definição).
- **Volume grande de eventos**: a busca deve permanecer responsiva mesmo com centenas de
  eventos cadastrados.
- **Principal escolhido é um satélite já existente de outro grupo**: recusar (não pode ser
  principal — regra herdada da 053).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O sistema MUST permitir buscar eventos candidatos a agrupamento por texto
  (nome do evento e/ou data), filtrando a lista em tempo real conforme o usuário digita.
- **FR-002**: O sistema MUST remover a limitação de janela de data (±3 dias) da feature
  053 — qualquer evento elegível MUST poder ser encontrado e selecionado,
  independentemente da distância de data em relação ao evento atual.
- **FR-003**: O sistema MUST permitir selecionar **múltiplos** eventos de uma vez via
  checkbox e agrupá-los em uma única ação de confirmação.
- **FR-004**: O sistema MUST permitir, após a seleção, escolher qual evento (entre o
  evento atual e os selecionados) é o principal do grupo, com o evento atual como padrão.
- **FR-005**: O sistema MUST exibir uma lista inicial de eventos candidatos ao abrir o
  seletor, mesmo sem texto de busca digitado.
- **FR-006**: O sistema MUST excluir da lista de candidatos: o próprio evento atual,
  eventos do tipo ENSAIO, e (para feedback claro) MUST sinalizar/impedir eventos que já
  são satélites ou principais de outros grupos.
- **FR-007**: O sistema MUST preservar todas as validações de integridade da feature 053
  ao confirmar a multi-seleção (evento já satélite, evento já principal, ENSAIO,
  auto-agrupamento), avisando qual evento é inválido sem concluir um agrupamento
  incorreto.
- **FR-008**: O sistema MUST exigir confirmação explícita antes de zerar dados comerciais
  de qualquer evento selecionado que já tenha valor de venda preenchido (FR-005 da 053,
  agora aplicada a múltiplos eventos).
- **FR-009**: O sistema MUST registrar no histórico/log de cada evento envolvido o
  agrupamento realizado (mantendo a auditoria da feature 053).
- **FR-010**: O sistema MUST preservar a seleção e a escolha do usuário em caso de erro de
  validação (não apagar os eventos marcados nem a escolha de principal).
- **FR-011**: A funcionalidade MUST permanecer restrita aos perfis COMERCIAL, FINANCEIRO e
  SUPERADMIN (mesma regra de acesso da feature 053).
- **FR-012**: O sistema MUST manter o resultado final idêntico ao da feature 053 (um
  principal + N satélites; satélites com campos comerciais zerados herdando do principal;
  painel financeiro tratando o grupo como 1 venda) — esta feature altera apenas a etapa de
  seleção, não o modelo de dados nem os efeitos do agrupamento.

### Key Entities

Esta feature **não introduz novas entidades**. Reutiliza o vínculo de agrupamento já
existente na feature 053 (evento principal ↔ eventos satélites). A mudança é apenas na
interface e no fluxo de seleção.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: O usuário consegue agrupar eventos de datas distantes (fora da janela de ±3
  dias), o que era impossível antes — 100% dos eventos elegíveis ficam alcançáveis pela
  busca.
- **SC-002**: O usuário consegue agrupar 3 eventos sob um contrato em uma única operação
  (uma confirmação), em vez de repetir o fluxo 3 vezes.
- **SC-003**: A busca filtra a lista em menos de 1 segundo (percepção de "tempo real") com
  o volume atual de eventos cadastrados.
- **SC-004**: Nenhuma regressão nas proteções de integridade da feature 053 — todos os
  agrupamentos inválidos continuam sendo recusados com aviso claro.
- **SC-005**: O resultado de um agrupamento feito pela nova tela é indistinguível, no banco
  e no painel financeiro, de um agrupamento feito pelo fluxo antigo.

## Assumptions

- A busca pode ser feita **no cliente** (sobre a lista de eventos elegíveis já carregada na
  página), já que o volume de eventos é da ordem de centenas — não há necessidade de busca
  paginada no servidor para o volume atual.
- "Eventos elegíveis" para a lista inicial são todos os eventos não-ENSAIO exceto o próprio
  evento atual; eventos que já pertencem a um grupo aparecem sinalizados/bloqueados em vez
  de ocultados, para o usuário entender por que não pode selecioná-los (decisão de UX que
  pode ser refinada no plano).
- O padrão de seleção escolhido é **lista com busca + checkbox** (confirmado com o
  usuário), não o dual-list de transferência — por simplicidade e aderência ao princípio
  mobile-first da constituição.
- O agrupamento continua sendo sempre **manual** (nunca automático/sugerido), como na
  feature 053.
- A estrutura do grupo permanece **plana** (2 níveis: um principal + satélites diretos);
  não há grupos aninhados.
