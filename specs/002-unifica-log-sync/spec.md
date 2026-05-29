# Feature Specification: Unificar "Log Agenda" e "Sync Agenda"

**Feature Branch**: `002-unifica-log-sync`

**Created**: 2026-05-29

**Status**: Draft

**Input**: User description: "unifique as páginas log agenda e sync agenda"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Um único lugar para a saúde da agenda (Priority: P1)

Hoje existem duas telas separadas para cuidar da agenda: "Log Agenda" (histórico de
atividades/sincronizações) e "Sync Agenda" (status de sincronização + ações). O usuário
administrativo precisa adivinhar qual abrir. Esta feature reúne tudo em **uma página
única**: status de sincronização, ações de sincronização e histórico recente de
atividades da agenda, no mesmo lugar.

**Why this priority**: É a dor relatada ("totalmente fora do padrão"). Consolidar elimina
a confusão e o retrabalho de navegar entre duas telas que tratam do mesmo assunto.

**Independent Test**: Abrir a página unificada e confirmar que dá para ver o status de
sincronização, disparar sincronização manual e ver o histórico de atividades — sem
precisar de uma segunda tela.

**Acceptance Scenarios**:

1. **Given** o usuário quer checar a agenda, **When** abre a página unificada, **Then**
   vê numa só tela o status de frescor por mês, o botão de sincronizar e o log recente.
2. **Given** o usuário está na página unificada, **When** dispara a sincronização manual,
   **Then** a ação funciona como funcionava na antiga "Sync Agenda".
3. **Given** o usuário quer auditar mudanças da agenda, **When** olha a seção de log da
   página unificada, **Then** vê o histórico recente de atividades da agenda.

---

### User Story 2 - Menu sem duplicação (Priority: P2)

O menu lateral deixa de ter dois itens ("Log Agenda" e "Sync Agenda") e passa a ter
**um único item** claro que leva à página unificada.

**Why this priority**: Reduz o ruído visual e a ambiguidade do menu — o "fora do padrão"
que mais incomoda no dia a dia.

**Independent Test**: Abrir o menu e confirmar que há apenas um item para
sincronização/log da agenda, e que ele leva à página unificada.

**Acceptance Scenarios**:

1. **Given** o menu lateral, **When** o usuário procura por sincronização/log da agenda,
   **Then** encontra exatamente um item, não dois.

---

### User Story 3 - Links antigos não quebram (Priority: P3)

Quem tiver bookmark ou link antigo da página de "Log Agenda" continua chegando ao lugar
certo, sem erro.

**Why this priority**: Evita links quebrados e confusão para quem já usava o caminho antigo.

**Independent Test**: Acessar o endereço antigo de "Log Agenda" e confirmar que leva à
página unificada (sem 404).

**Acceptance Scenarios**:

1. **Given** o endereço antigo de "Log Agenda", **When** o usuário o acessa, **Then** é
   redirecionado para a página unificada.

---

### Edge Cases

- **Sem atividades registradas ainda**: a seção de log mostra um estado vazio claro.
- **Usuário sem permissão**: o controle de acesso atual é preservado (quem não podia ver
  as telas antigas continua sem acesso).
- **Log muito extenso**: a página unificada mostra um recorte recente e oferece caminho
  para o histórico completo, sem ficar pesada.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Deve existir UMA única página que reúna o status de sincronização da agenda,
  as ações de sincronização e o histórico recente de atividades da agenda.
- **FR-002**: O menu de navegação MUST conter apenas um item apontando para essa página
  (sem o item duplicado).
- **FR-003**: A página unificada MUST preservar a função de disparar a sincronização
  manual que existia na tela de "Sync Agenda".
- **FR-004**: A página unificada MUST exibir o histórico recente de atividades da agenda
  que existia na tela de "Log Agenda".
- **FR-005**: O endereço antigo da página de log MUST continuar acessível, redirecionando
  para a página unificada (sem links quebrados / sem 404).
- **FR-006**: O controle de acesso atual MUST ser preservado para a página unificada.
- **FR-007**: O sistema NÃO MUST manter telas/arquivos órfãos da função antiga após a
  unificação (sem código/tela morta).

### Key Entities *(include if feature involves data)*

- **Registro de atividade da agenda**: histórico de quem fez o quê (incluindo
  sincronizações automáticas). Já existe; será reutilizado.
- **Frescor por mês**: quando cada mês foi sincronizado pela última vez. Já existe; será
  reutilizado.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: O menu passa a ter exatamente 1 item para sincronização/log da agenda
  (antes: 2).
- **SC-002**: A partir do menu, o usuário acessa status de sincronização E histórico de
  atividades na mesma página, em no máximo 1 clique.
- **SC-003**: 0 links quebrados — acessar o endereço antigo leva à página unificada.
- **SC-004**: 0 regressão nas funções existentes: sincronização manual e visualização do
  log continuam funcionando.

## Assumptions

- A página de sincronização atual será a base da página unificada (mantém status e ações),
  recebendo adicionalmente a seção de histórico recente da agenda.
- O histórico/log geral de auditoria continua existindo; a página unificada mostra o
  recorte da agenda e oferece um caminho para o histórico completo.
- O controle de acesso atual (perfis administrativos) é mantido, sem ampliar nem reduzir
  quem pode ver.
- A unificação inclui remover a tela/arquivo órfão remanescente da função antiga.
