# Implementation Plan: KPIs financeiros de evento agrupado

**Branch**: `137-kpi-eventos-agrupados` | **Date**: 2026-07-20 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/137-kpi-eventos-agrupados/spec.md`

## Summary

O painel financeiro da página do evento (`event_detail.html`, seção "Comercial", KPIs de
Custo de cachês / Gastos extras / Lucro líquido) hoje calcula esses três valores olhando
só para o evento aberto. Quando o evento pertence a um grupo comercial (feature 053 —
principal + satélites, um único contrato), isso produz números sem sentido: a "Venda" já
vem do principal, mas o custo/gastos vêm só do evento individual — o "Lucro líquido"
resultante não representa o contrato real.

Abordagem: no route handler `event_detail()`, resolver a lista de "eventos do grupo"
(o próprio evento se ele não pertence a grupo nenhum; ou principal+satélites se pertence)
e usar essa lista para agregar `event_cost`, `event_expenses` e `event_bv_total` — em vez
de olhar só `event.roles`/`event.id`. O template ganha um aviso "valores do contrato
inteiro" quando o evento pertence a um grupo, e a lista de gastos extras passa a mostrar a
qual evento do grupo cada gasto pertence. O detalhamento de cachê por evento individual já
existe (seção "Elenco" lista talento + cachê do evento aberto) — nenhuma UI nova precisa
ser criada para a User Story 2, só garantir que ela continua visível ao lado do total
agregado.

## Technical Context

**Language/Version**: Python 3.11, Flask + SQLAlchemy (stack já existente, nenhuma
dependência nova)

**Primary Dependencies**: Flask, SQLAlchemy, Jinja2 (nenhuma adição)

**Storage**: PostgreSQL (produção e `manto_local`) — nenhuma mudança de schema; a feature
é puramente de leitura/agregação sobre `CalendarEvent`, `EventRole`, `SpecialExpense` e os
acréscimos (`OrcamentoAcrescimo`/equivalente) já existentes

**Testing**: script de verificação funcional com Flask test client contra `manto_local`
(padrão do projeto), cobrindo grupo com múltiplos eventos e evento avulso (sem regressão)

**Target Platform**: aplicação web server-side (Flask + Jinja2), mesma superfície de
`event_detail.html`

**Project Type**: web application (monolito Flask existente)

**Performance Goals**: N/A — mesma ordem de grandeza de queries que já rodam na página do
evento hoje (um grupo tem tipicamente 2-10 eventos, não é um agregado pesado)

**Constraints**: não pode alterar como Venda/Comissão/dados comerciais são calculados
(já seguem o principal, fora de escopo); não pode mudar a Planilha de Pagamentos nem
relatórios financeiros gerais — escopo é só a página do evento

**Scale/Scope**: um único endpoint (`GET /events/<id>`) e um template
(`event_detail.html`); sem migração de banco

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **I. Reutilizar antes de criar**: `CalendarEvent` já expõe `is_satellite`,
  `is_group_leader`, `group_leader`, `satellites`, `group_display_name` (feature 053) — a
  única peça nova é uma função pequena que resolve "todos os eventos do grupo dado
  qualquer membro dele", reaproveitando essas properties existentes. Nenhuma lógica
  duplicada.
- **II. Padrões de código Python**: função nova com type hints + docstring, dentro do
  limite de ~30 linhas, sem aninhamento profundo.
- **III. Arquitetura em camadas**: a agregação é lógica de leitura dentro do próprio
  handler `event_detail()` (mesmo padrão já usado para `event_cost`/`event_expenses`
  hoje — não é regra de negócio nova, é o mesmo cálculo existente, só que somado por
  múltiplos eventos); nenhuma query solta nova em outra camada.
- **IV. Não quebrar o que funciona**: evento fora de grupo é o caminho dominante e MUST
  ficar bit-a-bit idêntico ao comportamento atual (FR-002) — verificação funcional cobre
  esse caso explicitamente, não só o caso de grupo.
- **V. UI/UX consistente**: o aviso "valores do contrato inteiro" segue o padrão visual já
  usado no alert-info de agrupamento (linhas 1363-1375/1378-1420 de
  `event_detail.html`); nenhuma cor hardcoded nova.
- **VII. Valores monetários**: nenhuma mudança na formatação — os totais agregados
  continuam passando pelo mesmo filtro `| brl` já usado.

Nenhuma violação. Gate passa sem exceções.

## Project Structure

### Documentation (this feature)

```text
specs/137-kpi-eventos-agrupados/
├── plan.md              # This file
├── spec.md
├── checklists/
│   └── requirements.md
└── tasks.md             # Phase 2 output (/speckit-tasks)
```

Sem `research.md`/`data-model.md`/`contracts/`/`quickstart.md`: não há incógnita técnica
a pesquisar (stack e padrões já estabelecidos no projeto), não há entidade nova, e a
feature não expõe nenhuma interface externa (é uma página server-rendered interna).

### Source Code (repository root)

```text
app/
├── calendar/
│   └── routes.py        # event_detail(): nova função helper de agregação por grupo +
│                         #   event_cost/event_expenses/event_bv_total passam a somar
│                         #   os eventos do grupo quando aplicável
└── templates/
    └── event_detail.html # KPIs "Custo (cachês)"/"Gastos extras"/"Lucro líquido" ganham
                          #   aviso de "valores do contrato" quando agrupado; lista de
                          #   gastos extras ganha coluna/rótulo do evento de origem
