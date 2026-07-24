# Feature Specification: Reconstrução do Formulário de Cadastro/Edição de Eventos

**Feature Branch**: `184-eventos-formulario-completo`

**Created**: 2026-07-24

**Status**: Draft

**Input**: User description: "Refatorar e aperfeiçoar por completo o formulário de Cadastro/Edição de Eventos (/events/new e /events/[id]/edit) no app Beta — tela mais crítica do comercial, exige 100% de paridade de campos com a versão Live, organização em 7 blocos e validação com feedback visual imediato e auto-scroll ao primeiro erro."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Vendedor cadastra um evento novo com todos os campos do sistema atual (Priority: P1) 🎯 MVP

Um vendedor (papel COMERCIAL) abre "Novo evento" e encontra, organizados em blocos claros e densos, absolutamente todos os campos que hoje existem espalhados na versão em produção: cliente e pré-contrato, dados do evento, elenco, valores e comissões, forma de pagamento com comprovantes, contrato e observações (inclusive com foto) — sem precisar abrir a tela antiga para nada.

**Why this priority**: É a tela mais usada e mais crítica do comercial; qualquer campo faltando hoje obriga o vendedor a voltar para a tela antiga, quebrando o fluxo e gerando risco de dado divergente entre as duas telas.

**Independent Test**: Preencher um evento do zero cobrindo os 7 blocos (incluindo cadastro rápido de cliente, comprovante de pagamento, contrato e uma observação com foto) e confirmar que o evento é criado com todos os dados, idêntico ao que a tela antiga produziria.

**Acceptance Scenarios**:

1. **Given** o vendedor está em "Novo evento", **When** ele busca e seleciona um cliente já cadastrado, **Then** o cliente aparece na lista de associados com um seletor de relação (Contratante, Assessora, Mãe/Pai, Familiar, Outros).
2. **Given** o cliente não existe ainda, **When** o vendedor clica "+ Cadastrar novo cliente" e preenche nome e telefone, **Then** o cliente é criado (ou reaproveitado, se o telefone já existir) e adicionado à lista de associados sem sair da tela.
3. **Given** o vendedor digita ao menos 2 personagens no Bloco de Elenco, **When** ele clica "Gerar título automaticamente", **Then** o campo Título é preenchido no padrão `(TIPO) PERSONAGEM 1 + PERSONAGEM 2`, e deixa de ser sobrescrito automaticamente assim que o vendedor editar o título manualmente.
4. **Given** o vendedor está preenchendo Valores, **When** ele digita o valor antes do desconto e o valor de venda, **Then** o sistema exibe o percentual de desconto calculado em tempo real.
5. **Given** o vendedor escolhe a forma de pagamento "Faturado", **When** o formulário é exibido, **Then** aparece o campo de vencimento; escolhendo "Dividido no PIX", aparece o campo de parcelas (2 a 12).
6. **Given** o vendedor anexa dois comprovantes de pagamento com seus respectivos valores, **When** ele salva o evento, **Then** os dois comprovantes ficam vinculados ao evento criado, cada um com seu valor.
7. **Given** o vendedor anexa o arquivo do contrato e marca "Contrato já assinado", **When** ele salva o evento, **Then** o contrato aparece vinculado ao evento com o status assinado.
8. **Given** o vendedor adiciona uma observação do tipo Foto, **When** ele salva o evento, **Then** a foto aparece na lista de observações do evento criado.
9. **Given** o tipo de evento é "SHOW", **When** o vendedor vê o bloco Dados do Evento, **Then** o aviso "Eventos SHOW sempre geram ensaio automaticamente" é exibido e o ensaio é sempre criado, independente do checkbox.
10. **Given** o vendedor marca "Este evento terá reembolso de despesas da cliente", **When** ele preenche descrição e valor (e opcionalmente anexa a nota fiscal do gasto), **Then** o reembolso fica registrado no evento criado.

---

### User Story 2 - Sistema impede o salvamento de um evento incompleto e guia o vendedor ao erro (Priority: P1)

