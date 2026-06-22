# Quickstart — Verificação manual da feature 067

**Aplicar migration e rodar contra `manto_local` (Postgres)**:

```powershell
$env:DATABASE_URL = (Get-Content .local-db-url -Raw).Trim()
python -m flask db upgrade
.\scripts\db\run-local.ps1
```

## Passo 1 — Registrar adiantamento com comprovante (US1)

1. Em `/financeiro/pagamentos`, clicar em **Editar** num salário; informar adiantamento (ex.:
   R$ 300) e anexar um comprovante; salvar.
   - ✅ O item passa a mostrar o **líquido** (salário − 300) e indica o adiantamento; comprovante
     acessível.

## Passo 2 — Comprovante obrigatório / limite (FR-002/004)

1. Tentar salvar adiantamento > 0 **sem** comprovante.
   - ✅ Recusado com mensagem.
2. Tentar adiantamento **maior** que o salário.
   - ✅ Recusado com mensagem.

## Passo 3 — Editar/zerar (US2)

1. Alterar o adiantamento (novo comprovante) → líquido recalculado.
2. Zerar o adiantamento → item volta ao valor cheio (sem exigir comprovante).

## Passo 4 — Balanço inalterado (FR-008)

1. Conferir o custo de salário do período no painel antes/depois de um adiantamento.
   - ✅ Igual (adiantamento é caixa, não custo).

## Checklist de qualidade (Portões da constituição)

- [ ] Migration manual aplica e reverte.
- [ ] `ruff check` sem erros novos nos arquivos tocados.
- [ ] Verificado contra `manto_local` (Postgres): líquido, obrigatoriedade do comprovante, limite,
  custo de salário inalterado.
- [ ] Ações de pagamento e demais itens sem regressão.
