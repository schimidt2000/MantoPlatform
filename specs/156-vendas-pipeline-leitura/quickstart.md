# Quickstart — Pipeline de Vendas em React (156)

## Rodar localmente

```powershell
.\scripts\db\run-local.ps1        # backend Flask contra manto_local
npm run dev:internal              # frontend, noutro terminal
```

## Roteiro manual

1. `/vendas` — como Comercial, conferir lista de eventos com venda/custo/comissão (sem coluna
   de lucro).
2. Mesma tela como Financeiro/Superadmin — conferir que a coluna de lucro aparece.
3. Conferir que evento satélite não aparece como linha própria (some no grupo do principal).
4. Clicar em "Ver" num evento — deve abrir o detalhe React já existente.
5. Como usuário sem papel Comercial/Financeiro/Superadmin (nem responsável EducaManto),
   confirmar que a tela/API recusa acesso (403).

## Verificação automatizada

```powershell
$env:DATABASE_URL = (Get-Content .local-db-url -Raw).Trim(); $env:PYTHONPATH = (Get-Location).Path
.venv\Scripts\python.exe scripts\db\verify_156_vendas_pipeline.py
```

Cobre paridade API×Jinja (venda/custo/comissão/lucro), exclusão de satélites, filtro do
responsável EducaManto, e os gates de acesso (403 para papel fora de Vendas).