Ao tentar salvar um evento com campos obrigatórios vazios ou inválidos, o vendedor recebe destaque visual imediato em cada campo problemático e é levado automaticamente até o primeiro erro, sem precisar caçar manualmente o que falta em um formulário longo.

**Why this priority**: Sem isso, formulários longos como este geram tentativas de salvar incompletas, retrabalho e frustração — é a segunda característica mais citada explicitamente no pedido, junto com a paridade de campos.

**Independent Test**: Submeter o formulário totalmente vazio e confirmar que aparece o banner de erro e que a tela rola sozinha até o primeiro campo inválido, com foco nele.

**Acceptance Scenarios**:

1. **Given** um campo obrigatório (ex.: Data) foi deixado em branco, **When** o vendedor sai do campo (`onBlur`) sem preenchê-lo, **Then** o campo exibe borda vermelha espessa e uma mensagem de erro específica logo abaixo, imediatamente — sem esperar o envio do formulário.
2. **Given** o vendedor tenta submeter o formulário com um ou mais campos obrigatórios inválidos, **When** o envio é bloqueado, **Then** aparece um banner de erro no topo e no rodapé ("Existem campos obrigatórios não preenchidos. Verifique os destaques em vermelho.") e a tela rola suavemente até o primeiro campo com erro, colocando o foco nele.
3. **Given** o vendedor corrige o campo em foco, **When** ele preenche corretamente, **Then** o destaque vermelho daquele campo desaparece imediatamente (sem precisar submeter de novo para ver o campo "limpo").
4. **Given** o horário de fim é igual ao horário de início, **When** o vendedor sai do campo, **Then** aparece erro específico pedindo um horário de fim diferente.
5. **Given** o vendedor não é cortesia/permuta e deixa os valores de venda zerados, **When** ele tenta submeter, **Then** os dois campos de valor são destacados como obrigatórios.
6. **Given** o método de pagamento é "Dividido no PIX" e o número de parcelas está fora de 2–12, **When** o vendedor tenta submeter, **Then** o campo de parcelas é destacado com a mensagem correspondente.

---

### User Story 3 - Vendedor edita um evento já criado pela mesma tela unificada (Priority: P2)

Um vendedor (ou SUPERADMIN) abre um evento existente e edita qualquer um dos campos cobertos pelos 7 blocos — dados do evento, elenco, valores, pagamento, contrato, observações — em uma única tela, sem precisar navegar entre múltiplas ações espalhadas da tela de detalhe.

**Why this priority**: Hoje a edição de um evento já criado é feita através de várias ações pequenas e desconexas na tela de detalhe (uma para logística, uma para cada comprovante, etc.) — unificar isso na mesma tela do cadastro é a segunda maior mudança estrutural pedida, mas depende da US1 já estar pronta (mesmos blocos, mesma UI).

**Independent Test**: Abrir `/events/:id/edit` de um evento existente, confirmar que todos os campos vêm pré-preenchidos com os valores atuais, alterar um campo de cada bloco e salvar; reabrir o evento e confirmar que as mudanças persistiram.

**Acceptance Scenarios**:

1. **Given** um evento existente com cliente, elenco, valores, pagamento, contrato e observações já cadastrados, **When** o vendedor com permissão de edição abre `/events/:id/edit`, **Then** todos os campos aparecem pré-preenchidos com os dados atuais do evento.
2. **Given** o vendedor altera o título, a data ou os valores de venda, **When** ele salva, **Then** o evento é atualizado e a tela de detalhe reflete os novos valores.
3. **Given** o vendedor adiciona um novo comprovante de pagamento ou um novo contrato durante a edição, **When** ele salva, **Then** o novo anexo aparece na lista de anexos do evento, ao lado dos que já existiam.
4. **Given** um usuário sem permissão de edição de evento (ex.: papel ENSAIO) abre a URL de edição diretamente, **Then** o acesso é bloqueado, com paridade ao mesmo controle já aplicado nas ações de edição da tela de detalhe.
5. **Given** o evento tem um grupo comercial (satélites) ou já está com o Google Agenda sincronizado, **When** o vendedor edita e salva, **Then** o comportamento de sincronização/agrupamento não é alterado por esta feature (fora de escopo — ver Assumptions).

