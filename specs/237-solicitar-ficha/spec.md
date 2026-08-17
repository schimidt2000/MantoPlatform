# Feature Specification: Solicitar ficha de figurino a partir da busca

**Feature Branch**: `237-solicitar-ficha`

**Created**: 2026-08-14

**Status**: Draft

**Input**: User description: "Solicitar ficha de figurino a partir da busca: o FigurinoPicker (porta única de escolha de ficha, usado em evento, catálogo e produção) ganha um botão 'Solicitar ficha' para quando a pesquisa não encontra o personagem — abre um mini-formulário (nome do personagem pré-preenchido com o que foi digitado + observação opcional) e cria um pedido do NOVO TIPO 'ficha' no módulo Produção e Compras do figurino (feature 225), sem valores nem compra, com fluxo solicitado → em andamento → concluído; concluir exige vincular a ficha recém-criada (pelo próprio picker), fechando o loop para o solicitante; o pedido registra quem solicitou e de onde veio."

## Contexto

Quem procura uma ficha de figurino (no evento, no catálogo ou na produção) usa sempre a mesma
busca visual — e quando o personagem ainda não tem ficha, o pedido para criá-la sai do sistema:
vira mensagem de voz ou lembrete solto para a equipe de figurino. A feature liga a ponta que
falta: da própria busca, um clique registra "essa ficha precisa existir" na fila de trabalho que
o figurino já usa todos os dias (Produção e Compras, feature 225), sem inventar uma superfície
nova.

## Decisões já tomadas com o dono do produto

Conversa de 14/08/2026:

1. O pedido de ficha entra como **novo TIPO no módulo Produção e Compras** — mesma fila, mesmos
   responsáveis, sem valores nem compra (as duas ideias do dono convergem: o módulo 225 já é a
   área de tarefas do figurino).
2. **Concluir exige vincular a ficha recém-criada** (escolhida pela própria busca) — o pedido
   termina apontando para a ficha e o solicitante a encontra com um clique.
3. O botão vive na **busca única** (a porta por onde todas as telas escolhem ficha), então
   aparece automaticamente em todos os lugares.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Pedir a ficha que não existe, sem sair da busca (Priority: P1)

O comercial está escalando um personagem novo num evento, pesquisa a ficha e não encontra.
No rodapé da própria busca clica em "Solicitar ficha", confere o nome (já preenchido com o que
digitou), escreve uma observação se quiser, e envia. O pedido aparece na fila de Produção e
Compras do figurino como tipo "Ficha", com quem pediu e de onde veio.

**Why this priority**: é o coração da feature — sem o botão, nada existe.

**Independent Test**: em qualquer tela com a busca de ficha, pesquisar um nome inexistente,
solicitar e conferir o pedido na fila do figurino.

**Acceptance Scenarios**:

1. **Given** a busca de ficha aberta em qualquer tela, **When** o usuário digita um nome sem
   resultado e clica em "Solicitar ficha", **Then** abre um mini-formulário com o nome
   pré-preenchido com o texto digitado e um campo de observação opcional.
2. **Given** o mini-formulário preenchido, **When** o usuário envia, **Then** um pedido do tipo
   "Ficha" é criado em Produção e Compras com status inicial "solicitado", registrando quem
   pediu e a tela de origem, e o usuário recebe confirmação visual.
3. **Given** um nome vazio, **When** o usuário tenta enviar, **Then** o envio é bloqueado com
   erro apontado no campo.
4. **Given** a busca COM resultados, **When** o usuário rola a lista, **Then** o botão
   "Solicitar ficha" continua disponível no rodapé (o personagem certo pode não estar entre os
   parecidos).

---

### User Story 2 - O figurino trabalha o pedido na fila de sempre (Priority: P2)

A equipe de figurino vê o pedido tipo "Ficha" na fila de Produção e Compras, com o filtro/rótulo
próprio do tipo. O fluxo é curto — solicitado → em andamento → concluído — sem aprovação, sem
valores, sem compra. Para concluir, escolhe a ficha recém-criada na própria busca: o pedido
termina vinculado a ela.

**Why this priority**: fecha o loop do lado de quem executa; depende da US1 para existir pedido.

**Independent Test**: mover um pedido tipo "Ficha" pelo fluxo até concluir, vinculando a ficha.

**Acceptance Scenarios**:

