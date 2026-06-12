# Feature Specification: Seleção em massa correta na Planilha de Pagamentos

**Feature Branch**: `044-pagamentos-selecao`

**Created**: 2026-06-12

**Status**: Draft

**Input**: User description: "está filtrado por no banco, mas ao clicar para selecionar todos,
seleciona todos, inclusive fora do banco — isso está incorreto. E teve alguns pagamentos, vindos
dos gastos extras, que ao selecionar e mudar em massa o estado, não alterou; precisou alterar um
por um. E as comissões está sem quadradinho para selecionar na esquerda também."

## Contexto

Na Planilha de Pagamentos:
1. Com um filtro ativo (ex.: "No banco"), o "selecionar tudo" marca também as linhas escondidas
   pelo filtro — a ação em massa atinge itens que o usuário não está vendo.
2. Itens vindos de **gastos extras** não são tratados pela ação em massa: o pedido é enviado como
   se fossem cachês, então o gasto não muda — e, pior, um cachê de número igual pode ser alterado
   por engano.
3. Linhas de **comissões** não têm caixa de seleção — não entram em nenhuma ação em massa.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Selecionar tudo respeita o filtro (Priority: P1)

Com o filtro "No banco" ativo, o "selecionar tudo" marca apenas as linhas visíveis; ao trocar de
filtro, seleções de linhas que ficaram escondidas são desfeitas.

**Acceptance Scenarios**:

1. **Given** filtro "No banco" ativo, **When** clica em selecionar tudo, **Then** só as linhas no
   banco ficam marcadas e a contagem reflete só elas.
2. **Given** linhas selecionadas, **When** troca o filtro e algumas somem, **Then** as escondidas
   são desmarcadas (a ação em massa nunca atinge o que não está na tela).

---

### User Story 2 - Ações em massa funcionam para gastos extras (Priority: P1)

Selecionar pagamentos de gastos extras e aplicar "Marcar pago"/"No banco"/"Não pago" atualiza
todos de uma vez — e nunca altera um cachê por engano.

**Acceptance Scenarios**:

1. **Given** 3 gastos selecionados, **When** aplica "Marcar pago", **Then** os 3 ficam pagos.
2. **Given** um gasto selecionado, **When** qualquer ação em massa é aplicada, **Then** nenhum
   cachê com número coincidente é alterado.
3. **Given** gastos selecionados, **When** aplica "Excluir", **Then** gastos NÃO são excluídos por
   aqui (registro pertence ao módulo de gastos) e o usuário é avisado.

---

### User Story 3 - Comissões com caixa de seleção (Priority: P2)

Linhas de comissão têm caixa de seleção e aceitam mudança de situação em massa (pago / não pago).

**Acceptance Scenarios**:

1. **Given** a planilha com comissões, **Then** cada linha de comissão tem caixa de seleção.
2. **Given** comissões selecionadas, **When** "Marcar pago", **Then** todas as comissões daquele
   vendedor/período ficam pagas (mesmo efeito do controle individual).
3. **Given** comissões selecionadas, **When** "Excluir" ou "No banco", **Then** comissões são
   ignoradas com aviso (não têm esses estados) — os demais itens selecionados seguem normalmente.

---

### Edge Cases

- Seleção mista (cachês + salários + gastos + comissões): cada tipo é tratado corretamente na
  mesma ação.
- "No banco" não existe para comissão: a ação em massa "No banco" ignora comissões (aviso).
- Excluir em massa continua funcionando para cachês e salários.
- A contagem "N selecionados" sempre bate com as linhas visíveis marcadas.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O "selecionar tudo" MUST marcar apenas linhas visíveis no filtro atual; trocar o
  filtro MUST desmarcar linhas que saíram da tela.
- **FR-002**: Ações em massa MUST tratar cada tipo de item (cachê, salário, gasto, comissão) no
  seu próprio registro — 0 alterações em registros de tipo errado.
- **FR-003**: Gastos extras MUST aceitar mudança de situação em massa; exclusão em massa de gastos
  MUST ser recusada com aviso.
- **FR-004**: Linhas de comissão MUST ter caixa de seleção; em massa aceitam pago/não pago;
  "no banco"/excluir MUST ser ignorados com aviso.
- **FR-005**: Após uma ação em massa, o usuário MUST ver aviso do que foi feito (e do que foi
  ignorado, se houver).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Com filtro ativo, 100% dos itens marcados pelo selecionar tudo estão visíveis.
- **SC-002**: 0 registros de tipo errado alterados por ações em massa.
- **SC-003**: Mudar a situação de N gastos selecionados leva 1 ação (antes: N ações).
- **SC-004**: Comissões podem ser marcadas pagas em massa.

## Assumptions

- Exclusão de gasto continua só no módulo de gastos; exclusão de comissão só na tela de comissões
  (financeiro). A planilha exclui apenas cachês e salários, como hoje.
- Comissão segue com dois estados visíveis (pago / não pago), como no controle individual atual.
