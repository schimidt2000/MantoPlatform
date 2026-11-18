# Quickstart — validar a 352

## Pré-requisitos

- Banco `manto_352` (dump de produção de 17/11 02h00). URL: a de `.local-db-url` trocando o nome do
  banco para `manto_352` (guardada fora do repositório, no scratchpad da sessão).
- PowerShell:

```powershell
$env:DATABASE_URL = '<url do manto_352>'; $env:FLASK_ENV = 'development'; $env:MANTO_SEM_THREADS = '1'; $env:PYTHONUTF8 = '1'
```

## 1. Ensaio da migration (sequência real do start)

```powershell
.venv\Scripts\flask.exe db upgrade; .venv\Scripts\python.exe seed.py
```

Esperado: head `f352a1b2c3d4`; 41 fornecedores; `select count(*) from special_expenses where
disbursement_type='fornecedor' and fornecedor_id is null` = 0; "Adão Lima da Silva" com 5 gastos.

## 2. Verify

```powershell
.venv\Scripts\python.exe specs\352-fornecedores-gastos-extras\verify_352.py
```

Esperado: todos os cenários OK, inclusive o 9 (Figurino recebe 403).

## 3. Tela (Browser pane, 390px e desktop)

1. Gastos Extras → "+ Novo gasto" → "Pagamento a fornecedor" → digitar "thun": aparece "Thunder Print
   3D" com PIX e "Marketing"; escolher preenche nome, PIX e categoria.
2. Digitar um nome inexistente: aparece "Fornecedor novo: ficará salvo para os próximos gastos."
3. Como Financeiro: botão "Fornecedores" → lista com totais; alterar, arquivar/reativar e juntar
   (o diálogo diz quantos gastos passam e o que deixa de existir).
4. Typecheck: `cd frontend; npm run typecheck`.
