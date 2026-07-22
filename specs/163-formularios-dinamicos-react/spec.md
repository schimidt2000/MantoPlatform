# Feature Specification: Formulários Dinâmicos Públicos em React

**Feature Branch**: `163-formularios-dinamicos-react`

**Created**: 2026-07-22

**Status**: Draft

**Input**: User description: "Migrar os formulários públicos dinâmicos /f/pre-contrato e
/f/corporativo (hoje Jinja em app/formularios/routes.py, dirigidos por FormFieldDefinition —
sem campos fixos no código) para o app frontend/apps/public em React, como 3ª fatia da US5
(Superfícies Públicas) da migração 144 — depois do catálogo (161) e do cadastro de talentos
(162). Precisa de um componente de formulário genérico no React que renderiza a partir de um
schema retornado pela API (não um formulário hardcoded por caso), já que os campos são editáveis
pelo painel administrativo (SUPERADMIN) e podem mudar sem alteração de código. Escopo: as duas
telas públicas de envio, com honeypot anti-bot, rate limiting, aviso de duplicidade não se aplica
aqui (é o cadastro que tem isso), preenchimento automático de endereço por CEP (ViaCEP,
client-side), envio salva a resposta e abre o WhatsApp com a mensagem formatada. A área interna
autenticada (listagem de respostas, associar/desvincular cliente e evento, editor de estrutura do
formulário) NÃO faz parte desta fatia — continua só em Jinja, é superfície interna (US6), não
pública."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Visitante preenche e envia um formulário de pré-contrato (Priority: P1)

Uma pessoa interessada em contratar (pessoa física ou representante de empresa) acessa o link
público do formulário, preenche os campos vigentes (definidos pela equipe no painel
administrativo) e envia — o WhatsApp abre com a mensagem já formatada para confirmar o envio.

**Why this priority**: é o fluxo inteiro — sem ele os dois formulários não têm valor nenhum; é o
motivo de eles existirem (substituir o WhatsForm por um canal que salva a resposta antes de abrir
o WhatsApp).

**Independent Test**: abrir `/f/pre-contrato` (ou `/f/corporativo`), preencher todos os campos
obrigatórios vigentes naquele momento e enviar — a resposta é salva e a pessoa vê a tela de
confirmação com um botão para abrir o WhatsApp com a mensagem pronta.

**Acceptance Scenarios**:

1. **Given** o formulário de pré-contrato (pessoa física), **When** a pessoa preenche todos os
   campos obrigatórios vigentes e envia, **Then** a resposta é salva e a tela de confirmação abre
   o WhatsApp automaticamente (com plano B de um botão, caso a abertura automática falhe).
2. **Given** o formulário corporativo, **When** a pessoa preenche todos os campos obrigatórios
   vigentes e envia, **Then** o mesmo comportamento de sucesso ocorre, com a mensagem
   identificando que é um contrato corporativo.
3. **Given** qualquer um dos dois formulários, **When** a estrutura de campos muda no painel
   administrativo (campo novo, removido, obrigatoriedade alterada), **Then** a tela pública
   reflete a mudança automaticamente, sem precisar de novo código/deploy.
4. **Given** um campo obrigatório vazio ou um CPF/CNPJ/CEP/e-mail/data em formato inválido,
   **When** a pessoa tenta enviar, **Then** o envio é recusado e cada campo com problema mostra
   sua própria mensagem de erro, sem perder o que já foi preenchido nos demais campos.

---

### User Story 2 - Endereço preenchido automaticamente a partir do CEP (Priority: P2)

Quando o formulário tem um campo de CEP, ao terminar de digitar os 8 dígitos os campos de
endereço (logradouro, bairro, cidade, estado) são preenchidos automaticamente, sem a pessoa
precisar digitá-los à mão.

**Why this priority**: é uma conveniência que reduz fricção no preenchimento, mas o formulário
continua 100% funcional sem ela (a pessoa preenche o endereço manualmente) — por isso vem depois
do fluxo de envio em si.

**Independent Test**: digitar um CEP válido existente e ver os campos de endereço se
preencherem sozinhos; digitar um CEP inexistente e ver que nada quebra (a pessoa preenche à mão).

**Acceptance Scenarios**:

1. **Given** um formulário com campo de CEP e campos de endereço, **When** a pessoa digita um CEP
   válido e sai do campo, **Then** logradouro/bairro/cidade/estado são preenchidos
   automaticamente, sem sobrescrever o que a pessoa já tiver digitado manualmente.
2. **Given** o mesmo cenário, **When** o CEP não existe ou o serviço de consulta falha, **Then**
   nada quebra — a pessoa preenche os campos de endereço manualmente.

---

### Edge Cases

- O que acontece com o campo condicional "Descreva outros" (só aparece quando a forma de
  pagamento escolhida é "Outros")? Continua escondido até essa condição ser satisfeita, e vira
  obrigatório só nesse caso — mesma regra de hoje.
