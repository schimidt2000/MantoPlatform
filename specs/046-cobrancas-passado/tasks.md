# Tasks: Cobranças comerciais incluindo o passado

**Input**: `specs/046-cobrancas-passado/`
**Tests**: boot + ruff + test client. Sem migration.

- [x] T001 `app/__init__.py`: severidade `atrasado`/`vencido`, flag `is_past`, ordenação (atrasados
      primeiro, mais antigos no topo).
- [x] T002 `app/templates/home.html`: badges ATRASADO/VENCIDO/URGENTE/SINAL PENDENTE + realce.
- [x] T003 `app/templates/admin_settings.html`: ajuda do `release_date` citando as cobranças.
- [x] T004 Verificação (US1–US3) + commit.

## Dependencies
- T001 → T002; T003 independente; T004 por último.
