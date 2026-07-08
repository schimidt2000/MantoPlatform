# Feature Specification: Formulários de Pré-Contrato (substituto do WhatsForm)

**Feature Branch**: `118-formularios-pre-contrato`

**Created**: 2026-07-08

**Status**: Draft

**Input**: User description: "Seção de formulários com link copiável para enviar à cliente. Ela preenche e, ao enviar, dispara mensagem de WhatsApp para o 11970570577 com a resposta E salva no sistema como banco de respostas, conversando com o banco de clientes. Dois formulários: contratos (comum) e contratos corporativos, conforme a pasta 'formularios contexto'. Nova resposta gera alerta na home do comercial ('pré-contrato preenchido e não associado a cliente'). Super admin pode apagar uma resposta. 90% dos acessos serão por celular — otimizar para mobile, com feedback de erro sem perder o que foi digitado. Na tela de criar evento, trocar o 'cole aqui a resposta do whatsform' por um buscador que associa uma resposta preenchida."

## Contexto

Hoje a Manto usa o serviço WhatsForm para colher dados de pré-contrato das clientes: a
cliente preenche um formulário externo e a resposta chega como texto no WhatsApp da
empresa. O serviço é caro, não se integra ao Manto, e a resposta vira texto solto colado
manualmente na descrição do evento em `/events/new`. Esta feature internaliza o fluxo:
formulários próprios, hospedados no Manto, com resposta salva no banco (consultável,
associável a cliente e a evento) além do envio por WhatsApp que a equipe já conhece.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Cliente preenche o pré-contrato pelo celular (Priority: P1)

A equipe comercial copia o link do formulário (comum ou corporativo) na nova seção de
formulários e envia à cliente pelo WhatsApp. A cliente abre no celular, preenche os campos
(estrutura exata definida em `formularios contexto/formulario_comum.md` e
`formulario_corporativo.md`), e toca em "Enviar no WhatsApp". A resposta é salva no sistema
e, em seguida, abre o WhatsApp dela com a mensagem formatada pronta para enviar ao número
da Manto (11 97057-0577).

**Independent Test**: abrir o link do formulário sem estar logado, num viewport mobile,
preencher tudo e enviar; conferir que a resposta aparece no banco de respostas e que o
link de WhatsApp gerado contém todas as respostas endereçadas ao número da Manto.

**Acceptance Scenarios**:

1. **Given** cliente com o link do formulário comum, **When** preenche todos os campos
   obrigatórios e envia, **Then** a resposta é salva no sistema e o WhatsApp abre com a
   mensagem formatada para o número da Manto.
2. **Given** cliente que envia com um campo obrigatório vazio ou inválido (CPF/CNPJ,
   e-mail, telefone), **Then** vê mensagem de erro clara apontando o campo, **e nada do
   que já digitou se perde**.
3. **Given** formulário comum, **When** seleciona "Outros" na forma de pagamento, **Then**
   o campo "Descreva Outros" torna-se obrigatório; o mesmo vale para o corporativo.
4. **Given** acesso por celular (90% dos casos), **Then** o formulário é confortável de
   preencher em tela pequena: campos empilhados, fonte legível, botão de envio alcançável.
5. **Given** que a cliente não está logada no sistema, **Then** o formulário abre
   normalmente — é uma página pública, sem login.

### User Story 2 - Comercial vê alerta e associa resposta a cliente (Priority: P1)

Quando uma resposta nova é salva, a home do usuário comercial mostra um alerta de
"pré-contrato preenchido e não associado a cliente". O comercial abre o banco de
respostas, vê a resposta completa e a associa a um cliente existente (ou cria o cliente a
partir dos dados da resposta). Depois de associada, o alerta daquela resposta some.

**Independent Test**: salvar uma resposta de teste, logar como comercial, conferir o
alerta na home; associar a um cliente e conferir que o alerta desaparece.

**Acceptance Scenarios**:

1. **Given** resposta recém-salva sem cliente associado, **When** comercial abre a home,
   **Then** vê alerta indicando pré-contrato(s) preenchido(s) e não associado(s).
2. **Given** resposta cujo telefone bate com um cliente já cadastrado (telefone
   normalizado), **Then** o sistema sugere essa associação automaticamente.
3. **Given** resposta sem cliente correspondente, **When** comercial escolhe "criar
   cliente a partir da resposta", **Then** um cliente novo é criado com nome e telefone
   vindos da resposta e a associação é feita.
4. **Given** resposta associada a cliente, **Then** ela sai do alerta da home e passa a
   aparecer no histórico consultável do cliente.

### User Story 3 - Associar resposta ao criar evento (Priority: P2)

Na tela de criar evento (`/events/new`), no lugar da orientação "cole aqui a resposta do
whatsform" na descrição, existe um pequeno buscador de respostas de formulário. O
comercial busca (por nome, telefone ou data), seleciona a resposta, e ela fica vinculada
ao evento — os dados completos ficam acessíveis a partir do evento.

**Independent Test**: criar uma resposta de teste, abrir `/events/new`, buscar pelo nome
da contratante, selecionar, salvar o evento e conferir o vínculo.

**Acceptance Scenarios**:

1. **Given** respostas salvas no banco, **When** comercial digita no buscador da tela de
   criar evento, **Then** vê respostas correspondentes (busca ignora acentos, no mesmo
   padrão do buscador de clientes).
2. **Given** resposta selecionada, **When** o evento é salvo, **Then** o evento fica
   vinculado àquela resposta e ela é consultável a partir do evento.
