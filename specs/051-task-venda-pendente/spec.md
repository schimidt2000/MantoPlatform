# Feature Specification: Alertas de eventos sem valor de venda

**Feature Branch**: `051-task-venda-pendente`

**Created**: 2026-06-15

**Status**: Ready

**Input**: User description: "Eventos sem valor de venda após a data definida no painel de configurações criem uma task de urgência para o setor comercial preencher os eventos com os dados corretos."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Ver eventos sem preenchimento comercial (Priority: P1)

O time comercial (e o super admin) abre a home e vê imediatamente quais eventos ainda não têm valor de venda preenchido — separados das cobranças pendentes — para saber o que precisa de atenção urgente.

**Why this priority**: Eventos sem valor de venda não entram na régua de cobranças e ficam invisíveis; o comercial não sabe que falta dados.

**Independent Test**: Criar um evento futuro sem preencher "Valor antes do desconto" / "Valor de venda final" e verificar se aparece como alerta na home.

**Acceptance Scenarios**:

1. **Given** um evento após a `release_date` sem valor de venda preenchido, **When** o comercial/superadmin abre a home, **Then** o evento aparece no painel comercial com badge vermelho "SEM VALOR".
2. **Given** um evento com valor de venda preenchido, **When** o comercial abre a home, **Then** esse evento NÃO aparece na lista de "sem valor" (apenas em cobranças, se aplicável).
3. **Given** um evento do tipo ENSAIO, **When** o comercial abre a home, **Then** esse evento NÃO aparece na lista (ensaios não têm valor de venda).
4. **Given** um evento anterior à `release_date`, **When** o comercial abre a home, **Then** esse evento NÃO aparece na lista (fora do período rastreado pelo sistema).
5. **Given** que nenhum evento está sem valor, **When** o comercial abre a home, **Then** o painel comercial não exibe a seção de pendências de dados.

---

### Edge Cases

- Evento com `sale_value_gross` preenchido mas `sale_value` (final) zerado: trata como sem valor — o comercial precisa confirmar o valor final.
- Evento cancelado ou removido do Google Calendar: não aparece (já não existe no banco).
- `release_date` não configurado: usa hoje como cutoff (igual ao comportamento atual das tasks).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O sistema MUST listar, no painel comercial da home, todos os eventos após a `release_date` que não possuam valor de venda final preenchido (nulo ou zero).
- **FR-002**: Eventos do tipo ENSAIO MUST ser excluídos da lista.
- **FR-003**: Cada item da lista MUST exibir: nome do evento, data do evento e badge "SEM VALOR" em vermelho.
- **FR-004**: Cada item MUST ter link direto para a página de detalhes do evento.
- **FR-005**: A lista MUST ser exibida dentro do painel "💰 Comercial" já existente na home, antes das cobranças pendentes (maior urgência).
- **FR-006**: O contador no cabeçalho do painel Comercial MUST refletir o total combinado de alertas (sem valor + cobranças pendentes).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% dos eventos sem valor de venda após a release_date aparecem na lista, sem falsos positivos.
- **SC-002**: A seção desaparece completamente quando todos os eventos têm valor preenchido.
- **SC-003**: O time comercial consegue ir do alerta ao preenchimento do valor em no máximo 2 cliques.

## Assumptions

- "Sem valor de venda" = `sale_value` nulo ou zero no banco. `sale_value_gross` não é critério suficiente sozinho.
- A `release_date` configurada em Admin → Configurações é a mesma já usada para tasks de casting/figurino.
- Eventos de ENSAIO são identificados pelo campo `event_type` ou pelo título — o mesmo filtro `exclude_ensaios` já usado na home.
- Nenhuma alteração de modelo/banco é necessária.
- Visível apenas para COMERCIAL, FINANCEIRO e SUPERADMIN (mesmo `show_comercial` atual).
