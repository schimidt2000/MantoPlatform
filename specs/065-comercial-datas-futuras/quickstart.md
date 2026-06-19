# Quickstart — Verificação manual da feature 065

**Aplicar migration e rodar contra `manto_local` (Postgres)**:

```powershell
$env:DATABASE_URL = (Get-Content .local-db-url -Raw).Trim()
python -m flask db upgrade
.\scripts\db\run-local.ps1
```

## Passo 1 — Parcelas com data e valor (US1, FR-001/002/007)

1. Num evento, em Dados de Venda, escolher **"Parcelado (datas)"**, adicionar 2 parcelas
   (datas futuras distintas + valores), salvar e reabrir.
   - ✅ As 2 parcelas aparecem; soma exibida; aviso se ≠ valor de venda.
2. Editar/remover/adicionar parcela e salvar.
   - ✅ Cronograma reflete as mudanças.

## Passo 2 — Data de emissão da NF (US2, FR-003)

1. Marcar "emitir nota" e informar a **data prevista de emissão**; salvar e reabrir.
   - ✅ Data persiste e é exibida.

## Passo 3 — Painel: recebimentos previstos + NF a emitir (US3, FR-004/005/006)

1. No painel, no período que contém as datas das parcelas/NF:
   - ✅ Seção "Recebimentos previstos" lista as parcelas (data, evento, valor) + total.
   - ✅ Seção "NF a emitir" lista os eventos (data, evento, valor) + total.
2. Conferir a **receita** do período.
   - ✅ Igual ao comportamento anterior (não mudou por causa das datas futuras).

## Checklist de qualidade (Portões da constituição)

- [ ] Migration manual aplica e reverte (`flask db upgrade`/`downgrade`).
- [ ] `ruff check` sem erros novos nos arquivos tocados.
- [ ] Verificado contra `manto_local` (Postgres): persistência + painel + receita inalterada.
- [ ] Métodos de pagamento e comprovantes atuais sem regressão.
