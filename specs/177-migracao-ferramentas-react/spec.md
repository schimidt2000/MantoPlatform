# Feature Specification: Migração das últimas ferramentas Jinja para React

**Feature Branch**: `177-migracao-ferramentas-react`

**Created**: 2026-07-23

**Status**: Draft

**Input**: User description: "Migração definitiva para React das 7 últimas telas/ferramentas que ainda rodam em Jinja legado (Gastos Extras, Avaliação de Casting, Formulários admin, Gastos Recorrentes, Calculadora de Orçamento, Configuração de Preços, Orçamentos/histórico), eliminando todo link externo/redirecionamento em navigation.tsx para telas antigas."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Gerenciar Gastos Extras sem sair da SPA (Priority: P1)

Um usuário do Financeiro precisa registrar, filtrar, aprovar, rejeitar, excluir e vincular a um evento uma despesa extra (gasto especial), tudo dentro da mesma aplicação React que já usa para o resto do financeiro — hoje esse fluxo abre uma aba separada com a tela clássica.

**Why this priority**: É a ferramenta financeira usada com mais frequência no dia a dia (aprovação de gastos é rotina diária); manter um redirecionamento externo aqui quebra o fluxo de trabalho mais vezes que qualquer outro item da lista.

**Independent Test**: Pode ser testada sozinha acessando a nova tela de Gastos Extras, criando um gasto, aprovando/rejeitando outro e vinculando um terceiro a um evento — sem depender de nenhuma das outras 6 telas.

**Acceptance Scenarios**:

1. **Given** um usuário do Financeiro autenticado, **When** ele abre "Gastos Extras" pelo menu, **Then** a tela carrega dentro da SPA (sem nova aba) mostrando a lista de gastos com filtros por status/categoria/período.
2. **Given** a lista de gastos carregada, **When** o usuário cria um novo gasto com descrição, categoria, valor e tipo de repasse, **Then** o gasto aparece na lista com status "pendente" e feedback de sucesso é exibido.
3. **Given** um gasto pendente, **When** o usuário aprova ou rejeita, **Then** o status muda imediatamente na tela e a ação fica registrada.
4. **Given** um gasto aprovado, **When** o usuário o vincula a um evento existente, **Then** o vínculo aparece na tela e o gasto passa a ser considerado na apuração daquele evento.

---

### User Story 2 - Calcular e enviar orçamento de show sem sair da SPA (Priority: P2)

Um usuário comercial monta um orçamento (elenco, horas, transporte, show) e recebe o cálculo de preço em tempo real, hoje feito na tela clássica de "Calculadora de Orçamento".

**Why this priority**: É a ferramenta que gera negócio (orçamentos para clientes) — fluxo comercial crítico e de uso frequente, mas depende apenas dos módulos de precificação já existentes no backend (sem dependência das outras telas desta lista).

**Independent Test**: Pode ser testada sozinha preenchendo o formulário de orçamento (elenco, quantidade de horas, opção de show, transporte) e conferindo que o resultado de preço bate com o cálculo da tela clássica para os mesmos parâmetros.

**Acceptance Scenarios**:

1. **Given** a tela de Calculadora de Orçamento aberta na SPA, **When** o usuário preenche elenco/horas/transporte/show e envia, **Then** o resultado do orçamento (valores por faixa de hora, transporte, total) aparece na tela sem navegação para fora da SPA.
2. **Given** um resultado de orçamento calculado, **When** o usuário confirma, **Then** o orçamento é salvo no histórico para consulta posterior.

---

### User Story 3 - Gerenciar Gastos Recorrentes sem sair da SPA (Priority: P3)

Um usuário do Financeiro cadastra e administra despesas recorrentes (assinaturas, débitos automáticos, gastos programados), incluindo pagar, pular ou reabrir parcelas específicas.

**Why this priority**: Mesmo domínio financeiro do P1, usado com frequência regular (mensal/quinzenal) mas menos vezes por dia que aprovação de gastos avulsos.

