# Feature Specification: Filtro por card + troca de situação em tempo real (Pagamentos)

**Feature Branch**: `033-pagamentos-filtro-realtime`

**Created**: 2026-06-09

**Status**: Draft

**Input**: User description: "melhorar a filtragem e ordenação da página de pagamentos. Cada card em
cima deve ser clicável e servir para filtrar (clicar em 'No banco' → só os do banco, e assim por
diante). Ao mudar a situação (no banco / pago / não pago) deve manter o filtro atual. Hoje toda troca
recarrega a página; o ideal é não recarregar (tempo real); se por alguma lógica precisar atualizar,
seguimos assim."

## Contexto

Na **Planilha de Pagamentos** há 5 cards de resumo no topo (Total no período, Pagos, No banco,
Pendentes, Futuro) e uma tabela de itens, cada um com uma **situação** (Não pago / Pago / No banco).

Problemas hoje:
- Os **cards são apenas informativos** — não dá para clicar para filtrar a lista.
- Mudar a situação de um item dispara um **recarregamento da página inteira** (envio de formulário),
  o que é lento e **perde qualquer contexto** (e perderia o filtro).

Objetivos:
1. **Cards clicáveis como filtro**: clicar em um card mostra só os itens daquela situação; clicar de
   novo (ou em "Total") volta a mostrar tudo.
2. **Troca de situação em tempo real**: mudar Não pago / Pago / No banco **sem recarregar** a página,
   atualizando a linha e os totais na hora, **mantendo o filtro atual**.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Filtrar pelos cards (Priority: P1)

A pessoa clica em um card do topo e a tabela passa a mostrar **apenas** os itens daquela situação.

**Why this priority**: É o pedido central de filtragem; agiliza muito achar o que pagar.

**Independent Test**: Clicar em "No banco" e confirmar que só aparecem itens "No banco"; clicar em
"Pagos" e confirmar que só aparecem os pagos.

**Acceptance Scenarios**:

1. **Given** a lista com itens variados, **When** clico no card "No banco", **Then** a tabela mostra
   só os itens com situação "No banco" e o card fica visivelmente ativo.
2. **Given** o card "Pagos" ativo, **When** clico nele de novo (ou no card "Total no período"),
   **Then** a tabela volta a mostrar todos os itens.
3. **Given** os cards "Pendentes" e "Futuro", **When** clico em cada um, **Then** a lista mostra,
   respectivamente, os não pagos do período e os não pagos futuros.
4. **Given** um filtro ativo sem itens correspondentes, **When** aplico, **Then** vejo um estado vazio
   claro ("nenhum item nesta situação").

---

### User Story 2 - Trocar a situação sem recarregar, mantendo o filtro (Priority: P1)

Ao mudar a situação de um item (Não pago ↔ Pago ↔ No banco), a mudança é salva **sem recarregar** a
página; a linha e os totais dos cards se atualizam na hora, e o **filtro ativo é mantido**.

**Why this priority**: É a principal dor relatada (recarregar a cada troca, perdendo o contexto).

**Independent Test**: Com o filtro "No banco" ativo, mudar um item para "Pago" e confirmar que a
página não recarrega, os totais mudam, e o filtro "No banco" continua ativo.

**Acceptance Scenarios**:

1. **Given** um item na lista, **When** mudo sua situação, **Then** a mudança é salva sem recarregar e
   a linha reflete a nova situação imediatamente.
2. **Given** um filtro ativo, **When** mudo a situação de um item, **Then** o filtro permanece ativo
   (a lista continua filtrada).
3. **Given** que mudei uma situação, **When** observo os cards, **Then** os totais (Pagos / No banco /
   Pendentes / Futuro / Total) refletem a mudança na hora.
4. **Given** que um item deixa de pertencer ao filtro atual após a mudança (ex.: filtro "No banco" e
   marco "Pago"), **When** salvo, **Then** ele sai da visão filtrada de forma coerente.
5. **Given** uma falha ao salvar (ex.: conexão), **When** tento mudar, **Then** recebo um aviso e a
   situação anterior é mantida na tela (sem mudança "fantasma").

---

### Edge Cases

- **Recarregamentos legítimos** (trocar o mês, ações em massa): o filtro ativo MUST ser reaplicado
  após o recarregamento (não voltar ao "tudo").
- **Comissão (item agregado)**: muda em tempo real como os demais; "No banco" para comissão é tratado
  como "a pagar" (comportamento atual preservado).
- **Filtro sem resultados**: estado vazio claro.
- **Falha de rede ao salvar**: reverte a situação na tela e avisa (sem perder dados).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Cada card de resumo (Total, Pagos, No banco, Pendentes, Futuro) MUST ser clicável e
  filtrar a tabela para a situação correspondente; "Total no período" mostra todos.
- **FR-002**: O card do filtro ativo MUST ter destaque visual; clicar no card ativo de novo limpa o
  filtro.
- **FR-003**: Mudar a situação de um item MUST salvar **sem recarregar** a página (tempo real),
  atualizando a linha imediatamente.
- **FR-004**: Após mudar uma situação, os totais dos cards MUST refletir a mudança na hora.
- **FR-005**: O filtro ativo MUST ser mantido ao mudar situações e MUST ser reaplicado após
  recarregamentos legítimos (troca de mês, ações em massa).
- **FR-006**: Se o salvamento falhar, a situação anterior MUST ser mantida na tela com aviso (sem
  mudança fantasma).
- **FR-007**: O comportamento de salvar a situação no banco de dados MUST permanecer correto e
  consistente (mesma regra de hoje, inclusive comissão e itens futuros).
- **FR-008**: As ações em massa e a exportação MUST continuar funcionando.

### Key Entities

- Nenhuma entidade nova. A feature afeta a **apresentação e a interação** da Planilha de Pagamentos
  (cards, filtro, atualização da situação). Sem mudança de banco.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Clicar em qualquer card filtra a lista para a situação correspondente em 100% dos casos.
- **SC-002**: Trocar a situação não recarrega a página em 100% dos casos de sucesso.
- **SC-003**: Em 100% das trocas, os totais dos cards ficam coerentes com a lista, sem recarregar.
- **SC-004**: O filtro ativo é mantido em 100% das trocas de situação e reaplicado após recarregamentos
  legítimos.
- **SC-005**: 0 mudanças "fantasma" — falha ao salvar sempre reverte a situação exibida.

## Assumptions

- Filtro é **único** por vez (um card ativo), não combinável.
- "No banco" para comissão segue mapeando para "a pagar" (regra atual).
- A ordenação atual (por data) é mantida; "melhorar a ordenação" aqui se concretiza pela filtragem por
  situação (sem nova regra de ordenação além da existente). Caso se queira ordenar por outra coluna,
  fica como follow-up.
- Sem mudança de banco. O endpoint de salvar situação passa a também responder de forma adequada para
  atualização em tempo real, mantendo o caminho antigo como reserva.