```

## Design Decisions

1. **Helper de resolução do grupo** — em `app/calendar/routes.py`, função nova (perto de
   `_clear_event_side_tables`/outras helpers de evento):

   ```python
   def _group_events(event: CalendarEvent) -> list[CalendarEvent]:
       """Retorna todos os eventos do mesmo grupo comercial que `event` (ele incluso).

       Se `event` não pertence a nenhum grupo, retorna [event] — mesmo comportamento
       de hoje, sem agregação.
       """
       if event.is_satellite:
           leader = event.group_leader
           return [leader, *leader.satellites]
       if event.is_group_leader:
           return [event, *event.satellites]
       return [event]
   ```

2. **Agregação em `event_detail()`** — substituir o cálculo atual (que usa só `event`)
   por uma soma sobre `_group_events(event)`:
   - `event_cost` = soma de `cache_value` de `EventRole` com talento escalado, de todos
     os eventos do grupo (hoje: só do evento aberto).
   - `event_expenses` = todos os `SpecialExpense` com `status="aprovado"` vinculados a
     qualquer evento do grupo, ordenados por data (hoje: só `event_id=event.id`) — cada
     item já carrega `event_id`, então o template consegue rotular a origem (FR-005) sem
     campo novo.
   - `event_bv_total` = soma dos acréscimos BV de todos os eventos do grupo (hoje: só do
     evento aberto), para manter "Lucro líquido" consistente com custo/gastos agregados.
   - `event_expenses_total` segue sendo `sum(e.amount for e in event_expenses)`, já
     correto automaticamente pela lista agregada.
   - Uma nova variável `event_group_size = len(_group_events(event))` é passada ao
     template só para decidir se mostra o aviso "valores do contrato inteiro" (>1) — sem
     duplicar a lógica de `is_satellite`/`is_group_leader` que o template já usa em outro
     lugar.
   - Nenhuma mudança em `sale_value`, `commission_rate`, `event_commission` (FR-006) —
     continuam vindo só de `event` (que já é o principal quando satélite consulta, pela
     regra existente de "dados comerciais seguem o principal" — não, na verdade
     `event_commission` hoje é calculado com `event.sale_value` do evento ABERTO, que é
     None para satélite; ver nota abaixo).

   **Nota importante**: ao investigar o código atual, `event.sale_value` de um satélite é
   zerado (`None`) ao entrar no grupo (`_apply_satellite`, feature 053) — ou seja, hoje,
   abrir um satélite já mostra "Venda: R$ 0,00" e "Comissão: R$ 0,00" no KPI grid, porque
   o grid lê `event.sale_value` (o aberto), não o do principal. Isso é PARTE do mesmo
   problema relatado (números sem sentido num evento agrupado) mas o FR-006 do spec disse
   "fora de escopo mudar como Venda/Comissão são calculados". Reconciliando: FR-006 se
   refere a NÃO mudar a *regra de negócio* de que só o principal tem venda própria
   (comportamento arquitetural já estabelecido e usado pelas outras seções da tela,
   como pagamentos/parcelas) — mas o KPI grid especificamente deve, ao mostrar o painel
   de um evento agrupado, exibir Venda/Comissão do **principal** em vez de `0,00`
   quando o evento aberto é satélite, para o "Lucro líquido" fazer sentido (esse é o
   próprio ponto central do FR-001/SC-001: o lucro tem que bater com o resultado real do
   contrato). Decisão: KPI grid usa `_group_events(event)[0]` como "evento de referência
   comercial" (o principal, sempre primeiro da lista) para `sale_value`/
   `sale_value_gross`/`commission_rate`/`event_commission` — sem alterar o formulário de
   edição "Dados de Venda" em si (que continua editável só no principal, regra
   inalterada).

3. **Template (`event_detail.html`)**:
   - Onde o KPI grid usa `event.sale_value`/`event.commission_rate`/`event.seller`,
     passar a usar uma variável de contexto `kpi_event` (= evento de referência comercial,
     resolvida no passo 2) no lugar de `event` — sem tocar no formulário "Dados de Venda"
     em si, que continua ligado a `event`/`event.id` (edição sempre no evento realmente
     aberto, comportamento inalterado).
   - Acima do `kpi-grid` existente (linha ~1874), quando `event_group_size > 1`: um
     `<div class="meta">` simples — "Valores do contrato inteiro ({{ event_group_size }}
     eventos agrupados)" — reaproveitando a classe `.meta` já usada em todo o resto da
     tela, sem CSS novo.
   - Na tabela "Gastos extras vinculados" (linha ~1905-1930): quando `event_group_size >
     1`, adicionar uma coluna "Evento" mostrando `g.event.title` (relationship já
     existente em `SpecialExpense`) — coluna só aparece quando faz diferença (grupo com
     mais de 1 evento); em evento avulso a tabela fica idêntica a hoje.

4. **Verificação funcional**: script novo (padrão dos anteriores, `scripts/db/verify_137_*.py`,
   gitignored) criando via ORM um grupo sintético (1 principal + 2 satélites, cada um com
   `EventRole` de talento e `SpecialExpense` aprovado próprios) e conferindo, pelo test
   client:
   - Abrir o principal e um satélite mostram os MESMOS totais agregados de custo/gastos/
     lucro/venda/comissão.
   - Evento avulso (fora de qualquer grupo) mostra exatamente os números de antes
     (comparação com o cálculo manual dos seus próprios dados).
   - Gasto extra de status "pendente" continua fora do total.
   - Tabela de gastos extras rotula corretamente o evento de origem quando há mais de um
     evento no grupo.
