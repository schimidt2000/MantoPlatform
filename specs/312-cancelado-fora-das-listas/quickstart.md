# Quickstart — Feature 312

## 1. Verify contra o `manto_local`

```powershell
$env:DATABASE_URL = (Get-Content C:\Users\schim\Desktop\Manto_Platform\.local-db-url -Raw).Trim()
$env:FLASK_ENV = 'development'; $env:MANTO_SEM_THREADS = '1'; $env:PYTHONUTF8 = '1'
python specs/312-cancelado-fora-das-listas/verify_312.py            # rodada inteira
python specs/312-cancelado-fora-das-listas/verify_312.py --so=16     # um cenário (aspas no PowerShell: '--so=16d')
python specs/312-cancelado-fora-das-listas/verify_312.py --limpar    # só a limpeza
```

Antes de confiar numa rodada vermelha: nenhum outro `verify_*` rodando no mesmo `manto_local` (outro worktree).
Esperado: 23/23 verdes; contra a `main`, os cenários "deve falhar" vermelhos pelo motivo certo
(`verify_312_primeira_falha.txt`).

Regressão: `verify_306.py` (base 67/69), `verify_306b.py` 8/8, `verify_303.py`, e de `scripts/db/`
`verify_cancelamento_evento.py`, `verify_145_agenda_read.py`, `verify_196_dashboard_comercial.py`, `verify_205.py`.

## 2. Portões

```powershell
cd frontend; npm run typecheck; cd ..
ruff check <arquivos tocados>   # comparar com a main antes de acusar erro novo
```

## 3. Tela aberta

Semente de tela: `verify_312.py --semear-tela` (cancelado do exemplo com dois escalados, um principal vivo com um
dia cancelado, um gasto e uma tag ligados) e `--limpar-tela`. Backend `127.0.0.1:5011` (`t097_flask.py` do
scratchpad) e Vite `127.0.0.2:5193` (config temporária, fora do repo). Conferir, nos dois temas:

1. Agenda Dia/Mês/Lista e busca no dia do cancelado — ele não aparece; o marcado aparece.
2. Tela do cancelado como Superadmin (só consulta + painéis de venda), Comercial (motivo + frase "só o
   Superadmin altera") e Casting (sem motivo; escala com "Tirar da escala").
3. Home como Casting — "Eventos cancelados — excluir e avisar"; o WhatsApp abre com a mensagem; tirar some a
   linha.
4. Página de Cancelamentos como Financeiro (menu, filtros na URL, busca, vazio, 1024 px).
5. Dashboard Comercial (Superadmin e Comercial) e DRE — o card e os links.
6. Ficha da cliente (sublinha) e do talento; Gastos Extras (selo e select); painel do grupo do principal vivo.
7. Página pública de avaliação de 320 a 430 px; ficha de figurino do portal em 375×812.

## 4. Em produção, depois do deploy (só leitura)

Sem endpoint novo, a versão se prova por SSH (`git log -1` no `manto-backend` e grep do bundle do
`manto-frontend` por "Eventos cancelados — excluir e avisar"), e uma sonda `/api/` com JSON prova o Flask no ar.
Os dois cancelados (388 e 1358) fora do Dia e da busca.