---

### User Story 4 - Vendedor cadastra um cliente novo sem sair do formulário (Priority: P2)

Ao não encontrar o cliente na busca, o vendedor cadastra um cliente novo com nome, telefone e empresa opcional, direto no bloco de Cliente, sem abrir outra aba ou perder o restante do formulário já preenchido.

**Why this priority**: É um gargalo citado explicitamente (hoje só existe na tela antiga) e uma ação frequente no dia a dia comercial — mas é uma peça isolada do formulário maior, testável e entregável de forma independente.

**Independent Test**: Em qualquer ponto do formulário (novo ou edição), clicar "+ Cadastrar novo cliente", preencher nome/telefone, salvar, e ver o cliente imediatamente selecionado na lista de associados.

**Acceptance Scenarios**:

1. **Given** o vendedor clica "+ Cadastrar novo cliente", **When** o formulário inline expande, **Then** aparecem os campos Nome completo (obrigatório), Telefone com DDD (obrigatório) e Empresa (opcional), com o botão "Salvar e adicionar".
2. **Given** o vendedor preenche nome e telefone válidos, **When** ele clica "Salvar e adicionar", **Then** o cliente é criado (ou reaproveitado, se já existir um cliente com aquele telefone) e adicionado à lista de associados do evento, com o mini-formulário fechando automaticamente.
3. **Given** o vendedor tenta salvar sem nome ou sem telefone, **When** ele clica "Salvar e adicionar", **Then** os campos inválidos são destacados sem fechar o mini-formulário.

---

### User Story 5 - Vendedor gera o título automaticamente e vê o desconto calculado (Priority: P3)

Conveniências que aceleram o preenchimento sem serem bloqueantes: o vendedor não precisa digitar o título manualmente nem calcular de cabeça o percentual de desconto aplicado.

**Why this priority**: São automações de conveniência (não alteram a persistência nem bloqueiam o fluxo) — agregam valor mas o formulário funciona plenamente sem elas, por isso ficam por último.

**Independent Test**: Preencher dois personagens e o tipo do evento, clicar "Gerar título automaticamente" e conferir o texto gerado; digitar valor antes do desconto e valor de venda diferentes e conferir o percentual exibido.

**Acceptance Scenarios**:

1. **Given** dois personagens "Mickey" e "Minnie" e tipo "SHOW", **When** o vendedor clica "Gerar título automaticamente", **Then** o título vira "(SHOW) MICKEY + MINNIE".
2. **Given** valor antes do desconto R$ 1.000,00 e valor de venda R$ 800,00, **When** os dois campos estão preenchidos, **Then** o sistema mostra "20% de desconto" (ou equivalente) atualizado a cada tecla.

### Edge Cases

- Evento do tipo SHOW: o checkbox de ensaio fica sempre marcado e não pode ser desmarcado (ensaio é automático); o texto explicativo deixa isso claro.
- Horário de fim menor que o de início (evento vira a noite): não é erro — apenas um aviso informativo, distinto do erro real de "fim igual ao início".
- Cortesia/permuta marcada: os campos de valor deixam de ser obrigatórios e ficam visualmente esmaecidos/desabilitados; o evento é salvo com venda R$ 0.
- Anexar um comprovante de pagamento sem informar o valor: permitido (paridade com o legado — o valor pode ficar em branco e ser preenchido depois).
- Falha ao enviar um anexo (comprovante/contrato/foto de observação) depois que o evento já foi criado com sucesso: o evento não pode "desaparecer" nem ficar em estado ambíguo — o vendedor precisa de um caminho claro para tentar reenviar só o anexo que falhou, sem duplicar o evento.
- Arquivo maior que o limite ou de tipo não aceito: rejeitado com mensagem clara antes do envio, sem travar o restante do formulário.
- Vendedor sem papel COMERCIAL/SUPERADMIN tenta acessar `/events/new` ou `/events/:id/edit`: acesso bloqueado, mesma regra já aplicada na API hoje.
- Edição de um evento que é um "ensaio" (satélite gerado automaticamente) ou que é o líder de um grupo comercial: fora de escopo desta feature — ver Assumptions.
- Dois vendedores editando o mesmo evento ao mesmo tempo: fora de escopo (sem lock otimista) — última gravação vence, mesmo comportamento de hoje.

