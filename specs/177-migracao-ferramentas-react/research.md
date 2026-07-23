# Phase 0 Research: Migração das últimas ferramentas Jinja para React

Nenhum `NEEDS CLARIFICATION` restou no Technical Context do plan.md — as decisões abaixo
documentam escolhas feitas a partir da leitura do código existente (não há ambiguidade de
requisito, só decisões de mapeamento técnico).

## RBAC por área (replicar como função, nunca decorator Flask-Login, por FR-006)

- **Decision**: cada API nova reimplementa o mesmo check de papel já usado na view Jinja
  equivalente, como função chamada no início do handler (padrão de toda a migração 144).
- **Gastos Extras** (`app/gastos/routes.py:29-31,80`): qualquer usuário autenticado pode listar/
  criar gasto próprio; só **SUPERADMIN** vê todos os gastos e aprova/rejeita/exclui/vincula a
  evento (`_is_superadmin()`).
- **Gastos Recorrentes** (`app/gastos/routes.py:304-316`): **FINANCEIRO ou SUPERADMIN**
  (`_can_manage_recorrentes()`), sem o caso "próprio usuário" que existe em Gastos Extras.
- **Avaliação de Casting** (`app/talents/routes.py:262-264,318-319,555-559`): qualquer usuário
  autenticado vê avaliações (`@login_required` simples); só **SUPERADMIN** liga/desliga o modo
  anônimo total e (por `is_superadmin`) enxerga o autor mesmo quando outros usuários veem
  anonimizado.
- **Formulários (staff/admin)** (`app/formularios/routes.py:99,106-108,119-121,640`):
  **COMERCIAL, FINANCEIRO ou SUPERADMIN** para visualizar/associar/buscar; **apenas SUPERADMIN**
  para excluir resposta e para o editor de campos (`can_edit_structure`).
- **Calculadora / Histórico / PDF de Orçamento** (`app/orcamento/routes.py:31,34-45`):
  **COMERCIAL ou SUPERADMIN** (`_require_vendas`, conjunto `_CAN_USE` — nome do decorator não
  reflete o RoleName real, é papel COMERCIAL).
- **Configuração de Preços** (`app/orcamento/routes.py:47-53,856-859`): **apenas SUPERADMIN**
  (`_require_superadmin`).

## Extração de lógica inline → `*_ops.py`

- **Decision**: cada `*_ops.py` novo é puro (sem `flask.request`/`render_template`/`flash`),
  recebe dados já validados/parseados e devolve dicts/models/exceções próprias de validação —
  mesmo padrão dos `*_ops.py` das fatias 145-176 (ex. `package_ops.py` da 175).
- **Gastos** (`gastos_ops.py`): funções para criar/aprovar/rejeitar/excluir/vincular
  `SpecialExpense` e para o CRUD completo de `RecurringExpense`/`RecurringExpenseEntry` (criar,
  editar, toggle, preencher/pular parcela, pagar/reabrir/excluir parcela). `ensure_recurring_entries()`
  e `recurring_alerts()` (`routes.py:357,395`) são movidas para dentro do módulo mas mantêm a
  mesma assinatura pública — checar callers em outros blueprints (ex. dashboard/financeiro) antes
  de mover, e ajustar os imports desses callers para o novo caminho.
- **Avaliações** (`rating_ops.py`): filtros por período/categoria/evento, cálculo de distribuição
  de notas por categoria, resolução de autor considerando modo anônimo, toggle do modo anônimo
  (`SiteSetting.ratings_fully_anonymous`).
- **Formulários (staff)** (`formularios_ops.py`): associar/desassociar cliente, vincular/
  desvincular evento, excluir resposta, busca, e as operações do editor de campos (`FormFieldDefinition`:
  criar/editar/mover/excluir campo, com guarda contra alterar/excluir campo `is_system`).
- **Orçamento** (`quote_ops.py`): a orquestração hoje em `_process_quote()`
  (`routes.py:163-583`, ~420 linhas) é quebrada em funções menores (≤30 linhas cada, princípio II)
  que chamam `pricing.py`/`transport.py` já existentes; config de preços continua 100% em
  `settings.py` (só ganha um adapter fino na API); histórico/PDF reusa `_legacy_quote()` (adaptar
  para função pública do módulo) e `pdf.gerar_orcamento_pdf()` sem alteração.

## Nomenclatura de módulos de API (evitar colisão, por Constraint do plan.md)

- **Decision**: `app/api/formularios_admin_read.py` / `formularios_admin_write.py` para o lado
  staff — o nome `formularios_write.py` já existe e cobre exclusivamente o fluxo público `/f/*`
  (schema + submit). Os demais domínios (`gastos_*`, `ratings_*`, `orcamento_*`) não têm módulo
  homônimo hoje em `app/api/`, então seguem a convenção simples `<dominio>_read.py`/`_write.py`.
- **Alternativa considerada**: um único `orcamento_read.py`/`_write.py` cobrindo calculadora +
  config de preços + histórico/PDF (adotada) vs. três pares separados — rejeitada porque os três
  fluxos compartilham o mesmo blueprint Jinja de origem e a mesma checagem de RBAC (exceto
  config de preços, que é SUPERADMIN-only e fica isolada em funções próprias dentro do mesmo
  módulo, não em arquivo separado).

## Armazenamento da Configuração de Preços

- **Decision**: `app/orcamento/settings.py` persiste a configuração via `load()`/`save()`
  (JSON, não uma tabela SQLAlchemy dedicada — confirmado lendo `settings.py:209-232`). A API nova
  só chama essas duas funções existentes; nenhuma migration é necessária.

## PDF e e-mail do histórico de orçamento

- **Decision**: `GET /api/orcamento/historico/<id>/pdf` retorna bytes via
  `app/orcamento/pdf.py:gerar_orcamento_pdf(quote)` (já existente), consumido no frontend por
  `apiFetchBlob` (mesmo padrão do primeiro download binário da migração, feature 160). O envio por
  e-mail reaproveita o serviço de e-mail já usado por outras áreas (`email_service`, usado por
  admin/config — feature 168) — nenhum provedor novo.

## Registros legados de `OrcamentoHistory`

- **Decision**: `_legacy_quote(entry)` (`routes.py:595-631`) vira uma função pública dentro de
  `quote_ops.py` reusada tanto pela view Jinja quanto pela API de histórico, garantindo que
  orçamentos salvos antes do formato "snapshot" atual continuem sendo exibidos e gerando PDF
  corretamente (FR-007).
