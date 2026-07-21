# Feature Specification: Upload e Gestão de Anexos do Evento

**Feature Branch**: `153-upload-anexos-evento`

**Created**: 2026-07-21

**Status**: Draft

**Input**: User description: "Upload e Gestão de Anexos/Arquivos do Evento (fecha US2 - Agenda e Eventos) — migrar para a tela React do evento os fluxos de anexo de arquivo que as features 149-152 deixaram só no Jinja: nota fiscal, contrato, comprovante de pagamento de cachê, comprovante de reembolso e observação com imagem."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Nota fiscal e contrato do evento (Priority: P1)

Como Comercial/Financeiro, ao abrir a tela de um evento no React eu preciso anexar a nota
fiscal e o contrato assinado do evento, e ver os que já foram anexados — hoje a nota fiscal
não aparece em lugar nenhum da tela React e o contrato aparece na base de dados mas não é
mostrado nem pode ser anexado por lá, obrigando a equipe a voltar para a tela antiga (Jinja)
sempre que precisa desses dois documentos.

**Why this priority**: são os dois documentos que mais bloqueiam a equipe comercial/financeira
a abandonar a tela antiga — sem eles, ninguém consegue usar só a tela React no dia a dia do
evento.

**Independent Test**: pode ser testado sozinho — abrir um evento na tela React, anexar um
arquivo de nota fiscal e um de contrato, recarregar a página e confirmar que ambos aparecem
na lista com opção de abrir/baixar o arquivo.

**Acceptance Scenarios**:

1. **Given** um evento sem nenhuma nota fiscal anexada, **When** o usuário Comercial/Financeiro
   envia um arquivo de nota fiscal pela tela do evento, **Then** o arquivo é salvo, a nota
   passa a aparecer na lista de notas fiscais do evento com link para abrir/baixar.
2. **Given** um evento sem contrato anexado, **When** o usuário envia o arquivo do contrato
   assinado (com valor e indicação de "assinado" opcionais), **Then** o contrato aparece na
   lista de contratos do evento com link para abrir/baixar.
3. **Given** um evento com nota fiscal ou contrato já anexados, **When** a tela do evento é
   aberta, **Then** a lista mostra todos os arquivos já enviados, sem precisar abrir a tela
   antiga.
4. **Given** um usuário sem papel Comercial/Financeiro/SUPERADMIN, **When** ele abre a tela do
   evento, **Then** ele não vê a opção de anexar nem a lista de notas fiscais/contratos (mesma
   regra de visibilidade já aplicada hoje ao restante do bloco comercial/financeiro).
5. **Given** um contrato já anexado, **When** um usuário SUPERADMIN marca/desmarca "assinado"
   ou exclui o contrato, **Then** a lista reflete a mudança imediatamente; qualquer outro
   papel não vê essas duas ações.

---

### User Story 2 - Comprovante de pagamento de cachê (Priority: P2)

Como Financeiro, preciso anexar o comprovante de um pagamento de cachê feito a um talento
diretamente na tela do evento em React, ver os comprovantes já anexados (com link para
abrir/baixar) e, quando eu for SUPERADMIN, corrigir o valor ou excluir um comprovante lançado
errado — hoje isso só é possível na tela antiga.

**Why this priority**: fluxo financeiro recorrente (todo evento pago gera um lançamento), mas
menos bloqueante que nota fiscal/contrato porque o financeiro já tem outras telas para
acompanhar pagamentos.

**Independent Test**: pode ser testado sozinho — anexar um comprovante de pagamento com valor
na tela do evento, confirmar que aparece na lista com o link do arquivo; como SUPERADMIN,
editar o valor e depois excluir o lançamento, confirmando que ele some da lista.

**Acceptance Scenarios**:

1. **Given** um evento, **When** o usuário Financeiro informa um valor e anexa o arquivo do
   comprovante de pagamento, **Then** o pagamento é registrado e aparece na lista de
   pagamentos do evento com link para abrir/baixar o comprovante.
2. **Given** um valor informado sem arquivo anexado (ou arquivo sem valor), **When** o usuário
   tenta enviar, **Then** o sistema recusa com uma mensagem clara indicando o campo faltante,
   sem criar nenhum registro.
3. **Given** um comprovante de pagamento já lançado, **When** um usuário SUPERADMIN corrige o
   valor, **Then** o novo valor é refletido na lista imediatamente.
4. **Given** um comprovante de pagamento já lançado, **When** um usuário SUPERADMIN exclui o
   lançamento, **Then** ele deixa de aparecer na lista de pagamentos do evento.
