# Tasks: Comissões visíveis para o comercial

**Input**: `specs/043-comissoes-comercial/`
**Tests**: boot + ruff + test client. Sem migration.

- [x] T001 Rota `comissoes`: `require_vendas`, `can_manage`, filtro por `seller_id` quando comercial.
- [x] T002 Template comissoes.html: ações/`← Financeiro` só com `can_manage`; subtítulo restrito.
- [x] T003 base.html: link "Comissões" no bloco do comercial.
- [x] T004 Verificação: ruff + boot + test client (US1–US3); commit.

## Dependencies
- T001 → T002; T003 independente; T004 por último.
