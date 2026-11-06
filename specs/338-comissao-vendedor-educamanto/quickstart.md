# Quickstart — validar a 338

Pré-requisitos: worktree `C:\tmp\mp338`; banco `manto_338` (cópia da produção de 06/11, `research.md` R9),
com a URL em `C:\tmp\mp338\.local-db-url`; Python do `.venv` do checkout principal.

```powershell
cd C:\tmp\mp338
$env:DATABASE_URL = (Get-Content .local-db-url -Raw).Trim(); $env:FLASK_ENV = 'development'; $env:MANTO_SEM_THREADS = '1'; $env:PYTHONUTF8 = '1'
C:\Users\schim\Desktop\Manto_Platform\.venv\Scripts\python.exe -m flask db upgrade
C:\Users\schim\Desktop\Manto_Platform\.venv\Scripts\python.exe specs\338-comissao-vendedor-educamanto\verify_338.py
```

Esperado: todos os cenários `OK`, o cenário de autorização com o 403 que deve sair, e a limpeza sem resto.
Os números-âncora (produção de 06/11): Jundiaí Shopping → R$ 771,82; Santo Américo → R$ 61,01.

Portões: `cd frontend; npm run typecheck`; `ruff check` nos arquivos tocados; tela aberta (card Comercial de
um EducaManto e Comissões) no Browser pane, com backend e Vite próprios do worktree.

Depois do deploy (pelo dono): no evento do Jundiaí Shopping, card Comercial — vendedor Thaís e "Comissão do
vendedor" R$ 1.500; conferir em Comissões/Planilha: Gabriel R$ 771,82 + R$ 61,01; Thaís R$ 1.500 no repasse
de 05/11.
