# Tasks: Talento estrangeiro + telefone com país (092)

**Feature**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)

Sem testes automatizados solicitados — verificação manual contra `manto_local` (Postgres).

## Phase 1: Foundational (modelo + migração)

- [ ] T001 `app/models.py`: `cpf` → `nullable=True`; adicionar `is_foreigner` (Boolean, default False,
  server_default "0"); adicionar `@property whatsapp_number` (dígitos com país; fallback `55` quando sem `+`).
- [ ] T002 Migração `migrations/versions/a3d4e5f6a7b8_estrangeiro_telefone_pais.py` (down_revision
  `z2c3d4e5f6a7`): add `is_foreigner`, alter `cpf` nullable, e `UPDATE` prefixando `+55 ` aos telefones sem `+`.

## Phase 2: US1 — Cadastro estrangeiro sem CPF (P1) 🎯 MVP

- [ ] T003 [US1] `templates/cadastro/form.html`: checkbox "Sou estrangeiro(a) (não tenho CPF)" + JS que
  remove o `required` do CPF quando marcado; seletor de país (DDI, Brasil padrão) + número no telefone.
- [ ] T004 [US1] `app/cadastro/routes.py` `submit()`: ler `is_foreigner`; se estrangeiro, CPF opcional
  (`None`) e exigir documento substituto; combinar `phone_ddi` + `phone_national` em `+55 <número>`.

## Phase 3: US2 — Acesso ao portal por e-mail (P1)

- [ ] T005 [US2] `app/talent_portal/routes.py`: helper `_talent_by_login(value)` (e-mail ou CPF) usado em
  `login`, `first_access`, `forgot_password`.
- [ ] T006 [US2] `templates/portal/login.html`, `first_access.html`, `forgot_password.html`: rótulo
  "CPF ou e-mail".

## Phase 4: US3 — Telefone com país + WhatsApp

- [ ] T007 [US3] `templates/event_detail.html`: `wa.me/55{{ phone_digits }}` → `wa.me/{{ whatsapp_number }}`
  (2 ocorrências).

## Phase 5: Verificação

- [ ] T008 Verificar contra `manto_local`: migração aplica (telefones com `+55`, sem duplicar); cadastro
  estrangeiro sem CPF OK; brasileiro sem CPF dá erro; login/first-access por e-mail e por CPF; `whatsapp_number`
  correto. `ruff` sem erros novos.

## Dependencies

- T001 → T002 (modelo antes da migração). T003/T004 (US1) dependem do modelo. T005/T006 (US2) independem de US1.
  T007 depende de `whatsapp_number` (T001). T008 por último.

## MVP

US1 (cadastro estrangeiro) + US2 (acesso por e-mail) = MVP funcional para a pessoa estrangeira.
