# Feature Specification: Leitura e Gestão de Talentos e Figurino

**Feature Branch**: `154-talentos-figurino-leitura`

**Created**: 2026-07-21

**Status**: Draft

**Input**: User description: "Leitura e Gestão de Talentos e Figurino (US3, fatia P1) — migrar para React a base de leitura e as ações de gestão mais centrais dos módulos de Talentos (banco de talentos) e Figurino (fichas de figurino), hoje 100% Jinja: buscar/ver perfil de talento, aprovar/rejeitar pendente, editar cadastro, anotações internas; listar/criar/editar/excluir ficha de figurino."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Buscar e consultar talentos (Priority: P1)

Como Casting (ou qualquer pessoa da equipe), preciso buscar talentos no banco pela tela React
— por nome, ou filtrando por características (idioma, tamanho, altura, tags, personagem já
interpretado etc.) — e abrir o perfil completo de um talento para ver seus dados, documentos e
histórico de eventos, sem precisar abrir a tela antiga.

**Why this priority**: é a ação mais frequente do dia a dia do Casting — encontrar o talento
certo para um personagem. Sem isso, ninguém consegue abandonar a tela antiga.

**Independent Test**: pode ser testado sozinho — abrir a lista de talentos na tela React,
buscar por nome ou aplicar um filtro, abrir o perfil de um resultado e conferir que os dados
(contato, aparência, documentos, histórico de eventos com cachê total) aparecem certos.

**Acceptance Scenarios**:

1. **Given** a lista de talentos ativos, **When** o usuário busca por um nome (ou parte dele),
   **Then** a lista mostra só os talentos cujo nome ou nome artístico contém o texto buscado.
2. **Given** a lista de talentos ativos, **When** o usuário aplica um ou mais filtros
   (idioma, raça, tamanho, altura, passaporte/visto, tag, "já trabalhou com a Manto",
   personagem já interpretado), **Then** a lista mostra só os talentos que atendem a TODOS os
   filtros ativos, e os filtros aplicados ficam visíveis para remover individualmente.
3. **Given** uma lista de talentos, **When** o usuário abre o perfil de um talento,
   **Then** a tela mostra dados de contato, aparência, documentos (CPF/RG/PIX), veículo (se
   houver), anotação interna e nível de alerta (se o usuário pode ver), e o histórico de
   eventos do talento (personagens, datas, cachê recebido, total).
4. **Given** a aba "Pendentes", **When** o usuário abre a lista, **Then** vê só talentos com
   cadastro aguardando aprovação, separados dos ativos.
5. **Given** uma lista de talentos maior que uma página, **When** o usuário navega para a
   próxima página, **Then** vê o próximo grupo de resultados mantendo a busca/filtros ativos.

---

### User Story 2 - Aprovar ou rejeitar talento pendente (Priority: P2)

Como Casting, preciso aprovar um cadastro pendente (liberando o talento para escalação) ou
rejeitá-lo (removendo o cadastro), direto pela tela React.

**Why this priority**: fluxo de onboarding recorrente — todo cadastro público novo passa por
aqui antes de virar um talento disponível para escalar.

**Independent Test**: pode ser testado sozinho — na aba "Pendentes", aprovar um talento e
confirmar que ele passa a aparecer na aba "Ativos"; em outro, rejeitar e confirmar que o
cadastro desaparece da lista.

**Acceptance Scenarios**:

1. **Given** um talento pendente, **When** um usuário Casting/Superadmin aprova o cadastro,
   **Then** o talento passa a aparecer na aba "Ativos" e some da aba "Pendentes".
2. **Given** um talento pendente, **When** um usuário Casting/Superadmin rejeita o cadastro,
   **Then** o cadastro é removido e não aparece mais em nenhuma lista.
3. **Given** um usuário sem papel Casting/Superadmin, **When** ele tenta aprovar ou rejeitar,
   **Then** a ação é recusada (mesma regra de hoje).

---

### User Story 3 - Editar cadastro e anotações internas (Priority: P3)

Como Casting, preciso corrigir/completar os dados de um talento (contato, aparência,
documentos, PIX, veículo) e registrar uma anotação interna (com nível de alerta, quando
necessário) direto pela tela React.

**Why this priority**: manutenção de dados — importante, mas menos frequente que buscar/
consultar (US1) e que aprovar onboarding (US2).

**Independent Test**: pode ser testado sozinho — abrir o perfil de um talento, editar um campo
(ex.: telefone) e salvar, conferindo que o perfil reflete a mudança; em seguida, salvar uma
anotação interna com nível de alerta e confirmar que aparece no perfil.

**Acceptance Scenarios**:

1. **Given** o perfil de um talento, **When** um usuário Casting/Superadmin edita os dados
   (contato, aparência, documentos, PIX, veículo) e salva, **Then** o perfil passa a mostrar
   os novos valores.
2. **Given** o campo CPF, **When** um usuário Casting (não superadmin) tenta editá-lo,
   **Then** o campo não pode ser alterado por esse usuário (só superadmin edita CPF).
