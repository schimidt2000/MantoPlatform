# Tasks: Correções da calculadora EducaManto (079)

**Feature**: `079-educamanto-calc-fixes` | **Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)

Só template. Verificação contra **`manto_local`**.

---

## Fase 1 — Tempo real (US1)

- [X] T001 [US1] `educamanto/index.html`: `acrescimoValor()` lê o valor localmente (dígitos→centavos), **sem** `_brlSum` (que não existe nesta tela e quebrava `calcular()`).

## Fase 2 — Pessoas = catering apresentação (US2)

- [X] T002 [US2] `educamanto/index.html`: `cateringApresentacaoQty(E)` (acha o item "Catering apresentação", qty + ensemble_add·E) e `syncPessoasTransporte(E)` que seta `#t-pessoas`; campo `#t-pessoas` vira **readonly**; chamado em `calcular()` antes de `calcTransporte()`.

## Fase 3 — Acréscimo / com NF (US3)

- [X] T003 [US3] `educamanto/index.html`: `valoresPacote(p,d1,d2,E,acrescimo)` — sem NF = ceil100(original+acréscimo); com NF = ceil100((original+acréscimo)/0,84). `calcular()` e `gerarOrcamento()` passam o acréscimo; transporte somado plano aos dois valores.

## Fase 4 — Verificação

- [X] T004 Contra **`manto_local`**: página renderiza; `_brlSum` só em comentário; réplica confirma sem/com NF (ratio ~1,19) e pessoas = catering apresentação; com acréscimo, sem soma e com = (orig+acr)/0,84.

---

## Dependências

- T001/T002/T003 no mesmo arquivo; T004 ao final.

## MVP

T001 (tempo real) desbloqueia tudo; T002/T003 completam.