- O que acontece com um envio automatizado que preenche o campo-armadilha oculto (honeypot)? É
  silenciosamente ignorado — nenhuma resposta é salva, mas a pessoa (ou robô) vê a mesma tela de
  confirmação, sem revelar o bloqueio.
- O que acontece com excesso de tentativas de envio em pouco tempo? É recusado temporariamente
  com uma mensagem amigável (mesmo limite de hoje).
- O que acontece se a resposta puder ser associada automaticamente a um evento já existente na
  agenda? Continua funcionando nos bastidores, sem nenhuma mudança visível para quem preenche o
  formulário (é um processo interno, não afeta a experiência pública).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O sistema DEVE exibir os dois formulários públicos (pré-contrato e corporativo)
  renderizados dinamicamente a partir da definição de campos vigente — nenhuma lista de campos
  fixa no código da tela.
- **FR-002**: O sistema DEVE suportar todos os tipos de campo hoje existentes (texto curto, texto
  longo, seleção com opções, telefone com código de país, data, hora, e-mail, CPF, CNPJ, CEP,
  sim/não), cada um com sua própria validação de formato quando aplicável.
- **FR-003**: O sistema DEVE agrupar os campos nas mesmas seções visuais definidas pela equipe,
  na mesma ordem.
- **FR-004**: O sistema DEVE recusar o envio quando um campo obrigatório estiver vazio ou um
  campo com formato específico (CPF, CNPJ, CEP, e-mail, data) estiver inválido, mostrando a
  mensagem de erro específica junto ao campo problemático, sem apagar o que já foi preenchido.
- **FR-005**: O sistema DEVE aplicar a regra especial do campo "Descreva outros": obrigatório e
  visível apenas quando a forma de pagamento selecionada for "Outros".
- **FR-006**: O sistema DEVE preencher automaticamente os campos de endereço a partir de um CEP
  válido, sem sobrescrever valores já preenchidos manualmente, e sem impedir o envio caso a
  consulta de CEP falhe.
- **FR-007**: O sistema DEVE ignorar silenciosamente envios que preencham o campo-armadilha
  anti-robô, sem salvar resposta nenhuma, mostrando a mesma confirmação de sucesso ao remetente.
- **FR-008**: O sistema DEVE limitar a taxa de tentativas de envio por visitante numa janela de
  tempo, recusando temporariamente o excesso.
- **FR-009**: O sistema DEVE, a cada envio válido, salvar a resposta antes de exibir o link/botão
  de abertura do WhatsApp com a mensagem formatada (título do formulário + seções + campos
  preenchidos).
- **FR-010**: O sistema DEVE tentar associar automaticamente a resposta a um evento já existente
  na agenda quando os critérios de confiança já usados hoje forem satisfeitos — processo interno,
  sem qualquer alteração na experiência de quem preenche o formulário.
- **FR-011**: O sistema NÃO DEVE alterar a área interna autenticada (listagem de respostas,
  associação a cliente/evento, editor de estrutura) — permanece fora do escopo desta fatia.

### Key Entities

- **FormResponse (Resposta de formulário)**: já existe no sistema — esta funcionalidade apenas
  cria novas respostas através de uma nova superfície (React), sem alterar sua estrutura.
- **FormFieldDefinition (Definição de campo)**: já existe — consultada (somente leitura) para
  montar o formulário dinâmico; sua edição continua restrita à área interna (fora de escopo).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Uma pessoa consegue preencher e enviar qualquer um dos dois formulários em uma
  única sessão, em qualquer tela de 320–430px de largura, sem rolagem horizontal.
- **SC-002**: 100% dos envios com campo obrigatório vazio ou campo em formato inválido recebem
  uma mensagem de erro específica junto ao campo problemático, sem perda do preenchimento já
  feito.
- **SC-003**: Zero regressão funcional em relação à versão hoje em produção: uma mudança de
  estrutura de campo feita no painel administrativo aparece na tela pública sem precisar de
  código novo, e o mesmo conjunto de dados de entrada produz a mesma resposta salva e a mesma
  mensagem de WhatsApp.
- **SC-004**: O preenchimento automático por CEP funciona para CEPs válidos e não impede o envio
  quando a consulta falhar ou o CEP não existir.

## Assumptions

- Nenhuma regra de negócio nova é introduzida: toda validação, montagem de seções/mensagem e
  tentativa de vínculo automático de evento hoje presentes na versão Jinja são preservadas
  exatamente, apenas re-expostas via API JSON.
- O design visual segue os mesmos padrões visuais já estabelecidos para o app público
  (`frontend/apps/public`, iniciado na feature 161).
- As rotas Jinja `/f/pre-contrato` e `/f/corporativo` permanecem ativas em paralelo (mesmo
  critério das fatias anteriores da US5).
- A área interna (`/formularios/*` autenticada) não é tocada nesta fatia — migra em uma fatia
  futura da cauda administrativa (US6), fora do escopo de superfícies públicas.
