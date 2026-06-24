# Tasks: Senha auto + salário comissão (084)

**Feature**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)

Sem testes automatizados solicitados — verificação manual contra `manto_local`.

## Phase 1: User Story 1 — Salário só comissão / sem salário (P1) 🎯 MVP

- [X] T001 [US1] Adicionar helper `_normalize_salary(salary_value, payment_type)` em
  `app/admin/routes.py` (comissao→0; semanal/quinzenal exigem >0; senão erro de tipo).
- [X] T002 [US1] Reescrever `_parse_salary_form()` em `app/admin/routes.py`: seção opcional quando sem
  tipo e salário vazio/0 (corrige default "0,00"); usar `_normalize_salary` para o restante.
- [X] T003 [US1] Atualizar `add_salary()` em `app/admin/routes.py` para validar via `_normalize_salary`
  (mantém flash/redirect), aceitando "Somente comissão" com base 0.

## Phase 2: User Story 2 — Senha de primeiro uso gerada e copiada (P1)

- [X] T004 [US2] Em `app/templates/admin_create_user.html`: campo de senha legível + botão "🔄 Gerar
  nova"; gerar senha forte no carregamento (modo com acesso) e ao clicar no botão.
- [X] T005 [US2] Em `app/templates/admin_create_user.html`: copiar a senha para a área de transferência
  no submit (modo com acesso), de forma síncrona, antes do envio.
- [X] T006 [US2] Em `create_user()` (`app/admin/routes.py`): no sucesso "com acesso", flash informando
  que a senha de primeiro uso foi copiada para a área de transferência.

## Phase 3: Polish & Verificação

- [X] T007 Verificar contra `manto_local`: criar usuário comissão (salary=0, payment_type='comissao');
  criar usuário sem salário (sem registro); semanal/quinzenal sem valor barrado; GET da tela traz JS de
  geração/cópia. Rodar `ruff` (sem erros novos).

## Dependencies

- T001 → T002, T001 → T003 (helper antes dos usos).
- T004 → T005 (geração antes da cópia).
- T001–T003 (routes.py) e T004–T005 (template) tocam arquivos diferentes — mas T006 também é routes.py;
  manter routes.py sequencial.
- T007 por último.

## MVP

User Story 1 (correção do salário) é o MVP — destrava a criação de usuários hoje quebrada.
