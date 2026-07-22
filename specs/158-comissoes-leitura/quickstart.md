# Quickstart — Comissões em React (158)

## Rodar localmente

```powershell
.\scripts\db\run-local.ps1        # backend Flask contra manto_local
npm run dev:internal              # frontend, noutro terminal
```

## Roteiro manual

1. `/financeiro/comissoes` — como Financeiro/Superadmin, conferir a lista de comissões do mês
   corrente com os mesmos valores da tela antiga (`/financeiro/comissoes`).
2. Trocar o mês (seletor `YYYY-MM`) e conferir que a lista e o total a pagar recalculam.
3. Conferir que estornos pendentes aparecem numa lista separada, somados ao total, independente
   do mês selecionado.
4. Como usuário Comercial (sem papel Financeiro/Superadmin), confirmar que só as próprias
   comissões/estornos aparecem, sem seletor de vendedor.
5. Como responsável EducaManto configurado (sem papel Comercial/Financeiro), confirmar acesso
   liberado e visão restrita às próprias comissões.
6. Como usuário sem nenhum dos papéis/exceção acima, confirmar que a tela/API recusa acesso (403).

## Verificação automatizada

```powershell
$env:DATABASE_URL = (Get-Content .local-db-url -Raw).Trim(); $env:PYTHONPATH = (Get-Location).Path
.venv\Scripts\python.exe scripts\db\verify_158_financeiro_comissoes.py
```

Cobre paridade API×Jinja (entries, estornos, total a pagar) para Financeiro e para Comercial,
filtro de mês (válido/inválido/default), e o gate de acesso (403 fora de Comercial/Financeiro/
Superadmin/responsável EducaManto).