## Requirements *(mandatory)*

### Functional Requirements

**Bloco 1 — Cliente e pré-contrato**

- **FR-001**: O sistema MUST permitir buscar e selecionar um ou mais clientes existentes (por nome ou telefone), cada um com um seletor de tipo de relação (Contratante, Assessora, Mãe/Pai, Familiar, Outros).
- **FR-002**: O sistema MUST permitir cadastrar um cliente novo inline (nome completo, telefone com DDD, empresa opcional) sem sair do formulário, reaproveitando um cliente já existente se o telefone informado já estiver cadastrado.
- **FR-003**: O sistema MUST permitir buscar e vincular uma resposta de formulário de pré-contrato (por nome, telefone ou data) ao evento.

**Bloco 2 — Dados do evento**

- **FR-004**: O sistema MUST exigir data, horário de início e horário de fim, com horário de fim diferente do horário de início.
- **FR-005**: O sistema MUST oferecer o campo Tipo de evento com as opções SHOW, CORP, R&I e VM.
- **FR-006**: O sistema MUST oferecer local do evento (texto livre) e descrição (texto livre, multi-linha), com o texto de ajuda informando que a descrição aparece no Google Agenda e na página do evento.
- **FR-007**: O sistema MUST, para eventos do tipo SHOW, manter o ensaio sempre habilitado (marcado e não editável), com texto explicativo; para os demais tipos, o vendedor MUST poder optar por adicionar ensaio manualmente.
- **FR-008**: O sistema MUST permitir marcar que o evento terá reembolso de despesas da cliente, exibindo então descrição, valor e (opcional) anexo da nota fiscal do gasto original.

**Bloco 3 — Elenco e equipe**

- **FR-009**: O sistema MUST permitir adicionar/remover múltiplas linhas de personagem, cada uma com nome, ficha de figurino (auto-detectada pelo nome ou escolhida manualmente), talento pré-escalado opcional, e os checkboxes Maquiagem e Cantor(a).
- **FR-010**: O sistema MUST permitir pré-escalar um coordenador específico (opcional), com texto explicando que a vaga fica aberta ao casting se deixada em branco.
- **FR-011**: O sistema MUST oferecer um botão que gera o título automaticamente a partir do tipo de evento e dos nomes dos personagens (padrão `(TIPO) PERSONAGEM 1 + PERSONAGEM 2`), sem impedir a edição manual do título a qualquer momento.

**Bloco 4 — Valores e comissões**

- **FR-012**: O sistema MUST oferecer um alternador de "Cortesia/permuta (sem venda)" que, quando ativo, dispensa a obrigatoriedade dos valores e sinaliza visualmente que a venda será registrada como R$ 0.
- **FR-013**: O sistema MUST exigir valor antes do desconto e valor de venda quando não for cortesia/permuta, exibindo o percentual de desconto calculado em tempo real a partir dos dois valores.
- **FR-014**: O sistema MUST oferecer transporte (R$) e acréscimo (R$) como campos opcionais, separados do valor de venda.
- **FR-015**: O sistema MUST oferecer o alternador "Precisa de nota fiscal".
- **FR-016**: O sistema MUST exigir vendedor responsável e data da venda.

**Bloco 5 — Forma de pagamento e comprovantes**

