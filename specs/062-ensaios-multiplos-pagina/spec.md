# Feature Specification: Múltiplos ensaios por evento + página de ensaio simplificada

**Feature Branch**: `062-ensaios-multiplos-pagina`

**Created**: 2026-06-19

**Status**: Draft

**Input**: User description: "preciso fazer duas coisas relacionadas aos ensaios. 1 - cada evento pode ter mais de um ensaio marcado. 2 - não faz muito sentido um ensaio ter toda a página completa de evento."

## Contexto

Um evento (show) pode precisar de **ensaio(s)** marcados pela equipe de ensaio. Hoje:

1. **Múltiplos ensaios**: o vínculo evento→ensaios já é de um-para-muitos e a página do evento
   permite marcar mais de um, **mas** na home (onde a equipe de ensaio trabalha) um evento que
   já tem ensaio sai da fila de "falta agendar" e não há um caminho direto para **marcar outro
   ensaio** — só editar/cancelar os existentes. Falta deixar isso evidente e cômodo.
2. **Página do ensaio**: ao abrir um ensaio, hoje ele exibe **a página completa de evento**
   (casting, figurino, venda/financeiro, etc.), o que não faz sentido — um ensaio só precisa de
   informações enxutas (quando, onde, de qual show é, e poder editar/cancelar).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Marcar mais de um ensaio por evento (Priority: P1) 🎯 MVP

Como equipe de ensaio, quero marcar **mais de um ensaio** para o mesmo evento (ex.: um ensaio de
marcação e outro com figurino), de forma evidente tanto na página do evento quanto na home.

**Why this priority**: É metade do pedido e cobre o caso real de eventos que ensaiam mais de uma
vez.

**Independent Test**: Em um evento, marcar dois ensaios em datas diferentes e confirmar que ambos
aparecem (no evento e na home), sem que o segundo substitua o primeiro.

**Acceptance Scenarios**:

1. **Given** um evento sem ensaio, **When** a equipe marca um ensaio e depois marca **outro**,
   **Then** os **dois** ensaios ficam vinculados ao evento e aparecem listados.
2. **Given** um evento que já tem ensaio(s), **When** a equipe está na home, **Then** existe um
   caminho claro para **marcar outro ensaio** (sem precisar caçar a opção).
3. **Given** vários ensaios no mesmo evento, **When** exibidos, **Then** aparecem ordenados por
   data, cada um com seus próprios dados (data/hora/local/descrição) e ações (editar/cancelar).

---

### User Story 2 - Página de ensaio simplificada (Priority: P1)

Como qualquer usuário que abre um ensaio, quero uma página **enxuta**, com só o que importa do
ensaio (data/hora, local, de qual show ele é, descrição) e as ações de editar/cancelar — sem os
painéis de casting, figurino, venda e financeiro que pertencem ao show.

**Why this priority**: É a outra metade do pedido; melhora muito a clareza e evita ações
indevidas na página errada.

**Independent Test**: Abrir um ensaio e confirmar que a página mostra apenas as informações do
ensaio (e o vínculo ao show), sem os painéis completos de evento.

**Acceptance Scenarios**:

1. **Given** um ensaio, **When** sua página é aberta, **Then** mostra data/hora, local,
   descrição e **de qual show** ele é (com link para o show, se existir).
2. **Given** um ensaio, **When** sua página é aberta, **Then** **não** mostra os painéis de
   casting, figurino, venda/financeiro, contrato, pagamentos, nota fiscal nem agrupamento.
3. **Given** um usuário da equipe de ensaio/admin, **When** abre o ensaio, **Then** pode
   **editar** (data/hora/local/descrição) e **cancelar** o ensaio dali.
4. **Given** um ensaio órfão (show removido), **When** sua página é aberta, **Then** ela
   funciona normalmente e deixa claro que não há show vinculado, permitindo cancelar (feature
   057 preservada).

---

### Edge Cases

- **Ensaio órfão** (sem show pai): a página simplificada funciona e permite cancelar.
- **Show com 0 ensaios**: nada muda na exibição do show além do que já existe.
- **Marcar outro ensaio na mesma data**: permitido (não há regra de unicidade por data).
- **Permissão**: editar/cancelar ensaio segue restrito à equipe de ensaio/casting/admin; demais
  usuários veem a página simplificada em modo leitura.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O sistema MUST permitir **vários ensaios** vinculados ao mesmo evento, sem que um
  novo substitua os anteriores.
- **FR-002**: A página do evento MUST permitir marcar um ensaio **mesmo quando já existem**
  ensaios marcados (sem escondê-la após o primeiro).
- **FR-003**: A home MUST oferecer, para um evento que já tem ensaio(s), um caminho claro para
  **marcar outro ensaio**.
- **FR-004**: Todos os ensaios de um evento MUST ser exibidos (ordenados por data) com seus
  dados e ações individuais (editar/cancelar).
- **FR-005**: Ao abrir um **ensaio**, o sistema MUST exibir uma página **simplificada** contendo
  apenas: data/hora, local, descrição e o show de origem (com link, se houver).
- **FR-006**: A página de ensaio MUST **não** exibir os painéis próprios de show (casting,
  figurino, venda/financeiro, contrato, pagamentos, nota fiscal, agrupamento).
- **FR-007**: A página de ensaio MUST permitir **editar** e **cancelar** o ensaio para os perfis
  autorizados (equipe de ensaio/casting/admin); leitura para os demais.
- **FR-008**: Ensaios órfãos MUST continuar funcionando na página simplificada (cancelar
  disponível) — sem regressão da feature 057.

### Key Entities

- **Ensaio (existente)**: evento do tipo ENSAIO vinculado a um show (campo de "evento pai"). Tem
  data/hora, local e descrição. Esta feature não muda os dados; muda **como é exibido** e
  reforça o suporte a **vários** por show.
- **Evento/Show (existente)**: pode ter zero, um ou vários ensaios.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: É possível ter 2+ ensaios no mesmo evento e todos aparecem (evento e home).
- **SC-002**: A partir da home, a equipe consegue marcar um segundo ensaio sem sair para procurar
  a opção em outro lugar.
- **SC-003**: A página de um ensaio mostra apenas informações do ensaio + vínculo ao show; 0
  painéis de show (casting/figurino/venda/financeiro/contrato/pagamentos/NF/agrupamento).
- **SC-004**: Editar e cancelar ensaio continuam funcionando a partir da nova página, sem
  regressão.

## Assumptions

- "Mais de um ensaio por evento" já é suportado no vínculo de dados; o trabalho é garantir a
  experiência (não esconder a opção; oferecer "marcar outro" na home) e exibir todos.
- A página simplificada é uma **visão dedicada** ao tipo ENSAIO; o show continua com a página
  completa.
- Itens úteis ao ensaio que já existam (ex.: elenco do show em modo leitura, materiais de
  ensaio) podem aparecer na página simplificada se já forem pertinentes, mas sem trazer os
  painéis de edição do show.
- Permissões de editar/cancelar ensaio seguem as já existentes (equipe de ensaio/casting/admin).
