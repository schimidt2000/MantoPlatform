# Quickstart — conferir a 314

## 1. Verify (backend)

No worktree `C:\tmp\mp314`, em PowerShell:

```powershell
$env:DATABASE_URL = (Get-Content .local-db-url -Raw).Trim(); $env:FLASK_ENV = 'development'; $env:MANTO_SEM_THREADS = '1'; $env:PYTHONUTF8 = '1'
C:\Users\schim\Desktop\Manto_Platform\.venv\Scripts\python.exe specs\314-gastos-extras-filtros\verify_314.py
```

Esperado: todos os cenários `OK`. O cenário da mutação diz "verify morde: a regra quebrada derrubou o cenário 2". A
limpeza não deixa gasto nem usuário descartável no `manto_local` (o verify confere por conexão separada no fim).

Antes do núcleo (T do verify), o esperado é falhar no cenário 1 com "gasto sem `situacao`".

## 2. Typecheck

```powershell
cd frontend; npm run typecheck
```

## 3. Tela (skill `manto-conferir-tela`)

⚠️ `preview_start` num worktree sobe o Vite do **checkout principal** (lição da 316): suba o Vite deste worktree
(`frontend/apps/internal`) e o Flask apontando para o `manto_local`, ou use a receita da skill.

Como Superadmin, em `/gastos`:

| Largura | O que conferir |
|---|---|
| 1920 | página sem coluna central; tabela de 7 colunas sem barra lateral; Ações inteiras |
| 1366 | idem; "Devolução de cancelado: travada." inteira; nenhuma rolagem lateral (`document.documentElement.scrollWidth <= innerWidth`) |
| 1280 | idem (borda do `xl`) |
| 375 | cartões; nada cortado; sem rolagem lateral da página |

Fluxo:

1. Abertura: só aguardando + a pagar + no banco; cartões "Pagos — N gastos · R$ X" e "Rejeitados — …" fechados.
2. Abrir "Pagos" → lista aparece com animação; fechar → recolhe.
3. Cartão-filtro "A pagar" → só a pagar; reclicar → volta. "Todos" → volta.
4. Busca "lalamove" (ou um fornecedor do espelho) com e sem acento; contagem e total mudam; URL ganha `busca=`.
5. Categoria + mês; ‹ › ; "Todos os meses"; "Limpar filtros".
6. Recarregar com filtros → mesmo recorte.
7. Aprovar um gasto descartável → ele sai da lista principal e vai para o grupo certo sem recarregar; grupo
   aberto continua aberto.
8. Filtro sem resultado → "Nenhum gasto encontrado." + "Limpar filtros".

Repetir 1366 com um usuário sem papel de gestão (Casting): só os próprios, sem autor, sem Aprovar/Rejeitar.

Pagamentos (`/financeiro/pagamentos`): os cartões-filtro continuam iguais (o cartão foi extraído).