**Independent Test**: Pode ser testada sozinha criando uma despesa recorrente, gerando/pagando uma parcela e reabrindo-a — sem depender das outras telas.

**Acceptance Scenarios**:

1. **Given** a tela de Gastos Recorrentes aberta na SPA, **When** o usuário cadastra uma nova despesa recorrente com frequência e valor, **Then** ela aparece na lista com as parcelas futuras previstas.
2. **Given** uma despesa recorrente ativa, **When** o usuário paga, pula ou exclui uma parcela específica, **Then** o estado da parcela é atualizado imediatamente na tela.
3. **Given** uma despesa recorrente, **When** o usuário a desativa (toggle), **Then** ela para de gerar novas parcelas mas o histórico permanece visível.

---

### User Story 4 - Consultar histórico de orçamentos e baixar PDF (Priority: P4)

Um usuário comercial revisita orçamentos já calculados, vê o detalhe de um orçamento salvo, baixa o PDF ou reenvia por e-mail para o cliente.

**Why this priority**: Depende conceitualmente do resultado gerado pela calculadora (P2), mas é uma jornada separada e menos frequente (consulta pós-venda, não geração ativa).

**Independent Test**: Pode ser testada sozinha abrindo o histórico, visualizando um orçamento previamente salvo (inclusive um registro "legado" anterior ao formato atual) e baixando o PDF correspondente.

**Acceptance Scenarios**:

1. **Given** a tela de Orçamentos (histórico) aberta na SPA, **When** o usuário lista os orçamentos salvos, **Then** vê nome do cliente, data e valor total de cada um, incluindo registros antigos em formato legado.
2. **Given** um orçamento do histórico selecionado, **When** o usuário pede o PDF, **Then** o arquivo é baixado com os mesmos dados exibidos na tela.
3. **Given** um orçamento do histórico selecionado, **When** o usuário envia por e-mail, **Then** recebe confirmação de envio na tela.

---

### User Story 5 - Configurar preços da calculadora sem sair da SPA (Priority: P5)

Um administrador ajusta os valores de referência (ator, cantor, técnico, coordenador, maquiador, itens especiais, tipos de acréscimo) usados pela Calculadora de Orçamento.

**Why this priority**: Tela de configuração usada esporadicamente (reajuste de preços), não no dia a dia — mas precisa estar em React para fechar o domínio de Ferramentas junto com P2/P4.

**Independent Test**: Pode ser testada sozinha alterando um valor de referência e conferindo que a próxima simulação na Calculadora de Orçamento reflete o novo valor.

**Acceptance Scenarios**:

1. **Given** a tela de Configuração de Preços aberta na SPA, **When** o administrador altera o valor de uma categoria (ex.: ator) e salva, **Then** a mudança é confirmada na tela e persiste para os próximos cálculos.
2. **Given** a lista de itens especiais, **When** o administrador adiciona ou remove um item especial, **Then** a lista atualizada aparece imediatamente e passa a estar disponível na Calculadora.

---

### User Story 6 - Avaliar elenco de um evento sem sair da SPA (Priority: P6)

Um usuário com acesso a Casting consulta as avaliações de desempenho do elenco por evento/período/categoria, incluindo a distribuição de notas, e pode alternar o modo de anonimato das avaliações.

**Why this priority**: Consulta de acompanhamento, não uma ferramenta operacional diária — menor urgência que Financeiro/Comercial, mas ainda faz parte da regra "zero link externo".

**Independent Test**: Pode ser testada sozinha aplicando filtros de período/categoria/evento e conferindo que a distribuição de notas e a lista de avaliações batem com a tela clássica para os mesmos filtros.

**Acceptance Scenarios**:

1. **Given** a tela de Avaliação de Casting aberta na SPA, **When** o usuário filtra por evento, período ou categoria, **Then** a lista de avaliações e a distribuição de notas são atualizadas de acordo.
2. **Given** o modo anônimo desligado, **When** um usuário autorizado o ativa, **Then** as avaliações passam a ser exibidas sem identificar o autor, conforme a configuração do sistema.