5. **Given** um usuário que não é SUPERADMIN, **When** ele tenta editar ou excluir um
   comprovante já lançado, **Then** a ação é recusada (mesma regra de hoje).

---

### User Story 3 - Comprovante de reembolso (Priority: P3)

Como Comercial/Financeiro, preciso anexar o comprovante do gasto original ao registrar um
reembolso a cobrar da cliente, e depois anexar o comprovante de recebimento quando o
reembolso for efetivamente cobrado — hoje os dois uploads só existem na tela antiga; a tela
React de hoje já mostra a lista de reembolsos e seus valores, mas sem nenhum dos dois
arquivos.

**Why this priority**: fluxo financeiro válido mas de menor frequência que pagamento de
cachê — a maioria dos eventos não gera reembolso.

**Independent Test**: pode ser testado sozinho — registrar um novo reembolso com comprovante
do gasto anexado, confirmar que aparece na lista; depois marcar esse reembolso como cobrado
anexando o comprovante de recebimento e valor recebido, confirmando que o status muda para
"cobrado" com o link do comprovante.

**Acceptance Scenarios**:

1. **Given** um evento, **When** o usuário registra um novo reembolso com descrição, valor e
   (opcionalmente) o comprovante do gasto original, **Then** o reembolso aparece na lista como
   pendente, com link para o comprovante quando enviado.
2. **Given** um reembolso pendente, **When** o usuário informa o valor recebido e anexa o
   comprovante de recebimento, **Then** o reembolso passa a aparecer como "cobrado", com o
   valor recebido e o link do comprovante.
3. **Given** um reembolso pendente, **When** o usuário tenta marcar como cobrado sem anexar o
   comprovante de recebimento, **Then** o sistema recusa com mensagem clara, sem alterar o
   status do reembolso.
4. **Given** um reembolso já marcado como cobrado, **When** o usuário tenta marcar como cobrado
   de novo, **Then** o sistema recusa (mesma regra de hoje — não é possível cobrar duas
   vezes).
5. **Given** um reembolso já registrado (cobrado ou não), **When** um usuário SUPERADMIN o
   exclui, **Then** ele deixa de aparecer na lista; qualquer outro papel não vê essa ação.

---

### User Story 4 - Observação do evento com imagem (Priority: P4)

Como usuário com acesso ao evento, preciso anexar uma imagem como observação do evento pela
tela React — hoje só consigo criar observações de texto ou link por lá (feature 150); a
observação de imagem já é exibida quando existe, mas só pode ser criada na tela antiga.

**Why this priority**: fecha a última lacuna de uma migração já quase completa (observações);
uso pontual comparado às notas fiscais/contratos/pagamentos.

**Independent Test**: pode ser testado sozinho — na tela do evento em React, adicionar uma
observação do tipo imagem enviando um arquivo, e confirmar que ela aparece na lista de
observações exibindo a imagem, do mesmo jeito que uma observação de imagem criada na tela
antiga.

**Acceptance Scenarios**:

1. **Given** um evento, **When** o usuário adiciona uma observação do tipo imagem com um
   arquivo válido, **Then** a observação é criada e a imagem aparece na lista de observações
   do evento.
2. **Given** uma tentativa de observação do tipo imagem sem arquivo, **When** o usuário envia,
   **Then** o sistema recusa com mensagem clara, sem criar a observação.

---

### Edge Cases

- Arquivo maior que o limite de tamanho aceito (mesmo limite já aplicado hoje pela tela
  antiga: 10 MB para nota fiscal/contrato/comprovantes, 20 MB para observação-imagem) → envio
  recusado com mensagem clara, nenhum registro é criado.
- Tipo de arquivo/extensão qualquer aceito hoje pela tela antiga (sem lista de extensões
  permitidas) continua aceito pela tela React — nenhuma nova restrição de tipo é introduzida
  por esta fatia.
- Falha de rede/timeout durante o envio → usuário vê mensagem de erro amigável e pode tentar
  novamente; nenhum registro parcial (arquivo salvo sem o registro correspondente, ou
  vice-versa) fica visível na tela.
- Usuário sem o papel necessário tentando anexar/editar/excluir por fora da tela (chamando a
  ação diretamente) → recusado com a mesma regra de permissão já aplicada nas telas
  equivalentes de hoje.
