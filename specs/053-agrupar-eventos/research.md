# Research: Agrupamento de Eventos por Contrato

**Feature**: 053-agrupar-eventos | **Date**: 2026-06-16

Nenhum item da seção Technical Context do plan.md ficou marcado como
`NEEDS CLARIFICATION` — todas as decisões de produto já foram confirmadas
pelo usuário durante o `/speckit-specify` (ver `spec.md`, seção Assumptions).
Este documento registra as decisões técnicas de implementação necessárias
para a fase de design.

## 1. Como representar o vínculo de grupo no banco

**Decision**: Adicionar uma única coluna nova em `CalendarEvent`:
`group_leader_id` (Integer, FK para `calendar_event.id`, nullable, sem
`ondelete='CASCADE'`).

- `group_leader_id IS NULL` → evento independente (comportamento atual, sem mudança).
- `group_leader_id == self.id` → não permitido (FR-004), validado na rota.
- `group_leader_id == <id de outro evento>` e esse outro evento não é satélite de ninguém → este evento é satélite daquele.
- Um evento é "principal" se `CalendarEvent.query.filter_by(group_leader_id=evento.id)` retornar 1+ resultados.

**Rationale**: Espelha exatamente o padrão já existente e aprovado de
`parent_event_id` (self-FK simples, sem tabela associativa), o que é a opção
de menor complexity cost e mais fácil de auditar/entender pela equipe.
Atende ao requisito de estrutura plana (Assumptions: "apenas 2 níveis") porque
a validação na rota impede que um evento que já é principal (tem satélites)
seja escolhido como satélite de outro, e impede que um satélite vire principal.

**Alternatives considered**:
- *Tabela associativa `EventGroup` (M:N)*: rejeitada — over-engineering para
  uma relação que é sempre 1 principal : N satélites, nunca M:N. Constituição
  Princípio I (reutilizar/simplicidade) pesa contra introduzir uma tabela nova
  quando uma coluna resolve.
- *Reutilizar `parent_event_id`*: rejeitada explicitamente pelo usuário e pela
  spec — colidiria semanticamente com o mecanismo de Ensaios (que já consulta
  `parent_event_id` para lógica própria de auto-clear de roles).

## 2. Onde limpar os campos comerciais do satélite

**Decision**: Lógica centralizada em um helper `_apply_satellite(event)` em
`app/calendar/routes.py`, chamado pela rota de agrupar. Limpa exatamente os
campos listados na FR-005: `sale_value`, `sale_value_gross`, `sale_date`,
`with_invoice`, `is_cortesia_permuta`, `seller_id`, `commission_rate`,
`payment_method`, `payment_installments`, `payment_due_date`,
`transport_value`, `acrescimo_value`, `invoice_file`,
`orcamento_history_id`.

**Rationale**: Mantém a lógica de negócio fora do template e fora da camada de
financeiro (que só lê, não deveria gravar em `CalendarEvent`), seguindo
Princípio III (rotas chamam helpers, sem lógica espalhada em Jinja).

**Alternatives considered**: limpar via trigger de banco — rejeitado, projeto
não usa triggers em nenhum outro lugar e isso quebraria a auditoria explícita
exigida pela FR-015 (log de quem fez o quê).

## 3. Como o financeiro agrega custo (CPV) do grupo

**Decision**: Estender a função existente `_event_cost(event)` em
`app/financeiro/routes.py` com uma nova função `_group_cost(event)` que,
quando `event` é principal, soma `_event_cost(event)` + `_event_cost(s)` para
cada satélite `s`. Todos os pontos que hoje chamam `_event_cost(e)` para
calcular CPV/margem em listagens de "eventos vendidos" passam a usar
`_group_cost(e)` apenas para o evento principal; satélites são explicitamente
filtrados (`group_leader_id IS NOT NULL` → excluído da listagem de vendas,
igual ao tratamento já existente de `is_cortesia_permuta` na feature 052).

**Rationale**: Reaproveita 100% a função já testada em produção
(`_event_cost`), só adicionando a soma do grupo por cima — menor superfície de
mudança possível no módulo mais sensível do sistema (financeiro), que sofreu
um incidente de produção nesta mesma sessão.

**Alternatives considered**: recalcular tudo do zero numa nova query agregada
SQL — rejeitado por aumentar a complexidade e o risco de divergência com a
lógica Python já existente de `_event_cost` (que trata `cache_value` Numeric
com cuidado, conforme o bugfix de Decimal/float desta sessão).

## 4. Onde aplicar o filtro "satélite não conta como evento vendido"

**Decision**: No mesmo ponto onde a feature 052 já filtra
`is_cortesia_permuta` (a lista `normais` usada para `cpv`, `marketing`,
contagem de eventos e ticket médio em `app/financeiro/routes.py`), adicionar
`and e.group_leader_id is None` ao filtro existente.

**Rationale**: É literalmente o mesmo padrão de exclusão já estabelecido —
zero lógica nova, apenas uma condição adicional no filtro que já existe.

## 5. Sync do Google Calendar

**Decision**: Nenhuma mudança em `app/calendar/service.py` ou no bloco de
sync de `app/calendar/routes.py`. Confirmado (Explore agent, sessão anterior)
que o sync atualiza campos em-place por `google_event_id` e nunca toca
`parent_event_id` — o novo campo `group_leader_id` seguirá exatamente a mesma
propriedade por construção (não está na lista de campos que o sync escreve).

**Rationale**: Atende FR-014 e SC-006 sem exigir código defensivo extra.

## 6. Migration

**Decision**: Migration manual (autogenerate quebrado por drift
pré-existente, conforme memória do projeto). Adiciona coluna
`group_leader_id` (Integer, nullable) + FK constraint para `calendar_event.id`
via `batch_alter_table`, seguindo o padrão das migrations manuais recentes do
projeto (ex.: `7cea4da9e282_figurino_native_fields.py`).

**Rationale**: Consistente com o processo já documentado e usado nas últimas
features.