- **FR-017**: O sistema MUST oferecer a forma de pagamento como seleção única entre À vista (PIX), Dividido no PIX, Faturado e Cartão de Crédito, exibindo o campo de parcelas (2 a 12, obrigatório) quando "Dividido no PIX" for escolhido e a data de vencimento quando "Faturado" for escolhido.
- **FR-018**: O sistema MUST permitir anexar múltiplos comprovantes de pagamento (PDF, JPG ou PNG, até 20 MB cada), cada um com um valor (R$) opcional e um botão de remover antes de salvar.

**Bloco 6 — Contrato**

- **FR-019**: O sistema MUST permitir anexar opcionalmente o arquivo do contrato (PDF, PNG ou JPG, até 20 MB) e marcar se o contrato já está assinado.

**Bloco 7 — Observações e ações**

- **FR-020**: O sistema MUST permitir adicionar observações dos tipos Texto, Foto e Link, cada uma com um rótulo opcional, e remover uma observação antes de salvar (na edição, também depois de salva).
- **FR-021**: O sistema MUST oferecer um botão primário de envio ("Adicionar à Agenda" na criação) e um botão de cancelar, disponível tanto no topo quanto no rodapé do formulário.

**Validação e feedback**

- **FR-022**: O sistema MUST validar cada campo obrigatório ao perder o foco (`onBlur`) e ao digitar, destacando campos inválidos com borda vermelha espessa e uma mensagem de erro específica abaixo do campo, sem esperar a tentativa de envio.
- **FR-023**: O sistema MUST, ao bloquear um envio por haver campos inválidos, exibir um banner de erro no topo e no rodapé do formulário e rolar a tela suavemente até o primeiro campo inválido, posicionando o foco nele.
- **FR-024**: O sistema MUST remover o destaque de erro de um campo assim que ele passar a atender a validação, sem exigir nova tentativa de envio.

**Paridade de edição (novo, sem equivalente direto no legado)**

- **FR-025**: O sistema MUST oferecer uma tela de edição (`/events/:id/edit`) com os mesmos 7 blocos da criação, pré-preenchida com os dados atuais do evento, restrita a quem já tem permissão de editar o evento hoje.
- **FR-026**: O sistema MUST permitir, a partir da tela de detalhe do evento, navegar diretamente para a tela de edição quando o usuário tiver permissão.
- **FR-027**: O sistema MUST refletir na tela de detalhe do evento qualquer alteração salva pela tela de edição.

**Escopo e integridade**

- **FR-028**: O sistema MUST manter toda alteração restrita a `frontend/apps/internal`; nenhuma view, rota ou template Jinja legado (`app/calendar/routes.py`, `app/templates/event_create.html`, `app/templates/event_detail.html`) MUST ser alterado.
- **FR-029**: O sistema MUST impedir que uma falha no envio de um anexo (comprovante, contrato ou foto de observação) após a criação do evento principal deixe o vendedor sem saber o que foi salvo — o sistema MUST indicar claramente quais anexos foram salvos e quais falharam, permitindo reenviar apenas os que falharam.

### Key Entities

- **Evento (CalendarEvent)**: já existente — ganha um novo caminho de atualização (edição) cobrindo os campos centrais (título, tipo, datas/horários, local, descrição, ensaio, valores, pagamento, vendedor).
- **Cargo de evento (EventRole)**: personagem/equipe do elenco — já existente, criação/edição via este formulário.
- **Cliente vinculado ao evento (EventClient)**: relação entre evento e cliente com um tipo (Contratante, Assessora etc.) — já existente; ganha edição em bloco (não só na criação).
- **Comprovante de pagamento (EventPayment)**: arquivo + valor — já existente.
- **Contrato (EventContract)**: arquivo + assinado — já existente.
- **Reembolso (EventReimbursement)**: descrição + valor + nota fiscal do gasto — já existente.
- **Observação (EventObservation)**: texto, link ou foto com rótulo opcional — já existente; ganha suporte a foto na criação.
- **Cliente (Client)**: já existente — ganha um caminho de criação rápida a partir do formulário de evento.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Um vendedor consegue criar um evento completo (todos os 7 blocos preenchidos, incluindo comprovante, contrato e observação com foto) sem sair da tela nem precisar abrir a versão antiga.
- **SC-002**: 100% dos campos hoje disponíveis na criação/edição de evento na versão em produção têm um equivalente funcional nesta tela (paridade de campos).
- **SC-003**: Ao tentar salvar um formulário com erros, o vendedor vê o primeiro campo problemático em foco, com a tela já rolada até ele, em menos de 1 segundo após o clique de envio.
- **SC-004**: Um vendedor consegue editar qualquer campo coberto pelos 7 blocos de um evento existente e ver a mudança refletida na tela de detalhe imediatamente após salvar.
- **SC-005**: Cadastrar um cliente novo direto do formulário de evento leva no máximo 3 campos e 1 clique adicional em relação a selecionar um cliente já existente.

