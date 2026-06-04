# Feature Specification: Feedback de senha (shake) + não limpar form ao falhar criação

**Feature Branch**: `018-feedback-followups`

**Created**: 2026-06-04

**Status**: Draft

**Input**: Follow-ups da política de feedback (constituição v1.1.0): (1) na tela de senha, ao tentar
salvar com requisitos faltando, chacoalhar os requisitos não cumpridos; (2) na criação de evento,
se a criação falhar no servidor, não limpar o que foi preenchido.

## Contexto

Após reforçar o Princípio V (feedback visual), dois pontos ficaram pendentes:

1. **Tela de senha do portal**: o botão "Salvar" fica desabilitado até cumprir tudo, então clicar
   não dá feedback de *o que* falta. O usuário quer que, ao tentar salvar, os requisitos não
   cumpridos **chacoalhem** (shake), deixando claro o que resolver.
2. **Criar evento**: a validação no cliente (feature 017) já cobre os erros comuns, mas se a criação
   falhar no servidor (ex.: API do Google indisponível), a tela ainda re-renderiza **limpando** o
   que foi digitado. Deve **preservar** os dados.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Chacoalhar requisitos de senha faltantes (Priority: P1)

Na tela de criar/redefinir senha, ao tentar salvar com requisitos não cumpridos (ou senhas que não
coincidem), o envio é bloqueado e os requisitos faltantes chacoalham, com foco no campo de senha.

**Acceptance Scenarios**:

1. **Given** requisitos não cumpridos, **When** o usuário clica em salvar, **Then** o envio é
   bloqueado e cada requisito faltante (marcado com "✗") chacoalha.
2. **Given** as senhas não coincidem, **When** o usuário tenta salvar, **Then** o aviso de
   divergência é exibido/chacoalhado e o envio é bloqueado.
3. **Given** todos os requisitos cumpridos e senhas iguais, **When** o usuário salva, **Then** o
   botão entra em carregamento e não permite envio duplicado.

---

### User Story 2 - Não perder o formulário quando a criação falha (Priority: P1)

Ao criar um evento, se o servidor retornar erro (validação de segurança ou falha ao criar no Google
Calendar), a tela reexibe os dados já preenchidos (campos do evento, valores e a lista de
personagens), em vez de limpar tudo.

**Acceptance Scenarios**:

1. **Given** um envio que o servidor rejeita, **When** a tela recarrega com o erro, **Then** os
   campos preenchidos (título, data, horários, tipo, local, descrição, valores, vendedor, data da
   venda) reaparecem com o que foi digitado.
2. **Given** personagens adicionados, **When** a tela recarrega com erro, **Then** as linhas de
   personagem reaparecem (nome, maquiagem, cantor, cachê).
3. **Given** um arquivo anexado (NF/contrato/comprovante), **When** a tela recarrega com erro,
   **Then** o anexo precisa ser reenviado (limitação do navegador) — claramente o único item não
   restaurado.

---

### Edge Cases

- **Senha**: com JavaScript desligado, o servidor continua validando (rede de segurança).
- **Criar evento**: anexos (arquivos) nunca são restaurados por nenhuma aplicação web (segurança do
  navegador) — é a única exceção; os demais campos voltam.
- **Fluxo a partir do orçamento**: ao recarregar com erro, os valores digitados prevalecem sobre o
  pré-preenchimento do orçamento.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Na(s) tela(s) de senha, ao tentar salvar com requisitos faltando, o envio MUST ser
  bloqueado e os requisitos não cumpridos MUST chacoalhar (shake).
- **FR-002**: Senhas divergentes MUST bloquear o envio com aviso visível.
- **FR-003**: Com tudo válido, o botão de salvar senha MUST entrar em estado de carregamento e
  impedir envio duplicado.
- **FR-004**: Na criação de evento, qualquer re-renderização por erro do servidor MUST preservar os
  campos preenchidos (dados do evento, valores, vendedor/data de venda) e a lista de personagens.
- **FR-005**: A única exceção permitida à preservação são os **arquivos anexados**, que o navegador
  não permite restaurar — e isso deve ficar evidente.
- **FR-006**: Nenhuma regra de validação do servidor MUST ser enfraquecida; o feedback é camada
  adicional.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% das tentativas de salvar senha com requisitos faltando mostram shake e não
  enviam.
- **SC-002**: 0 envios de senha duplicados quando válido (botão em carregamento).
- **SC-003**: 100% dos campos de texto/seleção e linhas de personagem reaparecem após erro do
  servidor na criação de evento (exceto anexos).

## Assumptions

- Aplica-se às duas telas de senha (criar e redefinir), por consistência.
- "Chacoalhar os requisitos" = animação de shake nas linhas de requisito não cumpridas.
- Restauração da criação de evento é feita no servidor (reexibindo os valores enviados); anexos são
  a única exceção.
