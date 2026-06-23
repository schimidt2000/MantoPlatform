# Tasks: Padronizar emojis das seções da home (073)

**Feature**: `073-padronizar-emojis-secoes` | **Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)

Só template. Verificação de render contra **`manto_local`**.

---

## Fase 1 — Rótulos (US1)

- [X] T001 [US1] `app/templates/home.html`: rótulo do cabeçalho **Casting** → `👥 Casting`.
- [X] T002 [US1] `app/templates/home.html`: rótulo do cabeçalho **Ensaio** → `🎭 Ensaio`.
- [X] T003 [US1] `app/templates/home.html`: rótulo do cabeçalho **Figurino** → `👗 Figurino`.

## Fase 2 — Verificação

- [X] T004 Render da home contra **`manto_local`**: confirmar `👥 Casting`, `🎭 Ensaio`, `👗 Figurino`; Nota Fiscal (🧾) e Comercial (💰) inalterados.

---

## Dependências

- T001/T002/T003 independentes; T004 ao final.

## MVP

T001–T003 entregam a padronização.
