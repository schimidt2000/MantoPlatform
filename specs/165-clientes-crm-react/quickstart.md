# Quickstart — Clientes (CRM) em React (165)

## Rodar localmente

```powershell
.\scripts\db\run-local.ps1        # backend Flask contra manto_local
npm run dev:internal              # frontend, noutro terminal
```

## Roteiro manual

1. `/clientes` (React) — como Comercial/Financeiro/Superadmin, buscar por nome com acento e
   sem acento, conferir que os resultados batem com `/clientes` (Jinja) para o mesmo termo.
2. Abrir a ficha de um cliente com eventos associados e conferir eventos, relação e total vendido
   contra a tela antiga.
3. Editar CPF/CNPJ/endereço na ficha e confirmar persistência.
4. No seletor de cliente da tela de evento (React, já migrada), buscar/criar cliente e confirmar
   que o fluxo continua funcionando (agora via `/api/clientes/search` e `/api/clientes/
   quick-create`).
5. Como Comercial (sem Financeiro/Superadmin), tentar excluir um cliente e confirmar 403; como
   Financeiro/Superadmin, excluir um cliente com evento associado e confirmar que o evento
   permanece, agora sem cliente vinculado.
6. `/clientes/avaliacoes` (React) — aplicar cada filtro (período, nota, tag, cliente) e conferir
   totais/distribuição/lista de atenção contra a tela antiga.
7. Como usuário sem papel Comercial/Financeiro/Superadmin, confirmar 403 em todas as telas/API.

## Verificação automatizada

```powershell
$env:DATABASE_URL = (Get-Content .local-db-url -Raw).Trim(); $env:PYTHONPATH = (Get-Location).Path
.venv\Scripts\python.exe scripts\db\verify_165_clientes_react.py
```

Cobre paridade API×Jinja (busca, lista, ficha, avaliações) para Comercial/Financeiro/Superadmin,
criação rápida (novo + reaproveitado + erros de validação), edição, exclusão (sucesso e 403 para
Comercial) e o gate de acesso (403 fora dos papéis autorizados).
