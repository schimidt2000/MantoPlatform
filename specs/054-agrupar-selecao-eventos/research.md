# Research: Seleção de eventos no agrupamento (busca + multi-seleção)

Decisões técnicas para a feature 054. Todas resolvidas — sem `NEEDS CLARIFICATION`
pendentes (a única decisão de UX foi confirmada com o usuário antes do spec).

---

## 1. Padrão de seleção: lista com busca + checkbox (não dual-list)

- **Decisão**: lista única de candidatos com campo de busca acima e um checkbox por
  evento; após marcar, o usuário escolhe o principal entre os participantes.
- **Rationale**: confirmado com o usuário; mais simples e aderente ao mobile-first
  (Princípio V / constituição) que um dual-list de duas colunas, que fica apertado no
  celular. Menos JS e zero dependências novas.
- **Alternativas consideradas**: dual-list "mover para a direita" (rejeitado: pior em
  telas estreitas, mais código); manter um-a-um (rejeitado: é a dor relatada).

## 2. Busca no cliente, reaproveitando o padrão da feature 045

- **Decisão**: filtrar a lista de candidatos **no cliente** (JS), reusando o helper de
  normalização acento-insensível já presente em
  `app/templates/financeiro/pagamentos.html`:
  `(s||'').toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g,'')`.
- **Rationale**: Princípio I (reutilizar). O volume é de centenas de eventos — carregar
  todos e filtrar no cliente é instantâneo e evita uma rota/endpoint novo de busca. Mesma
  experiência já validada na planilha de pagamentos.
- **Alternativas consideradas**: busca no servidor com AJAX/paginação (rejeitado: YAGNI
  para o volume atual; adicionaria endpoint, estado e complexidade).

## 3. Lista de candidatos: remover a janela de ±3 dias

- **Decisão**: na rota `event_detail`, trocar o filtro de janela
  (`start_at` entre ±3 dias) por **todos os eventos não-ENSAIO exceto o próprio**,
  ordenados por data desc (mais recentes primeiro), passando também o estado de
  agrupamento de cada um (é satélite? é principal?).
- **Rationale**: FR-002 — eventos do mesmo contrato em datas distantes precisam aparecer.
  A busca client-side cobre a navegação nessa lista maior.
- **Alternativas consideradas**: aumentar a janela (ex.: ±90 dias) — rejeitado: ainda
  arbitrário e não resolve contratos com eventos muito espaçados.

## 4. Eventos já agrupados: exibir desabilitados, não ocultar

- **Decisão**: eventos que já são satélites de outro grupo ou já são principais aparecem
  na lista **desabilitados** (checkbox bloqueado) com uma etiqueta explicativa ("já
  agrupado"), em vez de sumirem.
- **Rationale**: Princípio V (feedback claro) + FR-006/FR-010 — o usuário entende por que
  não pode selecioná-los, e a impossibilidade de marcá-los evita o erro de servidor que
  apagaria a seleção. As validações de servidor (FR-007) permanecem como backstop.
- **Alternativas consideradas**: ocultar os já agrupados (rejeitado: usuário fica sem
  entender a ausência); deixar selecionável e só barrar no servidor (rejeitado: viola
  FR-010, apagaria a seleção em erro).

## 5. Contrato da ação: de `target_event_id` (1) para `target_event_ids[]` (N)

- **Decisão**: `_handle_group_events` passa a ler `request.form.getlist("target_event_ids")`
  (múltiplos) em vez de um único `target_event_id`. `leader_event_id` continua único
  (o principal escolhido). Validação aplicada a cada satélite; a operação é atômica
  (ou agrupa todos os válidos da seleção, ou recusa apontando o inválido — ver contrato).
- **Rationale**: FR-003/FR-004. Mantém a mesma `action=group_events` e o mesmo padrão de
  action-dispatch (`_EVENT_ACTIONS`) já usado — sem rota nova (Princípio I).
- **Atomicidade**: se **qualquer** evento selecionado for inválido (já satélite, já
  principal, ENSAIO, igual ao principal, ou com venda preenchida sem confirmação), a
  operação inteira é recusada com aviso indicando o evento problemático e **nada** é
  alterado — assim a seleção do usuário é preservada (FR-010) e não há grupo parcial
  inesperado.
- **Alternativas consideradas**: agrupar os válidos e ignorar os inválidos (rejeitado:
  resultado ambíguo, usuário não sabe o que entrou); criar rota dedicada (rejeitado:
  duplicaria o mecanismo da 053).

## 6. Prevenção de erro no cliente (Princípio V / FR-010)

- **Decisão**: validar no cliente antes de enviar — ≥1 evento marcado e um principal
  escolhido; se algum marcado tiver venda, exigir a marcação do checkbox de confirmação
  de substituição. Botão de envio desabilita ao submeter (anti-duplo-envio).
- **Rationale**: o erro de validação mais comum nunca chega ao servidor, então a seleção
  não se perde. Espelha o feedback por campo das features 028/031.
- **Alternativas consideradas**: só validar no servidor (rejeitado: perderia a seleção em
  erro, violando FR-010 e o Princípio V).

## 7. Escolha do principal entre N participantes

- **Decisão**: após a seleção, a escolha do principal é um conjunto de opções (radio)
  contendo o evento atual + os eventos marcados, com o **evento atual pré-selecionado**
  como padrão (FR-004). A lista de opções de principal é montada no cliente a partir dos
  checkboxes marcados.
- **Rationale**: o usuário decide qual concentra os dados comerciais; o atual é o padrão
  natural (é de onde a ação parte). Atualizar as opções no cliente evita recarregar.
- **Alternativas consideradas**: sempre o atual como principal (rejeitado: o usuário pode
  querer outro como principal); escolher o principal antes de marcar (rejeitado: fluxo
  menos natural — primeiro define o conjunto, depois quem lidera).