- Envio de mais de um arquivo na mesma ação onde a tela antiga permite múltiplos (ex.:
  vários comprovantes de pagamento ao criar o evento) está fora do escopo desta fatia — aqui
  cada ação de anexar trata um arquivo por vez, no contexto de um evento já existente.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O sistema DEVE permitir que um usuário Comercial/Financeiro/SUPERADMIN anexe um
  arquivo de nota fiscal a um evento existente pela tela React, e listar as notas fiscais já
  anexadas ao evento (hoje isso não aparece na tela React em nenhuma forma).
- **FR-002**: O sistema DEVE permitir que um usuário Comercial/Financeiro/SUPERADMIN anexe um
  arquivo de contrato a um evento existente pela tela React, e mostrar a lista de contratos já
  anexados (hoje já existe no retorno da API, mas não é exibida na tela).
- **FR-003**: O sistema DEVE permitir que um usuário Financeiro/SUPERADMIN registre um
  pagamento de cachê com valor e comprovante anexado pela tela React, recusando o envio se
  faltar valor ou arquivo.
- **FR-004**: O sistema DEVE mostrar, para quem já vê a lista de pagamentos hoje
  (Financeiro/SUPERADMIN), um link para abrir/baixar o comprovante de cada pagamento
  (atualmente a lista mostra valor e data, mas não o arquivo).
- **FR-005**: O sistema DEVE permitir que um usuário SUPERADMIN corrija o valor de um
  comprovante de pagamento já lançado, e recusar essa ação para qualquer outro papel.
- **FR-006**: O sistema DEVE permitir que um usuário SUPERADMIN exclua um comprovante de
  pagamento já lançado, e recusar essa ação para qualquer outro papel.
- **FR-007**: O sistema DEVE permitir registrar um novo reembolso a cobrar da cliente com
  descrição, valor e, opcionalmente, o comprovante do gasto original anexado.
- **FR-008**: O sistema DEVE permitir marcar um reembolso pendente como cobrado, exigindo valor
  recebido e comprovante de recebimento; DEVE recusar a ação se faltar o comprovante ou se o
  reembolso já estiver marcado como cobrado.
- **FR-009**: O sistema DEVE mostrar, na lista de reembolsos já exibida hoje, os links para o
  comprovante do gasto original (quando existir) e para o comprovante de recebimento (quando o
  reembolso já foi cobrado) — nenhum dos dois aparece hoje.
- **FR-010**: O sistema DEVE permitir criar uma observação do tipo imagem pela tela React,
  recusando o envio se não houver arquivo anexado.
- **FR-011**: Todo envio de arquivo desta fatia DEVE respeitar o mesmo limite de tamanho já
  aplicado pela tela antiga para aquele tipo de anexo (10 MB para nota fiscal/contrato/
  comprovante de pagamento/comprovante de reembolso; 20 MB para imagem de observação),
  recusando arquivos maiores com mensagem clara.
- **FR-012**: Toda ação desta fatia DEVE respeitar exatamente as mesmas regras de permissão
  (papel necessário) já aplicadas hoje ao fluxo equivalente na tela antiga — nenhum novo nível
  de acesso é criado.
- **FR-013**: O fluxo de anexo de arquivo na tela antiga (Jinja) DEVE continuar funcionando sem
  nenhuma mudança de comportamento enquanto ela existir, em paralelo à tela React.
- **FR-014**: O sistema DEVE permitir que um usuário SUPERADMIN exclua um contrato já anexado,
  e marque/desmarque um contrato como "assinado", pela tela React; DEVE recusar as duas ações
  para qualquer outro papel.
- **FR-015**: O sistema DEVE permitir que um usuário SUPERADMIN exclua um reembolso já
  registrado (cobrado ou não) pela tela React; DEVE recusar essa ação para qualquer outro
  papel.
- **FR-016**: O sistema NÃO DEVE introduzir uma ação de excluir nota fiscal — essa ação não
  existe hoje em nenhuma tela (a nota fiscal só é removida indiretamente, editando a lista
  completa de notas no formulário de dados comerciais/venda, fora do escopo — ver Assumptions)
  e fica fora do escopo desta fatia.

### Key Entities

- **Nota Fiscal (EventInvoice)**: nota fiscal de um evento; tem valor, data de emissão,
  status (a emitir / emitida) e o arquivo da nota. Um evento pode ter mais de uma. Esta fatia
  cobre anexar o arquivo pela tela do evento; a tarefa de "marcar como emitida" no painel
  financeiro (tela separada) não faz parte desta fatia.
- **Contrato (EventContract)**: contrato assinado de um evento; tem o arquivo, valor opcional
  e indicação de assinado. Um evento pode ter mais de um.
