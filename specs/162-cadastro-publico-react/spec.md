# Feature Specification: Cadastro Público de Talentos em React

**Feature Branch**: `162-cadastro-publico-react`

**Created**: 2026-07-22

**Status**: Draft

**Input**: User description: "Migrar a página pública de cadastro de talentos (/cadastro, hoje Jinja em app/cadastro/routes.py + app/templates/cadastro/form.html e success.html) para o app frontend/apps/public em React, como 2ª fatia da US5 (Superfícies Públicas) da migração 144 — a 1ª fatia foi o catálogo público (feature 161, já mergeada). Escopo: formulário público sem login de cadastro de talento (dados pessoais, documentos, medidas, PIX, upload de fotos/documentos — rosto, corpo inteiro, documento obrigatórios, CNH opcional), validação de CPF duplicado em tempo real (/cadastro/check-cpf), honeypot anti-bot, rate limiting, e página de confirmação de envio. Resultado: Talent criado com status=pending, source=public_form. A rota Jinja /cadastro/* deve continuar existindo em paralelo até este slice estar validado. Endpoints novos em app/api (JSON), reaproveitando a lógica já existente em app/cadastro/routes.py sem duplicar regra de negócio nova."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Candidato preenche e envia o cadastro (Priority: P1)

Um visitante anônimo (candidato a talento) acessa a página pública de cadastro, preenche seus
dados pessoais, medidas, dados de pagamento (PIX) e envia fotos/documentos exigidos, então
confirma o envio.

**Why this priority**: é o fluxo inteiro — sem ele não há valor algum entregue; é o único motivo
da página existir (alimentar o banco de talentos com candidatos pendentes de aprovação).

**Independent Test**: um visitante anônimo, sem conta, preenche todos os campos obrigatórios,
anexa as 3 fotos/documentos obrigatórios (rosto, corpo inteiro, documento) e envia — o sistema
cria um talento pendente e mostra a confirmação, sem exigir login em nenhum momento.

**Acceptance Scenarios**:

1. **Given** o formulário público de cadastro, **When** o candidato preenche todos os campos
   obrigatórios e anexa as fotos/documentos exigidos, **Then** um talento é criado com status
   pendente e o candidato vê a página de confirmação de envio.
2. **Given** o formulário público de cadastro, **When** o candidato deixa um campo obrigatório
   em branco e tenta enviar, **Then** o sistema mostra uma mensagem de erro específica sobre o
   campo faltante, sem perder o preenchimento já feito nos demais campos.
3. **Given** o formulário público de cadastro, **When** o candidato anexa um arquivo de tipo ou
   tamanho não permitido, **Then** o sistema recusa o envio com uma mensagem clara sobre qual
   arquivo e por quê.

---

### User Story 2 - Aviso de CPF já cadastrado antes de enviar tudo (Priority: P2)

Enquanto digita o CPF, o candidato brasileiro recebe um aviso em tempo real se aquele CPF já
existe no banco de talentos, antes de precisar preencher o restante do formulário e anexar
arquivos.

**Why this priority**: evita que o candidato perca tempo preenchendo um formulário longo e
enviando arquivos pesados só para descobrir no final que já está cadastrado — mas o produto
continua funcional (com um erro no envio final) mesmo sem essa checagem antecipada.

**Independent Test**: um visitante digita um CPF que já existe no banco e vê o aviso aparecer
sem precisar submeter o formulário; digitando um CPF novo, nenhum aviso aparece.

**Acceptance Scenarios**:

1. **Given** o campo de CPF preenchido com um CPF já cadastrado, **When** o candidato termina de
   digitar os 11 dígitos, **Then** um aviso indica que aquele CPF já está cadastrado.
2. **Given** o campo de CPF preenchido com um CPF novo (ou incompleto), **When** o candidato
   digita, **Then** nenhum aviso de duplicidade aparece.

---

### User Story 3 - Proteção contra automações e abuso (Priority: P3)

O sistema continua protegido contra envios automatizados/robôs (honeypot) e contra excesso de
tentativas em curto período (limite de taxa), sem que o candidato humano perceba qualquer
fricção extra.

**Why this priority**: é uma proteção operacional que já existe hoje — precisa sobreviver à
migração, mas não é o que o candidato humano experimenta diretamente; menor prioridade que os
fluxos que o candidato de fato vê.

**Independent Test**: um envio automatizado que preenche o campo-armadilha oculto é
silenciosamente redirecionado para a confirmação sem criar talento; um excesso de tentativas de
envio ou de checagem de CPF em curto período é bloqueado temporariamente.

**Acceptance Scenarios**:

1. **Given** uma submissão que preenche o campo oculto (honeypot), **When** o envio acontece,
   **Then** nenhum talento é criado e o remetente vê a mesma confirmação de sucesso (sem revelar
   que foi bloqueado).
2. **Given** muitas tentativas de envio em pouco tempo do mesmo visitante, **When** o limite é
   excedido, **Then** o sistema recusa temporariamente novas tentativas com uma mensagem amigável.

---

### Edge Cases

- O que acontece quando o candidato é estrangeiro (sem CPF brasileiro)? O CPF deixa de ser
  obrigatório, mas os demais campos obrigatórios continuam sendo exigidos.
