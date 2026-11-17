# Quickstart — 328 Conversas em equipe

Contratos em [contracts/api.md](contracts/api.md); tabelas em [data-model.md](data-model.md).

## 1. Verificação automática (sem Meta)

Na worktree (`C:\tmp\mp328`), com o `.venv` ligado ao do checkout principal:

```powershell
$env:DATABASE_URL = (Get-Content .local-db-url -Raw).Trim(); $env:FLASK_ENV = 'development'; $env:MANTO_SEM_THREADS = '1'
$env:PYTHONUTF8 = '1'; .venv\Scripts\python.exe specs/328-crm-equipe-na-caixa/verify_328.py
```

Esperado: todos `OK` (inclusive os que **devem** falhar), 0 escapes de rede. O cenário do áudio gera um webm de
1 s com o ffmpeg local. Sem ffmpeg na máquina, ele é marcado como pulado e explica o motivo.

## 2. Tela

1. `flask db upgrade` no `manto_local` (migration da 328 sobre a da 325).
2. `verify_328.py --manter`: conversas, notas, respostas rápidas e as usuárias Ana e Bia de demonstração.
3. A `preview_start` usa a `launch.json` do **checkout principal**, que está em outra branch (memória "conferir
   tela em worktree"). Por isso, o backend e o Vite sobem da worktree, em outra porta (5328/5329), com
   `run_in_background`, e a tela abre por `preview_start {url}`.
4. Conferir:
   - os filtros "Todas", "Minhas" e "Sem responsável" e a espera;
   - Assumir, Transferir e Devolver;
   - a nota interna;
   - as respostas rápidas (inserir no campo e gerenciar);
   - o microfone (no Browser pane a permissão de microfone pode ser negada: conferir a mensagem);
   - desktop e 375×812.

## 3. Com o número de teste da Meta (depois, pelo dono)

Mesmo roteiro da 325 §3, mais:
- duas pessoas respondendo, para conferir que a primeira fica responsável;
- esperar 15 minutos sem responder, para ver o aviso no sino;
- gravar um áudio no Chrome e ouvir no celular como nota de voz.
