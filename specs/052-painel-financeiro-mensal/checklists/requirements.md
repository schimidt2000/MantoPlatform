# Specification Quality Checklist: Painel Financeiro Mês a Mês

**Created**: 2026-06-15
**Feature**: [spec.md](../spec.md)

## Content Quality
- [x] Focado em valor de negócio (corrige distorção de permuta, separa realizado/projetado)
- [x] Escrito para stakeholders (financeiro/superadmin)
- [x] Todas as seções obrigatórias preenchidas
- [x] Detalhes de implementação mantidos em Assumptions (stack), não nos requisitos

## Requirement Completeness
- [x] Sem marcadores [NEEDS CLARIFICATION] (3 dúvidas resolvidas com o usuário)
- [x] Requisitos testáveis e sem ambiguidade (cascata da DRE com fórmulas exatas)
- [x] Critérios de sucesso mensuráveis
- [x] Cenários de aceitação definidos por user story
- [x] Edge cases identificados (divisão por zero, permuta com venda, período cruzando meses)
- [x] Escopo delimitado (gastos recorrentes = feature seguinte)
- [x] Dependências e premissas identificadas

## Feature Readiness
- [x] Cada FR tem critério de aceitação claro
- [x] User scenarios cobrem fluxos primários (P1: permuta + realizado/projetado)
- [x] Atende aos resultados mensuráveis
- [x] Sem vazamento de implementação nos requisitos

## Decisões do usuário (clarificações)
1. **Break-even / Estrutura**: por ora só Salários; cadastro de gastos recorrentes mensais será feature separada que alimentará o break-even.
2. **Constantes fiscais**: configuráveis em Settings (taxa imposto, corte Fator R).
3. **Receita projetada**: exibida separada de Realizado na DRE/KPIs.

## Notas
- Migration manual: `is_cortesia_permuta` (CalendarEvent), `tax_rate` + `fator_r_threshold` (SiteSetting).
- Reusa `with_invoice` para "Emitir Nota" — sem coluna duplicada.
- Stack: Flask + Jinja2 + CSS/JS vanilla (sem React/Tailwind).
