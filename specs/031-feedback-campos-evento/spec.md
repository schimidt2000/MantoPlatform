# Feature Specification: Feedback de validação completo em "Criar evento"

**Feature Branch**: `031-feedback-campos-evento`

**Created**: 2026-06-08

**Status**: Draft

**Input**: User description: "Preciso que verifique por completo a página de criação de evento se ela
está dando feedbacks que façam sentido para cada campo preenchido incorretamente."

## Contexto

Auditoria da página de criação de evento (`/events/new`) revelou que o feedback de validação é
**inconsistente entre os campos**:

| Campo | Marcado obrigatório (`*`) | Validado de verdade? | Feedback hoje |
|---|---|---|---|
| Data | sim | sim (cliente + servidor) | bom (destaca campo + rola até a mensagem) |
| Início / Fim | sim (após fix 030) | sim (cliente + servidor) | bom |
| Fim ≤ Início | — | sim | bom |
| Título | sim | sim (cliente + servidor) | bom |
| **Valor de venda** | **sim** | **NÃO** | **nenhum** (incoerência: tem `*` mas não valida) |
| **Vendedor responsável** | não | NÃO | nenhum |
| Parcelas (quando "Dividido no PIX") | — | NÃO | nenhum |
| Transporte / Acréscimo | não | tolerante (máscara) | ok (opcional) |
| Data da venda | não (padrão hoje) | — | ok |

Problemas concretos:
- **Valor de venda** mostra asterisco de obrigatório mas **não é validado** — se vazio, o evento é
  criado sem valor, sem nenhum aviso (mesma classe do bug do horário recém-corrigido).
- **Vendedor responsável** define a comissão do mês, mas pode ficar vazio sem aviso.
- **Parcelas** (no "Dividido no PIX") pode ficar vazia/ inválida sem aviso.
- Campos que o servidor recusa exibem a mensagem **no topo** de um formulário longo; o ideal é que
  **o campo problemático** seja destacado, não só a faixa no topo.

Decisões do usuário: **Valor de venda** e **Vendedor responsável** passam a ser **obrigatórios**
(com feedback claro no campo). O princípio geral: **todo campo com regra dá um aviso que faz sentido,
no próprio campo, e nenhum campo marcado como obrigatório fica sem validação.**

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Cada campo errado avisa no próprio campo (Priority: P1)

Ao tentar criar um evento com um campo obrigatório vazio ou inválido, a pessoa vê **uma mensagem
clara apontando exatamente qual campo** está com problema, com destaque visual nesse campo — sem
precisar adivinhar nem procurar.

**Why this priority**: É o objetivo central pedido ("feedbacks que façam sentido para cada campo").

**Independent Test**: Deixar cada campo obrigatório vazio, um de cada vez, e confirmar que o aviso
aponta o campo certo e o destaca.

**Acceptance Scenarios**:

1. **Given** o valor de venda vazio, **When** clico em "Adicionar à Agenda", **Then** vejo "Informe o
   valor de venda" e o campo é destacado/recebe foco.
2. **Given** o vendedor não selecionado, **When** envio, **Then** vejo "Selecione o vendedor
   responsável" e o campo é destacado.
3. **Given** "Dividido no PIX" selecionado e parcelas vazio/ inválido, **When** envio, **Then** vejo
   um aviso pedindo o número de parcelas (2 a 12).
4. **Given** qualquer campo obrigatório vazio, **When** envio, **Then** a tela leva o foco/rolagem
   até o primeiro campo com problema.

---

### User Story 2 - Coerência entre "obrigatório" e validação (Priority: P1)

Nenhum campo marcado com asterisco (`*`) pode passar sem ser validado, e nenhum campo validado como
obrigatório fica sem o asterisco. O que parece obrigatório **é** obrigatório.

**Why this priority**: A causa da confusão atual é o "valor de venda" ter `*` mas não validar.

**Acceptance Scenarios**:

