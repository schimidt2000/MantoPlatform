# Data Model: Migração das últimas ferramentas Jinja para React

Nenhum modelo novo, nenhuma migration. Todos os models já existem em `app/models.py` e cobrem
100% dos requisitos do spec — o trabalho desta feature é extrair a lógica hoje inline em
`routes.py` para `*_ops.py` puros e expor via API JSON.

## SpecialExpense (`app/models.py:808`) — US1

Gasto extra pontual. Qualquer usuário cria o próprio; só SUPERADMIN aprova/rejeita/vincula.

| Campo | Tipo | Regra |
|---|---|---|
| `description` | string(200) | obrigatório |
| `category` | enum (`Figurino`/`Escritório`/`Marketing`/`Manutenção`/`Outros`) | default `Outros` |
| `amount` | Numeric(10,2) | obrigatório, > 0 |
| `expense_date` | Date | competência — mês em que o gasto impacta o balanço |
| `status` | enum (`pendente`/`aprovado`/`rejeitado`) | só SUPERADMIN transiciona |
| `disbursement_type` | enum (`reembolso`/`fornecedor`) | define `payee_name`/`payee_pix` |
| `payment_status` | string | `nao_pago`/`pago` — consumido também pelo Financeiro (dashboard/pagamentos) |
| `paid_at_creation` | bool | feature 128 — se `true`, nunca entra na Planilha de Pagamentos mesmo pago |
| `event_id` | FK CalendarEvent, nullable | vínculo opcional — gasto aprovado vira custo do evento |

API de escrita não pode duplicar a regra de "só aprovado conta no balanço" nem a de
`paid_at_creation` — ambas seguem exatamente como estão em `app/gastos/routes.py` hoje, só
extraídas para `gastos_ops.py`.

## RecurringExpense (`app/models.py:884`) / RecurringExpenseEntry (`app/models.py:1036`) — US3

Despesa que se repete numa frequência; cada ocorrência é uma parcela (`Entry`) com estado
próprio. Restrito a FINANCEIRO/SUPERADMIN.

| Campo (`RecurringExpense`) | Tipo | Regra |
|---|---|---|
| `expense_type` | enum (`variavel`/`debito_automatico`/`assinatura`/`programado`) | define o fluxo de geração de parcela |
| `amount` | Numeric, nullable | valor fixo (tipos fixos) |
| `amount_min`/`amount_max` | Numeric, nullable | faixa esperada (só `variavel`) |
| `frequency` | enum (`mensal`/`semanal`/`quinzenal`/`anual`) | feature 112 |
| `is_active` | bool | toggle — desativar não apaga histórico, só para de gerar novas parcelas |

| Campo (`RecurringExpenseEntry`) | Tipo | Regra |
|---|---|---|
| `month_ref` | string(7) "YYYY-MM" | único por `recurring_id` |
| `amount` | Numeric, nullable (só NULL em `pulado`) | |
| `status` | enum (`a_pagar`/`pago`/`registrado`/`pulado`) | transições: preencher→pagar / pular / excluir-parcela / reabrir |
| `out_of_range` (property) | bool calculada | destaque visual quando foge da faixa/valor de referência — não é regra de bloqueio |

`ensure_recurring_entries()` e `recurring_alerts()` (hoje em `routes.py:357,395`) são movidas para
`gastos_ops.py` preservando assinatura — checar outros callers (ex. Financeiro/Home) antes de
mover o import.

## OrcamentoHistory (`app/models.py:1201`) — US2, US4

Orçamento calculado e salvo. `result_snapshot` é a fonte de verdade para exibição/PDF/e-mail —
nunca recalculado a partir de preços atuais (congela o que foi cotado).

| Campo | Tipo | Regra |
|---|---|---|
| `client_name`, `event_location`, `event_date` | string, nullable | metadados de exibição na lista |
| `total_1h`/`total_2h`/`total_3h`/`total_4h` | Numeric, nullable | totais por faixa de hora, usados na listagem sem precisar desserializar o snapshot |
| `form_snapshot` | JSON (texto) | estado de entrada do formulário — permite reabrir/editar |
| `result_snapshot` | JSON (texto) | resultado congelado — usado por PDF (`pdf.gerar_orcamento_pdf`) e pela tela de detalhe |

Registros anteriores ao formato atual (sem `result_snapshot` completo) passam por
`_legacy_quote(entry)` — a mover para função pública em `quote_ops.py`, reusada por Jinja e API,
para não duplicar a lógica de adaptação (FR-007).

## Configuração de Preços — US5

Não é uma tabela SQLAlchemy: `app/orcamento/settings.py` persiste via `load()`/`save()` (JSON em
disco/`SiteSetting`-like, confirmado lendo o módulo). A API nova (`orcamento_read.py`/
`orcamento_write.py`) é um adapter fino sobre essas duas funções — nenhuma migration, nenhum
model novo.

## EventRating (`app/models.py:1231`) / EventSubRating (`:1261`) / EventRatingVersion (`:1281`) — US6

Avaliação de desempenho de um talento em um evento, com sub-notas por categoria e histórico de
edição.

| Campo (`EventRating`) | Tipo | Regra |
|---|---|---|
| `score` | int 1–5 | nota geral |
| `edit_count` / `edited_at` | int / datetime | cada edição gera uma `EventRatingVersion` com o snapshot anterior |

| Campo (`EventSubRating`) | Tipo | Regra |
|---|---|---|
| `category` | enum (`som`/`figurino`/`texto`/`coordenacao`/`maquiagem`/`artista`) | |
| `subject_talent_id` | FK Talent, nullable | preenchido só nas categorias "de pessoa" (ex. `artista`) |
| `score` | int 1–5 | usado no cálculo de distribuição por categoria |

Modo anônimo: `SiteSetting.ratings_fully_anonymous` (flag única do sistema) — só SUPERADMIN
alterna; quando ligado, a API omite o autor/talent avaliado das respostas para quem não é
SUPERADMIN, mesma regra hoje aplicada na view Jinja.

## FormResponse (`app/models.py:1633`) / FormFieldDefinition (`:1685`) — US7

Resposta recebida de um formulário público e a definição editável dos campos desse formulário.
O fluxo público (preencher/enviar) já está migrado — esta feature cobre só o lado staff.

| Campo (`FormResponse`) | Tipo | Regra |
|---|---|---|
| `data` | JSON (texto) | lista de seções/campos na ordem original — respostas antigas (pré-123) podem não ter `field_key`, ainda assim exibidas |
| `client_id` / `event_id` | FK, nullable | vínculos manuais ou automáticos (`event_link_source`) |
| `event_link_locked` | bool | uma vez `true` (humano decidiu), a automação de vínculo nunca mais sobrescreve |

| Campo (`FormFieldDefinition`) | Tipo | Regra |
|---|---|---|
| `form_type` | enum (`comum`/`corporativo`) | |
| `section_name` | string | agrupamento visual — muda de seção quando o valor muda, percorrendo por `order` |
| `is_system` | bool | campo usado por outras partes do sistema (extração de contratante/telefone/CPF/CNPJ/CEP) — **não pode ser excluído nem ter `field_type`/`field_key` alterado pelo editor** (regra a preservar tal qual no `formularios_ops.py`) |

## Sem mudança de schema

Nenhum campo novo é necessário para nenhuma das 7 user stories. Todo o trabalho é extração de
núcleo de negócio (`*_ops.py`) + camada de API + apresentação React.
