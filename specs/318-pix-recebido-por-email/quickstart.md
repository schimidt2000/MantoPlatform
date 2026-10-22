# Quickstart — 318

## 1. Verificar (local)

```powershell
$env:DATABASE_URL = (Get-Content .local-db-url -Raw).Trim(); $env:FLASK_ENV = 'development'; $env:MANTO_SEM_THREADS = '1'; $env:PYTHONUTF8 = '1'
python specs/318-pix-recebido-por-email/verify_318.py
```

Esperado: todos os cenários da tabela da spec verdes (os "deve falhar" recusados). Migration antes:
`flask db upgrade` no `manto_local` e ensaio no dump fresco (`flask db upgrade && python seed.py`, downgrade, upgrade).

## 2. Ensaio contra os PIX reais (antes de ligar)

```powershell
python specs/318-pix-recebido-por-email/ensaio_318.py --desde 2026-06-01 --gabarito "C:\Users\schim\Downloads\Manto_diagnostico_financeiro_2026-10-21\detalhes\receitas_entradas_classificadas.csv"
```

Lê a caixa joao@manto (só leitura), roda a regra no `manto_local` com rollback, imprime só contagens. Critério:
`auto_errado = 0`. Guardar a saída (sem nomes) na entrada do `docs/03`.

## 3. Tela aberta

Skill `manto-conferir-tela`: `/pix` (fila com PIX sintético, resumo por conta, saúde, config como
Superadmin), Home (linha "PIX para conferir"), página do evento (pagamento de PIX sem arquivo; anexar comprovante →
pergunta de duplicata; campo "Conta que recebeu").

## 4. Depois do deploy (dono)

1. Filtro da Prime → joao@manto: **feito em 22/10/2026**.
2. `/pix` → Configuração: número das contas Inter MEI e Inter Prime (como aparece no aviso "na conta …"),
   conferir pagadores próprios (acrescentar o nome do sócio), **ligar**.
3. No dia seguinte: faixa de saúde sem alerta; "contas vistas" com Inter MEI e Inter Prime; conferir as primeiras
   ligações automáticas.