1. **Given** a página de criar evento, **When** olho os campos com `*`, **Then** todos são realmente
   validados (Data, Início, Fim, Título, Valor de venda, Vendedor).
2. **Given** o vendedor agora obrigatório, **When** vejo o rótulo, **Then** ele tem o `*`.

---

### User Story 3 - Mensagens corretas, nunca enganosas (Priority: P2)

As mensagens descrevem o problema real do campo. Um campo inválido nunca gera uma mensagem sobre
outra coisa (ex.: erro de dados não pode aparecer como "falha do Google").

**Why this priority**: Reforça a confiança; recentemente um campo vazio gerava mensagem de "Google".

**Acceptance Scenarios**:

1. **Given** um campo obrigatório vazio, **When** envio, **Then** a mensagem é sobre aquele campo —
   não uma mensagem genérica/de sistema.

---

### Edge Cases

- **Vários campos errados ao mesmo tempo**: todos são destacados; a tela rola até o primeiro.
- **Valor de venda "0,00"**: tratado como inválido (precisa ser maior que zero).
- **Bypass do cliente** (JS desligado): o servidor recusa igualmente, com a mesma mensagem por campo
  (rede de segurança).
- **Erro preserva tudo**: nenhum dado preenchido é perdido ao recarregar com erro (Princípio V).
- **Proteção de clique duplo**: continua valendo (não regredir 028).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Todo campo obrigatório vazio/inválido MUST gerar uma mensagem específica que **identifica
  o campo** e o **destaca** (realce + foco/rolagem até ele).
- **FR-002**: **Valor de venda** MUST ser obrigatório e maior que zero; vazio/zero bloqueia o envio
  com "Informe o valor de venda".
- **FR-003**: **Vendedor responsável** MUST ser obrigatório; sem seleção bloqueia o envio com
  "Selecione o vendedor responsável", e o rótulo MUST exibir o asterisco.
- **FR-004**: Quando a forma de pagamento for "Dividido no PIX", o **número de parcelas** MUST ser
  válido (2 a 12); caso contrário, aviso específico.
- **FR-005**: Todo campo marcado com `*` MUST ser efetivamente validado (sem asterisco "decorativo").
- **FR-006**: As validações MUST existir no cliente (feedback imediato no campo) **e** no servidor
  (rede de segurança), com mensagens equivalentes.
- **FR-007**: Em erro, os dados preenchidos MUST ser preservados e a tela MUST levar até o problema.
- **FR-008**: Nenhuma mensagem MUST atribuir a um campo um problema que não é dele (sem mensagens
  enganosas/genéricas para erro de campo).
- **FR-009**: A proteção contra envio duplicado MUST continuar funcionando (não regredir).

### Key Entities

- Nenhuma entidade nova. A feature afeta a **validação e o feedback** do formulário de criação de
  evento. Sem mudança de banco.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% dos campos obrigatórios vazios/inválidos produzem mensagem específica do campo, com
  destaque e rolagem até ele.
- **SC-002**: 0 campos com `*` sem validação real (auditoria conferida).
- **SC-003**: 0 mensagens enganosas (campo inválido nunca gera mensagem de outro assunto).
- **SC-004**: 100% das falhas preservam o que foi preenchido.
- **SC-005**: Valor de venda e Vendedor passam a bloquear o envio quando vazios, em 100% das tentativas
  (cliente e servidor).

## Assumptions

- Campos obrigatórios da tela: Data, Início, Fim, Título, **Valor de venda**, **Vendedor responsável**.
  Demais (transporte, acréscimo, descrição, local, data da venda, nota fiscal) permanecem opcionais.
- "Dividido no PIX" exige parcelas válidas; os outros métodos de pagamento não exigem campos extras.
- Reaproveita o mecanismo de destaque/rolagem já existente (fix 028) e o padrão de validação por
  campo já usado em Data/Título (Princípio I). Sem migration.
- Esta feature é construída sobre o fix 030 (horário obrigatório), que segue incluído.