- **Comprovante de Pagamento (EventPayment)**: comprovante de um cachê pago a um talento; tem
  valor, data e o arquivo do comprovante. Um evento pode ter vários.
- **Reembolso (EventReimbursement)**: valor que a empresa adiantou num evento e precisa cobrar
  da cliente; tem descrição, valor a cobrar, comprovante do gasto original (opcional na
  criação), e — quando cobrado — valor recebido e comprovante de recebimento.
- **Observação com imagem (EventObservation, obs_type="image")**: observação do evento cujo
  conteúdo é uma imagem anexada, com legenda opcional.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Um usuário Comercial/Financeiro consegue anexar nota fiscal, contrato,
  comprovante de pagamento e comprovante de reembolso de um evento inteiramente pela tela
  React, sem precisar abrir a tela antiga em nenhum momento do fluxo.
- **SC-002**: 100% dos anexos existentes de um evento (nota fiscal, contrato, comprovante de
  pagamento, comprovante de reembolso, observação-imagem) ficam visíveis e abríveis/baixáveis
  na tela React do evento.
- **SC-003**: Toda tentativa de envio sem os dados obrigatórios (arquivo ou valor faltando) é
  recusada com uma mensagem clara em menos de 1 segundo após o envio, sem deixar registro
  parcial.
- **SC-004**: O comportamento da tela antiga (Jinja) para os mesmos fluxos permanece idêntico
  ao de antes desta fatia, verificado por paridade automatizada entre os dois caminhos.

## Assumptions

- "Anexos/Arquivos do Evento" cobre exatamente os cinco fluxos que as features 149-152
  deixaram só no Jinja: nota fiscal, contrato, comprovante de pagamento de cachê, comprovante
  de reembolso (duas etapas: gasto original e recebimento) e observação com imagem — mesmo
  escopo descrito no pedido original desta fatia.
- Fotos de ficha de figurino, upload do catálogo público e da revisão de mídia estão fora do
  escopo (já migrados/têm fluxo próprio, confirmado no pedido original).
- Materiais de ensaio (`EnsaioMaterial`, upload de arquivo/link vinculado a evento) também
  ficam fora do escopo desta fatia: não fazem parte da lista de itens adiados pelas features
  149-152 e não são consumidos pela tela de evento que esta fatia está fechando — migração
  própria, se necessária, fica para uma fatia futura.
- A tarefa "marcar nota fiscal como emitida" do painel financeiro (`/financeiro/nf/<id>/
  emitir`) é uma tela separada (fila de pendências do Financeiro, não a tela do evento) e fica
  fora do escopo — esta fatia cobre apenas o anexo de nota fiscal a partir da tela do evento.
- "Ver/baixar/remover" do pedido original se aplica plenamente a comprovante de pagamento,
  contrato (excluir + marcar assinado) e reembolso (excluir) — todos já editáveis/excluíveis
  por SUPERADMIN na tela antiga — e como "ver/baixar" (sem remover) para nota fiscal, cuja
  única forma de remoção hoje é indireta (editar a lista completa no formulário de dados
  comerciais/venda, fora do escopo desta fatia).
- O armazenamento do arquivo em si (onde o arquivo físico é salvo — volume local/Railway,
  `USE_S3=false`) não muda nesta fatia; é o mesmo mecanismo já usado por todo o resto do
  sistema (features 087/133).
- Envio de múltiplos comprovantes de pagamento/contrato em uma única ação (hoje só possível no
  momento da criação do evento, feature 152 — `payment_files[]`) fica fora do escopo: esta
  fatia cobre anexar um arquivo por vez a um evento já existente, que é como a tela antiga
  permite anexar depois que o evento já foi criado.
- A nota fiscal, na tela antiga, vive dentro do formulário maior de "dados comerciais/venda"
  (valor de venda, acréscimos, clientes, `with_invoice`), com uma lista reconciliável (adicionar/
  editar/remover várias notas de uma vez ao salvar o formulário inteiro). Migrar esse formulário
  inteiro não é o objetivo desta fatia (é a edição comercial do evento, ainda inteiramente
  Jinja). Por isso, para nota fiscal, esta fatia cobre apenas ADICIONAR uma nova nota (valor,
  data, arquivo opcional) como ação isolada — sem editar/remover notas existentes nem mexer no
  campo `with_invoice` — mesmo padrão aditivo de "adicionar" já usado por contrato/pagamento/
  reembolso. Editar ou remover uma nota fiscal continua exigindo a tela antiga.