- O que acontece se o candidato selecionar "Outro" no campo de gênero? Um campo de texto livre
  deve ser exibido e seu conteúdo usado como valor do gênero.
- O que acontece se o candidato enviar apenas uma foto/documento obrigatório e esquecer outro?
  O envio é recusado citando exatamente qual anexo está faltando.
- O que acontece se dois candidatos enviarem o mesmo CPF quase simultaneamente (corrida)? Apenas
  o primeiro é aceito; o segundo recebe o erro de CPF duplicado no envio final (a checagem em
  tempo real é apenas um aviso antecipado, não uma garantia).
- O que acontece com a rota antiga (Jinja) durante a transição? Continua no ar e funcional em
  paralelo, sem alteração de comportamento, até este slice estar validado.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O sistema DEVE exibir um formulário público de cadastro de talento, acessível sem
  autenticação, com todos os campos hoje presentes na versão existente (dados pessoais, contato,
  medidas corporativas, dados de PIX, idiomas, habilidades, informações de veículo/CNH quando
  aplicável, situação de passaporte/visto).
- **FR-002**: O sistema DEVE exigir upload de foto de rosto, foto de corpo inteiro e foto/arquivo
  de documento de identificação; o arquivo de CNH é opcional.
- **FR-003**: O sistema DEVE validar tipo e tamanho de cada arquivo enviado antes de aceitar o
  envio, recusando com mensagem específica quando inválido.
- **FR-004**: O sistema DEVE tratar CPF como obrigatório apenas quando o candidato não se
  identificar como estrangeiro; para estrangeiros, o CPF fica de fora do registro.
- **FR-005**: O sistema DEVE oferecer uma checagem de CPF em tempo real (antes do envio final)
  que informa se aquele CPF já está cadastrado.
- **FR-006**: O sistema DEVE recusar o envio final quando o CPF informado já existir no banco
  (mesma regra vale mesmo que a checagem em tempo real não tenha sido usada).
- **FR-007**: O sistema DEVE criar um registro de talento com status pendente (aguardando
  aprovação da equipe) e origem "formulário público" para cada envio válido.
- **FR-008**: O sistema DEVE exibir uma página de confirmação após o envio bem-sucedido.
- **FR-009**: O sistema DEVE ignorar silenciosamente envios que preencham o campo-armadilha
  anti-robô (honeypot), respondendo com a mesma confirmação de sucesso sem criar talento.
- **FR-010**: O sistema DEVE limitar a taxa de tentativas de envio e de checagem de CPF por
  visitante em uma janela de tempo, recusando temporariamente o excesso.
- **FR-011**: O sistema DEVE manter a rota pública existente (versão atual) funcionando sem
  alteração em paralelo à nova versão, até este slice ser validado.
- **FR-012**: O sistema DEVE preservar cada mensagem de validação específica por campo hoje
  existente (nome, gênero, telefone, e-mail, idioma, data de nascimento, CPF, RG, PIX, raça/cor,
  altura, manequim superior/inferior, tamanho de sapato, passaporte, habilidades).
- **FR-013**: O sistema NÃO DEVE expor detalhes técnicos de erro (stack traces) ao candidato em
  nenhum cenário de falha.

### Key Entities

- **Talent (Talento)**: candidato cadastrado publicamente; entra com status pendente, origem
  "formulário público", dados pessoais/medidas/PIX/documentos anexados. Já existe no sistema —
  esta funcionalidade apenas cria novos registros através de uma nova superfície.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Um candidato consegue preencher e enviar o cadastro completo (incluindo os 3
  anexos obrigatórios) em uma única sessão sem recarregar a página, em qualquer tela de
  320–430px de largura.
- **SC-002**: 100% dos envios com campo obrigatório faltante ou arquivo inválido recebem uma
  mensagem de erro específica sobre o problema, sem perda dos dados já preenchidos.
- **SC-003**: Zero regressão funcional em relação à versão hoje em produção: os mesmos dados,
  as mesmas validações e o mesmo resultado (talento pendente) são produzidos para os mesmos
  dados de entrada.
- **SC-004**: A checagem de CPF em tempo real responde antes do candidato terminar de preencher
  o restante do formulário, evitando que descubra a duplicidade só no envio final.

## Assumptions

- O design visual da nova tela segue os mesmos padrões visuais já estabelecidos para o app
  público (`frontend/apps/public`, iniciado na feature 161 — catálogo).
- Nenhuma regra de negócio nova é introduzida: toda validação, parsing e normalização hoje
  presentes na versão Jinja são preservados exatamente, apenas re-expostos via API JSON.
  Componente de upload de arquivo é o único elemento verdadeiramente novo do lado da interface
  (a versão Jinja usa upload de formulário tradicional).
  A checagem de CPF, o honeypot e o rate limiting já existem hoje e serão reaproveitados sem
  mudança de comportamento.
- A rota Jinja `/cadastro/*` permanece ativa em paralelo (decisão sobre desligá-la ou não fica
  para o plano técnico, seguindo o mesmo critério usado na feature 161 para o catálogo).
