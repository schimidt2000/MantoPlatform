# Feature Specification: Talento estrangeiro (sem CPF) + telefone com país (092)

**Feature Branch**: `092-cadastro-estrangeiro-telefone-pais`

**Created**: 2026-06-29

**Status**: Draft

**Input**: "Uma pessoa que trabalhará conosco é estrangeira, logo não tem CPF, e algumas questões do
portal são baseadas no CPF. Precisamos de uma forma de lidar com isso — no formulário a pessoa deve poder
marcar que é estrangeira, e as verificações importantes passam a ser por telefone e/ou e-mail. Também mudar
o campo de telefone para o padrão onde se seleciona primeiro o país e depois digita. Todos os telefones já
cadastrados devem receber o +55 no início (foram preenchidos só com o DDD da cidade)."

## Contexto

Hoje o **CPF** é obrigatório no cadastro público (`/cadastro`) e é a **chave de identidade** do Portal do
Artista: login, primeiro acesso e recuperação de senha usam o CPF. Uma pessoa **estrangeira** não tem CPF,
então não consegue se cadastrar nem acessar o portal. Além disso, os telefones foram cadastrados apenas com
o **DDD** (sem o código do país), o que quebra links de WhatsApp e não suporta números de outros países.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Estrangeiro se cadastra sem CPF (Priority: P1) 🎯 MVP

Como pessoa estrangeira sem CPF, quero **marcar que sou estrangeiro** no formulário público para conseguir
me cadastrar usando meu **passaporte/documento**, telefone e e-mail no lugar do CPF.

**Acceptance Scenarios**:

1. **Given** o formulário público, **When** marco "Sou estrangeiro(a) (não tenho CPF)", **Then** o campo de
   CPF deixa de ser obrigatório e o sistema aceita o envio sem CPF.
2. **Given** que sou estrangeiro, **When** envio sem documento de identificação, **Then** recebo um aviso
   pedindo o número do documento/passaporte (substituto do CPF).
3. **Given** um cadastro **não** estrangeiro, **When** envio, **Then** o CPF continua **obrigatório** e
   validado (11 dígitos + unicidade), como hoje.

### User Story 2 - Estrangeiro acessa o portal por e-mail (Priority: P1)

Como talento estrangeiro (sem CPF), quero **entrar no portal pelo meu e-mail** (em vez do CPF) para usar o
primeiro acesso, o login e a recuperação de senha.

**Acceptance Scenarios**:

1. **Given** a tela de login, **When** informo meu **e-mail** e senha, **Then** entro no portal normalmente.
2. **Given** o primeiro acesso, **When** informo meu **e-mail**, **Then** recebo a senha temporária no
   e-mail cadastrado.
3. **Given** um talento brasileiro, **When** informo o **CPF**, **Then** o acesso continua funcionando como
   hoje (compatibilidade total).

### User Story 3 - Telefone com seletor de país (Priority: P2)

Como pessoa preenchendo o cadastro, quero **escolher o país (código DDI)** e depois digitar o número, para
que o telefone fique completo e correto (inclusive para estrangeiros).

**Acceptance Scenarios**:

1. **Given** o campo de telefone, **When** abro o seletor de país, **Then** o **Brasil (+55)** já vem
   selecionado por padrão.
2. **Given** que escolho outro país e digito o número, **When** envio, **Then** o telefone é salvo com o
   código do país (ex.: `+1 ...`).
3. **Given** os telefones **já cadastrados** (preenchidos só com DDD), **When** a migração roda, **Then**
   todos passam a ter o **+55** no início.

### Edge Cases

- Telefone já salvo que (por acaso) já começa com `+` → a migração **não** duplica o prefixo.
- Estrangeiro sem CPF: dois ou mais cadastros sem CPF **não** podem colidir por causa do CPF vazio.
- Link de WhatsApp deve usar o telefone **com** código do país, sem duplicar o `55`.
- E-mail é usado como identidade do estrangeiro → dois talentos não devem compartilhar o mesmo e-mail de
  login (avisar/comportar-se de forma previsível se houver duplicado).

## Requirements *(mandatory)*

- **FR-001**: O formulário público MUST permitir marcar **"sou estrangeiro (não tenho CPF)"**; nesse caso o
  CPF NÃO é obrigatório.
- **FR-002**: Para estrangeiro, o sistema MUST exigir um **documento de identificação** (passaporte/RG/doc)
  como substituto do CPF.
- **FR-003**: Para não estrangeiro, o CPF MUST permanecer obrigatório e validado (11 dígitos + único).
- **FR-004**: O Portal (login, primeiro acesso, recuperar senha) MUST aceitar **CPF ou e-mail** como
  identificador, mantendo o fluxo por CPF inalterado para quem tem CPF.
- **FR-005**: O campo de telefone MUST oferecer **seleção de país (DDI)** com **Brasil (+55)** como padrão,
  e salvar o número **com** o código do país.
- **FR-006**: Uma rotina única (migração) MUST inserir **+55** no início de todos os telefones existentes que
  ainda não tenham um código de país (`+`), sem duplicar para os que já tenham.
- **FR-007**: Os links de WhatsApp MUST usar o telefone com código do país, **sem** duplicar o `55`.

## Success Criteria *(mandatory)*

- **SC-001**: Uma pessoa estrangeira consegue concluir o cadastro **sem CPF** em uma única tentativa.
- **SC-002**: Um talento estrangeiro consegue **fazer primeiro acesso e login** usando o e-mail.
- **SC-003**: 100% dos telefones já cadastrados passam a ter código de país (`+55` quando faltava), sem
  duplicação.
- **SC-004**: Talentos brasileiros continuam cadastrando e acessando o portal **sem nenhuma mudança** no que
  fazem hoje.

## Assumptions

- O canal de verificação prático para estrangeiro é o **e-mail** (já existe infraestrutura de e-mail no
  sistema; não há envio de SMS). O telefone fica como contato/WhatsApp.
- O documento substituto do CPF para estrangeiro é informado no campo de documento já existente (RG/doc) e na
  **foto do documento** (já obrigatória).
- A identidade de login do estrangeiro é o **e-mail cadastrado**.
- "Inserir +55 em todos" significa **prefixar +55** ao conteúdo atual (que era só DDD+número), conforme o
  pedido — assumindo que todos os existentes são brasileiros.