---

### User Story 7 - Gerenciar respostas de Formulários (lado Comercial) sem sair da SPA (Priority: P7)

Um usuário comercial revisa as respostas recebidas nos formulários públicos (pré-contrato, corporativo), associa/desassocia a um cliente, vincula/desvincula a um evento, exclui respostas indesejadas, busca respostas e edita a definição de campos de cada formulário.

**Why this priority**: Última fatia da lista — fluxo de retaguarda usado quando chega uma nova resposta de formulário, com cadência menor que os itens financeiros/comerciais anteriores.

**Independent Test**: Pode ser testada sozinha abrindo uma resposta de formulário existente, associando-a a um cliente e a um evento, e editando a definição de um campo do formulário — sem depender de nenhuma outra tela desta lista.

**Acceptance Scenarios**:

1. **Given** a tela de Formulários (Comercial) aberta na SPA, **When** o usuário busca ou filtra respostas, **Then** a lista é atualizada de acordo com o termo buscado.
2. **Given** uma resposta de formulário aberta, **When** o usuário a associa a um cliente e a um evento, **Then** os vínculos aparecem na tela e passam a refletir nas telas de Clientes/Agenda que já consultam esses vínculos.
3. **Given** o editor de campos de um formulário, **When** o usuário adiciona, edita, reordena ou exclui um campo (não de sistema), **Then** a mudança aparece imediatamente no formulário público correspondente.

---

### Edge Cases

- O que acontece se o usuário tentar acessar a URL antiga (`/gastos/`, `/orcamento/`, `/talents/avaliacoes`, `/formularios/`) diretamente pelo navegador? A rota Jinja continua funcionando (não foi removida), mas nenhum link dentro da SPA deve mais apontar para ela.
- Como o sistema trata um orçamento do histórico salvo em formato antigo (pré-existência do "snapshot" atual)? Deve ser exibido e gerar PDF corretamente via adaptação para o formato atual.
- O que acontece se o usuário tentar excluir uma parcela de gasto recorrente já paga, ou aprovar um gasto que já foi rejeitado? O sistema deve impedir a ação e mostrar mensagem de erro clara.
- O que acontece se dois usuários tentam aprovar/rejeitar o mesmo gasto ao mesmo tempo? A segunda ação deve falhar de forma clara (estado já alterado), sem duplicar o gasto.
- Como o sistema se comporta quando um usuário sem a permissão necessária (ex.: sem acesso a Financeiro) tenta acessar diretamente a URL de uma das 7 novas telas React? Deve ser bloqueado com a mesma regra de RBAC já aplicada nas telas clássicas equivalentes.
- O que acontece com um campo de formulário marcado como "campo de sistema" (`is_system`)? Não pode ser excluído nem ter a chave renomeada pelo editor.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O sistema DEVE oferecer uma tela React equivalente para cada uma das 7 ferramentas (Gastos Extras, Calculadora de Orçamento/Transporte, Gastos Recorrentes, Orçamentos/histórico, Configuração de Preços, Avaliação de Casting, Formulários/Comercial), com paridade funcional com a versão Jinja existente.
- **FR-002**: O menu de navegação da SPA (`navigation.tsx`) NÃO DEVE mais conter nenhum item marcado como link externo/redirecionamento para essas 7 áreas — todos devem apontar para rotas internas do React Router.
- **FR-003**: O sistema DEVE manter as rotas Jinja legadas das 7 áreas funcionando sem alteração de comportamento (estratégia strangler-fig, sem decommissioning nesta feature).
- **FR-004**: Toda ação de escrita nas 7 telas (criar, aprovar, rejeitar, excluir, vincular, pagar, pular, reabrir, ativar/desativar, editar campo, calcular, salvar configuração) DEVE ser refletida via chamada à API JSON e exibir estado de carregamento/erro/sucesso.
- **FR-005**: Toda ação destrutiva (excluir gasto, excluir parcela, excluir resposta de formulário, excluir campo, remover item especial de preço) DEVE pedir confirmação antes de executar.
- **FR-006**: O sistema DEVE aplicar as mesmas regras de RBAC já existentes nas telas clássicas equivalentes a cada uma das 7 novas telas React e suas respectivas APIs.
- **FR-007**: A tela de Orçamentos/histórico DEVE exibir corretamente tanto orçamentos no formato atual quanto orçamentos salvos em formato legado (pré-snapshot).
- **FR-008**: A geração de PDF de um orçamento do histórico DEVE produzir o mesmo conteúdo hoje gerado pela tela clássica.
- **FR-009**: A tela de Avaliação de Casting DEVE respeitar a configuração de modo anônimo do sistema ao exibir avaliações e permitir alternar esse modo.
- **FR-010**: O editor de campos de Formulários DEVE impedir exclusão ou renomeação de campos marcados como "campo de sistema".
- **FR-011**: Alterações feitas na Configuração de Preços DEVEM refletir imediatamente nos cálculos subsequentes feitos pela Calculadora de Orçamento.

