# Quickstart — validar a 353

## Pré-requisitos

Banco `manto_352` (dump de 17/11 + `f352a1b2c3d4`); URL no scratchpad da sessão. PowerShell:

```powershell
$env:DATABASE_URL = '<url do manto_352>'; $env:FLASK_ENV = 'development'; $env:MANTO_SEM_THREADS = '1'; $env:PYTHONUTF8 = '1'
```

## 1. Migration

```powershell
.venv\Scripts\python.exe -m flask db upgrade; .venv\Scripts\python.exe seed.py
```

Esperado: head `f352`→`f353a1b2c3d4`; tabela `gasto_parcelas` vazia; nenhum gasto muda.

## 2. Verify (e regressão)

```powershell
.venv\Scripts\python.exe specs\353-gasto-extra-parcelado\verify_353.py
.venv\Scripts\python.exe specs\352-fornecedores-gastos-extras\verify_352.py
.venv\Scripts\python.exe specs\331-atrasados-na-planilha\verify_331.py
```

## 3. Tela

1. Gastos Extras → "+ Novo gasto" → fornecedor "Adão Lima da Silva" → "Pagar em parcelas": duas linhas; R$ 500,00 em
   20/11 e R$ 700,00 em 30/11; o valor do gasto mostra R$ 1.200,00.
2. Como Financeiro: "Salvar e aprovar"; a lista mostra as parcelas.
3. Planilha de Pagamentos de novembro: dois itens "Parcela 1 de 2" e "Parcela 2 de 2"; marcar a primeira paga; o gasto
   fica "A pagar"; editar o gasto mostra a primeira travada.
