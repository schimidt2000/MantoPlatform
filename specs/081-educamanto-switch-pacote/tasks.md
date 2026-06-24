# Tasks: Trocar de plano sem reload (081)

**Feature**: `081-educamanto-switch-pacote` | **Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)

Só template. Verificação contra **`manto_local`**.

---

## Fase 1 — Troca client-side (US1)

- [X] T001 [US1] `educamanto/index.html`: seletor de pacote `onchange="switchPackage(this.value)"` (sem reload); link "Editar pacote" recebe `id="edu-edit-link"`.
- [X] T002 [US1] JS `window.switchPackage(id)`: troca `pkg`, `loadConfig()`, `calcular()`, atualiza o href do "Editar pacote" e a URL (`history.replaceState`). Preserva dias/ensemble/transporte/acréscimo.

## Fase 2 — Cap por plano consistente (US1)

- [X] T003 [US1] `calcular()`: cap do acréscimo = `min(digitado, valor original do plano)`, **sem reescrever** o input (preserva ao trocar); aviso de máximo.
- [X] T004 [US1] `gerarOrcamento()`: para cada pacote, cap por plano `min(digitado, original do pacote)` antes de `valoresPacote` — mesma fórmula da tela, garantindo PDF == tela.

## Fase 3 — Verificação

- [X] T005 Contra **`manto_local`**: seletor usa `switchPackage` (sem `location.href`); render OK; réplica confirma valor por plano (cap por plano) idêntico entre tela e PDF; JS balanceado.

---

## Dependências

- T001 → T002. T003/T004 (consistência). T005 ao final.

## MVP

T001/T002 (sem reload) resolvem o relato; T003/T004 garantem paridade tela/PDF.
