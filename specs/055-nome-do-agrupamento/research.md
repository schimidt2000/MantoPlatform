# Research: Nome do agrupamento de eventos

Decisões técnicas da feature 055. Sem `NEEDS CLARIFICATION` pendentes.

---

## 1. Onde guardar o nome do grupo

- **Decisão**: nova coluna `group_name` (String, nullable) em `calendar_events`, preenchida
  apenas no **evento principal**. O grupo já é representado pelo principal (053/054); o nome
  é mais um atributo dele.
- **Rationale**: Princípio I (sem nova entidade); o principal é a fonte de verdade comercial
  do grupo. Satélites não usam o campo.
- **Alternativas**: tabela `event_group` dedicada (rejeitado: YAGNI; reescreveria o vínculo
  já consolidado das 053/054); guardar no satélite (rejeitado: o grupo é identificado pelo
  principal).

## 2. Fonte única do rótulo: propriedade `group_display_name`

- **Decisão**: adicionar a propriedade `group_display_name` no modelo:
  `return self.group_name or self.title`. Todas as telas (home, dashboard, pipeline, detalhe)
  consomem essa propriedade.
- **Rationale**: Princípio I/V — uma única regra de fallback, sem repetir `group_name or
  title` espalhado por templates. Garante consistência do rótulo.
- **Alternativas**: cada template fazer `ev.group_name or ev.title` (rejeitado: duplicação,
  risco de divergência).

## 3. Edição do nome: no agrupamento e depois, via action-dispatch

- **Decisão**: o campo "nome do grupo" (opcional) entra no formulário de agrupar (054) e é
  lido por `_handle_group_events`. Para editar depois, uma nova ação `rename_group` no
  mesmo `_EVENT_ACTIONS`, disponível na seção do evento principal.
- **Rationale**: Princípio I — mesmo padrão de mutação de evento já usado. Restrito a
  COMERCIAL/FINANCEIRO/SUPERADMIN (reusa `_can_group_events`).
- **Alternativas**: rota dedicada (rejeitado: duplicaria o mecanismo); editar via título do
  evento (rejeitado: o título é sincronizado do Google e não deve ser sobrescrito).

## 4. Home comercial: uma entrada por grupo

- **Decisão**:
  - **Cobranças pendentes** (`pending_payments`): já filtram `sale_value > 0`; satélites têm
    `sale_value = None` (zerado ao agrupar), então só o principal aparece — nenhuma mudança
    de query necessária. O template passa a exibir `ev.group_display_name`.
  - **Eventos sem valor** (`events_sem_valor`): hoje **não** exclui satélites (eles têm
    `sale_value = None` e apareceriam como "SEM VALOR"). Adicionar
    `CalendarEvent.group_leader_id.is_(None)` à query para ocultá-los.
- **Rationale**: FR-004/FR-005. O comportamento "uma cobrança só" já vem do modelo 053
  (satélites sem venda); falta (a) rotular pelo nome do grupo e (b) tirar o satélite da lista
  de "sem valor".
- **Alternativas**: agrupar dinamicamente no template (rejeitado: a consolidação já é
  estrutural via principal/satélite — basta filtrar e rotular).

## 5. Balanço financeiro: tabela de eventos sem satélites, rótulo pelo nome

- **Decisão**: no `dashboard()`, a tabela `events_data` passa a **pular eventos satélites**
  (`if e.is_satellite: continue`), e o template usa `ev.group_display_name` na coluna Evento.
  Os cálculos consolidados (`_compute_drg`, `_group_cost`, KPIs) **não mudam** — já excluem
  satélites e somam seus custos no principal desde a 053.
- **Rationale**: FR-006/FR-007. Evita linha duplicada do satélite (que apareceria como "Sem
  valor"), mantendo os totais idênticos.
- **Alternativas**: manter satélites na tabela com marcação (rejeitado: o usuário pediu
  explicitamente uma entrada única; satélite com R$0 polui o balanço).

## 6. Pipeline de vendas (`/vendas/`) — consistência mínima

- **Decisão**: a coluna de título do pipeline passa a usar `group_display_name` no líder
  (consistência do rótulo). Os satélites continuam visíveis com o selo "satélite" já
  existente (054) — o pipeline é uma lista operacional de vendas, não um "balanço".
- **Rationale**: aproveita a mesma propriedade sem esconder linhas; mudança trivial e
  coerente. Esconder satélites do pipeline está fora do escopo pedido (que falou de "home
  comercial" e "balanços financeiros").
- **Alternativas**: esconder satélites também no pipeline (adiado: não solicitado; manteria
  o padrão se pedido depois).

## 7. Migration manual

- **Decisão**: migration manual `..._group_name.py`, `down_revision = q3f4a5b6c7d8`,
  `op.batch_alter_table("calendar_events").add_column(group_name String nullable)`.
- **Rationale**: autogenerate quebrado por drift (memória do projeto); mesmo padrão das
  migrations recentes (053).
- **Alternativas**: autogenerate (rejeitado: gera ruído por drift pré-existente).
