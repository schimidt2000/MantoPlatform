# Implementation Plan: Agrupamento de Eventos por Contrato

**Branch**: `053-agrupar-eventos` | **Date**: 2026-06-16 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/053-agrupar-eventos/spec.md`

## Summary

Permitir que um usuário COMERCIAL/FINANCEIRO/SUPERADMIN vincule dois ou mais
`CalendarEvent` já existentes (criados separadamente porque cada um tem
horário/elenco/personagens diferentes, mas pertencem ao mesmo contrato) sob um
único "evento principal", que passa a concentrar os dados comerciais (venda,
comissão, nota fiscal, forma de pagamento). Os demais eventos do grupo tornam-se
"satélites": continuam com elenco/figurino/cachês próprios (intocados), mas
perdem seus campos comerciais individuais. Painel Financeiro e Painel de Vendas
passam a tratar o grupo como uma única venda (1 evento vendido), somando os
cachês de todos os satélites no custo (CPV) do principal.

Abordagem técnica: um único campo novo, auto-referencial, em `CalendarEvent`
(`group_leader_id`), seguindo o mesmo padrão de simplicidade já usado por
`parent_event_id` (vínculo de Ensaios) — sem nova tabela, sem novo serviço
externo, 100% dentro do stack Flask + SQLAlchemy + Jinja2 já existente.

## Technical Context

**Language/Version**: Python 3.11 (já em uso no projeto)

**Primary Dependencies**: Flask, SQLAlchemy, Flask-Migrate (Alembic), Flask-Login — todas já presentes, nenhuma dependência nova

**Storage**: SQLite (dev) / PostgreSQL (produção, Railway) — via migration manual (autogenerate está quebrado por drift pré-existente, conforme `migrations-autogenerate-quebrado` já documentado)

**Testing**: Não há suite automatizada no projeto (`pytest`/`conftest.py` inexistentes); verificação por script standalone + Flask test_client + checagem manual no app real, como já praticado nas features 051/052

**Target Platform**: Web (navegador desktop/mobile), backend Flask servido via gunicorn no Railway

**Project Type**: Web application monolítica (Flask + Jinja2), um único projeto (não há frontend/backend separados)

**Performance Goals**: N/A — operação é manual, baixo volume (poucos agrupamentos por mês); sem requisito de performance específico além do padrão já aceito pelo painel financeiro

**Constraints**: Não pode alterar o comportamento de `parent_event_id` (Ensaios); não pode quebrar a sincronização com Google Calendar; não pode afetar casting/figurino/pagamento individual de cachês (FR-013)

**Scale/Scope**: Escopo único: modelo (1 coluna nova), 1 rota de agrupar + 1 de desagrupar, ajustes em 2 telas (`event_detail.html`, `financeiro/dashboard.html` + `vendas/pipeline.html`) e nas funções de cálculo do financeiro (`app/financeiro/routes.py`)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **I. Reutilizar antes de criar** — PASS. Reaproveita o padrão já existente de
  vínculo auto-referencial em `CalendarEvent` (`parent_event_id`), só que com
  semântica e nome de campo distintos para não colidir com o mecanismo de
  Ensaios. Reaproveita `_event_cost`, `_compute_drg`, `_pct` já existentes no
  financeiro — apenas estende para somar cachês do grupo.
- **II. Padrões de código Python** — PASS. Novas funções terão type hints,
  docstring Google style, nomes descritivos; nenhuma função passará de ~30
  linhas (vão ser quebradas em helpers como já é o padrão em `financeiro/routes.py`).
- **III. Arquitetura em camadas** — PASS. Lógica de agrupamento fica em helpers
  no módulo de rotas (mesmo padrão já usado no projeto, que não tem camada de
  `services/` separada — rotas chamam helpers puros, sem regra de negócio
  espalhada em templates).
- **IV. Não quebrar o que funciona** — PASS, com atenção: a alteração mais
  sensível é em `app/financeiro/routes.py` (`_compute_drg`, contagem de
  eventos, auditoria de "sem valor") e no fluxo de sync do Google Calendar
  (`app/calendar/routes.py`). Plano cobre verificação explícita de que o novo
  campo nunca é tocado pelo bloco de sync, e que casting/figurino/pagamentos
  continuam consultando `EventRole` por evento individual, sem mudança.
- **V. UI/UX consistente** — PASS. Botão de agrupar/desagrupar segue padrão de
  confirmação para ação que limpa dados (Princípio V: ações destrutivas exigem
  confirmação) e estado de loading/feedback ao salvar.
- **VI. Planejar antes de codar** — PASS. Spec → Plan → Tasks → Implement já em andamento.
- **VII. Valores monetários em padrão BR** — PASS. Nenhum valor monetário novo
  é exibido fora do helper `money()` / formatação já usada no financeiro;
  campos comerciais do satélite somem da tela (não há novo campo de dinheiro
  para digitar).

Nenhuma violação a justificar em Complexity Tracking.

## Project Structure

### Documentation (this feature)

```text
specs/053-agrupar-eventos/
├── plan.md              # Este arquivo
├── research.md          # Fase 0 — decisões técnicas
├── data-model.md        # Fase 1 — modelo de dados
├── quickstart.md        # Fase 1 — roteiro de verificação manual
├── contracts/
│   └── routes.md        # Fase 1 — contrato das rotas novas
└── tasks.md              # Fase 2 (/speckit-tasks)
```

### Source Code (repository root)

```text
app/
├── models.py                          # + campo CalendarEvent.group_leader_id (self FK)
├── calendar/
│   ├── routes.py                      # + rotas agrupar/desagrupar; validações
│   └── service.py                     # (sem mudança — confirmar que sync não toca o campo novo)
├── financeiro/
│   └── routes.py                      # + helper de custo agregado do grupo; ajuste em
│                                       #   _compute_drg, contagem de eventos, auditoria
├── templates/
│   ├── event_detail.html              # + banner de grupo (principal/satélite) + ação agrupar/desagrupar
│   ├── financeiro/dashboard.html       # (sem mudança visual; dados já corrigidos no backend)
│   └── vendas/pipeline.html            # + indicação de evento satélite agrupado
migrations/versions/
└── <novo>_group_leader_id.py          # migration manual (Alembic), seguindo padrão batch_alter_table
```

**Structure Decision**: Aplicação monolítica Flask já existente — sem novos
diretórios/projetos. Toda a feature cabe nos módulos `calendar` (gestão do
vínculo) e `financeiro` (cálculo agregado), mais um campo novo em `models.py`
e ajustes pontuais em 3 templates.

## Complexity Tracking

*Sem violações da constituição a justificar.*
