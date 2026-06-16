# Feature Specification: Agrupamento de Eventos por Contrato

**Feature Branch**: `053-agrupar-eventos`

**Created**: 2026-06-16

**Status**: Draft

**Input**: User description: "preciso de uma nova feature que precisa conversar muito bem com o restante do site. Existem eventos que tem mais de 1 dia de duracao. ou seja, eu precisava criar um agrupamento de eventos. no dia 27. Pq esse evento tem apenas uma pagamento e um contrato, porem como esse evento tem diversos horarios de entrada diferentes e personagens, foi mais facil criar varios eventos para ficar separadinho. Preciso de um mecanismo para organizar eventos como esse. E criar uma regra de funcionamento para quando isso acontecer no futuro"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Agrupar eventos sob um único contrato (Priority: P1)

Um usuário comercial/financeiro está com um evento multi-dia (ou multi-horário) que foi cadastrado como vários eventos separados na agenda — porque cada dia/horário tem elenco e personagens diferentes — mas que na realidade tem um único cliente, um único contrato e um único pagamento. Ele precisa vincular esses eventos entre si, escolhendo um deles como "evento principal", que passa a concentrar os dados comerciais (valor de venda, comissão, nota fiscal, contrato, forma de pagamento) de todo o grupo.

**Why this priority**: É o problema relatado — sem isso, o usuário não tem como representar corretamente, no sistema, um contrato que gera múltiplos eventos de agenda. É a fundação de toda a feature.

**Independent Test**: Pode ser testado criando 2 eventos distintos no sistema, agrupando um ao outro a partir da tela de evento, e confirmando que o evento satélite passa a exibir um indicativo de grupo com link para o principal.

**Acceptance Scenarios**:

1. **Given** dois eventos existentes e independentes na agenda, **When** o usuário abre um deles e escolhe "agrupar" com o outro, **Then** o sistema pede para escolher qual dos dois é o evento principal e confirma a criação do vínculo.
2. **Given** um evento satélite que já tinha valor de venda preenchido antes de ser agrupado, **When** o usuário confirma o agrupamento, **Then** o sistema avisa explicitamente que esse valor será substituído/zerado e só prossegue após confirmação.
3. **Given** um evento do tipo ENSAIO, **When** o usuário tenta agrupá-lo a outro evento, **Then** o sistema bloqueia a ação, pois ENSAIO já usa outro mecanismo de vínculo (evento pai/filho).

---

### User Story 2 - Painel financeiro trata o grupo como uma única venda (Priority: P1)

O time financeiro precisa que o Painel Financeiro e o Painel de Vendas reflitam a realidade comercial: um contrato multi-dia deve contar como **uma única venda** (ticket médio, número de eventos vendidos), mas o custo de elenco (cachês) de todos os dias do grupo deve ser somado corretamente como custo dessa venda, sem inflar a contagem de eventos nem distorcer a margem.

**Why this priority**: Sem isso, o agrupamento seria apenas cosmético — os números do financeiro continuariam errados (ticket médio baixo demais, contagem de "eventos vendidos" inflada, ou custo de cachê não batendo com a receita), que é exatamente o problema de distorção que a feature 052 já corrigiu para permutas e que não deve voltar por outra via.

**Independent Test**: Pode ser testado agrupando 2 eventos com cachês cadastrados sob um principal com valor de venda definido, e confirmando no `/financeiro/` que: (a) o grupo conta como 1 evento vendido, (b) o CPV do principal inclui os cachês de ambos os eventos.

**Acceptance Scenarios**:

1. **Given** um grupo com 1 evento principal (venda R$ 5.000) e 1 satélite (sem venda própria, cachês de R$ 800), **When** o Painel Financeiro calcula o período, **Then** a receita bruta conta R$ 5.000 uma única vez, o CPV do grupo soma os cachês dos dois eventos, e a contagem de "eventos vendidos" é 1.
2. **Given** um evento satélite sem valor de venda (por estar agrupado), **When** o alerta de "eventos sem valor de venda" (feature 051) roda, **Then** esse satélite não aparece na lista de alerta — assim como já acontece hoje com eventos de cortesia/permuta.

---

### User Story 3 - Visualizar e desfazer o agrupamento (Priority: P2)

Qualquer usuário que abra um evento principal ou um evento satélite precisa entender, de forma clara e imediata, que aquele evento faz parte de um grupo, ver quais outros eventos estão vinculados, e — se o agrupamento foi um erro — desfazer o vínculo, devolvendo o evento ao estado independente.

**Why this priority**: Sem visibilidade clara, o agrupamento se torna uma "caixa preta" que confunde a operação (alguém pode editar o evento satélite esperando que o valor de venda seja salvo, por exemplo). Importante, mas depende das User Stories 1 e 2 já existirem.

