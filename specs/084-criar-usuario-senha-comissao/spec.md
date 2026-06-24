# Feature Specification: Senha de primeiro uso automática + salário só comissão

**Feature Branch**: `084-criar-usuario-senha-comissao`

**Created**: 2026-06-24

**Status**: Draft

**Input**: "Ao criar usuário: (1) a senha de primeiro uso já deve vir gerada, e ao clicar em criar o
usuário, copiá-la para a área de transferência. (2) A parte de salário está quebrada — quero poder
deixar apenas comissão, ou seja, o salário em si é 0."

## Contexto

Na tela **Criar Usuário**, o super admin hoje precisa **digitar à mão** a senha de primeiro uso, e a
seção de **Salário** rejeita o cadastro com "Salário inválido. Tipo de pagamento inválido." mesmo quando
o objetivo é não definir salário ou definir **somente comissão** (salário-base 0). Como o formulário já
vem com "Salário (R$)" preenchido com "0,00" e "Tipo de pagamento" em "-- selecione --", qualquer
criação esbarra nessa validação.

Esta feature: (1) gera automaticamente a senha de primeiro uso e a copia ao criar; (2) corrige a seção
de salário para aceitar **sem salário** e **somente comissão** (salário 0).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Salário só comissão / sem salário (Priority: P1) 🎯 MVP

Como super admin, quero criar um usuário sem definir salário, ou definindo **somente comissão** (com
salário-base 0), sem ser bloqueado por erro de validação.

**Acceptance Scenarios**:

1. **Given** a tela Criar Usuário com "Salário (R$)" em "0,00" e tipo em "-- selecione --", **When**
   clico em criar, **Then** o usuário é criado **sem registro de salário** (a seção é opcional) e sem
   mensagem de erro.
2. **Given** que escolho o tipo **"Somente comissão"** (com salário 0,00), **When** crio o usuário,
   **Then** o usuário é criado com um registro de salário **somente comissão** e **salário-base 0**.
3. **Given** que escolho **"Semanal"** ou **"Dia 5 e 20"** com salário **0,00** (ou vazio), **When**
   tento criar, **Then** recebo erro pedindo um salário válido (> 0), pois esses tipos exigem valor.
4. **Given** a mesma regra na página de edição do usuário ("Registrar salário"), **When** registro
   "Somente comissão", **Then** o salário-base é 0 e é aceito.

### User Story 2 - Senha de primeiro uso gerada e copiada (Priority: P1)

Como super admin, quero que a senha de primeiro uso já venha **gerada** no formulário e que, ao **criar
o usuário**, ela seja **copiada para a área de transferência**, para eu enviar à pessoa sem digitar
nada.

**Acceptance Scenarios**:

1. **Given** que abro a tela Criar Usuário no modo "Com acesso ao sistema", **When** a página carrega,
   **Then** o campo "Senha de primeiro uso" já vem preenchido com uma senha forte gerada.
2. **Given** o campo preenchido, **When** clico em "Criar usuário", **Then** a senha é copiada para a
   área de transferência e a confirmação informa que ela foi copiada.
3. **Given** que quero outra senha, **When** uso a opção de gerar nova, **Then** o campo é atualizado
   com uma nova senha forte.
4. **Given** o modo "Apenas pagamento" (sem acesso), **When** vejo o formulário, **Then** não há senha
   a gerar nem a copiar (campo de senha não se aplica).

### Edge Cases

- Admin apaga a senha gerada e digita a própria: ao criar, copia exatamente o que estiver no campo.
- Tipo "Somente comissão" com um valor digitado (> 0): o salário-base é tratado como 0 (somente
  comissão), conforme a intenção.
- Salário preenchido (> 0) mas sem tipo selecionado: erro pedindo para selecionar o tipo de pagamento.

## Requirements *(mandatory)*

### Salário

- **FR-001**: A seção de salário MUST ser **opcional**: sem tipo selecionado e sem valor (> 0), o
  usuário é criado **sem** registro de salário, sem erro.
- **FR-002**: O tipo **"Somente comissão"** MUST ser aceito com **salário-base 0** (o valor é
  normalizado para 0).
- **FR-003**: Os tipos **"Semanal"** e **"Dia 5 e 20"** MUST exigir salário **maior que 0**.
- **FR-004**: As mesmas regras MUST valer tanto na **criação** do usuário quanto no **registro de
  salário** na edição.

### Senha de primeiro uso

- **FR-005**: No modo "Com acesso ao sistema", o campo "Senha de primeiro uso" MUST vir **pré-preenchido
  com uma senha forte** gerada ao carregar a tela.
- **FR-006**: MUST haver uma forma de **gerar uma nova** senha sob demanda.
- **FR-007**: Ao **criar o usuário** (modo com acesso), a senha do campo MUST ser **copiada para a área
  de transferência**.
- **FR-008**: A confirmação de criação MUST informar que a senha foi copiada.
- **FR-009**: A geração/cópia MUST se aplicar **apenas** ao modo com acesso (não ao "Apenas pagamento").

## Success Criteria *(mandatory)*

- **SC-001**: É possível criar um usuário sem salário, ou com "Somente comissão", em 100% das vezes sem
  erro de validação.
- **SC-002**: Um usuário "Somente comissão" fica registrado com salário-base 0.
- **SC-003**: O super admin cria um usuário com acesso **sem digitar** a senha, e a senha fica
  disponível na área de transferência logo após criar.
- **SC-004**: "Semanal"/"Dia 5 e 20" sem valor continuam sendo barrados com mensagem clara.

## Assumptions

- **Senha gerada no cliente**: a senha de primeiro uso é gerada no navegador e enviada normalmente como
  o valor do campo; permanece editável pelo admin. Continua valendo `must_change_password=True` (a
  pessoa troca no primeiro login).
- **Visibilidade**: por ser uma senha temporária a ser comunicada, o campo é exibido em texto legível
  (não mascarado), facilitando conferência antes de enviar.
- **Comprimento/força**: senha aleatória de ~12 caracteres com letras maiúsculas/minúsculas, dígitos e
  ao menos um símbolo, evitando caracteres ambíguos.
- **"Somente comissão" = salário 0**: o valor base é sempre normalizado para 0 nesse tipo; o cálculo de
  comissão em si é tratado em outras telas (não faz parte desta feature).
- **Cópia**: usa a área de transferência do navegador, com mecanismo síncrono de reserva para concluir
  a cópia antes do envio do formulário.
