# Feature Specification: Página de Acesso Negado (403)

**Feature Branch**: `050-erro-acesso-negado`

**Created**: 2026-06-15

**Status**: Ready

**Input**: User description: "Página de erro 403 com GIF divertido e texto 'Opa, parece que vc não tem acesso a essa página', com botão de contato via WhatsApp (mesmo formato da página 404 existente)."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Ver página amigável ao ser barrado (Priority: P1)

Quando um usuário tenta acessar uma área sem permissão, vê uma página amigável com GIF divertido, mensagem clara e botão para reportar pelo WhatsApp — em vez de cair na página de "não encontrado".

**Why this priority**: Melhora a experiência e facilita o suporte, diferenciando claramente "sem permissão" de "não existe".

**Independent Test**: Acessar qualquer rota protegida com um usuário sem a role necessária e verificar a página exibida.

**Acceptance Scenarios**:

1. **Given** um usuário sem a permissão correta, **When** ele acessa uma URL restrita, **Then** vê a página 403 com GIF, mensagem "Opa, parece que vc não tem acesso a essa página" e botão do WhatsApp.
2. **Given** a página 403, **When** o usuário clica em "Ir para o início", **Then** é redirecionado para a home.
3. **Given** a página 403 e o WhatsApp configurado, **When** o usuário clica em "Reportar pelo WhatsApp", **Then** abre conversa com mensagem pré-preenchida sobre o acesso negado.

---

### Edge Cases

- Se o WhatsApp não estiver configurado no ambiente, o botão de WhatsApp não aparece (igual ao comportamento da 404).
- Usuário não autenticado tentando acesso direto a URL protegida: vê a 403 normalmente.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O sistema MUST exibir uma página dedicada (403) — diferente da 404 — quando o acesso é negado por falta de permissão.
- **FR-002**: A página MUST conter o GIF `giphy.gif` (arquivo já presente no projeto).
- **FR-003**: A página MUST exibir o texto "Opa, parece que vc não tem acesso a essa página" como mensagem principal.
- **FR-004**: A página MUST ter botões "Ir para o início" e "Voltar", seguindo o mesmo layout da 404.
- **FR-005**: A página MUST exibir botão "Reportar pelo WhatsApp" quando o número estiver configurado, com mensagem contextualizada para acesso negado.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Usuário sem permissão vê a página 403 dedicada (não a 404) em 100% dos casos de `abort(403)`.
- **SC-002**: A mensagem "Opa, parece que vc não tem acesso a essa página" é visível sem scroll na tela.
- **SC-003**: O botão WhatsApp abre com mensagem pré-preenchida relevante ao problema de acesso.

## Assumptions

- O arquivo `giphy.gif` já existe na pasta raiz do projeto e será movido para `static/`.
- O número do WhatsApp de suporte é configurado via variável de ambiente `SUPPORT_WHATSAPP` (igual ao fluxo da 404/500).
- Nenhuma alteração no banco de dados é necessária.
- O layout da página segue exatamente o padrão da `404.html` existente (mesmos estilos CSS inline).