**Independent Test**: Pode ser testado abrindo o evento principal de um grupo já criado e verificando que a lista de satélites aparece corretamente; e testado também desfazendo o vínculo de um satélite e confirmando que ele volta a ter campos comerciais próprios e editáveis.

**Acceptance Scenarios**:

1. **Given** um evento principal com 2 satélites, **When** o usuário abre a tela desse evento, **Then** vê a lista dos 2 eventos satélites (título e data) com link para cada um.
2. **Given** um evento satélite, **When** o usuário abre sua tela, **Then** vê um aviso "este evento faz parte do grupo de [evento principal]" com link, e os campos comerciais aparecem bloqueados/somente leitura.
3. **Given** um evento satélite vinculado, **When** o usuário escolhe "desfazer agrupamento", **Then** o evento volta a ter campos comerciais próprios, zerados e editáveis, sem afetar elenco/figurino já cadastrados nele.

---

### User Story 4 - Casting, figurino e sincronização continuam por evento individual (Priority: P3)

A equipe de casting e figurino precisa continuar vendo e gerenciando cada dia/horário do contrato como um evento separado (cada um com seu próprio elenco e personagens), exatamente como já funciona hoje — o agrupamento não deve alterar esse fluxo. A sincronização com o Google Calendar também precisa continuar funcionando normalmente, sem apagar o vínculo de agrupamento em uma re-sincronização.

**Why this priority**: É uma garantia de não-regressão mais do que uma funcionalidade nova — importante documentar e testar, mas não bloqueia o valor entregue pelas histórias anteriores.

**Independent Test**: Pode ser testado re-sincronizando o Google Calendar após criar um grupo e confirmando que o vínculo persiste; e abrindo as telas de casting/figurino para confirmar que cada evento do grupo aparece separadamente, com suas próprias tarefas.

**Acceptance Scenarios**:

1. **Given** um grupo de eventos já criado, **When** a sincronização com o Google Calendar roda novamente, **Then** o vínculo de agrupamento permanece intacto em ambos os eventos.
2. **Given** um grupo de eventos com elenco cadastrado em cada um, **When** o usuário abre as telas de casting e figurino, **Then** cada evento do grupo aparece e é gerenciado separadamente, como hoje.

### Edge Cases

- O que acontece se o usuário tentar agrupar um evento que já é satélite de outro grupo? → Sistema bloqueia e orienta a desagrupar primeiro.
- O que acontece se o usuário tentar excluir um evento principal que ainda tem satélites vinculados? → Sistema impede a exclusão direta e orienta a desagrupar os satélites antes.
- O que acontece se o usuário tentar agrupar um evento a ele mesmo? → Sistema bloqueia.
- O que acontece se o evento escolhido como satélite for do tipo ENSAIO? → Sistema bloqueia (ENSAIO já tem vínculo próprio via evento pai/filho).
- O que acontece com os comprovantes de pagamento (`EventPayment`) e contrato já anexados a um evento que vira satélite? → Permanecem visíveis no evento satélite para histórico, mas o cálculo financeiro do grupo passa a considerar apenas os dados do evento principal a partir da data do agrupamento.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O sistema MUST permitir que um usuário com perfil COMERCIAL, FINANCEIRO ou SUPERADMIN vincule dois ou mais eventos existentes, designando um deles como "evento principal" do grupo e os demais como "eventos satélites".
- **FR-002**: O sistema MUST impedir que um evento que já é satélite de um grupo seja agrupado novamente (como principal ou como satélite de outro grupo) antes de ser desvinculado do grupo atual.
- **FR-003**: O sistema MUST impedir que eventos do tipo ENSAIO sejam agrupados por este mecanismo.
- **FR-004**: O sistema MUST impedir que um evento seja agrupado a ele mesmo.
- **FR-005**: Ao vincular um evento como satélite, o sistema MUST limpar os campos comerciais próprios desse evento (valor de venda, valor bruto, comissão, nota fiscal, forma de pagamento, parcelas, cortesia/permuta) e MUST exigir confirmação explícita do usuário antes de prosseguir caso algum desses campos já tivesse valor preenchido.
- **FR-006**: O sistema MUST exibir, na tela de qualquer evento satélite, um indicativo claro de que ele pertence a um grupo, com link para o evento principal, substituindo os campos comerciais editáveis por um resumo somente leitura dos dados do principal.
- **FR-007**: O sistema MUST exibir, na tela do evento principal, a lista dos eventos satélites vinculados (título e data de cada um).
- **FR-008**: Usuários autorizados MUST conseguir desfazer o vínculo de um evento satélite a qualquer momento, restaurando seus campos comerciais como independentes e editáveis (inicialmente zerados).
- **FR-009**: O sistema MUST impedir a exclusão direta de um evento principal que ainda possua satélites vinculados, orientando o usuário a desagrupar os satélites antes.
- **FR-010**: No Painel Financeiro (`/financeiro/`) e no Painel de Vendas (`/vendas/`), o sistema MUST contar um grupo de eventos (principal + satélites) como uma única venda para fins de número de eventos vendidos e cálculo de ticket médio.
- **FR-011**: No cálculo de custo (CPV) e margem do evento principal, o sistema MUST somar os cachês de talentos de todos os eventos satélites do grupo, além dos seus próprios cachês.
- **FR-012**: O sistema MUST excluir eventos satélites da auditoria de "eventos sem valor de venda" (mesma lógica já aplicada hoje a eventos de cortesia/permuta na feature 052), já que a ausência de valor de venda nesses eventos é esperada por design.
- **FR-013**: Tarefas de casting, tarefas de figurino e o fluxo de pagamento individual de cachês (tela de Pagamentos) MUST continuar operando por evento individual, sem alteração de comportamento causada pelo agrupamento.
- **FR-014**: A sincronização com o Google Calendar MUST preservar o vínculo de agrupamento de um evento entre re-sincronizações — o campo de agrupamento nunca deve ser sobrescrito ou apagado pelo processo de sync.
- **FR-015**: O sistema MUST registrar em log de auditoria quando um agrupamento é criado ou desfeito, incluindo usuário responsável e data/hora.