## Assumptions

- **Criação em duas fases para anexos**: como o endpoint de criação de evento (`POST /api/events`) é hoje estritamente JSON (sem arquivos) e não há precedente de upload em lote nesse endpoint, a criação salva primeiro os dados centrais do evento e, na sequência, envia cada anexo (comprovantes, contrato, fotos de observação) usando os endpoints de anexo já existentes (mesmos usados pela tela de detalhe). Se o evento foi criado mas algum anexo falhar, o formulário informa exatamente quais anexos ainda precisam ser reenviados (FR-029), em vez de perder o evento criado ou duplicá-lo.
- **Novo endpoint de edição**: não existe hoje nenhum endpoint que atualize em bloco os campos centrais de um evento (título, datas, valores, elenco como conjunto, clientes como conjunto etc.) — só ações pontuais (logística, papel por papel, comprovante por comprovante). Esta feature introduz um novo endpoint de atualização em bloco, seguindo o mesmo padrão arquitetural já usado no repositório (rota em `app/api/`, núcleo de negócio em `app/calendar/*_ops.py`), sem tocar nas views Jinja legadas.
- **Anexos na edição reaproveitam os endpoints já existentes**: como o evento em edição já tem um id, adicionar/remover comprovantes, contrato, reembolsos e observações na tela de edição usa os mesmos endpoints e hooks já usados pela tela de detalhe hoje — não é criado nenhum endpoint novo de anexo.
- **Duração customizada de orçamento** (ex.: eventos de 2,5 horas, fora do padrão 1–4h) e **linhas de elenco do tipo "equipe" sem figurino** (`role_type="extra"`) preenchidas manualmente continuam fora do escopo desta feature — hoje só aparecem via pré-preenchimento de orçamento, um fluxo que não muda aqui.
- **Calculadora de desconto** é só uma conveniência visual (mesmo comportamento do legado): não é persistida separadamente — o vendedor ajusta o valor de venda final livremente, e o percentual é só um indicador.
- **Fora de escopo**: agrupamento de eventos satélites, edição de eventos do tipo "ensaio" automático, e qualquer trava de edição concorrente (dois vendedores editando o mesmo evento ao mesmo tempo) — nenhum desse comportamento muda nesta feature. A sincronização com o Google Agenda **é** afetada de forma pontual: ao editar título/data/horário/local/descrição, o evento correspondente no Google Agenda é atualizado também (best-effort — uma falha do Google não impede salvar a edição no Manto, ver research.md §10).
- **RBAC de edição**: reaproveita as mesmas regras já aplicadas hoje pela API (`COMERCIAL`/`SUPERADMIN` para criar; o mesmo conjunto de papéis que já pode editar campos do evento na tela de detalhe para editar pela tela nova), sem introduzir papéis novos.
- **Gestão de anexos já salvos, na edição**: a tela de edição permite adicionar novos comprovantes/contrato/reembolso/observações (mesma UI da criação). Excluir, editar valor ou marcar como coletado/assinado um anexo **já salvo** continua sendo feito na tela de detalhe do evento (que já cobre isso por completo, feature 153) — a tela de edição não duplica essa gestão, só mostra quantos já existem com um link para lá.
