# Quickstart — Verificação manual da feature 066

**Rodar contra `manto_local` (Postgres)**: `.\scripts\db\run-local.ps1`

## Passo 1 — Admin edita CPF (US1, FR-001/003/004)

1. Como super admin, abrir a edição de um talento, alterar o CPF para um valor válido (11
   dígitos) e salvar.
   - ✅ CPF atualizado e exibido no perfil.
2. Informar CPF inválido (ex.: 9 dígitos).
   - ✅ Recusado com mensagem; CPF anterior mantido.
3. Informar um CPF já usado por outro talento.
   - ✅ Recusado (único); CPF anterior mantido.
4. Deixar o campo de CPF vazio e salvar.
   - ✅ Mantém o CPF atual (não apaga).

## Passo 2 — Não-admin não altera (US2, FR-002)

1. Como casting (não super admin), abrir a edição.
   - ✅ CPF aparece **somente leitura**.
2. Enviar uma alteração de CPF por formulário adulterado.
   - ✅ O servidor **não** altera o CPF.

## Passo 3 — Auditoria (FR-006)

1. Após uma alteração de CPF por admin.
   - ✅ Registro de auditoria criado (ator/ação), **sem** o número do CPF no texto.

## Checklist de qualidade (Portões da constituição)

- [ ] Sem migration.
- [ ] `ruff check` sem erros novos nos arquivos tocados.
- [ ] Verificado contra `manto_local` (Postgres): admin altera; não-admin bloqueado; inválido/
  duplicado recusados; vazio mantém.
- [ ] Demais campos do form sem regressão.