### Key Entities

- **Evento principal**: evento existente que passa a concentrar os dados comerciais (valor de venda, comissão, nota fiscal, contrato, forma de pagamento) de todo o grupo. É o evento que aparece como "a venda" nos painéis financeiro e de vendas.
- **Evento satélite**: evento vinculado a um evento principal; mantém seu próprio elenco, personagens e cachês para fins operacionais (casting, figurino, pagamento de talentos), mas não tem mais dados comerciais próprios — eles são herdados/exibidos a partir do evento principal.
- **Grupo de eventos**: conjunto formado por 1 evento principal + N eventos satélites, identificado implicitamente pelo vínculo entre eles (sem necessidade de uma entidade própria no banco).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Um usuário comercial consegue agrupar 2 ou mais eventos existentes em menos de 1 minuto, preenchendo os dados financeiros do contrato uma única vez.
- **SC-002**: O ticket médio e a contagem de "eventos vendidos" no Painel Financeiro passam a refletir o número real de contratos fechados, não o número de linhas de agenda.
- **SC-003**: Nenhum evento satélite aparece na lista de alerta de "eventos sem valor de venda".
- **SC-004**: O custo total de cachês de um contrato multi-dia aparece integralmente associado a uma única linha de receita no DRE, sem distorcer a margem bruta do grupo.
- **SC-005**: Desfazer um agrupamento restaura o evento satélite ao estado de evento independente sem qualquer perda de dados de elenco, personagens ou figurino já cadastrados nele.
- **SC-006**: Uma re-sincronização com o Google Calendar não desfaz nenhum agrupamento existente.

## Assumptions

- Casting, figurino, pagamento individual de cachês e sincronização com Google Calendar permanecem operando por evento individual — está fora do escopo desta feature alterar esse comportamento (User Story 4 é uma garantia de não-regressão).
- O campo já existente `parent_event_id` (usado hoje para vincular Ensaios ao evento principal) é um mecanismo diferente, com propósito distinto, e não deve ser reutilizado nem confundido com o agrupamento financeiro desta feature — será introduzido um vínculo novo e independente.
- Apenas perfis com acesso COMERCIAL, FINANCEIRO ou SUPERADMIN podem criar ou desfazer agrupamentos.
- Não há limite rígido de quantos eventos satélites um evento principal pode ter.
- A estrutura de agrupamento é plana (apenas 2 níveis): um evento satélite não pode, por sua vez, ser principal de outro grupo; um evento principal não pode ser satélite de outro grupo ao mesmo tempo.
- Decisões confirmadas com o usuário: (1) os dados financeiros do grupo ficam armazenados no evento principal, sem necessidade de uma nova entidade/tabela; (2) para fins de KPI, um grupo conta como 1 evento vendido; (3) a criação do agrupamento é sempre manual, feita pelo usuário a partir da tela de evento — não há sugestão automática de agrupamento nesta versão.
- Stack: implementação em Flask + Jinja2 + CSS/JS vanilla, seguindo o padrão já estabelecido no restante do sistema (sem frameworks JS novos).
