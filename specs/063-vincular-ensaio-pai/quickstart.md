# Quickstart — Verificação manual da feature 063

**Rodar contra a cópia local `manto_local` (Postgres)**: `.\scripts\db\run-local.ps1`

## Passo 1 — Vincular ensaio órfão (US1, FR-001/004)

1. Abrir um ensaio órfão (bloco "Show de origem" diz que não há show).
2. No form, **buscar** um show pelo nome, selecionar e **Vincular**.
   - ✅ A página passa a mostrar o show em "Show de origem" (com link).
   - ✅ Abrir o show: o ensaio aparece na lista de ensaios dele.

## Passo 2 — Trocar o pai (US2, FR-002)

1. Num ensaio já vinculado, escolher **outro** show e confirmar.
   - ✅ Passa a apontar para o novo show; some da lista do show antigo.

## Passo 3 — Rejeições (FR-003/006)

1. Confirmar sem selecionar nada → mensagem clara, sem mudança.
2. A lista **não** oferece eventos do tipo ENSAIO nem o próprio ensaio.
3. (Servidor) tentar vincular a um id de ensaio/ao próprio → recusado.

## Passo 4 — Permissão (FR-005)

1. Usuário sem perfil de ensaio/casting/admin não vê a ação (e a rota recusa).

## Checklist de qualidade (Portões da constituição)

- [ ] Sem migration.
- [ ] `ruff check` sem erros novos nos arquivos tocados.
- [ ] Verificado contra `manto_local` (Postgres).
- [ ] Criação/edição/cancelamento de ensaio e página de show sem regressão.