3. **Given** o perfil de um talento, **When** um usuário Casting/Superadmin salva uma anotação
   interna com nível de alerta (leve/moderado/grave), **Then** o perfil passa a mostrar a
   anotação e o indicador de alerta correspondente.
4. **Given** um usuário sem papel Casting/Superadmin, **When** ele tenta editar dados ou salvar
   anotação, **Then** a ação é recusada (mesma regra de hoje).

---

### User Story 4 - Consultar e gerir fichas de figurino (Priority: P4)

Como Figurino, preciso ver a lista de fichas de figurino (com aviso de quais personagens ainda
não têm ficha), criar uma ficha nova, editar uma existente (nome, peças, notas) ou excluir uma
ficha, tudo pela tela React.

**Why this priority**: fluxo do dia a dia do Figurino, mas com volume/urgência menor que a
busca de talentos e o onboarding.

**Independent Test**: pode ser testado sozinho — abrir a lista de fichas, criar uma nova com
nome e peças, editar a lista de peças de uma ficha existente, e excluir uma ficha, conferindo
que cada ação reflete na lista.

**Acceptance Scenarios**:

1. **Given** a lista de fichas de figurino, **When** a tela é aberta, **Then** mostra todas as
   fichas cadastradas e, se houver personagens já usados em eventos sem ficha correspondente,
   um aviso listando quais.
2. **Given** a lista de fichas, **When** um usuário Figurino/Superadmin cria uma ficha nova com
   nome do personagem e uma lista de peças (cada uma com quantidade), **Then** a ficha aparece
   na lista.
3. **Given** uma ficha existente, **When** um usuário Figurino/Superadmin edita o nome, as
   peças ou as notas e salva, **Then** a ficha passa a mostrar os novos valores.
4. **Given** uma ficha existente vinculada a cargos de eventos, **When** um usuário Figurino/
   Superadmin a exclui, **Then** a ficha é removida e os cargos que apontavam para ela deixam
   de ter ficha vinculada (sem erro).
5. **Given** um usuário sem papel Figurino/Superadmin, **When** ele tenta criar, editar ou
   excluir uma ficha, **Then** a ação é recusada (mesma regra de hoje); a lista continua
   visível normalmente.

---

### Edge Cases

- Busca de talento sem resultados → lista vazia com mensagem clara, sem erro.
- Combinação de filtros que não bate com nenhum talento → mesmo tratamento (lista vazia, sem
  erro).
- Tentar aprovar/rejeitar um talento que não está mais pendente (ex.: outra pessoa já agiu
  nele) → recusado com mensagem clara, sem duplicar a ação.
- Excluir uma ficha de figurino que nenhum cargo usa → funciona normalmente (nada para
  desvincular).
- Criar uma ficha com nome de personagem que já tem ficha → mesmo comportamento de hoje
  (permite duplicidade; não há checagem de unicidade no fluxo atual).
- Editar/anotar um talento cujo cadastro está pendente (ainda não aprovado) → permitido, mesma
  regra de hoje (edição não depende do status).
- Usuário autenticado sem nenhum papel especial (ex.: só Financeiro) → pode ver listas e
  perfis de talento e de figurino normalmente (leitura é aberta a qualquer autenticado), mas
  não vê nenhuma ação de edição/aprovação/criação/exclusão.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O sistema DEVE permitir que qualquer usuário autenticado busque talentos por
  nome/nome artístico e liste os resultados paginados, na tela React.
- **FR-002**: O sistema DEVE permitir filtrar a lista de talentos ativos por idioma, raça,
  tamanho de roupa (superior/inferior), tamanho de calçado, altura (com operador maior/menor
  ou igual), status de passaporte/visto, tags, personagem já interpretado e "já trabalhou com
  a Manto", combináveis entre si.
- **FR-003**: O sistema DEVE mostrar separadamente, em abas, os talentos ativos e os
  pendentes de aprovação.
- **FR-004**: O sistema DEVE mostrar, no perfil de um talento, seus dados de contato,
  aparência, documentos (CPF/RG/PIX), dados de veículo (quando houver), anotação interna e
  nível de alerta, e o histórico de eventos em que participou (personagem, data, cachê,
  evento), incluindo o total de cachê recebido.
- **FR-005**: O sistema DEVE permitir que um usuário CASTING/SUPERADMIN aprove um talento
  pendente, tornando-o ativo.
- **FR-006**: O sistema DEVE permitir que um usuário CASTING/SUPERADMIN rejeite um talento
  pendente, removendo o cadastro; DEVE recusar a rejeição de um talento que não está mais
  pendente.
- **FR-007**: O sistema DEVE permitir que um usuário CASTING/SUPERADMIN edite os dados de um
  talento (contato, aparência, documentos exceto CPF, PIX, veículo); o campo CPF só pode ser
  editado por um usuário SUPERADMIN.
- **FR-008**: O sistema DEVE permitir que um usuário CASTING/SUPERADMIN salve uma anotação
  interna (texto) e um nível de alerta (nenhum/leve/moderado/grave) para um talento.
