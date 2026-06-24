# Tasks: Revendedor EducaManto + acréscimo + taxa interna (078)

**Feature**: `078-revendedor-educamanto` | **Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)

Sem migration. Verificação contra **`manto_local`**.

---

## Fase 1 — Perfil restrito (US1)

- [X] T001 `app/constants.py`: `RoleName.REVENDEDOR_EDUCAMANTO = "REVENDEDOR_EDUCAMANTO"`.
- [X] T002 `seed.py`: `get_or_create_role("REVENDEDOR_EDUCAMANTO")` (criado no deploy).
- [X] T003 `app/__init__.py`: helper `_is_revendedor_only(user)` + `@app.before_request` allow-list (permite `/agenda`, `/events/`, `/educamanto`, `/auth`, `/uploads`, `/static`, `/health`, `/impersonate/reset`; bloqueia o resto → redirect `/agenda`); `/` redireciona revendedor p/ `/agenda`. Injetar `is_revendedor_only` no contexto (context_processor).
- [X] T004 `app/templates/base.html`: nav — revendedor-only vê só **Agenda** + **EducaManto** (gate `not is_revendedor_only` nas demais seções/itens; EducaManto sem "Pacotes").
- [X] T005 `app/educamanto/routes.py`: `_CAN_USE += {REVENDEDOR_EDUCAMANTO}`; nav educamanto (base.html) inclui o perfil.

## Fase 2 — Limpar transporte (US2)

- [X] T006 [US2] `app/educamanto/index.html`: botão "Limpar" no bloco de transporte; JS reseta endereço/tKmIda/tipo/carretinha/pessoas e recalcula (transporte → 0).

## Fase 3 — Acréscimo do vendedor = comissão (US3)

- [X] T007 [US3] `app/educamanto/index.html`: campo "Acréscimo do vendedor (R$)" (máscara brl); soma ao valor final (sem/com NF) como o transporte; mostra "Comissão do vendedor: R$X".
- [X] T008 [US3] Geração: incluir o acréscimo nos valores enviados (sem_nota/com_nota já somados) + `acrescimo` no snapshot; PDF total já inclui (sem linha de comissão). `educamanto/routes.py` guarda `acrescimo` no snapshot.

## Fase 4 — Taxa interna (US4)

- [X] T009 [US4] `app/educamanto/index.html`: esconder a antiga "Comissão Vendedor" (sum-comissao) e o cfg "Comissão vendedor" (cfg-cr) da calculadora.
- [X] T010 [US4] `app/educamanto/package_form.html`: rótulo "Comissão do vendedor (%)" → "Taxa interna (%)" (campo `commission_rate` inalterado, segue customizável).

## Fase 5 — Verificação

- [X] T011 Contra **`manto_local`**: criar usuário só com REVENDEDOR_EDUCAMANTO → acessa /agenda e /educamanto (200); /financeiro,/talents,/admin,/ → bloqueado (302→/agenda); POST de edição de evento → negado. Limpar transporte zera; acréscimo soma ao final e ao PDF; package_form mostra "Taxa interna"; nav do revendedor só Agenda+EducaManto. `ruff` sem erros novos.

---

## Dependências

- T001 → T002/T003/T005. T003 → T004. T007 → T008. T011 ao final.

## MVP

T001–T005 (perfil) + T007/T008 (acréscimo) são o núcleo; T006/T009/T010 completam.
