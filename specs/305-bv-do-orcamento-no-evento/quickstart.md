# Quickstart — validar a Feature 305

## Pré-requisitos

- `manto_local` atualizado (`.local-db-url`); nada roda contra a produção.
- Todo script com `create_app()`:

```powershell
$env:DATABASE_URL = (Get-Content .local-db-url -Raw).Trim(); $env:FLASK_ENV = 'development'
$env:MANTO_SEM_THREADS = '1'; $env:PYTHONIOENCODING = 'utf-8'; $env:PYTHONUTF8 = '1'
```

## 1. Verify (Princípio VIII)

```powershell
.\.venv\Scripts\python.exe specs\305-bv-do-orcamento-no-evento\verify_305.py
```

Esperado: todos os cenários da tabela da spec verdes (os "deve falhar" verdes = a recusa aconteceu);
as duas mutações declaradas (cenários 17 e 49) quebram quando ligadas. Google dublado; eventos R&I;
limpeza no `finally`. Primeira rodada, antes do núcleo: vermelho pelos motivos certos (guardar a saída
em `verify_305_primeira_falha.txt`).

## 2. Regressão (cenário 27)

```powershell
.\.venv\Scripts\python.exe specs\273-*\verify_273.py
.\.venv\Scripts\python.exe specs\267b-hotfix-data-da-venda\verify_267b.py
.\.venv\Scripts\python.exe specs\301-orcamentos-visiveis-comercial\verify_301.py
.\.venv\Scripts\python.exe specs\215b-hotfix-taxa-e-vendedor\verify_215b.py
.\.venv\Scripts\python.exe specs\267c-hotfix-trava-do-lote\verify_267c.py
.\.venv\Scripts\python.exe specs\267-integridade-comissao\verify_267.py
```

Locais (gitignored, `scripts/db/`): `verify_249_comercial_ops.py`, `verify_251_acrescimos_parcelas_api.py`,
`verify_210_horario_anexo_orcamento.py`.

## 3. Portões

```bash
cd frontend && npm run typecheck
```

`ruff check` nos arquivos tocados; `ruff format` só nos novos; `npm run build` antes do merge.

## 4. Tela aberta (desktop; app interno — backend `manto-backend-sem-google`, front `manto-internal`)

Usuários temporários (Comercial, Financeiro, Superadmin) criados e apagados por script no scratchpad.

1. **Novo evento** a partir de um orçamento com BV: o quadro "BV · 10% → R$ X" muda com a duração;
   com venda diferente do total, o aviso de proporção; os campos "Quem recebe o BV" e "PIX de quem
   recebe" obrigatórios; o 400 cai nos campos.
2. **Aba Comercial → Acréscimos**: abrir e salvar sem mexer (PIX e "pago" ficam); rótulo do % do BV;
   recusa sem PIX na linha; valor com vírgula aceito; linha BV nova em %; BV em reais como digitado.
3. **Aba Comercial → Orçamento**: chip do BV; "Vincular e aplicar" pede os dois campos; frase do relatório.
4. **Alerta** num evento criado depois do corte (no painel Acréscimos, sob o valor de venda e na edição
   completa), "Lançar o BV" abrindo o editor preenchido em reais; um evento antigo (1218, 1236 ou 1268)
   aberto **sem** alerta.
5. **Venda que muda**: no VendaForm, mudar a venda com BV a pagar → aviso "O BV acompanhou a venda…".
6. **Planilha** do mês do evento como Financeiro: o BV com recebedor e PIX, sem "⚠ falta PIX".

## 5. Antes do merge (operação do agente)

- Recontar, só leitura, em produção (por SSH, `sql` read-only) as duas consultas da 3.7 do plano do
  backlog (vínculos com valores aplicados e BVs em % existentes).
- No último commit antes do merge, gravar `CORTE_ALERTA_BV` com `datetime.now(UTC)` do Python.
- Depois do push: sondar `GET /api/formularios/comum/schema` (JSON) e conferir o código no container.