- **FR-009**: O sistema DEVE recusar qualquer ação de aprovar/rejeitar/editar/anotar talento
  para um usuário que não seja CASTING ou SUPERADMIN (mesma regra de hoje).
- **FR-010**: O sistema DEVE permitir que qualquer usuário autenticado veja a lista de fichas
  de figurino, incluindo o aviso de quais personagens já usados em eventos ainda não têm ficha
  correspondente.
- **FR-011**: O sistema DEVE permitir que um usuário FIGURINO/SUPERADMIN crie uma ficha de
  figurino nova com nome do personagem, lista de peças (nome + quantidade) e notas.
- **FR-012**: O sistema DEVE permitir que um usuário FIGURINO/SUPERADMIN edite o nome, as
  peças e as notas de uma ficha existente.
- **FR-013**: O sistema DEVE permitir que um usuário FIGURINO/SUPERADMIN exclua uma ficha de
  figurino, desvinculando automaticamente qualquer cargo de evento que apontava para ela (sem
  erro).
- **FR-014**: O sistema DEVE recusar qualquer ação de criar/editar/excluir ficha de figurino
  para um usuário que não seja FIGURINO ou SUPERADMIN (mesma regra de hoje).
- **FR-015**: O fluxo de leitura e gestão de talentos/figurino na tela antiga (Jinja) DEVE
  continuar funcionando sem nenhuma mudança de comportamento enquanto ela existir, em paralelo
  à tela React.

### Key Entities

- **Talento (Talent)**: pessoa cadastrada no banco de talentos; tem status (pendente/ativo),
  dados de contato, aparência física, documentos, PIX, veículo, anotação interna e nível de
  alerta. Um talento participa de eventos através de cargos.
- **Ficha de Figurino (FigurinoSheet)**: descreve o figurino de um personagem — nome do
  personagem, lista de peças (cada uma com quantidade) e notas. Pode estar vinculada a um ou
  mais cargos de evento com aquele personagem.
- **Cargo de Evento (EventRole)**: já existente (features 145-153) — vínculo entre um evento,
  um personagem e (opcionalmente) um talento e uma ficha de figurino; é a fonte do histórico
  de eventos exibido no perfil do talento e do aviso de "personagens sem ficha".

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Um usuário Casting consegue encontrar um talento específico e abrir seu perfil
  completo em menos de 15 segundos, sem abrir a tela antiga.
- **SC-002**: Um usuário Casting consegue aprovar ou rejeitar um cadastro pendente inteiramente
  pela tela React, sem precisar da tela antiga.
- **SC-003**: 100% dos dados hoje visíveis no perfil do talento (contato, aparência,
  documentos, PIX, veículo, anotação, histórico de eventos com total de cachê) aparecem na
  tela React.
- **SC-004**: Um usuário Figurino consegue listar, criar, editar e excluir uma ficha de
  figurino inteiramente pela tela React.
- **SC-005**: O comportamento da tela antiga (Jinja) para os mesmos fluxos permanece idêntico
  ao de antes desta fatia, verificado por paridade automatizada entre os dois caminhos.

## Assumptions

- Upload de foto/documento do talento (rosto, corpo inteiro, documento, CNH) e upload/rotação
  de foto de ficha de figurino ficam fora desta fatia — mesmo padrão da migração de Agenda
  (upload só entrou depois que leitura+escrita sem arquivo estavam prontas, feature 153). O
  perfil do talento na tela React mostra as fotos/documentos já existentes (se houver), só não
  permite enviar um novo nesta fatia.
- Impressão de ficha de figurino (single ou em lote por evento) é um documento imprimível, não
  uma tela de trabalho — continua servida pela tela antiga; a tela React de figurino pode
  linkar para a impressão existente sem reimplementá-la.
- Sincronização com Google Drive de fichas de figurino é uma ferramenta de migração legada
  (SSE, uso pontual) — fica inteiramente fora, só na tela antiga.
- O dashboard de avaliações de talentos (`/talents/avaliacoes`) é uma tela própria e separada
  do perfil do talento — fica fora desta fatia, para uma fatia futura se necessário.
- Reset de senha do portal do talento é uma rota sem uso hoje (nenhum link na interface atual)
  — fica fora desta fatia; não é migrada nem removida.
- Importação de talentos via Google Sheets é uma ferramenta administrativa pontual — continua
  Jinja-only, fora desta fatia.
- O portal do próprio talento (login do ator para ver a própria ficha) é um módulo separado do
  painel interno — não faz parte desta fatia.
- Assim como hoje, ver a lista/perfil de talentos e a lista de fichas de figurino continua
  aberto a qualquer usuário autenticado, sem exigir papel específico — só as ações de escrita
  são restritas (CASTING/SUPERADMIN para talento, FIGURINO/SUPERADMIN para figurino).
- "Rejeitar" um talento pendente continua sendo uma exclusão definitiva do cadastro (não existe
  hoje um estado "rejeitado" separado) — esta fatia preserva esse comportamento, não introduz
  um novo estado.