3. **Given** que nenhuma resposta corresponde, **Then** o comercial pode seguir criando o
   evento normalmente sem vínculo (associação é opcional).

### User Story 4 - Super admin exclui uma resposta (Priority: P3)

Se uma resposta foi preenchida errado ou é teste/spam, um super admin pode excluí-la do
banco de respostas, com confirmação antes da ação.

**Acceptance Scenarios**:

1. **Given** usuário super admin no banco de respostas, **When** exclui uma resposta e
   confirma, **Then** ela some da listagem e dos alertas.
2. **Given** usuário comercial (não super admin), **Then** não vê a opção de excluir.

## Requirements *(mandatory)*

- **FR-001**: O sistema DEVE ter uma seção interna de formulários onde a equipe copia o
  link público de cada formulário (comum e corporativo) para enviar às clientes.
- **FR-002**: Os dois formulários DEVEM ser páginas públicas (sem login), com campos,
  seções, obrigatoriedades, máscaras e lógica condicional exatamente conforme
  `formularios contexto/formulario_comum.md` e `formulario_corporativo.md`.
- **FR-003**: Ao enviar, a resposta DEVE ser salva no sistema E o WhatsApp da cliente DEVE
  abrir com a mensagem formatada (todas as respostas) endereçada ao número 11 97057-0577.
  Se o salvamento falhar, a cliente vê erro claro e os dados digitados são preservados.
- **FR-004**: Erros de validação DEVEM apontar o campo com mensagem clara e NUNCA
  descartar o que a cliente já digitou.
- **FR-005**: Os formulários DEVEM ser otimizados para celular (mobile-first): coluna
  única, campos e botão confortáveis ao toque, teclado adequado por tipo de campo
  (numérico para CPF/CEP/telefone, e-mail para e-mail).
- **FR-006**: O sistema DEVE manter um banco de respostas interno, consultável pela equipe
  comercial e super admin, mostrando a resposta completa e sua situação (associada ou não
  a cliente, vinculada ou não a evento).
- **FR-007**: Resposta salva sem cliente associado DEVE gerar alerta na home dos usuários
  comerciais ("pré-contrato preenchido e não associado a cliente"), que some quando a
  associação é feita ou a resposta é excluída.
- **FR-008**: O sistema DEVE permitir associar uma resposta a um cliente existente
  (sugerindo automaticamente quando o telefone normalizado coincidir) ou criar um cliente
  novo a partir dos dados da resposta.
- **FR-009**: Apenas super admin PODE excluir uma resposta, com confirmação antes.
- **FR-010**: A tela de criar evento DEVE oferecer um buscador de respostas (por nome,
  telefone ou data do evento, ignorando acentos) para vincular uma resposta ao evento;
  o vínculo é opcional e a resposta vinculada fica consultável a partir do evento.
- **FR-011**: A orientação atual de "colar a resposta do whatsform" na descrição do evento
  DEVE ser substituída pelo buscador (a descrição continua existindo para texto livre).

### Key Entities

- **Resposta de Formulário**: registro de um preenchimento — tipo do formulário (comum ou
  corporativo), todas as respostas, data/hora, cliente associado (opcional), evento
  vinculado (opcional).
- **Cliente**: entidade existente do CRM; ganha a relação com respostas de formulário
  (telefone normalizado é a chave de sugestão).
- **Evento**: entidade existente; ganha vínculo opcional com uma resposta de formulário.

## Success Criteria *(mandatory)*

- **SC-001**: Cliente completa e envia o formulário pelo celular sem ajuda da equipe; a
  mensagem chega no WhatsApp da Manto no mesmo formato de conteúdo que o WhatsForm
  entregava (nenhuma informação a menos).
- **SC-002**: 100% das respostas enviadas ficam salvas e consultáveis no sistema — mesmo
  que a cliente desista de mandar a mensagem no WhatsApp depois do envio.
- **SC-003**: Nenhum dado digitado se perde em caso de erro de validação ou falha de
  envio.
- **SC-004**: Comercial encontra e associa uma resposta a cliente em menos de 1 minuto a
  partir do alerta da home.
- **SC-005**: Ao criar evento com resposta vinculada, o comercial não precisa mais colar
  texto do WhatsForm manualmente.
- **SC-006**: Custo do WhatsForm eliminado (serviço pode ser cancelado após adoção).

## Assumptions

- O envio por WhatsApp é feito abrindo o link oficial `api.whatsapp.com/send` no aparelho
  da cliente com a mensagem pré-preenchida (mesmo comportamento do WhatsForm) — a cliente
  dá o toque final de enviar. Não há integração com API paga de WhatsApp.
- A resposta é salva ANTES de abrir o WhatsApp: se a cliente não concluir o envio da
  mensagem, o registro no sistema já existe (o alerta na home cobre o acompanhamento).
- O número de destino (11 97057-0577) fica em configuração do sistema, não fixo no código
  de página, para permitir troca futura sem mexer em código.
- Links dos formulários são estáveis e públicos (sem token por cliente) — mesmo modelo do
  WhatsForm atual; quem tem o link pode preencher.
- O banco de respostas é acessível aos papéis COMERCIAL e SUPERADMIN (mesmo grupo que já
  cuida de clientes e vendas).
- Exclusão de resposta é definitiva (hard delete) com confirmação — volume esperado é
  baixo e o caso de uso é limpeza de teste/erro.
- Auto-preenchimento de endereço por CEP (ViaCEP) é desejável no formulário comum, mas se
  o serviço externo falhar a cliente preenche manualmente — nunca bloqueia o envio.