### Key Entities

- **Gasto Especial (SpecialExpense)**: despesa extra pontual — descrição, categoria, valor, data, status (pendente/aprovado/rejeitado), tipo de repasse (reembolso/fornecedor), vínculo opcional a evento.
- **Despesa Recorrente (RecurringExpense) / Parcela (RecurringExpenseEntry)**: despesa que se repete em uma frequência (mensal/semanal/quinzenal/anual/programada); cada ocorrência vira uma parcela com seu próprio estado de pagamento.
- **Avaliação de Evento (EventRating) / Sub-avaliação (EventSubRating) / Histórico de Edição (EventRatingVersion)**: nota geral e notas por categoria (som, figurino, texto, coordenação, maquiagem, artista) dadas a um talento em um evento, com histórico de edições.
- **Resposta de Formulário (FormResponse) / Definição de Campo (FormFieldDefinition)**: submissão recebida de um formulário público e a estrutura configurável de campos por tipo de formulário.
- **Orçamento (OrcamentoHistory)**: registro de um cálculo de orçamento salvo, com snapshot dos dados de entrada e do resultado calculado.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% dos itens de menu da SPA relacionados às 7 ferramentas deixam de abrir tela fora da SPA (0 links externos remanescentes em `navigation.tsx` para essas áreas).
- **SC-002**: Um usuário consegue completar o fluxo principal de cada uma das 7 ferramentas (ex.: aprovar um gasto, calcular um orçamento, avaliar um evento) inteiramente dentro da SPA, sem nenhuma navegação de página inteira.
- **SC-003**: Para cada uma das 7 telas, os resultados calculados/exibidos (valores de orçamento, distribuição de notas, listas filtradas) são idênticos aos produzidos pela tela clássica equivalente, para as mesmas entradas.
- **SC-004**: Nenhuma regressão de permissão é introduzida — um usuário sem acesso a uma área continua bloqueado tanto na tela React quanto na API correspondente.

## Assumptions

- As 7 telas são de uso exclusivo de staff autenticado (mesmo público de `frontend/apps/internal`); não há necessidade de versão pública/anônima para nenhuma delas.
- Reaproveita-se a infraestrutura de API JSON e o design system (`AppLayout`, `PageHeader`, `DenseCard`, `@manto/ui`, `@manto/api-client`, `@manto/money`) já estabelecidos pela migração 144.
- As rotas Jinja legadas das 7 áreas permanecem no código como estão (mesma regra aplicada às migrações anteriores) — decommissioning é iniciativa futura separada.
- Não há mudança de regra de negócio nesta feature: a extração de lógica para módulos `*_ops.py` deve preservar o comportamento exato hoje existente nas views Jinja.
- O reenvio de orçamento por e-mail reaproveita o serviço de e-mail já usado por outras áreas do sistema (nenhum provedor novo é introduzido).