1. **Given** um pedido tipo "Ficha" na fila, **When** a equipe o visualiza, **Then** ele mostra
   o nome do personagem, a observação, quem pediu, a origem e o rótulo do tipo — sem campos de
   custo/fornecedor.
2. **Given** o pedido em andamento, **When** a equipe tenta concluir SEM vincular uma ficha,
   **Then** a conclusão é bloqueada com mensagem clara.
3. **Given** a ficha criada no acervo, **When** a equipe conclui o pedido escolhendo-a na busca,
   **Then** o pedido fica concluído apontando para a ficha.
4. **Given** um pedido cancelado (personagem desistido), **When** a equipe cancela com motivo,
   **Then** o pedido sai da fila aberta (regra atual do módulo).

---

### Edge Cases

- Pedido duplicado (dois vendedores pedem o mesmo personagem): permitido — a equipe de figurino
  enxerga os dois na fila e cancela um com motivo (sem trava de unicidade; nomes variam).
- Já existe ficha homônima: o pedido é criado mesmo assim (pode ser variação legítima do
  personagem); a equipe decide.
- O solicitante perde acesso/sai: o pedido permanece (registro histórico, como nos demais tipos).
- Busca usada dentro do próprio módulo de produção (ex.: vincular ficha a um pedido): o botão
  aparece ali também — comportamento idêntico, sem caso especial.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: A busca única de ficha DEVE exibir a ação "Solicitar ficha" no rodapé da lista de
  resultados (com e sem resultados), em todas as telas que a usam.
- **FR-002**: A ação DEVE abrir um mini-formulário com: nome do personagem (obrigatório,
  pré-preenchido com o texto pesquisado) e observação (opcional), com feedback de envio.
- **FR-003**: O envio DEVE criar um pedido do tipo "Ficha" no módulo Produção e Compras com
  status inicial "solicitado", sem campos de valor/compra, registrando o solicitante e a tela
  de origem.
- **FR-004**: O tipo "Ficha" DEVE ter fluxo próprio curto — solicitado → em andamento →
  concluído (+ cancelamento com motivo, como os demais) — **sem etapa de aprovação**.
- **FR-005**: Concluir um pedido do tipo "Ficha" DEVE exigir o vínculo com uma ficha existente
  do acervo (escolhida pela busca única); a conclusão sem vínculo é bloqueada com mensagem.
- **FR-006**: A fila, os filtros e o cabeçalho do módulo DEVEM reconhecer o novo tipo (rótulo
  "Ficha"), e o pedido concluído DEVE exibir o link da ficha vinculada.
- **FR-007**: Qualquer papel com acesso à busca de ficha PODE solicitar; a gestão do pedido
  segue as permissões atuais do módulo de Produção e Compras.
- **FR-008**: Os demais tipos (produção, manutenção, compra) NÃO mudam de comportamento.

### Key Entities

- **Pedido de Produção (existente)**: ganha o valor de tipo "ficha"; usa campos já existentes —
  título (nome do personagem), descrição (observação + origem), solicitante, responsável,
  vínculo opcional com ficha (obrigatório na conclusão deste tipo). Sem colunas novas.
- **Busca única de ficha (existente)**: ganha a ação de solicitar; nenhum dado novo.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: De qualquer uma das telas com a busca, solicitar uma ficha leva menos de 30
  segundos (pesquisou → clicou → confirmou).
- **SC-002**: 100% dos pedidos criados aparecem na fila de Produção e Compras com tipo "Ficha",
  solicitante e origem corretos.
- **SC-003**: Nenhum pedido do tipo "Ficha" consegue ser concluído sem ficha vinculada; 100%
  dos concluídos exibem o link da ficha.
- **SC-004**: Os fluxos dos tipos existentes permanecem intocados (verificação de regressão do
  módulo passa).

## Assumptions

- Sem migração de banco: o tipo é um valor novo numa coluna existente e o fluxo curto reusa os
  status existentes do módulo.
- A "origem" registrada é a tela de onde a busca foi aberta (texto automático na descrição),
  suficiente para contexto — sem vínculo estruturado com evento nesta versão.
- Responsáveis elegíveis do tipo "Ficha" seguem a regra dos tipos de oficina (produção/
  manutenção), não a do tipo compra.
- Notificação ativa ao solicitante quando concluir fica fora do escopo (ele encontra pela
  busca ou pelo pedido); pode virar melhoria futura.
