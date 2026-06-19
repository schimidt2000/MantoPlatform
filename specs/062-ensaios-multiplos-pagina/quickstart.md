# Quickstart — Verificação manual da feature 062

**Rodar contra a cópia local `manto_local` (Postgres)**: `.\scripts\db\run-local.ps1`

## Passo 1 — Múltiplos ensaios (US1, FR-001..004)

1. Num show, marcar um ensaio (data A) e depois **outro** (data B).
   - ✅ Os dois aparecem (ordenados por data) na página do show e na home.
2. Na home, no card "Ensaios agendados" de um show, usar **"+ Marcar outro ensaio"**.
   - ✅ Cria mais um ensaio e volta para a home.

## Passo 2 — Página de ensaio simplificada (US2, FR-005/006/007)

1. Abrir um ensaio (clicando nele na agenda, ou via link).
   - ✅ Mostra só: data/hora, local, descrição e o **show de origem** (com link).
   - ✅ **Não** mostra casting, figurino, venda/financeiro, contrato, pagamentos, NF, agrupamento.
2. Como equipe de ensaio/admin: **editar** e **cancelar** o ensaio pela própria página.
   - ✅ Editar salva e permanece na página do ensaio; cancelar remove e volta ao show/home.

## Passo 3 — Órfão (FR-008, feature 057)

1. Abrir um ensaio cujo show não existe mais.
   - ✅ Página simplificada funciona; avisa que não há show; permite cancelar.

## Checklist de qualidade (Portões da constituição)

- [ ] Sem migration.
- [ ] `ruff check` sem erros novos nos arquivos tocados (comparar com `git stash`).
- [ ] Verificado contra `manto_local` (Postgres).
- [ ] Página de show e cancelar de órfão sem regressão.
