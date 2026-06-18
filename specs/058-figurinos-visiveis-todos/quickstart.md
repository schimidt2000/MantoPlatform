# Quickstart — Verificação manual da feature 058

Validar visualização aberta + edição restrita, no app real (`python run.py`).

## Passo 1 — Visualização para todos (US1, FR-001/FR-002)

1. Logar com um perfil **sem** FIGURINO/SUPERADMIN (ex.: comercial).
2. Conferir o menu: item **"Figurinos"** aparece.
3. Abrir `/figurinos`: catálogo visível; abrir a impressão de uma ficha.
   - ✅ Visualiza e imprime.
4. Conferir que **não** há botões de criar/editar/excluir/sync.

## Passo 2 — Edição restrita na UI (US2, FR-004/FR-005)

1. Como FIGURINO ou SUPERADMIN, abrir `/figurinos`.
   - ✅ Botões "Nova Ficha", lápis "Editar", "Sync Drive" (superadmin) aparecem.

## Passo 3 — Edição restrita no servidor (US2, FR-003/FR-006)

1. Como usuário **sem** permissão, acessar por URL direta:
   `/figurinos/new`, `/figurinos/<id>/edit`, `delete`, `rotate-photo`, `sync-drive`.
   - ✅ Todas retornam **403** (acesso negado); nada é alterado.
2. Como FIGURINO/SUPERADMIN, repetir.
   - ✅ Funcionam normalmente (sem regressão).

## Checklist de qualidade (Portões da constituição)

- [ ] Sem migration (modelo inalterado).
- [ ] `ruff check` sem erros novos nos arquivos tocados.
- [ ] Recusa no servidor (não só botão escondido).
- [ ] Comportamento conferido no app real (Princípio IV).
