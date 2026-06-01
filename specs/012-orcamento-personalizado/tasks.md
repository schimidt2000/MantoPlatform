# Tasks: Orçamento personalizado (valor final ou multiplicador)

**Input**: `specs/012-orcamento-personalizado/` (spec.md, plan.md)
**Tests**: sem suíte automatizada — verificação manual no app real.

## Phase 1: Servidor (fork de cálculo)

- [ ] T001 Em [app/orcamento/routes.py](../../app/orcamento/routes.py): helper `_parse_num(raw)`
      (vírgula→ponto; retorna float ≥ 0 ou None) e leitura dos campos personalizados do form.
- [ ] T002 Em `_process_quote`: capturar `cache_base = list(cache_totals)` logo após somar
      coordenador + show customizado (antes de `aplicar_markup`).
- [ ] T003 Em `_process_quote`: envolver o bloco automático (markup + brinde + noturno + técnico +
      maquiador + transporte especial/BGE + transporte fora SP + acréscimo + NF + duração custom)
      em `if not personalizado:`; no `else`, calcular `totals` por critério (multiplicador →
      `cache_base[i]*mult[i]`; valor_final → `valor[i]`), com `transport_breakdown=None`,
      `transport_total=0`, `total_custom=None`. Fallback: valores inválidos → flash + redirect.
- [ ] T004 Persistir personalização: adicionar ao `session["orcamento_quote"]` (`personalizado`,
      `personalizado_criterio`, `cache_base`, `custom_mult`) e ao `snapshot` do histórico
      (`personalizado_ativo`, `personalizado_criterio`, `cust_mult_*`, `cust_valor_*`).

## Phase 2: Formulário (UI + estado)

- [ ] T005 [app/templates/orcamento/index.html](../../app/templates/orcamento/index.html): painel
      "Personalizar valores" (toggle + radios critério + 3 campos por duração + leitura do
      cachê-base) abaixo de "Incluir no orçamento".
- [ ] T006 [app/static/js/orcamento.js](../../app/static/js/orcamento.js): estado
      (`personalizadoAtivo/Criterio`, `custMult`, `custValor`) + handlers (ativar, trocar critério,
      pré-preencher multiplicador com o markup vigente, exibir cachê-base).
- [ ] T007 `calcTotals()`: fork personalizado (base × mult ou valor final; sem extras). Refatorar
      para expor `cacheBase()` reutilizável.
- [ ] T008 `updateDebugPanel()`: no modo personalizado, mostrar até "Subtotal Cachê" + linha
      "Personalizado" e early-return.
- [ ] T009 Submit handler: preencher hidden fields personalizados; validar (durações incluídas com
      total > 0) com `.orc-field-error`.

## Phase 3: Resultado + histórico

- [ ] T010 [app/templates/orcamento/resultado.html](../../app/templates/orcamento/resultado.html):
      nota "Orçamento personalizado" (critério; para multiplicador, base × mult = total por duração).
- [ ] T011 `_applySnapshot` (JS): restaurar painel e campos personalizados ao reabrir do histórico.

## Phase 4: Polish

- [ ] T012 `ruff check` nos .py tocados.
- [ ] T013 Verificação no app real: valor final 2400→2400 (PIX 2280); multiplicador = base×mult;
      transporte/NF não somam no modo; modo desligado idêntico ao atual; reabrir restaura.

## Dependencies
- T001→T002→T003→T004. T005→T006→T007→T008→T009. T010, T011 após Phase 1/2.

## Notes
- Sem migration. Reaproveita mensagem/PDF/email/histórico/seleção de durações (feature 003).
- Inputs `number` (mult com `×`, valor com prefixo `R$`); máscara BRL fica para depois.
